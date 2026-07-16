# RandoHub 🚴‍♂️
> Plataforma global, neutral y no oficial de agregación y visualización de datos del ciclismo Randonneur.

**RandoHub** (proyecto de Trabajo Fin de Máster - TFM) nace con la visión de centralizar la información históricamente fragmentada del ciclismo de larga distancia no competitivo (*brevets*, *permanentes*, *flechas* y grandes eventos). La plataforma funciona como un archivo histórico público y neutral que respeta la autoridad de las entidades oficiales (como el Audax Club Parisien) y promueve la transparencia de datos y la privacidad del ciclista.

---

## ✨ Características Principales (MVP)

- **Directorio de Clubes Reales**: Base de datos unificada con 202 clubes oficiales de España.
- **Calendario de Eventos Dinámico**: Visualización estructurada de pruebas deportivas (*Brevets* BRM, LRM, Flechas y Super Randonnées).
- **Cálculo de Reconocimientos (Motor Inteligente)**: Algoritmo en memoria que calcula automáticamente la elegibilidad de un ciclista para el reconocimiento anual de *Super Randonneur (SR)* basándose en la serie completada en un año natural `{200, 300, 400, 600}`.
- **Blindaje e Integridad de Datos (Data Armor)**: 
  - Cálculo automático de estatus (*Finisher* vs *Over Time*) según la normativa de tiempos límites ACP.
  - Validación y unicidad de códigos de homologación oficiales para evitar duplicidades.
  - Flexibilidad para ultra-distancias mediante un sistema de sobrescritura dinámica de límites de tiempo (`max_time_override`).

---

## 🛠️ Stack Tecnológico

- **Lenguaje**: Python 3.12+
- **Framework Backend**: Django 6.0.2 (Arquitectura MTV - Model-Template-View)
- **Base de Datos**: SQLite (Desarrollo local) / Preparado para PostgreSQL
- **Estilos / Frontend**: HTML5 semántico y Pico.css (Framework minimalista y accesible)
- **Control de Versiones**: Git y GitHub

---

## 🚀 Guía de Instalación y Despliegue Local

Sigue estos sencillos pasos para clonar el repositorio y arrancar el servidor de desarrollo en tu ordenador local:

### 1. Requisitos previos
Asegúrate de tener instalado Python 3.11 o superior en tu sistema.

### 2. Clonar el repositorio y acceder a él
```bash
git clone https://github.com/kimegarar/RandoHub.git
cd RandoHub
