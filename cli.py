#!/usr/bin/env python
"""
wildintel-trapper-sdk — CLI de gestión.

Uso:
    uv run cli test [unit|integration|e2e|all] [-k keyword] [-v]
    uv run cli docs serve [--port 8000]
    uv run cli docs build
    uv run cli trapper up [v1|v2|all] [--branch RAMA] [--port-offset N]
    uv run cli trapper status|logs|env|down|destroy [v1|v2|all]
"""
import json
import os
import re
import secrets
import shlex
import socket
import subprocess
import sys
import time
import zlib
from dataclasses import dataclass, replace
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
app     = typer.Typer(help="wildintel-trapper-sdk — herramienta de gestión.")


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
        title="wildintel-trapper-sdk — tests",
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


# ── trapper (despliega Trapper v1, v2 y v2-ninja para las pruebas) ───────────

#: Compose y semillas de las instancias de prueba (sin los contenedores de IA ni de ciencia ciudadana).
STACK_DIR = ROOT_DIR / "dev" / "trapper"
#: Secretos, puertos y credenciales de cada instancia; git no los versiona.
STATE_DIR = STACK_DIR / ".state"
TRAPPER_IMAGE_REPO = "registry.gitlab.com/trapper-project/trapper"


@dataclass(frozen=True)
class Stack:
    """Una versión de Trapper y los puertos en los que se publica (sin desplazamiento)."""

    #: ``v1``, ``v2`` o ``ninja``: lo que se elige en la línea de órdenes.
    key: str
    #: La versión de Trapper (``v1`` o ``v2``): el compose que se usa.
    version: str
    default_branch: str
    nginx_image: str
    postgres_image: str
    app_port: int
    nginx_port: int
    uploader_port: int
    rabbitmq_port: int
    tusd_image: str = ""
    #: Se suma a todos los puertos. Con un desplazamiento es **otra instancia**: otro proyecto de compose, otros
    #: volúmenes y otra carpeta de estado, así que convive con la de desplazamiento 0.
    offset: int = 0
    #: Etiqueta de la instancia (``ninja`` -> ``v2-ninja``); sin ella se nombra por el desplazamiento (``v2-p1000``).
    label: str = ""

    @property
    def name(self) -> str:
        suffix = self.label or (f"p{self.offset}" if self.offset else "")
        return f"{self.version}-{suffix}" if suffix else self.version

    @property
    def subnet(self) -> str:
        """Una subred /24 de 10.77.x.0 para esta instancia (Docker se queda sin las suyas si hay muchas redes de otros proyectos)."""
        return f"10.77.{20 + zlib.crc32(self.name.encode()) % 200}.0/24"

    @property
    def project(self) -> str:
        return f"wildintel-sdktest-trapper-{self.name}"

    @property
    def compose_file(self) -> Path:
        return STACK_DIR / f"docker-compose.{self.version}.yml"

    @property
    def state(self) -> Path:
        return STATE_DIR / self.name


STACKS = {
    "v1": Stack(
        key="v1", version="v1", default_branch="latest",
        nginx_image="registry.gitlab.com/trapper-project/trapper-nginx/no-ssl:latest",
        postgres_image="registry.gitlab.com/trapper-project/trapper-postgresql:latest",
        app_port=8010, nginx_port=8080, uploader_port=8088, rabbitmq_port=15672,
    ),
    "v2": Stack(
        key="v2", version="v2", default_branch="2.0.0a2",
        nginx_image="registry.gitlab.com/trapper-project/trapper-nginx/no-ssl:video-streaming",
        postgres_image="registry.gitlab.com/trapper-project/trapper-postgresql:timescaledb",
        app_port=8100, nginx_port=8180, uploader_port=8188, rabbitmq_port=15772,
        tusd_image="tusproject/tusd:v2.10.1",
    ),
    # The new API (Django Ninja, ``/api/v2/``) of the branch refactor/api-ninja: a v2 with its own ports, so that it
    # runs next to the other two.
    "ninja": Stack(
        key="ninja", version="v2", default_branch="refactor-api-ninja", label="ninja",
        nginx_image="registry.gitlab.com/trapper-project/trapper-nginx/no-ssl:video-streaming",
        postgres_image="registry.gitlab.com/trapper-project/trapper-postgresql:timescaledb",
        app_port=8200, nginx_port=8280, uploader_port=8288, rabbitmq_port=15872,
        tusd_image="tusproject/tusd:v2.10.1",
    ),
}


class StackChoice(str, Enum):
    v1    = "v1"
    v2    = "v2"
    ninja = "ninja"
    all   = "all"


