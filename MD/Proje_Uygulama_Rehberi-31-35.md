Sanal Portföy · Proje Uygulama Rehberi 

# **17  Ek: Hazır dosyalar** 

## **17.1** `.gitignore` 

```
# Ortam ve gizli bilgiler
.env
*.env.local
# Python
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
# Node
node_modules/
dist/
coverage/
playwright-report/
test-results/
# Editör / işletim sistemi
.vscode/*
!.vscode/extensions.json
.idea/
.DS_Store
Thumbs.db
```

## **17.2** `.env.example` 

```
# --- Veritabanı ---
POSTGRES_USER=app
POSTGRES_PASSWORD=app_dev_sifre
POSTGRES_DB=portfolio
DATABASE_URL=postgresql+asyncpg://app:app_dev_sifre@db:5432/portfolio
# --- Güvenlik (gerçek .env'de uzun rastgele bir değer yazın) ---
SECRET_KEY=bunu-degistir-en-az-32-karakter-rastgele-deger
FRONTEND_ORIGIN=http://localhost:5173
# Yerel geliştirmede false; HTTPS ile yayındaysa true
COOKIE_SECURE=false
# --- Simülasyon ayarları ---
STARTING_CASH=10000
FEE_RATE=0.001
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT
# --- Piyasa verisi ---
# live = Binance'tan canlı, replay = kayıtlı veri (test/demo yedeği)
MARKET_SOURCE=live
BINANCE_WS_URL=wss://data-stream.binance.vision
BINANCE_REST_URL=https://data-api.binance.vision
QUOTE_STALE_SECONDS=5
```

CEN317 · 3 kişilik ekip · 4 hafta 

31 

Sanal Portföy · Proje Uygulama Rehberi 

**17.3** `docker-compose.yml` 

```
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
  backend:
    build: ./backend
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "8000:8000"
    # TEK işçi: fiyat hafızası tek süreçte tutulur (Bölüm 15)
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"
  frontend:
    build: ./frontend
    environment:
      VITE_API_TARGET: http://backend:8000   # Docker içinde backend'in adresi
    ports:
      - "5173:5173"
    depends_on:
      - backend
volumes:
  pgdata:
```

`backend/Dockerfile` : 

```
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

`frontend/Dockerfile` (geliştirme amaçlı): 

```
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
```

Frontend'in `/api` isteklerini backend'e yönlendirmek için `vite.config.ts` içinde proxy tanımlanır: 

```
server: {
  proxy: {
    "/api": {
      target: process.env.VITE_API_TARGET ?? "http://localhost:8000",
      changeOrigin: true,
      rewrite: (p) => p.replace(/^\/api/, ""),
    },
  },
},
```

Docker içinde çalışırken `VITE_API_TARGET` değeri compose dosyasından gelir ( `http://backend:8000` ); Docker dışında çalışırken varsayılan `http://localhost:8000` kullanılır. Bu proxy sayesinde tarayıcı her 

CEN317 · 3 kişilik ekip · 4 hafta 

32 

Sanal Portföy · Proje Uygulama Rehberi 

şeyi aynı adresten ( `localhost:5173/api/...` ) ister; çerez ve CORS sorunları ortadan kalkar. 

**17.4** `.github/workflows/ci.yml` 

```
name: CI
on:
  pull_request:
  push:
    branches: [main]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: app_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U app -d app_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    defaults:
      run:
        working-directory: backend
    env:
      DATABASE_URL: postgresql+asyncpg://app:app@localhost:5432/app_test
      SECRET_KEY: ci-test-secret-key-en-az-32-karakter-uzun
      MARKET_SOURCE: replay          # CI ASLA Binance'a bağlanmaz
      SYMBOLS: BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT
      FEE_RATE: "0.001"
      STARTING_CASH: "10000"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: |
            backend/requirements.txt
            backend/requirements-dev.txt
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Lint
        run: ruff check .
      - name: Migration
        run: alembic upgrade head
      - name: Testler
        run: pytest -q
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - name: Lint
        run: npm run lint
      - name: Tip kontrolü
        run: npx tsc --noEmit
      - name: Birim testleri
        run: npx vitest run --passWithNoTests
      - name: Derleme
        run: npm run build
```

