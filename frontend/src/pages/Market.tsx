import { useEffect, useState } from "react";

type Coin = {
  symbol: string;
  name: string;
  bid: number | null;
  ask: number | null;
  updatedAt: number | null;
};

const initialCoins: Coin[] = [
  { symbol: "BTCUSDT", name: "Bitcoin", bid: null, ask: null, updatedAt: null },
  { symbol: "ETHUSDT", name: "Ethereum", bid: null, ask: null, updatedAt: null },
  { symbol: "BNBUSDT", name: "BNB", bid: null, ask: null, updatedAt: null },
  { symbol: "SOLUSDT", name: "Solana", bid: null, ask: null, updatedAt: null },
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

  // "x sn önce" yazısının her saniye yenilenmesi için
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const streams = ["btcusdt", "ethusdt", "bnbusdt", "solusdt"]
      .map((symbol) => `${symbol}@ticker`)
      .join("/");

    const socket = new WebSocket(
      `wss://stream.binance.com:9443/stream?streams=${streams}`
    );

    socket.onopen = () => setStatus("Canlı bağlantı aktif");
    socket.onerror = () => setStatus("Bağlantı hatası");
    socket.onclose = () => setStatus("Bağlantı kapandı");

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      const data = message.data;

      setCoins((currentCoins) =>
        currentCoins.map((coin) =>
          coin.symbol === data.s
            ? {
                ...coin,
                bid: Number(data.b),
                ask: Number(data.a),
                updatedAt: Date.now(),
              }
            : coin
        )
      );
    };

    return () => socket.close();
  }, []);

  const isLive = status === "Canlı bağlantı aktif";

  return (
    <section className="market-page">
      <h1>Piyasa</h1>
      <p>Kripto para piyasasını canlı takip et.</p>

      <div className="market-notice">
        {isLive ? "🟢" : "🔴"} Veri durumu: {status}. Fiyatlar Binance Spot
        canlı verileridir; işlemler bu ekranda gerçekleştirilmez.
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
                coin.bid !== null && coin.ask !== null
                  ? coin.ask - coin.bid
                  : null;
              const seconds =
                coin.updatedAt !== null
                  ? Math.max(0, Math.round((now - coin.updatedAt) / 1000))
                  : null;

              return (
                <tr key={coin.symbol}>
                  <td>
                    <strong>{coin.symbol.replace("USDT", "/USDT")}</strong>
                    <span className="market-coin-name">{coin.name}</span>
                  </td>
                  <td>{fmt(coin.bid)}</td>
                  <td>{fmt(coin.ask)}</td>
                  <td>{fmt(spread, 4)}</td>
                  <td>{seconds === null ? "—" : `${seconds} sn önce`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
} 
