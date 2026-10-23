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
  source?: string;
  mode?: string;
  market_source?: string;
  replay?: boolean;
};

const REPLAY_EVENT = "replay-mode-change";

function checkStaticReplay(): boolean {
  const envSource = String(import.meta.env.VITE_MARKET_SOURCE ?? "").toLowerCase();
  if (envSource === "replay") return true;
  if (typeof window !== "undefined") {
    try {
      const params = new URLSearchParams(window.location.search);
      if (
        params.get("replay") === "1" ||
        params.get("mode")?.toLowerCase() === "replay" ||
        params.get("source")?.toLowerCase() === "replay"
      ) {
        return true;
      }
      if (window.localStorage.getItem("MARKET_SOURCE")?.toLowerCase() === "replay") {
        return true;
      }
    } catch {
      /* storage erişim hatası yoksayılır */
    }
  }
  return false;
}

let globalReplayDetected = checkStaticReplay();

export function setReplayDetected(value: boolean) {
  if (globalReplayDetected !== value) {
    globalReplayDetected = value;
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent(REPLAY_EVENT, { detail: value }));
    }
  }
}

export function isReplayPayload(data: unknown): boolean {
  if (!data || typeof data !== "object") return false;
  const obj = data as Record<string, unknown>;
  if (obj.replay === true) return true;
  const candidates = [obj.source, obj.mode, obj.market_source];
  return candidates.some((v) => typeof v === "string" && v.toLowerCase() === "replay");
}

export function useReplayMode(): boolean {
  const [isReplay, setIsReplay] = useState<boolean>(() => globalReplayDetected || checkStaticReplay());

  useEffect(() => {
    const sync = () => setIsReplay(globalReplayDetected || checkStaticReplay());
    window.addEventListener(REPLAY_EVENT, sync);
    sync();

    if (!globalReplayDetected) {
      fetch("/api/health", { credentials: "include" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (isReplayPayload(data)) {
            setReplayDetected(true);
          }
        })
        .catch(() => {
          /* ağ hatası yoksayılır */
        });
    }

    return () => {
      window.removeEventListener(REPLAY_EVENT, sync);
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
        if (isReplayPayload(s)) {
          setReplayDetected(true);
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
