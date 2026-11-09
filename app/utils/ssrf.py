"""SSRF protection for outbound fetches (spec §10)."""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

Resolver = Callable[[str, int], Awaitable[list[str]]]


class UnsafeURLError(ValueError):
    """Raised when a URL must not be fetched."""


async def default_resolver(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return addr.is_global and not addr.is_multicast


async def validate_public_url(url: str, resolver: Resolver = default_resolver) -> str:
    """Return the URL if it is http(s) and every resolved address is public.

    Raises UnsafeURLError otherwise. Callers must re-validate every redirect hop.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeURLError(f"unsupported scheme {parts.scheme!r}")
    if not parts.hostname:
        raise UnsafeURLError("URL has no host")
    if parts.username or parts.password:
        raise UnsafeURLError("credentials in URL are not allowed")
    port = parts.port or (443 if parts.scheme == "https" else 80)

    try:
        literal = ipaddress.ip_address(parts.hostname)
    except ValueError:
        try:
            addresses = await resolver(parts.hostname, port)
        except OSError as exc:
            raise UnsafeURLError(f"could not resolve {parts.hostname}") from exc
    else:
        addresses = [str(literal)]

    if not addresses:
        raise UnsafeURLError(f"{parts.hostname} resolved to no addresses")
    for ip in addresses:
        if not _is_public(ip):
            raise UnsafeURLError(f"{parts.hostname} resolves to a non-public address")
    return url
