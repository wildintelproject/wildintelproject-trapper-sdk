"""``uv run cli trapper``: image of a branch, the .env of an instance, and the commands that call Docker."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

import cli


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STATE_DIR", tmp_path / ".state")
    return tmp_path / ".state"


def stack(version="v2", offset=0):
    return cli.replace(cli.STACKS[version], offset=offset)


# -- the image of a branch ---------------------------------------------------

@pytest.mark.parametrize("branch, slug", [
    ("refactor/api-ninja", "refactor-api-ninja"), ("Feature/ABC_def", "feature-abc-def"),
    ("--x--", "x"), ("a" * 80, "a" * 63), ("main", "main"),
])
def test_the_slug_is_the_one_of_the_gitlab_ci(branch, slug):
    assert cli._slug(branch) == slug


def test_the_tag_as_given_is_tried_before_its_slug():
    assert cli._tag_candidates("2.0.0a2") == ["2.0.0a2", "2-0-0a2"]
    assert cli._tag_candidates("main") == ["main"]


def test_the_first_tag_that_exists_wins(monkeypatch):
    present = {f"{cli.TRAPPER_IMAGE_REPO}:refactor-api-ninja"}
    monkeypatch.setattr(cli, "_image_exists", lambda image: image in present)
    assert cli._resolve_image("refactor/api-ninja") == f"{cli.TRAPPER_IMAGE_REPO}:refactor-api-ninja"


def test_a_branch_with_no_image_is_an_error(monkeypatch):
    monkeypatch.setattr(cli, "_image_exists", lambda image: False)
    with pytest.raises(cli.typer.Exit):
        cli._resolve_image("nope")


def test_the_image_is_looked_for_locally_and_then_in_the_registry(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or MagicMock(returncode=1))
    assert cli._image_exists("x:y") is False
    assert [c[1] for c in calls] == ["image", "manifest"]


# -- the .env of an instance -------------------------------------------------

def test_the_env_has_the_image_the_ports_and_secrets(state):
    path = cli._write_env(stack("v2"), "img:tag")
    env = cli._read_env(path)
    assert env["TRAPPER_IMAGE"] == "img:tag" and env["COMPOSE_PROJECT_NAME"] == "wildintel-trapper-v2"
    assert (env["APP_PORT"], env["NGINX_PORT"], env["UPLOADER_PORT"]) == ("8100", "8180", "8188")
    assert all(len(env[k]) >= 20 for k in ("POSTGRES_PASSWORD", "RABBITMQ_PASSWORD", "TRAPPER_SECRET_KEY", "TUS_HOOK_SECRET"))


def test_the_secrets_are_kept_when_the_env_is_written_again(state):
    first = cli._read_env(cli._write_env(stack("v1"), "img:a"))
    second = cli._read_env(cli._write_env(stack("v1"), "img:b"))
    for key in ("POSTGRES_PASSWORD", "RABBITMQ_PASSWORD", "TRAPPER_SECRET_KEY", "TUS_HOOK_SECRET"):
        assert first[key] == second[key]          # the database was born with them
    assert second["TRAPPER_IMAGE"] == "img:b"


def test_an_instance_with_an_offset_is_a_separate_one(state):
    """Same project, volumes and state folder would make ``up --port-offset`` replace the other instance."""
    base, other = stack("v2"), stack("v2", 1000)
    assert other.project != base.project and other.state != base.state and other.name == "v2-p1000"
    env_base = cli._read_env(cli._write_env(base, "img:a"))
    env_other = cli._read_env(cli._write_env(other, "img:b"))
    assert env_other["COMPOSE_PROJECT_NAME"] == "wildintel-trapper-v2-p1000"
    assert env_other["NGINX_PORT"] == "9180" and env_base["NGINX_PORT"] == "8180"
    assert env_other["POSTGRES_PASSWORD"] != env_base["POSTGRES_PASSWORD"]      # each has its own database
    assert env_base["TRAPPER_IMAGE"] == "img:a"                                  # and writing one leaves the other alone


def test_the_two_versions_do_not_share_ports_or_project():
    one, two = stack("v1"), stack("v2")
    assert one.project != two.project
    assert not {one.app_port, one.nginx_port, one.uploader_port, one.rabbitmq_port} & \
        {two.app_port, two.nginx_port, two.uploader_port, two.rabbitmq_port}


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_every_compose_file_exists_and_names_the_services(version):
    text = stack(version).compose_file.read_text()
    for service in ("postgres:", "rabbitmq:", "memcached:", "trapper:", "trapper-celery:", "trapper_uploader:", "trapper-nginx:"):
        assert service in text
    assert "ai" not in [line.strip().rstrip(":") for line in text.splitlines() if line.startswith("  trapper-ai")]
    assert "frontend:" not in text


# -- commands that call Docker -----------------------------------------------

def test_compose_is_called_with_the_files_of_the_instance(state, monkeypatch):
    seen = []
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: seen.append((cmd, kw)) or MagicMock(returncode=0, stdout=""))
    cli._write_env(stack("v1"), "img:a")
    cli._compose(stack("v1"), "ps", "-q")
    cmd = seen[0][0]
    assert cmd[:2] == ["docker", "compose"] and str(stack("v1").compose_file) in cmd
    assert str(state / "v1" / ".env") in cmd and cmd[-2:] == ["ps", "-q"]


def test_down_does_nothing_for_an_instance_that_was_never_deployed(state, monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert CliRunner().invoke(cli.app, ["trapper", "down"]).exit_code == 0
    run.assert_not_called()


def test_destroy_asks_before_deleting(state, monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(cli.subprocess, "run", run)
    cli._write_env(stack("v1"), "img:a")
    result = CliRunner().invoke(cli.app, ["trapper", "destroy", "v1"], input="n\n")
    assert result.exit_code != 0
    run.assert_not_called()


def test_destroy_with_yes_removes_the_volumes(state, monkeypatch):
    seen = []
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: seen.append(cmd) or MagicMock(returncode=0))
    cli._write_env(stack("v1"), "img:a")
    assert CliRunner().invoke(cli.app, ["trapper", "destroy", "v1", "--yes"]).exit_code == 0
    assert seen[0][-2:] == ["down", "-v"]


def test_env_prints_the_variables_of_the_e2e_tests(state):
    cli._write_env(stack("v2"), "img:a")
    (state / "v2" / "seed.json").write_text(json.dumps({"password": "pw", "tokens": {"sdktest": "tok"}, "research_project": 4}))
    out = CliRunner().invoke(cli.app, ["trapper", "env", "v2"]).output
    assert "export WILDINTEL_BASE_URL=http://localhost:8180" in out
    assert "export WILDINTEL_ACCESS_TOKEN=tok" in out and "export WILDINTEL_USER_PASSWORD=pw" in out
    assert "export WILDINTEL_RPROJECT_PK=4" in out and "sdktest@example.org" in out


def test_env_without_accounts_says_how_to_get_them(state):
    result = CliRunner().invoke(cli.app, ["trapper", "env", "v1"])
    assert result.exit_code != 0 and "cli trapper up" in result.output


def test_a_port_that_is_in_use_stops_up_before_docker(state, monkeypatch):
    monkeypatch.setattr(cli, "_resolve_image", lambda branch: "img:a")
    monkeypatch.setattr(cli, "_busy", lambda port: True)
    monkeypatch.setattr(cli, "_compose", lambda *a, **k: MagicMock(returncode=0, stdout=""))
    result = CliRunner().invoke(cli.app, ["trapper", "up", "v1"])
    assert result.exit_code != 0 and "port-offset" in result.output


def test_the_seed_reads_the_json_line_and_keeps_the_tokens(state, monkeypatch):
    cli._write_env(stack("v1"), "img:a")
    payload = {"password": "pw", "tokens": {"sdktest": "t"}, "research_project": 1}
    monkeypatch.setattr(cli, "_compose", lambda *a, **k: MagicMock(returncode=0, stdout="x\nSEED_JSON:" + json.dumps(payload) + "\n", stderr=""))
    assert cli._seed_accounts(stack("v1")) == payload
    assert json.loads((state / "v1" / "seed.json").read_text()) == payload


def test_a_failed_seed_is_an_error(state, monkeypatch):
    cli._write_env(stack("v1"), "img:a")
    monkeypatch.setattr(cli, "_compose", lambda *a, **k: MagicMock(returncode=1, stdout="Traceback", stderr="boom"))
    with pytest.raises(cli.typer.Exit):
        cli._seed_accounts(stack("v1"))


@pytest.mark.parametrize("branch, v1, v2, expected_v1, expected_v2", [
    (None, None, None, "latest", "2.0.0a2"),                              # the defaults
    ("development", None, None, "development", "development"),            # one branch for the instances chosen
    ("development", "latest", None, "latest", "development"),             # a version's own wins
    (None, None, "refactor-api-ninja", "latest", "refactor-api-ninja"),
    ("a", "b", "c", "b", "c"),
])
def test_the_branch_of_each_version(branch, v1, v2, expected_v1, expected_v2):
    assert cli._branch_for(stack("v1"), branch, v1, v2) == expected_v1
    assert cli._branch_for(stack("v2"), branch, v1, v2) == expected_v2


def test_up_deploys_the_image_of_the_branch_it_is_given(state, monkeypatch):
    resolved = []
    monkeypatch.setattr(cli, "_resolve_image", lambda branch: resolved.append(branch) or f"img:{branch}")
    monkeypatch.setattr(cli, "_busy", lambda port: False)
    monkeypatch.setattr(cli, "_compose", lambda *a, **k: MagicMock(returncode=0, stdout=""))
    monkeypatch.setattr(cli, "_wait_for", lambda url, timeout: True)
    monkeypatch.setattr(cli, "_seed_accounts", lambda stack: {"research_project": 1})
    result = CliRunner().invoke(cli.app, ["trapper", "up", "all", "--v2-branch", "refactor/api-ninja", "--branch", "development"])
    assert result.exit_code == 0, result.output
    assert resolved == ["development", "refactor/api-ninja"]
    assert cli._read_env(state / "v1" / ".env")["TRAPPER_IMAGE"] == "img:development"
    assert cli._read_env(state / "v2" / ".env")["TRAPPER_IMAGE"] == "img:refactor/api-ninja"


def test_each_instance_has_its_own_subnet_in_the_env_and_the_compose_files(state):
    names = {cli.replace(cli.STACKS[v], offset=o).subnet for v in ("v1", "v2") for o in (0, 1000, 2000)}
    assert len(names) == 6 and all(n.startswith("10.77.") and n.endswith(".0/24") for n in names)
    assert cli._read_env(cli._write_env(stack("v1"), "img:a"))["NETWORK_SUBNET"] == stack("v1").subnet
    for version in ("v1", "v2"):
        assert "${NETWORK_SUBNET}" in stack(version).compose_file.read_text()
