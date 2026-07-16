from django.core.management.base import BaseCommand
from datetime import datetime
from core.models import Club, Event


class Command(BaseCommand):
    help = 'Crea datos de prueba para Eventos (pruebas rando)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Creando Eventos de prueba...")

        #1. limpieza
        Event.objects.all().delete()
        self.stdout.write(" - Datos antiguos eliminados correctamente.")

        #2. recuperar clubs, organizadores
        try:
            cc_riazor = Club.objects.get(acp_club_code='ES111258')
            cc_chamartin = Club.objects.get(acp_club_code='ES011194')

        except Club.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"Error: Faltan clubes oficiales en la base de datos. {e}"))
            return

        # 3. DATOS DE EVENTOS, inventados
        events_data = [
            {
                'name': 'Brevet 200 de A Coruña',
                'slug': 'brevet-200-coruna-2024',#Slug: versión "limpia" de url con nombre www.randoatlas.com/eventos/brevet-200-coruna-2024
                'type': Event.EventType.BRM,
                'club': cc_riazor,
                'year': 2024,
                'date': datetime(2024, 3, 23).date(),
                'distance': 200,
                'elevation': 2500,
                'location': 'A Coruña'
            },
            {
                'name': 'Brevet 300 de Madrid',
                'slug': 'brm-300-madrid-2024',
                'type': Event.EventType.BRM,
                'club': cc_chamartin,
                'year': 2024,
                'date': datetime(2024, 4, 20).date(),
                'distance': 300,
                'elevation': 3500,
                'location': 'Madrid'
            },
            {
                'name': 'Brevet 400 de Madrid',
                'slug': 'brm-400-madrid-2024',
                'type': Event.EventType.BRM,
                'club': cc_chamartin,
                'year': 2024,
                'date': datetime(2024, 5, 18).date(),
                'distance': 400,
                'elevation': 4500,
                'location': 'Madrid'
            },
            {
                'name': 'Brevet 600 de A Coruña',
                'slug': 'brm-600-coruna-2024',
                'type': Event.EventType.BRM,
                'club': cc_riazor,
                'year': 2024,
                'date': datetime(2024, 6, 15).date(),
                'distance': 600,
                'elevation': 6800,
                'location': 'A Coruña'
            },
            {
                'name': 'Flecha Ibérica',
                'slug': 'flecha-iberica-2024',
                'type': Event.EventType.FLECHE,
                'club': cc_riazor,
                'year': 2024,
                'date': datetime(2024, 3, 30).date(),
                'distance': 360,
                'elevation': None,
                'location': 'España'
            }
        ]

        #4: CREACIÓN EN BUCLE
        count = 0
        for data in events_data:
            Event.objects.create(
                name=data['name'],
                slug=data['slug'],
                event_type=data['type'],
                organizing_club=data['club'],
                year=data['year'],
                start_date=data['date'],
                distance_km=data['distance'],
                elevation_gain=data['elevation'],
                location=data['location'],
                country='ES'
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"¡Éxito! Se han creado {count} eventos de prueba conectados a clubes reales."))






#python manage.py import_clubs
