# Binance Erişim Testi (SPIKE) Sonuçları

## 1. Test Ortamı
* **Bağlantı Türü:** REST API ve WebSocket
* **Ortam:** Yerel Bilgisayar (Python 3.12) ve Okul Ağı
* **Kullanılan Adresler:** `data-api.binance.vision` ve `data-stream.binance.vision`

## 2. Test Sonuçları
* **REST API:** Başarılı. `exchangeInfo` üzerinden sembol bilgileri (BTCUSDT vb.) sorunsuz çekildi.
* **WebSocket:** Başarılı. 30 saniye boyunca `bookTicker` kanalından kesintisiz canlı bid/ask fiyatları alındı. Okul ağında bağlantı engeliyle karşılaşılmadı.

## 3. Gelen Veri Analizi (bookTicker)
WebSocket üzerinden gelen örnek bir mesaj şu şekildedir:

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