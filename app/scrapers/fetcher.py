"""SSRF-safe, robots.txt-aware page fetcher with size and redirect limits."""

from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import get_settings
from app.utils.ssrf import Resolver, UnsafeURLError, default_resolver, validate_public_url


class FetchError(Exception):
    """A page could not be retrieved (blocked, too large, non-HTML, network...)."""


@dataclass(frozen=True)
class FetchedPage:
    url: str  # final URL after redirects
    status_code: int
    html: str


class SafeFetcher:
    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Resolver = default_resolver,
    ) -> None:
        self._settings = get_settings()
        self._transport = transport
        self._resolver = resolver

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self._transport,
            follow_redirects=False,  # we follow manually so every hop is validated
            timeout=self._settings.fetch_timeout_seconds,
            headers={"User-Agent": self._settings.fetch_user_agent},
        )

    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        for _ in range(self._settings.fetch_max_redirects + 1):
            try:
                await validate_public_url(url, self._resolver)
            except UnsafeURLError as exc:
                raise FetchError(f"blocked: {exc}") from exc
            try:
                async with client.stream("GET", url) as response:
                    if response.is_redirect and (location := response.headers.get("location")):
                        url = urljoin(url, location)
                        continue
                    ctype = response.headers.get("content-type", "")
                    if (
                        response.status_code < 400
                        and "html" not in ctype.lower()
                        and "xml" not in ctype.lower()
                        and "text" not in ctype.lower()
                    ):
                        raise FetchError(f"unsupported content type {ctype!r}")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self._settings.fetch_max_bytes:
                            raise FetchError("response too large")
                    # Body is already decoded by httpx: drop encoding/length headers so the
                    # rebuilt response is not decoded a second time.
                    headers = {
                        k: v
                        for k, v in response.headers.items()
                        if k.lower() not in ("content-encoding", "content-length")
                    }
                    return httpx.Response(
                        response.status_code,
                        headers=headers,
                        content=bytes(body),
                        request=response.request,
                    )
            except httpx.HTTPError as exc:
                raise FetchError(f"network error: {exc.__class__.__name__}") from exc
        raise FetchError("too many redirects")

    async def allowed_by_robots(self, client: httpx.AsyncClient, url: str) -> bool:
        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        try:
            response = await self._get(client, robots_url)
        except FetchError:
            return True  # no usable robots.txt -> nothing disallows us
        if response.status_code >= 400:
            return True
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser.can_fetch(self._settings.fetch_user_agent, url)

    async def fetch_page(self, url: str) -> FetchedPage:
        async with self._client() as client:
            await validate_public_url_or_raise(url, self._resolver)
            if not await self.allowed_by_robots(client, url):
                raise FetchError("disallowed by robots.txt")
            response = await self._get(client, url)
            final_url = str(response.request.url)
            return FetchedPage(url=final_url, status_code=response.status_code, html=response.text)


async def validate_public_url_or_raise(url: str, resolver: Resolver) -> None:
    try:
        await validate_public_url(url, resolver)
    except UnsafeURLError as exc:
        raise FetchError(f"blocked: {exc}") from exc
