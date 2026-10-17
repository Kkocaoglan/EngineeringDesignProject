"""Tüm ayarlar .env'den okunur. Kodun içine ayar gömülmez."""

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str
    secret_key: str
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    session_max_age_seconds: int = 7 * 24 * 3600

    starting_cash: Decimal = Decimal("10000")
    fee_rate: Decimal = Decimal("0.001")
    price_tolerance: Decimal = Decimal("0.01")
    symbols: str = "BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT"
    market_source: str = "live"
    binance_rest_url: str = "https://data-api.binance.vision"
    binance_ws_url: str = "wss://data-stream.binance.vision"
    quote_stale_seconds: int = 5

    # Testlerde "null": her istek kendi bağlantısını açar (event loop sorunlarını önler)
    db_pool: str = "default"

    @property
    def symbol_list(self) -> list[str]:
        """SYMBOLS=BTCUSDT,ETHUSDT → ["BTCUSDT", "ETHUSDT"]"""
        return [s.strip().upper() for s in self.symbols.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
