# IGP Sismos API

API serverless (AWS Lambda + API Gateway + DynamoDB, con Serverless Framework)
que obtiene los 10 últimos sismos reportados por el **Instituto Geofísico del
Perú (IGP)** y los almacena en DynamoDB.

## Cómo se obtienen los datos

La página pública del IGP (`https://ultimosismo.igp.gob.pe/productos/reportes-sismicos`)
es una SPA: el HTML viene casi vacío y los datos se cargan vía JavaScript.
En vez de usar un navegador headless (Selenium/Playwright), la Lambda consume
directamente el servicio **ArcGIS REST (FeatureServer)** público que esa SPA
usa internamente:

```
https://ide.igp.gob.pe/arcgis/rest/services/monitoreocensis/SismosReportados/MapServer/0/query
```

Esto es más rápido, más estable (no depende de la estructura del HTML/CSS de
la página) y es la misma fuente de datos oficial que usa el IGP.

Parámetros usados en la query:

| Parámetro | Valor |
|---|---|
| `where` | `1=1` (sin filtro) |
| `outFields` | `*` (todos los campos) |
| `orderByFields` | `fechaevento DESC` (más reciente primero) |
| `resultRecordCount` | `10` |
| `f` | `json` |

## Arquitectura

```
EventBridge (cada 15 min) ──┐
                             ├──> Lambda scrapeSismos ──> DynamoDB (tabla sismos)
POST /scrape (API GW) ───────┘

GET /sismos (API GW) ──> Lambda getSismos ──> DynamoDB (tabla sismos)
```

- **`scrapeSismos`**: consulta el servicio del IGP, normaliza los campos y
  hace upsert en DynamoDB usando `sismo_id` (el código oficial de reporte del
  IGP, ej. `RS 2026-0290`) como clave, así que reejecutar el scraping nunca
  duplica datos.
- **`getSismos`**: expone `GET /sismos?limit=10` para consultar lo
  almacenado.

## Estructura del proyecto

```
igp-sismos-api/
├── serverless.yml
├── requirements.txt
├── package.json
├── src/
│   ├── common/
│   │   ├── igp_client.py        # Llama al servicio ArcGIS del IGP
│   │   ├── normalizador.py      # Limpia/transforma los datos crudos
│   │   └── dynamo_repository.py # Guarda/lee de DynamoDB
│   └── handlers/
│       ├── scrape_sismos.py     # Lambda: cron + POST /scrape
│       └── get_sismos.py        # Lambda: GET /sismos
└── tests/
    └── test_local_scrape.py     # Prueba local sin tocar AWS
```

## Instalación y despliegue

### 1. Instalar dependencias

```bash
npm install
```

Esto instala `serverless` y el plugin `serverless-python-requirements`
(empaqueta automáticamente las dependencias de `requirements.txt` dentro del
zip de las Lambdas).

### 2. Probar la lógica de scraping localmente (sin AWS)

```bash
pip install -r requirements.txt
python -m tests.test_local_scrape
```

Esto imprime en consola los 10 sismos normalizados, tal cual quedarían en
DynamoDB, sin escribir nada todavía.

### 3. Desplegar a AWS

Asegúrate de tener configuradas tus credenciales AWS (`aws configure` o
variables de entorno) y luego:

```bash
npx serverless deploy --stage dev
```

Al terminar, la salida del comando te mostrará algo como:

```
endpoints:
  POST - https://xxxxxxx.execute-api.us-east-1.amazonaws.com/scrape
  GET  - https://xxxxxxx.execute-api.us-east-1.amazonaws.com/sismos
```

### 4. Probar los endpoints

```bash
# Disparar el scraping manualmente
curl -X POST https://xxxxxxx.execute-api.us-east-1.amazonaws.com/scrape

# Consultar lo guardado
curl https://xxxxxxx.execute-api.us-east-1.amazonaws.com/sismos?limit=10
```

### 5. Ver logs

```bash
npx serverless logs -f scrapeSismos --stage dev -t
npx serverless logs -f getSismos --stage dev -t
```

## Ajustar la frecuencia del cron

En `serverless.yml`, dentro de la función `scrapeSismos`, cambia:

```yaml
- schedule:
    rate: rate(15 minutes)
```

por ejemplo a `rate(5 minutes)` o una expresión `cron(...)` si necesitas más
control sobre los horarios.

## Esquema del item en DynamoDB

```json
{
  "sismo_id": "RS 2026-0290",
  "reporte": 290,
  "fecha_hora": "2026-05-19T17:57:51+00:00",
  "fecha": 1747679871000,
  "hora": "12:57:51",
  "latitud": -14.8,
  "longitud": -75.7,
  "profundidad_km": 81,
  "clasificacion_profundidad": "Intermedio",
  "referencia": "41 km al sur de Ica, Ica",
  "departamento": "Ica",
  "magnitud": 6.1,
  "magnitud_tipo": "Mw",
  "intensidad": "VI",
  "fue_sentido": "Si",
  "fuente": "IGP - CENSIS",
  "actualizado_en": "2026-06-18T15:00:00+00:00"
}
```

> Nota: los nombres exactos de algunos campos (`profundidad`, `int_`,
> `sentido`, etc.) dependen de cómo los devuelve el servicio del IGP en cada
> momento; revisa `tests/test_local_scrape.py` para confirmar el payload
> real antes de desplegar a producción, ya que el IGP puede ajustar su
> esquema sin previo aviso.

## Eliminar todo

```bash
npx serverless remove --stage dev
```

Esto borra las Lambdas, el API Gateway y la tabla DynamoDB (¡cuidado, se
pierden los datos guardados!).
# tareasemana12Cloud
