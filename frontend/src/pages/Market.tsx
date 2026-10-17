import { useEffect, useRef, useState } from "react";
import Decimal from "decimal.js";

/* ---------- Ayarlar (şimdilik örnek değerler) ---------- */
const COMMISSION_RATE = "0.001"; // yüzde 0,1
const USDT_BALANCE = "1000";
const COIN_BALANCE = "1";
const ORDER_URL = "/api/orders"; // docs/api.md → Emir (K1) bölümüne göre düzeltilecek
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
const ERROR_MESSAGES: Record<string, string> = {
  INSUFFICIENT_BALANCE: "Yetersiz bakiye.",
  PRICE_MOVED: "Fiyat değişti. Önizlemeyi kontrol edip tekrar dene.",
  INVALID_QUANTITY: "Miktar geçersiz.",
};

/* ---------- Önizleme hesabı (decimal.js) ---------- */
const floorToStep = (v: Decimal, step: Decimal) => v.div(step).floor().mul(step);

function calcPreview(side: "BUY" | "SELL", price: string, quantity: string, stepSize: string) {
  try {
    const p = new Decimal(price);
    const rawQty = new Decimal(quantity);
    const step = new Decimal(stepSize);
    const rate = new Decimal(COMMISSION_RATE);
    if (p.lte(0) || rawQty.lte(0) || step.lte(0)) return null;

    const qty = floorToStep(rawQty, step);
    const notional = p.mul(qty);
    const fee = notional.mul(rate);
    const balance = new Decimal(side === "BUY" ? USDT_BALANCE : COIN_BALANCE);

    const total = side === "BUY" ? notional.plus(fee) : notional.minus(fee);
    const remaining = side === "BUY" ? balance.minus(total) : balance.minus(qty);
    const maxQty =
      side === "BUY"
        ? floorToStep(balance.div(p.mul(rate.plus(1))), step)
        : floorToStep(balance, step);
    const insufficient = side === "BUY" ? total.gt(balance) : qty.gt(balance);

    return { qty, rounded: !qty.eq(rawQty), fee, total, remaining, maxQty, insufficient, dec: step.decimalPlaces() };
  } catch {
    return null;
  }
}

/* ---------- Emir gönderme: 10 sn zaman aşımı, aynı anahtarla 1-2-4 sn arayla 3 tekrar ---------- */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const BACKOFF = [1000, 2000, 4000];

async function submitOrder(body: object, key: string, onChecking: () => void) {
  for (let i = 0; i <= BACKOFF.length; i++) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 10_000);
    try {
      const res = await fetch(ORDER_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": key },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      const data = await res.json().catch(() => null);
      if (res.ok) return { ok: true as const, message: "" };
      if (res.status < 500) {
        const code = data?.code ?? "UNKNOWN";
        return { ok: false as const, message: ERROR_MESSAGES[code] ?? "Emir reddedildi." };
      }
    } catch {
      /* zaman aşımı veya ağ hatası: tekrar denenecek */
    } finally {
      clearTimeout(timer);
    }
    if (i === BACKOFF.length) break;
    onChecking();
    await sleep(BACKOFF[i]);
  }
  return {
    ok: false as const,
    message: "Emrin sonucu doğrulanamadı. Geçmiş sayfasından kontrol et, tekrar gönderme.",
  };
}

/* ---------- Market sayfası ---------- */
type Coin = {
  symbol: string;
  name: string;
  bid: number | null;
  ask: number | null;
  updatedAt: number | null;
  dir: "up" | "down" | null;
  tick: number;
};

const makeCoin = (symbol: string, name: string): Coin => ({
  symbol, name, bid: null, ask: null, updatedAt: null, dir: null, tick: 0,
});

const initialCoins: Coin[] = [
  makeCoin("BTCUSDT", "Bitcoin"),
  makeCoin("ETHUSDT", "Ethereum"),
  makeCoin("BNBUSDT", "BNB"),
  makeCoin("SOLUSDT", "Solana"),
  makeCoin("XRPUSDT", "XRP"),
  makeCoin("DOGEUSDT", "Dogecoin"),
  makeCoin("ADAUSDT", "Cardano"),
  makeCoin("AVAXUSDT", "Avalanche"),
];

function fmt(value: number | null, maxDigits = 2) {
  if (value === null) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: maxDigits,
  });
}

