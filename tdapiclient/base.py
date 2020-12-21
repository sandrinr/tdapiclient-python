import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal
from itertools import chain
from typing import Any, Dict, Mapping, Tuple

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

    def _post(
        self, path: str, expect_response_body: bool = True, **request_args
    ) -> Tuple[Any, Mapping[str, str]]:
        return self._call(
            method="POST",
            path=path,
            expect_response_body=expect_response_body,
            **request_args,
        )

    def _put(
        self, path: str, expect_response_body: bool = True, **request_args
    ) -> Tuple[Any, Mapping[str, str]]:
        return self._call(
            method="PUT",
            path=path,
            expect_response_body=expect_response_body,
            **request_args,
        )

    def _delete(
        self, path: str, expect_response_body: bool = True, **request_args
    ) -> Tuple[Any, Mapping[str, str]]:
        return self._call(
            method="DELETE",
            path=path,
            expect_response_body=expect_response_body,
            **request_args,
        )

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
        self, method: str, path: str, expect_response_body: bool = True, **request_args
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

        if expect_response_body:
            data = res.json(parse_float=Decimal)
        else:
            data = None

        return data, res.headers

    @staticmethod
    def params_from_locals(locals_: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms a dict into a query parameter dict. Switching from snake case
        to lower camel case. Suited to be applied to locals().
        """

        def snake2camel(in_: str) -> str:
            first, *others = in_.split("_")
            return "".join(chain([first.lower()], map(str.title, others)))

        params: Dict[str, Any] = {}
        for k, v in locals_.items():
            if k == "self":
                continue
            if v is None:
                continue
            key = snake2camel(k)
            if isinstance(v, Decimal):
                params[key] = str(v)
            elif isinstance(v, (datetime.date, datetime.datetime)):
                params[key] = v.isoformat()
            else:
                params[key] = v

        return params
