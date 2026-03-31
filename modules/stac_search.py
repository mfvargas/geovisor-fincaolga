"""Búsqueda de imágenes Sentinel-2 via STAC API (Element84 Earth Search)."""

from pystac_client import Client

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"

# Bandas de interés y sus claves en los assets de Earth Search
BAND_KEYS = {
    "red": "red",       # B04 - 10m
    "green": "green",   # B03 - 10m
    "blue": "blue",     # B02 - 10m
    "nir": "nir",       # B08 - 10m
    "swir16": "swir16", # B11 - 20m
}


def search_sentinel2(bbox, date_start, date_end, max_cloud_cover=30, max_items=50):
    """Busca imágenes Sentinel-2 L2A para un bbox y rango de fechas.

    Args:
        bbox: [west, south, east, north] en grados decimales.
        date_start: Fecha de inicio (str "YYYY-MM-DD" o date).
        date_end: Fecha de fin (str "YYYY-MM-DD" o date).
        max_cloud_cover: Porcentaje máximo de nubosidad (0-100).
        max_items: Número máximo de resultados.

    Returns:
        Lista de dicts con: id, datetime, cloud_cover, assets (dict band->url), thumbnail.
    """
    catalog = Client.open(STAC_URL)

    results = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=f"{date_start}T00:00:00Z/{date_end}T23:59:59Z",
        query={"eo:cloud_cover": {"lt": max_cloud_cover}},
        max_items=max_items,
        sortby=[{"field": "properties.datetime", "direction": "desc"}],
    )

    items = []
    for item in results.items():
        assets = {}
        for band_name, asset_key in BAND_KEYS.items():
            if asset_key in item.assets:
                assets[band_name] = item.assets[asset_key].href

        cloud_cover = item.properties.get("eo:cloud_cover", None)
        thumbnail = item.assets.get("thumbnail", None)

        items.append({
            "id": item.id,
            "datetime": item.properties.get("datetime", ""),
            "cloud_cover": cloud_cover,
            "assets": assets,
            "thumbnail": thumbnail.href if thumbnail else None,
        })

    return items
