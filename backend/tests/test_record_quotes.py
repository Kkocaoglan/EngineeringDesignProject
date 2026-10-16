"""Kayıt aracı ve fixture testleri (K3 · 3.5). İnternetsiz: yerel sahte WS ve kayıtlı fixture."""

import importlib.util
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from websockets.asyncio.server import serve

from app.market.binance import parse_book_ticker

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "record_quotes.py"
EXPECTED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"}


def _load_recorder_module():
    spec = importlib.util.spec_from_file_location("record_quotes", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quotes_fixture_exists_under_1mb_and_parses_cleanly():
    fixture_files = sorted(FIXTURES_DIR.glob("quotes_*.jsonl"))
    assert len(fixture_files) >= 1, "En az bir quotes_*.jsonl fixture dosyası olmalı"

    for fixture in fixture_files:
        size = fixture.stat().st_size
        assert 0 < size < 1_000_000, f"{fixture.name} boyutu 1 MB'tan küçük olmalı ({size} B)"

        lines = [ln for ln in fixture.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) >= len(EXPECTED_SYMBOLS)

        seen_symbols: set[str] = set()
        for line in lines:
            payload = json.loads(line)
            assert "received_at" in payload
            assert "stream" in payload
            assert "data" in payload

            rec_dt = datetime.fromisoformat(payload["received_at"].replace("Z", "+00:00"))
            assert rec_dt.tzinfo is not None

            quote = parse_book_ticker(line, rec_dt, allowed=EXPECTED_SYMBOLS)
            assert quote is not None
            assert isinstance(quote.bid, Decimal)
            assert isinstance(quote.ask, Decimal)
            assert quote.bid <= quote.ask
            seen_symbols.add(quote.symbol)

        assert seen_symbols == EXPECTED_SYMBOLS


async def test_record_quotes_writes_valid_jsonl_from_local_fake_ws(tmp_path: Path):
    recorder = _load_recorder_module()
    out_file = tmp_path / "quotes_test.jsonl"

    frames = [
        json.dumps(
            {
                "stream": "btcusdt@bookTicker",
                "data": {
                    "u": 1001,
                    "s": "BTCUSDT",
                    "b": "83000.00000000",
                    "B": "1.25000000",
                    "a": "83000.10000000",
                    "A": "2.50000000",
                },
            }
        ),
        "bozuk_json_satiri",
        json.dumps(
            {
                "stream": "dogeusdt@bookTicker",
                "data": {
                    "u": 1002,
                    "s": "DOGEUSDT",
                    "b": "0.15000000",
                    "B": "100.00000000",
                    "a": "0.15010000",
                    "A": "200.00000000",
                },
            }
        ),
        json.dumps(
            {
                "stream": "ethusdt@bookTicker",
                "data": {
                    "u": 1003,
                    "s": "ETHUSDT",
                    "b": "2500.00000000",
                    "B": "10.00000000",
                    "a": "2500.05000000",
                    "A": "8.00000000",
                },
            }
        ),
    ]

    async def fake_binance(connection):
        for frame in frames:
            await connection.send(frame)

    async with serve(fake_binance, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        written = await recorder.record_quotes(
            output_path=out_file,
            symbols=["BTCUSDT", "ETHUSDT"],
            ws_url=f"ws://127.0.0.1:{port}",
            duration_seconds=0.3,
            min_interval_seconds=0.0,
            max_bytes=50_000,
        )

    assert written == 2
    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    now = datetime(2026, 10, 16, 18, 0, 0, tzinfo=UTC)
    q1 = parse_book_ticker(lines[0], now)
    q2 = parse_book_ticker(lines[1], now)
    assert q1 is not None and q1.symbol == "BTCUSDT" and q1.bid == Decimal("83000.00000000")
    assert q2 is not None and q2.symbol == "ETHUSDT" and q2.ask == Decimal("2500.05000000")
