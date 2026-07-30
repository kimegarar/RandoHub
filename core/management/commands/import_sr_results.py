# core/management/commands/import_sr_results.py

import csv
import io
import re
import os
import requests
import unicodedata
from datetime import timedelta, datetime
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core import management
from core.models import Randonneur, Event, Result


def sanear_corrupcion_encoding(texto):
    """
    Corrige artefactos comunes de decodificacion corrupta de tildes
    y eñes antes de realizar la comparacion de tokens.
    """
    texto = re.sub(r'^\d+\s+', '', texto)
    texto = re.sub(r'^nuevo/\s*', '', texto)
    texto = texto.lower()

    # Se eliminan caracteres no alfabeticos comunes primero para normalizar
    texto = re.sub(r'[^a-z\s]', '', texto)

    reemplazos = {
        'lapez': 'lopez',
        'lape': 'lope',
        'gomez': 'gomez',
        'sancez': 'sanchez',
        'rodrigez': 'rodriguez',
    }
    for corrupto, corregido in reemplazos.items():
        texto = texto.replace(corrupto, corregido)
    return texto


# Diccionario de equivalencias de cabeceras para soportar multiples idiomas y formatos
HEADER_MAPPINGS = {
    'first_name': ['first_name', 'nombre', 'prenom', 'first name', 'given name', 'name'],
    'last_name': ['last_name', 'apellido', 'apellidos', 'nom', 'last name', 'family name', 'surname'],
    'country': ['country', 'pais', 'pays', 'nationality', 'nacionalidad', 'nat'],
    'gender': ['gender', 'sexo', 'sexe', 'sex', 'gender'],
    'route_name': ['route_name', 'ruta', 'sr_name', 'super_randonnee', 'sr name', 'route', 'prueba'],
    'route_country': ['route_country', 'route country', 'pais_ruta', 'pays_sr', 'route_nat'],
    'date': ['date', 'fecha', 'date_started', 'start_date', 'date'],
    'time': ['time', 'tiempo', 'duracion', 'duration', 'time_registered', 'h'],
    'status': ['status', 'estado', 'completion'],
    'modality': ['modality', 'modalidad', 'mode', 'rando_tourist', 'type', 'option', 'version'],
    'homologation_code': ['homologation_code', 'homologation', 'code', 'cert', 'certificate', 'numero', 'homol']
}


def normalizar_cabecera(cabecera_cruda):
    """
    Normaliza el nombre de una columna para buscar su equivalencia en el mapeador.
    """
    cabecera = cabecera_cruda.strip().lower()
    cabecera = unicodedata.normalize('NFD', cabecera)
    cabecera = "".join([c for c in cabecera if not unicodedata.combining(c)])
    cabecera = re.sub(r'[^a-z0-9_]', '', cabecera.replace(' ', '_'))

    for clave_estandar, sinonimos in HEADER_MAPPINGS.items():
        if cabecera in sinonimos:
            return clave_estandar
    return None


