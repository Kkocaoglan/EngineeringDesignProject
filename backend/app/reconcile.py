"""Mutabakat (K1 · Hafta 3 · görev 1.12).

Her hesap için iki değişmezi denetler:
  1. accounts.cash == SUM(cash_entries.amount)            (bakiye = nakit defterinin toplamı)
  2. positions.quantity == SUM(alım miktarı) − SUM(satım)  (pozisyon = işlemlerin toplamı)
Tutarsızlık varsa listeler ve 1 koduyla çıkar; yoksa "0 tutarsızlık" yazar ve 0 ile çıkar.

Kullanım:  cd backend && python -m app.reconcile
Docker'da: docker compose exec backend python -m app.reconcile
(ops/restore.sh geri yüklemeden sonra bu komutu çalıştırır.)
"""

import asyncio
import sys
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.money import fmt


@dataclass(frozen=True)
class Inconsistency:
    account_id: uuid.UUID
    kind: str  # "cash" | "position"
    symbol: str | None
    expected: Decimal  # defterden / işlemlerden hesaplanan
    actual: Decimal  # tabloda yazan

    def __str__(self) -> str:
        what = "nakit" if self.kind == "cash" else f"pozisyon {self.symbol}"
        return (f"hesap {self.account_id} · {what}: tabloda {fmt(self.actual)}, "
                f"hesaplanan {fmt(self.expected)} (fark {fmt(self.actual - self.expected)})")


_CASH_SQL = text("""
    SELECT a.id, a.cash, COALESCE(SUM(ce.amount), 0) AS ledger
    FROM accounts a
    LEFT JOIN cash_entries ce ON ce.account_id = a.id
    GROUP BY a.id, a.cash
    HAVING a.cash <> COALESCE(SUM(ce.amount), 0)
""")

# Pozisyon tablosu ile işlem toplamı karşılaştırılır; iki taraftan birinde hiç satır olmayan
# (ör. işlemi olup pozisyonu silinmiş) durumlar da yakalansın diye FULL OUTER JOIN.
_POSITION_SQL = text("""
    WITH traded AS (
        SELECT account_id, symbol,
               SUM(CASE WHEN side = 'BUY' THEN quantity ELSE -quantity END) AS qty
        FROM trades
        GROUP BY account_id, symbol
    )
    SELECT COALESCE(p.account_id, t.account_id) AS account_id,
           COALESCE(p.symbol, t.symbol) AS symbol,
           COALESCE(t.qty, 0) AS expected,
           COALESCE(p.quantity, 0) AS actual
    FROM positions p
    FULL OUTER JOIN traded t ON t.account_id = p.account_id AND t.symbol = p.symbol
    WHERE COALESCE(p.quantity, 0) <> COALESCE(t.qty, 0)
""")


async def reconcile(conn: AsyncConnection) -> list[Inconsistency]:
    issues = [Inconsistency(r.id, "cash", None, r.ledger, r.cash)
              for r in await conn.execute(_CASH_SQL)]
    issues += [Inconsistency(r.account_id, "position", r.symbol, r.expected, r.actual)
               for r in await conn.execute(_POSITION_SQL)]
    return issues


async def _run() -> int:
    from app.db import engine  # komut satırından çalışınca bağlantı burada kurulur

    async with engine.connect() as conn:
        accounts = (await conn.execute(text("SELECT count(*) FROM accounts"))).scalar_one()
        issues = await reconcile(conn)
    await engine.dispose()
    for issue in issues:
        print(f"TUTARSIZ  {issue}")
    print(f"{accounts} hesap denetlendi · {len(issues)} tutarsızlık")
    return 1 if issues else 0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Türkçe Windows konsolunda da düzgün yazsın
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
