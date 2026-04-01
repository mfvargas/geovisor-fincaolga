"""Geovisor Finca Olga - Visualizador de imágenes Sentinel-2."""

import os
import json
from datetime import date, timedelta

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from streamlit_folium import st_folium

from modules.stac_search import search_sentinel2
from modules.imagery import make_true_color, make_false_color, compute_ndvi, ndvi_to_image
from modules.map_display import (
    create_base_map,
    add_image_overlay,
    add_bbox_outline,
    create_split_map,
)
from modules.change_detection import ndvi_change, change_to_image

# Variables de entorno para lectura eficiente de COGs remotos
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"] = "EMPTY_DIR"
os.environ["AWS_NO_SIGN_REQUEST"] = "YES"
os.environ["GDAL_HTTP_MERGE_CONSECUTIVE_RANGES"] = "YES"
os.environ["GDAL_HTTP_MULTIPLEX"] = "YES"
os.environ["GDAL_BAND_BLOCK_CACHE"] = "HASHSET"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif,.tiff"
os.environ["GDAL_HTTP_TIMEOUT"] = "30"

# Configuracion de pagina
st.set_page_config(
    page_title="Geovisor Finca Olga",
    page_icon="\U0001F30D",
    layout="wide",
)

# Cargar bbox
BBOX_PATH = os.path.join(os.path.dirname(__file__), "bbox.geojson")
with open(BBOX_PATH) as f:
    bbox_geojson = json.load(f)

# Extraer coordenadas del bbox
coords = bbox_geojson["features"][0]["geometry"]["coordinates"][0][0]
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]
BBOX = [min(lons), min(lats), max(lons), max(lats)]  # [west, south, east, north]

# Titulo
st.title("\U0001F30D Geovisor Finca Olga")
st.markdown("Visualizador de imagenes satelitales Sentinel-2 para Finca Olga, Costa Rica")

# --- Sidebar ---
st.sidebar.header("Parametros de busqueda")

# Rango de fechas
today = date.today()
default_start = today - timedelta(days=180)
col_start, col_end = st.sidebar.columns(2)
date_start = col_start.date_input("Fecha inicio", value=default_start)
date_end = col_end.date_input("Fecha fin", value=today)

# Nubosidad
max_cloud = st.sidebar.slider("Nubosidad maxima (%)", 0, 100, 30)

# Buscar
search_clicked = st.sidebar.button("Buscar imagenes", type="primary", use_container_width=True)

if search_clicked:
    with st.spinner("Buscando imagenes Sentinel-2..."):
        results = search_sentinel2(BBOX, str(date_start), str(date_end), max_cloud)
    st.session_state["search_results"] = results

# Resultados de busqueda
results = st.session_state.get("search_results", [])

if not results:
    # Mostrar mapa base si no hay resultados
    st.sidebar.info("Haga clic en 'Buscar imagenes' para comenzar.")
    m = create_base_map(BBOX)
    add_bbox_outline(m, BBOX_PATH)
    st_folium(m, width=900, height=600, use_container_width=True)
    st.stop()

# Mostrar resultados en sidebar
st.sidebar.markdown(f"**{len(results)} imagenes encontradas**")
image_labels = [
    f"{r['datetime'][:10]} | Nub: {r['cloud_cover']:.1f}%" for r in results
]

# Modo de visualizacion
st.sidebar.markdown("---")
st.sidebar.header("Visualizacion")
mode = st.sidebar.radio(
    "Modo",
    ["Imagen individual", "Comparar fechas", "Deteccion de cambios"],
)

# Seleccion de composicion de bandas
composite_options = {
    "Color verdadero (RGB)": "true_color",
    "Falso color (NIR-R-G)": "false_color",
    "NDVI": "ndvi",
}

if mode == "Imagen individual":
    composite = st.sidebar.selectbox("Composicion de bandas", list(composite_options.keys()))
    selected_idx = st.sidebar.selectbox(
        "Seleccione imagen",
        range(len(results)),
        format_func=lambda i: image_labels[i],
    )
    opacity = st.sidebar.slider("Opacidad", 0.0, 1.0, 0.9, 0.05)

    selected = results[selected_idx]
    st.sidebar.markdown(f"**ID:** `{selected['id']}`")

    with st.spinner("Cargando imagen satelital..."):
        comp_key = composite_options[composite]
        if comp_key == "true_color":
            image = make_true_color(selected["assets"], BBOX)
            layer_name = f"RGB - {selected['datetime'][:10]}"
        elif comp_key == "false_color":
            image = make_false_color(selected["assets"], BBOX)
            layer_name = f"Falso color - {selected['datetime'][:10]}"
        else:
            ndvi = compute_ndvi(selected["assets"], BBOX)
            image = ndvi_to_image(ndvi)
            layer_name = f"NDVI - {selected['datetime'][:10]}"

    m = create_base_map(BBOX)
    add_bbox_outline(m, BBOX_PATH)
    add_image_overlay(m, image, BBOX, name=layer_name, opacity=opacity)
    st_folium(m, width=900, height=600, use_container_width=True)

    # Mostrar histograma NDVI si esta seleccionado
    if comp_key == "ndvi":
        with st.expander("Histograma NDVI"):
            fig, ax = plt.subplots(figsize=(8, 3))
            valid_ndvi = ndvi[ndvi != 0]
            ax.hist(valid_ndvi.flatten(), bins=50, color="green", alpha=0.7, edgecolor="darkgreen")
            ax.set_xlabel("NDVI")
            ax.set_ylabel("Frecuencia")
            ax.set_title(f"Distribucion NDVI - {selected['datetime'][:10]}")
            ax.axvline(x=np.mean(valid_ndvi), color="red", linestyle="--", label=f"Media: {np.mean(valid_ndvi):.3f}")
            ax.legend()
            st.pyplot(fig)

