from json import JSONDecodeError
import json
import csv
import io
import zipfile
from typing import Dict, Any
import requests
import attr
from typing_extensions import Literal
from trapper_client import err
import logging

logger = logging.getLogger(__name__)

@attr.s
class APIClientBase:
    """
    Base client for interacting with the Trapper API.

    Provides common functionality for authentication, sending HTTP requests,
    handling pagination, and processing JSON or CSV responses.

    :param access_token: Authentication token used for API requests (if available)
    :type access_token: str
    :param user_name: Username for basic authentication
    :type user_name: str
    :param user_password: Password for basic authentication
    :type user_password: str
    :param verify_ssl: Whether to verify SSL certificates, defaults to True
    :type verify_ssl: bool, optional
    :param base_url: Base URL of the Trapper API, defaults to "https://wildintel-trap.uhu.es"
    :type base_url: str, optional
    """
    access_token: str = attr.ib(repr=False)
    user_name: str = attr.ib(repr=False)
    user_password: str = attr.ib(repr=False)
    verify_ssl: bool = attr.ib(repr=False, default=True)
    base_url: str = attr.ib(repr=False, default="https://wildintel-trap.uhu.es")
    logger = attr.field(repr=False, default=logger)

    name = "trapper_api_client"
    user_id: str = "me"

    def _paginate(self, items, page: int, per_page: int = 10):
        """
        Return a specific page of results from a list.

        :param items: List of items to paginate
        :type items: list
        :param page: Page number to return (1-indexed)
        :type page: int
        :param per_page: Number of items per page, defaults to 10
        :type per_page: int, optional
        :return: Items corresponding to the requested page
        :rtype: list
        """

        start = (page - 1) * per_page
        end = start + per_page
        return items[start:end]

    def _auth(self):
        """
        Return authentication headers or credentials tuple.

        If `access_token` is provided, returns headers with the token.
        Otherwise, returns a `(username, password)` tuple for basic authentication.

        :return: Tuple of headers and auth tuple
        :rtype: tuple[dict, tuple[str, str] | None]
        :raises ValueError: If neither token nor username/password are configured
        """

        if self.access_token:
            return {"Authorization": f"Token {self.access_token}"}, None
        elif self.user_name and self.user_password:
            return {}, (self.user_name, self.user_password)
        else:
            raise ValueError("No se ha configurado ni token ni usuario/clave")

    def get_authenticated_session(self) -> requests.Session:
        """
        Returns a requests.Session() authenticated either via:
        - Token (Authorization header)
        - Username/password (login form, Django session)
        """
        self.session = requests.Session()

        if self.access_token:
            # Token auth
            self.session.headers.update({"Authorization": f"Token {self.access_token}"})
            logger.debug("Using token authentication")
            return self.session
        elif self.user_name and self.user_password:

            # Form login (Django)
            login_url = self.base_url.rstrip("/") + "/account/login/"
            # Primero obtener CSRF
            r = self.session.get(login_url, verify=self.verify_ssl)
            csrf_token = self.session.cookies.get("csrftoken")
            if not csrf_token:
                raise ValueError("No CSRF token found during login")

            payload = {
                "login": self.user_name,
                "password": self.user_password,
                "csrfmiddlewaretoken": csrf_token,
            }
            headers = {"Referer": login_url}

            r = self.session.post(
                login_url,
                data=payload,
                headers=headers,
                verify=self.verify_ssl,
                allow_redirects=True,
            )

            if "sessionid" not in self.session.cookies:
                raise ValueError("Login failed: no sessionid cookie")

            logger.debug(f"Authenticated session via login, sessionid={self.session.cookies['sessionid']}")
            return self.session
        else:
            raise ValueError("No access token or username/password configured")

    def make_request(
        self,
        endpoint: str,
        method: Literal["GET", "POST", "PATCH", "DELETE", "PUT"],
        query: Dict[str,Any] = None,
        body: Dict = None,
        raise_on_error=True,
        only_json: bool = True,
    ) -> requests.Response:
        """
        Make an HTTP request to the API with authentication and error handling.

        Handles JSON and CSV responses, including paginated results.

        :param endpoint: API endpoint to call
        :type endpoint: str
        :param method: HTTP method, one of "GET", "POST", "PATCH", "DELETE", "PUT"
        :type method: str
        :param query: Dictionary of query parameters
        :type query: dict[str, Any], optional
        :param body: Request body for POST, PATCH, PUT
        :type body: dict, optional
        :param raise_on_error: Whether to raise exceptions for non-2xx responses, defaults to True
        :type raise_on_error: bool, optional
        :return: HTTP response object
        :param only_json: convert CSV responses to JSON format, defaults to True
        :type only_json: bool, optional

        :rtype: requests.Response
        :raises ValueError: If an invalid HTTP method is provided
        :raises err.APIError: For general API errors
        :raises err.HTTP_ERRORS_MAP: For specific HTTP error codes mapped to exceptions
        """

        allowed_methods = "GET POST PATCH DELETE PUT".split()
        if method not in allowed_methods:
            raise ValueError(
                f'Invalid method: {method}. Must be one of {", ".join(allowed_methods)}'
            )

        headers, auth = self._auth()
        url = self.base_url.rstrip("/") + "/" + endpoint.lstrip("/")
        logger.debug(f"Making {method} request to {endpoint}")
        logger.debug("Query: " +   "&".join([f"{k}={v}" for k,v in query.items()]) if query else "None")
        session = requests.Session()

        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request auth: {auth}")

        r = session.request(method, url, headers=headers, auth=auth,params=query, json=body, verify=self.verify_ssl)

        if 200 <= r.status_code < 300:
            content_type = r.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = r.json()
                logger.debug(f"Response JSON:  {json.dumps(data,indent=4)}")

                if "pagination" not in data or "results" not in data:
                    logger.debug(f"Add pagination to response")

                    page = 1
                    per_page = len(data) if isinstance(data, list) else 1
                    pages = 1
                    total = len(data) if isinstance(data, list) else 1
                    paged_rows = data if isinstance(data, list) else [data]

                    response_obj = {
                        "pagination": {
                            "page": page,
                            "page_size": per_page,
                            "pages": pages,
                            "count": total,
                        },
                        "results": paged_rows,
                    }

                    r._content = json.dumps(response_obj).encode("utf-8")
                    r.headers["Content-Type"] = "application/json"
                    r.json = lambda: response_obj

                return r
            elif "text/csv" in content_type or r.text.strip().startswith(
                    tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")):

                if only_json:
                    if r.content[:4] == b'PK\x03\x04' or "zip" in content_type:
                        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                            csv_name = next((n for n in zf.namelist() if n.endswith(".csv")), None)
                            csv_text = zf.read(csv_name).decode("utf-8") if csv_name else ""
                    elif r.content[:2] == b'\x1f\x8b' or "gzip" in content_type:
                        import gzip
                        csv_text = gzip.decompress(r.content).decode("utf-8")
                    elif r.content[:2] == b'BZ' or "bzip2" in content_type:
                        import bz2
                        csv_text = bz2.decompress(r.content).decode("utf-8")
                    else:
                        csv_text = r.text

                    reader = csv.DictReader(io.StringIO(csv_text))
                    rows = list(reader)
                    logger.debug(f"Response CSV: {rows[1]}...")
                    total = len(rows)

                    response_obj = {
                        "pagination": {
                            "page": 1,
                            "page_size": total,
                            "pages": 1,
                            "count": total,
                        },
                        "results": rows,
                    }

                    r._content = json.dumps(response_obj).encode("utf-8")
                    r.headers["Content-Type"] = "application/json"
                    r.json = lambda: response_obj
                    logger.debug(f"Results from csv {response_obj}")
                    return r
                return r
            else:
                return r
        try:
            body = r.json()
            try:
                message = body["_error"]["message"]
            except (KeyError, TypeError):
                message = body
        except JSONDecodeError:
            body = r.text
            message = body

        logger.error(f"Unsuccessful request to {r.url}: [{r.status_code}] {message}")
        logger.debug(f"Full response: {body}")
        logger.debug(f"Headers: {r.headers}")
        logger.debug(f"Params: {query}")
        logger.debug(f"Body: {body}")
        if not raise_on_error:
            logger.warning(
                f"raise_on_error is False, ignoring API error and returning response"
            )
            return r

        if r.status_code in err.HTTP_ERRORS_MAP:
            raise err.HTTP_ERRORS_MAP[r.status_code](message)
        else:
            raise err.APIError(message)

    def get(
        self, endpoint: str, query: Dict = None, raise_on_error: bool = True
    ) -> Dict:
        """
        Send a GET request to the API.

        :param endpoint: API endpoint
        :type endpoint: str
        :param query: Dictionary of query parameters
        :type query: dict, optional
        :param raise_on_error: Whether to raise an exception for non-2xx responses, defaults to True
        :type raise_on_error: bool, optional
        :return: HTTP response
        :rtype: requests.Response
        """

        r = self.make_request(endpoint, method="GET", query=query, raise_on_error=raise_on_error)
        data = r.json()

        # Normalizar si no hay paginación
        if "pagination" not in data or "results" not in data:
            paged_rows = data if isinstance(data, list) else [data]
            data = {
                "pagination": {
                    "page": 1,
                    "page_size": len(paged_rows),
                    "pages": 1,
                    "count": len(paged_rows),
                },
                "results": paged_rows,
            }

        return data

    def get_all_pages(
            self, endpoint: str, query: Dict = None, raise_on_error: bool = True
    ) -> Dict:
        """
        Retrieve all paginated results from an endpoint.

        Always returns a dictionary with 'pagination' and 'results'.

        :param endpoint: API endpoint
        :type endpoint: str
        :param query: Dictionary of query parameters (the 'page' key is ignored)
        :type query: dict, optional
        :param raise_on_error: Whether to raise exceptions for non-2xx responses, defaults to True
        :type raise_on_error: bool, optional
        :return: Dictionary with combined 'results' and updated 'pagination'
        :rtype: dict
        """
        query = {} if query is None else query.copy()
        query.pop("page", None)

        # Primera página
        data = self.get(endpoint, query=query, raise_on_error=raise_on_error)
        pagination = data.get("pagination", {"page": 1, "pages": 1})
        page = pagination.get("page", 1)
        pages = pagination.get("pages", 1)

        results = {k: (v[:] if isinstance(v, list) else v) for k, v in data.items()}

        # Obtener siguientes páginas
        while page < pages:
            page += 1
            query["page"] = page
            next_page = self.get(endpoint, query=query, raise_on_error=raise_on_error)

            for k, v in next_page.items():
                if isinstance(v, list) and k in results:
                    results[k].extend(v)
                elif k not in results:
                    results[k] = v

            pagination = next_page.get("pagination", pagination)

        results["pagination"] = pagination
        return results

    def post(
        self,
        endpoint: str,
        query: Dict = None,
        body: Dict = None,
        raise_on_error: bool = True,
    ) -> requests.Response:
        """
        Send a POST request to the API.

        :param endpoint: API endpoint
        :type endpoint: str
        :param query: Dictionary of query parameters
        :type query: dict, optional
        :param body: Request body
        :type body: dict, optional
        :param raise_on_error: Whether to raise exceptions for non-2xx responses, defaults to True
        :type raise_on_error: bool, optional
        :return: HTTP response
        :rtype: requests.Response
        """
        return self.make_request(
            endpoint,
            method="POST",
            query=query,
            body=body,
            raise_on_error=raise_on_error,
        )

    def patch(
        self,
        endpoint: str,
        query: Dict = None,
        body: Dict = None,
        raise_on_error: bool = True,
    ) -> requests.Response:
        """
        Send a PATCH request to the API.

        :param endpoint: API endpoint
        :type endpoint: str
        :param query: Dictionary of query parameters
        :type query: dict, optional
        :param body: Request body
        :type body: dict, optional
        :param raise_on_error: Whether to raise exceptions for non-2xx responses, defaults to True
        :type raise_on_error: bool, optional
        :return: HTTP response
        :rtype: requests.Response
        """
        return self.make_request(
            endpoint,
            method="PATCH",
            query=query,
            body=body,
            raise_on_error=raise_on_error,
        )

    def put(
        self,
        endpoint: str,
        query: Dict = None,
        body: Dict = None,
        raise_on_error: bool = True,
    ) -> requests.Response:
        """
        Send a PUT request to the API.

        :param endpoint: API endpoint
        :type endpoint: str
        :param query: Dictionary of query parameters
        :type query: dict, optional
        :param body: Request body
        :type body: dict, optional
        :param raise_on_error: Whether to raise exceptions for non-2xx responses, defaults to True
        :type raise_on_error: bool, optional
        :return: HTTP response
        :rtype: requests.Response
        """
        return self.make_request(
            endpoint,
            method="PUT",
            query=query,
            body=body,
            raise_on_error=raise_on_error,
        )

    def delete(
        self,
        endpoint: str,
        query: Dict = None,
        body: Dict = None,
        raise_on_error: bool = True,
    ) -> requests.Response:
        """
        Send a DELETE request to the API.

        :param endpoint: API endpoint
        :type endpoint: str
        :param query: Dictionary of query parameters
        :type query: dict, optional
        :param body: Request body
        :type body: dict, optional
        :param raise_on_error: Whether to raise exceptions for non-2xx responses, defaults to True
        :type raise_on_error: bool, optional
        :return: HTTP response
        :rtype: requests.Response
        """
        return self.make_request(
            endpoint,
            method="DELETE",
            query=query,
            body=body,
            raise_on_error=raise_on_error,
        )