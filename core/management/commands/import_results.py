#"tabla pivote" (relación Muchos a Muchos): relaciona un Randonneur con un Event,
#guardando el tiempo total, si finalizó (FIN) o abandonó (DNF) y su código de homologación.

from datetime import timedelta
from django.core.management.base import BaseCommand
from core.models import Randonneur, Event, Result

class Command(BaseCommand):
    help = 'Crea resultados de prueba para conectar Randonneurs con Eventos.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Creando Resultados de prueba...")

        # 1. LIMPIEZA
        Result.objects.all().delete()
        self.stdout.write(" - Datos antiguos de resultados eliminados correctamente.")

        # 2. RECUPERAR CICLISTAS Y EVENTOS EXISTENTES
        try:
            # Recuperamos los ciclistas
            pepe = Randonneur.objects.get(first_name='Pepe', last_name='Rodríguez')
            laura = Randonneur.objects.get(first_name='Laura', last_name='García')
            john = Randonneur.objects.get(first_name='John', last_name='Smith')

            # Recuperamos los eventos
            brevet_200 = Event.objects.get(slug='brevet-200-coruna-2024')
            brevet_300 = Event.objects.get(slug='brm-300-madrid-2024')
            flecha = Event.objects.get(slug='flecha-iberica-2024')

        except (Randonneur.DoesNotExist, Event.DoesNotExist) as e:
            self.stdout.write(self.style.ERROR(f"Error: No encuentro los ciclistas o eventos requeridos. {e}"))
            return

        # 3. DEFINICIÓN DE RESULTADOS DE PRUEBA
        # Usamos timedelta para definir la duración (horas y minutos)
        results_data = [
            {
                'randonneur': pepe,
                'event': brevet_200,
                'status': Result.Status.FINISHER,
                'time': timedelta(hours=8, minutes=45),  # Pepe tardó 8h 45m
                'homologation': '123456'
            },
            {
                'randonneur': pepe,
                'event': brevet_300,
                'status': Result.Status.FINISHER,
                'time': timedelta(hours=14, minutes=15),  # Pepe tardó 14h 15m
                'homologation': '123457'
            },
            {
                'randonneur': laura,
                'event': brevet_200,
                'status': Result.Status.FINISHER,
                'time': timedelta(hours=9, minutes=10),  # Laura tardó 9h 10m
                'homologation': '123458'
            },
            {
                'randonneur': laura,
                'event': brevet_300,                    'status': Result.Status.DNF,  # Laura no pudo terminar el 300
                'time': None,
                'homologation': None
            },
            {
                'randonneur': john,
                'event': flecha,
                'status': Result.Status.FINISHER,
                'time': timedelta(hours=22, minutes=0),  # John terminó la Flecha en 22h
                'homologation': 'F00001'
            }
        ]

        # 4. CREACIÓN EN BUCLE
        count = 0
        for data in results_data:
            Result.objects.create(
                randonneur=data['randonneur'],
                event=data['event'],
                status=data['status'],
                time=data['time'],
                homologation_code=data['homologation']
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"¡Éxito! Creados {count} resultados conectados a ciclistas y eventos."))