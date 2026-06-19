"""
Cliente para consultar el servicio ArcGIS REST (FeatureServer) que alimenta
el visor "Reportes Sismicos" del IGP:
https://ultimosismo.igp.gob.pe/productos/reportes-sismicos

El sitio es una SPA que internamente consume esta capa publica:
  https://ide.igp.gob.pe/arcgis/rest/services/monitoreocensis/SismosReportados/MapServer/0

En vez de renderizar la pagina con un navegador headless (lento y fragil),
consultamos directamente este endpoint JSON, que es mucho mas estable.
"""
import os
import logging
from typing import Any
from urllib.parse import urlencode

import urllib3

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5.0, read=10.0))

IGP_API_URL = os.environ.get(
    "IGP_API_URL",
    "https://ide.igp.gob.pe/arcgis/rest/services/monitoreocensis/SismosReportados/MapServer/0/query",
)


class IgpApiError(Exception):
    """Error al consultar o parsear la respuesta del servicio del IGP."""


def fetch_ultimos_sismos(limit: int = 10) -> list[dict[str, Any]]:
    """
    Consulta los ultimos `limit` sismos reportados, ordenados por fecha
    de evento descendente (el mas reciente primero).

    Devuelve una lista de diccionarios con los "attributes" crudos que
    entrega el servicio ArcGIS (fecha, hora, lat, lon, prof, ref,
    magnitud, departamento, reporte, code, etc.)
    """
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "orderByFields": "fechaevento DESC",
        "resultRecordCount": str(limit),
        "f": "json",
    }
    url = f"{IGP_API_URL}?{urlencode(params)}"

    logger.info("Consultando API del IGP: %s", url)

    try:
        response = http.request("GET", url)
    except urllib3.exceptions.HTTPError as exc:
        raise IgpApiError(f"Fallo de red al consultar el IGP: {exc}") from exc

    if response.status != 200:
        raise IgpApiError(
            f"El servicio del IGP respondio con status {response.status}"
        )

    try:
        body = response.json()
    except Exception as exc:  # respuesta no es JSON valido
        raise IgpApiError(f"Respuesta no es JSON valido: {exc}") from exc

    if "error" in body:
        raise IgpApiError(f"El servicio del IGP devolvio un error: {body['error']}")

    features = body.get("features", [])
    if not features:
        logger.warning("La respuesta del IGP no contiene features (sismos).")
        return []

    sismos = [feature["attributes"] for feature in features if "attributes" in feature]
    logger.info("Se obtuvieron %d sismos del IGP.", len(sismos))
    return sismos
