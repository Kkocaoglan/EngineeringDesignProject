import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import Decimal from "decimal.js";
import { createChart, ColorType } from "lightweight-charts";

/* ---------- Ayarlar ---------- */
const API_BASE = "/api";
const DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"];

// Kırıntı tespiti için adım değerleri (Market.tsx'tekiyle aynı)
const STEP_SIZES: Record<string, string> = {
  BTCUSDT: "0.00001",
  ETHUSDT: "0.0001",
  BNBUSDT: "0.001",
  SOLUSDT: "0.001",
  XRPUSDT: "0.1",
};

type MarketSymbol = { symbol: string };

const COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#475569"];

const ERROR_MESSAGES: Record<string, string> = {
  NOT_AUTHENTICATED: "Oturumun kapanmış. Lütfen tekrar giriş yap.",
};

/* ---------- Tipler (docs/api.md) ---------- */
type Position = {
  symbol: string;
  quantity: string;
  avg_cost: string;
  market_value: string;
  unrealized_pnl: string;
};
type PortfolioData = {
  cash: string;
  equity: string;
  realized_pnl: string;
  unrealized_pnl: string;
  valued_at: string;
  positions: Position[];
};
type EquityPoint = { taken_at: string; equity: string };
type Candle = { open_time: string; open: string; high: string; low: string; close: string };

/* ---------- API ---------- */
class ApiError extends Error {}

function extractCode(data: unknown): string {
  const obj = data as Record<string, any> | null;
  const c =
    obj?.code ??
    obj?.error?.code ??
    obj?.detail?.code ??
    (typeof obj?.detail === "string" ? obj.detail : undefined) ??
    (typeof obj?.error === "string" ? obj.error : undefined);
  return typeof c === "string" ? c : "UNKNOWN";
}

async function apiGet<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  } catch {
    throw new ApiError("Sunucuya ulaşılamadı.");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const code = extractCode(data);
    throw new ApiError(ERROR_MESSAGES[code] ?? "Veri alınamadı.");
  }
  return data as T;
}

/* ---------- Biçimlendirme (para string, decimal.js) ---------- */
function money(s: string, digits = 2) {
  try {
    const [int, frac] = new Decimal(s).toFixed(digits).split(".");
    const neg = int.startsWith("-");
    const body = (neg ? int.slice(1) : int).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return `${neg ? "-" : ""}${body}${frac ? "." + frac : ""}`;
  } catch {
    return s;
  }
}

function qty(s: string) {
  try {
    return new Decimal(s).toFixed(); // üstel gösterim yok, gereksiz sıfır yok
  } catch {
    return s;
  }
}

// Sadece renk için işaret bakılır, K/Z hesaplanmaz
function signClass(s: string) {
  try {
    const d = new Decimal(s);
    if (d.gt(0)) return "price-up";
    if (d.lt(0)) return "price-down";
  } catch {
    /* geçersiz değer */
  }
  return "";
}

// Satılamayan kırıntı: miktar > 0 ama borsa adımının (stepSize) altında
function isDust(p: Position) {
  const step = STEP_SIZES[p.symbol];
  if (!step) return false;
  try {
    const q = new Decimal(p.quantity);
    return q.gt(0) && q.lt(step);
  } catch {
    return false;
  }
}

function hasQuantity(p: Position) {
  try {
    return new Decimal(p.quantity).gt(0);
  } catch {
    return false;
  }
}

/* ---------- Zaman (Türkiye saati) ---------- */
const trFormat = (opts: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat("tr-TR", { timeZone: "Europe/Istanbul", ...opts });
const fmtTick = trFormat({ hour: "2-digit", minute: "2-digit" });
const fmtFull = trFormat({
  day: "2-digit", month: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit", second: "2-digit",
});

function toDate(iso: string) {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : iso + "Z");
}
function toSeconds(iso: string) {
  return Math.floor(toDate(iso).getTime() / 1000);
}

/* ---------- Stil ---------- */
const cardStyle: CSSProperties = {
  padding: 16,
  border: "1px solid #cbd5e1",
  borderRadius: 12,
  background: "#ffffff",
  color: "#0f172a",
};
const gridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: 12,
  marginBottom: 16,
};
const chartGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: 12,
  marginBottom: 16,
};

