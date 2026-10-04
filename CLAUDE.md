# Proje kuralları (AI dahil herkes uyar)
- Görev bir issue'dur; sadece o issue'nun klasöründe çalış. Başka klasöre
  dokunman gerekiyorsa DUR ve sor.
- Para/miktar: ASLA float veya JS number. DB NUMERIC(28,8), Python Decimal(str),
  API'de string, frontend'de decimal.js. Yuvarlama sadece app/money.py.
- Kâr/zarar ve portföy hesabı SADECE backend'de. Frontend gösterir.
- Migration'ları sadece K1 yazar. Alembic dosyası oluşturma, issue aç.
- trades ve cash_entries'e UPDATE/DELETE yazma; düzeltme yeni kayıttır.
- Fiyat yoksa/eskiyse emir reddedilir. Asla fiyat uydurma.
- Testlerde canlı Binance yok: fixture, ReplayProvider, sahte Clock.
- Kabul koşulundaki sayıları ve var olan testleri "geçsin diye" değiştirme.
- Bir PR = bir iş. İlgisiz değişiklikleri aynı PR'a koyma. Yeni paket ekleme, öner.
- API değişirse: docs/api.md + docs/openapi.json güncellenir
  (cd backend && python -m app.export_openapi > ../docs/openapi.json).
- Uvicorn tek worker çalışır (--workers 1).
