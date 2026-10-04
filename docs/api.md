# API Sözleşmesi (TASLAK — G2 toplantısında dondurulur, sonra değişiklik 3 kişinin onayıyla)

Kurallar:
- Tüm para ve miktar alanları STRING'dir: "1001.10010000"
- Tüm zamanlar ISO 8601, UTC: "2026-10-12T14:03:22.123Z"
- Hata biçimi: {"error": {"code": "INSUFFICIENT_FUNDS", "message": "..."}}
- Tarayıcı istekleri /api ön ekiyle gider (Vite proxy kaldırır): /api/auth/login → /auth/login

## Sistem
GET /health → 200 {"status":"ok"}
GET /ready  → 200 {"db":"ok","market":"HEALTHY","symbols_open":5} | 503

## Kimlik (K1)
POST /auth/register {email, password}  → 201 {id, email}
                                        → 409 EMAIL_TAKEN · 422 doğrulama hatası (şifre en az 8 karakter)
POST /auth/login    {email, password}  → 200 {id, email} + httpOnly çerez "session"
                                        → 401 INVALID_CREDENTIALS
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
Header: Idempotency-Key: <uuid>   (yoksa 400)
Body: {"symbol":"BTCUSDT","side":"BUY","quantity":"0.01","expected_price":"100010.00"}
→ 201 {"order_id":"...","fill_price":"100010.00","quantity":"0.01","fee":"1.00010000",
       "cash_after":"8998.89990000","quote":{"bid":"100000.00","ask":"100010.00","received_at":"..."}}
→ 409 QUOTE_STALE | PRICE_MOVED
→ 422 INSUFFICIENT_FUNDS | INSUFFICIENT_POSITION | FILTER_VIOLATION | DEPTH_EXCEEDED | IDEMPOTENCY_KEY_REUSED
GET /trades?cursor=...

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
