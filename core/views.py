#aqui la logica web, recibe peticiones user, busca datos de models, y se muestra
# (en flask lo de abajo de @app.route(/'inicio')

from django.shortcuts import render, get_object_or_404, redirect #para redirigir de págin
from django.contrib.auth.forms import UserCreationForm #formulario de registro nativo y seguro de Django
from django.contrib.auth import login #para loguear al usuario automáticamente tras registrarse
from django.contrib.auth.decorators import login_required #proteger vista
from django.db.models import Q, Value # Importación de valores estáticos

from django.db.models.functions import Concat # Importación de concatenación en busqueda
from core.models import Club, Randonneur, Event
from core.forms import RandonneurProfileForm ##import del formulario privacidad rrss

from django.contrib import messages
from core.models import MergeRequest # El sistema importa el nuevo modelo
from django.utils import timezone # El sistema importa la utilidad de tiempo de Django


#la def DEBE recibir el objeto 'request' (quién es, qué navegador usa, qué pide...)
#nota: esta def Recibe el paquete de información (request) cuando alguien llama a la puerta.
#Procesa, pasa los datos y Responde cn render y entrega el request para k Django sepa a quién enviar el HTML resultante

# la logica web recibe peticiones de usuario, busca datos en los modelos y los muestra

def home(request):
    """
    Vista para la pagina de inicio.
    Calcula estadisticas agregadas de clubes y randonneurs registrados.
    """
    total_clubs = Club.objects.count()
    total_randonneurs = Randonneur.objects.count()

    events = Event.objects.all()
    randonneurs = Randonneur.objects.all()

    context = {
        'total_clubs': total_clubs,
        'total_randonneurs': total_randonneurs,
        'events': events,
        'randonneurs': randonneurs,
    }
    return render(request, 'home.html', context)


def event_list(request):
    """
    Vista publica para gestionar y mostrar el calendario de eventos.
    Captura los parametros de busqueda opcionales del navegador y filtra dinamicamente la base de datos.
    """
    # 1. Consulta base de inicio: preparamos el plano filtrando solo las series principales
    events_query = Event.objects.filter(parent_series__isnull=True)

    # 2. Capturamos los filtros del formulario HTML (Añadido el filtro de pais)
    query_type = request.GET.get('type')
    query_distance = request.GET.get('distance')
    query_year = request.GET.get('year')
    query_country = request.GET.get('country')

    # 3. Modificamos el plano de la consulta dinámicamente según la selección del usuario
    if query_type:
        events_query = events_query.filter(event_type=query_type)
    if query_distance:
        events_query = events_query.filter(distance_km=query_distance)
    if query_year:
        events_query = events_query.filter(year=query_year)
    if query_country:
        events_query = events_query.filter(country=query_country.upper())

    # Obtenemos los paises unicos de las series principales para el desplegable del buscador
    paises_disponibles = Event.objects.filter(
        parent_series__isnull=True
    ).values_list('country', flat=True).order_by().distinct()

    paises_traducidos = []
    for p_code in paises_disponibles:
        nombre_pais = "España" if p_code == 'ES' else p_code
        paises_traducidos.append({'code': p_code, 'name': nombre_pais})

    context = {
        'events': events_query,
        'paises': paises_traducidos,
        'selected_type': query_type,
        'selected_distance': query_distance,
        'selected_year': query_year,
        'selected_country': query_country,
    }

    return render(request, 'event_list.html', context)


