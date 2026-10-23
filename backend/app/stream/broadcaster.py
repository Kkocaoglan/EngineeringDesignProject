"""Canlı portföy yayını için süreç içi bildirim mekanizması (K3 · görev 3.8).

Uygulama tek işçi süreçle (uvicorn --workers 1) çalıştığı için kullanıcı başına
açık SSE bağlantılarını bellekteki asyncio.Event kümesiyle uyandırmak yeterlidir.
"""

import asyncio
import contextlib
import uuid
from collections.abc import Iterator

_portfolio_subscribers: dict[uuid.UUID, set[asyncio.Event]] = {}


@contextlib.contextmanager
def subscribe_portfolio(user_id: uuid.UUID | None) -> Iterator[asyncio.Event | None]:
    """Kullanıcının canlı portföy bildirimlerine abone olur; bağlantısı kapanınca temizler."""
    if user_id is None:
        yield None
        return
    event = asyncio.Event()
    subs = _portfolio_subscribers.setdefault(user_id, set())
    subs.add(event)
    try:
        yield event
    finally:
        subs.discard(event)
        if not subs:
            _portfolio_subscribers.pop(user_id, None)


def notify_portfolio_updated(user_id: uuid.UUID) -> None:
    """İşlem tamamlandığında o kullanıcının açık tüm SSE akışlarını beklemeden uyandırır."""
    for event in list(_portfolio_subscribers.get(user_id, ())):
        event.set()
