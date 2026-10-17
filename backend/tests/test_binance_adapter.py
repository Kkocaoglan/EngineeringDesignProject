"""Binance adaptörü (K3 · 3.3). İnternetsiz: istemci yerel sahte Binance sunucusuna bağlanır."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from websockets.asyncio.server import serve

from app.market.binance import BinanceProvider, parse_book_ticker, stream_url
from app.market.clock import SystemClock
from app.market.provider import QuoteStore
from app.orders.quotes import Quote
from tests.fake_clock import FakeClock

NOW = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def message(symbol="BTCUSDT", bid="83180.00000000", bid_qty="3.70791000",
            ask="83180.01000000", ask_qty="5.85900000") -> str:
    """spike raporundaki gerçek combined stream mesajıyla aynı biçim."""
    return json.dumps({
        "stream": f"{symbol.lower()}@bookTicker",
        "data": {"u": 101379076336, "s": symbol, "b": bid, "B": bid_qty, "a": ask, "A": ask_qty},
    })


def test_stream_url_is_one_combined_stream():
    url = stream_url("wss://data-stream.binance.vision/", SYMBOLS)
    assert url == (
        "wss://data-stream.binance.vision/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker"
    )


def test_parse_valid_message_gives_decimal_quote():
    quote = parse_book_ticker(message(), NOW)
    assert quote == Quote(
        "BTCUSDT", Decimal("83180.00000000"), Decimal("83180.01000000"),
        Decimal("3.70791000"), Decimal("5.85900000"), NOW,
    )
    for value in (quote.bid, quote.ask, quote.bid_qty, quote.ask_qty):
        assert isinstance(value, Decimal)
    assert quote.received_at.tzinfo is not None


def test_parse_accepts_bytes():
    assert parse_book_ticker(message().encode(), NOW) is not None


@pytest.mark.parametrize("raw", [
    "bu json degil",
    "[]",
    json.dumps({"stream": "x"}),                                   # data yok
    json.dumps({"data": "metin"}),                                 # data sözlük değil
    json.dumps({"data": {"s": "BTCUSDT"}}),                        # alanlar eksik
    message(bid="abc"),                                            # sayı değil
    message(bid="NaN"),
    message(ask="Infinity"),
    message(bid="0"),                                              # sıfır fiyat
    message(bid="-1"),                                             # negatif fiyat
    message(bid="100", ask="99"),                                  # bid > ask
    message(bid_qty="-1"),                                         # negatif miktar
])
def test_parse_rejects_bad_messages(raw):
    assert parse_book_ticker(raw, NOW) is None


def test_parse_ignores_symbols_we_did_not_subscribe_to():
    assert parse_book_ticker(message("DOGEUSDT"), NOW, allowed=set(SYMBOLS)) is None
    assert parse_book_ticker(message("BTCUSDT"), NOW, allowed=set(SYMBOLS)) is not None


def test_store_keeps_latest_quote_per_symbol():
    store = QuoteStore()
    first = parse_book_ticker(message(bid="100", ask="101"), NOW)
    second = parse_book_ticker(message(bid="102", ask="103"), NOW)
    eth = parse_book_ticker(message("ETHUSDT", bid="3000", ask="3001"), NOW)
    for quote in (first, second, eth):
        store.update(quote)

    assert store.get("BTCUSDT") == second
    assert store.get("SOLUSDT") is None
    snapshot = store.snapshot()
    assert set(snapshot) == {"BTCUSDT", "ETHUSDT"}
    snapshot.clear()  # dışarıdan değiştirmek hafızayı bozmaz
    assert store.get("BTCUSDT") == second


def test_system_clock_is_utc():
    assert SystemClock().now().utcoffset().total_seconds() == 0


async def test_provider_reads_stream_from_local_fake_binance():
    seen_paths: list[str] = []
    frames = [
        message(bid="100.00", ask="100.10"),
        "bozuk mesaj",                                  # atlanır, bağlantıyı bozmaz
        message("ETHUSDT", bid="3000.00", ask="3000.50"),
        message("DOGEUSDT", bid="1", ask="2"),          # abone olmadığımız sembol
        message(bid="101.00", ask="101.10"),            # BTC'nin yeni fiyatı
    ]

    async def fake_binance(connection):
        seen_paths.append(connection.request.path)
        for frame in frames:
            await connection.send(frame)

    clock = FakeClock()
    async with serve(fake_binance, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        provider = BinanceProvider(SYMBOLS, ws_url=f"ws://127.0.0.1:{port}", clock=clock)
        await provider.run()  # sunucu kapatınca temiz döner

    assert seen_paths == ["/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker"]
    snapshot = provider.snapshot()
    assert set(snapshot) == {"BTCUSDT", "ETHUSDT"}
    assert snapshot["BTCUSDT"].bid == Decimal("101.00")  # son mesaj kazanır
    assert snapshot["ETHUSDT"].ask == Decimal("3000.50")
    assert snapshot["BTCUSDT"].received_at == clock.now()  # bizim saatimiz, Binance'ın değil
    assert provider.get_quote("BTCUSDT") == snapshot["BTCUSDT"]
    assert provider.get_quote("DOGEUSDT") is None


async def test_received_at_is_taken_per_message():
    class TickingClock(FakeClock):
        """Her now() çağrısında 1 sn ilerler: iki mesajın received_at değeri farklı olmalı."""

        def now(self) -> datetime:
            current = super().now()
            self.advance(1)
            return current

    clock = TickingClock()
    start = clock.now()  # start okuması da saati 1 sn ilerletir

    async def fake_binance(connection):
        await connection.send(message(bid="100", ask="101"))
        await connection.send(message("ETHUSDT", bid="3000", ask="3001"))

    async with serve(fake_binance, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        provider = BinanceProvider(SYMBOLS, ws_url=f"ws://127.0.0.1:{port}", clock=clock)
        await provider.run()

    btc, eth = provider.get_quote("BTCUSDT"), provider.get_quote("ETHUSDT")
    assert (btc.received_at - start).total_seconds() == 1
    assert (eth.received_at - btc.received_at).total_seconds() == 1
