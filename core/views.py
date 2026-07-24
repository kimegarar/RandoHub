#aqui la logica web, recibe peticiones user, busca datos de models, y se muestra
# (en flask lo de abajo de @app.route(/'inicio')

from django.contrib.auth.forms import UserCreationForm  #formulario de registro nativo y seguro de Django
from django.contrib.auth import login  #para loguear al usuario automáticamente tras registrarse
from django.shortcuts import redirect  #para redirigir de página

from django.shortcuts import render, get_object_or_404
from core.models import Club, Randonneur, Event

from django.contrib.auth.decorators import login_required  # proteger la vista
from django.db.models import Q  #para hacer búsquedas avanzadas OR (nombre o apellido)
from core.forms import RandonneurProfileForm  #import del formulario privacidad rrss


#la def DEBE recibir el objeto 'request' (quién es, qué navegador usa, qué pide...)
#nota: esta def Recibe el paquete de información (request) cuando alguien llama a la puerta.
#Procesa, pasa los datos y Responde cn render y entrega el request para k Django sepa a quién enviar el HTML resultante

def home(request): #request es variable local con info de las peticiones de user al visitar web
    # consulta a la Base de Datos (Query)
    #count() del ORM de Django, rápido y eficiente
    ##my_clubs = Club.objects.all() #de TODOS los objetos Club
    total_clubs = Club.objects.count()
    total_randonneurs = Randonneur.objects.count()

    #todos los eventos ordenados por fecha
    events = Event.objects.all()
    #y randonneurs
    randonneurs = Randonneur.objects.all()

    # Agrupo toda la información en un dict (contexto) para la plantilla

    context = {
        'total_clubs': total_clubs,
        'total_randonneurs': total_randonneurs,
        'events': events,
        'randonneurs': randonneurs, #se envian lista de cilcistas
    }

    # Envia el contexto al archivo HTML
    return render(request, 'home.html', context)
    #render pide 3 la petición, el nombre del html, y opcional datos)


def event_list(request): #Vista pública para gestionar y mostrar el calendario de eventos.
    #Captura los parámetros de búsqueda opcionales del navegador (GET) y filtra la base de datos.
    # Traemos todos los events de la bbdd

    #1. Consulta base: todos los eventos
    events_query = Event.objects.all()   #!!! OJO VARIABLE events o all_events

    #2. Capturamos los filtros que el usuario ha seleccionado en los desplegables de la web
    query_type = request.GET.get('type') #tipo de prueba
    query_distance = request.GET.get('distance') #de distnacia
    query_year = request.GET.get('year') #fecha OJO no seria mejor MES y AÑO???

    #filtros dinámicos al vuelo en el servidor si existen
    if query_type:
        events_query = events_query.filter(event_type=query_type)

    if query_distance:
        events_query = events_query.filter(distance_km=query_distance)

    if query_year:
        events_query = events_query.filter(year=query_year)

    #Ejecutamos la consulta filtrada final
    filtered_events = events_query

    #Agrupamos el contexto y enviamos los "selected_..." para que el formulario
    # mantenga seleccionada la opción seleccionada después de que la página se refresque.
    context = {
        'events': filtered_events,
        'selected_type': query_type,
        'selected_distance': query_distance,
        'selected_year': query_year,
    }



    return render(request, 'event_list.html', context)



def randonneur_detail(request, pk):
    """
    Vista dinámica para mostrar el perfil deportivo de un ciclista específico.
    Usa el parámetro 'pk' (Primary Key / ID) de la URL.
    """
    #se busca al ciclista por su ID, si no existe, Django da un error 404
    randonneur = get_object_or_404(Randonneur, pk=pk) #util d django get_object_or_404

    # Calculamos de forma dinámica si este ciclista en concreto es Super Randonneur 2024
    es_sr = randonneur.es_super_randonneur(2024)

    context = {
        'randonneur': randonneur,
        'es_sr_2024': es_sr,
    }
    return render(request, 'randonneur_detail.html', context)


def club_detail(request, pk):
    """
    def dinámica para mostrar la ficha de un club específico.
    cuenta el total de miembros de un club respetando el estricto cumplimiento del RGPD.
    """
    club = get_object_or_404(Club, pk=pk)

    #SOLUCIÓN RGPD: Contamos los miembros con .count() de forma agregada,
    # SIN exponer nombres o perfiles individuales de forma pública sin consentimiento explícito.
    total_miembros = club.randonneur_set.count()

    context = {
        'club': club,
        'total_miembros': total_miembros,
    }
    return render(request, 'club_detail.html', context)


def club_country_list(request):
    """
    Pantalla 1: Muestra un listado muy limpio de los países que tienen
    clubes registrados en el sistema (de momento, España).
    """
    # Obtenemos los códigos únicos de países que tienen clubes activos en el sistema
    #se duplicaban, con order_by() vacío antes de .distinct() elimina el ordenamiento por defecto del modelo (por nombre de club) en la consulta SQL
    paises_codigos = Club.objects.filter(active=True).values_list('country', flat=True).order_by().distinct()

    # Creamos una lista con el nombre legible y el código de cada país
    countries = []
    for codigo in paises_codigos:
        # Django-countries nos traduce el código a su nombre legible (ej: 'ES' -> 'Spain')
        # Para forzar la traducción a Español en tu TFM, podemos mapearlo o usar la traducción de Django.
        nombre_pais = "España" if codigo == 'ES' else codigo
        countries.append({
            'code': codigo.lower(),  # Guardamos en minúsculas para las URLs
            'name': nombre_pais
        })

    #Apunta al archivo real de tu carpeta de plantillas 'club_list.html'
    return render(request, 'club_list.html', {'countries': countries})


