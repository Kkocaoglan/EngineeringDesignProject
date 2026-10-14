"""Borsa kuralları senkronu (K3 · 3.2). İnternetsiz: Binance cevabı fixture'dan gelir."""

import json
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import text

from app.db import engine
from app.market.exchange_info import parse_asset_rows, sync_assets

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"]
SAMPLE = json.loads(
    (Path(__file__).parent / "fixtures" / "exchange_info_sample.json").read_text(encoding="utf-8")
)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _ok(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/api/v3/exchangeInfo"
    assert json.loads(request.url.params["symbols"]) == SYMBOLS  # sadece SYMBOLS istenir
    return httpx.Response(200, json=SAMPLE)


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("Binance'e ulaşılamıyor", request=request)


async def _all_assets() -> dict[str, tuple]:
    async with engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT symbol, base_asset, quote_asset, tick_size, step_size, min_qty, min_notional "
            "FROM assets ORDER BY symbol"
        ))
        return {r[0]: tuple(r[1:]) for r in rows}


async def test_sync_writes_five_correct_rows():
    async with _client(_ok) as client:
        written = await sync_assets(SYMBOLS, client=client)

    assert written == 5
    rows = await _all_assets()
    assert sorted(rows) == sorted(SYMBOLS)
    assert rows["BTCUSDT"] == (
        "BTC", "USDT", Decimal("0.01"), Decimal("0.00001"), Decimal("0.00001"), Decimal("5")
    )
    assert rows["ETHUSDT"][3:5] == (Decimal("0.0001"), Decimal("0.0001"))
    assert rows["XRPUSDT"][2:] == (  # eski MIN_NOTIONAL filtresi de okunur
        Decimal("0.0001"), Decimal("0.1"), Decimal("0.1"), Decimal("5")
    )
    for row in rows.values():
        assert all(isinstance(v, Decimal) for v in row[2:])


async def test_sync_updates_existing_rows():
    async with _client(_ok) as client:
        await sync_assets(SYMBOLS, client=client)
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE assets SET tick_size = 1, min_notional = 99"))

    async with _client(_ok) as client:
        assert await sync_assets(SYMBOLS, client=client) == 5

    rows = await _all_assets()
    assert len(rows) == 5
    assert rows["BTCUSDT"][2] == Decimal("0.01")
    assert rows["BTCUSDT"][5] == Decimal("5")


async def test_binance_unreachable_keeps_old_values_and_does_not_crash():
    async with _client(_ok) as client:
        await sync_assets(SYMBOLS, client=client)
    before = await _all_assets()

    async with _client(_down) as client:
        assert await sync_assets(SYMBOLS, client=client) == 0  # çökmez

    assert await _all_assets() == before


async def test_http_error_and_broken_payload_do_not_crash():
    def server_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    def broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="bu json degil")

    for handler in (server_error, broken):
        async with _client(handler) as client:
            assert await sync_assets(SYMBOLS, client=client) == 0
    assert await _all_assets() == {}


def test_parse_skips_non_trading_and_missing_symbols():
    payload = json.loads(json.dumps(SAMPLE))
    payload["symbols"][0]["status"] = "BREAK"  # BTCUSDT işleme kapalı
    rows = parse_asset_rows(payload, [*SYMBOLS, "DOGEUSDT"])  # DOGEUSDT cevapta yok
    assert [r["symbol"] for r in rows] == ["ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"]


def test_parse_skips_symbol_without_required_filter():
    payload = json.loads(json.dumps(SAMPLE))
    payload["symbols"][1]["filters"] = [
        f for f in payload["symbols"][1]["filters"] if f["filterType"] != "LOT_SIZE"
    ]
    rows = parse_asset_rows(payload, SYMBOLS)
    assert "ETHUSDT" not in [r["symbol"] for r in rows]
    assert len(rows) == 4
