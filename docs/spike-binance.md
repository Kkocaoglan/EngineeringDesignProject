# Binance Erişim Testi (SPIKE) Sonuçları

## 1. Test Ortamı

* **Bağlantı Türü:** REST API ve WebSocket
* **Ortam:** Tek bilgisayar + okul ağı üzerinde test edildi; ekip kararıyla yeterli görüldü.
* **Kullanılan Adresler:** `data-api.binance.vision` (REST) ve `data-stream.binance.vision` (WebSocket)
* **Kütüphaneler:** `httpx` (REST, `timeout=10.0`), `websockets` (WS)

## 2. Test Sonuçları

| Test | Sonuç | Not |
|---|---|---|
| REST `exchangeInfo` | ✅ Başarılı | 200 OK, sembol bilgisi alındı |
| WebSocket `bookTicker` (30 sn) | ✅ Başarılı | Kesintisiz bid/ask verisi aktı |
| Okul ağı erişimi | ✅ Başarılı | Binance `data-*` adresleri engelsiz |

## 3. Gelen Veri Analizi (bookTicker)

WebSocket üzerinden gelen örnek bir `btcusdt@bookTicker` mesajı:

```json
{
  "stream": "btcusdt@bookTicker",
  "data": {
    "u": 101379076336,
    "s": "BTCUSDT",
    "b": "83180.00000000",
    "B": "3.70791000",
    "a": "83180.01000000",
    "A": "5.85900000"
  }
}
```

### ⚠️ Önemli Bulgu: Zaman Alanı Yok

`bookTicker` mesajında **zaman bilgisi (timestamp) bulunmuyor** — sadece `u` (updateId), `s`, `b`, `B`, `a`, `A` alanları var.

**Tasarım kararı:** `QuoteGuard`, fiyat tazeliğini Binance'ın zaman bilgisiyle değil, **sunucumuzun mesajı aldığı UTC zamanıyla (`received_at`)** takip edecek. Bu değer, WebSocket'ten mesaj geldiğinde `datetime.now(UTC)` olarak atanır.

## 4. Binance Kullanım Koşulları — Veri Gösterimi Özeti

Binance'ın [API Kullanım Koşulları](https://www.binance.com/en/terms) veri gösterimine ilişkin ana maddeler:

- **Yalnızca fiyat okuma:** `data-api.binance.vision` ve `data-stream.binance.vision` adresleri, API anahtarı gerektirmeksizin piyasa verisi sunmak için tasarlanmıştır. Bu proje bu verileri **yalnızca görüntüleme amacıyla** kullanmaktadır.
- **Gerçek emir yok:** Binance'a herhangi bir alım-satım emri gönderilmemektedir; bakiye ve işlemler tamamen kendi sistemimizde tutulmaktadır.
- **Kaynak belirtimi:** Ekranda "Veri kaynağı: Binance" ibaresi sabit olarak gösterilecektir.
- **Ticari kullanım kısıtlaması:** Bu proje bir ders ödevi olup ticari amaç taşımamaktadır; bu nedenle akademik kullanım kapsamında değerlendirilmektedir.