trapper_app = typer.Typer(help="Despliega instancias de Trapper v1, v2 y v2-ninja con los datasets de prueba, y lanza los e2e (sin IA ni ciencia ciudadana).")
app.add_typer(trapper_app, name="trapper")


def _stacks(choice: StackChoice, offset: int = 0, label: str | None = None) -> list[Stack]:
    stacks = list(STACKS.values()) if choice == StackChoice.all else [STACKS[choice.value]]
    return [replace(stack, offset=offset, label=_slug(label) if label else stack.label) for stack in stacks]


#: ``--name`` de todos los comandos de ``trapper``: el mismo que se dio en ``up``.
NAME_OPTION = typer.Option(None, "--name", "-n", help="Etiqueta de la instancia (p. ej. ds1 -> v2-ds1); la misma que en up.")


def _slug(branch: str) -> str:
    """El nombre que da el CI de GitLab a la etiqueta de una rama: minúsculas, lo demás a ``-``, 63 como mucho."""
    return re.sub(r"[^a-z0-9]+", "-", branch.lower()).strip("-")[:63]


def _tag_candidates(branch: str) -> list[str]:
    """La rama tal cual (una etiqueta como ``2.0.0a2``) y su nombre en el CI (``refactor/api-ninja`` -> ``refactor-api-ninja``)."""
    return list(dict.fromkeys([branch, _slug(branch)]))


def _image_exists(image: str) -> bool:
    """¿Está la imagen en local o en el registro? (``docker manifest inspect`` mira el registro, sin descargarla)."""
    for cmd in (["docker", "image", "inspect", image], ["docker", "manifest", "inspect", image]):
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            return True
    return False


def _resolve_image(branch: str) -> str:
    """La imagen de Trapper de una rama (o etiqueta). Termina con un error claro si no existe."""
    tried = []
    for tag in _tag_candidates(branch):
        image = f"{TRAPPER_IMAGE_REPO}:{tag}"
        tried.append(image)
        if _image_exists(image):
            return image
    console.print(f"[red]No hay imagen para «{branch}»[/red] (probé {', '.join(tried)}), o no hay red hacia el registro.")
    raise typer.Exit(1)


def _branch_for(stack: Stack, branch: str | None, v1_branch: str | None, v2_branch: str | None,
                ninja_branch: str | None = None) -> str:
    """La rama de una instancia: la de su versión, si no ``--branch``, si no la de por defecto."""
    return {"v1": v1_branch, "v2": v2_branch, "ninja": ninja_branch}[stack.key] or branch or stack.default_branch


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def _write_env(stack: Stack, image: str) -> Path:
    """Escribe el ``.env`` de la instancia. Los secretos se crean una vez y se conservan: la base de datos nace con ellos."""
    stack.state.mkdir(parents=True, exist_ok=True)
    path = stack.state / ".env"
    old = _read_env(path)
    env = {
        "COMPOSE_PROJECT_NAME": stack.project,
        "TRAPPER_IMAGE": image,
        "NGINX_IMAGE": stack.nginx_image,
        "POSTGRES_IMAGE": stack.postgres_image,
        "TUSD_IMAGE": stack.tusd_image,
        "APP_PORT": str(stack.app_port + stack.offset),
        "NGINX_PORT": str(stack.nginx_port + stack.offset),
        "UPLOADER_PORT": str(stack.uploader_port + stack.offset),
        "RABBITMQ_MGMT_PORT": str(stack.rabbitmq_port + stack.offset),
        "NETWORK_SUBNET": stack.subnet,
        **{k: old.get(k) or secrets.token_urlsafe(24)
           for k in ("POSTGRES_PASSWORD", "RABBITMQ_PASSWORD", "TRAPPER_SECRET_KEY", "TUS_HOOK_SECRET")},
    }
    path.write_text("# Generado por `uv run cli trapper up`; no lo edites (los secretos se conservan).\n"
                    + "".join(f"{k}={v}\n" for k, v in env.items()))
    return path


