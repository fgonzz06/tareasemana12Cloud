"""
Handler de la Lambda `scrapeSismos`.

Se ejecuta:
  - Automaticamente cada 15 minutos via EventBridge (schedule).
  - Manualmente via POST /scrape.

Flujo: consulta el servicio ArcGIS del IGP -> normaliza -> guarda en DynamoDB.
"""
import json
import logging
import os

from common.igp_client import fetch_ultimos_sismos, IgpApiError
from common.normalizador import normalizar_sismo
from common.dynamo_repository import guardar_sismos

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

CANTIDAD_SISMOS = 10


def handler(event, context):
    logger.info("Iniciando scraping de sismos del IGP. Evento: %s", event)

    try:
        sismos_crudos = fetch_ultimos_sismos(limit=CANTIDAD_SISMOS)
    except IgpApiError as exc:
        logger.error("Error consultando el IGP: %s", exc)
        return _respuesta(502, {"error": str(exc)})

    if not sismos_crudos:
        logger.warning("No se obtuvieron sismos del IGP en esta ejecucion.")
        return _respuesta(200, {"mensaje": "Sin datos nuevos", "guardados": 0})

    sismos_normalizados = [normalizar_sismo(s) for s in sismos_crudos]

    resultado = guardar_sismos(sismos_normalizados)

    return _respuesta(
        200,
        {
            "mensaje": "Scraping completado",
            "total_obtenidos": len(sismos_normalizados),
            **resultado,
        },
    )


def _respuesta(status_code: int, body: dict) -> dict:
    """
    Formato compatible tanto con invocacion HTTP (API Gateway/httpApi)
    como con invocacion directa por EventBridge (donde el valor de retorno
    simplemente se ignora, pero no debe romper).
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str, ensure_ascii=False),
    }
