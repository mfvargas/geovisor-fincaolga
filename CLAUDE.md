# CLAUDE.md

## Proyecto

Geovisor Finca Olga: aplicacion Streamlit para visualizar imagenes satelitales Sentinel-2 sobre una finca en Costa Rica (bbox definido en `bbox.geojson`).

## Entorno de desarrollo

- Entorno conda: `geovisor-fincaolga` (Python 3.13)
- Activar: `conda activate geovisor-fincaolga`
- Ejecutar: `streamlit run app.py`

## Arquitectura

- `app.py` — punto de entrada Streamlit, define la UI y conecta los modulos
- `modules/stac_search.py` — busqueda de imagenes Sentinel-2 L2A via Element84 Earth Search STAC API (sin autenticacion). Retorna id, datetime, cloud_cover, platform, assets y thumbnail
- `modules/imagery.py` — lectura de COGs remotos con rasterio (lectura por ventana con reproyeccion de bbox a UTM), composiciones de bandas (true color, false color, NDVI)
- `modules/map_display.py` — mapas folium con ImageOverlay y DualMap para comparacion
- `modules/change_detection.py` — diferencia de NDVI entre dos fechas, clasificacion de cambios

## Detalles tecnicos importantes

- Los COGs de Sentinel-2 estan en UTM, no WGS84. `read_band()` en `imagery.py` usa `rasterio.warp.transform_bounds` para reproyectar el bbox antes de leer.
- Se requieren variables de entorno GDAL para lectura eficiente de COGs remotos (`AWS_NO_SIGN_REQUEST=YES`, etc.), definidas al inicio de `app.py`.
- El bbox es pequeno (~3x3 km), produciendo imagenes de ~335x332 px a 10m de resolucion.
- Las bandas de 20m (SWIR) se resamplean a la grilla de 10m con `out_shape` en rasterio.
- `@st.cache_data` en `read_band()` cachea las lecturas de bandas para evitar re-descargas.

## STAC API

- Endpoint: `https://earth-search.aws.element84.com/v1`
- Coleccion: `sentinel-2-l2a`
- Sin autenticacion requerida
- Assets son COGs publicos en S3

## Despliegue

- Destino: Hugging Face Spaces (sdk: streamlit)
- `packages.txt` define dependencias de sistema (libgdal-dev, gdal-bin) para el contenedor de HF Spaces
- `requirements.txt` define dependencias Python (no incluir streamlit, HF lo provee)
