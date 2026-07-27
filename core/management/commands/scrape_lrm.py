"""
MODULO DE INGESTA DE DATOS (PROCESO ETL) - RANDONNEUR.ME SCRAPER
================================================================

HISTORIAL DE DESARROLLO Y RECTIFICACIONES (CONTROL DE CAMBIOS TFM):
------------------------------------------------------------------
- Intento 1 (BeautifulSoup / HTML Scraping): Intento inicial de procesar el
  HTML estatico de la pagina principal. Fallo debido a que la pagina es una
  Single Page Application (SPA) desarrollada en AngularJS. El servidor envia un
  esqueleto de plantilla con variables vacias tipo '{{:: result.year }}', lo que
  provocaba un error de tipo 'ValueError' al intentar procesar los datos.

- Intento 2 (API Directa / results.json): Intento de descargar el archivo JSON
  directo del servidor. Fallo con un error HTTP 404 debido a que el servidor de la
  plataforma aloja sus datos estaticamente en la carpeta '/data/' en formato .js.

- Intento 3 (results.js / Regex): Descarga del archivo results.js y extraccion
  mediante expresiones regulares del array de datos. Fallo debido a que el archivo
  de resultados solo contiene claves de relacion relacionales (eid, uid), sin
  nombres de ciclistas ni de eventos.

- Intento 4 (Fusion Relacional Integrada en Memoria): Se diseña una solucion ETL
  robusta. Descarga de forma unificada tres archivos independientes de datos
  (results.js, events.js y users.js). Se procesan y limpian las estructuras de
  JavaScript a formato JSON en la memoria del servidor de desarrollo. Se cruzan
  las entidades dinamicamente usando diccionarios de busqueda rapida y se insertan
  de forma relacional en la base de datos local SQLite aplicando get_or_create.
"""

import re
import json
import unicodedata  # Para normalizar tildes y asegurar comparaciones de texto
from datetime import timedelta
import requests
from django.core.management.base import BaseCommand
from core.models import Randonneur, Event, Result

def limpiar_js_a_json(texto_js):
    """
    Funcion de utilidad para extraer la estructura JSON limpia de un archivo JS.
    Busca el primer caracter de apertura ([ o {) y el ultimo de cierre (] o })
    para aislar el contenido util de forma portable.
    """
    indices_apertura = [texto_js.find('['), texto_js.find('{')]
    start_idx = min([i for i in indices_apertura if i != -1], default=-1)

    indices_cierre = [texto_js.rfind(']'), texto_js.rfind('}')]
    end_idx = max([i for i in indices_cierre if i != -1], default=-1)

    if start_idx == -1 or end_idx == -1:
        return None

    return texto_js[start_idx:end_idx + 1]


def normalizar_texto(texto):
    """
    Elimina tildes, convierte a mayusculas y limpia espacios en blanco
    para permitir comparaciones seguras de nombres en la base de datos.
    """
    if not texto:
        return ""
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_limpio = "".join([c for c in texto_normalizado if not unicodedata.combining(c)])
    return texto_limpio.strip().upper()