class Command(BaseCommand):
    help = "Importa y procesa cualquier hoja de resultados de SR600 desde una URL de Google Sheets o un archivo CSV"

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, required=True,
                            help="Ruta al archivo CSV local o URL de Google Sheets")

    def handle(self, *args, **options):
        source = options['source']
        self.stdout.write(f"Iniciando ingesta de resultados desde la fuente: {source}...")

        # Convertir URL de Google Sheets a exportacion CSV nativa si aplica
        if "docs.google.com/spreadsheets" in source:
            source = re.sub(r'/edit.*$', '/export?format=csv', source)
            try:
                response = requests.get(source, timeout=15)
                response.raise_for_status()
                csv_file = io.StringIO(response.text)
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Error de conexion al descargar la hoja de Google: {e}"))
                return
        else:
            if not os.path.exists(source):
                self.stdout.write(self.style.ERROR(f"No se encontro el archivo local: {source}"))
                return
            csv_file = open(source, 'r', encoding='utf-8')

        reader = csv.reader(csv_file)

        # Recuperar y normalizar las cabeceras de las columnas para el mapeo dinamico
        try:
            raw_headers = next(reader)
        except StopIteration:
            self.stdout.write(self.style.ERROR("El archivo de origen esta vacio."))
            return

        mapeo_columnas = {}
        for idx, col in enumerate(raw_headers):
            clave_estandar = normalizar_cabecera(col)
            if clave_estandar:
                mapeo_columnas[clave_estandar] = idx

        # Validacion de columnas criticas de negocio
        columnas_obligatorias = ['first_name', 'last_name', 'route_name']
        for col in columnas_obligatorias:
            if col not in mapeo_columnas:
                self.stdout.write(
                    self.style.ERROR(f"Error: No se pudo identificar la columna equivalente para '{col}'."))
                return

        resultados_creados = 0
        randonneurs_creados = 0
        eventos_creados = 0
        randonneurs_afectados = set()

        for row in reader:
            if not row or len(row) < len(mapeo_columnas):
                continue

            # Extraccion dinamica usando el indice mapeado
            raw_first_name = row[mapeo_columnas['first_name']]
            raw_last_name = row[mapeo_columnas['last_name']]
            raw_route_name = row[mapeo_columnas['route_name']]

            if not raw_first_name or not raw_last_name or not raw_route_name:
                continue

            nombre = sanear_corrupcion_encoding(raw_first_name).upper()
            apellidos = sanear_corrupcion_encoding(raw_last_name).upper()

            # Obtencion de variables opcionales con valores de respaldo seguros
            country = row[mapeo_columnas['country']].strip().upper() if 'country' in mapeo_columnas else 'ES'
            if len(country) != 2:
                country = 'ES'

            gender = row[mapeo_columnas['gender']].strip().upper() if 'gender' in mapeo_columnas else None
            gender = gender if gender in ['M', 'F', 'O'] else None

            # 1. Gestion relacional del Ciclista (Randonneur)
            randonneur_obj, r_created = Randonneur.objects.get_or_create(
                first_name=nombre,
                last_name=apellidos,
                defaults={
                    'country': country,
                    'gender': gender,
                    'is_claimed': False,
                    'user': None
                }
            )
            if r_created:
                randonneurs_creados += 1
            randonneurs_afectados.add(randonneur_obj)

            # 2. Gestion relacional de la Ruta Permanente (Event)
            route_slug = f"sr600-{slugify(raw_route_name)}"
            route_country = row[
                mapeo_columnas['route_country']].strip().upper() if 'route_country' in mapeo_columnas else 'ES'
            if len(route_country) != 2:
                route_country = 'ES'

            year_str = row[mapeo_columnas['date']].strip() if 'date' in mapeo_columnas else '2024'
            try:
                year = int(year_str[:4]) if '-' in year_str else int(year_str[-4:])
            except ValueError:
                year = 2024

            event_obj, e_created = Event.objects.get_or_create(
                slug=route_slug,
                defaults={
                    'name': raw_route_name,
                    'event_type': Event.EventType.SR600,
                    'year': year,
                    'start_date': f"{year}-01-01",
                    'distance_km': 600,
                    'location': raw_route_name,
                    'country': route_country,
                    'organizing_club': None,
                    'parent_series': None
                }
            )
            if e_created:
                eventos_creados += 1

            # 3. Gestion relacional del Resultado (Result)
            raw_time = row[mapeo_columnas['time']].strip() if 'time' in mapeo_columnas else None
            duration = None
            if raw_time:
                time_match = re.match(r"(\d+)h(\d+)", raw_time)
                if time_match:
                    hrs = int(time_match.group(1))
                    mins = int(time_match.group(2))
                    duration = timedelta(hours=hrs, minutes=mins)

            modality = row[mapeo_columnas['modality']].strip().upper() if 'modality' in mapeo_columnas else 'RANDO'
            status = Result.Status.FINISHER
            if 'rando' not in modality.lower() and 'r' != modality.lower():
                # Si es version Turista, no tiene limite de tiempo obligatorio ni se guarda la duracion
                duration = None

            homol = row[mapeo_columnas['homologation_code']].strip() if 'homologation_code' in mapeo_columnas else None

            # Evitar colisiones de guardado si el resultado ya existia para la combinacion ciclista-evento
            result_obj, res_created = Result.objects.get_or_create(
                randonneur=randonneur_obj,
                event=event_obj,
                defaults={
                    'status': status,
                    'time': duration,
                    'homologation_code': homol if homol else None
                }
            )
            if res_created:
                resultados_creados += 1

        # Cierre del descriptor de archivo si no es una URL
        if not "docs.google.com/spreadsheets" in source:
            csv_file.close()

        self.stdout.write(self.style.SUCCESS(
            f"Ingesta masiva finalizada de forma satisfactoria:\n"
            f" - {eventos_creados} nuevas rutas SR600 registradas.\n"
            f" - {randonneurs_creados} nuevos perfiles de ciclistas creados.\n"
            f" - {resultados_creados} nuevos resultados individuales cargados."
        ))

        # 4. POST-INGESTION PIPELINE: Saneamiento y recalculo automatizado
        self.stdout.write("Ejecutando pipeline de deduplicacion de datos...")
        management.call_command('deduplicate_randonneurs')

        self.stdout.write("Recalculando medallas de retos 10x/20x/30x en tiempo real...")
        recalculados_count = 0
        for r_afectado in randonneurs_afectados:
            # Forzamos al modelo a recalcular y guardar fisicamente sus medallas en base a sus nuevos resultados
            r_afectado.sincronizar_logros()
            recalculados_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pipeline completado con exito. {recalculados_count} ciclistas actualizados relacionalmente."
        ))

