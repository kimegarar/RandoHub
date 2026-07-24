#con django ModelForms (Formularios vinculados a modelos),
# automatizan la validación y el guardado de datos, para editar privacidad del ciclista y añadir rrss

from django import forms
from core.models import Randonneur

#Formulario dinámico vinculado al modelo Randonneur.
#Permite al usuario editar su privacidad y enlaces de forma segura.
class RandonneurProfileForm(forms.ModelForm):

    class Meta:
        model = Randonneur
        #se definen los campos que el usuario tiene permitido editar
        fields = ['privacy_level', 'strava_link', 'instagram_link', 'other_link']

        # etiquetas legibles para la interfaz de usuario
        labels = {
            'privacy_level': 'Nivel de Privacidad del Perfil',
            'strava_link': 'Enlace a tu perfil de Strava (opcional)',
            'instagram_link': 'Enlace a tu Instagram (opcional)',
            'other_link': 'Enlace a tu web o blog personal (opcional)',
        }