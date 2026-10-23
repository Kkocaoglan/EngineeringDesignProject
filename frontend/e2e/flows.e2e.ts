import { expect, test, type Page } from "@playwright/test";

type TradeItem = {
  id: string;
  order_id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: string;
  price: string;
  notional: string;
  fee: string;
  created_at: string;
};

type PositionItem = {
  symbol: string;
  quantity: string;
  avg_cost: string;
  market_value: string;
  unrealized_pnl: string;
};

type MockState = {
  loggedIn: boolean;
  email: string;
  cash: string;
  tradeable: boolean;
  marketHealthy: boolean;
  positions: PositionItem[];
  trades: TradeItem[];
  idempotencyRecords: Map<string, Record<string, unknown>>;
  orderKeysSeen: string[];
  failFirstOrderWith502: boolean;
  forceInsufficientFunds422: boolean;
};

function createInitialState(): MockState {
  return {
    loggedIn: false,
    email: "test@example.com",
    cash: "10000.00000000",
    tradeable: true,
    marketHealthy: true,
    positions: [],
    trades: [],
    idempotencyRecords: new Map(),
    orderKeysSeen: [],
    failFirstOrderWith502: false,
    forceInsufficientFunds422: false,
  };
}

async function setupMockApi(page: Page, state: MockState) {
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname.replace(/^\/api/, "");
    const method = req.method();

    if (path === "/health" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "ok" }),
      });
      return;
    }

    if (path === "/auth/register" && method === "POST") {
      const body = JSON.parse(req.postData() ?? "{}") as { email?: string };
      if (body.email) state.email = body.email;
      state.cash = "10000.00000000";
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: "u-1", email: state.email }),
      });
      return;
    }

    if (path === "/auth/login" && method === "POST") {
      const body = JSON.parse(req.postData() ?? "{}") as { email?: string };
      if (body.email) state.email = body.email;
      state.loggedIn = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "u-1", email: state.email }),
      });
      return;
    }

    if (path === "/auth/logout" && method === "POST") {
      state.loggedIn = false;
      await route.fulfill({ status: 204, body: "" });
      return;
    }

    if (path === "/me" && method === "GET") {
      if (!state.loggedIn) {
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({
            error: { code: "NOT_AUTHENTICATED", message: "Giriş yapılmadı." },
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "u-1",
          email: state.email,
          cash: state.cash,
        }),
      });
      return;
    }

    if (path === "/markets" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            symbol: "BTCUSDT",
            bid: "100000.00000000",
            ask: "100010.00000000",
            spread: "10.00000000",
            received_at: "2026-10-23T12:00:00.000Z",
            tradeable: state.tradeable,
          },
          {
            symbol: "ETHUSDT",
            bid: "2500.00000000",
            ask: "2501.00000000",
            spread: "1.00000000",
            received_at: "2026-10-23T12:00:00.000Z",
            tradeable: state.tradeable,
          },
        ]),
      });
      return;
    }

    if (path === "/stream" && method === "GET") {
      const marketState = state.marketHealthy ? "HEALTHY" : "DOWN";
      const closed = state.tradeable && state.marketHealthy ? [] : ["BTCUSDT", "ETHUSDT"];
      const sseBody =
        `event: market_status\ndata: ${JSON.stringify({ state: marketState, symbols_closed: closed })}\n\n` +
        `event: quote\ndata: ${JSON.stringify([
          {
            symbol: "BTCUSDT",
            bid: "100000.00000000",
            ask: "100010.00000000",
            received_at: "2026-10-23T12:00:01.000Z",
          },
        ])}\n\n`;

      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        headers: { "Cache-Control": "no-cache" },
        body: sseBody,
      });
      return;
    }

    if (path === "/orders" && method === "POST") {
      const idemKey = req.headers()["idempotency-key"] ?? "";
      state.orderKeysSeen.push(idemKey);

      if (state.failFirstOrderWith502 && state.orderKeysSeen.length === 1) {
        await route.fulfill({
          status: 502,
          contentType: "application/json",
          body: JSON.stringify({ error: { code: "BAD_GATEWAY", message: "Geçici ağ hatası" } }),
        });
        return;
      }

      if (state.forceInsufficientFunds422) {
        await route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({
            error: { code: "INSUFFICIENT_FUNDS", message: "Yetersiz bakiye." },
          }),
        });
        return;
      }

      if (idemKey && state.idempotencyRecords.has(idemKey)) {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(state.idempotencyRecords.get(idemKey)),
        });
        return;
      }

      const payload = JSON.parse(req.postData() ?? "{}") as {
        symbol: string;
        side: "BUY" | "SELL";
        quantity: string;
      };

      if (payload.side === "BUY") {
        state.cash = "8998.89990000";
        state.positions = [
          {
            symbol: payload.symbol,
            quantity: payload.quantity,
            avg_cost: "100110.01000000",
            market_value: "1000.00000000",
            unrealized_pnl: "-1.10010000",
          },
        ];
        state.trades.unshift({
          id: `t-${state.trades.length + 1}`,
          order_id: `o-${state.trades.length + 1}`,
          symbol: payload.symbol,
          side: "BUY",
          quantity: payload.quantity,
          price: "100010.00000000",
          notional: "1000.10000000",
          fee: "1.00010000",
          created_at: "2026-10-23T12:01:00.000Z",
        });

        const responsePayload = {
          order_id: "o-buy-1",
          trade_id: "t-buy-1",
          symbol: payload.symbol,
          side: "BUY",
          fill_price: "100010.00000000",
          quantity: payload.quantity,
          fee: "1.00010000",
          cash_after: state.cash,
        };
        if (idemKey) state.idempotencyRecords.set(idemKey, responsePayload);

        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(responsePayload),
        });
        return;
      }

      // SELL
      state.cash = "9997.89990000";
      state.positions = [];
      state.trades.unshift({
        id: `t-${state.trades.length + 1}`,
        order_id: `o-${state.trades.length + 1}`,
        symbol: payload.symbol,
        side: "SELL",
        quantity: payload.quantity,
        price: "100000.00000000",
        notional: "1000.00000000",
        fee: "1.00000000",
        created_at: "2026-10-23T12:02:00.000Z",
      });

      const sellPayload = {
        order_id: "o-sell-1",
        trade_id: "t-sell-1",
        symbol: payload.symbol,
        side: "SELL",
        fill_price: "100000.00000000",
        quantity: payload.quantity,
        fee: "1.00000000",
        cash_after: state.cash,
      };
      if (idemKey) state.idempotencyRecords.set(idemKey, sellPayload);

      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(sellPayload),
      });
      return;
    }

    if (path === "/portfolio" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cash: state.cash,
          equity: state.positions.length > 0 ? "9998.89990000" : state.cash,
          realized_pnl: "0.00000000",
          unrealized_pnl: state.positions.length > 0 ? "-1.10010000" : "0.00000000",
          valued_at: "2026-10-23T12:01:05.000Z",
          positions: state.positions,
        }),
      });
      return;
    }

    if (path === "/portfolio/history" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { taken_at: "2026-10-23T11:00:00.000Z", equity: "10000.00000000" },
          { taken_at: "2026-10-23T12:00:00.000Z", equity: "9998.89990000" },
        ]),
      });
      return;
    }

    if (path.startsWith("/markets/") && path.endsWith("/candles") && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            open_time: "2026-10-23T11:58:00.000Z",
            open: "99950.00000000",
            high: "100050.00000000",
            low: "99900.00000000",
            close: "100000.00000000",
          },
          {
            open_time: "2026-10-23T11:59:00.000Z",
            open: "100000.00000000",
            high: "100020.00000000",
            low: "99980.00000000",
            close: "100010.00000000",
          },
        ]),
      });
      return;
    }

    if (path === "/trades" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: state.trades,
          next_cursor: null,
        }),
      });
      return;
    }

    await route.continue();
  });
}

