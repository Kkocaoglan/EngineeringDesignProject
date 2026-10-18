# API Sözleşmesi (TASLAK — G2 toplantısında dondurulur, sonra değişiklik 3 kişinin onayıyla)

Kurallar:
- Tüm para ve miktar alanları STRING'dir: "1001.10010000"
- Tüm zamanlar ISO 8601, UTC: "2026-10-12T14:03:22.123Z"
- Hata biçimi: {"error": {"code": "INSUFFICIENT_FUNDS", "message": "..."}}
- Tarayıcı istekleri /api ön ekiyle gider (Vite proxy kaldırır): /api/auth/login → /auth/login
- Durum değiştiren isteklerde (POST/PUT/PATCH/DELETE) Origin başlığı uygulamanın kendi adresi
  değilse → 403 BAD_ORIGIN (CSRF koruması)
- İstek sınırı aşılırsa → 429 TOO_MANY_REQUESTS + "Retry-After: <saniye>" başlığı

## Sistem
GET /health → 200 {"status":"ok"}
GET /ready  → 200 {"db":"ok","market":"HEALTHY","symbols_open":5} | 503

## Kimlik (K1)
POST /auth/register {email, password}  → 201 {id, email}
                                        → 409 EMAIL_TAKEN · 422 doğrulama hatası (şifre en az 8 karakter)
POST /auth/login    {email, password}  → 200 {id, email} + httpOnly çerez "session"
                                        → 401 INVALID_CREDENTIALS
                                        → 429 TOO_MANY_REQUESTS (e-posta başına dakikada 5 deneme)
POST /auth/logout                      → 204 (çerez silinir)
GET  /me                               → 200 {id, email, cash} · 401 NOT_AUTHENTICATED

## Piyasa (K3)
GET /markets
→ [{"symbol":"BTCUSDT","bid":"100000.00","ask":"100010.00","spread":"10.00",
    "received_at":"...","tradeable":true}]
GET /markets/{symbol}/candles?limit=300
→ [{"open_time":"...","open":"...","high":"...","low":"...","close":"..."}]

## Emir (K1)
POST /orders
Header: Idempotency-Key: <uuid>   (her form açılışında yeni; tekrar denemede AYNI anahtar)
Body: {"symbol":"BTCUSDT","side":"BUY","quantity":"0.01","expected_price":"100010.00"}
      quantity ve expected_price STRING (JSON sayı gönderilirse 422). expected_price opsiyonel,
      K2 her zaman önizlemedeki ask (alış) / bid (satış) değerini gönderir.
      Miktar stepSize'a AŞAĞI yuvarlanır; cevaptaki quantity gerçekleşen miktardır.
→ 201 {"order_id":"...","trade_id":"...","symbol":"BTCUSDT","side":"BUY",
       "fill_price":"100010.00000000","quantity":"0.01000000","fee":"1.00010000",
       "cash_after":"8998.89990000",
       "quote":{"bid":"100000.00000000","ask":"100010.00000000","received_at":"2026-10-12T14:03:22.123Z"}}
       Aynı anahtar + aynı içerik tekrar gelirse: aynı 201 cevabı birebir (yeni işlem yapılmaz).
→ 400 IDEMPOTENCY_KEY_REQUIRED | IDEMPOTENCY_KEY_INVALID
→ 401 NOT_AUTHENTICATED
→ 409 QUOTE_STALE (taze fiyat yok) | PRICE_MOVED (fiyat aleyhe PRICE_TOLERANCE'tan fazla oynadı)
→ 422 INSUFFICIENT_FUNDS | INSUFFICIENT_POSITION | FILTER_VIOLATION | DEPTH_EXCEEDED
      | IDEMPOTENCY_KEY_REUSED (aynı anahtar, farklı içerik)
→ 429 TOO_MANY_REQUESTS (hesap başına saniyede 5 emir)
      Reddedilen emirde veritabanında hiçbir şey değişmez.

GET /trades?limit=50&cursor=...   (en yeniden eskiye; limit 1–100)
→ 200 {"items":[{"id","order_id","symbol","side","quantity","price","notional","fee",
                 "realized_pnl","bid","ask","quote_received_at","created_at"}],
       "next_cursor":"..." | null}
→ 400 BAD_CURSOR · 401 NOT_AUTHENTICATED

GET /trades/{trade_id}            (tek işlem; yukarıdaki items[] elemanıyla aynı biçim)
→ 200 {...} · 401 NOT_AUTHENTICATED
→ 404 TRADE_NOT_FOUND (yok YA DA başka kullanıcıya ait; ikisi aynı cevabı alır, numara sızmaz)
→ 422 trade_id bir UUID değil

Fiyat kaynağı (K1 ↔ K3): backend/app/orders/quotes.py
  get_tradeable_quote(symbol) -> Quote(symbol, bid, ask, bid_qty, ask_qty, received_at)
  Taze değilse QuoteStale fırlatır. K3 bağlayana kadar varsayılan kaynak her emri 409 QUOTE_STALE
  ile reddeder (uydurma fiyat yok).

## Portföy (K3)
GET /portfolio
→ {"cash":"...","equity":"...","realized_pnl":"...","unrealized_pnl":"...","valued_at":"...",
   "positions":[{"symbol":"BTCUSDT","quantity":"...","avg_cost":"...","market_value":"...","unrealized_pnl":"..."}]}
GET /portfolio/history?range=1d → [{"taken_at":"...","equity":"..."}]

## Canlı yayın (K3)
GET /stream (SSE)
event: quote             data: [{symbol, bid, ask, received_at}, ...]   (saniyede 1)
event: market_status     data: {state: "HEALTHY|DOWN", symbols_closed: [...]}
event: portfolio_updated data: {GET /portfolio biçimi}   (saniyede 1 + işlem sonrası)
