"""
Prueba local rapida: consulta el IGP y muestra los sismos normalizados
en la consola, SIN escribir nada en DynamoDB.

Uso:
    python -m tests.test_local_scrape
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from common.igp_client import fetch_ultimos_sismos
from common.normalizador import normalizar_sismo


def main():
    sismos_crudos = fetch_ultimos_sismos(limit=10)
    print(f"Obtenidos {len(sismos_crudos)} sismos crudos del IGP.\n")

    normalizados = [normalizar_sismo(s) for s in sismos_crudos]
    print(json.dumps(normalizados, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
