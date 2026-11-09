import httpx
import pytest

from app.scrapers.fetcher import FetchError
from app.utils.ssrf import UnsafeURLError, validate_public_url
from tests.helpers import GOOD_HTML, fake_resolver, make_fetcher


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/",
        "file:///etc/passwd",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.1.2.3/",
        "http://192.168.0.1/",
        "http://internal.test/",
        "http://rebind.test/",  # one public + one loopback answer -> blocked
        "http://user:pw@example.com/",
        "http://unknown-host.test/",
        "http:///nohost",
    ],
)
async def test_unsafe_urls_blocked(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        await validate_public_url(url, fake_resolver)


async def test_public_url_allowed() -> None:
    assert await validate_public_url("https://example.com/x", fake_resolver)


async def test_fetch_success_and_robots_checked() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, html=GOOD_HTML)

    page = await make_fetcher(handler).fetch_page("https://acme.com/")
    assert page.status_code == 200 and "Acme Plumbing" in page.html
    assert "/robots.txt" in seen


async def test_robots_disallow_respected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return httpx.Response(200, html=GOOD_HTML)

    with pytest.raises(FetchError, match="robots"):
        await make_fetcher(handler).fetch_page("https://acme.com/")


async def test_redirect_to_internal_address_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "http://169.254.169.254/secret"})

    with pytest.raises(FetchError, match="blocked"):
        await make_fetcher(handler).fetch_page("https://acme.com/")


async def test_redirect_loop_and_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "https://acme.com/again"})

    with pytest.raises(FetchError, match="redirect"):
        await make_fetcher(handler).fetch_page("https://acme.com/")


async def test_follows_safe_redirect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "acme.com":
            return httpx.Response(301, headers={"location": "https://www.acme.com/home"})
        return httpx.Response(200, html=GOOD_HTML)

    page = await make_fetcher(handler).fetch_page("https://acme.com/")
    assert page.url == "https://www.acme.com/home"


async def test_too_large_and_non_html_rejected() -> None:
    def big(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, html="x" * 2_000_000)

    with pytest.raises(FetchError, match="large"):
        await make_fetcher(big).fetch_page("https://acme.com/")

    def pdf(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})

    with pytest.raises(FetchError, match="content type"):
        await make_fetcher(pdf).fetch_page("https://acme.com/")


async def test_network_error_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(FetchError, match="network"):
        await make_fetcher(handler).fetch_page("https://acme.com/")


async def test_gzip_encoded_response_is_decoded_once() -> None:
    """Regression: live research failed with DecodingError on compressed pages."""
    import gzip

    payload = gzip.compress(GOOD_HTML.encode())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200,
            content=payload,
            headers={"content-encoding": "gzip", "content-type": "text/html; charset=utf-8"},
        )

    page = await make_fetcher(handler).fetch_page("https://acme.com/")
    assert "Acme Plumbing" in page.html