def randonneur_detail(request, pk):
    """
    Vista dinamica para mostrar el perfil deportivo de un ciclista especifico.
    Implementa motor de validacion GDPR para restringir acceso segun el nivel de privacidad.
    Sincroniza y calcula los reconocimientos reales en la base de datos antes de renderizar.
    """
    randonneur = get_object_or_404(Randonneur, pk=pk)

    # 1. EVALUACIÓN DE PRIVACIDAD: Nivel Privado
    if randonneur.privacy_level == Randonneur.PrivacyLevel.PRIVATE:
        if not request.user.is_authenticated or randonneur.user != request.user:
            return render(
                request,
                'profile_private.html',
                {'randonneur_name': f"{randonneur.first_name} {randonneur.last_name}"},
                status=403
            )

    # 2. EVALUACIÓN DE PRIVACIDAD: Nivel Comunidad
    elif randonneur.privacy_level == Randonneur.PrivacyLevel.COMMUNITY:
        if not request.user.is_authenticated:
            return render(
                request,
                'profile_restricted.html',
                {'randonneur_name': f"{randonneur.first_name} {randonneur.last_name}"},
                status=401
            )

    # 3. PROCESO DE NEGOCIO: Si supera el control de privacidad, se procesa la informacion
    # Sincronizacion de logros fisicos en la base de datos
    randonneur.sincronizar_logros()

    # Recuperacion de logros agrupados estructurados
    logros_agrupados = randonneur.obtener_logros_agrupados()

    # El sistema calcula el progreso del ciclista para el ano actual (fijado en 2024 para las pruebas)
    progreso_sr = randonneur.calcular_progreso_super_randonneur(2024)
    # El sistema recupera las SR600 completadas y agrupadas
    sr600_agrupadas = randonneur.obtener_sr600_completadas_agrupadas()

    context = {
        'randonneur': randonneur,
        'logros_agrupados': logros_agrupados,
        'progreso_sr': progreso_sr,
        'sr600_agrupadas': sr600_agrupadas,  # Enviamos las SR600 agrupadas a la plantilla
    }


    return render(request, 'randonneur_detail.html', context)




def club_detail(request, pk):
    """
    Vista dinamica para mostrar la ficha de un club especifico.
    Calcula el total de miembros de forma agregada para cumplir con el RGPD.
    """
    club = get_object_or_404(Club, pk=pk)
    total_miembros = club.randonneur_set.count()

    context = {
        'club': club,
        'total_miembros': total_miembros,
    }
    return render(request, 'club_detail.html', context)


def club_country_list(request):
    """
    Pantalla 1 del directorio de clubes: muestra la lista de paises con clubes activos.
    """
    paises_codigos = Club.objects.filter(active=True).values_list('country', flat=True).order_by().distinct()

    countries = []
    for codigo in paises_codigos:
        nombre_pais = "España" if codigo == 'ES' else codigo
        countries.append({
            'code': codigo.lower(),
            'name': nombre_pais
        })

    return render(request, 'club_list.html', {'countries': countries})


def club_region_list(request, country_code):
    """
    Pantalla 2 del directorio de clubes: muestra los clubes de un pais agrupados por region.
    """
    country_upper = country_code.upper()
    clubs = Club.objects.filter(country=country_upper, active=True).order_by('region', 'name')

    regiones_brutas = Club.objects.filter(
        country=country_upper,
        active=True
    ).exclude(region__isnull=True).values_list('region', flat=True)

    regiones_unicas = set(regiones_brutas)

    regiones_traducidas = []
    for r_code in regiones_unicas:
        etiqueta = Club.RegionChoices(r_code).label if r_code in Club.RegionChoices.values else r_code
        regiones_traducidas.append({'code': r_code, 'name': etiqueta})

    regiones_traducidas.sort(key=lambda x: x['name'])

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
    return render(request, 'club_region_list.html', context)


