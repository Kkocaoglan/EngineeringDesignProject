# Ekip Rehberi: kurulum, günlük çalışma ve kurallar

Bu dosya K1, K2 ve K3'ün hepsi için. Uzun rehberle (Proje_Uygulama_Rehberi.pdf) çelişirse
**Ek Rehber v1.1** ve bu dosya geçerlidir.

Repo: https://github.com/Kkocaoglan/EngineeringDesignProject

---

## 1. İlk kurulum (her bilgisayarda bir kez)

| Araç | Sürüm | Kontrol komutu |
|---|---|---|
| Git (Windows'ta **Git Bash** ile gelir) | herhangi | `git --version` |
| Docker Desktop | açık olmalı (görev çubuğunda balina) | `docker compose version` |
| Python | **3.12.x** | `python --version` veya `py -3.12 --version` |
| Node.js | **22 LTS** (CI 22 kullanır; 24 de çalışır) | `node --version` |
| VS Code | önerilir | |

> **Windows:** Bütün komutları **Git Bash** ile çalıştırın (PowerShell/CMD değil).
>
> **Windows:** `python` yazınca "Python was not found… Microsoft Store" çıkıyorsa Python
> PATH'te değildir. Ya Python'u "Add to PATH" seçeneğiyle yeniden kurun ya da sanal ortamı
> `py -3.12 -m venv .venv` ile oluşturun. Sanal ortamı aktif ettikten sonra `python` çalışır.

### Windows'ta önerilen ayar

Türkçe Windows'ta Python, dosyaya yazarken UTF-8 yerine Windows-1254 kodlamasını kullanır.
`app/export_openapi.py` bunu kendisi düzeltiyor; yine de başka betiklerde aynı sorunu
yaşamamak için Git Bash'te bir kez şunu çalıştırın, sonra Git Bash'i kapatıp açın:

```bash
echo 'export PYTHONUTF8=1' >> ~/.bashrc
```

---

## 2. Repoyu indir ve çalıştır

```bash
cd ~/Desktop
git clone https://github.com/Kkocaoglan/EngineeringDesignProject.git
cd EngineeringDesignProject
cp .env.example .env
docker compose up --build
```

İlk açılış 3–5 dakika sürer. Kontrol:

- http://localhost:5173 → "Backend durumu: ok"
- http://localhost:8000/docs → API dokümantasyonu

Durdurmak için `Ctrl + C`. Arka planda çalıştırmak için `docker compose up -d`.

> ⚠️ **`docker compose down -v` ASLA.** `-v` veritabanını siler. Sadece `docker compose down`.
>
> ⚠️ Siteyi **`localhost`** ile açın, `127.0.0.1` ile değil. Backend, POST isteklerinde
> Origin'i kontrol eder; `127.0.0.1` başka bir site sayılır ve giriş/kayıt 403 `BAD_ORIGIN` döner.

---

## 3. Günlük geliştirme (hızlı mod)

Docker'daki frontend ve backend, kod değişince **kendiliğinden yenilenmez**. Kod yazarken
veritabanını Docker'da, uygulamayı doğrudan bilgisayarda çalıştırın:

```bash
# 1) Sadece veritabanı
docker compose up -d db
```

```bash
# 2) Backend (ayrı terminal)
cd backend
py -3.12 -m venv .venv                 # sadece ilk sefer (veya: python -m venv .venv)
source .venv/Scripts/activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt   # ilk sefer ve requirements değişince
export DATABASE_URL=postgresql+asyncpg://app:app_dev_sifre@localhost:5432/portfolio
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

```bash
# 3) Frontend (ayrı terminal)
cd frontend
npm ci                                 # ilk sefer ve package-lock değişince
npm run dev
```

Bu modda Docker'daki backend/frontend kapalı olmalı (port çakışır). PR açmadan önce bir kez
`docker compose up --build` ile tam sistemi deneyin.

### Backend testleri

Testler bağlandıkları veritabanındaki tabloları **boşaltır**. Bu yüzden ayrı bir test
veritabanı kullanılır:

```bash
docker compose exec db createdb -U app portfolio_test     # sadece ilk sefer
cd backend
source .venv/Scripts/activate
export DATABASE_URL=postgresql+asyncpg://app:app_dev_sifre@localhost:5432/portfolio_test
export DB_POOL=null
alembic upgrade head
pytest -q
ruff check .
```

Yeni terminal açınca `source …activate` ve `export` satırları tekrar çalıştırılır.

### Frontend kontrolleri (CI'daki ile aynı)

```bash
cd frontend
npm run lint
npx tsc -b --noEmit
npx vitest run --passWithNoTests
npm run build
```

---

## 4. Bir işin yaşam döngüsü

1. Board'da issue sana atanmış olmalı → "Yapılıyor"a çek.
2. Branch **her zaman main'den** açılır, başkasının branch'inden asla:
   ```bash
   git checkout main
   git pull
   git checkout -b feat/k2-login-ekrani
   ```
3. Küçük commit'ler, günde en az bir push:
   ```bash
   git add .
   git commit -m "feat(auth-ui): giriş formu"
   git push -u origin feat/k2-login-ekrani
   ```
4. GitHub'da PR aç → şablonu doldur → `Closes #N` yaz → Reviewer ekle.
5. CI yeşil + 1 onay → **Squash and merge** → **Delete branch**.
6. Kendi bilgisayarında:
   ```bash
   git checkout main
   git pull
   git branch -d feat/k2-login-ekrani
   ```

**Kim kimi inceler:** K1'in PR'ını K2, K2'ninkini K3, K3'ünkini K1. 24 saatte cevap
yoksa üçüncü kişi inceler.

**İsimlendirme**
- Branch: `feat/k2-order-form`, `fix/k1-login-409`, `docs/k3-spike`
- Commit: `feat(market): …`, `fix(orders): …`, `docs: …`, `test(auth): …`, `chore: …`

**Sık karşılaşılanlar**
- PR'da **"Update branch"** butonu çıktı: Başka bir PR merge edilmiştir. Bas, CI tekrar
  yeşil olunca merge et. Normaldir.
- `main`'e doğrudan push reddedildi: Doğru davranış. Branch + PR kullan.
- **package-lock.json çakıştı:** Elle çözme. Main'deki hâlini al, `npm install` ile yeniden üret.
- **requirements.txt çakıştı:** İki satırı da tut.
- Merge conflict: `git fetch origin` ve `git merge origin/main` → VS Code'da doğru tarafı seç → emin değilsen
  dosyanın sahibine sor.

---

## 5. Kurallar (AI dahil herkes uyar; `CLAUDE.md` ile aynı)

- Görev bir issue'dur; sadece o issue'nun klasöründe çalışılır.
- **Para/miktar asla float veya JS `number` değildir.** DB `NUMERIC(28,8)`, Python
  `Decimal(str)`, API'de string, frontend'de `decimal.js`.
- Kâr/zarar ve portföy hesabı **sadece backend'de**. Frontend gösterir.
- **Migration'ları sadece K1 yazar.** Tablo ihtiyacın varsa issue aç.
- `trades` ve `cash_entries`'e UPDATE/DELETE yok; düzeltme yeni kayıttır.
- Fiyat yoksa ya da eskiyse emir reddedilir. Uydurma fiyat yok.
- Testlerde canlı Binance yok (fixture, ReplayProvider, sahte Clock).
- Var olan testleri ve kabul sayılarını "geçsin diye" değiştirme.
- Bir PR = bir iş. Yeni paket eklemek ekip kararıdır.
- `.env` asla repoya girmez (`.env.example` girer).
- Uvicorn tek worker (`--workers 1`).
- PR sahibi kodu açıklayabilmeli; "AI yazdı" cevap değildir.

### API değiştirirsen

`docs/api.md`'yi güncelle ve şemayı yeniden üret:

```bash
cd backend
python -m app.export_openapi > ../docs/openapi.json
```

Dosya güncel değilse CI kırmızı olur.

---

## 6. Sorun giderme

| Belirti | Sebep / çözüm |
|---|---|
| `port is already allocated` (5432) | Bilgisayarda başka PostgreSQL çalışıyor. Onu durdur ya da `docker-compose.yml`'de `"5432:5432"` → `"5433:5432"` (o zaman yerel URL'lerde de 5433). |
| `port is already allocated` (8000 / 5173) | Hızlı moddaki uvicorn / `npm run dev` açık. Kapat. |
| `bad interpreter` / `\r` hataları | Dosyalar CRLF'e dönmüş. Repo `.gitattributes` ile LF'e zorlar; repoyu yeniden klonla. |
| `failed to connect to the docker API` | Docker Desktop açık değil. |
| Giriş/kayıtta 403 `BAD_ORIGIN` | Siteyi `127.0.0.1` veya IP ile açtın. `localhost:5173` kullan. |
| CI'da "API sözleşmesi güncel mi?" kırmızı | `openapi.json`'u yeniden üret (Bölüm 5) ve PR'a ekle. |
| CI'da "Migration en fazla bir head mi?" kırmızı | İki migration çakıştı. K1'e haber ver. |
| `python` bulunamıyor | `py -3.12` kullan (Bölüm 1). |
| Telefondan test | Önce tarayıcının mobil görünümü (F12 → cihaz simgesi, 375 px). Gerçek telefonda giriş için `.env`'de `FRONTEND_ORIGIN`'i bilgisayarın IP adresiyle değiştirmek gerekir. |
