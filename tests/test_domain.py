import pytest

from app.utils.domain import normalize_domain


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://www.Example.com/about?x=1#top", "example.com"),
        ("http://example.com:8080/", "example.com"),
        ("EXAMPLE.COM", "example.com"),
        ("www.example.co.uk", "example.co.uk"),
        ("example.com.", "example.com"),
        ("https://user:pw@shop.example.com/path", "shop.example.com"),
        ("https://bücher.de", "xn--bcher-kva.de"),
    ],
)
def test_normalizes(raw: str, expected: str) -> None:
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "localhost",
        "http://127.0.0.1/",
        "192.168.1.5",
        "not a domain",
        "a..com",
        "-a.com",
        "example.123",
    ],
)
def test_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        normalize_domain(bad)