elif mode == "Comparar fechas":
    composite = st.sidebar.selectbox("Composicion de bandas", list(composite_options.keys()))
    col1, col2 = st.sidebar.columns(2)
    idx_left = col1.selectbox(
        "Imagen izquierda",
        range(len(results)),
        format_func=lambda i: image_labels[i],
        key="left",
    )
    idx_right = col2.selectbox(
        "Imagen derecha",
        range(len(results)),
        format_func=lambda i: image_labels[i],
        index=min(1, len(results) - 1),
        key="right",
    )

    left_item = results[idx_left]
    right_item = results[idx_right]

    with st.spinner("Cargando imagenes para comparacion..."):
        comp_key = composite_options[composite]

        if comp_key == "true_color":
            img_left = make_true_color(left_item["assets"], BBOX)
            img_right = make_true_color(right_item["assets"], BBOX)
        elif comp_key == "false_color":
            img_left = make_false_color(left_item["assets"], BBOX)
            img_right = make_false_color(right_item["assets"], BBOX)
        else:
            ndvi_left = compute_ndvi(left_item["assets"], BBOX)
            ndvi_right = compute_ndvi(right_item["assets"], BBOX)
            img_left = ndvi_to_image(ndvi_left)
            img_right = ndvi_to_image(ndvi_right)

    label_left = left_item["datetime"][:10]
    label_right = right_item["datetime"][:10]

    m = create_split_map(img_left, img_right, BBOX, label_left=label_left, label_right=label_right)
    st.markdown(f"**Izquierda:** {label_left} | **Derecha:** {label_right}")
    st_folium(m, width=900, height=600, use_container_width=True)

else:  # Deteccion de cambios
    st.sidebar.markdown("Seleccione dos fechas para detectar cambios de vegetacion (NDVI).")
    col1, col2 = st.sidebar.columns(2)
    idx_before = col1.selectbox(
        "Fecha anterior",
        range(len(results)),
        format_func=lambda i: image_labels[i],
        key="before",
    )
    idx_after = col2.selectbox(
        "Fecha posterior",
        range(len(results)),
        format_func=lambda i: image_labels[i],
        index=min(1, len(results) - 1),
        key="after",
    )
    threshold = st.sidebar.slider("Umbral de cambio", 0.05, 0.3, 0.1, 0.01)

    before_item = results[idx_before]
    after_item = results[idx_after]

    with st.spinner("Calculando deteccion de cambios..."):
        change, ndvi1, ndvi2, stats = ndvi_change(
            before_item["assets"], after_item["assets"], BBOX
        )
        change_img = change_to_image(change, threshold=threshold)

    # Mapa de cambios
    m = create_base_map(BBOX)
    add_bbox_outline(m, BBOX_PATH)
    add_image_overlay(m, change_img, BBOX, name="Cambios NDVI", opacity=0.85)
    st_folium(m, width=900, height=600, use_container_width=True)

    # Leyenda
    st.markdown(
        f"**Cambios entre {before_item['datetime'][:10]} y {after_item['datetime'][:10]}**"
    )
    st.markdown(
        "🔴 Rojo = perdida de vegetacion | 🟡 Amarillo = estable | 🟢 Verde = ganancia"
    )

    # Estadisticas
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("Cambio medio NDVI", f"{stats['mean_change']:+.4f}")
    col_s2.metric("Perdida (%)", f"{stats['loss_pct']:.1f}%")
    col_s3.metric("Estable (%)", f"{stats['stable_pct']:.1f}%")
    col_s4.metric("Ganancia (%)", f"{stats['gain_pct']:.1f}%")

    # Histograma de cambios
    with st.expander("Histograma de cambios"):
        fig, ax = plt.subplots(figsize=(8, 3))
        valid_change = change[(change != 0)]
        ax.hist(valid_change.flatten(), bins=50, color="steelblue", alpha=0.7, edgecolor="navy")
        ax.axvline(x=-threshold, color="red", linestyle="--", alpha=0.7, label=f"Umbral perdida (-{threshold})")
        ax.axvline(x=threshold, color="green", linestyle="--", alpha=0.7, label=f"Umbral ganancia (+{threshold})")
        ax.axvline(x=0, color="gray", linestyle="-", alpha=0.5)
        ax.set_xlabel("Cambio NDVI")
        ax.set_ylabel("Frecuencia")
        ax.set_title("Distribucion de cambios NDVI")
        ax.legend()
        st.pyplot(fig)
