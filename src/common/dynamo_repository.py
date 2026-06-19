"""
Capa de acceso a datos: guarda y lee sismos de DynamoDB.
"""
import logging
import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "igp-sismos-api-dev-sismos")

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(TABLE_NAME)


def _a_decimal(item: dict[str, Any]) -> dict[str, Any]:
    """DynamoDB no acepta floats nativos de Python; los convierte a Decimal."""
    converted = {}
    for key, value in item.items():
        if isinstance(value, float):
            converted[key] = Decimal(str(value))
        else:
            converted[key] = value
    return converted


def guardar_sismos(sismos: list[dict[str, Any]]) -> dict[str, int]:
    """
    Guarda (upsert) una lista de sismos normalizados en DynamoDB.
    Como sismo_id es la PK, repetir un sismo simplemente lo sobrescribe
    (idempotente) en vez de duplicarlo.
    """
    guardados = 0
    errores = 0

    with _table.batch_writer(overwrite_by_pkeys=["sismo_id"]) as batch:
        for sismo in sismos:
            try:
                batch.put_item(Item=_a_decimal(sismo))
                guardados += 1
            except Exception:
                logger.exception("Error guardando sismo %s", sismo.get("sismo_id"))
                errores += 1

    logger.info("Guardados: %d, errores: %d", guardados, errores)
    return {"guardados": guardados, "errores": errores}


def listar_sismos(limit: int = 10) -> list[dict[str, Any]]:
    """
    Devuelve hasta `limit` sismos guardados en Dynamo, ordenados por
    fecha_hora descendente, usando el GSI fecha_hora_index.

    Nota: como fecha_hora_index usa fecha_hora solo como hash key (no hay
    range key), hacemos un scan + sort en memoria. Para volumenes grandes
    conviene rediseñar el GSI con una partition key fija y fecha_hora como
    sort key.
    """
    response = _table.scan()
    items = response.get("Items", [])

    # Pagina si hiciera falta (la tabla deberia ser pequeña, pero por si acaso)
    while "LastEvaluatedKey" in response:
        response = _table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    items.sort(key=lambda x: x.get("fecha_hora", ""), reverse=True)
    return items[:limit]
