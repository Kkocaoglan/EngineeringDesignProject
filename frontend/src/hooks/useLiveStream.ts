import { useEffect, useRef, useState } from "react";

export type MarketStatus =
  | "Canlı bağlantı aktif"
  | "Canlı veri alınamıyor"
  | "Bağlantı hatası"
  | "Bağlanıyor..."
  | "Piyasa verisi alınamadı";

export type QuoteUpdate = {
  symbol: string;
  bid: string;
  ask: string;
  received_at: string;
};

export type MarketStatusEvent = {
  state: "HEALTHY" | "DOWN";
  symbols_closed?: string[];
};

export function useLiveStream(onQuote?: (quotes: QuoteUpdate[]) => void) {
  const [status, setStatus] = useState<MarketStatus>("Bağlanıyor...");
  const onQuoteRef = useRef(onQuote);

  useEffect(() => {
    onQuoteRef.current = onQuote;
  }, [onQuote]);

  useEffect(() => {
    let alive = true;
    // Rehber 2.5: withCredentials: true ile çerez tabanlı SSE bağlantısı
    const es = new EventSource("/api/stream", { withCredentials: true });

    es.onopen = () => {
      if (alive) setStatus("Canlı bağlantı aktif");
    };

    es.addEventListener("quote", (e) => {
      if (!alive) return;
      try {
        const quotes: QuoteUpdate[] = JSON.parse((e as MessageEvent).data);
        if (onQuoteRef.current) {
          onQuoteRef.current(quotes);
        }
      } catch {
        /* bozuk mesaj */
      }
    });

    es.addEventListener("market_status", (e) => {
      if (!alive) return;
      try {
        const s: MarketStatusEvent = JSON.parse((e as MessageEvent).data);
        setStatus(
          s.state === "HEALTHY" ? "Canlı bağlantı aktif" : "Canlı veri alınamıyor"
        );
      } catch {
        /* bozuk mesaj */
      }
    });

    es.onerror = () => {
      if (alive) setStatus("Bağlantı hatası");
    };

    return () => {
      alive = false;
      es.close();
    };
  }, []);

  const isLive = status === "Canlı bağlantı aktif";

  return { status, isLive, setStatus };
}
