import { useEffect, useState } from "react";
import Decimal from "decimal.js";

const API_BASE = "/api";
const PAGE_LIMIT = 50;

type Trade = {
  id: string;
  order_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: string;
  price: string;
  notional: string;
  fee: string;
  created_at: string;
};

type TradesPage = { items: Trade[]; next_cursor: string | null };

// docs/api.md → GET /trades hata kodları
const ERROR_MESSAGES: Record<string, string> = {
  BAD_CURSOR: "Sayfalama bilgisi geçersiz. Listeyi yenileyip tekrar dene.",
  NOT_AUTHENTICATED: "Oturumun kapanmış. Lütfen tekrar giriş yap.",
};

class ApiError extends Error {}

function extractCode(data: any): string {
  const c =
    data?.code ??
    data?.error?.code ??
    data?.detail?.code ??
    (typeof data?.detail === "string" ? data.detail : undefined) ??
    (typeof data?.error === "string" ? data.error : undefined);
  return typeof c === "string" ? c : "UNKNOWN";
}

async function fetchTrades(cursor: string | null): Promise<TradesPage> {
  const params = new URLSearchParams({ limit: String(PAGE_LIMIT) });
  if (cursor) params.set("cursor", cursor);

  const res = await fetch(`${API_BASE}/trades?${params}`, {
    credentials: "include", // oturum çerezi için
  });
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const code = extractCode(data);
    throw new ApiError(ERROR_MESSAGES[code] ?? "İşlem geçmişi alınamadı.");
  }
  return data as TradesPage;
}

// Tarih: Türkiye saati
function formatDate(iso: string) {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  const d = new Date(hasZone ? iso : iso + "Z");
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString("tr-TR", {
    timeZone: "Europe/Istanbul",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// Alışta tutar + komisyon, satışta tutar - komisyon (emir önizlemesiyle aynı mantık)
function totalOf(t: Trade) {
  const n = new Decimal(t.notional);
  const f = new Decimal(t.fee);
  return t.side === "BUY" ? n.plus(f) : n.minus(f);
}

function safe(fn: () => string, fallback: string) {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

export default function TradeHistory() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(cursor: string | null) {
    setLoading(true);
    setError("");
    try {
      const page = await fetchTrades(cursor);
      setTrades((prev) => {
        if (cursor === null) return page.items; // ilk yükleme / yenileme
        const seen = new Set(prev.map((t) => t.id));
        return [...prev, ...page.items.filter((t) => !seen.has(t.id))];
      });
      setNextCursor(page.next_cursor ?? null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sunucuya ulaşılamadı.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(null);
  }, []);

  return (
    <section className="market-page">
      <div className="market-heading">
        <h1>Geçmiş</h1>
        <p>Gerçekleşen işlemlerin (en yeniden eskiye, Türkiye saati).</p>
      </div>

      {error && <p className="order-error">{error}</p>}

      <div className="market-table-wrapper">
        <table className="market-table">
          <thead>
            <tr>
              <th>Tarih</th>
              <th>Coin</th>
              <th>Yön</th>
              <th>Miktar</th>
              <th>Fiyat (USDT)</th>
              <th>Komisyon (USDT)</th>
              <th>Toplam (USDT)</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id}>
                <td>{formatDate(t.created_at)}</td>
                <td><strong>{t.symbol.replace("USDT", "/USDT")}</strong></td>
                <td className={t.side === "BUY" ? "price-up" : "price-down"}>
                  {t.side === "BUY" ? "Alış" : "Satış"}
                </td>
                <td>{safe(() => new Decimal(t.quantity).toString(), t.quantity)}</td>
                <td>{safe(() => new Decimal(t.price).toFixed(2), t.price)}</td>
                <td>{safe(() => new Decimal(t.fee).toFixed(4), t.fee)}</td>
                <td>{safe(() => totalOf(t).toFixed(2), t.notional)}</td>
              </tr>
            ))}
            {!loading && !error && trades.length === 0 && (
              <tr>
                <td colSpan={7}>Henüz işlem yok.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div>
        {nextCursor && (
          <button type="button" onClick={() => load(nextCursor)} disabled={loading}>
            {loading ? "Yükleniyor..." : "Daha fazla yükle"}
          </button>
        )}
        <button type="button" onClick={() => load(null)} disabled={loading}>
          Yenile
        </button>
        {loading && trades.length === 0 && <span> Yükleniyor...</span>}
      </div>
    </section>
  );
}