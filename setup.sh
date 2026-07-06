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
echo -e "${BOLD}==> trapper-client — setup${NC}"
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
echo "==> Listo. Comandos disponibles:"
echo ""
echo "    uv run cli test              ← tests unit + integration (por defecto)"
echo "    uv run cli test unit         ← solo unit"
echo "    uv run cli test integration  ← solo integration"
echo "    uv run cli test e2e          ← e2e (requiere un servidor Trapper real)"
echo "    uv run cli docs serve        ← sirve la documentación en local"
echo "    uv run cli docs build        ← genera el sitio estático en site/"
echo ""
