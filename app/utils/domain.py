"""Domain normalization used for company deduplication."""

import ipaddress
import re
from urllib.parse import urlsplit

_LABEL_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def normalize_domain(value: str) -> str:
    """Return the canonical registrable-looking host for a URL or bare domain.

    Lowercases, strips scheme, userinfo, port, path/query/fragment, a leading
    ``www.`` and any trailing dot. Unicode hosts are converted to punycode.

    Raises:
        ValueError: if the value is empty, an IP address, ``localhost``-like
            (no dot) or otherwise not a syntactically valid hostname.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("domain is empty")

    parts = urlsplit(raw if "://" in raw else f"//{raw}")
    host = parts.hostname  # strips userinfo and port, lowercases
    if not host:
        raise ValueError(f"could not extract a host from {value!r}")

    host = host.rstrip(".")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError(f"invalid hostname {value!r}") from exc

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP addresses are not accepted as company domains")

    if host.startswith("www."):
        host = host[4:]

    labels = host.split(".")
    if len(labels) < 2 or not all(_LABEL_RE.match(label) for label in labels):
        raise ValueError(f"invalid hostname {value!r}")
    if labels[-1].isdigit():
        raise ValueError(f"invalid top-level domain in {value!r}")
    return host
