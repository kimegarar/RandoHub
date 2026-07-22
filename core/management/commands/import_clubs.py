import csv
import os #para que el programa se comunique directamente con el sistema operativo del ordenador (os.path rutas de archivos)
import re #Expresiones Regulares (RegEx), limpiar datos clubs, patrón: r'\s*\(\d+\)\s*$'... C. C. RIAZOR (10)
#\s* busca espacios en blanco, \( y \) busca parentesis, \d+ para nºs dentro de (), $ solo si al final del txt,
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Club, Organization


class Command(BaseCommand):
    #La cadena de ayuda aparecerá si se ejecuta: python manage.py help import_clubs
    #help = 'Genera datos de prueba (Seed Data) iniciales para Organizaciones y Clubes.'
    # ERA PARA TEST CON DATOS INVENTAODS DE CLUBS
    help = 'Importa la lista real de clubes de España desde el archivo CSV.'

    #Métdo principal que ejecuta Django al llamar al comando. Aquí esta toda la lógica del script.

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando la importación de clubes reales...")

        #PASO 1: LIMPIEZA DE DATOS ANTIGUOS
        # Antes de crear nada, se borra tdo x si acaso y recomenzar. y se puede ejecutar x veces
        #no se acumulan duplicados

        self.stdout.write(" - Limpiando base de datos antigua...")
        Club.objects.all().delete()  # Borra todos los clubes
        Organization.objects.all().delete()  # Borra todas las organizaciones
        # Nota: Al borrar una Organización, si tuvieras on_delete=CASCADE en el modelo,
        # se borrarían los clubes automáticamente. Pero es mejor ser explícito aquí.
        self.stdout.write(" - Datos antiguos eliminados correctamente.")


        #PASO 2: CREAR LA ORGANIZACIÓN "PADRE o matriz" ---la fr y esp
        #es el modelo de datos, un Club no puede existir en el aire;
        # debe pertenecer a una Organización Nacional.

        # Usamos 'get_or_create': Un métod potente de django.

        org_acp, created = Organization.objects.get_or_create(
            code='ACP',
            defaults={
                'name': 'Audax Club Parisien',
                'org_type': Organization.OrgType.ACP,
                'country': 'FR'
            }
        )
        if created:
            self.stdout.write(f" - ✅ Organización creada nueva: {org_acp}")
        else:
            self.stdout.write(f" - ℹ️ Usando organización existente: {org_acp}")

        # Intenta buscar una org (con code='ESP'). Si no existe, la crea con los 'defaults'.
        # Devuelve una tupla: (objeto_instancia, booleano_creado)
        org_es, created = Organization.objects.get_or_create(
            code='ESP',
            defaults={
                'name': 'RanCat',
                'org_type': Organization.OrgType.NATIONAL,  # Usamos el ENUM definido en models.py
                'country': 'ES'
            }
        )

        if created:
            self.stdout.write(f" - ✅ Organización creada nueva: {org_es}")
        else:
            self.stdout.write(f" - ℹ️ Usando organización existente: {org_es}")

        # --- PASO 3: APERTURA Y LECTURA DEL ARCHIVO CSV ---
        # calculamos la ruta del archivo 'clubs.csv' que está en la raíz de tu proyecto.
        csv_path = os.path.join(settings.BASE_DIR, 'clubs.csv')

        # Verificamos si el archivo realmente existe en la ruta para evitar errores inesperados
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"Error: No se encuentra el archivo CSV en: {csv_path}"))
            return

        self.stdout.write(" - Leyendo archivo CSV e importando registros...")


        # --- PASO 4: CREACIÓN DE REGISTROS EN BUCLE ---
        #Abrimos el archivo en modo lectura con codificación UTF-8 para evitar problemas con las tildes y la 'ñ'.

        clubs_creados = 0
        with open(csv_path, mode='r', encoding='utf-8') as file:
            # DictReader asocia automáticamente la primera fila (cabecera) como llaves de un dict

            reader = csv.DictReader(file)
            for row in reader: # Limpiamos los textos de posibles espacios innecesarios
                raw_club_name = row['name'].strip() #nombre del club tal cual esta en cvs
                #quita automáticamente cualquier paréntesis con números al final del nombre
                club_name = re.sub(r'\s*\([\d-]+\)\s*$', '', raw_club_name)
                club_location = row['location'].strip() if row['location'] else "Desconocida"
                club_acp_code = row['acp_code'].strip() if row['acp_code'] else None
                # Creamos cada club asociándolo a RanCat (org_es)
                Club.objects.create(
                    name=club_name,  #inserta el nombre ya limpio
                    location=club_location,
                    acp_club_code=club_acp_code,
                    is_organizer=False,  #OJO NO Todos clubes participan son organizadores
                    country='ES',  # Definimos España como su pais, OJO por cada pais se tendra que hacer esto??
                    organization=org_es  #OJO NO Todos dependen de la organización RanCat que creamos arriba
                )
                clubs_creados += 1

        self.stdout.write(self.style.SUCCESS(
            f"¡Éxito total! Se han generado {clubs_creados} clubes reales en la base de datos a partir del CSV."
        ))


#python manage.py import_clubs