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

const REPLAY_EVENT = "replay-mode-change";

let globalReplayDetected: boolean | null = null;

export function setReplayDetected(value: boolean) {
  if (globalReplayDetected !== value) {
    globalReplayDetected = value;
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(REPLAY_EVENT, { detail: value }));
    }
  }
}

export function useReplayMode(): boolean {
  const [isReplay, setIsReplay] = useState<boolean>(() => globalReplayDetected === true);

  useEffect(() => {
    const sync = () => setIsReplay(globalReplayDetected === true);
    window.addEventListener(REPLAY_EVENT, sync);
    sync();

    let es: EventSource | null = null;
    if (globalReplayDetected === null) {
      es = new EventSource("/api/stream", { withCredentials: true });
      es.addEventListener("market_status", (e) => {
        try {
          const s: MarketStatusEvent = JSON.parse((e as MessageEvent).data);
          setReplayDetected(s.source === "replay");
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
      window.removeEventListener(REPLAY_EVENT, sync);
      es?.close();
    };
  }, []);

  return isReplay;
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
        setReplayDetected(s.source === "replay");
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
