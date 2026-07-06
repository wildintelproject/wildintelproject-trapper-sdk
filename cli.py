#!/usr/bin/env python
"""
trapper-client — CLI de gestión.

Uso:
    uv run cli test [unit|integration|e2e|all] [-k keyword] [-v]
    uv run cli docs serve [--port 8000]
    uv run cli docs build
"""
import os
import subprocess
import sys
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel


def _find_root() -> Path:
    """Locate the project root by walking up from the current directory.

    `cli.py` is force-included into the built distribution so that the
    `cli` entry point script works (see pyproject.toml). That means when
    invoked as `uv run cli`, this file is executed from a copy inside
    site-packages and `Path(__file__).parent` no longer points at the repo
    — so the root is located from the CWD instead, which is where `uv run`
    is expected to be invoked from.
    """
    current = Path.cwd()
    for directory in (current, *current.parents):
        if (directory / "pyproject.toml").exists() and (directory / "mkdocs.yml").exists():
            return directory
    return current


# ── Constantes ────────────────────────────────────────────────────────────────

ROOT_DIR   = _find_root()
MKDOCS_CFG = ROOT_DIR / "mkdocs.yml"

console = Console()
app     = typer.Typer(help="trapper-client — herramienta de gestión.")


# ── Enums ─────────────────────────────────────────────────────────────────────

class TestSuite(str, Enum):
    unit        = "unit"
    integration = "integration"
    e2e         = "e2e"
    all         = "all"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(*args: str) -> None:
    result = subprocess.run(list(args), cwd=ROOT_DIR)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


# ── test ──────────────────────────────────────────────────────────────────────

@app.command()
def test(
    suite:   TestSuite  = typer.Argument(TestSuite.all, help="Suite a ejecutar."),
    verbose: bool       = typer.Option(False, "--verbose", "-v", help="Salida detallada (-v de pytest)."),
    keyword: str | None = typer.Option(None, "--keyword", "-k", help="Filtro de tests por nombre (-k de pytest)."),
) -> None:
    """Ejecuta los tests con pytest (unit / integration / e2e / all)."""
    marker = {
        TestSuite.unit:        "unit",
        TestSuite.integration: "integration",
        TestSuite.e2e:         "e2e",
        TestSuite.all:         "unit or integration",
    }[suite]

    console.print(Panel(
        f"[bold]Suite:[/bold] {suite.value}   [bold]Marcador:[/bold] -m \"{marker}\"",
        title="trapper-client — tests",
    ))

    if suite == TestSuite.e2e and not os.getenv("WILDINTEL_SMOKE_ENABLED"):
        console.print(
            "[yellow]⚠  WILDINTEL_SMOKE_ENABLED no está definido: los tests e2e se "
            "saltarán salvo que también definas WILDINTEL_BASE_URL y las credenciales "
            "(WILDINTEL_ACCESS_TOKEN o WILDINTEL_USER_NAME/WILDINTEL_USER_PASSWORD).[/yellow]\n"
        )

    cmd = [sys.executable, "-m", "pytest", "tests", "-m", marker]
    cmd.append("-v" if verbose else "-q")
    if keyword:
        cmd.extend(["-k", keyword])

    _run(*cmd)


# ── docs (generar o servir la documentación) ─────────────────────────────────

docs_app = typer.Typer(help="Genera o sirve la documentación (mkdocs).")
app.add_typer(docs_app, name="docs")


@docs_app.command("serve")
def docs_serve(
    port: int = typer.Option(8000, "--port", "-p", help="Puerto del servidor de documentación."),
) -> None:
    """Sirve la documentación en local con recarga automática (http://127.0.0.1:<port>)."""
    console.print(f"[green]Documentación en http://127.0.0.1:{port}[/green]\n")
    _run("mkdocs", "serve", "--config-file", str(MKDOCS_CFG), "--dev-addr", f"127.0.0.1:{port}")


@docs_app.command("build")
def docs_build() -> None:
    """Genera el sitio estático de la documentación en site/."""
    console.print("[green]Generando documentación...[/green]")
    _run("mkdocs", "build", "--config-file", str(MKDOCS_CFG))
    console.print(f"[green]✔  Sitio generado en {ROOT_DIR / 'site'}[/green]")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
