"""Construcción de mapas folium con overlays de imágenes satelitales."""

import json

import folium
from folium.plugins import DualMap, MousePosition
from folium.raster_layers import ImageOverlay
from jinja2 import Template

from modules.imagery import array_to_png_base64


# Indicador de zoom: muestra el nivel actual en la esquina inferior derecha
_ZOOM_INDICATOR = folium.MacroElement()
_ZOOM_INDICATOR._template = Template("""
{% macro script(this, kwargs) %}
    var zoomDiv = L.DomUtil.create('div', 'leaflet-control');
    zoomDiv.style.cssText = 'background:rgba(255,255,255,0.8);padding:2px 6px;font:12px monospace;border-radius:3px;';
    zoomDiv.innerHTML = 'Zoom: ' + {{this._parent.get_name()}}.getZoom();
    var ZoomControl = L.Control.extend({
        options: {position: 'bottomright'},
        onAdd: function(map) {
            map.on('zoomend', function() {
                zoomDiv.innerHTML = 'Zoom: ' + map.getZoom();
            });
            return zoomDiv;
        }
    });
    {{this._parent.get_name()}}.addControl(new ZoomControl());
{% endmacro %}
""")


def _bbox_to_bounds(bbox):
    """Convierte [west, south, east, north] a [[south, west], [north, east]] para folium."""
    return [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]


def _bbox_center(bbox):
    """Retorna [lat, lon] del centro del bbox."""
    return [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2]


def _add_map_controls(m):
    """Agrega controles de coordenadas y zoom a un mapa folium."""
    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="Lat/Lon:",
        num_digits=5,
    ).add_to(m)

    zoom_indicator = folium.MacroElement()
    zoom_indicator._template = _ZOOM_INDICATOR._template
    m.add_child(zoom_indicator)


def create_base_map(bbox, zoom_start=15):
    """Crea un mapa folium centrado en el bbox con basemap satelital."""
    m = folium.Map(
        location=_bbox_center(bbox),
        zoom_start=zoom_start,
        max_zoom=22,
        control_scale=True,
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        max_native_zoom=22,
    )
    # Capa de etiquetas
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png",
        attr="CartoDB",
        name="Etiquetas",
        overlay=True,
        control=False,
    ).add_to(m)
    _add_map_controls(m)
    return m


def add_image_overlay(m, image_array, bbox, name="Imagen satelital", opacity=0.9):
    """Agrega un overlay de imagen sobre el mapa.

    Args:
        m: Mapa folium.
        image_array: numpy array RGBA uint8 (H, W, 4).
        bbox: [west, south, east, north].
        name: Nombre de la capa.
        opacity: Opacidad (0-1).
    """
    bounds = _bbox_to_bounds(bbox)
    png_b64 = array_to_png_base64(image_array)
    image_url = f"data:image/png;base64,{png_b64}"

    ImageOverlay(
        image=image_url,
        bounds=bounds,
        name=name,
        opacity=opacity,
        interactive=False,
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


def add_bbox_outline(m, geojson_path):
    """Agrega el contorno del área de interés al mapa."""
    with open(geojson_path) as f:
        geojson_data = json.load(f)

    folium.GeoJson(
        geojson_data,
        name="Area de interes",
        style_function=lambda x: {
            "color": "#ff7800",
            "weight": 2,
            "fillOpacity": 0,
        },
    ).add_to(m)
    return m


def create_split_map(image_left, image_right, bbox, label_left="Fecha 1", label_right="Fecha 2"):
    """Crea un DualMap para comparación lado a lado.

    Args:
        image_left: numpy array RGBA uint8 para el panel izquierdo.
        image_right: numpy array RGBA uint8 para el panel derecho.
        bbox: [west, south, east, north].
        label_left: Etiqueta para el panel izquierdo.
        label_right: Etiqueta para el panel derecho.

    Returns:
        folium.plugins.DualMap
    """
    bounds = _bbox_to_bounds(bbox)
    center = _bbox_center(bbox)

    m = DualMap(location=center, zoom_start=15, max_zoom=22, control_scale=True)
    _add_map_controls(m.m1)

    # Panel izquierdo
    png_left = array_to_png_base64(image_left)
    ImageOverlay(
        image=f"data:image/png;base64,{png_left}",
        bounds=bounds,
        name=label_left,
        opacity=0.9,
    ).add_to(m.m1)

    # Panel derecho
    png_right = array_to_png_base64(image_right)
    ImageOverlay(
        image=f"data:image/png;base64,{png_right}",
        bounds=bounds,
        name=label_right,
        opacity=0.9,
    ).add_to(m.m2)

    return m
