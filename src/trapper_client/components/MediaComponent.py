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

    #
    # Download
    #

    def download(self, cp_id: int, m_id:Union[int, "TrapperMedia"], destination_folder: Path
                 , filename_overwrite:str=None
                 , session = None, download_private:bool = False) -> Path:
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

        logger.debug(f"Starting download of media {m_id} from classification project {cp_id} to folder {destination_folder}")

        if not isinstance(m_id, int):
            media = m_id
            if cp_id is not None:
                raise ValueError("Si se pasa un TrapperMedia, no se debe especificar cp_id.")
        else:
            logger.debug(f"Getting trapper media for id {m_id} from classification project {cp_id}")

            media = self.get_by_media_id(cp_id, m_id)

            if media.results is None or len(media.results) == 0:
                raise Exception(f"No se encontró media con mediaID {m_id} en el proyecto de clasificación {cp_id}.")

            media = media.results[0]

        return self._download_media(media, destination_folder, filename_overwrite, session, download_private)

    def download_one(self, cp_id: int, m_id:Union[int, "TrapperMedia"], destination_folder: Path,
                     filename_overwrite:str=None, session = None, download_private:bool = False) -> Path:
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
        return self.download(cp_id, m_id, destination_folder, filename_overwrite, session, download_private)

    def download_many(
        self,
        cp_id: int,
        medias: List[Union[int, "TrapperMedia"]],
        destination_folder: Path,
        compress: bool = False,
        max_workers=2,
        download_private:bool = False,
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

        if download_private:
            session = self._create_authenticated_session()

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
            return self.download(cp_id, item, out_put_dir, None, session, download_private)

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
                                    compress: bool = False, workers = 2,download_private: bool = False
                                    ,callback: callable = None
                                    ) -> (Path, Report):
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

        return self.download_many(None, results.results, out_put_dir, compress, workers, download_private, callback)

    def download_by_collection(self, cp_id: int, c_id:int, query: dict = None, destination_folder: Path=None,
                                           compress: bool = False, workers = 2, download_private:bool=False
                               ,callback: callable = None) -> (Path, Report):
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

        return self.download_many(None, results.results, out_put_dir, compress, workers, download_private,callback)

    def _download_media(
        self,
        media: TrapperMedia,
        destination_folder: Path,
        filename_overwrite: str = None,
        session: requests.Session = None,
        download_private:bool = False,
    ) -> Path:
        logger.debug(f"Downloading MediaID={media.mediaID}, public={media.filePublic}, url={media.filePath}")

        os.makedirs(destination_folder, exist_ok=True)

        filename = filename_overwrite or media.fileName
        destination_path = Path(destination_folder) / filename

        if session is None and not download_private:
            session = requests.Session()
        else:
            logger.debug("Getting authenticated session for private media download")
            session = self._create_authenticated_session()

        file_bytes = self._download_url(session, str(media.filePath))

        with open(destination_path, "wb") as f:
            f.write(file_bytes)

        return destination_path


    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _download_url(
        self,
        session: requests.Session,
        url: str,
    ) -> bytes:
        logger.debug("Downloading URL: {url}")

        response = session.get(
            url,
            verify=self._client.verify_ssl,
            stream=True,
            timeout=30,
        )
        response.raise_for_status()
        return response.content

    def _create_authenticated_session(self) -> requests.Session:
        logger.debug("Creating authenticated session")
        try:
            r= self._client.get_authenticated_session()
        except Exception as e:
            logger.error(f"Error creating authenticated session: {str(e)}")
            raise e
        logger.debug(f"Authentication response data: {r}")
        return r

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