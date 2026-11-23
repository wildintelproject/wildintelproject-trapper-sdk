# wildintel-trapper-sdk

![WildINTEL](img/wildIntel_logo_cropped.webp){ .logo }
![wildintel-trapper-sdk](img/logo.png){ .logo }

**wildintel-trapper-sdk** es un cliente Python tipado para la API REST de
[Trapper](https://gitlab.com/trapper-project/trapper), la plataforma de código abierto para gestionar y
clasificar datos de fototrampeo: localizaciones, despliegues, recursos multimedia, colecciones de
almacenamiento, proyectos de investigación y resultados de clasificación, tanto manual como asistida
por IA.

Funciona con **Trapper v1 y Trapper v2**: la versión del servidor se detecta automáticamente y las
pocas diferencias entre ambas están documentadas en [Versiones de Trapper](guide/versions.md).

Cada recurso de Trapper se expone como un componente Python tipado que comparte la misma interfaz de
paginación, filtrado y exportación, además de acceso de escritura a los dos recursos (localizaciones y
despliegues) que la API REST no ofrece de forma nativa.

---

## Mapa de la documentación

**[Instalación](installation.md)**

Cómo instalar el paquete con pip/uv, o preparar el repositorio para desarrollo.

**[Uso](usage.md)**

Los patrones de acceso comunes a todos los componentes (`get`, `get_all`/`all`, `where`, `find`,
`export`) y la particularidad de las claves primarias en las tablas intermedias, útil conocer desde el
principio.

**Guías de componentes**

Una guía por recurso (Localizaciones, Despliegues, Clasificaciones, Proyectos de clasificación,
Recursos, Colecciones y más); la lista completa está en la barra lateral.

**[Características](features.md)**

Qué cubre el cliente en detalle: lectura de datos, modelos tipados, las soluciones de escritura para
localizaciones y despliegues, subidas por fragmentos y reintentos, autenticación y gestión de errores.

**[Pruebas](testing.md)**

Las tres capas de pruebas (`unit`, `integration`, `e2e`) y cómo ejecutar cada una.

**[Referencia de la API](api/index.md)**

Referencia generada de todos los componentes, esquemas y del cliente de bajo nivel. Solo está
disponible en inglés.

**[Acerca de](about.md)**

Contexto del proyecto y financiación de WildINTEL.

---

## Instalación

<div class="termy">

```console
$ pip install git+https://github.com/wildintelproject/wildintelproject-trapper-sdk
---> 100%
Successfully installed wildintel-trapper-sdk-0.1.0

// O, con uv:
$ uv add git+https://github.com/wildintelproject/wildintelproject-trapper-sdk
Resolved 1 package in 340ms
Installed 1 package in 12ms
 + wildintel-trapper-sdk==0.1.0 (from git+https://github.com/wildintelproject/wildintelproject-trapper-sdk)
```

</div>

El paquete se instala desde GitHub (no está en PyPI): consulta [Instalación](installation.md).

---

## Inicio rápido

```python
from trapper_client import TrapperClient

client = TrapperClient(
    base_url="https://your-trapper.example",
    access_token="<token>",
)

# Recorrer todas las localizaciones
for loc in client.locations.where(page_size=50):
    print(loc.pk, loc.name)

# Obtener una página de despliegues
page = client.deployments.get(page=1, page_size=25)
print(page.pagination.count, "deployments found")

# Exportar los resultados de clasificación a CSV
client.classification_results.export_project_results(
    project_pk=7,
    file="results.csv",
)
```

---

## Recursos disponibles

| Atributo del cliente | Recurso de la API |
|---|---|
| `client.locations` | Localizaciones |
| `client.locations_geojson` | Localizaciones como GeoJSON |
| `client.deployments` | Despliegues |
| `client.project_deployments` | Despliegues de un proyecto de clasificación y sus acciones (v2) |
| `client.resources` | Recursos multimedia |
| `client.collections` | Colecciones de almacenamiento |
| `client.research_projects` | Proyectos de investigación |
| `client.classification_projects` | Proyectos de clasificación |
| `client.classifications` | Observaciones de clasificación |
| `client.ai_classifications` | Clasificaciones asistidas por IA |
| `client.classification_media` | Medios de clasificación por proyecto |
| `client.classification_results_agg` | Resultados agregados por despliegue |
| `client.classification_package` | Paquetes de datos de resultados |
