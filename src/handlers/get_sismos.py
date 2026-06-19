"""
Handler de la Lambda `getSismos`.

Expone GET /sismos para consultar los ultimos sismos guardados en DynamoDB.
Soporta un query param opcional `limit` (por defecto 10, max 50).
"""
import json
import logging
import os

from common.dynamo_repository import listar_sismos

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

LIMITE_DEFAULT = 10
LIMITE_MAX = 50


def handler(event, context):
    logger.info("Consultando sismos almacenados. Evento: %s", event)

    query_params = (event or {}).get("queryStringParameters") or {}
    limit = _parsear_limit(query_params.get("limit"))

    try:
        sismos = listar_sismos(limit=limit)
    except Exception as exc:
        logger.exception("Error consultando DynamoDB")
        return _respuesta(500, {"error": f"Error interno: {exc}"})

    return _respuesta(200, {"total": len(sismos), "sismos": sismos})


def _parsear_limit(raw_limit) -> int:
    if not raw_limit:
        return LIMITE_DEFAULT
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return LIMITE_DEFAULT
    return max(1, min(limit, LIMITE_MAX))


def _respuesta(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str, ensure_ascii=False),
    }
