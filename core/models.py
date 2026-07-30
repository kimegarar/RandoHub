from django.db import models
from datetime import timedelta  #para poder manejar tiempos limites de los events
from django.contrib.auth.models import User
from django_countries.fields import CountryField
from django.utils.translation import gettext_lazy as _


# 1. UTILIDADES (Mixins)
# class abstracta, los modelos heredan de aqui ganan automáticamente los campos de auditoría
#para cumplir a rajatabla el principio DRY (Don't Repeat Yourself)
# y saber cuando se genero y actualizo; created y updated se añaden directametne a toda clase que herede de esta
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        abstract = True


# 2. MODELOS BASE
# representa a la organizacion que sea. Necesario para agrupar clubes
class Organization(TimeStampedModel):
    class OrgType(models.TextChoices):
        ACP = 'ACP', 'Audax Club Parisien'
        LRM = 'LRM', 'Les Randonneurs Mondiaux'
        NATIONAL = 'NAT', _('National Federation-representative')

    name = models.CharField(max_length=200, verbose_name=_("Name"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("Code"))  # x ejem: ACP
    org_type = models.CharField(max_length=10, choices=OrgType.choices, default=OrgType.NATIONAL)
    country = CountryField(blank=True, null=True, verbose_name=_("Country"))
    website = models.URLField(blank=True, verbose_name=_("Website"))

    def __str__(self):
        return f"{self.code} - {self.name}"

    def __repr__(self):
        return f"<Organization: {self.code}>"


# Clubs, 1:N (Uno a Muchos): Una Organización tiene muchos clubes.
class Club(TimeStampedModel):

    #DICt DE TRADUCCIÓN CC.AA.
    #OJO esto habra que hacerlo de cada pais?!??!?!?
    class RegionChoices(models.TextChoices): #TextChoices de Django
        ANDALUCIA = 'an', 'Andalucía'
        ARAGON = 'ar', 'Aragón'
        ASTURIAS = 'as', 'Asturias'
        BALEARES = 'ba', 'Islas Baleares'
        CANARIAS = 'cn', 'Canarias'
        CANTABRIA = 'cb', 'Cantabria'
        CASTILLA_LEON = 'cl', 'Castilla y León'
        CASTILLA_MANCHA = 'cm', 'Castilla-La Mancha'
        CATALUNA = 'ca', 'Cataluña'
        VALENCIA = 'vl', 'Comunidad Valenciana'
        EXTREMADURA = 'ex', 'Extremadura'
        GALICIA = 'ga', 'Galicia'
        MADRID = 'ma', 'Madrid'
        MURCIA = 'mu', 'Región de Murcia'
        NAVARRA = 'na', 'Navarra'
        PAIS_VASCO = 'va', 'País Vasco'
        LA_RIOJA = 'lo', 'La Rioja'


    name = models.CharField(max_length=100, verbose_name=_("Club Name"))

    # Sin unique=True global, pq puede haber 'CC Riazor' en dos países distintos (raro, pero posible)
    # Vinculamos a la Organización (ej: este club pertenece a la federación española)
    # 1:N
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clubs',
        verbose_name=_("Affiliated Organization")
    )
    location = models.CharField(max_length=150, verbose_name=_("Location")) #ciudad-poblacion
    #en plantilla HTML de ficha del club (club_detail.html),
    #con la etiqueta especial d Django {{ club.get_region_display }}, Django leerá el código 'ga'
    region = models.CharField(
        max_length=100,
        choices=RegionChoices.choices,  # aqui vincula las opciones ga > galicia, ...
        blank=True,
        null=True,
        verbose_name=_("Region")
    )
    country = CountryField(verbose_name=_("Country")) #pais

    # MODIFICACIÓN: Añadido campo solicitado para saber si organiza pruebas
    is_organizer = models.BooleanField(default=False, verbose_name=_("Is Organizer?"))

    acp_club_code = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name=_("ACP Code"))
    website = models.URLField(blank=True)
    active = models.BooleanField(default=True, verbose_name=_("Is Active?"))

    class Meta:
        ordering = ['name']
        verbose_name = _("Club")
        verbose_name_plural = _("Clubs")

    def __str__(self):
        return f"{self.name} ({self.country})"

    def __repr__(self):
        return f"<Club id={self.id}: {self.name}>"


