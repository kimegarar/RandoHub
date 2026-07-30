# RandoHub 🚴‍♂️

> Plataforma global, neutral y no oficial de agregación y visualización de datos del ciclismo Randonneur de ultra-distancia.

**RandoHub** es un proyecto de Trabajo Fin de Máster (TFM) diseñado para resolver la fragmentación histórica de los datos en el ciclismo de larga distancia no competitivo (*brevets*, *permanentes*, *flechas* y grandes eventos). La plataforma funciona como un archivo histórico público y neutral que unifica los resultados históricos dispersos en múltiples formatos, respetando la autoridad de las entidades oficiales (como el Audax Club Parisien y Les Randonneurs Mondiaux) y aplicando principios de protección de datos personales.

---

## ✨ Características Principales (Fases A, B y C)

### 1. Ingesta de Datos Core y MVP Nacional (Fase A)
- **Directorio de Clubes Reales**: Base de datos unificada con 202 clubes oficiales de España indexados por códigos ACP.
- **Calendario de Eventos Dinámico**: Visualización estructurada de pruebas deportivas (*Brevets* BRM, LRM, Flechas y Super Randonnées).
- **Cálculo de Reconocimientos (Motor Inteligente)**: Algoritmo en memoria que calcula automáticamente la elegibilidad de un ciclista para el reconocimiento anual de *Super Randonneur (SR)* basándose en la serie completada en un año natural `{200, 300, 400, 600}`.
- **Blindaje e Integridad de Datos (Data Armor)**: 
  - Cálculo automático de estatus (*Finisher* vs *Over Time*) según la normativa de tiempos límites oficiales de la ACP.
  - Validación y unicidad de códigos de homologación oficiales para evitar duplicidades accidentales.
  - Flexibilidad para ultra-distancias mediante un sistema de sobrescritura dinámica de límites de tiempo (`max_time_override`).

### 2. Identidad, Cuentas y Privacidad GDPR (Fase B)
- **Desacoplamiento de Identidad**: Separación arquitectónica estricta entre la cuenta técnica del usuario (`User` de Django) y el perfil público e histórico del ciclista (`Randonneur`).
- **Niveles de Privacidad (Privacy by Design)**: Tres niveles de visibilidad (`Público`, `Comunidad` y `Privado`) blindados activamente a nivel de backend en las vistas de detalle.
- **Flujo de Reclamación Voluntaria (Claiming Flow)**: Mecanismo seguro para que un usuario se asocie a su historial randonneur real existente mediante el consentimiento explícito.
- **Sistema de Solicitud de Fusión (Merge Requests)**: Permite que los ciclistas registrados propongan fusiones de perfiles duplicados. El administrador aprueba y ejecuta la fusión con un solo clic desde el panel Django Admin.

### 3. Automatización, Deduplicación e Ingesta de SR600 (Fase C)
- **Ingesta de Hojas de Cálculo Dinámica**: Comando de importación multilingüe que lee desde archivos locales o convierte URLs públicas de Google Sheets directamente a formato CSV para su análisis relacional.
- **Motor de Resolución de Entidades (Deduplicación)**: Script automático que limpia caracteres corruptos por problemas de decodificación tipográfica (como `"la“pez"` a `"lopez"`), normaliza nombres y los compara mediante conjuntos de palabras (*Token Set Matching*), obviando el orden de nombre/apellidos.
- **Calculador de Progreso en Tiempo Real**: Módulo visual que indica al ciclista en su perfil qué pruebas de la serie SR tiene completadas y cuáles le faltan exactamente para obtener el título en el año en curso.
- **Reconocimiento SR10, SR20 y SR30**: Algoritmos de sincronización de logros acumulativos basados en la realización de múltiples rutas SR600 permanentes distintas.

---

## 🛠️ Stack Tecnológico

- **Lenguaje**: Python 3.12+
- **Framework Backend**: Django 6.0.2 (Arquitectura MTV - Model-Template-View)
- **Base de Datos**: SQLite (Desarrollo local) / Diseñado para PostgreSQL (Producción)
- **Estilos / Frontend**: HTML5 semántico y Pico.css (Framework minimalista y accesible)
- **Control de Versiones**: Git y GitHub

---

## 🚀 Guía de Instalación y Despliegue Local

Sigue estos sencillos pasos para clonar el repositorio, configurar el entorno y arrancar el servidor de desarrollo en tu ordenador local:

### 1. Clonar el repositorio y acceder a él
```bash
git clone https://github.com/kimegarar/RandoHub.git
cd RandoHub

### 2. Crear y activar el entorno virtual

En macOS y Linux:
code Bash

python3 -m venv .venv
source .venv/bin/activate

En Windows:
code Bash

python -m venv .venv
.venv\Scripts\activate

### 3. Instalar las dependencias del proyecto
code Bash

pip install --upgrade pip
pip install -r requirements.txt

### 4. Ejecutar las migraciones de la base de datos

Este comando estructurará la base de datos local SQLite bajo la Tercera Forma Normal (3FN):
code Bash

python manage.py makemigrations
python manage.py migrate

5. Crear la cuenta de administrador (Superusuario)
code Bash

python manage.py createsuperuser

6. Cargar y sembrar los datos (Seeding & Ingesta)

Ejecuta los comandos de gestión personalizados para poblar tu base de datos con los datos reales e históricos del portal:
code Bash

# Ingesta de clubes y ciclistas base
python manage.py import_clubs
python manage.py import_randonneurs

# Ingesta masiva de resultados de internet (LRM)
python manage.py scrape_lrm

# Ingesta de las rutas de las Super Randonnees permanentes
python manage.py import_sr600_routes

# Ingesta de los logros del reto 10x de las SR permanentes
python manage.py import_sr_challenge_sheet

# Pipeline automatizado de resolucion de entidades (Deduplicacion)
python manage.py deduplicate_randonneurs

7. Iniciar el servidor de desarrollo local
code Bash

python manage.py runserver

Abre tu navegador web y accede a: http://127.0.0.1:8000/
🏛️ Justificación Académica y Patrones de Diseño

    Patrón MTV (Model-Template-View): Desacoplamiento estricto de responsabilidades. La persistencia e integridad lógica residen en el Modelo (models.py); la orquestación del flujo de datos en la Vista (views.py); y la presentación en las plantillas semánticas HTML5.

    Modelo Normalizado (3FN): El dominio randonneur está estructurado en base a dependencias transitivas claras, erradicando los problemas de redundancia e inconsistencia durante la inserción de resultados masivos de internet.

    TimeStampedModel: Implementación de una clase base abstracta (abstract = True) de auditoría de marcas temporales para evitar la duplicidad de código en la base de datos, respetando el principio DRY.

