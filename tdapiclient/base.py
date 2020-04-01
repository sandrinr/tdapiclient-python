import datetime
import logging
from dataclasses import dataclass
from typing import Any, Mapping, Tuple

import requests
from requests import Response

LOGGER = logging.getLogger(__name__)


class TDAPIClientException(Exception):
    pass


@dataclass
class TDAuthContext:
    client_id: str
    refresh_token: str
    access_token: str
    access_token_valid_until: datetime.datetime


class TDBase:
    url_base = "https://api.tdameritrade.com/v1"
    auth_context: TDAuthContext

    def __init__(self, auth_context: TDAuthContext):
        self.auth_context = auth_context

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.auth_context.access_token}"}

    def _get(self, path: str, **request_args) -> Tuple[Any, Mapping[str, str]]:
        return self._call(method="GET", path=path, **request_args)

    def _post(self, path: str, **request_args) -> Tuple[Any, Mapping[str, str]]:
        return self._call(method="POST", path=path, **request_args)

    def _delete(self, path: str, **request_args) -> Tuple[Any, Mapping[str, str]]:
        return self._call(method="DELETE", path=path, **request_args)

    @staticmethod
    def _trace_response(res: Response):
        def _trunc(s):
            return f"{s[:75]}[...]" if len(s) > 75 else s

        request_headers = "\n".join(
            [f"{k}: {_trunc(v)}" for k, v in res.request.headers.items()]
        )
        response_headers = "\n".join(
            [f"{k}: {_trunc(v)}" for k, v in res.headers.items()]
        )
        return f"""
Status: {res.status_code} {res.reason}
>>>>>>>>
{res.request.method} {res.request.url}
{request_headers}

{str(res.request.body) if res.request.body is not None else '<NULL>'}
<<<<<<<<
{res.status_code} {res.reason}
{response_headers}

{res.text if res.text is not None else '<NULL>'}
"""

    def _call(
        self, method: str, path: str, **request_args
    ) -> Tuple[Any, Mapping[str, str]]:
        url = self.url_base + path
        LOGGER.debug("_call: %s %s", method, url)
        res = requests.request(
            method=method, url=url, headers=self._auth_headers(), **request_args
        )
        if not res.ok:
            LOGGER.error(
                "_call: request resulted in an error: %s", self._trace_response(res)
            )

        res.raise_for_status()
        return (res.json() if res.text else None), res.headers
