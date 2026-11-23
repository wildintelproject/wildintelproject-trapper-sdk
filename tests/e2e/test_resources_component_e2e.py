"""
End-to-end tests for ResourcesComponent against a real Trapper server.

Requires environment variables:
    WILDINTEL_BASE_URL, WILDINTEL_ACCESS_TOKEN, WILDINTEL_SMOKE_ENABLED=1

Optional:
    WILDINTEL_RESOURCE_PK     — pk of an existing resource
    WILDINTEL_COLLECTION_PK   — pk of an existing collection
    WILDINTEL_LOCATION_PK     — pk of an existing location
"""
from __future__ import annotations

import os

import pytest

from tests.base_component_tests import ComponentE2ETestBase, assert_page_size_respected
from trapper_client.api_query import APIQuery
from trapper_client.components.resources import ResourcesComponent
from trapper_client.schemas import PaginatedResult, Resource


# ── tests heredados ───────────────────────────────────────────────────────────

class TestResourcesComponentE2E(ComponentE2ETestBase):
    component_class = ResourcesComponent
    schema = Resource
    export_schema = Resource
    env_pk_var = "WILDINTEL_RESOURCE_PK"


# ── helpers ───────────────────────────────────────────────────────────────────

def _collection_pk() -> str:
    return os.getenv("WILDINTEL_COLLECTION_PK", "").strip()


def _location_pk() -> str:
    return os.getenv("WILDINTEL_LOCATION_PK", "").strip()


def _resource_pk() -> str:
    return os.getenv("WILDINTEL_RESOURCE_PK", "").strip()


# ── tests sub-endpoint /collection ───────────────────────────────────────────