class Command(BaseCommand):
    help = 'Descarga y unifica las bases de datos relacionales de randonneur.me para poblar el sistema.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando el cargador relacional LRM de internet...")

        url_results = "https://www.randonneur.me/data/results.js"
        url_events = "https://www.randonneur.me/data/events.js"
        url_users = "https://www.randonneur.me/data/users.js"

        try:
            self.stdout.write(" - Descargando tablas de resultados, eventos y usuarios...")
            res_results = requests.get(url_results, timeout=15)
            res_events = requests.get(url_events, timeout=15)
            res_users = requests.get(url_users, timeout=15)

            res_results.raise_for_status()
            res_events.raise_for_status()
            res_users.raise_for_status()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Error de conexion al servidor de datos: {e}"))
            return

        json_results = limpiar_js_a_json(res_results.text)
        json_events = limpiar_js_a_json(res_events.text)
        json_users = limpiar_js_a_json(res_users.text)

        if not json_results or not json_events or not json_users:
            self.stdout.write(self.style.ERROR("Error: Fallo al extraer las estructuras de datos relacionales."))
            return

        try:
            results_data = json.loads(json_results)
            events_data = json.loads(json_events)
            users_data = json.loads(json_users)
        except ValueError as json_err:
            self.stdout.write(self.style.ERROR(f"Error: Fallo al convertir los datos a formato JSON. {json_err}"))
            return

        self.stdout.write(self.style.SUCCESS(f" - Tablas descargadas. Total resultados: {len(results_data)}"))

        # Se construye el indice de eventos en memoria
        eventos_index = {}
        if isinstance(events_data, list):
            for item in events_data:
                event_id = item.get('id') or item.get('eid')
                if event_id:
                    eventos_index[event_id] = item
        else:
            eventos_index = events_data

        # Se construye el indice de usuarios en memoria
        usuarios_index = {}
        if isinstance(users_data, list):
            for item in users_data:
                user_id = item.get('id') or item.get('uid')
                if user_id:
                    usuarios_index[user_id] = item
        else:
            usuarios_index = users_data

        # Se procesa la totalidad del archivo de resultados de internet sin limitador
        pruebas_a_procesar = results_data

        eventos_creados = 0
        randonneurs_creados = 0
        resultados_creados = 0

        for r_item in pruebas_a_procesar:
            # Se recuperan las claves de relacion de la tabla de resultados
            eid = r_item.get('eid')
            uid = r_item.get('uid')
            raw_time = r_item.get('time')
            cert = str(r_item.get('cert', ''))

            # Se buscan las entidades correspondientes en las tablas de memoria usando las claves reales
            event_data = eventos_index.get(eid) or eventos_index.get(str(eid))
            user_data = usuarios_index.get(uid) or usuarios_index.get(str(uid))

            # Se descarta el registro si no se encuentran sus datos correspondientes en las tablas maestras
            if not event_data or not user_data or not raw_time:
                continue

            # Se extrae la informacion del evento usando las claves reales descubiertas (name, dist, date, cid)
            raw_event_name = event_data.get('name')
            raw_distance = event_data.get('dist')
            raw_date = event_data.get('date')
            event_country = event_data.get('cid', 'FR').strip()

            # Se extrae la informacion del ciclista aplicando la normalizacion de tildes
            # Esto evita duplicados relacionales si un nombre viene con tildes en una fuente y sin ellas en otra
            nombre = normalizar_texto(user_data.get('fname', ''))
            apellidos = normalizar_texto(user_data.get('lname', ''))
            raw_sex = user_data.get('sex', '').strip().upper()
            r_country = user_data.get('country', 'ES').strip()

            # Si el pais viene en formato largo de texto, se usa el codigo ISO del evento por compatibilidad
            if len(r_country) > 2:
                r_country = event_country

            if not raw_event_name or not raw_distance or not nombre or not apellidos:
                continue

            # Se realiza el parseo de la fecha para extraer el ano de forma segura
            start_date_str = raw_date.split('T')[0] if raw_date else None
            try:
                distance = int(raw_distance)
                year = int(start_date_str[:4]) if start_date_str else 1989
            except ValueError:
                continue

            # Se parsea el tiempo "74h29" a timedelta
            time_match = re.match(r"(\d+)h(\d+)", raw_time.strip())
            duration = None
            if time_match:
                hrs = int(time_match.group(1))
                mins = int(time_match.group(2))
                duration = timedelta(hours=hrs, minutes=mins)

            # Se crea o recupera el evento de la serie madre de forma relacional sin duplicados
            series_slug = f"{raw_event_name.lower().replace(' ', '-')}-series"
            series_obj, _ = Event.objects.get_or_create(
                slug=series_slug,
                defaults={
                    'name': raw_event_name,
                    'event_type': Event.EventType.LRM,
                    'year': year,  # Se asigna el primer ano detectado como referencia
                    'start_date': start_date_str if start_date_str else f"{year}-01-01",
                    'distance_km': distance,
                    'location': raw_event_name,
                    'country': event_country,
                    'organizing_club': None,
                    'parent_series': None  # Es la serie madre, no tiene padre
                }
            )

            # 🛠️ SECCIÓN DE CORRECCIÓN: Se evita duplicar el ano si este ya consta en el nombre original de la prueba
            nombre_edicion_final = raw_event_name
            if not raw_event_name.endswith(str(year)):
                nombre_edicion_final = f"{raw_event_name} {year}"

            # Se crea o recupera la edicion concreta conectandola relacionalmente a la serie madre
            event_slug = f"{raw_event_name.lower().replace(' ', '-')}-{year}"
            event_obj, event_new = Event.objects.get_or_create(
                slug=event_slug,
                defaults={
                    'name': nombre_edicion_final,  # 👈 ACTUALIZADO CON EL NOMBRE LIMPIO SIN AÑO DUPLICADO
                    'event_type': Event.EventType.LRM,
                    'year': year,
                    'start_date': start_date_str if start_date_str else f"{year}-01-01",
                    'distance_km': distance,
                    'location': raw_event_name,
                    'country': event_country,
                    'organizing_club': None,
                    'parent_series': series_obj  # Enlazado dinamicamente a la serie madre
                }
            )
            if event_new:
                eventos_creados += 1

            # Se crea o recupera el ciclista de forma relacional, mapeando el campo gender
            randonneur_obj, r_new = Randonneur.objects.get_or_create(
                first_name=nombre,
                last_name=apellidos,
                defaults={
                    'country' : r_country,
                    'club': None,
                    'gender': raw_sex if raw_sex in ['M', 'F', 'O'] else None,
                    'is_claimed': False,
                    'user': None
                }
            )
            if r_new:
                randonneurs_creados += 1

            # Se crea o recupera el resultado de participacion asociado a la edicion de la prueba
            result_obj, res_new = Result.objects.get_or_create(
                randonneur=randonneur_obj,
                event=event_obj,
                defaults={
                    'status': Result.Status.FINISHER,
                    'time': duration,
                    'homologation_code': cert if cert else None
                }
            )
            if res_new:
                resultados_creados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Sincronizacion completada con exito:\n"
            f" - {eventos_creados} nuevas Ediciones LRM indexadas.\n"
            f" - {randonneurs_creados} nuevos Randonneurs Internacionales importados.\n"
            f" - {resultados_creados} nuevos Resultados de participacion asociados."
        ))

        #python manage.py scrape_lrm