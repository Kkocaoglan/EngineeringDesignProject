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
  source?: string;
  symbols_closed?: string[];
};

const SOURCE_EVENT = "market-source-change";

let globalMarketSource: string | null = null;

export function setMarketSource(value: string) {
  if (globalMarketSource !== value) {
    globalMarketSource = value;
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(SOURCE_EVENT, { detail: value }));
    }
  }
}

export function useMarketSource(): string | null {
  const [source, setSource] = useState<string | null>(() => globalMarketSource);

  useEffect(() => {
    const sync = () => setSource(globalMarketSource);
    window.addEventListener(SOURCE_EVENT, sync);
    sync();

    let es: EventSource | null = null;
    if (globalMarketSource === null) {
      es = new EventSource("/api/stream", { withCredentials: true });
      es.addEventListener("market_status", (e) => {
        try {
          const s: MarketStatusEvent = JSON.parse((e as MessageEvent).data);
          if (typeof s.source === "string") {
            setMarketSource(s.source);
          }
        } catch {
          /* bozuk mesaj */
        } finally {
          es?.close();
          es = null;
        }
      });
      es.onerror = () => {
        es?.close();
        es = null;
      };
    }

    return () => {
      window.removeEventListener(SOURCE_EVENT, sync);
      es?.close();
    };
  }, []);

  return source;
}

export function useReplayMode(): boolean {
  const source = useMarketSource();
  return source === "replay";
}

export function useLiveStream(onQuote?: (quotes: QuoteUpdate[]) => void) {
  const [status, setStatus] = useState<MarketStatus>("Bağlanıyor...");
  const [symbolsClosed, setSymbolsClosed] = useState<string[]>([]);
  const isReplay = useReplayMode();
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
        setSymbolsClosed(Array.isArray(s.symbols_closed) ? s.symbols_closed : []);
        if (typeof s.source === "string") {
          setMarketSource(s.source);
        }
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

  return { status, isLive, symbolsClosed, isReplay, setStatus };
}