/* ---------- Sayfa ---------- */
export default function Portfolio() {
  const [pf, setPf] = useState<PortfolioData | null>(null);
  const [pfError, setPfError] = useState("");
  const [history, setHistory] = useState<EquityPoint[]>([]);
  const [histError, setHistError] = useState("");
  const [symbols, setSymbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [candleError, setCandleError] = useState("");
  const chartRef = useRef<HTMLDivElement>(null);
  const equityChartRef = useRef<HTMLDivElement>(null);

  // Sembol listesini /api/markets'ten al
  useEffect(() => {
    let alive = true;
    apiGet<MarketSymbol[]>("/markets")
      .then((rows) => {
        if (alive && Array.isArray(rows) && rows.length > 0) {
          setSymbols(rows.map((r) => r.symbol));
        }
      })
      .catch(() => {
        /* hata durumunda 5 varsayılan sembol kalır */
      });
    return () => {
      alive = false;
    };
  }, []);

  // Portföy: açılışta, 5 sn'de bir ve SSE portfolio_updated olayı geldiğinde yenilenir
  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const data = await apiGet<PortfolioData>("/portfolio");
        if (!alive) return;
        setPf(data);
        setPfError("");
      } catch (e) {
        if (alive) setPfError(e instanceof ApiError ? e.message : "Portföy alınamadı.");
      }
    }
    load();
    const timer = setInterval(load, 5000);

    const es = new EventSource("/api/stream", { withCredentials: true });
    es.addEventListener("portfolio_updated", (ev) => {
      if (!alive) return;
      try {
        const data: PortfolioData = JSON.parse((ev as MessageEvent).data);
        setPf(data);
        setPfError("");
      } catch {
        /* bozuk mesaj */
      }
    });

    return () => {
      alive = false;
      clearInterval(timer);
      es.close();
    };
  }, []);

  // Portföy değeri geçmişi: açılışta ve 30 sn'de bir
  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const data = await apiGet<EquityPoint[]>("/portfolio/history?range=1d");
        if (!alive) return;
        setHistory(data);
        setHistError("");
      } catch (e) {
        if (alive) setHistError(e instanceof ApiError ? e.message : "Değer geçmişi alınamadı.");
      }
    }
    load();
    const timer = setInterval(load, 30000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  // Portföy değeri çizgi grafiği (lightweight-charts)
  useEffect(() => {
    const el = equityChartRef.current;
    if (!el || history.length === 0) return;

    const chart = createChart(el, {
      width: el.clientWidth,
      height: 260,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#64748b" },
      grid: {
        vertLines: { color: "rgba(148,163,184,0.2)" },
        horzLines: { color: "rgba(148,163,184,0.2)" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (t: unknown) => fmtTick.format(new Date(Number(t) * 1000)),
      },
      localization: {
        timeFormatter: (t: unknown) => fmtFull.format(new Date(Number(t) * 1000)),
      },
    });

    const lineSeries = chart.addLineSeries({
      color: "#2563eb",
      lineWidth: 2,
    });

    const byTime = new Map<number, { time: number; value: number }>();
    for (const h of history) {
      const time = toSeconds(h.taken_at);
      if (Number.isNaN(time)) continue;
      byTime.set(time, { time, value: Number(h.equity) });
    }
    const data = [...byTime.values()].sort((a, b) => a.time - b.time);
    lineSeries.setData(data as never);
    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [history]);

  // Mum grafiği: coin değişince yeniden kurulur
  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;
    setCandleError("");

    const chart = createChart(el, {
      width: el.clientWidth,
      height: 320,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#64748b" },
      grid: {
        vertLines: { color: "rgba(148,163,184,0.2)" },
        horzLines: { color: "rgba(148,163,184,0.2)" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (t: unknown) => fmtTick.format(new Date(Number(t) * 1000)),
      },
      localization: {
        timeFormatter: (t: unknown) => fmtFull.format(new Date(Number(t) * 1000)),
      },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#16a34a",
      downColor: "#dc2626",
      wickUpColor: "#16a34a",
      wickDownColor: "#dc2626",
      borderVisible: false,
    });

    let alive = true;
    (async () => {
      try {
        const rows = await apiGet<Candle[]>(`/markets/${symbol}/candles?limit=300`);
        if (!alive) return;
        // Grafik çizimi için sayıya çevrilir (para hesabı yapılmaz)
        const byTime = new Map<number, { time: number; open: number; high: number; low: number; close: number }>();
        for (const r of rows) {
          const time = toSeconds(r.open_time);
          if (Number.isNaN(time)) continue;
          byTime.set(time, {
            time,
            open: Number(r.open),
            high: Number(r.high),
            low: Number(r.low),
            close: Number(r.close),
          });
        }
        const data = [...byTime.values()].sort((a, b) => a.time - b.time);
        series.setData(data as never); // time tipi kütüphanede özel bir sayı tipi
        chart.timeScale().fitContent();
      } catch (e) {
        if (alive) setCandleError(e instanceof ApiError ? e.message : "Mum verisi alınamadı.");
      }
    })();

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    ro.observe(el);

    return () => {
      alive = false;
      ro.disconnect();
      chart.remove();
    };
  }, [symbol]);

  const openPositions = useMemo(() => (pf ? pf.positions.filter(hasQuantity) : []), [pf]);
  const dustPositions = useMemo(() => openPositions.filter(isDust), [openPositions]);

  // Grafik için sayıya çevrilir (sadece çizim)
  const pieSlices = useMemo(() => {
    if (!pf) return [];
    const rows = [
      { name: "Nakit (USDT)", value: Number(pf.cash) },
      ...openPositions.map((p) => ({ name: p.symbol.replace("USDT", ""), value: Number(p.market_value) })),
    ].filter((r) => r.value > 0);

    const total = rows.reduce((acc, r) => acc + r.value, 0);
    if (total <= 0) return [];

    const circumference = 2 * Math.PI * 65;
    let offset = 0;
    return rows.map((r, i) => {
      const ratio = r.value / total;
      const length = ratio * circumference;
      const slice = {
        ...r,
        color: COLORS[i % COLORS.length],
        percent: ratio * 100,
        length,
        circumference,
        offset,
      };
      offset += length;
      return slice;
    });
  }, [pf, openPositions]);

  const summary = pf
    ? [
        { label: "Nakit (USDT)", value: pf.cash, signed: false },
        { label: "Toplam değer (USDT)", value: pf.equity, signed: false },
        { label: "Gerçekleşmiş K/Z (USDT)", value: pf.realized_pnl, signed: true },
        { label: "Gerçekleşmemiş K/Z (USDT)", value: pf.unrealized_pnl, signed: true },
      ]
    : [];

  return (
    <section className="market-page">
      <div className="market-heading">
        <h1>Portföy</h1>
        <p>
          Varlıkların ve kâr/zarar durumun.
          {pf && ` Son değerleme: ${fmtFull.format(toDate(pf.valued_at))}`}
        </p>
      </div>

      {pfError && <p className="order-error">{pfError}</p>}
      {!pf && !pfError && <p>Yükleniyor...</p>}

      {pf && (
        <>
          {/* Özet kartları */}
          <div style={gridStyle}>
            {summary.map((c) => (
              <div key={c.label} style={cardStyle}>
                <div style={{ fontSize: 13, color: "#64748b" }}>{c.label}</div>
                <div
                  className={c.signed ? signClass(c.value) : ""}
                  style={{ fontSize: 22, fontWeight: 600, marginTop: 4 }}
                >
                  {money(c.value)}
                </div>
              </div>
            ))}
          </div>

          {/* Pozisyonlar */}
          <h2>Pozisyonlar</h2>
          <div className="market-table-wrapper">
            <table className="market-table">
              <thead>
                <tr>
                  <th>Coin</th>
                  <th>Miktar</th>
                  <th>Ort. maliyet (USDT)</th>
                  <th>Piyasa değeri (USDT)</th>
                  <th>Gerçekleşmemiş K/Z (USDT)</th>
                </tr>
              </thead>
              <tbody>
                {openPositions.map((p) => (
                  <tr key={p.symbol}>
                    <td>
                      <strong>{p.symbol.replace("USDT", "/USDT")}</strong>
                      {isDust(p) && (
                        <span
                          title="Bu miktar borsanın minimum adımının altında, satılamaz."
                          style={{ marginLeft: 8, color: "#b45309", fontSize: 12 }}
                        >
                          kırıntı
                        </span>
                      )}
                    </td>
                    <td>{qty(p.quantity)}</td>
                    <td>{money(p.avg_cost)}</td>
                    <td>{money(p.market_value)}</td>
                    <td className={signClass(p.unrealized_pnl)}>{money(p.unrealized_pnl)}</td>
                  </tr>
                ))}
                {openPositions.length === 0 && (
                  <tr>
                    <td colSpan={5}>Henüz pozisyonun yok.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Satılamayan kırıntılar */}
          {dustPositions.length > 0 && (
            <div style={{ ...cardStyle, marginTop: 12, borderColor: "#f59e0b" }}>
              <strong>Satılamayan kırıntı</strong>
              <p style={{ margin: "6px 0" }}>
                Aşağıdaki miktarlar borsanın minimum adım değerinin altında olduğu için satılamaz:
              </p>
              <ul style={{ margin: 0 }}>
                {dustPositions.map((p) => (
                  <li key={p.symbol}>
                    {p.symbol.replace("USDT", "")}: {qty(p.quantity)} (≈ {money(p.market_value, 4)} USDT)
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Pasta ve değer grafiği */}
      <div style={{ ...chartGridStyle, marginTop: 16 }}>
        <div style={{ ...cardStyle, minWidth: 0 }}>
          <h3 style={{ marginTop: 0 }}>Varlık dağılımı</h3>
          {pieSlices.length === 0 ? (
            <p>Gösterilecek varlık yok.</p>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap", minHeight: 260 }}>
              <svg width="180" height="180" viewBox="0 0 180 180" style={{ flexShrink: 0 }}>
                <g transform="rotate(-90 90 90)">
                  {pieSlices.map((s) => (
                    <circle
                      key={s.name}
                      cx="90"
                      cy="90"
                      r="65"
                      fill="transparent"
                      stroke={s.color}
                      strokeWidth="28"
                      strokeDasharray={`${s.length} ${s.circumference}`}
                      strokeDashoffset={-s.offset}
                    >
                      <title>{`${s.name}: ${money(String(s.value))} USDT (%${s.percent.toFixed(1)})`}</title>
                    </circle>
                  ))}
                </g>
              </svg>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
                {pieSlices.map((s) => (
                  <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        width: 12,
                        height: 12,
                        borderRadius: 3,
                        background: s.color,
                        display: "inline-block",
                      }}
                    />
                    <span>{s.name}:</span>
                    <strong>{money(String(s.value))} USDT</strong>
                    <span style={{ color: "#64748b" }}>(%{s.percent.toFixed(1)})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div style={{ ...cardStyle, minWidth: 0 }}>
          <h3 style={{ marginTop: 0 }}>Portföy değeri (son 1 gün, Türkiye saati)</h3>
          {histError && <p className="order-error">{histError}</p>}
          {!histError && history.length === 0 ? (
            <p>Henüz değer geçmişi yok.</p>
          ) : (
            <div ref={equityChartRef} style={{ width: "100%", height: 260 }} />
          )}
        </div>
      </div>

      {/* Mum grafiği */}
      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>
          Mum grafiği{" "}
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s.replace("USDT", "/USDT")}
              </option>
            ))}
          </select>
        </h3>
        {candleError && <p className="order-error">{candleError}</p>}
        <div ref={chartRef} style={{ width: "100%", height: 320 }} />
        <p style={{ margin: "8px 0 0", fontSize: 11, color: "#64748b", textAlign: "right" }}>
          Grafik altyapısı:{" "}
          <a
            href="https://www.tradingview.com/lightweight-charts/"
            target="_blank"
            rel="noreferrer"
            style={{ color: "#2563eb" }}
          >
            TradingView Lightweight Charts™
          </a>
        </p>
      </div>
    </section>
  );
}
