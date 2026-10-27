"""Borsa kuralları (K3 · görev 3.2): Binance exchangeInfo → assets tablosu.

Sadece .env'deki SYMBOLS çekilir. Backend açılışında çalışır (app.main lifespan).
Binance'e ulaşılamazsa uygulama çökmez; tablodaki son değerlerle devam edilir.
Sayılar Decimal(str(...)) ile okunur, asla float kullanılmaz.
"""

import json
import logging
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.db import SessionLocal
from app.models import Asset

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 10.0
_UPDATE_COLUMNS = ("base_asset", "quote_asset", "tick_size", "step_size", "min_qty", "min_notional")
DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "fixtures"
    / "exchange_info_sample.json"
)


async def fetch_exchange_info(
    symbols: Sequence[str], client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Sadece verilen sembollerin exchangeInfo cevabını döner."""
    url = f"{get_settings().binance_rest_url}/api/v3/exchangeInfo"
    params = {"symbols": json.dumps(list(symbols), separators=(",", ":"))}
    if client is None:
        async with httpx.AsyncClient() as own_client:
            response = await own_client.get(url, params=params, timeout=FETCH_TIMEOUT)
    else:
        response = await client.get(url, params=params, timeout=FETCH_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _row_from_symbol_info(info: dict[str, Any]) -> dict[str, Any] | None:
    """Tek sembolün assets satırı. Eksik/geçersiz kural varsa None (sembol atlanır)."""
    symbol = info["symbol"]
    filters = {f["filterType"]: f for f in info.get("filters", [])}
    # Yeni sembollerde NOTIONAL, eski sembollerde MIN_NOTIONAL
    notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")
    try:
        row = {
            "symbol": symbol,
            "base_asset": info["baseAsset"],
            "quote_asset": info["quoteAsset"],
            "tick_size": Decimal(str(filters["PRICE_FILTER"]["tickSize"])),
            "step_size": Decimal(str(filters["LOT_SIZE"]["stepSize"])),
            "min_qty": Decimal(str(filters["LOT_SIZE"]["minQty"])),
            "min_notional": Decimal(str(notional["minNotional"])) if notional else None,
        }
    except (KeyError, TypeError, ArithmeticError):
        logger.warning("%s için borsa kuralları okunamadı, atlandı", symbol)
        return None
    if row["min_notional"] is None:
        logger.warning("%s için NOTIONAL/MIN_NOTIONAL filtresi yok, atlandı", symbol)
        return None
    if row["tick_size"] <= 0 or row["step_size"] <= 0:
        logger.warning("%s için tick_size/step_size geçersiz, atlandı", symbol)
        return None
    return row


def parse_asset_rows(payload: dict[str, Any], symbols: Sequence[str]) -> list[dict[str, Any]]:
    """exchangeInfo cevabından, istenen ve TRADING durumundaki semboller için satır üretir."""
    by_symbol = {s["symbol"]: s for s in payload["symbols"]}
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        info = by_symbol.get(symbol)
        if info is None:
            logger.warning("%s exchangeInfo cevabında yok, atlandı", symbol)
            continue
        if info.get("status") != "TRADING":
            logger.warning("%s TRADING durumunda değil (%s), atlandı", symbol, info.get("status"))
            continue
        row = _row_from_symbol_info(info)
        if row is not None:
            rows.append(row)
    return rows


async def sync_assets(
    symbols: Sequence[str] | None = None,
    client: httpx.AsyncClient | None = None,
    session_factory=SessionLocal,
) -> int:
    """Kuralları çekip assets tablosuna upsert eder; yazılan satır sayısını döner.

    Binance'e ulaşılamaz ya da cevap bozuksa hata fırlatmaz:
    - replay modundaysa tests/fixtures/exchange_info_sample.json dosyasından yükler;
    - diğer modlarda 0 döner: tablodaki son değerler kalır ve uygulama onlarla devam eder.
    """
    settings = get_settings()
    symbols = list(symbols) if symbols is not None else settings.symbol_list
    try:
        payload = await fetch_exchange_info(symbols, client)
        rows = parse_asset_rows(payload, symbols)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        if settings.market_source != "replay":
            logger.warning(
                "exchangeInfo alınamadı, assets tablosundaki son değerlerle devam: %r", exc
            )
            return 0
        try:
            payload = json.loads(DEFAULT_FIXTURE_PATH.read_text(encoding="utf-8"))
            rows = parse_asset_rows(payload, symbols)
            logger.info(
                "exchangeInfo indirilemedi (%r), replay fixture'ından yüklendi: %s",
                exc,
                DEFAULT_FIXTURE_PATH.name,
            )
        except (OSError, ValueError, KeyError, TypeError) as fallback_exc:
            logger.warning("Replay exchangeInfo fixture okunamadı: %r", fallback_exc)
            return 0
    if not rows:
        logger.warning("exchangeInfo'dan hiç geçerli kural çıkmadı, assets tablosu değişmedi")
        return 0

    stmt = pg_insert(Asset).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Asset.symbol],
        set_={**{c: stmt.excluded[c] for c in _UPDATE_COLUMNS}, "updated_at": func.now()},
    )
    async with session_factory() as session:
        await session.execute(stmt)
        await session.commit()
    logger.info("assets güncellendi: %s", ", ".join(r["symbol"] for r in rows))
    return len(rows)
