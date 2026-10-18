"""İstek sınırlama (K1 · Hafta 3 · görev 1.11).

Kayan pencereli, bellek içi sınırlayıcı. Anahtar IP değil, e-posta (giriş) ve hesap (emir)
olur: Vite proxy arkasında bütün kullanıcılar aynı IP'den geliyormuş gibi görünür, IP'ye göre
sınır herkesi birlikte kilitlerdi (Ek Rehber v1.1). Uygulama tek işçi süreçle çalıştığı için
(uvicorn --workers 1) bellekte tutmak yeterlidir; yeni bir paket (ör. slowapi) eklenmedi.
"""

import math
import time
from collections import deque
from collections.abc import Callable

from app.config import get_settings
from app.errors import AppError

_SWEEP_AT = 10_000  # bu kadar anahtar birikince süresi dolanlar temizlenir


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window_seconds
        self.clock = clock  # testler sahte saat verir
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> None:
        """Bir isteği sayar; pencere doluysa 429 TOO_MANY_REQUESTS fırlatır (sayılmaz)."""
        now = self.clock()
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            retry_after = max(1, math.ceil(q[0] + self.window - now))
            raise AppError(429, "TOO_MANY_REQUESTS",
                           f"Çok fazla istek. {retry_after} saniye sonra tekrar deneyin.",
                           headers={"Retry-After": str(retry_after)})
        q.append(now)
        if len(self._hits) > _SWEEP_AT:
            self._sweep(now)

    def _sweep(self, now: float) -> None:
        for key in [k for k, q in self._hits.items() if not q or q[-1] <= now - self.window]:
            del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


_settings = get_settings()
# Giriş: e-posta başına dakikada 5 deneme · Emir: hesap başına saniyede 5 istek
login_limiter = RateLimiter(_settings.login_attempts_per_minute, 60.0)
order_limiter = RateLimiter(_settings.orders_per_second, 1.0)
