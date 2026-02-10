from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Randonneur, Club

class Command(BaseCommand):
    help = 'Crea datos de prueba para Randonneurs (Ciclistas)'

    def handle(self, *args, **kwargs):
        self.stdout.write(" Creando Randonneurs de prueba...")

        # 1. LIMPIEZA (Opcional)
        Randonneur.objects.all().delete()
        # Nota: No borramos los Users para no cargarnos al superusuario que usas para entrar al admin.

        # 2. RECUPERAR CLUBES EXISTENTES por CODIGO ACP oficial, no por nombre
        try:
            #busco el C. C. RIAZOR (10) por su código ACP real
            cc_riazor = Club.objects.get(acp_club_code='ES111258')
            #tb el de randoneurs andalucia
            randonneurs_andalucia = Club.objects.get(acp_club_code='ES111793')
        except Club.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"Error: No encuentro los clubes de la base de datos {e}"))
            return

        # 3. CREAR UN USUARIO REAL (Para probar el Login)
        # creo un par de users para loguear como si fuera este ciclista. PRUEBAS
        user_pepe, created = User.objects.get_or_create(
            username='pepe_randonneur',
            defaults={'email': 'pepe@ejemplo.com'}
        )
        if created:
            user_pepe.set_password('rando123') # Contraseña para las pruebas
            user_pepe.save()
            self.stdout.write(f" - Usuario de sistema creado: {user_pepe.username}")

        #creo otro usuario logeado no ciclista ni tenga pruebas realizadas
        #este no va a list randonneurs_data
        user_new, created = User.objects.get_or_create(
            username='aficionado_uno',
            defaults={'email': 'afi:ejemplo.es'}
        )
        if created:
            user_new.set_password('afione')
            user_new.save()
            self.stdout.write(f"- Usuario raso creado: {user_new.username}")


        # 4. CREAR RANDONNEURS
        randonneurs_data = [
            {
                'first_name': 'Pepe',
                'last_name': 'Rodríguez',
                'country': 'ES',
                'club': cc_riazor,
                'user': user_pepe,      # ESTE ESTÁ RECLAMADO (Tiene usuario)
                'is_claimed': True,
                'privacy': Randonneur.PrivacyLevel.COMMUNITY
            },
            {
                'first_name': 'Laura',
                'last_name': 'García',
                'country': 'ES',
                'club': cc_riazor,
                'user': None,           # ESTE NO TIENE USUARIO (Perfil fantasma/histórico)
                'is_claimed': False,
                'privacy': Randonneur.PrivacyLevel.PUBLIC
            },
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'country': 'GB',        # Un extranjero
                'club': randonneurs_andalucia,
                'user': None,
                'is_claimed': False,
                'privacy': Randonneur.PrivacyLevel.PUBLIC
            }
        ]

        for data in randonneurs_data:
            Randonneur.objects.create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                country=data['country'],
                club=data['club'],
                user=data['user'],
                is_claimed=data['is_claimed'],
                privacy_level=data['privacy']
            )

        self.stdout.write(self.style.SUCCESS(f" ¡Éxito! Se han creado {len(randonneurs_data)} randonneurs."))



#importo randoneurs en terminal con: python manage.py import_randonneurs
#sale verde confirma que las tablas de usuarios, perfiles de ciclistas y clubes reales
#ahora se comunican perfectamente bajo el ORM de Django