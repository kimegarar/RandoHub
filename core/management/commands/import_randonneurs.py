import csv
import os  # Sistema operativo, necesario para gestionar rutas de archivos de forma portable
import unicodedata  # Para normalizar tildes y asegurar comparaciones de texto
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings  # Encontrar la raíz del proyecto, configuración global para usar settings.BASE_DIR
from core.models import Randonneur, Club


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
    # Str que aparecerá al ejecutar: python manage.py help import_randonneurs
    help = (
        'Importa ciclistas reales de prueba desde un archivo CSV, crea ciclistas de control para pruebas de lógica'
        'asociándolos dinámicamente a sus clubes.'
    )

    # Antes: 'Crea datos de prueba para Randonneurs (Ciclistas)'

    def handle(self, *args, **kwargs):  # Método ppal que Django ejecuta cuando llamas al comando desde la consola
        self.stdout.write('Creando Randonneurs reales de España de prueba...')

        # LIMPIEZA (Opcional) evita duplicados, sin acumular registros repetidos
        Randonneur.objects.all().delete()
        self.stdout.write(" - Datos antiguos de randonneurs eliminados correctamente.")
        # Nota: No borramos los Users para no cargarnos al superusuario que uso para entrar al admin.

        # PASO A: INGESTA INGESTA Y DEPURACIÓN AUTO DEL CSV REAL
        # DEFINE RUTA DEL CSV DE PARTICIPANTES
        # Calcula la ruta absoluta del archivo CSV en el disco duro del Mac
        # ARCHIVO REAL EXTRAÍDO DEL PDF con el parse_pdf.py
        csv_path = os.path.join(settings.BASE_DIR, 'randonneurs_reales_esp25.csv')

        # Control de seguridad: si borra el archivo por error, el programa no se cae; te avisa
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"Error: No se encuentra el archivo CSV en: {csv_path}"))
            return

        self.stdout.write(" - Leyendo archivo CSV e importando participantes reales...")

        # Abrimos el archivo con UTF-8 para que tildes y 'Ñ' no den problemas
        randonneurs_csv = 0
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:  # Depurado de textos fila a fila
                raw_apellidos = row['cognoms'].strip()
                raw_nombre = row['nom'].strip()
                acp_code = row['acp_code'].strip()
                club_name = row['club_name'].strip()

                # 🛠️ APLICAMOS LA NORMALIZACIÓN DE TEXTO UNICODE
                apellidos = normalizar_texto(raw_apellidos)
                nombre = normalizar_texto(raw_nombre)

                # ASOCIAR EL CLUB DE FORMA INTELIGENTE (Antes de crear al ciclista)
                club_to_assign = None

                # Código 'ES111199' representa oficialmente a ciclistas sin club (Independientes)
                # FILTRO: Si contiene la palabra 'independiente' o es el código ES111199, va por libre
                if 'independiente' in club_name.lower() or acp_code == 'ES111199':
                    club_to_assign = None
                else:
                    # En vez de usar .get(), usamos .filter().first() para evitar caídas del sistema
                    club_to_assign = Club.objects.filter(acp_club_code=acp_code).first()

                    if not club_to_assign:  # Si el club no existe en la base de datos de 202 clubes, avisa
                        self.stdout.write(self.style.WARNING(
                            f"Advertencia: El club '{club_name}' ({acp_code}) no existe. Se asigna Independiente."
                        ))

                # EVITAR DUPLICADOS EN LA IMPORTACIÓN:
                # get_or_create busca si ya existe el ciclista por su nombre y apellidos normalizados.
                # Se quita el campo country de la busqueda para evitar duplicar ciclistas que corran en el extranjero.
                randonneur_obj, created = Randonneur.objects.get_or_create(
                    first_name=nombre,
                    last_name=apellidos,
                    defaults={
                        'country': 'ES',
                        'club': club_to_assign,
                        'is_claimed': False,
                        'user': None
                    }
                )

                # Solo sumamos al contador de importados si realmente era un registro nuevo (created=True)
                if created:
                    randonneurs_csv += 1

        self.stdout.write(self.style.SUCCESS(f" - ✅ {randonneurs_csv} ciclistas reales importados desde el CSV."))

        # ==========================================
        # PASO B: CREAR CICLISTAS DE CONTROL (Pepe, Laura y John)
        # ==========================================
        # Son indispensables porque sobre ellos hemos cargado los eventos e historiales de prueba
        self.stdout.write(" - Creando ciclistas de control para pruebas de algoritmos...")

        # Recuperamos los clubes para Pepe, Laura y John usando los códigos reales
        cc_riazor = Club.objects.filter(acp_club_code='ES111258').first()
        randonneurs_andalucia = Club.objects.filter(acp_club_code='ES111793').first()

        # Creamos los usuarios del sistema para probar el Login y Claim de perfiles
        user_pepe, _ = User.objects.get_or_create(
            username='pepe_randonneur',
            defaults={'email': 'pepe@ejemplo.com'}
        )
        user_pepe.set_password('rando123')
        user_pepe.save()

        user_new, _ = User.objects.get_or_create(
            username='aficionado_uno',
            defaults={'email': 'afi@ejemplo.es'}
        )
        user_new.set_password('afione')
        user_new.save()

        # Datos estructurados para Pepe, Laura y John (Simula diferentes escenarios de privacidad)
        randonneurs_control = [
            {
                'first_name': 'Pepe',
                'last_name': 'Rodríguez',
                'country': 'ES',
                'club': cc_riazor,
                'user': user_pepe,  # Reclamado
                'is_claimed': True,
                'privacy': Randonneur.PrivacyLevel.COMMUNITY  # Solo visible para usuarios registrados
            },
            {
                'first_name': 'Laura',
                'last_name': 'García',
                'country': 'ES',
                'club': cc_riazor,
                'user': None,  # No reclamado (Fantasma/histórico)
                'is_claimed': False,
                'privacy': Randonneur.PrivacyLevel.PUBLIC
            },
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'country': 'GB',  # Extranjero
                'club': randonneurs_andalucia,
                'user': None,
                'is_claimed': False,
                'privacy': Randonneur.PrivacyLevel.PUBLIC
            }
        ]

        # Guardamos en la base de datos relacional los ciclistas de control aplicando la normalizacion de tildes
        for data in randonneurs_control:
            Randonneur.objects.create(
                first_name=normalizar_texto(data['first_name']),
                last_name=normalizar_texto(data['last_name']),
                country=data['country'],
                club=data['club'],
                user=data['user'],
                is_claimed=data['is_claimed'],
                privacy_level=data['privacy']
            )

        self.stdout.write(self.style.SUCCESS(
            f" - ✅ {len(randonneurs_control)} ciclistas de control creados correctamente."
        ))
        self.stdout.write(self.style.SUCCESS("¡Éxito total en la ingesta de Randonneurs!"))







#importo randoneurs en terminal con: python manage.py import_randonneurs
#sale verde confirma que las tablas de usuarios, perfiles de ciclistas y clubes reales
#ahora se comunican perfectamente bajo el ORM de Django