def club_region_list(request, country_code):
    """
    Pantalla 2: Muestra el directorio exclusivo de un país.
    Permite filtrar los clubes dinámicamente por Región (Comunidad Autónoma) mediante un desplegable.
    """
    # Convertimos el código de la URL a mayúsculas (ej: 'es' -> 'ES') para buscar en la base de datos
    country_upper = country_code.upper()

    # Traemos los clubes de ese país específico
    clubs = Club.objects.filter(country=country_upper, active=True).order_by('region', 'name')

    # Obtenemos la lista "sucia" con duplicados desde la base de dato
    regiones_brutas = Club.objects.filter(
        country=country_upper,
        active=True
    ).exclude(region__isnull=True).values_list('region', flat=True)

    regiones_unicas = set(regiones_brutas)

    # Traducimos las regiones a sus nombres legibles para el desplegable
    # (Leemos el diccionario RegionChoices que creamos en tu models.py)
    regiones_traducidas = []
    for r_code in regiones_unicas:
        # Buscamos la etiqueta legible en tu enumeración de modelos
        etiqueta = Club.RegionChoices(r_code).label if r_code in Club.RegionChoices.values else r_code
        regiones_traducidas.append({'code': r_code, 'name': etiqueta})


    regiones_traducidas.sort(key=lambda x: x['name']) #lista regiones ordenada alfabéticamente por nombre traducido

    # Capturamos si el usuario ha seleccionado alguna región en el buscador (GET)
    selected_region = request.GET.get('region')
    if selected_region:
        clubs = clubs.filter(region=selected_region)

    context = {
        'clubs': clubs,
        'country_code': country_code,
        'country_name': "España" if country_upper == 'ES' else country_upper,
        'regiones': regiones_traducidas,
        'selected_region': selected_region,
    }

    #Apunta a 'club_region_list.html' y pasamos el contexto correcto
    return render(request, 'club_region_list.html', context)


def signup(request):
#gestionar el registro de nuevos usuarios en la plataforma
    # Si el usuario ya está logueado, lo mandamos a la home
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Si el usuario envía el formulario con sus datos
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Guardamos el nuevo usuario de forma encriptada y segura en la base de datos
            user = form.save()
            # Lo logueamos automáticamente
            login(request, user)
            # Redirigimos a la portada de momento
            return redirect('home')
    else:
        # Si entra por primera vez, le mostramos el formulario vacío
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form})


@login_required
def claim_profile(request):
    """
    Pantalla de búsqueda de perfiles históricos disponibles para reclamar.
    Filtra mostrando solo perfiles de la base de datos que no hayan sido reclamados todavía.
    """
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        # Buscamos coincidencias en nombre o apellido, pero SOLO perfiles no reclamados aún (is_claimed=False)
        results = Randonneur.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query),
            is_claimed=False
        )

    return render(request, 'claim_profile.html', {'results': results, 'query': query})


@login_required
def confirm_claim(request, pk):
    """
    Acción que ejecuta el enlace relacional entre el usuario logueado (User)
    y el perfil histórico seleccionado (Randonneur), realizando el "PUM" relacional.
    """
    # Buscamos el perfil que se quiere reclamar. Debe estar libre (is_claimed=False)
    randonneur = get_object_or_404(Randonneur, pk=pk, is_claimed=False)

    # Realizamos la conexión relacional
    randonneur.user = request.user
    randonneur.is_claimed = True
    randonneur.save()

    # Redirigimos al usuario directamente a su nueva ficha de perfil dinámico
    return redirect('randonneur_detail', pk=randonneur.pk)


@login_required
def edit_profile(request, pk):
    """
    Vista segura para editar los detalles de privacidad y enlaces del perfil.
    Solo permite el acceso si el perfil pertenece al usuario logueado.
    """
    # BLINDAJE DE SEGURIDAD: Busca el perfil por su ID, pero obligatoriamente
    # debe estar enlazado relacionalmente al usuario que hace la petición (user=request.user)
    randonneur = get_object_or_404(Randonneur, pk=pk, user=request.user)

    if request.method == 'POST':
        # Pasamos los datos enviados por el usuario al formulario y lo vinculamos a su perfil existente
        form = RandonneurProfileForm(request.POST, instance=randonneur)
        if form.is_valid():
            form.save() # Guardamos los cambios en la base de datos
            return redirect('randonneur_detail', pk=randonneur.pk) #redirije a su perfil ya actualizado
    else:
        # Si entra por primera vez, cargamos el formulario relleno con sus datos actuales
        form = RandonneurProfileForm(instance=randonneur)

    return render(request, 'edit_profile.html', {'form': form, 'randonneur': randonneur})