import logging
from time import sleep

import requests
from websocket import create_connection

from .exceptions import Unauthorized

logger = logging.getLogger(__name__)


class BaseAudoClient:
    """Base class all clients inherit"""
    default_base_url = "https://api.audo.ai/v1"

    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = self.default_base_url if base_url is None else base_url
        self.request_handler = requests.request

    def request(self, method: str, route: str, on_code: dict = None, **kwargs):
        """
        Make an authenticated request with our API key to an endpoint
        Same arguments as requests.request
        Args:
            method: HTTP method (ie. "GET")
            route: Endpoint route relative to base url (ie. "/remove-noise")
            on_code: Dict of handlers for HTTP status codes
            kwargs: Rest of keyword arguments to pass to requests.request
        Returns:
            data: JSON response from successful request
        """
        on_code = on_code or {}
        headers = kwargs.get('headers', {})
        headers = {k.lower(): v for k, v in headers.items()}
        headers.setdefault('x-api-key', self.api_key)
        kwargs['headers'] = headers

        r = self.request_handler(method, self.url(route), **kwargs)
        if r.status_code in on_code:
            result = on_code[r.status_code](r)
            if isinstance(result, Exception):
                raise result
        else:
            if r.status_code == 429:
                logger.warning("Rate limit exceeded. Backing off...")
                sleep(int(r.headers['retry-after']))
                return self.request(method, route, on_code, **kwargs)
            if r.status_code == 401:
                raise Unauthorized(r.content)
            r.raise_for_status()
        return r.json()

    def url(self, route: str) -> str:
        """Create a full URL from a route (ie. /remove-noise)"""
        return self.base_url + route

    def connect_websocket(self, job_id):
        wss_base = self.base_url.replace("http://", "ws://")
        wss_base = wss_base.replace("https://", "wss://")
        wss_url = wss_base + "/wss/remove-noise/{}/status".format(job_id)
        auth_header = {'x-api-key': self.api_key}
        return create_connection(wss_url, header=auth_header)
