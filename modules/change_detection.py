"""Detección de cambios de vegetación mediante diferencia de NDVI."""

import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from modules.imagery import compute_ndvi


def ndvi_change(assets_date1, assets_date2, bbox):
    """Calcula la diferencia de NDVI entre dos fechas.

    Args:
        assets_date1: Dict de assets (band->url) de la fecha 1.
        assets_date2: Dict de assets (band->url) de la fecha 2.
        bbox: [west, south, east, north].

    Returns:
        (change_array, ndvi1, ndvi2, stats):
            change_array: float32 [-2, 2], positivo = ganancia de vegetación.
            ndvi1: NDVI de fecha 1.
            ndvi2: NDVI de fecha 2.
            stats: dict con estadísticas del cambio.
    """
    ndvi1 = compute_ndvi(assets_date1, bbox)
    ndvi2 = compute_ndvi(assets_date2, bbox)

    # Máscara de datos válidos (ambas fechas con datos)
    valid = (ndvi1 != 0) & (ndvi2 != 0)
    change = np.where(valid, ndvi2 - ndvi1, 0).astype(np.float32)

    # Estadísticas
    valid_pixels = change[valid]
    total_valid = len(valid_pixels)

    if total_valid > 0:
        stats = {
            "mean_change": float(np.mean(valid_pixels)),
            "std_change": float(np.std(valid_pixels)),
            "loss_pct": float(np.sum(valid_pixels < -0.1) / total_valid * 100),
            "gain_pct": float(np.sum(valid_pixels > 0.1) / total_valid * 100),
            "stable_pct": float(np.sum(np.abs(valid_pixels) <= 0.1) / total_valid * 100),
        }
    else:
        stats = {
            "mean_change": 0.0,
            "std_change": 0.0,
            "loss_pct": 0.0,
            "gain_pct": 0.0,
            "stable_pct": 0.0,
        }

    return change, ndvi1, ndvi2, stats


def change_to_image(change_array, threshold=0.1):
    """Convierte el array de cambio a imagen RGBA coloreada.

    Rojo = pérdida de vegetación, Verde = ganancia, Amarillo = estable.

    Args:
        change_array: float32, diferencia de NDVI.
        threshold: Umbral para considerar cambio significativo.

    Returns:
        numpy array uint8 (H, W, 4) RGBA.
    """
    norm = mcolors.TwoSlopeNorm(vmin=-0.5, vcenter=0, vmax=0.5)
    colormap = cm.RdYlGn
    colored = colormap(norm(np.clip(change_array, -0.5, 0.5)))
    colored = (colored * 255).astype(np.uint8)

    # Transparente donde no hay datos
    mask = (change_array == 0)
    colored[mask, 3] = 0

    return colored
