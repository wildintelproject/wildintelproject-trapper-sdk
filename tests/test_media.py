import logging
import zipfile
from pathlib import Path

import pytest
import yaml

from trapper_client.Schemas import TrapperMedia
from .helpers import validate_objects, run_test_by_filters

logger = logging.getLogger(__name__)

#
# pytest -o log_cli=true --log-cli-level=DEBUG
#

@pytest.fixture(scope="session")
def media_download_cases():
    path = Path(__file__).parent / "data" / "media_download_cases.yaml"
    with path.open() as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def download_cp_cases():
    path = Path(__file__).parent / "data" / "download_cp_cases.yaml"
    with path.open() as f:
        return yaml.safe_load(f)

# Función común de validación de deployments
def _validate_objects(deployments, expected_type=TrapperMedia):
    """Common validation for deployments responses."""
    assert hasattr(deployments, "results")
    assert hasattr(deployments, "pagination")

    if deployments.results:  # solo si hay resultados
        assert isinstance(deployments.results[0], expected_type)

# Funciones de validación específicas
def validate_project(results, expected):
    pass

def validate_resource_type(results, expected):
    assert all(d.resource_type == expected for d in results)

def validate_name(results, expected):
    assert all(d.name == expected for d in results)

def validate_status(results, expected):
    pass

def validate_rdata_from(results, expected):
    from datetime import datetime
    expected_date = datetime.fromisoformat(expected)
    assert all(d.date_recorded >= expected_date for d in results)

# Diccionario de validaciones por filtro
VALIDATIONS = {
    "project": validate_project,
    "name": validate_name,
    "status": validate_status,
    "rdate_from": validate_rdata_from
}

#explicit_fields = [
#    "rdate_from",  # BaseDateFilter sobre date_recorded__date (gte)
#    "rdate_to",  # BaseDateFilter sobre date_recorded__date (lte)
#    "udate_from",  # BaseDateFilter sobre date_uploaded__date (gte)
#    "udate_to",  # BaseDateFilter sobre date_uploaded__date (lte)
#    "rtime_from",  # BaseTimeFilter sobre date_recorded (gte)
#    "rtime_to",  # BaseTimeFilter sobre date_recorded (lte)
#    "owner",  # OwnResourceBooleanFilter
#    "locations_map",  # BaseLocationsMapFilter sobre deployment__location
#    "collections",  # MultipleChoiceFilter
#    "deployments",  # CharFilter, método get_deployments
#    "deployment__isnull",  # BooleanFilter
#    "tags",  # MultipleChoiceFilter
#    "observation_type",  # CharFilter, método get_observation_type
#    "species",  # CharFilter, método get_species
#    "timestamp_error",  # BooleanFilter, método get_timestamp_error
#]

# Parametrización de filtros a testear
@pytest.mark.parametrize(
    "cp_id, filter_name,filter_value",
    [
        (33, "project", 33),
        (33, "deployment", 660),
        (33, "collection", 47),
    ]
#"owner",  # OwnCollectionBooleanFilter
#"research_projects",
#"locations_map",
)
def test_trapper_client_classificator_filters(trapper_client, cp_id, filter_name, filter_value):
    method_name = f"get_by_{filter_name}"

    # Saltar si no hay método generado automáticamente
    if not hasattr(trapper_client.media, method_name):
        logging.debug(f"Method {method_name} not implemented, skipping...")
        pytest.skip(f"Method {method_name} not implemented")

    method = getattr(trapper_client.media, method_name)
    logger.info(f"Calling method {method_name}")
    results = method(cp_id, filter_value)
    _validate_objects(results)

    if filter_name in VALIDATIONS:
        VALIDATIONS[filter_name](results.results, filter_value)

    logging.debug(f"Filter '{filter_name}' returned {len(results.results)} results.")

def test_trapper_client_media_get_by_classification_project(trapper_client):
    try:
        deployments = trapper_client.media.get_by_classification_project("33")
        logging.info(deployments)
        validate_objects(deployments, expected_type=TrapperMedia)
        assert True
    except Exception as e:
        print(f"Error fetching research project: {e}")
        assert False, f"Exception occurred: {e}"

def test_trapper_client_media_get_by_mediaid(trapper_client):
    try:
        mediaID=3107568
        cp_id= 33
        results = trapper_client.media.get_by_media_id(cp_id,mediaID)
        logging.info(results)
        validate_objects(results, expected_type=TrapperMedia)
        assert len(results.results) == 1, f"Expected 1 result, got {len(results.results)}"
        assert results.results[0].mediaID == mediaID, f"Expected media ID {mediaID}, got {results.results[0].id}"
        assert True
    except Exception as e:
        print(f"Error fetching research project: {e}")
        assert False, f"Exception occurred: {e}"

#
# Download tests
#

def test_trapper_client_media_download_by_case(trapper_client, tmp_path, media_download_cases):
    cp_id = media_download_cases["classification_project"]

    for case in media_download_cases["cases"]:
        logger.info(f"Testing download case: {case}")
        media_id = case["media_id"]
        expect = case["expect"]

        if "raises" in expect:
            with pytest.raises(eval(expect["raises"])):
                trapper_client.media.download(cp_id, media_id, tmp_path)
            continue

        filename = trapper_client.media.download(cp_id, media_id, tmp_path)
        file_path = Path(filename)
        assert file_path.is_file()


