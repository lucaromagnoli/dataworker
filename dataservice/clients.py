from __future__ import annotations

from logging import getLogger

import httpx

from dataservice.models import Request, Response

logger = getLogger(__name__)


class HttpXClient:
    """Client that uses HTTPX library to make requests."""

    def __init__(self):
        super().__init__()
        self.async_client = httpx.AsyncClient

    def __call__(self, *args, **kwargs):
        return self.make_request(*args, **kwargs)

    async def make_request(self, request: Request) -> Response:
        """Make a request using HTTPX."""
        logger.info(f"Requesting {request.url}")
        async with self.async_client() as client:
            match request.method:
                case "GET":
                    response = await client.get(request.url, params=request.params)
                case "POST":
                    response = await client.post(
                        request.url,
                        params=request.params,
                        data=request.form_data,
                        json=request.json_data,
                    )
            response.raise_for_status()
            match request.content_type:
                case "text":
                    data = response.text
                case "json":
                    data = response.json()
        logger.info(f"Returning response for {request.url}")
        return Response(request=request, data=data)
