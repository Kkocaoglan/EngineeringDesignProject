import { useEffect, useRef, useState } from "react";
import Decimal from "decimal.js";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/languageContextDef";
import { useLiveStream } from "../hooks/useLiveStream";

/* ---------- Ayarlar ---------- */
const ORDER_URL = "/api/orders";
const COMMISSION_RATE = "0.001"; // yüzde 0,1 (sözleşme örneğiyle uyumlu)

const STEP_SIZES: Record<string, string> = {
  BTCUSDT: "0.00001",
  ETHUSDT: "0.0001",
  BNBUSDT: "0.001",
  SOLUSDT: "0.001",
  XRPUSDT: "0.1",
};
const NAMES: Record<string, string> = {
  BTCUSDT: "Bitcoin",
  ETHUSDT: "Ethereum",
  BNBUSDT: "BNB",
  XRPUSDT: "XRP",
  SOLUSDT: "Solana",
};
// Fiyatın ekranda kaç basamakla gösterileceği (varsayılan 2)
const PRICE_DIGITS: Record<string, number> = { XRPUSDT: 4 };
const digitsOf = (symbol: string) => PRICE_DIGITS[symbol] ?? 2;

const ERROR_MESSAGES: Record<string, string> = {
  INSUFFICIENT_FUNDS: "Yetersiz bakiye.",
  INSUFFICIENT_POSITION: "Elinde bu kadar coin yok.",
  FILTER_VIOLATION: "Miktar veya tutar borsa kurallarına uymuyor.",
  DEPTH_EXCEEDED: "Bu fiyattan bu kadar miktar alınamıyor, daha az dene.",
  QUOTE_STALE: "Canlı fiyat alınamıyor, emirler geçici olarak kapalı.",
  PRICE_MOVED: "Fiyat değişti. Önizlemeyi kontrol edip tekrar dene.",
  IDEMPOTENCY_KEY_REUSED: "Bu emir zaten gönderildi.",
  NOT_AUTHENTICATED: "Emir vermek için giriş yapmalısın.",
  TOO_MANY_REQUESTS: "Çok hızlı emir veriyorsun, biraz bekle.",
};

/* ---------- Önizleme hesabı (decimal.js) ---------- */
const floorToStep = (v: Decimal, step: Decimal) => v.div(step).floor().mul(step);

function calcPreview(
  side: "BUY" | "SELL",
  price: string,
  quantity: string,
  stepSize: string,
  cash: string | null
) {
  try {
    const p = new Decimal(price);
    const rawQty = new Decimal(quantity);
    const step = new Decimal(stepSize);
    const rate = new Decimal(COMMISSION_RATE);
    if (p.lte(0) || rawQty.lte(0) || step.lte(0)) return null;

    const qty = floorToStep(rawQty, step);
    const notional = p.mul(qty);
    const fee = notional.mul(rate);
    const total = side === "BUY" ? notional.plus(fee) : notional.minus(fee);

    // Bakiye kontrolü sadece alışta (satışta backend kontrol ediyor)
    let remaining: Decimal | null = null;
    let maxQty: Decimal | null = null;
    let insufficient = false;
    if (side === "BUY" && cash !== null) {
      const balance = new Decimal(cash);
      remaining = balance.minus(total);
      maxQty = floorToStep(balance.div(p.mul(rate.plus(1))), step);
      insufficient = total.gt(balance);
    }

    return {
      qty,
      tooSmall: qty.lte(0),
      rounded: !qty.eq(rawQty),
      fee,
      total,
      remaining,
      maxQty,
      insufficient,
      dec: step.decimalPlaces(),
    };
  } catch {
    return null;
  }
}

/* ---------- Emir gönderme ---------- */
type OrderOk = {
  symbol: string;
  quantity: string;
  fill_price: string;
  fee: string;
  cash_after: string;
};
type SubmitResult =
  | { ok: true; data: OrderOk }
  | { ok: false; code: string; message: string };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const BACKOFF = [1000, 2000, 4000]; // aynı anahtarla 1-2-4 sn arayla tekrar

