"""Lectura de COGs remotos y composiciones de bandas espectrales."""

import io
import base64

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from PIL import Image
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import streamlit as st


@st.cache_data(show_spinner=False)
def read_band(cog_url, bbox, target_shape=None):
    """Lee una banda de un COG remoto, recortada al bbox.

    Args:
        cog_url: URL HTTPS del archivo COG.
        bbox: [west, south, east, north] en EPSG:4326.
        target_shape: (height, width) para resamplear (bandas de 20m a 10m).

    Returns:
        numpy array float32 con los valores de la banda.
    """
    with rasterio.open(cog_url) as src:
        # Reproyectar bbox de EPSG:4326 al CRS del raster (UTM para Sentinel-2)
        dst_bounds = transform_bounds("EPSG:4326", src.crs, bbox[0], bbox[1], bbox[2], bbox[3])
        window = from_bounds(*dst_bounds, transform=src.transform)

        if target_shape:
            data = src.read(1, window=window, out_shape=target_shape, resampling=Resampling.bilinear)
        else:
            data = src.read(1, window=window)

    return data.astype(np.float32)


def _normalize(band, pct_low=2, pct_high=98):
    """Normaliza una banda a uint8 usando percentiles para ajustar contraste."""
    p_low = np.percentile(band[band > 0], pct_low) if np.any(band > 0) else 0
    p_high = np.percentile(band[band > 0], pct_high) if np.any(band > 0) else 1
    if p_high <= p_low:
        p_high = p_low + 1
    clipped = np.clip((band - p_low) / (p_high - p_low), 0, 1)
    return (clipped * 255).astype(np.uint8)


def make_true_color(assets, bbox):
    """Composición color verdadero (RGB) a partir de bandas B04, B03, B02.

    Returns:
        numpy array uint8 (H, W, 4) RGBA.
    """
    red = read_band(assets["red"], bbox)
    green = read_band(assets["green"], bbox)
    blue = read_band(assets["blue"], bbox)

    rgb = np.dstack([_normalize(red), _normalize(green), _normalize(blue)])
    alpha = np.where((red > 0) & (green > 0) & (blue > 0), 255, 0).astype(np.uint8)
    return np.dstack([rgb, alpha])


def make_false_color(assets, bbox):
    """Composición falso color (NIR-R-G) para análisis de vegetación.

    Returns:
        numpy array uint8 (H, W, 4) RGBA.
    """
    nir = read_band(assets["nir"], bbox)
    red = read_band(assets["red"], bbox)
    green = read_band(assets["green"], bbox)

    rgb = np.dstack([_normalize(nir), _normalize(red), _normalize(green)])
    alpha = np.where((nir > 0) & (red > 0) & (green > 0), 255, 0).astype(np.uint8)
    return np.dstack([rgb, alpha])


def compute_ndvi(assets, bbox):
    """Calcula el NDVI: (NIR - Red) / (NIR + Red).

    Returns:
        numpy array float32 con valores en [-1, 1].
    """
    nir = read_band(assets["nir"], bbox)
    red = read_band(assets["red"], bbox)
    denominator = nir + red
    ndvi = np.where(denominator > 0, (nir - red) / denominator, 0)
    return ndvi.astype(np.float32)


def ndvi_to_image(ndvi):
    """Convierte un array NDVI a imagen RGBA coloreada con colormap RdYlGn.

    Returns:
        numpy array uint8 (H, W, 4) RGBA.
    """
    norm = mcolors.Normalize(vmin=-0.2, vmax=0.9)
    colormap = cm.RdYlGn
    colored = colormap(norm(ndvi))
    colored = (colored * 255).astype(np.uint8)
    # Hacer transparente donde no hay datos
    mask = (ndvi == 0)
    colored[mask, 3] = 0
    return colored


def array_to_png_base64(arr):
    """Convierte un array RGBA uint8 a string base64 PNG para folium ImageOverlay."""
    img = Image.fromarray(arr, mode="RGBA")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
