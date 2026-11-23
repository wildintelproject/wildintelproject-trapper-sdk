# Installation

## Requirements

- Python **3.10** or newer
- A running Trapper instance with API access

!!! note "Not published on PyPI"
    The package is installed from its GitHub repository: `pip install wildintel-trapper-sdk` and
    `uv add wildintel-trapper-sdk` find nothing, because there is no such package on PyPI.

## Install with pip

<div class="termy">

```console
$ pip install git+https://github.com/wildintelproject/wildintelproject-trapper-sdk
---> 100%
Successfully installed wildintel-trapper-sdk-0.1.0
```

</div>

## Install with uv

<div class="termy">

```console
$ uv add git+https://github.com/wildintelproject/wildintelproject-trapper-sdk
Resolved 1 package in 340ms
Installed 1 package in 12ms
 + wildintel-trapper-sdk==0.1.0 (from git+https://github.com/wildintelproject/wildintelproject-trapper-sdk)
```

</div>

## Install a release

By default you get the latest code of the repository. To install a
[release](https://github.com/wildintelproject/wildintelproject-trapper-sdk/releases), name its tag (`vX.Y.Z`):

```bash
pip install git+https://github.com/wildintelproject/wildintelproject-trapper-sdk@vX.Y.Z
uv add git+https://github.com/wildintelproject/wildintelproject-trapper-sdk --tag vX.Y.Z
```

Or install the wheel that each release carries, from its URL on the releases page:

```bash
pip install https://github.com/wildintelproject/wildintelproject-trapper-sdk/releases/download/vX.Y.Z/wildintel_trapper_sdk-X.Y.Z-py3-none-any.whl
```

## Install the `upload` extra

Uploading packages to a Trapper v1 server needs [aiofiles](https://github.com/Tinche/aiofiles) and
[BLAKE3](https://github.com/oconnor663/blake3-py), which the `upload` extra brings. (Trapper v2 uploads do not
need it.)

```bash
pip install "wildintel-trapper-sdk[upload] @ git+https://github.com/wildintelproject/wildintelproject-trapper-sdk"
uv add "wildintel-trapper-sdk[upload] @ git+https://github.com/wildintelproject/wildintelproject-trapper-sdk"
```

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