class TestResourcesByCollectionE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ResourcesComponent(real_api_base)

    # ── where_by_collection ───────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_by_collection_returns_api_query(self, component):
        """where_by_collection() devuelve un APIQuery."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.where_by_collection(int(pk), page_size=5)
        assert isinstance(result, APIQuery)

    @pytest.mark.e2e
    def test_where_by_collection_iterates_resource_instances(self, component):
        """Iterar where_by_collection() devuelve instancias de Resource."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        items = []
        for res in component.where_by_collection(int(pk), page_size=10):
            items.append(res)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No resources available for this collection")

        assert all(isinstance(res, Resource) for res in items)

    @pytest.mark.e2e
    def test_where_by_collection_context_manager_exhausts_on_exit(self, component):
        """where_by_collection() como context manager queda exhausto al salir."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        with component.where_by_collection(int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    @pytest.mark.e2e
    def test_where_by_collection_passes_filter_fn(self, component):
        """where_by_collection() con filter_fn filtra los resultados."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        all_items = list(component.where_by_collection(int(pk), page_size=50))
        if not all_items:
            pytest.skip("No resources available for this collection")

        target_pk = all_items[0].pk
        filtered = list(component.where_by_collection(
            int(pk),
            page_size=50,
            filter_fn=lambda res: res.pk == target_pk,
        ))

        assert len(filtered) == 1
        assert filtered[0].pk == target_pk

    # ── get_by_collection ─────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_by_collection_returns_paginated_result(self, component):
        """get_by_collection() devuelve PaginatedResult."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_by_collection(int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_by_collection_returns_resource_instances(self, component):
        """get_by_collection() devuelve instancias de Resource."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_by_collection(int(pk), page_size=5)

        if not result.results:
            pytest.skip("No resources available for this collection")

        assert all(isinstance(res, Resource) for res in result.results)

    @pytest.mark.e2e
    def test_get_by_collection_page_size_respected(self, component):
        """get_by_collection() respeta el page_size solicitado."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_by_collection(int(pk), page_size=3)
        assert len(result.results) <= 3

    # ── get_all_by_collection ─────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_all_by_collection_count_matches_pagination(self, component):
        """get_all_by_collection() devuelve tantos items como indica pagination.count."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_all_by_collection(int(pk), page_size=50)
        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_get_all_by_collection_no_duplicate_pks(self, component):
        """get_all_by_collection() no devuelve items duplicados entre páginas."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        result = component.get_all_by_collection(int(pk), page_size=10)
        if not result.results:
            pytest.skip("No resources available for this collection")

        pks = [res.pk for res in result.results]
        assert len(pks) == len(set(pks))

    # ── find_by_collection ────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_by_collection_returns_resource(self, component):
        """find_by_collection() devuelve la instancia de Resource correcta."""
        collection_pk = _collection_pk()
        resource_pk = _resource_pk()
        if not collection_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_collection(int(collection_pk), int(resource_pk))

        assert isinstance(result, Resource)
        assert result.pk == int(resource_pk)

    @pytest.mark.e2e
    def test_find_by_collection_validate_false_returns_model(self, component):
        """find_by_collection() con validate=False devuelve modelo sin validar."""
        collection_pk = _collection_pk()
        resource_pk = _resource_pk()
        if not collection_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_collection(
            int(collection_pk), int(resource_pk), validate=False
        )
        assert isinstance(result, Resource)

    @pytest.mark.e2e
    def test_find_by_collection_nonexistent_raises(self, component):
        """find_by_collection() lanza excepción para resource_pk inexistente."""
        pk = _collection_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_COLLECTION_PK to run this test")

        with pytest.raises(Exception):
            component.find_by_collection(int(pk), 999999999)


# ── tests sub-endpoint /location ──────────────────────────────────────────────

class TestResourcesByLocationE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ResourcesComponent(real_api_base)

    # ── where_by_location ─────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_where_by_location_returns_api_query(self, component):
        """where_by_location() devuelve un APIQuery."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.where_by_location(int(pk), page_size=5)
        assert isinstance(result, APIQuery)

    @pytest.mark.e2e
    def test_where_by_location_iterates_resource_instances(self, component):
        """Iterar where_by_location() devuelve instancias de Resource."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        items = []
        for res in component.where_by_location(int(pk), page_size=10):
            items.append(res)
            if len(items) >= 5:
                break

        if not items:
            pytest.skip("No resources available for this location")

        assert all(isinstance(res, Resource) for res in items)

    @pytest.mark.e2e
    def test_where_by_location_context_manager_exhausts_on_exit(self, component):
        """where_by_location() como context manager queda exhausto al salir."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        with component.where_by_location(int(pk), page_size=5) as query:
            next(query, None)

        assert query._exhausted is True

    # ── get_by_location ───────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_by_location_returns_paginated_result(self, component):
        """get_by_location() devuelve PaginatedResult."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_by_location(int(pk), page_size=5)

        assert isinstance(result, PaginatedResult)
        assert result.pagination.page == 1

    @pytest.mark.e2e
    def test_get_by_location_returns_resource_instances(self, component):
        """get_by_location() devuelve instancias de Resource."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_by_location(int(pk), page_size=5)

        if not result.results:
            pytest.skip("No resources available for this location")

        assert all(isinstance(res, Resource) for res in result.results)

    @pytest.mark.e2e
    def test_get_by_location_page_size_respected(self, component):
        """get_by_location() respeta el page_size solicitado."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_by_location(int(pk), page_size=3)
        assert_page_size_respected(result, 3)

    # ── get_all_by_location ───────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_get_all_by_location_count_matches_pagination(self, component):
        """get_all_by_location() devuelve tantos items como indica pagination.count."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_all_by_location(int(pk), page_size=50)
        assert len(result.results) == result.pagination.count

    @pytest.mark.e2e
    def test_get_all_by_location_no_duplicate_pks(self, component):
        """get_all_by_location() no devuelve items duplicados entre páginas."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        result = component.get_all_by_location(int(pk), page_size=10)
        if not result.results:
            pytest.skip("No resources available for this location")

        pks = [res.pk for res in result.results]
        assert len(pks) == len(set(pks))

    # ── find_by_location ──────────────────────────────────────────────────────

    @pytest.mark.e2e
    def test_find_by_location_returns_resource(self, component):
        """find_by_location() devuelve la instancia de Resource correcta."""
        location_pk = _location_pk()
        resource_pk = _resource_pk()
        if not location_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_location(int(location_pk), int(resource_pk))

        assert isinstance(result, Resource)
        assert result.pk == int(resource_pk)

    @pytest.mark.e2e
    def test_find_by_location_validate_false_returns_model(self, component):
        """find_by_location() con validate=False devuelve modelo sin validar."""
        location_pk = _location_pk()
        resource_pk = _resource_pk()
        if not location_pk or not resource_pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK and WILDINTEL_RESOURCE_PK to run this test")

        result = component.find_by_location(
            int(location_pk), int(resource_pk), validate=False
        )
        assert isinstance(result, Resource)

    @pytest.mark.e2e
    def test_find_by_location_nonexistent_raises(self, component):
        """find_by_location() lanza excepción para resource_pk inexistente."""
        pk = _location_pk()
        if not pk:
            pytest.skip("Set WILDINTEL_LOCATION_PK to run this test")

        with pytest.raises(Exception):
            component.find_by_location(int(pk), 999999999)

class TestResourceDatesE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ResourcesComponent(real_api_base)

    @pytest.mark.e2e
    def test_date_recorded_is_an_aware_datetime(self, component):
        from datetime import datetime

        page = component.get(page_size=20)
        if not page.results:
            pytest.skip("No resources on this server")
        for res in page.results:
            assert isinstance(res.date_recorded, datetime) and res.date_recorded.tzinfo is not None, res.date_recorded
        ordered = sorted(page.results, key=lambda r: r.date_recorded)
        assert ordered[0].date_recorded <= ordered[-1].date_recorded


# ── download ──────────────────────────────────────────────────────────────────

class TestResourceDownloadE2E:
    """``download()`` needs the web session, so it needs ``WILDINTEL_USER_NAME``/``WILDINTEL_USER_PASSWORD``."""

    @pytest.fixture(scope="class")
    def session_client(self):
        from trapper_client import TrapperClient

        if os.getenv("WILDINTEL_SMOKE_ENABLED", "").strip() != "1":
            pytest.skip("Set WILDINTEL_SMOKE_ENABLED=1")
        user, password = os.getenv("WILDINTEL_USER_NAME", "").strip(), os.getenv("WILDINTEL_USER_PASSWORD", "").strip()
        if not (user and password):
            pytest.skip("Set WILDINTEL_USER_NAME and WILDINTEL_USER_PASSWORD (the web session is needed to download)")
        return TrapperClient(
            base_url=os.environ["WILDINTEL_BASE_URL"],
            access_token=os.environ["WILDINTEL_ACCESS_TOKEN"],
            user_name=user,
            user_password=password,
        )

    @pytest.mark.e2e
    def test_download_the_original(self, session_client, tmp_path):
        """The original of a resource is saved with the size of the file, or the server says why not."""
        from trapper_client import err

        page = session_client.resources.get(page_size=1)
        if not page.results:
            pytest.skip("No resources on this server")
        try:
            path = session_client.resources.download(page.results[0].pk, tmp_path)
        except err.APIError as exc:
            if "proxy" in str(exc):
                pytest.skip("this Trapper is not behind the proxy that serves its files (X-Accel-Redirect)")
            raise
        assert path.parent == tmp_path and path.stat().st_size > 0
        assert [p.name for p in tmp_path.iterdir()] == [path.name]       # no .part left
        assert path.read_bytes()[:3] in (b"\xff\xd8\xff", b"\x89PN", b"GIF")

    @pytest.mark.e2e
    def test_a_resource_that_does_not_exist_is_not_found(self, session_client, tmp_path):
        from trapper_client import err

        with pytest.raises(err.NotFoundError):
            session_client.resources.download(999999999, tmp_path / "x.jpg")
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.e2e
    def test_the_token_alone_cannot_download(self, real_api_base, tmp_path):
        """Without ``user_name``/``user_password`` it says so before any request for the file."""
        client = real_api_base
        if getattr(client, "user_name", None) and getattr(client, "user_password", None):
            pytest.skip("this client has credentials")
        with pytest.raises(ValueError, match="user_name"):
            ResourcesComponent(client).download(1, tmp_path / "x.jpg")


# ── list filters ──────────────────────────────────────────────────────────────

class TestResourceFiltersE2E:

    @pytest.fixture(scope="class")
    def component(self, real_api_base):
        return ResourcesComponent(real_api_base)

    @staticmethod
    def count(component, **filters) -> int:
        return component.get(page_size=1, **filters).pagination.count

    @pytest.mark.e2e
    def test_lists_and_comma_strings_filter_the_same_way(self, component):
        """Every spelling of a list filter gives the same result, instead of ignoring it or failing."""
        everything = list(component.where(page_size=100))
        if len(everything) < 3:
            pytest.skip("Not enough resources on this server")
        pks = [r.pk for r in everything[:3]]
        assert self.count(component, pk=pks) == 3
        assert self.count(component, pk=",".join(map(str, pks))) == 3

        deployments = sorted({d for d in (self._deployment_of(component, r.pk) for r in everything[:6]) if d})
        if len(deployments) >= 2:
            as_list = self.count(component, deployments=deployments)
            assert as_list == self.count(component, deployments=",".join(map(str, deployments)))
            assert as_list < len(everything)             # it filters: "1,2" used to be ignored and gave everything

    @staticmethod
    def _deployment_of(component, resource_pk):
        """The deployment of a resource, found through the deployments filter (the list does not say)."""
        from trapper_client.components.deployments import DeploymentsComponent

        for dep in DeploymentsComponent(component.client).where(page_size=100):
            if component.get(page_size=1, pk=resource_pk, deployments=dep.pk).pagination.count:
                return dep.pk
        return None

    @pytest.mark.e2e
    def test_collections_as_list_or_string_agree(self, component):
        from trapper_client.components.collections import CollectionsComponent

        pks = [c.pk for c in CollectionsComponent(component.client).where(page_size=10)][:2]
        if len(pks) < 2:
            pytest.skip("Fewer than two collections on this server")
        assert self.count(component, collections=pks) == self.count(component, collections=",".join(map(str, pks)))
        assert self.count(component, collections=pks) >= self.count(component, collections=pks[0])

    @pytest.mark.e2e
    def test_unknown_filters_warn_and_known_ones_do_not(self, component):
        import warnings

        from trapper_client import err

        with warnings.catch_warnings():
            warnings.simplefilter("error", err.UnknownFilterWarning)
            total = self.count(component)
            assert self.count(component, name="zzz-no-such-resource") == 0
        with pytest.warns(err.UnknownFilterWarning):
            ignored = component.get(page_size=1, ordering="-pk", radius="0,0,1")
        assert ignored.pagination.count == total

    @pytest.mark.e2e
    def test_deployment_isnull_is_still_a_server_error(self, component):
        """The warning says Trapper answers 500: if this stops failing, the warning has to go."""
        from trapper_client import err

        with pytest.warns(err.UnknownFilterWarning, match="500"), pytest.raises(err.APIError):
            component.get(page_size=1, deployment__isnull=True)


class TestDownloadResourcesE2E:
    """``deployments.download_resources()`` and ``collections.download_resources()`` need the web session."""

    @pytest.fixture(scope="class")
    def session_client(self):
        from trapper_client import TrapperClient

        if os.getenv("WILDINTEL_SMOKE_ENABLED", "").strip() != "1":
            pytest.skip("Set WILDINTEL_SMOKE_ENABLED=1")
        user, password = os.getenv("WILDINTEL_USER_NAME", "").strip(), os.getenv("WILDINTEL_USER_PASSWORD", "").strip()
        if not (user and password):
            pytest.skip("Set WILDINTEL_USER_NAME and WILDINTEL_USER_PASSWORD (the web session is needed to download)")
        return TrapperClient(
            base_url=os.environ["WILDINTEL_BASE_URL"], access_token=os.environ["WILDINTEL_ACCESS_TOKEN"],
            user_name=user, user_password=password,
        )

    @staticmethod
    def _skip_without_proxy(report):
        if any("proxy" in message for message in report.failed.values()):
            pytest.skip("this Trapper is not behind the proxy that serves its files (X-Accel-Redirect)")

    @pytest.mark.e2e
    def test_a_deployment_is_downloaded_with_a_filter_and_repeated(self, session_client, tmp_path):
        client = session_client
        found = None
        for deployment in client.deployments.where(page_size=50):
            resources = list(client.resources.where(deployments=deployment.pk, page_size=50))
            if len(resources) >= 2:
                found = deployment, resources
                break
        if not found:
            pytest.skip("No deployment with two resources on this server")
        deployment, resources = found

        everything = client.deployments.download_resources(deployment.pk, tmp_path)
        self._skip_without_proxy(everything)
        assert everything.ok and len(everything.downloaded) == len(resources)
        assert everything.directory == tmp_path / deployment.deployment_id
        assert all(p.stat().st_size > 0 for p in everything.downloaded)

        again = client.deployments.download_resources(deployment.pk, tmp_path)
        assert again.downloaded == [] and len(again.skipped) == len(resources)

        # a filter of the resource list chooses which ones (a list of pks), a filter_fn does it on the client
        chosen = [r.pk for r in resources[:2]]
        some = client.deployments.download_resources(deployment.pk, tmp_path / "some", pk=chosen)
        assert len(some.downloaded) == 2
        one = client.deployments.download_resources(deployment.pk, tmp_path / "one", filter_fn=lambda r: r.pk == chosen[0])
        assert len(one.downloaded) == 1

    @pytest.mark.e2e
    def test_a_collection_is_downloaded(self, session_client, tmp_path):
        client = session_client
        collection = next((c for c in client.collections.where(page_size=50)
                           if client.resources.get_by_collection(c.pk, page_size=1).pagination.count), None)
        if collection is None:
            pytest.skip("No collection with resources on this server")
        count = client.resources.get_by_collection(collection.pk, page_size=1).pagination.count
        events: list[str] = []
        report = client.collections.download_resources(
            collection.pk, tmp_path, progress_callback=lambda event, data: events.append(event))
        self._skip_without_proxy(report)
        assert report.ok and len(report.downloaded) == count and events == ["downloaded"] * count
