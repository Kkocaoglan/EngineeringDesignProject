import httpx
import asyncio
import websockets
import json
import time

def test_rest_api():
    print("--- REST API TESTİ BAŞLIYOR ---")
    url = "https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT"
    try:
        # requests yerine httpx kullanıldı ve 10 saniye zaman aşımı eklendi
        response = httpx.get(url, timeout=10.0)
        print(f"Durum Kodu: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("REST Bağlantısı Başarılı!")
            print(f"Sembol Bilgisi: {data['symbols'][0]['symbol']}")
        else:
            print("Hata:", response.text)
    except Exception as e:
        print("REST bağlantı hatası:", e)

async def test_websocket():
    print("\n--- WEBSOCKET TESTİ BAŞLIYOR (30 Saniye boyunca dinlenecek) ---")
    url = "wss://data-stream.binance.vision/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker"
    
    try:
        async with websockets.connect(url) as websocket:
            print("WebSocket bağlantısı kuruldu. Fiyatlar bekleniyor...")
            start_time = time.time()
            
            while time.time() - start_time < 30:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Gelen Mesaj: {json.dumps(data, indent=2)}")
                
    except Exception as e:
        print("WebSocket bağlantı hatası:", e)
    
    print("WebSocket testi süresi doldu ve tamamlandı.")

if __name__ == "__main__":
    test_rest_api()
    asyncio.run(test_websocket())