async function submitOrder(body: object, key: string, onChecking: () => void): Promise<SubmitResult> {
  for (let i = 0; i <= BACKOFF.length; i++) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 10_000); // 10 sn zaman aşımı
    try {
      const res = await fetch(ORDER_URL, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", "Idempotency-Key": key },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      const data = await res.json().catch(() => null);
      if (res.ok) return { ok: true, data: data as OrderOk };
      if (res.status < 500) {
        // 4xx kesin sonuçtur, tekrar denenmez
        const code = (data as { error?: { code?: string } } | null)?.error?.code ?? "UNKNOWN";
        return { ok: false, code, message: ERROR_MESSAGES[code] ?? "Emir reddedildi." };
      }
      // 5xx: aşağıda aynı anahtarla tekrar denenir
    } catch {
      // zaman aşımı veya ağ hatası: tekrar denenir
    } finally {
      clearTimeout(timer);
    }
    if (i === BACKOFF.length) break;
    onChecking();
    await sleep(BACKOFF[i]);
  }
  return {
    ok: false,
    code: "UNKNOWN_OUTCOME",
    message: "Emrin sonucu doğrulanamadı. Geçmiş sayfasından kontrol et, tekrar göndermeden önce bekle.",
  };
}

function successText(d: OrderOk) {
  try {
    return `Emir gerçekleşti: ${new Decimal(d.quantity).toFixed()} ${d.symbol} @ ${new Decimal(d.fill_price).toFixed(2)} USDT · komisyon ${new Decimal(d.fee).toFixed()} USDT · kalan bakiye ${new Decimal(d.cash_after).toFixed(2)} USDT`;
  } catch {
    return "Emir gerçekleşti.";
  }
}

/* ---------- Market sayfası ---------- */
type MarketRow = {
  symbol: string;
  bid: string | null;
  ask: string | null;
  spread: string | null;
  received_at: string | null;
  tradeable: boolean;
};
type Coin = MarketRow & { dir: "up" | "down" | null; tick: number };

function fmt(value: string | null, digits = 2) {
  return value === null ? "—" : new Decimal(value).toFixed(digits);
}

