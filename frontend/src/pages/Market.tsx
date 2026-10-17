
import { useEffect, useState } from "react";

type Coin = {
  symbol: string;
  name: string;
  price: string;
};

const initialCoins: Coin[] = [
  { symbol: "BTCUSDT", name: "Bitcoin", price: "Bağlanıyor..." },
  { symbol: "ETHUSDT", name: "Ethereum", price: "Bağlanıyor..." },
  { symbol: "BNBUSDT", name: "BNB", price: "Bağlanıyor..." },
  { symbol: "SOLUSDT", name: "Solana", price: "Bağlanıyor..." },
];

export default function Market() {
  const [coins, setCoins] = useState(initialCoins);
  const [status, setStatus] = useState("Bağlanıyor...");

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
            ? { ...coin, price: Number(data.c).toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              }) }
            : coin
        )
      );
    };

    return () => socket.close();
  }, []);

  return (
    <section className="market-page">
      <h1>Piyasa</h1>
      <p>Kripto para piyasasını canlı takip et.</p>

      <div className="market-notice">
        Veri durumu: {status}. Fiyatlar Binance Spot canlı verileridir;
        işlemler bu ekranda gerçekleştirilmez.
      </div>

      <div className="market-table-wrapper">
        <table className="market-table">
          <thead>
            <tr>
              <th>Coin</th>
              <th>Fiyat (USDT)</th>
              <th>Veri kaynağı</th>
            </tr>
          </thead>
          <tbody>
            {coins.map((coin) => (
              <tr key={coin.symbol}>
                <td>
                  <strong>{coin.symbol.replace("USDT", "/USDT")}</strong>
                  <span className="market-coin-name">{coin.name}</span>
                </td>
                <td>{coin.price}</td>
                <td>Binance Spot</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

