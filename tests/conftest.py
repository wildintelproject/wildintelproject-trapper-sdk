from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import pytest

from trapper_client import APIClientBase

load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trapper_client.trapper_client import TrapperClient


def _env_true(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests with no HTTP calls")
    config.addinivalue_line("markers", "integration: Integration tests with mocked HTTP")
    config.addinivalue_line("markers", "e2e: End-to-end tests against a real Trapper server")


def pytest_collection_modifyitems(config, items):
    e2e_enabled = _env_true(os.getenv("WILDINTEL_SMOKE_ENABLED"))

    skip_e2e = pytest.mark.skip(reason="Set WILDINTEL_SMOKE_ENABLED=1 to run e2e tests")

    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker("unit")
        elif "integration" in str(item.fspath):
            item.add_marker("integration")
        elif "e2e" in str(item.fspath) or "e2e" in item.keywords:
            if not e2e_enabled:
                item.add_marker(skip_e2e)


@pytest.fixture
def real_client() -> TrapperClient:
    base_url = os.getenv("WILDINTEL_BASE_URL", "").strip()
    token = os.getenv("WILDINTEL_ACCESS_TOKEN", "").strip()
    user_name = os.getenv("WILDINTEL_USER_NAME", "").strip()
    user_password = os.getenv("WILDINTEL_USER_PASSWORD", "").strip()
    verify_ssl = _env_true(os.getenv("WILDINTEL_VERIFY_SSL", "1"))
    timeout = int(os.getenv("WILDINTEL_TIMEOUT", "30"))

    if not base_url:
        pytest.skip("Missing WILDINTEL_BASE_URL for e2e tests")

    if not token and not (user_name and user_password):
        pytest.skip("Set WILDINTEL_ACCESS_TOKEN or WILDINTEL_USER_NAME/WILDINTEL_USER_PASSWORD")

    return TrapperClient(
        access_token=token or None,
        user_name=user_name or None,
        user_password=user_password or None,
        verify_ssl=verify_ssl,
        base_url=base_url,
        timeout=timeout,
    )

@pytest.fixture(scope="session")
def real_api_base() -> APIClientBase:
    base_url = os.getenv("WILDINTEL_BASE_URL", "").strip()
    token = os.getenv("WILDINTEL_ACCESS_TOKEN", "").strip()
    user_name = os.getenv("WILDINTEL_USER_NAME", "").strip()
    user_password = os.getenv("WILDINTEL_USER_PASSWORD", "").strip()
    verify_ssl = _env_true(os.getenv("WILDINTEL_VERIFY_SSL", "1"))
    timeout = int(os.getenv("WILDINTEL_TIMEOUT", "30"))

    if not base_url:
        pytest.skip("Missing WILDINTEL_BASE_URL for e2e tests")

    if not token and not (user_name and user_password):
        pytest.skip("Set WILDINTEL_ACCESS_TOKEN or WILDINTEL_USER_NAME/WILDINTEL_USER_PASSWORD")

    return APIClientBase(
        access_token=token or None,
        user_name=user_name or None,
        user_password=user_password or None,
        verify_ssl=verify_ssl,
        base_url=base_url,
        timeout=timeout,
    )


