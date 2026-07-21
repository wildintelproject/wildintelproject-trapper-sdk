#!/usr/bin/env bash
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  ✔  $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠  $*${NC}"; }
err()  { echo -e "${RED}  ✘  $*${NC}" >&2; }

echo ""
echo -e "${BOLD}==> wildintel-trapper-sdk — setup${NC}"
echo ""

# ── uv ────────────────────────────────────────────────────────────────────────

if command -v uv &>/dev/null; then
    ok "uv $(uv --version)"
else
    warn "uv no encontrado. Instalando..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if command -v uv &>/dev/null; then
        ok "uv $(uv --version) instalado correctamente."
        warn "Reinicia el terminal (o ejecuta: source ~/.bashrc) para que uv esté disponible en nuevas sesiones."
    else
        err "No se pudo instalar uv. Visita https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

# ── Dependencias ──────────────────────────────────────────────────────────────

echo ""
echo "==> Instalando dependencias (extras + grupo dev: tests, docs y CLI)..."
uv sync --all-extras
ok "Dependencias instaladas."

# ── Resumen ───────────────────────────────────────────────────────────────────

echo ""
echo "==> Listo. Activa el entorno virtual creado por uv:"
echo ""
echo "    source .venv/bin/activate"
echo ""
echo "==> Comandos disponibles (con el entorno activado, o con 'uv run' delante sin activarlo):"
echo ""
echo "    cli test              ← tests unit + integration (por defecto)"
echo "    cli test unit         ← solo unit"
echo "    cli test integration  ← solo integration"
echo "    cli test e2e          ← e2e (requiere un servidor Trapper real)"
echo "    cli docs serve        ← sirve la documentación en local"
echo "    cli docs build        ← genera el sitio estático en site/"
echo ""