CEN317 · 3 kişilik ekip · 4 hafta 

33 

Sanal Portföy · Proje Uygulama Rehberi 

`backend/requirements-dev.txt` en azından şunları içerir: `pytest` , `pytest-asyncio` , `httpx` , `ruff` . Frontend'de `vitest` dev bağımlılık olarak eklenir. Playwright testleri ilk aşamada yerel makinede çalıştırılır; vakit kalırsa Hafta 3'te CI'a ayrı bir iş olarak eklenir. 

**17.5** `.github/pull_request_template.md` 

```
## Ne yaptım?
<!-- 1-3 cümle -->
## İlgili issue
Closes #
## Nasıl test edilir?
1.
2.
## Kontrol listesi
- [ ] Testler yazıldı (başarılı + hatalı durumlar)
- [ ] Yerelde `docker compose up` ile denendi
- [ ] API/şema değiştiyse `docs/api.md` ve migration güncellendi
- [ ] Para hesabında float kullanılmadı
## Ekran görüntüsü (arayüz değişikliği varsa)
```

## **17.6** `docs/api.md` **başlangıç şablonu (G2'de doldurulur)** 

```
# API Sözleşmesi (G2'de donduruldu — değişiklik 3 kişinin onayıyla)
Kurallar:
- Tüm para ve miktar alanları STRING'dir: "1001.10010000"
- Tüm zamanlar ISO 8601, UTC: "2026-10-12T14:03:22.123Z"
- Hata biçimi: {"error": {"code": "INSUFFICIENT_FUNDS", "message": "..."}}
## Kimlik
POST /auth/register   {email, password}        → 201 {id, email}
POST /auth/login      {email, password}        → 200 (httpOnly çerez)
POST /auth/logout                              → 204
GET  /me                                       → 200 {id, email, cash}
## Piyasa
GET /markets
→ [{"symbol":"BTCUSDT","bid":"100000.00","ask":"100010.00",
    "spread":"10.00","received_at":"...","tradeable":true}]
GET /markets/{symbol}/candles?limit=300
→ [{"open_time":"...","open":"...","high":"...","low":"...","close":"..."}]
## Emir
POST /orders
Header: Idempotency-Key: <uuid>
Body: {"symbol":"BTCUSDT","side":"BUY","quantity":"0.01"}
→ 201 {"order_id":"...","fill_price":"100010.00","quantity":"0.01",
       "fee":"1.00010000","cash_after":"8998.89990000",
       "quote":{"bid":"100000.00","ask":"100010.00","received_at":"..."}}
→ 409 QUOTE_STALE
→ 422 INSUFFICIENT_FUNDS | INSUFFICIENT_POSITION | FILTER_VIOLATION | DEPTH_EXCEEDED
GET /trades?cursor=...
## Portföy
GET /portfolio
→ {"cash":"...","equity":"...","realized_pnl":"...","unrealized_pnl":"...",
   "valued_at":"...","positions":[{"symbol":"BTCUSDT","quantity":"...",
   "avg_cost":"...","market_value":"...","unrealized_pnl":"..."}]}
GET /portfolio/history?range=1d → [{"taken_at":"...","equity":"..."}]
## Canlı yayın (SSE)
GET /stream
event: quote              data: [{symbol, bid, ask, received_at}, ...]   (saniyede 1)
event: market_status      data: {state: "HEALTHY|SUSPECT|DOWN", symbols_closed: [...]}
event: portfolio_updated  data: {aynı GET /portfolio biçimi}             (saniyede 1 + işlem sonrası)
```

CEN317 · 3 kişilik ekip · 4 hafta 

34 

Sanal Portföy · Proje Uygulama Rehberi 

**17.7** `docs/saatler.md` **şablonu** 

```
| Hafta | K1 | K2 | K3 | Not |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
```

_Bu rehber bir plandır; gerçekleşen ilerleme değildir. Raporda sadece gerçekten yapılan işler "tamamlandı" olarak yazılmalıdır._ 

CEN317 · 3 kişilik ekip · 4 hafta 

35 