def test_trapper_client_media_download_cp_cases(trapper_client, tmp_path, download_cp_cases):
    cp_id = download_cp_cases["classification_project"]

    for case in download_cp_cases["cases"]:
        logger.info(f"Testing download case: {case}")




        compress = case.get("compress", False)
        expect = case["expect"]

        (filename, report) = trapper_client.media.download_by_classification_project(
            cp_id,
            query=None,
            destination_folder=tmp_path,
            compress=compress
        )

        file_path = Path(filename)

        # Validaciones generales
        if expect.get("is_file"):
            assert file_path.is_file(), f"El fichero `{file_path}` no existe o no es un fichero"
        if expect.get("is_dir"):
            assert file_path.is_dir(), f"El directorio `{file_path}` no existe o no es un directorio"

        # Validación suffix
        if "suffix" in expect:
            assert file_path.suffix.lower() == expect["suffix"], f"El fichero `{file_path}` no tiene la extensión {expect['suffix']}"

        # Validación de contenido
        if expect.get("contains_files"):
            assert any(p.is_file() for p in file_path.iterdir()), f"El directorio `{file_path}` no contiene ficheros"
        if expect.get("zip_contains_files"):
            assert zipfile.is_zipfile(file_path), f"El fichero `{file_path}` no es un zip válido"
            with zipfile.ZipFile(file_path) as z:
                names = z.namelist()
                assert any(not n.endswith("/") for n in names), f"El zip `{file_path}` no contiene ficheros"


def test_trapper_client_media_download_cp(trapper_client):
    folder = None

    try:
        cp_id = 33
        output = Path("/tmp")
        (filename, report) = trapper_client.media.download_by_classification_project(cp_id, query=None, destination_folder=output)
        logging.info(filename)
        folder = Path(filename)
        assert folder.exists() and folder.is_dir(), f"El resultado `{folder}` no existe o no es un directorio"

        try:
            folder.resolve().relative_to(output.resolve())
        except Exception:
            assert False, f"El directorio `{folder}` no está dentro de `output` `{output}`"

        assert any(p.is_file() for p in folder.iterdir()), f"El directorio `{folder}` no contiene ficheros"
        assert True
    except Exception as e:
        print(f"Error fetching research project: {e}")
        assert False, f"Exception occurred: {e}"
    finally:
        if folder and folder.exists():
            import shutil
            try:
                shutil.rmtree(folder)
            except Exception as e:
                logging.warning(f"No se pudo borrar `{folder}`: {e}")

def test_trapper_client_media_download_cp_zip(trapper_client):
    file_path = None
    try:
        cp_id = 33
        output = Path("/tmp")
        filename = trapper_client.media.download_by_classification_project(
            cp_id, query=None, destination_folder=output, compress=True
        )

        file_path = Path(filename)
        assert file_path.exists() and file_path.is_file(), f"El fichero `{file_path}` no existe o no es un fichero"
        assert file_path.suffix.lower() == ".zip", f"El fichero `{file_path}` no tiene extensión .zip"

        try:
            file_path.resolve().relative_to(output.resolve())
        except Exception:
            assert False, f"El fichero `{file_path}` no está dentro de `output` `{output}`"

        import zipfile
        assert zipfile.is_zipfile(file_path), f"El fichero `{file_path}` no es un zip válido"

        with zipfile.ZipFile(file_path) as z:
            names = z.namelist()
            assert any(not n.endswith("/") for n in names), f"El zip `{file_path}` no contiene ficheros"

        assert True
    except Exception as e:
        print(f"Error fetching research project: {e}")
        assert False, f"Exception occurred: {e}"
    finally:
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logging.warning(f"No se pudo borrar `{file_path}`: {e}")

def test_trapper_client_media_get_all(trapper_client):
    try:
        deployments = trapper_client.media.get_all()
    except NotImplementedError as e:
        assert True, f"Exception occurred: {e}"
    except Exception as e:
        print(f"Error fetching research project: {e}")
        assert False, f"Exception occurred: {e}"

def test_trapper_client_media_where_classification_project(trapper_client):
    test_cp_id = "33"

    with trapper_client.media.where(cp=test_cp_id) as q:
        for item in q:
            assert isinstance(item, TrapperMedia)



"""def _test_trapper_client_media_get_by_classification_project_only_animals(trapper_client):
    id_test = "33"
    try:
        media = trapper_client.media.get_by_classification_project_only_animals(id_test)
        _validate_media(media)
        logging.debug(f"Found {len(media.results)} active media in classification project {id_test}.")
    except Exception as e:
        logging.debug(f"Exception occurred: {e}")
        assert False, f"Exception occurred: {e}"
"""
"""def test_trapper_client_media_get_by_classification_project_only_animals(trapper_client) -> T:
    id_test = "33"
    try:
        media = trapper_client.media.get_by_classification_project_only_animals(id_test)
        _validate_media(media)
        logging.debug(f"Found {len(media.results)} active media in classification project {id_test}.")
    except Exception as e:
        logging.debug(f"Exception occurred: {e}")
        assert False, f"Exception occurred: {e}"
"""

"""
   def _trapper_client_media_download_by_classification_project_only_animals(self, cp_id: int, query: dict = None, zip_filename_base: str = None):
download_by_classification_project
"""