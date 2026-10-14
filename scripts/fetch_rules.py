"""
Görev 3.2 – Semboller ve Borsa Kuralları
=========================================
Binance exchangeInfo endpoint'inden aktif sembollerin borsa kurallarını
(tickSize, minQty) çeker ve docs/exchange_rules.json dosyasına kaydeder.
"""

import json
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
EXCHANGE_INFO_URL = "https://data-api.binance.vision/api/v3/exchangeInfo"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "docs" / "exchange_rules.json"


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def get_filter_value(filters: list[dict], filter_type: str, field: str) -> str | None:
    """Belirtilen filtre türü ve alan adına göre değeri döndürür."""
    for f in filters:
        if f.get("filterType") == filter_type:
            return f.get(field)
    return None


def fetch_exchange_info() -> dict:
    """Binance API'sinden ham exchangeInfo verisini çeker."""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(EXCHANGE_INFO_URL)
        response.raise_for_status()
        return response.json()


def extract_rules(raw_data: dict) -> list[dict]:
    """
    Yalnızca TRADING durumundaki sembolleri filtreler;
    her biri için tickSize ve minQty değerlerini ayıklar.
    """
    rules = []
    for symbol_info in raw_data.get("symbols", []):
        if symbol_info.get("status") != "TRADING":
            continue

        filters = symbol_info.get("filters", [])
        tick_size = get_filter_value(filters, "PRICE_FILTER", "tickSize")
        min_qty = get_filter_value(filters, "LOT_SIZE", "minQty")

        rules.append(
            {
                "symbol": symbol_info["symbol"],
                "baseAsset": symbol_info.get("baseAsset"),
                "quoteAsset": symbol_info.get("quoteAsset"),
                "tickSize": tick_size,
                "minQty": min_qty,
            }
        )
    return rules


def save_rules(rules: list[dict], output_path: Path) -> None:
    """Kuralları JSON olarak diske kaydeder."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------

def main() -> None:
    raw_data = fetch_exchange_info()
    rules = extract_rules(raw_data)
    save_rules(rules, OUTPUT_FILE)
    print("Kurallar başarıyla çekildi ve kaydedildi")


if __name__ == "__main__":
    main()
