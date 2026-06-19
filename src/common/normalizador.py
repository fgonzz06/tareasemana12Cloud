"""
Transforma los "attributes" crudos que devuelve el servicio ArcGIS del IGP
en un item limpio y consistente, listo para guardar en DynamoDB.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def _epoch_ms_to_iso(value: Any) -> str | None:
    """ArcGIS devuelve fechas como epoch millis (UTC). Las convertimos a ISO 8601."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        logger.warning("No se pudo parsear el timestamp: %r", value)
        return None


def normalizar_sismo(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convierte el dict crudo de ArcGIS (campos: fecha, hora, lat, lon, prof,
    ref, int_, magnitud, departamento, reporte, code, fechaevento, ...)
    en un item normalizado para DynamoDB.
    """
    code = raw.get("code")
    reporte = raw.get("reporte")
    fechaevento_iso = _epoch_ms_to_iso(raw.get("fechaevento"))

    # sismo_id: usamos el codigo de reporte del IGP si existe (es el
    # identificador oficial, p.ej. "RS 2026-0290"). Si no viniera, armamos
    # un fallback con fecha+hora+referencia para evitar duplicados.
    if code:
        sismo_id = str(code)
    elif reporte:
        sismo_id = f"reporte-{reporte}"
    else:
        sismo_id = f"{raw.get('fecha')}-{raw.get('hora')}-{raw.get('ref')}"

    item = {
        "sismo_id": sismo_id,
        "reporte": reporte,
        "fecha_hora": fechaevento_iso or f"{raw.get('fecha')} {raw.get('hora')}",
        "fecha": raw.get("fecha"),
        "hora": raw.get("hora"),
        "latitud": raw.get("lat"),
        "longitud": raw.get("lon"),
        "profundidad_km": raw.get("prof"),
        "clasificacion_profundidad": raw.get("profundidad"),
        "referencia": raw.get("ref"),
        "departamento": raw.get("departamento"),
        "magnitud": raw.get("magnitud"),
        "magnitud_tipo": raw.get("mag"),
        "intensidad": raw.get("int_"),
        "fue_sentido": raw.get("sentido"),
        "es_ultimo": raw.get("ultimo"),
        "fuente": "IGP - CENSIS",
        "actualizado_en": datetime.now(tz=timezone.utc).isoformat(),
    }

    # Limpiamos valores None para no guardar atributos vacios en Dynamo
    return {k: v for k, v in item.items() if v is not None}
