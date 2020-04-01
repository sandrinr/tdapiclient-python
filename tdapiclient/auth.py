import datetime
import logging
import ssl
import webbrowser
from dataclasses import dataclass
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from tempfile import NamedTemporaryFile
from typing import Optional
from urllib.parse import parse_qs
from urllib.parse import quote as q

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import NameOID

from .base import TDAPIClientException, TDAuthContext

LOGGER = logging.getLogger(__name__)


class TDAPIClientAuthenticationException(TDAPIClientException):
    pass


def authenticate(client_id: str, refresh_token: str) -> TDAuthContext:
    LOGGER.debug("authenticate: requesting a new access token")

    auth_ret = get_access_token(client_id=client_id, refresh_token=refresh_token)
    access_token = auth_ret["access_token"]
    valid_until = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(
        seconds=int(auth_ret["expires_in"])
    )

    LOGGER.debug(
        "authenticate: got new access token, access_token=%s..., valid_until=%s",
        access_token[:12],
        valid_until,
    )

    return TDAuthContext(
        client_id=client_id,
        refresh_token=refresh_token,
        access_token=access_token,
        access_token_valid_until=valid_until,
    )


def get_access_token(client_id, refresh_token) -> dict:
    client_id = client_id + "@AMER.OAUTHAP"
    LOGGER.debug("get_access_token: client_id=%s", client_id)

    from .base import TDBase

    url = TDBase.url_base + "/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    LOGGER.debug("get_access_token: POST %s", url)
    res = requests.post(url=url, data=data)
    res.raise_for_status()
    return res.json()


@dataclass
class AuthResponseContext:
    code: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None


class AuthResponseHandler(BaseHTTPRequestHandler):
    context: AuthResponseContext

    def __init__(self, context: AuthResponseContext, *args, **kwargs):
        self.context = context
        # Has to be called after member assignment
        super().__init__(*args, **kwargs)

    def _send_text_response(self, text: str):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode())

    def do_POST(self):  # pylint: disable=invalid-name
        self.do_GET()

    def do_GET(self):  # pylint: disable=invalid-name
        # Get path and query string
        path, _, query_string = self.path.partition("?")
        if path != "/" or not query_string:
            LOGGER.error("do_GET: got request on unknown path: %s", path)
            self.send_error(404)
            return
        qs_parsed = parse_qs(query_string)

        # Check whether we got an error from TD Ameritrade
        if "error" in qs_parsed:
            self.context.error = qs_parsed["error"][0]
            LOGGER.debug("do_GET: got error=%s", self.context.error)
            if "error_description" in qs_parsed:
                self.context.error_description = qs_parsed["error_description"][0]
                LOGGER.debug(
                    "do_GET: got error_description=%s", self.context.error_description
                )
            self._send_text_response(
                f"Got authentication error.\n"
                f"error={self.context.error}\n"
                f"error_description={self.context.error_description}\n"
            )
            return

        if "code" not in qs_parsed or len(qs_parsed["code"]) != 1:
            LOGGER.error("do_GET: got invalid query string: %s", query_string)
            self.send_error(400)
            return

        LOGGER.debug("do_GET: got authentication code")
        self.context.code = qs_parsed["code"]

        self._send_text_response(
            "Got authentication code.\n"
            "Proceed in calling Python program.\n"
            "You can close this browser session.\n"
        )


def get_refresh_token(
    client_id,
    redirect_uri=None,
    server_listen_host="localhost",
    server_listen_port=8123,
) -> dict:
    if redirect_uri is None:
        redirect_uri = f"https://{server_listen_host}:{server_listen_port}"
    LOGGER.debug("get_refresh_token: redirect_uri=%s", redirect_uri)

    client_id = client_id + "@AMER.OAUTHAP"
    LOGGER.debug("get_refresh_token: client_id=%s", client_id)

    LOGGER.debug("get_refresh_token: creating RSA key")
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    keyfile = NamedTemporaryFile(suffix=".pem")
    keyfile.write(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    keyfile.flush()

    LOGGER.debug("get_refresh_token: creating self signed RSA certificate")
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(
                NameOID.COMMON_NAME, f"{server_listen_host}:{server_listen_port}"
            )
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(
            # Our certificate shall be valid for 5 minutes
            datetime.datetime.utcnow()
            + datetime.timedelta(minutes=5)
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    certfile = NamedTemporaryFile(suffix=".pem")
    certfile.write(cert.public_bytes(encoding=serialization.Encoding.PEM))
    certfile.flush()

    LOGGER.debug("get_refresh_token: setting up HTTP server")
    context = AuthResponseContext()
    httpd = HTTPServer(
        (server_listen_host, server_listen_port), partial(AuthResponseHandler, context)
    )
    sslcontext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    sslcontext.load_cert_chain(certfile=certfile.name, keyfile=keyfile.name)
    with sslcontext.wrap_socket(httpd.socket, server_side=True) as sslsocket:
        httpd.socket = sslsocket

        # We do this quite late to trigger any infrastructure related errors
        # before being navigated to the browser.
        url = (
            f"https://auth.tdameritrade.com/auth?response_type=code&"
            f"redirect_uri={q(redirect_uri)}&client_id={q(client_id)}"
        )
        LOGGER.debug(
            "get_refresh_token: opening browser for user to login, url=%s", url
        )
        webbrowser.open(url)

        while context.code is None and context.error is None:
            LOGGER.debug("get_refresh_token: waiting for an auth code")
            httpd.handle_request()

    if context.error is not None:
        raise TDAPIClientAuthenticationException(
            f"Error during authentication. error={context.error}, "
            f"error_description={context.error_description}"
        )

    LOGGER.debug("get_refresh_token: code=%s", context.code)

    LOGGER.debug("get_refresh_token: requesting refresh token")
    from .base import TDBase

    url = TDBase.url_base + "/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "refresh_token": "",
        "access_type": "offline",
        "code": context.code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    LOGGER.debug("get_refresh_token: POST %s", url)
    res = requests.post(url, data=data)
    res.raise_for_status()
    return res.json()
