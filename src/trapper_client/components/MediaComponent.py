import datetime
import os
import shutil
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, Callable, TypeVar, List, Set, Union
from urllib.parse import urlparse

import requests
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from trapper_client import Schemas
from trapper_client.Reports import Report
from trapper_client.Schemas import TrapperMedia
from trapper_client.TrapperAPIComponent import TrapperAPIComponent, T
import attr

from trapper_client.components.CollectionsComponent import CollectionsComponent
from trapper_client.components.ObservationsComponent import ObservationsComponent
from trapper_client.components.ResourcesComponent import ResourcesComponent
import logging

logger = logging.getLogger(__name__)

@attr.s
class MediaComponent(TrapperAPIComponent):
    """
    Component for interacting with Media endpoint.

    Provides methods to retrieve and download media files from classification projects.
    """
    _endpoint = "/media_classification/api/media/{cp}/"
    _schema = Schemas.TrapperMediaList

    explicit_fields = [
        "project",
        "owner",
        "deployment",
#        "collection", --> overridden in self. get_by_collection (resol collection_id through CollectionsComponent)
        "locations_map",
        "status",
        "status_ai",
        "rdate_from",
        "rdate_to",
        "rtime_from",
        "rtime_to",
        "ftype",
        "classified",
        "classified_ai",
        "bboxes",
        # Dynamic attributes related to observations
        "species",
        "observation_type",
        "sex",
        "age",
        # Atributos personalizados (definidos en cada proyecto)
        # se agregan dinámicamente, por ejemplo:
        # "weather", "temperature", "habitat", etc.
    ]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @retry(
        stop=stop_after_attempt(5),  # hasta 5 intentos
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _download_media_with_retry(
            self,
            session: requests.Session,
            url: str,
    ) -> bytes:
        """
        Descarga un media con reintentos automáticos.
        """
        response = session.get(
            url,
            verify=self._client.verify_ssl,
            stream=True,
            timeout=30,  # MUY importante poner timeout
        )
        response.raise_for_status()
        return response.content


    def _download_trapper_media_list(self, media_list: Schemas.TrapperMediaList, zip_filename_base: str = None) -> List[
        str]:
        """
        Download media files and organize them into ZIP files.

        Parameters
        ----------
        media_list : Schemas.TrapperMediaList
            List of media items to download.
        zip_filename_base : str, optional
            Base name for the ZIP files. Defaults to "trapper_media_export".

        Returns
        -------
        List[str]
            List of paths to the created ZIP files.
        """

        MAX_ZIP_SIZE = 2 * 1024 ** 3  # 2 GB
        import tempfile, requests, zipfile
        temp_dir = Path(tempfile.mkdtemp(prefix="trapper_client_"))

        r = self._client.post(
            "/account/login/",
            body={"username": self._client.user_name, "password": self._client.user_password}
        )
        data = r.json()

        session_id = data["results"][0]["sessionid"]

        session = requests.Session()
        session.cookies.set(
            "sessionid",
            session_id,
            domain=urlparse(self._client.base_url).hostname,
            path="/"
        )

        if zip_filename_base is None:
            zip_filename_base = "trapper_media_export"

        zip_filename_base = os.path.join(temp_dir, zip_filename_base)

        zip_files = []
        zip_index = 1
        current_zip_size = 0
        zip_writer = None

        def start_new_zip():
            nonlocal zip_index, zip_writer, current_zip_size
            zip_name = f"{zip_filename_base}_{zip_index:03}.zip"
            zip_writer = zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED)
            zip_files.append(zip_name)
            current_zip_size = 0
            return zip_name

        # Iniciar el primer zip
        start_new_zip()

        for media in media_list.results:
            file_url = media.filePath
            file_name = f"{media.mediaID}:{media.fileName}"
            deployment_id = media.deploymentID
            mediatype = media.fileMediatype or "image/jpeg"
            file_ext = ".jpg" if mediatype == "image/jpeg" else ""
            zip_internal_path = os.path.join(deployment_id, file_name + file_ext)

            try:
                response = session.get(
                    str(file_url),
                    verify=self._client.verify_ssl,
                    stream=True
                )
                #response = requests.get(str(file_url))
                response.raise_for_status()
                file_data = response.content
                file_size = len(file_data)

                if current_zip_size + file_size > MAX_ZIP_SIZE:
                    zip_writer.close()
                    zip_index += 1
                    start_new_zip()

                zip_writer.writestr(zip_internal_path, file_data)
                current_zip_size += file_size

            except Exception as e:
                print(f"❌ Error descargando {file_name}: {e}")

        if zip_writer:
            zip_writer.close()

        return temp_dir

    def get_by_classification_project(self, cp_id: int, query: dict = None) -> T:
        """
        Retrieve media from a specific classification project.

        Parameters
        ----------
        cp_id : int
            The ID of the classification project (replaces {cp} in the endpoint).
        query : dict, optional
            Optional search/pagination parameters.

        Returns
        -------
        Schemas.TrapperMediaList
            Media items associated with the specified classification project.
        """
        query_copy = query.copy() if query else {}
        default_query =  {"cp": cp_id}
        combined_query = {**default_query, **query_copy}

        res = super().get(
                query = combined_query,
                filter_fn = None,
        )

        return res

    def get_all_by_classification_project(self, cp_id: int, query: dict = None) -> T:
        """
        Retrieve media from a specific classification project.

        Parameters
        ----------
        cp_id : int
            The ID of the classification project (replaces {cp} in the endpoint).
        query : dict, optional
            Optional search/pagination parameters.

        Returns
        -------
        Schemas.TrapperMediaList
            Media items associated with the specified classification project.
        """

        return self.get_all_by_classification_project(cp_id, query)

    def get_by_media_id(self, cp_id: int, m_id: int, query: dict = None) -> T:
        """
        Retrieve media by media ID within a specific classification project.

        Parameters
        ----------
        cp_id : int
            The ID of the classification project (replaces {cp} in the endpoint).
        m_id : int
            The media ID to filter by.
        query : dict, optional
            Optional search/pagination parameters.

        Returns
        -------
        Schemas.TrapperMediaList
            Media items associated with the specified classification project and media ID.
        """
        res = self.get_by_classification_project(cp_id, query)

        res.results = [entry for entry in res.results if entry.mediaID == m_id]

        return  res

    def get_by_collection(self, cp_id: int, c_id:int, query: dict = None) -> T:
        """
        Retrieve media from a specific classification project and collection.

        Parameters
        ----------
        cp_id : int
            The ID of the classification project (replaces {cp} in the endpoint).
        c_id : int
            The ID of the collection to filter media by.
        query : dict, optional
            Optional search/pagination parameters.

        Returns
        -------
        Schemas.TrapperMediaList
            Media items associated with the specified classification project and collection.
        """

        collections:CollectionsComponent = CollectionsComponent(self._client)
        results = collections.get_by_classification_project(cp_id)
        logger.info(results)

        collection_inter_id = [ r.pk for r in results.results if r.collection_pk == c_id ]

        if len(collection_inter_id) == 0:
            # No hay colecciones asociadas al proyecto de clasificacion
            return Schemas.TrapperMediaList(**{"pagination": {"count":0, "next":None, "previous":None}, "results":[]})

        q = query.copy() if query else {}
        q["collection"] = ",".join(map(str, collection_inter_id))

        res = super().get_all(
                query = q,
                filter_fn = None,
                endpoint = self._endpoint.format(cp=cp_id),
        )

        return res

    def get_by_classification_project_only_animals(self, cp_id: int, query: dict = None) -> T:
        """
        Retrieve media containing only animal observations from a classification project.

        Parameters
        ----------
        cp_id : int
            The ID of the classification project.
        query : dict, optional
            Optional search/pagination parameters.

        Returns
        -------
        Schemas.TrapperMediaList
            Media items containing only animal observations.
        """

        # Obtenemos los mediaid de los media que solo tengan animales
        observations: ObservationsComponent = ObservationsComponent(self._client)
        o = observations.get_by_classification_project(cp_id, query)

        mediaid_groups = defaultdict(list)
        for entry in o.results:
            mediaid_groups[entry.mediaID].append(entry)

        filtered = []
        for mediaid, entries in mediaid_groups.items():
            if all(e.observationType == 'animal' for e in entries):
                filtered.extend(entries)

        # Obtenemos todos los medias del proyecto de clasificacion
        endpoint = self._endpoint.format(cp=cp_id)
        res = self._client.get_all_pages(endpoint, query)
        medias = self._schema(**res)

        # Obtener el conjunto de mediaIDs válidos del paso anterior
        valid_media_ids = {obs.mediaID for obs in filtered}

        # Filtrar las entradas multimedia que tienen esos mediaIDs
        filtered = [entry for entry in medias.results if entry.mediaID in valid_media_ids]

        pagination = medias.pagination
        pagination.count = len(valid_media_ids)

        return Schemas.TrapperMediaList(**{"pagination": pagination, "results": filtered})


    def download(self, cp_id: int, m_id:Union[int, "TrapperMedia"], destination_folder: Path, filename_overwrite:str=None) -> Path:
        """
        Download a single media file.
        Parameters
        ----------
        cp_id : int
            The ID of the classification project.
        m_id : int or TrapperMedia
            The media ID to download or a TrapperMedia object.
        destination_folder : Path
            Folder to save the downloaded media.
        filename_overwrite : str, optional
            If provided, the downloaded file will be saved with this name.
        Returns
        -------
        Path
            Path to the downloaded media file.
        """

        if not isinstance(m_id, int):
            media = m_id
            if cp_id is not None:
                raise ValueError("Si se pasa un TrapperMedia, no se debe especificar cp_id.")
        else:
            media = self.get_by_media_id(cp_id, m_id)

            if media.results is None or len(media.results) == 0:
                raise Exception(f"No se encontró media con mediaID {m_id} en el proyecto de clasificación {cp_id}.")

            media = media.results[0]

        return self._download_media(media, destination_folder, filename_overwrite)

    def download_one(self, cp_id: int, m_id:Union[int, "TrapperMedia"], destination_folder: Path,
                     filename_overwrite:str=None) -> Path:
        """
        Download a single media file.
        Parameters
        ----------
        cp_id : int
            The ID of the classification project.
        m_id : int or TrapperMedia
            The media ID to download or a TrapperMedia object.
        destination_folder : Path
            Folder to save the downloaded media.
        filename_overwrite : str, optional
            If provided, the downloaded file will be saved with this name.
        Returns
        -------
        Path
            Path to the downloaded media file.
        """
        return self.download(cp_id, m_id, destination_folder, filename_overwrite)

    def download_many(
        self,
        cp_id: int,
        medias: List[Union[int, "TrapperMedia"]],
        destination_folder: Path,
        compress: bool = False,
        max_workers=2,
        callback: callable = None
    ) -> (Path, Report):

        """
        Download multiple media files concurrently.
        Parameters
        ----------
        cp_id : int
            The ID of the classification project.
        medias : List[Union[int, TrapperMedia]]
            List of media IDs or TrapperMedia objects to download.
        destination_folder : Path
            Folder to store downloaded media temporarily.
        compress : bool, optional
            If True, media will be zipped into a single file. Default is False.
        max_workers : int, optional
            Number of concurrent download workers. Default is 2.
        callback : callable, optional
            Optional callback function for progress updates.
        Returns
        -------
        Path
            Path to the folder with downloaded media or the ZIP file.
        Report
            Report object with details of the download process.
        """
        report:Report = Report(title=f"Downloading {len(medias)} media(s)")

        out_put_dir =self._create_random_subfolder(destination_folder, prefix=f"trapper_download_media_{cp_id}")

        def _notify(event: str, sid: int, name, total=None, step=None):
            if callback:
                try:
                    callback(event, sid, name, total, step)
                except Exception as e:
                    raise e
                    # self.logger.debug("Callback raised an exception", exc_info=True)

        # Wrapper to notify when thread starts
        def _worker(item):
            media_id = item if isinstance(item, int) else item.mediaID
            _notify("start", media_id, "Downloading file", total=None, step=0)
            return self.download(cp_id, item, out_put_dir)

        _notify("start", cp_id, "Downloading medias",  total=len(medias), step=0)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Lanzamos cada descarga como una tarea independiente
            futures = {executor.submit(_worker, item): item for item in medias}

            for future in as_completed(futures):
                item = futures[future]
                try:
                    media_id = item if isinstance(item, int) else item.mediaID
                    ok = future.result()  # devuelve Path
                    report.add_success(str(media_id),"download", str(ok))
                    _notify("end", media_id, "Downloading file", total=None, step=1)

                except Exception as e:
                    _notify("fail", media_id, "Downloading file", total=None, step=1)
                    report.add_error(str(media_id), "download", str(e))

        if compress:
            out_put_dir= self._compress_folder(out_put_dir, fmt="zip", remove_folder=True)
        report.finish()

        _notify("end", cp_id, "Downloading medias", total=len(medias), step=0)

        return out_put_dir, report

    def download_by_classification_project(self, cp_id: int, query: dict = None, destination_folder: Path=None,
                                    compress: bool = False, workers = 2, callback: callable = None) -> (Path, Report):
        """
        Download all media from a specific classification project.
        Parameters
        ----------
        cp_id : int
            The ID of the classification project.
        query : dict, optional
            Optional search/pagination parameters.
        destination_folder : Path
            Folder to store downloaded media temporarily.
        compress : Path, optional
            If provided, media will be zipped into this file.
        workers : int, optional
            Number of concurrent download workers. Default is 2.
        callback : callable, optional
            Optional callback function for progress updates.
        Returns
        -------
        Path
            Path to the folder with downloaded media or the ZIP file.
        Report
            Report object with details of the download process.
        """

        out_put_dir =self._create_random_subfolder(destination_folder, prefix=f"trapper_download_media_{cp_id}")
        results = self.get_by_classification_project(cp_id, query)

        return self.download_many(None, results.results, out_put_dir, compress, workers, callback)

    def download_by_collection(self, cp_id: int, c_id:int, query: dict = None, destination_folder: Path=None,
                                           compress: bool = False, workers = 2, callback: callable = None) -> (Path, Report):
        """
        Download all media from a specific classification project and collection.

        Parameters
        ----------
        cp_id : int
            The ID of the classification project.
        c_id : int
            The ID of the collection.
        query : dict, optional
            Optional search/pagination parameters.
        destination_folder : Path
            Folder to store downloaded media temporarily.
        compress : str, optional
            Base name for the ZIP files.
        workers : int, optional
            Number of concurrent download workers. Default is 2.
        callback : callable, optional
            Optional callback function for progress updates.

        Returns
        -------
        Path
            Path to the folder with downloaded media or the ZIP file.
        Report
            Report object with details of the download process.

        """

        out_put_dir = self._create_random_subfolder(destination_folder, prefix=f"trapper_download_media_{cp_id}")
        results = self.get_by_collection(cp_id, c_id, query)

        return self.download_many(None, results.results, out_put_dir, compress, workers, callback)

    def _download_media(self, media:TrapperMedia,destination_folder: Path, filename_overwrite:str=None) -> Path:
        """
        Download a single media file.
        Parameters
        ----------
        media : TrapperMedia
            The media item to download.
        destination_folder : Path
            Folder to save the downloaded media.
        filename_overwrite : str, optional
            If provided, the downloaded file will be saved with this name.
        Returns
        -------
        Path
            Path to the downloaded media file.
        """
        logger.debug(
            f"MediaID: {media.mediaID}, FileName: {media.fileName}, DeploymentID: {media.deploymentID}, FilePath: {media.filePath}"
        )


        if media.filePublic is True:
            package_url = media.filePath
        else:
            raise Exception("Media no es público, no se puede descargar directamente.")

        resp = requests.get(package_url, stream=True, timeout=60)
        resp.raise_for_status()
        filename = media.fileName

        if filename_overwrite:
            filename = filename_overwrite

        # Asegurar que la carpeta destino existe
        os.makedirs(destination_folder, exist_ok=True)
        destination_path = os.path.join(destination_folder, filename)

        # Guardar el contenido por chunks
        with open(destination_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return Path(destination_path)

    def _create_random_subfolder(self, destination_folder: Path, prefix:str="trapper_") -> Path:
        """
        Crea y devuelve una carpeta con nombre aleatorio dentro de `destination_folder`.
        """
        destination_folder.mkdir(parents=True, exist_ok=True)
        date_str = datetime.date.today().strftime("%Y%m%d")

        subdir = Path(tempfile.mkdtemp(prefix=f"{prefix}{date_str}_", dir=str(destination_folder)))
        return subdir

    def _compress_folder(self,folder: Path, fmt: str = "zip", remove_folder: bool = True) -> Path:
        """
        Comprime la carpeta `folder` en un archivo del mismo nombre en su directorio padre.
        - `fmt`: formato de archivo admitido por `shutil.make_archive` (por defecto "zip").
        - `remove_folder`: si True borra la carpeta original tras crear el archivo.
        Retorna la Path del archivo creado.
        """
        folder = Path(folder)
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(f"The folder {folder} does not exist or is not a directory.")

        archive_base = str(folder)  # base sin extensión
        archive_path_str = shutil.make_archive(archive_base, fmt, root_dir=folder.parent, base_dir=folder.name)
        archive_path = Path(archive_path_str)

        if remove_folder:
            shutil.rmtree(folder)

        return archive_path

## Fuerzo que se cree los métodos dinámicos,
#   MediaComponent.__init_subclass__()