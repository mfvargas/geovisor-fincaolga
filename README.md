---
title: Geovisor Finca Olga
emoji: "\U0001F30D"
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.55.0
app_file: app.py
pinned: false
license: mit
short_description: Sentinel-2 satellite imagery viewer for Finca Olga, Costa Rica
---

# Geovisor Finca Olga

Aplicacion web para visualizar imagenes satelitales Sentinel-2 sobre el area de Finca Olga, Costa Rica.

## Funcionalidades

- Busqueda de imagenes Sentinel-2 L2A por rango de fechas
- Filtrado por porcentaje de nubosidad
- Visualizacion de composiciones: color verdadero, falso color, NDVI
- Comparacion lado a lado de imagenes de diferentes fechas
- Deteccion de cambios de vegetacion mediante diferencia de NDVI

## Stack tecnologico

- **UI:** Streamlit
- **Datos satelitales:** Element84 Earth Search STAC API (Sentinel-2 L2A)
- **Mapas:** Folium + streamlit-folium
- **Procesamiento raster:** Rasterio + NumPy

## Ejecucion local

```bash
conda activate geovisor-fincaolga
streamlit run app.py
```

### Creacion del entorno conda

```bash
conda create -n geovisor-fincaolga python=3.13
conda activate geovisor-fincaolga
pip install -r requirements.txt
```

## Estructura del proyecto

```
geovisor-fincaolga/
├── app.py                  # Aplicacion Streamlit principal
├── bbox.geojson            # Bounding box del area de interes
├── requirements.txt        # Dependencias Python
├── packages.txt            # Dependencias de sistema para Hugging Face Spaces
└── modules/
    ├── stac_search.py      # Busqueda de imagenes via STAC API
    ├── imagery.py          # Lectura de COGs y composiciones de bandas
    ├── change_detection.py # Deteccion de cambios (NDVI)
    └── map_display.py      # Mapas folium con overlays
```

## Despliegue en Hugging Face Spaces

El archivo `README.md` contiene el frontmatter YAML necesario para Hugging Face Spaces. Se puede vincular directamente con un repositorio de GitHub o hacer push al Space.

Los archivos `requirements.txt` y `packages.txt` definen las dependencias de Python y de sistema (GDAL) respectivamente.
