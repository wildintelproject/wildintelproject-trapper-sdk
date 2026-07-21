# Installation

## Requirements

- Python **3.10** or newer
- A running Trapper instance with API access

## Install with pip

<div class="termy">

```console
$ pip install wildintel-trapper-sdk
---> 100%
Successfully installed wildintel-trapper-sdk
```

</div>

## Install with uv

<div class="termy">

```console
$ uv add wildintel-trapper-sdk
Resolved 1 package in 340ms
Installed 1 package in 12ms
 + wildintel-trapper-sdk==0.1.0
```

</div>

## Install for development

Clone the repository and install the package in editable mode together with the dev dependencies:

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

## Build the documentation

The repository ships a small `cli.py` (see [Testing](testing.md) for its `test` command) that wraps `mkdocs` so you don't need to remember its flags:

<div class="termy">

```console
$ uv run cli docs serve
Documentación en http://127.0.0.1:8000

INFO    -  Building documentation...
INFO    -  Documentation built in 0.32 seconds
INFO    -  [12:00:00] Watching paths for changes: 'docs', 'mkdocs.yml'
INFO    -  [12:00:00] Serving on http://127.0.0.1:8000/

// Or, to generate the static site once:
$ uv run cli docs build
Generando documentación...
INFO    -  Documentation built in 2.27 seconds
✔  Sitio generado en site/
```

</div>
