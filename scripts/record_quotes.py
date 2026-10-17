"""Binance bookTicker kayıt aracı (K3 · görev 3.5).

Gerçek Binance combined bookTicker akışını dinleyip mesajları zaman damgasıyla
JSON Lines (.jsonl) biçiminde backend/tests/fixtures/ altına kaydeder.
Testler ve ReplayProvider canlı Binance'a bağlanmadan bu dosyayı kullanır.

Kullanım:
    python scripts/record_quotes.py
    python scripts/record_quotes.py --duration 600
"""

import argparse
import asyncio
import json
import os
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "backend" / "tests" / "fixtures" / "quotes_sample.jsonl"
DEFAULT_WS_URL = "wss://data-stream.binance.vision"
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT")
DEFAULT_DURATION_SECONDS = 600.0  # 10 dakika
DEFAULT_MIN_INTERVAL_SECONDS = 1.0  # 10 dk boyunca ~600 KB (< 1 MB) için sembol başına 1 sn
MAX_FILE_BYTES = 950_000  # < 1 MB kabul koşulu


def load_env_file(env_path: Path) -> dict[str, str]:
    """Basit .env okuyucu (ek paket gerektirmeden)."""
    values: dict[str, str] = {}
    if not env_path.is_file():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip("'\"")
    return values


def resolve_config() -> tuple[str, list[str]]:
    """WS adresini ve sembol listesini ortam değişkenlerinden veya .env'den okur."""
    env_file = load_env_file(REPO_ROOT / ".env")
    ws_url = os.environ.get("BINANCE_WS_URL") or env_file.get("BINANCE_WS_URL") or DEFAULT_WS_URL
    raw_symbols = os.environ.get("SYMBOLS") or env_file.get("SYMBOLS")
    if raw_symbols:
        symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]
    else:
        symbols = list(DEFAULT_SYMBOLS)
    return ws_url, symbols


def build_stream_url(base_url: str, symbols: Sequence[str]) -> str:
    """Combined bookTicker WebSocket URL'si üretir."""
    streams = "/".join(f"{s.lower()}@bookTicker" for s in symbols)
    return f"{base_url.rstrip('/')}/stream?streams={streams}"


def iso_utc(dt: datetime) -> str:
    """UTC zamanını milisaniye hassasiyetli ISO 8601 dizgesine çevirir."""
    return dt.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def format_jsonl_line(
    raw: str | bytes, received_at: datetime, allowed: set[str] | None = None
) -> tuple[str, str] | None:
    """Ham WS mesajını doğrular ve (symbol, jsonl_satırı) döner; geçersizse None."""
    try:
        payload: dict[str, Any] = json.loads(raw)
        data = payload["data"]
        symbol = str(data["s"]).upper()
        bid_str, bid_qty_str = str(data["b"]), str(data["B"])
        ask_str, ask_qty_str = str(data["a"]), str(data["A"])
        bid, bid_qty = Decimal(bid_str), Decimal(bid_qty_str)
        ask, ask_qty = Decimal(ask_str), Decimal(ask_qty_str)
    except (ValueError, KeyError, TypeError, InvalidOperation):
        return None

    if allowed is not None and symbol not in allowed:
        return None
    if not all(v.is_finite() for v in (bid, ask, bid_qty, ask_qty)):
        return None
    if bid <= 0 or ask <= 0 or bid > ask or bid_qty < 0 or ask_qty < 0:
        return None

    record = {
        "received_at": iso_utc(received_at),
        "stream": payload.get("stream", f"{symbol.lower()}@bookTicker"),
        "data": {
            "u": data["u"],
            "s": symbol,
            "b": bid_str,
            "B": bid_qty_str,
            "a": ask_str,
            "A": ask_qty_str,
        },
    }
    return symbol, json.dumps(record, ensure_ascii=False)


async def record_quotes(
    output_path: Path,
    symbols: Sequence[str],
    ws_url: str = DEFAULT_WS_URL,
    duration_seconds: float = DEFAULT_DURATION_SECONDS,
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
    max_bytes: int = MAX_FILE_BYTES,
    connect: Callable[..., Any] = ws_connect,
) -> int:
    """Belirtilen süre veya boyut sınırına kadar bookTicker mesajlarını kaydeder."""
    allowed = {s.upper() for s in symbols}
    url = build_stream_url(ws_url, symbols)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_written_monotonic: dict[str, float] = {}
    written_count = 0
    written_bytes = 0
    deadline = time.monotonic() + duration_seconds

    with output_path.open("w", encoding="utf-8", newline="\n") as fp:
        async with connect(url, open_timeout=10.0) as websocket:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
                except (TimeoutError, ConnectionClosed):
                    break

                now_mono = time.monotonic()
                parsed = format_jsonl_line(raw, datetime.now(UTC), allowed)
                if parsed is None:
                    continue

                symbol, line = parsed
                prev_mono = last_written_monotonic.get(symbol)
                if prev_mono is not None and (now_mono - prev_mono) < min_interval_seconds:
                    continue

                line_with_nl = line + "\n"
                line_bytes = len(line_with_nl.encode("utf-8"))
                if written_bytes + line_bytes > max_bytes:
                    break

                fp.write(line_with_nl)
                fp.flush()
                last_written_monotonic[symbol] = now_mono
                written_bytes += line_bytes
                written_count += 1

    return written_count


def main() -> None:
    default_ws_url, default_symbols = resolve_config()
    parser = argparse.ArgumentParser(description="Binance bookTicker JSONL kayıt aracı")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Çıktı .jsonl dosya yolu",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION_SECONDS,
        help="Kayıt süresi (saniye, varsayılan: 600)",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=DEFAULT_MIN_INTERVAL_SECONDS,
        help="Sembol başına minimum kayıt aralığı (saniye, varsayılan: 1.0)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=MAX_FILE_BYTES,
        help="Maksimum dosya boyutu (bayt, varsayılan: 950000 < 1 MB)",
    )
    args = parser.parse_args()

    print(
        f"Kayıt başlıyor: semboller={','.join(default_symbols)} "
        f"süre={args.duration}s hedef={args.output}"
    )
    count = asyncio.run(
        record_quotes(
            output_path=args.output,
            symbols=default_symbols,
            ws_url=default_ws_url,
            duration_seconds=args.duration,
            min_interval_seconds=args.min_interval,
            max_bytes=args.max_bytes,
        )
    )
    size_kb = args.output.stat().st_size / 1024 if args.output.exists() else 0.0
    print(f"Tamamlandı: {count} mesaj yazıldı ({size_kb:.1f} KB) -> {args.output}")


if __name__ == "__main__":
    main()
