import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

import app.cli as cli
from tests.test_discovery_pipeline import CSV


@pytest.fixture
def cli_db(db_engine: AsyncEngine, monkeypatch):
    monkeypatch.setattr(
        cli, "get_sessionmaker", lambda: async_sessionmaker(db_engine, expire_on_commit=False)
    )


async def _main(args: list[str]) -> int:
    return await cli._run(cli._parser().parse_args(args))


async def test_cli_discover_and_top_leads(cli_db, tmp_path, capsys) -> None:
    csv_file = tmp_path / "leads.csv"
    csv_file.write_text(CSV, encoding="utf-8")
    assert await _main(["discover", "--provider", "csv", "--csv-file", str(csv_file)]) == 0
    assert "new=1 duplicates=1 invalid=1" in capsys.readouterr().out
    assert await _main(["top-leads"]) == 0
    out = capsys.readouterr().out
    assert "1 lead(s)" in out and "acme.com" in out and "n/a" in out


async def test_cli_errors(cli_db, capsys) -> None:
    import uuid

    assert await _main(["discover", "--provider", "csv"]) == 2
    assert await _main(["discover", "--provider", "google_places", "--query", "x"]) == 1
    assert await _main(["research", "--company-id", str(uuid.uuid4())]) == 1
    assert await _main(["score", "--lead-id", str(uuid.uuid4())]) == 1


def test_cli_rejects_unknown_command() -> None:
    with pytest.raises(SystemExit):
        cli._parser().parse_args(["send-email"])
