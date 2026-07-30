#descargua el documento oficial del reto 10x SR Challenge de internet,
# lo procese en memoria, cree los ciclistas y les otorgue sus distinciones de forma 100% automatizada.

# core/management/commands/import_sr_challenge_sheet.py

import csv
import io
import requests
import unicodedata
from django.core.management.base import BaseCommand
from core.models import Randonneur, Achievement
from django.core import management # Permite llamar comands por codigo interno (auto) en def handle

def normalizar_texto(texto):
    """
    Elimina tildes, convierte a mayusculas y limpia espacios en blanco.
    """
    if not texto:
        return ""
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_limpio = "".join([c for c in texto_normalizado if not unicodedata.combining(c)])
    return texto_limpio.strip().upper()

class Command(BaseCommand):
    help = "Descarga y procesa la lista oficial del reto 10x SR de Google Sheets"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando la conexion con la base de datos de Super Randonnees...")

        # URL del documento oficial de retos 10x (modificada para exportar a CSV de forma nativa)
        sheet_url = "https://docs.google.com/spreadsheets/d/1JTZl32y9J8AsgX8ndJ_Dm0NumtZqKOjoD5z4XV7ftwI/export?format=csv"

        try:
            response = requests.get(sheet_url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Error al descargar la hoja de calculo: {e}"))
            return

        # El sistema decodifica el contenido descargado en memoria
        csv_data = io.StringIO(response.text)
        reader = csv.reader(csv_data)

        # Se saltan las primeras lineas de cabecera de la hoja oficial si las tiene
        # En la hoja oficial del reto, la fila 1 contiene los titulos
        header = next(reader)

        randonneurs_vinculados = 0
        logros_registrados = 0

        for row in reader:
            # Validamos que la fila contenga datos suficientes (Nombre, Apellidos, Pais, Ano de consecucion)
            # Nota: La estructura oficial suele tener: [Nombre, Apellidos, Pais, Homologacion, Ano...]
            if len(row) < 4:
                continue

            first_name = normalizar_texto(row[0])
            last_name = normalizar_texto(row[1])
            country_code = row[2].strip().upper()
            year_str = row[3].strip()

            if not first_name or not last_name:
                continue

            # Validamos el ano de finalizacion
            try:
                year = int(year_str[:4])
            except ValueError:
                year = 2024  # Ano por defecto si el dato es corrupto

            # El sistema intenta buscar un ciclista ya registrado en la base de datos por su nombre
            # Esto evita duplicar perfiles que ya existan por brevets de LRM
            randonneur_obj = Randonneur.objects.filter(
                first_name=first_name,
                last_name=last_name
            ).first()

            # Si el ciclista no existe, se crea su perfil historico nuevo
            if not randonneur_obj:
                # El sistema mapea el pais de origen de forma segura (limitado a 2 caracteres)
                clean_country = country_code if len(country_code) == 2 else "ES"
                randonneur_obj = Randonneur.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    country=clean_country,
                    is_claimed=False,
                    user=None
                )
                randonneurs_vinculados += 1

            # Se registra de forma relacional la medalla de 10x SR Challenge en el ano correspondiente
            achievement_obj, created = Achievement.objects.get_or_create(
                randonneur=randonneur_obj,
                year=year,
                kind=Achievement.Type.SR10
            )

            if created:
                logros_registrados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Proceso de ingesta de retos finalizado con exito:\n"
            f" - {randonneurs_vinculados} nuevos ciclistas internacionales indexados.\n"
            f" - {logros_registrados} distinciones oficiales '10x SR Challenge' registradas."
        ))

        # El sistema ejecuta la deduplicacion automatica tras finalizar la ingesta
        self.stdout.write("Iniciando depuracion automatica de duplicados...")
        management.call_command('deduplicate_randonneurs')