# EL CICLISTA (Randonneur), con la lógica de PRIVACIDAD (tipo Dotwatcher)
class Randonneur(TimeStampedModel):
    class PrivacyLevel(models.TextChoices):
        PUBLIC = 'PUB', _('Public')
        COMMUNITY = 'COM', _('Community Only')  # visible solo para users logueados
        PRIVATE = 'PRI', _('Private')  # solo para el dueño

    # datos publicos (Históricos)
    first_name = models.CharField(max_length=100, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=100, verbose_name=_("Last Name"))
    country = CountryField(verbose_name=_("Country"))

    # MODIFICACIÓN: Opciones de género para análisis estadísticos
    class GenderChoices(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')
        OTHER = 'O', _('Other')

    gender = models.CharField(
        max_length=1,
        choices=GenderChoices.choices,
        blank=True,
        null=True,
        verbose_name=_("Gender")
    )

    # datos de gestión (Privacidad y Login), is_claimed y privacy_level claves en GDPR/Privacidad
    # relación 1:1 con el sistema de usuarios de Django
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='randonneur_profile'
    )
    is_claimed = models.BooleanField(default=False, help_text=_("Has the real user claimed this profile?"))
    privacy_level = models.CharField(max_length=3, choices=PrivacyLevel.choices, default=PrivacyLevel.PUBLIC)

    # RELACIÓN 1:N -> Un Randonneur pertenece a 1 Club principal (o a ninguno: independiente)
    # Si se borra el Club, el ciclista pasa a ser independiente (con SET_NULL)
    club = models.ForeignKey(
        Club,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Current Club")
    )

    # redes-links opcionales
    strava_link = models.URLField(blank=True)
    instagram_link = models.URLField(blank=True)
    other_link = models.URLField(blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        # Índice para buscar x nombre (clave para el buscador público)
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
        ]
        verbose_name = _("Randonneur")

    def __str__(self):
        status = "✅" if self.is_claimed else "👤"
        return f"{status} {self.first_name} {self.last_name} [{self.country}]"

    def __repr__(self):
        return f"<Randonneur id={self.id}: {self.first_name} {self.last_name}>"


    def es_super_randonneur(self, ano):
        """
        Algoritmo inteligente para detectar si el ciclista ha completado
        la serie completa (200, 300, 400 y 600 km) en un año específico.
        """
        # 1. Buscamos todos sus resultados exitosos en ese año
        resultados_exitosos = self.results.filter(
            event__year=ano,
            status='FIN'  # Usamos el código de tu enum de Status (Finisher)
        )

        # 2. Extraemos las distancias únicas completadas (usando un conjunto/set para evitar duplicados)
        distancias_completadas = set()
        for r in resultados_exitosos:
            distancias_completadas.add(r.event.distance_km)

        # 3. Comprobamos si tiene al menos una de cada distancia requerida para el título
        serie_requerida = {200, 300, 400, 600}

        # El operador issubset comprueba si todas las distancias de la serie están en su historial
        return serie_requerida.issubset(distancias_completadas)

    def es_elegible_challenge_lepertel(self):
        """
        para determinar si el ciclista califica para el Challenge Lepertel.
        Comprueba si se han finalizado pruebas de 1200 km o mas dsd el ano 2019 inclusive,
        durante cuatro anos naturales consecutivos, en al menos dos paises distintos.
        """
        # Se obtienen todos los resultados exitosos en pruebas de 1200 km o mas dsd el ano 2019
        # ordenados cronologicamente por la fecha de salida del evento
        resultados_ultra = self.results.filter(
            status='FIN',
            event__distance_km__gte=1200,
            event__year__gte=2019  # Constriccion de año: dsd 2019 inclusive
        ).order_by('event__start_date')

        if not resultados_ultra.exists():
            return False

        # Se asocia cada ano con el conjunto de paises de sus eventos de ultra distancia
        paises_por_ano = {}
        for r in resultados_ultra:
            ano = r.event.year
            pais = str(r.event.country)
            if ano not in paises_por_ano:
                paises_por_ano[ano] = set()
            paises_por_ano[ano].add(pais)

        # Se obtienen los anos unicos ordenados
        anos_ordenados = sorted(paises_por_ano.keys())

        # Se busca si existe al menos una secuencia de 4 anos consecutivos dsd 2019
        for i in range(len(anos_ordenados) - 3):
            secuencia = anos_ordenados[i:i + 4]

            # Se comprueba si la secuencia es estrictamente consecutiva (ej: 2021, 2022, 2023, 2024)
            es_consecutiva = (
                    secuencia[1] == secuencia[0] + 1 and
                    secuencia[2] == secuencia[1] + 1 and
                    secuencia[3] == secuencia[2] + 1
            )

            if es_consecutiva:
                # Se unifican los paises de participacion de estos 4 anos especificos
                paises_secuencia = set()
                for ano in secuencia:
                    paises_secuencia.update(paises_por_ano[ano])

                # Si hay participacion en al menos dos naciones distintas, califica
                if len(paises_secuencia) >= 2:
                    return True

        return False

    @property
    def safe_unicode_flag(self):
        """
        Retorna el emoji de la bandera de forma segura.
        Evita caidas del sistema si el codigo de pais esta vacio o es invalido.
        """
        # Se comprueba si el pais tiene un codigo de exactamente dos letras
        if self.country and hasattr(self.country, 'code') and len(self.country.code) == 2:
            try:
                # Se intenta retornar el emoji de la bandera de la libreria
                return self.country.unicode_flag
            except (IndexError, ValueError):
                # Si la libreria falla por un codigo corrupto, se retorna vacio de forma segura
                return ""
        return ""


    def sincronizar_logros(self):
        """
        Analiza los resultados del ciclista de forma automatica, calcula sus
        reconocimientos y los guarda fisicamente en la tabla de Achievement
        evitando duplicidades en la base de datos.
        """
        # 1. Sincronizacion de Super Randonneur (SR) por cada ano
        # Se analizan los ultimos anos para verificar si califica
        for ano in range(2018, 2027):
            if self.es_super_randonneur(ano):
                # Se importa el modelo aqui dentro para evitar problemas de importacion circular
                from core.models import Achievement
                Achievement.objects.get_or_create(
                    randonneur=self,
                    year=ano,
                    kind=Achievement.Type.SR
                )

        # 2. Sincronizacion de Challenge Lepertel
        # Si califica para el Challenge Lepertel, se registra el logro en el ultimo ano
        # de participacion ultra del ciclista
        if self.es_elegible_challenge_lepertel():
            from core.models import Achievement
            ultimo_resultado = self.results.filter(
                status='FIN',
                event__distance_km__gte=1200,
                event__year__gte=2019
            ).order_by('-event__start_date').first()

            if ultimo_resultado:
                Achievement.objects.get_or_create(
                    randonneur=self,
                    year=ultimo_resultado.event.year,
                    kind=Achievement.Type.LEPERTEL
                )
        #DETECTOR DE RETOS DE SUPER RANDONNÉES (10x, 20x, 30x)
        resultados_sr = self.results.filter(
            event__event_type=Event.EventType.SR600,
            status=Result.Status.FINISHER
        )

        # Se extraen los slugs unicos de las rutas para validar que sean diferentes
        rutas_distintas = set(resultados_sr.values_list('event__slug', flat=True))
        total_rutas = len(rutas_distintas)

        if total_rutas >= 10:
            from core.models import Achievement
            # Se registra el reconocimiento en el año de la ultima SR finalizada
            ultimo_sr = resultados_sr.order_by('-event__start_date').first()
            ano_logro = ultimo_sr.event.year if ultimo_sr else 2024

            # El sistema comprueba cuantos retos le corresponden de manera acumulativa
            Achievement.objects.get_or_create(
                randonneur=self,
                year=ano_logro,
                kind=Achievement.Type.SR10
            )
            if total_rutas >= 20:
                Achievement.objects.get_or_create(
                    randonneur=self,
                    year=ano_logro,
                    kind=Achievement.Type.SR20
                )
            if total_rutas >= 30:
                Achievement.objects.get_or_create(
                    randonneur=self,
                    year=ano_logro,
                    kind=Achievement.Type.SR30
                )


    def obtener_logros_agrupados(self):
        """
        Recupera los reconocimientos de la base de datos y los agrupa
        en formato de texto limpio: 'Tipo (Cantidad: Ano1, Ano2...)'.
        """
        logros = self.achievements.all().order_by('kind', 'year')
        agrupados = {}

        # Se agrupan los anos por cada tipo de logro
        for logro in logros:
            tipo_legible = logro.get_kind_display()
            if tipo_legible not in agrupados:
                agrupados[tipo_legible] = []
            agrupados[tipo_legible].append(str(logro.year))

        # Se formatea el resultado final para la plantilla HTML
        resultado_formateado = {}
        for tipo, anos in agrupados.items():
            resultado_formateado[tipo] = f"({len(anos)}: {', '.join(anos)})"

        return resultado_formateado


    def calcular_progreso_super_randonneur(self, ano):
        """
        Calcula de forma dinamica que distancias de la serie obligatoria
        de Super Randonneur (200, 300, 400, 600) ha completado el ciclista
        en el ano provisto, indicando cuales le faltan y el porcentaje de progreso.
        """
        # El sistema busca las distancias unicas completadas con exito en el ano de referencia
        # Se utiliza 'FIN' de forma directa para evitar conflictos de orden de definicion de clases
        completadas = set(self.results.filter(
            event__year=ano,
            status='FIN'
        ).values_list('event__distance_km', flat=True))

        serie_obligatoria = {200, 300, 400, 600}

        # Interseccion de conjuntos para obtener las completadas que forman parte de la serie
        completadas_serie = serie_obligatoria.intersection(completadas)

        # Diferencia de conjuntos para saber cuales faltan por completar
        faltantes_serie = serie_obligatoria - completadas_serie

        # Calculo de porcentaje de progreso (sobre 4 pruebas obligatorias)
        porcentaje = int((len(completadas_serie) / 4) * 100)

        return {
            'completadas': sorted(list(completadas_serie)),
            'faltantes': sorted(list(faltantes_serie)),
            'porcentaje': porcentaje,
            'completado_total': porcentaje == 100
        }

        # core/models.py -> dentro de la clase Randonneur

    def obtener_sr600_completadas_agrupadas(self):
        """
        Recupera todos los resultados de tipo SR600 finalizados por el ciclista
        y los agrupa por ruta permanente, devolviendo el total de veces completadas
        y la lista de anos en formato legible: 'Ruta (Pais) - Cantidad (Anos)'.
        """
        # El sistema filtra los resultados exitosos de tipo SR600 ordenados cronologicamente
        resultados_sr = self.results.filter(
            event__event_type='SR600',
            status='FIN'
        ).order_by('event__start_date')

        agrupados = {}
        for r in resultados_sr:
            # Se utiliza el nombre del evento y su pais como clave de agrupacion
            nombre_ruta = r.event.name
            pais = str(r.event.country)
            clave = f"{nombre_ruta} ({pais})"

            if clave not in agrupados:
                agrupados[clave] = []
            agrupados[clave].append(str(r.event.year))

        # Se formatea el diccionario resultante para renderizarlo directamente en la plantilla
        resultado_formateado = {}
        for clave, anos in agrupados.items():
            resultado_formateado[clave] = f" - {len(anos)} ({', '.join(anos)})"

        return resultado_formateado