export default function Market() {
  const { user, refreshMe } = useAuth();
  const { lang } = useLanguage();
  const en = lang === "en";
  const [coins, setCoins] = useState<Coin[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const [cash, setCash] = useState<string | null>(user?.cash ?? null);

  // Emir paneli
  const [selected, setSelected] = useState<string | null>("BTCUSDT");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const keyRef = useRef(crypto.randomUUID());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (user?.cash) setCash(user.cash);
  }, [user?.cash]);

  // Canlı SSE veri akışı (Rehber 2.5 & 2.10 - useLiveStream)
  const { status, isLive, symbolsClosed, setStatus } = useLiveStream((quotes) => {
    setCoins((prev) =>
      prev.map((c) => {
        const q = quotes.find((x) => x.symbol === c.symbol);
        if (!q) return c;
        let { dir, tick } = c;
        // Yön karşılaştırması Decimal ile
        if (c.bid !== null && !new Decimal(q.bid).eq(c.bid)) {
          dir = new Decimal(q.bid).gt(c.bid) ? "up" : "down";
          tick = c.tick + 1;
        }
        return {
          ...c,
          bid: q.bid,
          ask: q.ask,
          received_at: q.received_at,
          spread: new Decimal(q.ask).minus(q.bid).toFixed(),
          dir,
          tick,
        };
      })
    );
  });

  // Fiyatlar backend'den: ilk liste
  useEffect(() => {
    let alive = true;

    fetch("/api/markets")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((rows: MarketRow[]) => {
        if (alive && Array.isArray(rows)) {
          setCoins(rows.map((r) => ({ ...r, dir: null, tick: 0 })));
        }
      })
      .catch(() => {
        if (alive) setStatus("Piyasa verisi alınamadı");
      });

    return () => {
      alive = false;
    };
  }, [setStatus]);

  const selectedCoin = coins.find((c) => c.symbol === selected) ?? null;
  const isSelectedClosed =
    selectedCoin !== null && (!selectedCoin.tradeable || symbolsClosed.includes(selectedCoin.symbol));
  const isSelectedTradeable = Boolean(selectedCoin && isLive && !isSelectedClosed);
  // Alışta ask, satışta bid (string olarak, sözleşme gereği)
  const livePrice = selectedCoin ? (side === "BUY" ? selectedCoin.ask : selectedCoin.bid) : null;
  const preview =
    selectedCoin && livePrice !== null
      ? calcPreview(side, livePrice, quantity, STEP_SIZES[selectedCoin.symbol] ?? "0.00001", cash)
      : null;

  function selectCoin(symbol: string) {
    setSelected(symbol);
    setQuantity("");
    setError("");
    setSuccess("");
    keyRef.current = crypto.randomUUID(); // her form açılışında yeni anahtar
  }

  async function handleSubmit() {
    if (
      submitting ||
      !isLive ||
      !isSelectedTradeable ||
      !preview ||
      preview.tooSmall ||
      !selectedCoin ||
      livePrice === null
    ) {
      return;
    }
    setSubmitting(true);
    setError("");
    setSuccess("");

    const result = await submitOrder(
      {
        symbol: selectedCoin.symbol,
        side,
        quantity: preview.qty.toFixed(preview.dec), // string
        expected_price: livePrice,                  // string
      },
      keyRef.current,
      () => setChecking(true)
    );

    setChecking(false);
    setSubmitting(false);

    if (result.ok) {
      keyRef.current = crypto.randomUUID();
      setQuantity("");
      setCash(result.data.cash_after);
      setSuccess(successText(result.data));
      refreshMe();
    } else {
      // Kesin sonuç geldiyse yeni emir için yeni anahtar; belirsizse aynısı kalır
      if (result.code !== "UNKNOWN_OUTCOME") keyRef.current = crypto.randomUUID();
      setError(result.message);
    }
  }

  return (
    <section className="market-page">
      <div className="market-heading">
        <h1>{en ? "Markets" : "Piyasa"}</h1>
        <p>{en ? "Track the cryptocurrency market in real time." : "Kripto para piyasasını canlı takip et."}</p>
      </div>

      <div className="market-notice">
        {isLive ? "🟢" : status === "Bağlanıyor..." ? "🟡" : "🔴"}{" "}
        {en
          ? `Stream status: ${isLive ? "Live connection active" : status}. ${
              !isLive ? "Live price feed disconnected." : "Select a coin from the table to place an order."
            }`
          : `Veri durumu: ${status}. ${
              !isLive ? "Canlı fiyat akışı kesildi." : "Emir vermek için tablodan bir coin seç."
            }`}
      </div>

      <div className="market-grid">
        <div className="market-table-wrapper">
          <table className="market-table">
            <thead>
              <tr>
                <th>Coin</th>
                <th>{en ? "Bid (Buy)" : "Alış (bid)"}</th>
                <th>{en ? "Ask (Sell)" : "Satış (ask)"}</th>
                <th>Spread</th>
                <th>{en ? "Last update" : "Son güncelleme"}</th>
              </tr>
            </thead>
            <tbody>
              {coins.map((coin) => {
                const seconds =
                  coin.received_at !== null
                    ? Math.max(0, Math.round((now - Date.parse(coin.received_at)) / 1000))
                    : null;
                const d = digitsOf(coin.symbol);
                const effect = coin.dir ? `flash-${coin.dir} price-${coin.dir}` : "";
                const coinClosed = !coin.tradeable || symbolsClosed.includes(coin.symbol);

                return (
                  <tr
                    key={coin.symbol}
                    onClick={() => selectCoin(coin.symbol)}
                    className={selected === coin.symbol ? "row-selected" : ""}
                    style={{
                      cursor: "pointer",
                    }}
                  >
                    <td>
                      <strong>{coin.symbol.replace("USDT", "/USDT")}</strong>
                      <span className="market-coin-name">{NAMES[coin.symbol] ?? ""}</span>
                      {!isLive ? (
                        <span className="market-row-closed">
                          {en ? "Offline — trading halted" : "Bağlantı yok — işleme kapalı"}
                        </span>
                      ) : coinClosed ? (
                        <span className="market-row-closed">{en ? "Trading closed" : "İşleme kapalı"}</span>
                      ) : null}
                    </td>
                    <td key={`bid-${coin.tick}`} className={effect}>{fmt(coin.bid, d)}</td>
                    <td key={`ask-${coin.tick}`} className={effect}>{fmt(coin.ask, d)}</td>
                    <td>{fmt(coin.spread, 6)}</td>
                    <td>
                      {seconds === null ? "—" : en ? `${seconds}s ago` : `${seconds} sn önce`}
                      {!isLive ? (
                        <span className="market-row-closed">
                          {en ? " (No live data)" : " (Canlı veri yok)"}
                        </span>
                      ) : coinClosed ? (
                        <span className="market-row-closed">
                          {en ? " (Trading closed)" : " (İşleme kapalı)"}
                        </span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
              {coins.length === 0 && (
                <tr>
                  <td colSpan={5}>{en ? "Loading market data..." : "Piyasa verisi yükleniyor..."}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {selectedCoin && (
          <div className="order-form">
            <h2>
              {selectedCoin.symbol.replace("USDT", "/USDT")} {en ? "Order" : "emri"}
            </h2>

            <div className="order-side-tabs">
              <button
                type="button"
                className={`order-side-btn ${side === "BUY" ? "active-buy" : ""}`}
                onClick={() => setSide("BUY")}
                disabled={side === "BUY"}
              >
                {en ? "Buy" : "Al"}
              </button>
              <button
                type="button"
                className={`order-side-btn ${side === "SELL" ? "active-sell" : ""}`}
                onClick={() => setSide("SELL")}
                disabled={side === "SELL"}
              >
                {en ? "Sell" : "Sat"}
              </button>
            </div>

            <p className="order-meta">
              {en ? "Price" : "Fiyat"}: {fmt(livePrice, digitsOf(selectedCoin.symbol))} USDT
            </p>
            <p className="order-meta">
              {en ? "Balance" : "Bakiye"}: {cash === null ? "—" : fmt(cash, 2)} USDT
            </p>

            <label className="order-field-label">
              {en ? "Quantity" : "Miktar"}{" "}
              <input
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                inputMode="decimal"
                placeholder="0.00"
              />
            </label>

            {preview && (
              <div className="order-preview">
                <div>
                  {en ? "Quantity" : "Miktar"}: {preview.qty.toFixed(preview.dec)}
                </div>
                <div>
                  {en ? "Fee" : "Komisyon"}: {preview.fee.toFixed(4)} USDT
                </div>
                <div>
                  {en ? "Total" : "Toplam"}: {preview.total.toFixed(2)} USDT
                </div>
                {preview.remaining !== null && (
                  <div>
                    {en ? "Remaining balance" : "Kalan bakiye"}: {preview.remaining.toFixed(2)} USDT
                  </div>
                )}
                {preview.maxQty !== null && (
                  <div>
                    {en ? "Max" : "En fazla"}:{" "}
                    <button
                      type="button"
                      className="order-max-btn"
                      onClick={() => setQuantity(preview.maxQty!.toFixed(preview.dec))}
                    >
                      {preview.maxQty.toFixed(preview.dec)}
                    </button>
                  </div>
                )}
                {preview.rounded && !preview.tooSmall && (
                  <p className="order-warning">
                    {en
                      ? `Quantity rounded to ${preview.qty.toFixed(preview.dec)} per step size.`
                      : `Miktar adım değerine göre ${preview.qty.toFixed(preview.dec)} olarak yuvarlandı.`}
                  </p>
                )}
                {preview.tooSmall && (
                  <p className="order-error">
                    {en ? "Quantity is below minimum step size." : "Miktar, en küçük adım değerinin altında."}
                  </p>
                )}
                {preview.insufficient && (
                  <p className="order-error">{en ? "Insufficient balance." : "Yetersiz bakiye."}</p>
                )}
              </div>
            )}

            {!isLive ? (
              <p className="order-error" role="alert">
                {en
                  ? `Live data unavailable, orders temporarily disabled. (${status})`
                  : `Canlı veri alınamıyor, emirler geçici olarak kapalı. (${status})`}
              </p>
            ) : isSelectedClosed ? (
              <p className="order-error" role="alert">
                {en ? "Trading is currently closed for this coin." : "Bu coin için işlem şu an kapalı."}
              </p>
            ) : null}

            <button
              type="button"
              className={`order-submit-btn ${side === "BUY" ? "submit-buy" : "submit-sell"}`}
              onClick={handleSubmit}
              disabled={
                submitting ||
                !isLive ||
                !isSelectedTradeable ||
                !preview ||
                preview.tooSmall ||
                preview.insufficient
              }
            >
              {checking
                ? en
                  ? "Checking outcome..."
                  : "Sonuç kontrol ediliyor..."
                : submitting
                  ? en
                    ? "Submitting..."
                    : "Gönderiliyor..."
                  : en
                    ? "Place Order"
                    : "Emri ver"}
            </button>

            {error && <p className="order-error">{error}</p>}
            {success && <p className="order-success">{success}</p>}
          </div>
        )}
      </div>
    </section>
  );
}