export default function Market() {
  const [coins, setCoins] = useState(initialCoins);
  const [status, setStatus] = useState("Bağlanıyor...");
  const [now, setNow] = useState(Date.now());

  // Emir paneli
  const [selected, setSelected] = useState<string | null>(null);
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
    const streams = initialCoins.map((c) => `${c.symbol.toLowerCase()}@ticker`).join("/");
    const socket = new WebSocket(`wss://stream.binance.com:9443/stream?streams=${streams}`);

    socket.onopen = () => setStatus("Canlı bağlantı aktif");
    socket.onerror = () => setStatus("Bağlantı hatası");
    socket.onclose = () => setStatus("Bağlantı kapandı");

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data).data;
      setCoins((current) =>
        current.map((coin) => {
          if (coin.symbol !== data.s) return coin;
          const bid = Number(data.b);
          const ask = Number(data.a);
          let { dir, tick } = coin;
          if (coin.bid !== null && bid !== coin.bid) {
            dir = bid > coin.bid ? "up" : "down";
            tick = coin.tick + 1;
          }
          return { ...coin, bid, ask, updatedAt: Date.now(), dir, tick };
        })
      );
    };

    return () => socket.close();
  }, []);

  const isLive = status === "Canlı bağlantı aktif";

  // Seçili coin ve önizleme
  const selectedCoin = coins.find((c) => c.symbol === selected) ?? null;
  const livePrice = selectedCoin ? (side === "BUY" ? selectedCoin.ask : selectedCoin.bid) : null;
  const preview =
    selectedCoin && livePrice !== null
      ? calcPreview(side, String(livePrice), quantity, STEP_SIZES[selectedCoin.symbol] ?? "0.00001")
      : null;

  function selectCoin(symbol: string) {
    setSelected(symbol);
    setQuantity("");
    setError("");
    setSuccess("");
    keyRef.current = crypto.randomUUID(); // her form açılışında yeni anahtar
  }

  async function handleSubmit() {
    if (submitting || !preview || !selectedCoin || livePrice === null) return;
    setSubmitting(true);
    setError("");
    setSuccess("");

    const result = await submitOrder(
      {
        symbol: selectedCoin.symbol,
        side,
        quantity: preview.qty.toFixed(preview.dec),
        expected_price: String(livePrice),
      },
      keyRef.current,
      () => setChecking(true)
    );

    setChecking(false);
    setSubmitting(false);

    if (result.ok) {
      keyRef.current = crypto.randomUUID();
      setQuantity("");
      setSuccess("Emir gönderildi.");
    } else {
      setError(result.message);
    }
  }

  return (
    <section className="market-page">
      <h1>Piyasa</h1>
      <p>Kripto para piyasasını canlı takip et.</p>

      <div className="market-notice">
        {isLive ? "🟢" : "🔴"} Veri durumu: {status}. Fiyatlar Binance Spot canlı
        verileridir. Emir vermek için tablodan bir coin seç.
      </div>

      <div className="market-table-wrapper">
        <table className="market-table">
          <thead>
            <tr>
              <th>Coin</th>
              <th>Alış (bid)</th>
              <th>Satış (ask)</th>
              <th>Spread</th>
              <th>Son güncelleme</th>
            </tr>
          </thead>
          <tbody>
            {coins.map((coin) => {
              const spread =
                coin.bid !== null && coin.ask !== null ? coin.ask - coin.bid : null;
              const seconds =
                coin.updatedAt !== null
                  ? Math.max(0, Math.round((now - coin.updatedAt) / 1000))
                  : null;
              const effect = coin.dir ? `flash-${coin.dir} price-${coin.dir}` : "";

              return (
                <tr
                  key={coin.symbol}
                  onClick={() => selectCoin(coin.symbol)}
                  style={{
                    cursor: "pointer",
                    outline: selected === coin.symbol ? "2px solid #3b82f6" : "none",
                  }}
                >
                  <td>
                    <strong>{coin.symbol.replace("USDT", "/USDT")}</strong>
                    <span className="market-coin-name">{coin.name}</span>
                  </td>
                  <td key={`bid-${coin.tick}`} className={effect}>{fmt(coin.bid, 6)}</td>
                  <td key={`ask-${coin.tick}`} className={effect}>{fmt(coin.ask, 6)}</td>
                  <td>{fmt(spread, 6)}</td>
                  <td>{seconds === null ? "—" : `${seconds} sn önce`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedCoin && (
        <div className="order-form">
          <h2>{selectedCoin.symbol.replace("USDT", "/USDT")} emri</h2>

          <div>
            <button type="button" onClick={() => setSide("BUY")} disabled={side === "BUY"}>Al</button>
            <button type="button" onClick={() => setSide("SELL")} disabled={side === "SELL"}>Sat</button>
          </div>

          <p>Fiyat: {fmt(livePrice, 6)} USDT</p>

          <label>
            Miktar{" "}
            <input
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              inputMode="decimal"
            />
          </label>

          {preview && (
            <div className="order-preview">
              <div>Miktar: {preview.qty.toFixed(preview.dec)}</div>
              <div>Komisyon: {preview.fee.toFixed(4)} USDT</div>
              <div>Toplam: {preview.total.toFixed(2)} USDT</div>
              <div>Kalan bakiye: {preview.remaining.toFixed(side === "BUY" ? 2 : preview.dec)}</div>
              <div>
                En fazla:{" "}
                <button
                  type="button"
                  onClick={() => setQuantity(preview.maxQty.toFixed(preview.dec))}
                >
                  {preview.maxQty.toFixed(preview.dec)}
                </button>
              </div>
              {preview.rounded && (
                <p className="order-warning">
                  Miktar adım değerine göre {preview.qty.toFixed(preview.dec)} olarak yuvarlandı.
                </p>
              )}
              {preview.insufficient && <p className="order-error">Yetersiz bakiye.</p>}
            </div>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || !preview || preview.insufficient}
          >
            {checking ? "Sonuç kontrol ediliyor..." : submitting ? "Gönderiliyor..." : "Emri ver"}
          </button>

          {error && <p className="order-error">{error}</p>}
          {success && <p className="order-success">{success}</p>}
        </div>
      )}
    </section>
  );
}