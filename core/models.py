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
            elif self.distance_km == 1400:
                return timedelta(hours=110, minutes=0)
            elif self.distance_km == 1500:  # x ej: London-Edinburgh-London
                return timedelta(hours=125, minutes=0)
            elif self.distance_km == 2000: #OJO al andalus son 200h no 180
                return timedelta(hours=200, minutes=0)
            else: #velo. media mínima de 12 km/h para distancias de mas de 1200
                horas_calculadas = int(self.distance_km / 12)
                return timedelta(hours=horas_calculadas)#tolera si se crea otra prueba con otra distancia

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