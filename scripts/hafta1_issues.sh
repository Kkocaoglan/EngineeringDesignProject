#!/usr/bin/env bash
# Hafta 1 issue'larını GitHub'da tek seferde açar (isteğe bağlı; elle de açabilirsiniz).
# Gerekli: GitHub CLI (https://cli.github.com) ve bir kez `gh auth login`.
# Kullanım (repo klasöründe, Git Bash'te):
#   K1=kendi_kullanici_adin K2=arkadas1 K3=arkadas2 bash scripts/hafta1_issues.sh
set -euo pipefail
: "${K1:?K1 kullanıcı adı gerekli}" "${K2:?K2 kullanıcı adı gerekli}" "${K3:?K3 kullanıcı adı gerekli}"

for l in "k1:2563eb" "k2:059669" "k3:d97706" "ortak:7c3aed" "hafta-1:64748b"; do
  gh label create "${l%%:*}" --color "${l##*:}" --force >/dev/null
done

mk() { # mk <etiket> <atanan> <başlık> <açıklama>
  gh issue create --title "$3" --label "$1,hafta-1" --assignee "$2" --body "$4" >/dev/null
  echo "açıldı: $3"
}

mk ortak "$K1" "[Ortak] G1 Başlangıç toplantısı" "Rehberi birlikte oku, K1/K2/K3 isimleri, iletişim kanalı, toplantı saatleri."
mk ortak "$K1" "[Ortak] G2 API sözleşmesini dondur" "docs/api.md üç kişinin onayıyla dondurulur. Binance spike sonucu konuşulur."

mk k1 "$K1" "[K1] 1.1 Repo ve iskelet" "Klasörler, .gitignore, .gitattributes, .env.example, compose, Dockerfile'lar, PR şablonu, /health, main koruması, secret scanning."
mk k1 "$K1" "[K1] 1.2 CI" "ci.yml: lint, migration kontrolleri, pytest, OpenAPI farkı; frontend lint/tsc/vitest/build. Zorunlu kontrol olarak ayarla."
mk k1 "$K1" "[K1] 1.3 Veritabanı: users / accounts / cash_entries" "NUMERIC(28,8), CHECK cash >= 0, email UNIQUE. Migration 0001."
mk k1 "$K1" "[K1] 1.4 Kayıt ve giriş" "register (tek transaction, +10000 INITIAL), login (httpOnly çerez), logout, /me, CORS, Origin kontrolü."
mk k1 "$K1" "[K1] 1.5 Auth testleri" "409, 401, 401, başlangıç bakiyesi, argon2id."

mk k2 "$K2" "[K2] 2.1 React iskeleti ve sayfalar" "Router, /login /register /market /portfolio /history, korumalı sayfalar."
mk k2 "$K2" "[K2] 2.2 API istemcisi" "credentials: include, para string, openapi-typescript tipleri."
mk k2 "$K2" "[K2] 2.3 Giriş ve kayıt ekranları" "Türkçe hata mesajı, yükleniyor durumu."
mk k2 "$K2" "[K2] 2.4 Piyasa listesi" "Önce api.md mock verisi, sonra gerçek /markets. 375 px kontrolü."
mk k2 "$K2" "[K2] 2.5 Canlı bağlantı ve uyarılar" "useLiveStream, durum rozeti, sabit uyarı bandı."

mk k3 "$K3" "[K3] 3.1 Binance erişim testi (spike) — G2'ye kadar" "3 bilgisayar + okul ağı, docs/spike-binance.md."
mk k3 "$K3" "[K3] 3.2 Semboller ve borsa kuralları" "exchangeInfo → assets (migration'ı K1 yazar), önbellek davranışı."
mk k3 "$K3" "[K3] 3.3 Binance adaptörü ve fiyat hafızası" "Combined WS, Quote (Decimal), MarketDataProvider, Clock."
mk k3 "$K3" "[K3] 3.4 Yeniden bağlanma, /markets, /stream" "1-2-4…30 sn backoff, SSE saniyede 1."
mk k3 "$K3" "[K3] 3.5 Kayıt aracı ve fixture" "record_quotes.py, tests/fixtures/quotes_*.jsonl (< 1 MB)."
