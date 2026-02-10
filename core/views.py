#aqui la logica web, recibe peticiones user, busca datos de models, y se muestra
# (en flask lo de abajo de @app.route(/'inicio')

from django.shortcuts import render
from core.models import Club #se importa el modelo de club apra usarlo

#la def DEBE recibir el objeto 'request' (quién es, qué navegador usa, qué pide...)
#nota: esta def Recibe el paquete de información (request) cuando alguien llama a la puerta.
#Procesa, pasa los datos y Responde cn render y entrega el request para k Django sepa a quién enviar el HTML resultante
def home(request): #request es variable local con info de las peticiones de user al visitar web
    # consulta a la Base de Datos (Query)
    my_clubs = Club.objects.all() #de TODOS los objetos Club

    return render(request, 'home.html', {'clubs': my_clubs})
    #render pide 3 la petición, el nombre del html, y opcional datos)
