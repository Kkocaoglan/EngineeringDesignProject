# ADR 0001 — Web uygulaması ve alan bazlı görev bölünmesi
**Karar:** Responsive web (React + FastAPI). Görevler katmana göre değil alana göre bölünür
(K1 Hesap & İşlem, K2 Arayüz, K3 Piyasa & Değerleme).
**Neden:** 4 haftada tek kod tabanı, kolay demo; herkes hem kod hem test hem rapor yazar.
**Alternatifler:** Flutter/React Native mobil (ek 15–20 saat, demo ağ riski), katman bölünmesi.
