from django.contrib import admin
from .models import Organization, Club, Randonneur, Event, Result, Achievement
# Importar los modelos desde el archivo models.py de la misma carpeta (.)

# Los registro para que aparezcan en el panel admin de la web
admin.site.register(Organization)
admin.site.register(Club)
admin.site.register(Randonneur)
admin.site.register(Event)
admin.site.register(Result)
admin.site.register(Achievement)