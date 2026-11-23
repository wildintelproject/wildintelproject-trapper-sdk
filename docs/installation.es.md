# Instalación

## Requisitos

- Python **3.10** o superior
- Una instancia de Trapper (v1 o v2) en funcionamiento y con acceso a la API

## Instalar con pip

<div class="termy">

```console
$ pip install wildintel-trapper-sdk
---> 100%
Successfully installed wildintel-trapper-sdk
```

</div>

## Instalar con uv

<div class="termy">

```console
$ uv add wildintel-trapper-sdk
Resolved 1 package in 340ms
Installed 1 package in 12ms
 + wildintel-trapper-sdk==0.1.0
```

</div>

## Instalar para desarrollo

Clona el repositorio e instala el paquete en modo editable junto con las dependencias de desarrollo:

<div class="termy">

```console
$ git clone https://github.com/wildintelproject/wildintelproject-trapper-sdk.git
Cloning into 'wildintel-trapper-sdk'...
$ cd wildintel-trapper-sdk
$ uv sync
Resolved 42 packages in 120ms
Installed 42 packages in 850ms
```

</div>

## Generar la documentación

El repositorio incluye un pequeño `cli.py` (consulta [Pruebas](testing.md) para su comando `test`) que
envuelve `mkdocs` para que no tengas que recordar sus opciones:

<div class="termy">

```console
$ uv run cli docs serve
Documentación en http://127.0.0.1:8000

INFO    -  Building documentation...
INFO    -  Documentation built in 0.32 seconds
INFO    -  [12:00:00] Watching paths for changes: 'docs', 'mkdocs.yml'
INFO    -  [12:00:00] Serving on http://127.0.0.1:8000/

// O, para generar el sitio estático una vez:
$ uv run cli docs build
Generando documentación...
INFO    -  Documentation built in 2.27 seconds
✔  Sitio generado en site/
```

</div>

La documentación se genera en inglés y en castellano. Las páginas sin traducir se muestran en inglés.
