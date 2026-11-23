"""``download_many()`` and ``deployments``/``collections`` ``.download_resources()``."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.base_component_tests import paginated_response
from trapper_client import Collection, Deployment, Resource, err
from trapper_client.components.collections import CollectionsComponent
from trapper_client.components.deployments import DeploymentsComponent
from trapper_client.components.resources import DownloadReport, ResourcesComponent, safe_filename


def res(pk, name=None, mime="image/jpeg"):
    return Resource(pk=pk, name=name if name is not None else f"img{pk}", mime=mime)


@pytest.fixture
def resources(monkeypatch):
    """A resources component whose ``download()`` writes the pk into the file, and fails for ``comp.fail``."""
    comp = ResourcesComponent(MagicMock())
    comp.fail = {}
    comp.calls = []

    def download(pk, file, kind="original", **kw):
        comp.calls.append((pk, file.name, kind))
        if pk in comp.fail:
            raise comp.fail[pk]
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(str(pk))
        return file

    comp.download = download
    return comp


class TestFileNames:

    @pytest.mark.parametrize("name, mime, expected", [
        ("img", "image/jpeg", "img.jpg"),
        ("img.jpg", "image/jpeg", "img.jpg"),
        ("IMG.JPG", "image/jpeg", "IMG.JPG"),
        ("clip", "video/mp4", "clip.mp4"),
        ("pic", "image/png", "pic.png"),
        ("noext", None, "noext"),
        ("odd mime", "application/x-nothing", "odd mime"),
        ("a/b:c", "image/jpeg", "a_b_c.jpg"),
        ("", "image/jpeg", "resource-7.jpg"),
        ("..", "image/jpeg", "resource-7.jpg"),
    ])
    def test_name_and_extension(self, resources, tmp_path, name, mime, expected):
        resources.download_many([Resource(pk=7, name=name, mime=mime)], tmp_path)
        assert resources.calls[0][1] == expected

    def test_a_preview_or_a_thumbnail_is_a_jpg(self, resources, tmp_path):
        resources.download_many([res(1, "clip", "video/mp4")], tmp_path, kind="thumbnail")
        assert resources.calls[0][1:] == ("clip-thumbnail.jpg", "thumbnail")

    def test_two_resources_with_the_same_name_do_not_overwrite_each_other(self, resources, tmp_path):
        report = resources.download_many([res(1, "same"), res(2, "same"), res(3, "SAME")], tmp_path)
        assert sorted(p.name for p in report.downloaded) == ["SAME-3.jpg", "same-2.jpg", "same.jpg"]

    def test_safe_filename(self):
        assert safe_filename('x\\y/z') == "x_y_z" and safe_filename("  .a. ") == "a" and safe_filename(None) == "resource"


class TestDownloadMany:

    def test_downloads_into_the_folder_and_reports(self, resources, tmp_path):
        report = resources.download_many([res(1), res(2)], tmp_path / "new" / "dir")
        assert isinstance(report, DownloadReport) and report.ok
        assert [p.name for p in report.downloaded] == ["img1.jpg", "img2.jpg"]
        assert (tmp_path / "new" / "dir" / "img2.jpg").read_text() == "2"
        assert report.total == 2 and "2 downloaded" in str(report)

    def test_what_is_already_there_is_skipped(self, resources, tmp_path):
        (tmp_path / "img1.jpg").write_text("old")
        report = resources.download_many([res(1), res(2)], tmp_path)
        assert [p.name for p in report.skipped] == ["img1.jpg"] and [p.name for p in report.downloaded] == ["img2.jpg"]
        assert (tmp_path / "img1.jpg").read_text() == "old" and [c[0] for c in resources.calls] == [2]

    def test_skip_existing_can_be_turned_off(self, resources, tmp_path):
        (tmp_path / "img1.jpg").write_text("old")
        resources.download_many([res(1)], tmp_path, skip_existing=False)
        assert (tmp_path / "img1.jpg").read_text() == "1"

    def test_a_second_run_downloads_nothing(self, resources, tmp_path):
        resources.download_many([res(1), res(2)], tmp_path)
        again = resources.download_many([res(1), res(2)], tmp_path)
        assert again.downloaded == [] and len(again.skipped) == 2

    def test_a_failure_does_not_stop_the_rest(self, resources, tmp_path):
        resources.fail = {2: err.NotFoundError("gone")}
        report = resources.download_many([res(1), res(2), res(3)], tmp_path)
        assert [p.name for p in report.downloaded] == ["img1.jpg", "img3.jpg"]
        assert report.failed == {2: "gone"} and not report.ok

    def test_on_error_raise_stops_at_the_first(self, resources, tmp_path):
        resources.fail = {2: err.NotFoundError("gone")}
        with pytest.raises(err.NotFoundError):
            resources.download_many([res(1), res(2), res(3)], tmp_path, on_error="raise")
        assert [c[0] for c in resources.calls] == [1, 2]

    def test_a_failed_file_is_tried_again_in_the_next_run(self, resources, tmp_path):
        resources.fail = {2: err.NotFoundError("gone")}
        resources.download_many([res(1), res(2)], tmp_path)
        resources.fail = {}
        again = resources.download_many([res(1), res(2)], tmp_path)
        assert [p.name for p in again.downloaded] == ["img2.jpg"] and [p.name for p in again.skipped] == ["img1.jpg"]

    def test_the_callback_hears_about_every_file(self, resources, tmp_path):
        (tmp_path / "img2.jpg").write_text("x")
        resources.fail = {3: err.NotFoundError("gone")}
        events = []
        resources.download_many([res(1), res(2), res(3)], tmp_path, total=3,
                                progress_callback=lambda e, d: events.append((e, d["index"], d["total"], d["resource"].pk)))
        assert events == [("downloaded", 1, 3, 1), ("skipped", 2, 3, 2), ("failed", 3, 3, 3)]

    def test_the_callback_gets_the_error(self, resources, tmp_path):
        resources.fail = {1: err.NotFoundError("gone")}
        seen = {}
        resources.download_many([res(1)], tmp_path, progress_callback=lambda e, d: seen.update(d))
        assert str(seen["error"]) == "gone" and seen["path"].name == "img1.jpg"

    def test_an_original_and_its_thumbnail_share_a_folder_and_skip_on_their_own(self, resources, tmp_path):
        resources.download_many([res(1)], tmp_path)
        thumbs = resources.download_many([res(1)], tmp_path, kind="thumbnail")
        assert [p.name for p in thumbs.downloaded] == ["img1-thumbnail.jpg"]
        again = resources.download_many([res(1)], tmp_path, kind="thumbnail")
        assert [p.name for p in again.skipped] == ["img1-thumbnail.jpg"] and again.downloaded == []

    def test_it_takes_a_lazy_iterator(self, resources, tmp_path):
        report = resources.download_many((res(i) for i in (1, 2, 3)), tmp_path)
        assert len(report.downloaded) == 3

    def test_the_session_is_opened_once_and_options_are_passed_on(self, resources, tmp_path):
        resources.download = MagicMock(side_effect=lambda pk, file, **kw: file.write_text("x") or file)
        resources.download_many([res(1)], tmp_path, retry_attempts=5, retry_min_wait=2, retry_max_wait=9)
        resources.client.session_login.assert_called_once()
        assert resources.download.call_args.kwargs == {"kind": "original", "retry_attempts": 5, "retry_min_wait": 2, "retry_max_wait": 9}

    @pytest.mark.parametrize("kwargs", [{"kind": "big"}, {"on_error": "ignore"}])
    def test_wrong_options_are_refused_before_any_request(self, resources, tmp_path, kwargs):
        with pytest.raises(ValueError):
            resources.download_many([res(1)], tmp_path, **kwargs)
        assert resources.calls == [] and not resources.client.session_login.called

    def test_missing_credentials_are_reported(self, resources, tmp_path):
        resources.client.session_login.side_effect = ValueError("session_login() requires user_name/user_password")
        with pytest.raises(ValueError, match="user_name"):
            resources.download_many([res(1)], tmp_path)


class TestDeploymentAndCollection:

    @pytest.fixture
    def setup(self, monkeypatch, tmp_path):
        client = MagicMock()
        seen = {}

        def where(self, query=None, filter_fn=None, **kw):
            seen["where"] = (filter_fn, kw)
            return iter([r for r in (res(1), res(2), res(3)) if filter_fn is None or filter_fn(r)])

        def where_by_collection(self, collection_pk, filter_fn=None, **kw):
            seen["where_by_collection"] = (collection_pk, filter_fn, kw)
            return iter([r for r in (res(4), res(5)) if filter_fn is None or filter_fn(r)])

        def get(self, **kw):
            seen["get"] = kw
            return SimpleNamespace(pagination=SimpleNamespace(count=1))

        def get_by_collection(self, collection_pk, **kw):
            seen["get_by_collection"] = (collection_pk, kw)
            return SimpleNamespace(pagination=SimpleNamespace(count=1))

        def download(self, pk, file, **kw):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(str(pk))
            return file

        for name, fn in (("where", where), ("where_by_collection", where_by_collection), ("get", get),
                         ("get_by_collection", get_by_collection), ("download", download)):
            monkeypatch.setattr(f"trapper_client.components.resources.ResourcesComponent.{name}", fn)
        return client, seen

    def test_a_deployment_goes_into_its_own_folder(self, setup, tmp_path):
        client, seen = setup
        comp = DeploymentsComponent(client)
        comp.find = lambda pk: Deployment(pk=pk, deployment_id="don 01/a")
        report = comp.download_resources(12, tmp_path, resource_type="I", tags=[1])
        assert report.directory == tmp_path / "don 01_a" and len(report.downloaded) == 3
        assert seen["where"][1] == {"deployments": 12, "page_size": 100, "resource_type": "I", "tags": [1]}

    def test_the_filters_and_the_total(self, setup, tmp_path):
        client, seen = setup
        comp = DeploymentsComponent(client)
        comp.find = lambda pk: Deployment(pk=pk, deployment_id="d")
        events = []
        comp.download_resources(12, tmp_path, rdate_from="2024-01-01", progress_callback=lambda e, d: events.append(d["total"]))
        assert seen["get"] == {"page_size": 1, "deployments": 12, "rdate_from": "2024-01-01"} and events[0] == 1

    def test_filter_fn_chooses_which_and_the_total_is_unknown(self, setup, tmp_path):
        client, seen = setup
        comp = DeploymentsComponent(client)
        comp.find = lambda pk: Deployment(pk=pk, deployment_id="d")
        events = []
        report = comp.download_resources(12, tmp_path, filter_fn=lambda r: r.pk != 2, progress_callback=lambda e, d: events.append(d["total"]))
        assert sorted(p.name for p in report.downloaded) == ["img1.jpg", "img3.jpg"] and set(events) == {None}
        assert "get" not in seen

    def test_the_pk_of_the_resource_list_is_a_filter_not_the_deployment(self, setup, tmp_path):
        client, seen = setup
        comp = DeploymentsComponent(client)
        comp.find = lambda pk: Deployment(pk=pk, deployment_id="d")
        comp.download_resources(deployment_pk=12, directory=tmp_path, pk=[1, 2])
        assert seen["where"][1]["deployments"] == 12 and seen["where"][1]["pk"] == [1, 2]
        coll = CollectionsComponent(client)
        coll.find = lambda pk: Collection(pk=pk, name="c")
        coll.download_resources(collection_pk=5, directory=tmp_path, pk=[4])
        assert seen["where_by_collection"][0] == 5 and seen["where_by_collection"][2]["pk"] == [4]

    def test_a_deployment_cannot_be_combined_with_deployments(self, setup, tmp_path):
        comp = DeploymentsComponent(setup[0])
        with pytest.raises(ValueError, match="deployments"):
            comp.download_resources(12, tmp_path, deployments=[1])

    def test_a_collection_goes_into_a_folder_with_its_name(self, setup, tmp_path):
        client, seen = setup
        comp = CollectionsComponent(client)
        comp.find = lambda pk: Collection(pk=pk, name="Doñana primavera 2024")
        report = comp.download_resources(5, tmp_path, deployments=[12, 13], resource_type="I")
        assert report.directory == tmp_path / "Doñana primavera 2024" and len(report.downloaded) == 2
        assert seen["where_by_collection"][0] == 5
        assert seen["where_by_collection"][2] == {"page_size": 100, "deployments": [12, 13], "resource_type": "I"}

    def test_a_collection_with_filter_fn(self, setup, tmp_path):
        client, _ = setup
        comp = CollectionsComponent(client)
        comp.find = lambda pk: Collection(pk=pk, name="c")
        report = comp.download_resources(5, tmp_path, filter_fn=lambda r: r.pk == 5)
        assert [p.name for p in report.downloaded] == ["img5.jpg"]

    def test_options_reach_the_engine(self, setup, tmp_path):
        client, _ = setup
        comp = CollectionsComponent(client)
        comp.find = lambda pk: Collection(pk=pk, name="c")
        (tmp_path / "c").mkdir()
        (tmp_path / "c" / "img4.jpg").write_text("old")
        report = comp.download_resources(5, tmp_path)
        assert [p.name for p in report.skipped] == ["img4.jpg"]
        thumbs = comp.download_resources(5, tmp_path, kind="thumbnail")
        assert sorted(p.name for p in thumbs.downloaded) == ["img4-thumbnail.jpg", "img5-thumbnail.jpg"]
