"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.contrib import admin
from django.urls import path
from core import views #para poder usar las views que hay en core, da permiso a urls para acceder a core

urlpatterns = [
    path("admin/", admin.site.urls), #es la conecxion

#se define ruta de la portada
    # '' "cuando no escriban nada despues del dominio"
    # views.home: "usa la función home del archivo views"
    # name='home': "nombre d esta ruta 'home' para referirse a ella luego"

    path('', views.home, name='home'), #ruta de portada
    path('events/', views.event_list, name='event_list'), #los events o pruebas
    path('randonneurs/<int:pk>/', views.randonneur_detail, name='randonneur_detail'),#RUTA DINÁMICA
    path('clubs/<int:pk>/', views.club_detail, name='club_detail'), # RUTA DINÁMICA DE CLUB
    path('clubs/', views.club_country_list, name='club_list'),  # Selector de Países
    path('clubs/<str:country_code>/', views.club_region_list, name='club_region_list'), #Filtro por Región
    path('signup/', views.signup, name='signup'),  # RUTA DE REGISTRO
    path('claim/', views.claim_profile, name='claim_profile'),  # buscador de reclamos de perfil
    path('claim/confirm/<int:pk>/', views.confirm_claim, name='confirm_claim'), #la acción de reclamar
    path('randonneurs/<int:pk>/edit/', views.edit_profile, name='edit_profile'),#ruta de edición de perfil
    path('randonneurs/', views.randonneur_list, name='randonneur_list'), # RUTA DIRECTORIO DE CICLISTAS
]

