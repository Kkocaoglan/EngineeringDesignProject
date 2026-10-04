# Sanal Portföy ve İşlem Simülatörü (CEN317)

Gerçek Binance fiyatlarıyla, sanal bakiye üzerinden kripto alım-satım simülatörü.
Fiyatlar gerçek, para sanal. Yatırım tavsiyesi değildir.

## Hızlı başlangıç
Gereksinimler: Git, Docker Desktop. (Windows'ta komutları **Git Bash** ile çalıştırın.)

```bash
git clone https://github.com/Kkocaoglan/EngineeringDesignProject.git
cd EngineeringDesignProject
cp .env.example .env
docker compose up --build
```

- Web sitesi: http://localhost:5173 (`127.0.0.1` değil, `localhost` ile açın)
- API dokümantasyonu: http://localhost:8000/docs

> Uyarı: `docker compose down -v` veritabanını SİLER. `-v` kullanmayın.

## Testler (backend)
Testler bağlandıkları veritabanındaki tabloları boşaltır; bu yüzden ayrı bir test veritabanı
(`portfolio_test`) kullanılır.

```bash
docker compose up -d db
docker compose exec db createdb -U app portfolio_test     # sadece ilk sefer
cd backend
python -m venv .venv          # Windows'ta "python" bulunamazsa: py -3.12 -m venv .venv
source .venv/bin/activate     # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt
export DATABASE_URL=postgresql+asyncpg://app:app_dev_sifre@localhost:5432/portfolio_test
export DB_POOL=null
alembic upgrade head
pytest -q
ruff check .
```

Ekip için kurulum, günlük çalışma ve kurallar: [`docs/ekip-rehberi.md`](docs/ekip-rehberi.md).
Ayrıntılar: `docs/` klasörü ve proje rehberleri. (README Hafta 4'te tamamlanır.)
