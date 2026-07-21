"""
End-to-end tests for UserClassificationsComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_USER_CLASSIFICATION_PK  — pk of an existing user classification record
"""
from __future__ import annotations

import os

import pytest

from tests.base_component_tests import ComponentE2ETestBase
from trapper_client.api_query import APIQuery
from trapper_client.components.user_classifications import UserClassificationsComponent
from trapper_client.schemas import UserClassificationRecord


# ── tests heredados (get / get_all / where / find / export) ──────────────────

class TestUserClassificationsComponentE2E(ComponentE2ETestBase):
    component_class = UserClassificationsComponent
    schema = UserClassificationRecord
    export_schema = UserClassificationRecord
    env_pk_var = "WILDINTEL_USER_CLASSIFICATION_PK"

    # export() sin endpoint de results devuelve lo mismo que get_all;
    # la comprobación de conteo fila-a-fila del CSV heredada es válida
