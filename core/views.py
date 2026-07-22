#aqui la logica web, recibe peticiones user, busca datos de models, y se muestra
# (en flask lo de abajo de @app.route(/'inicio')

from django.shortcuts import render, get_object_or_404
from core.models import Club, Randonneur, Event

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