# 4. EVENTOS/PRUEBAS DEPORTIVAS
class Event(TimeStampedModel):
    class EventType(models.TextChoices):
        BRM = 'BRM', 'BRM (200-1000km)'
        BRM_S = 'BRM_S', _('BRM Special')
        LRM = 'LRM', 'LRM (+1200km)'
        PBP = 'PBP', 'Paris-Brest-Paris'
        SR600 = 'SR600', 'Super Randonnée (600km/10k)'
        FLECHE = 'FLECHE', _('Flèche')
        OTHER = 'OTHER', _('Other')

    name = models.CharField(max_length=200, verbose_name=_("Event Name"))
    #Slug: versión "limpia" de url con nombre www.randoatlas.com/eventos/brevet-200-coruna-2024
    #título de algo convertido a un formato para la barra navegador (tod minus, espacios -, )
    slug = models.SlugField(unique=True, help_text=_("URL friendly name, ej: madrid-gijon-2026"))
    event_type = models.CharField(max_length=10, choices=EventType.choices, default=EventType.BRM)
    # MODIFICACIÓN: Relación autorreferencial para unificar ediciones bajo una misma serie madre
    # Si es una edición (ej. LEL 1989), apunta al evento maestro (ej. London-Edinburgh-London)
    parent_series = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='editions',
        verbose_name=_("Parent Series"),
        help_text=_("Override standard limit if needed")
    )

    organizing_club = models.ForeignKey(
        Club,
        # CORRECCIÓN: on_delete=SET_NULL
        # Si club desaparece, el evento histórico PERMANECE, pero sin organizador enlazado
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organized_events',
        verbose_name=_("Organizer")
    )

    year = models.PositiveIntegerField(db_index=True, verbose_name=_("Year"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    distance_km = models.PositiveIntegerField(verbose_name=_("Distance (km)"))
    elevation_gain = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Elevation (m)"))

    location = models.CharField(max_length=150, verbose_name=_("Location"))
    country = CountryField(verbose_name=_("Country"))
    official_link = models.URLField(blank=True)

    #Campo opcional, sobrescribir límites estándar si es necesario, x las variaciones de eventos LRM
    #(Al-Andalus son 200h no 180h estándar), es sistema de sobrescritura dinámica a nivel de bbdd
    #mira si tiene el event tiempo límite personalizado, sino usa los tiempos estandar limite
    max_time_override = models.DurationField(
        null=True,
        blank=True,
        verbose_name=_("Custom Time Limit"),
        help_text=_("Override standard limit if needed (e.g. for LRM Al-Andalus 200h) (HH:MM)")) #:SS no necesarios

    class Meta:
        ordering = ['-start_date']
        verbose_name = _("Event")

    def __str__(self):
        return f"{self.name} ({self.year}) - {self.distance_km}km"

    def __repr__(self):
        return f"<Event id={self.id}: {self.slug}>"

    #metodo para detectar si un club esta asociado a un event lo marque como club organizador
    def save(self, *args, **kwargs):
        """
        se sobreescribe el guardado del evento para que, SI tiene un club organizador,
        este se marque automáticamente como 'is_organizer=True' en la base de datos.
        """
        # 1. se guarda el evento de forma normal
        super().save(*args, **kwargs)

        # 2. Si tiene club organizador y no estaba marcado como organizador, lo marca
        if self.organizing_club and not self.organizing_club.is_organizer:
            self.organizing_club.is_organizer = True
            self.organizing_club.save()  # Guardamos el cambio en el club


    def tiempo_maximo_permitido(self):
        """
        Calcula el tiempo límite oficial (ACP) para completar la prueba
        según el tipo de evento y su distancia.
        """
        if self.max_time_override: #1 Si se define tiempo personalizado, se usa
            return self.max_time_override

        #si no, aplica los límites estándar oficiales de la normativa
        if self.event_type == self.EventType.BRM:  #pruebas BRM
            if self.distance_km == 200:
                return timedelta(hours=13, minutes=30)
            elif self.distance_km == 300:
                return timedelta(hours=20, minutes=0)
            elif self.distance_km == 400:
                return timedelta(hours=27, minutes=0)
            elif self.distance_km == 600:
                return timedelta(hours=40, minutes=0)
            elif self.distance_km == 1000:
                return timedelta(hours=75, minutes=0)


        elif self.event_type == self.EventType.LRM:  # events LRM
            if self.distance_km == 1200:
                return timedelta(hours=90, minutes=0)
            elif self.distance_km == 1300:  # Ej: Alpi 4000 (1300km)
                return timedelta(hours=150, minutes=0)
            elif self.distance_km == 1400:
                return timedelta(hours=110, minutes=0)
            elif self.distance_km == 1450:  # Ej: Alpi 4000 (1450km)
                return timedelta(hours=160, minutes=0)
            elif self.distance_km == 1500:  # Ej: London-Edinburgh-London
                return timedelta(hours=125, minutes=0)
            elif self.distance_km == 1610:  # Ej: 1001 Miglia
                return timedelta(hours=134, minutes=0)
            elif self.distance_km == 2000:  # OJO: Al-Andalus son 200h no 180
                return timedelta(hours=200, minutes=0)
            else:  # Velo. media minima de 12 km/h para distancias de mas de 1200
                horas_calculadas = int(self.distance_km / 12)
                return timedelta(hours=horas_calculadas)

        #Super Randonnées Permanentes (600 km y +10.000m de desnivel)
        elif self.event_type == self.EventType.SR600:
            return timedelta(hours=60, minutes=0)  # Límite oficial fijo de 60h

        #flechas
        elif self.event_type == self.EventType.FLECHE:
            return timedelta(hours=24, minutes=0)

        return None  # Para otros eventos sin límite estricto




# 5. RESULTADOS, TABLA PIVOTE: Conecta Randonneur <-> Event. Aquí se guarda los tiempos y homologaciones
# N:N (Muchos a Muchos), ID del ciclista con el ID del evento. Un ciclista muchos eventos. Un evento muchos ciclistas.
class Result(TimeStampedModel):
    class Status(models.TextChoices):
        FINISHER = 'FIN', 'Finisher'
        DNF = 'DNF', 'Did Not Finish'
        DNS = 'DNS', 'Did Not Start'
        OT = 'OT', 'Over Time'

    # Si se borra el ciclista, se borra su resultado (CASCADE) -> Lógico
    randonneur = models.ForeignKey(Randonneur, on_delete=models.CASCADE, related_name='results')
    # Si se borra el evento (ej: creado por error), se borran los resultados (CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='results')

    status = models.CharField(max_length=5, choices=Status.choices, default=Status.FINISHER)
    time = models.DurationField(null=True, blank=True, help_text="Tiempo total (HH:MM)")
    homologation_code = models.CharField(max_length=50, blank=True, null=True, unique=True)

    class Meta:
        unique_together = ('randonneur', 'event')  # Un ciclista no puede tener 2 resultados en el mismo evento
        ordering = ['time']
        verbose_name = _("Result")

    def __str__(self):
        return f"{self.randonneur} @ {self.event}: {self.status}"

    def __repr__(self):
        return f"<Result: {self.randonneur.last_name} in {self.event.id}>"


    #Métdo save() personalizado para automatizar el estatus
    def save(self, *args, **kwargs): # Si el resultado viene marcado como DNF o DNS, no valida tiempos
        if self.status in [self.Status.DNF, self.Status.DNS]:
            self.time = None
            self.homologation_code = None
            # Si se ingresa un tiempo, el sistema decide el estatus
        elif self.time:
            limite = self.event.tiempo_maximo_permitido()
            if limite and self.time > limite:
                self.status = self.Status.OT  # Over Time (Fuera de tiempo)
                self.homologation_code = None  # No puede tener homologación
            else:
                self.status = self.Status.FINISHER  # Finisher dentro de tiempo

        #y se guarda definitivamente en la bbdd
        super().save(*args, **kwargs)

    def formatted_time(self): #formateo de tiempo al final de tu modelo Result
        """
        Formatea el objeto timedelta en un formato legible HH:MM,
        evitando que se muestre en dias y segundos (ej: '3 days, 2:29:00' pasa a '74:29').
        """
        if self.time:
            total_segundos = int(self.time.total_seconds())
            horas = total_segundos // 3600
            minutos = (total_segundos % 3600) // 60
            return f"{horas:02d}:{minutos:02d}"
        return ""



# ACHIEVEMENTS (RECONOCIMIENTOS) #hay mas por poner
class Achievement(TimeStampedModel):
    class Type(models.TextChoices):
        SR = 'SR', 'Super Randonneur'
        R5000 = 'R5000', 'Randonneur 5000'
        R10000 = 'R10000', 'Randonneur 10000'
        PBP = 'PBP', 'PBP Finisher'
        LEPERTEL = 'LEPERTEL', 'Challenge Lepertel (LRM)'
        #retos super randonees sr600
        SR10 = 'SR10', '10x Super Randonnee Challenge'
        SR20 = 'SR20', '20x Super Randonnee Challenge'
        SR30 = 'SR30', '30x Super Randonnee Challenge'


    randonneur = models.ForeignKey(Randonneur, on_delete=models.CASCADE, related_name='achievements')
    year = models.PositiveIntegerField(verbose_name=_("Year"))
    kind = models.CharField(max_length=10, choices=Type.choices, verbose_name=_("Type"))

    # opcional: Quién otorga el premio?
    issuing_org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        # CORRECCIÓN: Eliminado unique_together para permitir múltiples SR en un año
        ordering = ['-year']
        verbose_name = _("Achievement")

    def __str__(self):
        return f"{self.randonneur} - {self.get_kind_display()} ({self.year})"

    def __repr__(self):
        return f"<Achievement: {self.randonneur.id} {self.kind} {self.year}>"


#Para evitar que el registro de solicitudes se borre cuando eliminemos el perfil duplicado tras la fusión,
# configuraremos los campos master y duplicate con on_delete=models.SET_NULL (permitiendo valores nulos).
#y mantendrá el registro de auditoría histórico solicitudes, tb después de que el perfil duplicado haya dejado de existir.
class MergeRequest(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submitted_merge_requests',
        verbose_name=_("Requested by")
    )
    master = models.ForeignKey(
        Randonneur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merge_requests_as_master',
        verbose_name=_("Master Profile (Destination)")
    )
    duplicate = models.ForeignKey(
        Randonneur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merge_requests_as_duplicate',
        verbose_name=_("Duplicate Profile (To merge)")
    )
    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        verbose_name=_("Status")
    )

    class Meta:
        verbose_name = _("Merge Request")
        verbose_name_plural = _("Merge Requests")
        unique_together = ('master', 'duplicate')

    def __str__(self):
        # El sistema valida si los perfiles existen todavia antes de retornar la cadena
        master_name = f"ID {self.master.id}" if self.master else "Eliminado"
        dup_name = f"ID {self.duplicate.id}" if self.duplicate else "Eliminado"
        return f"Solicitud de {self.requested_by.username}: {dup_name} -> {master_name} ({self.get_status_display()})"