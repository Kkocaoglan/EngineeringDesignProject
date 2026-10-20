/**
 * Merkezi API İstemcisi
 * - Tüm istekler Vite proxy üzerinden '/api' adresiyle iletilir.
 * - 'credentials: "include"' sayesinde oturum çerezleri (cookie) otomatik taşınır.
 * - Para ve miktar değerleri string formatında korunur (hassasiyet kaybını önlemek için).
 */

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const ERROR_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "E-posta veya şifre hatalı.",
  EMAIL_TAKEN: "Bu e-posta adresiyle kayıtlı bir hesap zaten var.",
  NOT_AUTHENTICATED: "Oturum süreniz dolmuş veya giriş yapmadınız.",
  INSUFFICIENT_FUNDS: "İşlem için yeterli bakiyeniz yok.",
  INSUFFICIENT_POSITION: "Satış için elinizde yeterli coin yok.",
  FILTER_VIOLATION: "Girilen miktar borsa kurallarına uymuyor.",
  DEPTH_EXCEEDED: "Piyasada bu fiyattan yeterli derinlik yok, daha küçük miktar deneyin.",
  QUOTE_STALE: "Piyasa fiyatı güncel değil. Lütfen biraz bekleyin.",
  PRICE_MOVED: "İşlem sırasında fiyat değişti. Önizlemeyi kontrol edip tekrar deneyin.",
  IDEMPOTENCY_KEY_REUSED: "Bu emir zaten gönderilmiş.",
  BAD_CURSOR: "Sayfalama verisi geçersiz. Lütfen sayfayı yenileyin.",
};

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  // Başına '/api' ekle (örnek: '/auth/login' -> '/api/auth/login')
  const url = path.startsWith("/api")
    ? path
    : `/api${path.startsWith("/") ? "" : "/"}${path}`;

  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers,
      credentials: "include", // Çerez tabanlı oturum için zorunlu
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Sunucuya bağlanılamadı. Backend servisinin çalıştığından emin olun."
    );
  }

  // 204 No Content (içeriksiz başarılı cevap, örn: çıkış yapma)
  if (res.status === 204) {
    return null as T;
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const code =
      data?.error?.code ??
      data?.code ??
      (res.status === 401 ? "NOT_AUTHENTICATED" : "UNKNOWN_ERROR");

    // Backend'in gönderdiği mesaj varsa onu kullan, yoksa haritadan eşleştir
    let message = data?.error?.message ?? data?.message;
    if (!message && data?.detail) {
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map((d: any) => d.msg || "Geçersiz alan").join(", ");
      }
    }

    let finalMessage = message || ERROR_MESSAGES[code];
    if (!finalMessage) {
      if (res.status >= 500 && !data) {
        finalMessage = "Backend sunucusuna ulaşılamıyor (port 8000 kapalı veya servis çalışmıyor). Lütfen backend'i başlatın.";
      } else {
        finalMessage = "Beklenmeyen bir hata meydana geldi.";
      }
    }
    throw new ApiError(res.status, code, finalMessage);
  }

  return data as T;
}

export type UserInfo = {
  id: string;
  email: string;
  cash?: string;
};

export const api = {
  // Kimlik doğrulama işlemleri
  register: (email: string, password: string) =>
    apiFetch<UserInfo>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    apiFetch<UserInfo>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () =>
    apiFetch<null>("/auth/logout", {
      method: "POST",
    }),

  me: () =>
    apiFetch<UserInfo>("/me", {
      method: "GET",
    }),
};
