"""Binance adaptörü yeniden bağlanma (reconnection) testleri (K3 · 3.4).

İnternetsiz: sahte bağlantı ve yerel WebSocket kullanılır.
"""

import asyncio

import pytest

from app.market.binance import BinanceProvider
from app.market.provider import QuoteStore


@pytest.mark.asyncio
async def test_run_forever_reconnects_with_exponential_backoff():
    attempts = 0
    delays = []

    def failing_connect(url, **kwargs):
        nonlocal attempts
        attempts += 1
        raise ConnectionResetError("Bağlantı koptu")

    provider = BinanceProvider(
        symbols=["BTCUSDT"],
        ws_url="ws://127.0.0.1:9999",
        store=QuoteStore(),
        connect=failing_connect,
    )

    original_sleep = asyncio.sleep

    async def mock_sleep(d):
        delays.append(d)
        if len(delays) >= 3:
            raise asyncio.CancelledError()

    try:
        asyncio.sleep = mock_sleep
        with pytest.raises(asyncio.CancelledError):
            await provider.run_forever(base_delay=1.0, max_delay=30.0)
    finally:
        asyncio.sleep = original_sleep

    assert attempts >= 3
    # 1. deneme ~1s, 2. deneme ~2s, 3. deneme ~4s
    assert 1.0 <= delays[0] <= 1.5
    assert 2.0 <= delays[1] <= 2.5
    assert 4.0 <= delays[2] <= 4.5
    assert provider.is_connected is False


@pytest.mark.asyncio
async def test_run_forever_stops_on_cancellation():
    def hanging_connect(url, **kwargs):
        raise ConnectionResetError("Hata")

    provider = BinanceProvider(
        symbols=["BTCUSDT"],
        ws_url="ws://127.0.0.1:9999",
        store=QuoteStore(),
        connect=hanging_connect,
    )
    task = asyncio.create_task(provider.run_forever(base_delay=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.is_connected is False