def _compose(stack: Stack, *args: str, capture: bool = False, stdin: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", "-f", str(stack.compose_file), "--env-file", str(stack.state / ".env"), *args]
    return subprocess.run(cmd, cwd=ROOT_DIR, capture_output=capture, text=True, input=stdin)


def _busy(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_for(url: str, timeout: int) -> bool:
    """Espera a que la instancia conteste algo que no sea un error del servidor (nginx da 502 hasta que la app arranca)."""
    import httpx

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=5, follow_redirects=True).status_code < 500:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(3)
    return False


def _seed_accounts(stack: Stack) -> dict:
    """Crea (o actualiza) las cuentas y el proyecto de investigación, y guarda los tokens en el estado."""
    script = (STACK_DIR / "seed" / "accounts.py").read_text()
    result = _compose(stack, "exec", "-T", "-u", "trapper", "trapper", "python", "manage.py", "shell",
                      capture=True, stdin=script)
    line = next((l for l in result.stdout.splitlines() if l.startswith("SEED_JSON:")), None)
    if result.returncode != 0 or line is None:
        console.print(f"[red]No se pudieron crear las cuentas en {stack.name}:[/red]\n{result.stdout[-800:]}{result.stderr[-800:]}")
        raise typer.Exit(1)
    data = json.loads(line[len("SEED_JSON:"):])
    (stack.state / "seed.json").write_text(json.dumps(data, indent=2))
    return data


def _ports(stack: Stack) -> dict[str, int]:
    env = _read_env(stack.state / ".env")
    return {k: int(env[k]) for k in ("APP_PORT", "NGINX_PORT", "UPLOADER_PORT", "RABBITMQ_MGMT_PORT") if k in env}


@trapper_app.command("up")
def trapper_up(
    which: StackChoice = typer.Argument(StackChoice.all, help="Qué instancia desplegar."),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Rama (o etiqueta) de la imagen de Trapper, para las instancias elegidas; por defecto latest (v1) y 2.0.0a2 (v2)."),
    v1_branch: str | None = typer.Option(None, "--v1-branch", help="Rama solo para v1 (gana a --branch)."),
    v2_branch: str | None = typer.Option(None, "--v2-branch", help="Rama solo para v2 (gana a --branch)."),
    ninja_branch: str | None = typer.Option(None, "--ninja-branch", help="Rama solo para ninja (gana a --branch); por defecto refactor-api-ninja."),
    port_offset: int = typer.Option(0, "--port-offset", help="Se suma a todos los puertos (para tener otra instancia a la vez)."),
    name: str | None = NAME_OPTION,
    seed: bool = typer.Option(True, "--seed/--no-seed", help="Crear las cuentas y el proyecto de investigación."),
    timeout: int = typer.Option(600, "--timeout", help="Segundos de espera a que la app responda (el primer arranque migra la base de datos)."),
) -> None:
    """Despliega Trapper v1, v2 y/o ninja con las mismas cuentas de prueba; ``--branch`` elige la imagen."""
    for stack in _stacks(which, port_offset, name):
        image = _resolve_image(_branch_for(stack, branch, v1_branch, v2_branch, ninja_branch))
        env_path = _write_env(stack, image)
        console.print(Panel(f"[bold]{stack.name}[/bold]  imagen {image}", title="trapper up"))

        running = _compose(stack, "ps", "-q", capture=True).stdout.strip()
        busy = [p for p in _ports(stack).values() if _busy(p)] if not running else []
        if busy:
            console.print(f"[red]Puertos ocupados: {busy}.[/red] Para o borra la otra instancia, o usa [bold]--port-offset[/bold].")
            raise typer.Exit(1)

        result = _compose(stack, "up", "-d")
        if result.returncode != 0:
            raise typer.Exit(result.returncode)
        url = f"http://localhost:{_ports(stack)['NGINX_PORT']}/"
        console.print(f"Esperando a {url} (hasta {timeout} s)...")
        if not _wait_for(url, timeout):
            console.print(f"[red]La app no contestó en {timeout} s.[/red] Mira: uv run cli trapper logs {stack.key}")
            raise typer.Exit(1)
        if seed:
            data = _seed_accounts(stack)
            console.print(f"[green]✔  {stack.name}: cuentas y proyecto SDKT (pk {data['research_project']}) listos[/green]")
        console.print(f"[green]✔  {stack.name} en {url}[/green]  (estado: {env_path.parent})\n")
    console.print("Siguiente:  [bold]uv run cli trapper seed v1|v2|ninja --dataset 1|2[/bold], y luego "
                  "[bold]uv run cli trapper e2e v1|v2|ninja --dataset 1|2[/bold]")


@trapper_app.command("down")
def trapper_down(which: StackChoice = typer.Argument(StackChoice.all), port_offset: int = typer.Option(0, "--port-offset", help="El de la instancia (el mismo que le diste en up)."), name: str | None = NAME_OPTION)  -> None:
    """Para las instancias y conserva sus datos."""
    for stack in _stacks(which, port_offset, name):
        if (stack.state / ".env").exists():
            _compose(stack, "down")


@trapper_app.command("destroy")
def trapper_destroy(
    which: StackChoice = typer.Argument(StackChoice.all),
    yes: bool = typer.Option(False, "--yes", "-y", help="No pedir confirmación."),
    port_offset: int = typer.Option(0, "--port-offset", help="El de la instancia (el mismo que le diste en up)."),
    name: str | None = NAME_OPTION,
) -> None:
    """Borra las instancias **y sus datos** (volúmenes). Los secretos y puertos del estado se conservan."""
    stacks = _stacks(which, port_offset, name)
    if not yes and not typer.confirm(f"Borrar {', '.join(s.version for s in stacks)} y todos sus datos?"):
        raise typer.Exit(1)
    for stack in stacks:
        if (stack.state / ".env").exists():
            _compose(stack, "down", "-v")
            (stack.state / "seed.json").unlink(missing_ok=True)


@trapper_app.command("status")
def trapper_status(which: StackChoice = typer.Argument(StackChoice.all), port_offset: int = typer.Option(0, "--port-offset", help="El de la instancia (el mismo que le diste en up)."), name: str | None = NAME_OPTION)  -> None:
    """Contenedores de cada instancia."""
    for stack in _stacks(which, port_offset, name):
        console.print(f"[bold]{stack.name}[/bold]")
        if (stack.state / ".env").exists():
            _compose(stack, "ps")
        else:
            console.print("  sin desplegar (uv run cli trapper up)")


@trapper_app.command("logs")
def trapper_logs(
    which: StackChoice = typer.Argument(StackChoice.v2),
    service: str | None = typer.Argument(None, help="trapper, trapper-celery, trapper-nginx, postgres, ..."),
    follow: bool = typer.Option(False, "--follow", "-f"),
    tail: int = typer.Option(100, "--tail"),
    port_offset: int = typer.Option(0, "--port-offset", help="El de la instancia (el mismo que le diste en up)."),
    name: str | None = NAME_OPTION,
) -> None:
    """Registro de una instancia (de un servicio si das su nombre)."""
    for stack in _stacks(which, port_offset, name):
        args = ["logs", "--tail", str(tail), *(["-f"] if follow else []), *([service] if service else [])]
        _compose(stack, *args)


#: Los datasets de prueba: el script que siembra cada uno (``dev/trapper/seed/dataset<N>.py``).
DATASETS = {"1": "Mamíferos de Doñana y Sierra Morena (26 imágenes)", "2": "Cabañeros 2025 (640 imágenes, >500 filas)"}
DATASET_OPTION = typer.Option(..., "--dataset", "-d", help="1: Doñana y Sierra Morena (pequeño); 2: Cabañeros 2025 (>500 filas).")


def _ready(stack: Stack) -> dict:
    """El ``seed.json`` de la instancia (cuentas y tokens); termina con un error claro si no se desplegó."""
    seed_file = stack.state / "seed.json"
    if not seed_file.exists():
        console.print(f"[red]{stack.name}: sin desplegar o sin cuentas; ejecuta uv run cli trapper up {stack.key}[/red]")
        raise typer.Exit(1)
    return json.loads(seed_file.read_text())


def _container(stack: Stack) -> str:
    return f"{stack.project}-trapper-1"


def _e2e_variables(stack: Stack, dataset: str) -> dict[str, str | None]:
    """Las variables ``WILDINTEL_*`` de los e2e para la instancia sembrada con ``dataset`` (``seed/e2e_env.py``)."""
    import warnings

    sys.path.insert(0, str(STACK_DIR / "seed"))
    from e2e_env import variables

    if not (stack.state / f"dataset{dataset}.json").exists():
        console.print(f"[yellow]{stack.name}: el dataset {dataset} no consta como sembrado; "
                      f"uv run cli trapper seed {stack.key} --dataset {dataset}[/yellow]")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        values = variables(stack.state.name, dataset)
    return {k: (None if v is None else str(v)) for k, v in values.items()}


@trapper_app.command("seed")
def trapper_seed(
    which: StackChoice = typer.Argument(StackChoice.all, help="Qué instancia sembrar."),
    dataset: str = typer.Option("all", "--dataset", "-d", help="1, 2 o all (los dos, en la misma instancia)."),
    port_offset: int = typer.Option(0, "--port-offset", help="El de la instancia (el mismo que le diste en up)."),
    name: str | None = NAME_OPTION,
) -> None:
    """Siembra un dataset de prueba (``dev/trapper/seed/dataset<N>.py``): se puede repetir, no duplica nada."""
    chosen = sorted(DATASETS) if dataset == "all" else [dataset]
    if not set(chosen) <= set(DATASETS):
        console.print(f"[red]Dataset «{dataset}» desconocido:[/red] {', '.join(DATASETS)} o all")
        raise typer.Exit(1)
    for stack in _stacks(which, port_offset, name):
        _ready(stack)
        url = f"http://localhost:{_ports(stack)['NGINX_PORT']}"
        for n in chosen:
            console.print(Panel(f"[bold]{stack.name}[/bold]  dataset {n}: {DATASETS[n]}", title="trapper seed"))
            result = subprocess.run(
                [sys.executable, str(STACK_DIR / "seed" / f"dataset{n}.py"), "--base-url", url,
                 "--container", _container(stack)],
                cwd=ROOT_DIR, capture_output=True, text=True,
            )
            lines = result.stdout.splitlines()
            for line in lines:
                if not line.startswith(f"DATASET{n}_JSON:"):
                    console.print(f"  {line}")
            done = next((l for l in lines if l.startswith(f"DATASET{n}_JSON:")), None)
            if result.returncode != 0 or done is None:
                console.print(f"[red]No se pudo sembrar el dataset {n} en {stack.name}:[/red]\n{result.stderr[-2000:]}")
                raise typer.Exit(1)
            (stack.state / f"dataset{n}.json").write_text(done.split(":", 1)[1])
            console.print(f"[green]✔  {stack.name}: dataset {n} listo[/green]\n")


@trapper_app.command("env")
def trapper_env(
    which: StackChoice = typer.Argument(StackChoice.v2),
    dataset: str | None = typer.Option(None, "--dataset", "-d", help="Con un dataset sembrado: todas las variables de sus e2e (pk de proyecto, colección, ...)."),
    port_offset: int = typer.Option(0, "--port-offset", help="El de la instancia (el mismo que le diste en up)."),
    name: str | None = NAME_OPTION,
) -> None:
    """Imprime las variables WILDINTEL_* para los tests e2e (``eval "$(uv run cli trapper env v2 --dataset 1)"``)."""
    for stack in _stacks(which, port_offset, name):
        data = _ready(stack)
        typer.echo(f"# {stack.name}" + (f", dataset {dataset}" if dataset else ""))
        if dataset:
            for key, value in _e2e_variables(stack, dataset).items():
                typer.echo(f"unset {key}" if value is None else f"export {key}={shlex.quote(value)}")
            continue
        typer.echo(f"export WILDINTEL_BASE_URL=http://localhost:{_ports(stack)['NGINX_PORT']}")
        typer.echo(f"export WILDINTEL_ACCESS_TOKEN={data['tokens']['sdktest']}")
        typer.echo("export WILDINTEL_USER_NAME=sdktest@example.org   # el email: v1 entra por email")
        typer.echo(f"export WILDINTEL_USER_PASSWORD={data['password']}")
        typer.echo("export WILDINTEL_SMOKE_ENABLED=1")
        typer.echo("export WILDINTEL_ALLOW_WRITE=1")
        typer.echo(f"export WILDINTEL_RPROJECT_PK={data['research_project']}")


@trapper_app.command("e2e", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def trapper_e2e(
    ctx: typer.Context,
    which: StackChoice = typer.Argument(StackChoice.all, help="Contra qué instancia (all: una tras otra)."),
    dataset: str = DATASET_OPTION,
    port_offset: int = typer.Option(0, "--port-offset", help="El de la instancia (el mismo que le diste en up)."),
    name: str | None = NAME_OPTION,
) -> None:
    """Lanza ``tests/e2e`` contra una instancia sembrada; lo que sigue a ``--`` va a pytest (``-- -k species -x``)."""
    failed = []
    for stack in _stacks(which, port_offset, name):
        _ready(stack)
        env = {k: v for k, v in os.environ.items() if not k.startswith("WILDINTEL_")}
        env.update({k: v for k, v in _e2e_variables(stack, dataset).items() if v is not None})
        console.print(Panel(f"[bold]{stack.name}[/bold]  dataset {dataset}  {env['WILDINTEL_BASE_URL']}", title="trapper e2e"))
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/e2e", *ctx.args], cwd=ROOT_DIR, env=env)
        if result.returncode != 0:
            failed.append(stack.name)
    if failed:
        console.print(f"[red]Con fallos: {', '.join(failed)}[/red]")
        raise typer.Exit(1)



# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