test.describe("Sanal Portföy Uçtan Uca (E2E) Test Akışları (Görev 2.11)", () => {
  test("Akış 1: Kayıt -> Giriş -> Başlangıç bakiyesinin (10000.00 USDT) görünmesi", async ({
    page,
  }) => {
    const state = createInitialState();
    await setupMockApi(page, state);

    await page.goto("/register");
    await expect(page.getByRole("heading", { name: "Hesap Oluştur" })).toBeVisible();

    await page.locator("#register-email").fill("ogrenci@ornek.edu.tr");
    await page.locator("#register-password").fill("GucluSifre123");
    await page.locator("#confirm-password").fill("GucluSifre123");
    await page.getByRole("button", { name: "Kayıt Ol" }).click();

    await expect(page).toHaveURL(/\/market$/);
    await expect(page.getByText("ogrenci@ornek.edu.tr")).toBeVisible();
    await expect(page.getByText("10000.00 USDT").first()).toBeVisible();

    // Çıkış yapıp tekrar giriş ekranından giriş doğrulaması
    await page.getByRole("button", { name: "Çıkış Yap" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.locator("#email").fill("ogrenci@ornek.edu.tr");
    await page.locator("#password").fill("GucluSifre123");
    await page.getByRole("button", { name: "Giriş Yap" }).click();

    await expect(page).toHaveURL(/\/market$/);
    await expect(page.getByText("Bakiye: 10000.00 USDT")).toBeVisible();
  });

  test("Akış 2: Canlı fiyat -> BTC alım -> Portföyde görünme -> Satım -> Geçmişte görünme", async ({
    page,
  }) => {
    const state = createInitialState();
    state.loggedIn = true;
    await setupMockApi(page, state);

    await page.goto("/market");
    await expect(page.getByRole("cell", { name: /BTC\/USDT/ })).toBeVisible();
    await expect(page.getByText("100010.00").first()).toBeVisible();

    // 0.01 BTC alım emri
    const qtyInput = page.locator(".order-form input");
    await qtyInput.fill("0.01");
    await expect(page.getByText("Komisyon: 1.0001 USDT")).toBeVisible();
    await page.getByRole("button", { name: "Emri ver" }).click();

    await expect(page.getByText(/Emir gerçekleşti: 0\.01 BTCUSDT/)).toBeVisible();
    await expect(page.getByText("Bakiye: 8998.90 USDT")).toBeVisible();

    // Portföy ekranında BTC pozisyonunu gör
    await page.getByRole("link", { name: "Portföy", exact: true }).click();
    await expect(page).toHaveURL(/\/portfolio$/);
    await expect(page.getByRole("heading", { name: "Pozisyonlar" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "BTC/USDT", exact: true })).toBeVisible();
    await expect(page.getByRole("cell", { name: "0.01", exact: true })).toBeVisible();

    // Piyasa ekranına dönüp 0.01 BTC sat
    await page.getByRole("link", { name: "Piyasa", exact: true }).click();
    await expect(page).toHaveURL(/\/market$/);
    await page.getByRole("button", { name: "Sat", exact: true }).click();
    await page.locator(".order-form input").fill("0.01");
    await page.getByRole("button", { name: "Emri ver" }).click();
    await expect(page.getByText(/Emir gerçekleşti: 0\.01 BTCUSDT/)).toBeVisible();

    // Geçmiş sayfasında hem Alış hem Satış işlemini gör
    await page.getByRole("link", { name: "Geçmiş", exact: true }).click();
    await expect(page).toHaveURL(/\/history$/);
    await expect(page.getByRole("cell", { name: "Alış" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Satış" })).toBeVisible();
  });

  test("Akış 3: Yetersiz bakiyeyle alış -> Hata mesajı ve buton kilidi", async ({
    page,
  }) => {
    const state = createInitialState();
    state.loggedIn = true;
    await setupMockApi(page, state);

    await page.goto("/market");
    const qtyInput = page.locator(".order-form input");

    // 1) Önizlemede bakiye aşımı (0.5 BTC ~ 50,005 USDT > 10,000 USDT)
    await qtyInput.fill("0.5");
    await expect(page.getByText("Yetersiz bakiye.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Emri ver" })).toBeDisabled();

    // 2) Backend 422 INSUFFICIENT_FUNDS döndüğünde Türkçe hata mesajı
    state.forceInsufficientFunds422 = true;
    await qtyInput.fill("0.01");
    await page.getByRole("button", { name: "Emri ver" }).click();
    await expect(page.getByText("Yetersiz bakiye.")).toBeVisible();
  });

  test("Akış 4: Cevap kaybolursa aynı Idempotency-Key ile tekrar -> Tek işlem", async ({
    page,
  }) => {
    const state = createInitialState();
    state.loggedIn = true;
    state.failFirstOrderWith502 = true;
    await setupMockApi(page, state);

    await page.goto("/market");
    await page.locator(".order-form input").fill("0.01");
    await page.getByRole("button", { name: "Emri ver" }).click();

    // İlk deneme 502 aldığında "Sonuç kontrol ediliyor..." görünür, ardından aynı anahtarla tamamlanır
    await expect(page.getByText(/Emir gerçekleşti: 0\.01 BTCUSDT/)).toBeVisible({
      timeout: 6000,
    });

    expect(state.orderKeysSeen.length).toBe(2);
    expect(state.orderKeysSeen[0]).toBeTruthy();
    expect(state.orderKeysSeen[0]).toBe(state.orderKeysSeen[1]);
    expect(state.trades.length).toBe(1);
  });

  test("Akış 5: Kesinti / işleme kapalı durumunda emir butonunun kilitlenmesi", async ({
    page,
  }) => {
    const state = createInitialState();
    state.loggedIn = true;
    state.tradeable = false;
    state.marketHealthy = false;
    await setupMockApi(page, state);

    await page.goto("/market");
    await page.locator(".order-form input").fill("0.01");

    await expect(page.getByText(/işlem şu an kapalı|emirler geçici olarak kapalı/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Emri ver" })).toBeDisabled();
  });
});
