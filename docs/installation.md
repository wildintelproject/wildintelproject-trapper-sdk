# Installation

## Requirements

- Python **3.10** or newer
- A running Trapper instance with API access

## Install with pip

```bash
pip install trapper-client
```

## Install with uv

```bash
uv add trapper-client
```

## Install for development

Clone the repository and install the package in editable mode together with the dev dependencies:

```bash
git clone https://github.com/trapper-project/trapper-client.git
cd trapper-client
uv sync
```

## Build the documentation

```bash
uv run mkdocs serve   # live preview at http://127.0.0.1:8000
uv run mkdocs build   # static output in site/
```