def signup(request):
    """
    Gestiona el registro de nuevos usuarios en la plataforma de forma segura.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form})


@login_required
def claim_profile(request):
    """
    Pantalla de busqueda de perfiles historicos disponibles para reclamar.
    Filtra mostrando solo perfiles que no hayan sido reclamados todavia.
    """
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        results = Randonneur.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query),
            is_claimed=False
        )

    return render(request, 'claim_profile.html', {'results': results, 'query': query})


@login_required
def confirm_claim(request, pk):
    """
    Ejecuta el enlace relacional entre el usuario activo y el perfil historico seleccionado.
    """
    randonneur = get_object_or_404(Randonneur, pk=pk, is_claimed=False)
    randonneur.user = request.user
    randonneur.is_claimed = True
    randonneur.save()
    return redirect('randonneur_detail', pk=randonneur.pk)


@login_required
def edit_profile(request, pk):
    """
    Vista segura para editar los detalles de privacidad y enlaces de redes sociales del perfil.
    """
    randonneur = get_object_or_404(Randonneur, pk=pk, user=request.user)

    if request.method == 'POST':
        form = RandonneurProfileForm(request.POST, instance=randonneur)
        if form.is_valid():
            form.save()
            return redirect('randonneur_detail', pk=randonneur.pk)
    else:
        form = RandonneurProfileForm(instance=randonneur)

    return render(request, 'edit_profile.html', {'form': form, 'randonneur': randonneur})


def randonneur_list(request):
    """
    Muestra el directorio general de ciclistas registrados de forma publica.
    Excluye estrictamente los perfiles privados y permite buscar por nombre completo.
    """
    randonneurs_query = Randonneur.objects.exclude(privacy_level=Randonneur.PrivacyLevel.PRIVATE)

    query_name = request.GET.get('name', '').strip()
    query_country = request.GET.get('country', '').strip()
    query_club = request.GET.get('club', '').strip()

    if query_name:
        # Se genera una anotacion con el nombre completo concatenado para permitir
        # busquedas tolerantes de nombre y apellido a la vez (ej: "Keith Benton")
        randonneurs_query = randonneurs_query.annotate(
            full_name_concat=Concat('first_name', Value(' '), 'last_name')
        ).filter(
            Q(full_name_concat__icontains=query_name) |
            Q(first_name__icontains=query_name) |
            Q(last_name__icontains=query_name)
        )

    if query_country:
        randonneurs_query = randonneurs_query.filter(country=query_country.upper())

    if query_club:
        randonneurs_query = randonneurs_query.filter(club__pk=query_club)

    clubes_disponibles = Club.objects.filter(active=True, randonneur__isnull=False).distinct()
    paises_disponibles = Randonneur.objects.exclude(privacy_level=Randonneur.PrivacyLevel.PRIVATE).values_list(
        'country', flat=True).order_by().distinct()

    paises_traducidos = []
    for p_code in paises_disponibles:
        nombre_pais = "España" if p_code == 'ES' else p_code
        paises_traducidos.append({'code': p_code, 'name': nombre_pais})

    context = {
        'randonneurs': randonneurs_query.order_by('last_name', 'first_name'),
        'paises': paises_traducidos,
        'clubes': clubes_disponibles,
        'selected_name': query_name,
        'selected_country': query_country,
        'selected_club': query_club,
    }
    return render(request, 'randonneur_list.html', context)


def event_detail(request, pk):
    """
    Vista dinamica para mostrar la ficha de un evento o serie.
    Si es una serie madre, muestra sus ediciones historicas asociadas.
    Si es una edicion concreta, recupera sus resultados y los ciclistas finisher.
    """
    event = get_object_or_404(Event, pk=pk)

    # Se obtienen los resultados asociados a esta edicion de forma relacional
    # Solo aplica si es una edicion concreta (tiene serie madre)
    results = event.results.all().order_by('time') if event.parent_series else []

    context = {
        'event': event,
        'results': results,
    }
    return render(request, 'event_detail.html', context)


@login_required
def request_profile_merge(request, pk):
    """
    Registra una solicitud de fusion enviada por un usuario autenticado.
    El perfil reclamado del usuario actua como master y el perfil con el ID provisto como duplicado.
    """
    # El sistema intenta recuperar el perfil duplicado que se desea absorber
    duplicate = get_object_or_404(Randonneur, pk=pk, is_claimed=False)

    # Se comprueba si el usuario activo tiene un perfil ya reclamado
    try:
        master = request.user.randonneur_profile
    # El sistema captura la excepcion nativa de Django para relaciones OneToOne inexistentes
    except Randonneur.DoesNotExist:
        messages.error(request, "Error: Debes tener un perfil reclamado previamente para solicitar fusiones.")
        return redirect('randonneur_detail', pk=pk)

    if not master:
        messages.error(request, "Error: No posees un perfil deportivo activo vinculado a tu cuenta.")
        return redirect('randonneur_detail', pk=pk)

    # Evitar solicitar la fusion de un perfil consigo mismo
    if master.pk == duplicate.pk:
        messages.error(request, "Error: No puedes solicitar fusionar un perfil consigo mismo.")
        return redirect('randonneur_detail', pk=pk)

    # El sistema registra o recupera la solicitud de fusion pendiente para evitar duplicados en la cola
    merge_request, created = MergeRequest.objects.get_or_create(
        master=master,
        duplicate=duplicate,
        defaults={'requested_by': request.user}
    )

    if created:
        messages.success(request, "Solicitud de fusion registrada correctamente. Un administrador la revisara.")
    else:
        messages.info(request, "Ya existe una solicitud de fusion en cola de revision para estos perfiles.")

    return redirect('randonneur_detail', pk=duplicate.pk)