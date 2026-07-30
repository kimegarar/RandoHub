#motor de limpieza relacional
# "Resolución de Entidades (Entity Resolution) o Deduplicación de Datos (Data Deduplication)"
#Algoritmo de Coincidencia de Conjuntos de Fichas (Token Set Matching)
#Para automatizar la detección y fusión de miles de perfiles duplicados sin riesgo de romper
'''(RegEx): Elimina números al inicio (como "28 "), limpia el texto "NUEVO/"
y descarta iniciales sueltas de una sola letra (como la "P" al final).

Independencia del Orden (Tokenization): En lugar de comparar cadenas rígidas,
el algoritmo divide el nombre en un conjunto de palabras únicas (fichas) [1].
Así, el conjunto de "MANUEL BURGOS FLORES" es {"manuel", "burgos", "flores"}
y el de "BURGOS FLORES MANUEL" es {"burgos", "flores", "manuel"}. Al comparar conjuntos,
son exactamente iguales! Esto resuelve el orden invertido.

Criterio de Selección del Perfil Maestro (Sobreviviente):

    Si uno de los perfiles duplicados está reclamado (is_claimed=True), ese debe ser el maestro.

    Si ninguno está reclamado, el que tenga más resultados históricos asociados se convierte en el maestro.

    Si empatan, se conserva el que tenga el ID más antiguo.'''

# core/management/commands/deduplicate_randonneurs.py


import re
import unicodedata
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Randonneur


# core/management/commands/deduplicate_randonneurs.py

def sanear_corrupcion_encoding(texto):
    """
    Corrige artefactos comunes de decodificacion corrupta de tildes
    y eñes antes de realizar la comparacion de tokens.
    """
    # 1. Se eliminan los numeros iniciales (como el "65 ")
    texto = re.sub(r'^\d+\s+', '', texto)

    # 2. Se eliminan prefijos de control de carga
    texto = re.sub(r'^nuevo/\s*', '', texto)

    # 3. Se normaliza a minusculas para estandarizar
    texto = texto.lower()

    # 4. PRIMERO: Se elimina cualquier caracter que no sea estrictamente una letra a-z o espacio.
    # Esto garantiza que "la“pez", "la'pez", "lañpez" (con eñe corrupta) se conviertan de forma limpia en "lapez".
    texto = re.sub(r'[^a-z\s]', '', texto)

    # 5. SEGUNDO: Se corrigen las palabras limpias resultantes que sabemos que son erratas tipograficas
    reemplazos = {
        'lapez': 'lopez',
        'lape': 'lope',
        'gomez': 'gomez',
        'sancez': 'sanchez',
        'rodrigez': 'rodriguez',
    }

    for corrupto, corregido in reemplazos.items():
        texto = texto.replace(corrupto, corregido)

    return texto


def obtener_conjunto_tokens(first_name, last_name):
    """
    Normaliza, limpia y tokeniza el nombre completo en un conjunto
    de palabras unicas para obviar el orden de escritura y prefijos.
    """
    nombre_limpio = f"{first_name} {last_name}".strip()

    # Aplicacion del sanador de caracteres corruptos
    nombre_limpio = sanear_corrupcion_encoding(nombre_limpio)

    # Normalizacion de tildes restante
    nombre_limpio = unicodedata.normalize('NFD', nombre_limpio)
    nombre_limpio = "".join([c for c in nombre_limpio if not unicodedata.combining(c)])

    # Separacion en palabras (tokens)
    tokens = nombre_limpio.split()

    # Se descartan iniciales de una sola letra (ej: la "P" de Manuel P)
    tokens_filtrados = {t for t in tokens if len(t) > 1}

    return tokens_filtrados


class Command(BaseCommand):
    help = "Analiza la base de datos, agrupa ciclistas por similitud de tokens y los fusiona de forma automatica"

    def handle(self, *args, **options):
        self.stdout.write("Iniciando motor de Resolucion de Entidades en RandoHub...")

        # Se recuperan todos los randonneurs de la base de datos
        todos_randonneurs = list(Randonneur.objects.all())
        total_inicial = len(todos_randonneurs)

        # Estructura en memoria para agrupar por coincidencia de conjuntos de palabras
        agrupaciones = {}

        for r in todos_randonneurs:
            tokens = obtener_conjunto_tokens(r.first_name, r.last_name)

            # PROTECCIÓN: Si el registro tiene solo 1 palabra (ej: "AGUDO") o ninguna,
            # se descarta de la fusion automatica para evitar falsos positivos
            if not tokens or len(tokens) < 2:
                continue

            # Se crea una clave unica combinando el conjunto congelado de tokens y el codigo de pais
            clave = (frozenset(tokens), str(r.country).upper())

            if clave not in agrupaciones:
                agrupaciones[clave] = []
            agrupaciones[clave].append(r)

        # Filtrar agrupaciones que tengan mas de un registro (duplicados reales)
        duplicados_detectados = {k: v for k, v in agrupaciones.items() if len(v) > 1}

        self.stdout.write(f"Se han detectado {len(duplicados_detectados)} grupos de ciclistas con nombres duplicados.")

        fusiones_realizadas = 0

        # Procesar cada grupo de duplicados bajo una transaccion de base de datos segura
        for clave, lista_duplicados in duplicados_detectados.items():
            with transaction.atomic():
                # Determinar el perfil maestro segun los criterios de prioridad
                # Prioridad: reclamado > mas resultados > ID mas antiguo (evitando fusiones dudosas)
                lista_ordenada = sorted(
                    lista_duplicados,
                    key=lambda x: (x.is_claimed, x.results.count(), -x.id),
                    reverse=True
                )

                master = lista_ordenada[0]
                secundarios = lista_ordenada[1:]

                # Se fusiona cada duplicado secundario en el perfil maestro
                for duplicate in secundarios:
                    # 1. Transferencia de logros (Achievements)
                    duplicate.achievements.all().update(randonneur=master)

                    # 2. Transferencia de resultados (Results) controlando restricciones de unicidad
                    for res_dup in duplicate.results.all():
                        res_existente = master.results.filter(event=res_dup.event).first()
                        if res_existente:
                            if res_dup.status == 'FIN' and res_existente.status != 'FIN':
                                res_existente.time = res_dup.time
                                res_existente.status = res_dup.status
                                res_existente.homologation_code = res_dup.homologation_code
                                res_existente.save()
                            elif res_dup.status == 'FIN' and res_existente.status == 'FIN':
                                if res_dup.time and (not res_existente.time or res_dup.time < res_existente.time):
                                    res_existente.time = res_dup.time
                                    res_existente.homologation_code = res_dup.homologation_code or res_existente.homologation_code
                                    res_existente.save()
                            res_dup.delete()
                        else:
                            res_dup.randonneur = master
                            res_dup.save()

                    # 3. Transferencia de vinculacion de usuario tecnico
                    if not master.user and duplicate.user:
                        master.user = duplicate.user
                        master.is_claimed = True
                        master.save()

                        duplicate.user = None
                        duplicate.is_claimed = False
                        duplicate.save()

                    # 4. Eliminacion fisica del duplicado secundario
                    duplicate.delete()
                    fusiones_realizadas += 1

        total_final = Randonneur.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Proceso de deduplicacion finalizado con exito:\n"
            f" - Total perfiles antes: {total_inicial}\n"
            f" - Total perfiles despues: {total_final}\n"
            f" - Perfiles duplicados eliminados y fusionados: {fusiones_realizadas}"
        ))


        #python manage.py deduplicate_randonneurs