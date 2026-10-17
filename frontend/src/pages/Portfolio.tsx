import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import Decimal from "decimal.js";
import { createChart, ColorType } from "lightweight-charts";
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/* ---------- Ayarlar ---------- */
const API_BASE = "/api";
const SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT"];

// Kırıntı tespiti için adım değerleri (Market.tsx'tekiyle aynı, ortak yere taşınabilir)
const STEP_SIZES: Record<string, string> = {
  BTCUSDT: "0.00001",
  ETHUSDT: "0.0001",
  BNBUSDT: "0.001",
  SOLUSDT: "0.001",
  XRPUSDT: "0.1",
  DOGEUSDT: "1",
  ADAUSDT: "0.1",
  AVAXUSDT: "0.01",
};
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

function extractCode(data: any): string {
  const c =
    data?.code ??
    data?.error?.code ??
    data?.detail?.code ??
    (typeof data?.detail === "string" ? data.detail : undefined) ??
    (typeof data?.error === "string" ? data.error : undefined);
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
const fmtShort = trFormat({ day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
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
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [candleError, setCandleError] = useState("");
  const chartRef = useRef<HTMLDivElement>(null);

  // Portföy: açılışta ve 5 sn'de bir yenilenir
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
    return () => {
      alive = false;
      clearInterval(timer);
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
  const pieData = useMemo(() => {
    if (!pf) return [];
    const rows = [
      { name: "Nakit (USDT)", value: Number(pf.cash) },
      ...openPositions.map((p) => ({ name: p.symbol.replace("USDT", ""), value: Number(p.market_value) })),
    ];
    return rows.filter((r) => r.value > 0);
  }, [pf, openPositions]);

  const histData = useMemo(
    () =>
      history.map((h) => ({
        t: fmtShort.format(toDate(h.taken_at)),
        equity: Number(h.equity),
      })),
    [history]
  );

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
          {pieData.length === 0 ? (
            <p>Gösterilecek varlık yok.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={95} paddingAngle={2}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => `${money(String(v))} USDT`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div style={{ ...cardStyle, minWidth: 0 }}>
          <h3 style={{ marginTop: 0 }}>Portföy değeri (son 1 gün, Türkiye saati)</h3>
          {histError && <p className="order-error">{histError}</p>}
          {!histError && histData.length === 0 ? (
            <p>Henüz değer geçmişi yok.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={histData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="t" minTickGap={30} />
                <YAxis domain={["auto", "auto"]} width={80} tickFormatter={(v) => money(String(v), 0)} />
                <Tooltip formatter={(v) => `${money(String(v))} USDT`} />
                <Line type="monotone" dataKey="equity" stroke="#2563eb" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Mum grafiği */}
      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>
          Mum grafiği{" "}
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>
                {s.replace("USDT", "/USDT")}
              </option>
            ))}
          </select>
        </h3>
        {candleError && <p className="order-error">{candleError}</p>}
        <div ref={chartRef} style={{ width: "100%", height: 320 }} />
      </div>
    </section>
  );
}