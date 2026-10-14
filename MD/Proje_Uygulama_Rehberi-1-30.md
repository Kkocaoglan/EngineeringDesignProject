CEN317 · ENGINEERING DESIGN 

# **Proje Uygulama Rehberi** 

### Sanal Portföy ve İşlem Simülatörü 

3 kişi · 4 hafta · gerçek Binance verisi · adım adım, kim ne yapacak 



<!-- Start of picture text -->
Binance<br><!-- End of picture text -->

**canlı fiyat sanal emir portföy + K/Z** 

**ekran** 

_Fiyatlar gerçek, para sanal: Binance'tan yalnızca fiyat okunur; bakiye, emir ve kâr/zarar bizim sistemimizde._ 



<!-- Start of picture text -->
K1<br>Hesap ve İşlem<br><!-- End of picture text -->

kayıt/giriş · bakiye · emir motoru veritabanı · GitHub/CI Ad: ____________________ 

**K2 K3 Arayüz Piyasa ve Değerleme** tüm ekranlar · canlı fiyat · grafikler Binance bağlantısı · QuoteGuard E2E testler · demo kâr/zarar hesabı · REPLAY Ad: ____________________ Ad: ____________________ 

###### **Bu rehberde** 

- 12 görsel: uçtan uca akış, sistem şeması, veri modeli, takvim, GitHub ve CI akışları 

- Her hafta, her kişi için görevler, süreler ve işaretlenebilir kabul koşulları 

- GitHub kullanımı adım adım: branch, commit, PR, inceleme, merge conflict 

- Kopyala-yapıştır hazır dosyalar: docker-compose, CI, .env, PR şablonu, API sözleşmesi 

_Takvim varsayımı: 5 Ekim – 1 Kasım 2026 · Bu belge bir plandır, gerçekleşen ilerleme değildir._ 

Sanal Portföy · Proje Uygulama Rehberi 

## **İçindekiler** 

- **01** Bu belge nasıl kullanılır? **02** Web mi mobil mi? **03** Sistem tek paragrafta **04** Bilmen gereken 15 kelime **05** Sistemin görselleri (akış şemaları) **06** Kim ne yapıyor? Üçe bölünme ve adalet **07** Proje klasör yapısı 

- **08** İlk gün kurulumu (herkes) **09** GitHub: birlikte nasıl çalışacağız? **10** CI/CD gerekli mi? **11** Hafta hafta yapılacaklar ve kabul koşulları **12** Toplantılar 

- **13** "Bitti" ne demek? (Definition of Done) 

- **14** Bir şey ters giderse ne yapılır? **15** Yapma listesi **16** Teslim günü kontrol listesi 

- **17** Ek: Hazır dosyalar 

**Nasıl okunur:** Herkes 1–10 arası bölümleri okur (ortak kurallar). Bölüm 11'de her hafta her kişinin işi ayrı renkte yazılı; kendi işinle birlikte diğer ikisinin işini de oku. ☐ kutularını repodaki `.md` dosyasında `[x]` yaparak takip edin. 

CEN317 · 3 kişilik ekip · 4 hafta 

2 

Sanal Portföy · Proje Uygulama Rehberi 

## **1  Bu belge nasıl kullanılır?** 

- **Herkes** 1–10 arası bölümleri okur. Bunlar ortak kurallardır. 

- **Bölüm 11** 'de her hafta her kişinin işi ayrı yazılmıştır. Sadece kendi başlığını değil, diğer ikisinin işini de oku. Çünkü işler birbirine bağlı. 

- Her görevin yanında `[ ]` kutusu var. Bu dosyayı repoya koyun ve biten işleri `[x]` yapın. Takip bu kadar basit. 

- Kişiler **K1, K2, K3** diye geçiyor. İlk toplantıda isimlerinizi yazın: 

   - **K1 — Hesap ve İşlem:** `__________` 

   - **K2 — Arayüz:** `__________` 

   - **K3 — Piyasa Verisi ve Değerleme:** `__________` 

**Tarih varsayımı:** Gün 1 (G1) = **5 Ekim 2026 Pazartesi** , G28 = **1 Kasım 2026 Pazar** . Teslim tarihiniz farklıysa sadece tarihleri kaydırın, iş sırası aynı kalır. **Dikkat:** 28 Ekim yarım gün, 29 Ekim resmî tatil (Cumhuriyet Bayramı). 4. hafta bu yüzden biraz daha kısa. 

## **2  Web mi mobil mi?** 

**Karar: Web.** Ama telefondan da düzgün görünen (responsive) bir web sitesi. 

Neden: 

- **Tek kod, her cihaz.** Web sitesi bilgisayarda da telefonda da tarayıcıdan açılır. Mobil uygulama yazsaydık ayrıca Android/iOS derleme, emülatör, mağaza gibi dertlerle uğraşırdık. 

- **Demo kolay.** Hocaya bir link ya da `localhost` açarsın, biter. Telefona uygulama yüklemek gerekmez. 

- **4 hafta kısa.** Mobil uygulama ekstra 1–2 hafta yer. 

- **Ders mobil istemiyor.** Ders tanımı sadece "portföy yönetim sistemi" diyor. 

"Telefondan da düzgün görünsün" ne demek: K2 her ekranı tarayıcının geliştirici araçlarında telefon boyutunda (375 px genişlik) kontrol eder. Yazılar taşmıyor, butonlar basılabiliyorsa tamam. 

## **3  Sistem tek paragrafta** 

Kullanıcı web sitesine kayıt olur ve hesabına **10.000 sanal USDT** yüklenir (gerçek para değil). Ekranda Binance borsasından gelen **gerçek, canlı** kripto fiyatlarını görür (BTC, ETH, BNB, XRP, SOL). "0,01 BTC al" dediğinde sistem gerçek piyasadaki satış fiyatını (ask) kullanır, %0,1 komisyon keser, bakiyesinden düşer ve BTC'yi portföyüne ekler. Fiyatlar değiştikçe portföyünün değeri ve kâr/zararı **saniyede bir** güncellenir. Binance bağlantısı koparsa sistem alım-satımı kapatır, bağlantı gelince tekrar açar. 

**Önemli:** Binance'ta gerçek emir **vermiyoruz** . Binance'tan sadece **fiyat okuyoruz** . Alım-satım, bakiye ve kâr/zarar tamamen **bizim** sistemimizde, bizim veritabanımızda. Bu yüzden Binance hesabı veya API anahtarı gerekmiyor. 

CEN317 · 3 kişilik ekip · 4 hafta 

3 

Sanal Portföy · Proje Uygulama Rehberi 

## **4  Bilmen gereken 15 kelime** 

|**Kelime**|**Basitçe ne demek?**|
|---|---|
|**Frontend**|Kullanıcının gördüğü web sayfası (React). K2'nin alanı.|
|**Backend**|Arka planda çalışan sunucu; hesap tutar, hesaplar (FastAPI, Python).|
|**API**|Frontend'in backend'e "şunu yap" dediği adresler. Örnek:`POST /orders`.|
|**Veritabanı (DB)**|Verilerin kalıcı saklandığı yer (PostgreSQL).|
|**WebSocket**|Açık kalan bir telefon hattı gibi; Binance fiyatı değişince bize kendisi söyler.|
|**SSE**|Backend'den tarayıcıya tek yönlü canlı yayın. Fiyatları ekrana böyle göndeririz.|
|**Bid / Ask**|Bid = satarken alacağın fiyat. Ask = alırken ödeyeceğin fiyat. Ask her zaman biraz daha<br>yüksektir.|
|**Spread**|Ask ile bid arasındaki fark.|
|**Transaction**|"Ya hepsi olur ya hiçbiri." Para düşüp BTC eklenmemesi gibi yarım işleri engeller.|
|**Idempotency**|Kullanıcı butona iki kez basarsa işlemin iki kez yapılmaması.|
|**Migration**|Veritabanı tablolarını kodla oluşturma/değiştirme dosyası (Alembic).|
|**Branch**|Kodun kopyası. Herkes kendi kopyasında çalışır, ana kodu bozmaz.|
|**Pull Request (PR)**|"Kodumu ana koda eklemek istiyorum, bir kontrol eder misin?" isteği.|
|**CI**|Her PR'da testleri otomatik çalıştıran GitHub robotu.|
|**Docker Compose**|Tek komutla (veritabanı + backend + frontend) her şeyi başlatan araç.|



CEN317 · 3 kişilik ekip · 4 hafta 

4 

Sanal Portföy · Proje Uygulama Rehberi 

## **5  Sistemin görselleri (flowchart)** 

##### **5.1 Uçtan uca kullanıcı akışı** 

Kullanıcı siteye girdiği andan emir verip sonucunu gördüğü ana kadar olan her şey: 



<!-- Start of picture text -->
Kullanict siteyi acar<br>Hesabi<br>var mi?<br>10.000 sanalKayitUSDTolur yiiklenir Evet<br>Giris yapar<br>Piyasa ekran!<br>5 coinin canlt bid / ask fiyati<br>Emir formu rae<br>AL/ SAT + miktar x.<br>tahmini Onizlemefiyat + komisyon an an<br>Onayla + POST /orders \<br>paglere seguir? Hey"ayr S| VeritabanindaReddedilir:© kullanicihicbirfiyatforma eski seydéner dedismez (409) . \\ \ ekran gincellenir<br>.<br>\<br>Evet \<br>\<br>1<br>1<br>Bakiye<br>ve borsa/ eldekikurallan miktar Hayir_( Veritabaninda Reddedilir: nedenihicbirgésterilirsey degismez (422) 11<br>uygun mu? © kullanici forma déner i<br>,<br>Evet /<br>TEK TRANSACTION<br>® nakit hareketi @ islem kaydi @ pozisyon uo<br>Portféy yeniden hesaplanir oa<br>ortalama maliyet<br>: kar/ zarar _?<br>Sonuc aninda ekrana génderilir (SSE)<br><!-- End of picture text -->

_Şekil 1 — Uçtan uca kullanıcı akışı. Reddedilen emirlerde veritabanında hiçbir şey değişmez._ 

##### **5.2 Sistem parçaları ve kimin sorumluluğunda oldukları** 

Renkler yerine kutu başlıklarında kişi adı var: 

CEN317 · 3 kişilik ekip · 4 hafta 

5 

Sanal Portföy · Proje Uygulama Rehberi 



<!-- Start of picture text -->
‘ Disdinya<br>''<br>'Binance Spot |<br>\ canli fiyat \<br>, | WebSocket + REST } |<br>N /<br>yat akisi<br>K3 - Piyasa verisi ve qdegerleme<br>Binance adaptori<br>veriyi alir, cevirir<br>QuoteGuard<br>fiyat hafizasi +<br>baglanti sagligi<br>\<br>syat S<br>\<br>\<br>afe) \\ SSE fiyatlar (1 sn)<br>\<br>\\<br>\SSE: portféy (1 sn) 1 aze fiyat<br>N<br>React web sitesi<br>bilgisayar + telefon<br>—.;<br>\dakikada 1 kayit fest ay. angst emir<br>Cengisd Ot transaction + kontroller<br>' re 7 Emir motoru |<br>——<br>PostgreSQL<br>veritaban!<br><!-- End of picture text -->

_Şekil 2 — Sistem parçaları ve sahiplikleri. Kutular aynı sunucudaki modüllerdir, ayrı servis değildir._ 

##### **5.3 Fiyat nasıl ekrana geliyor? (zaman sırası)** 

CEN317 · 3 kişilik ekip · 4 hafta 

6 

Sanal Portföy · Proje Uygulama Rehberi 



<!-- Start of picture text -->
: Adaptér +<br>OAS CE)<br>bookTicker: BTC bid/ask degisti_, ’ i<br>(saniyede defalarca) ' ' '<br>———————_—_—> ' \ \<br>\\<br>\\<br>' \<br>1 \ \<br>c | © HER1SANIYEDE BIR | if a<br>! I SSE ‘quote’: 5 coinin son fiyatlar! 1 !<br>1 —_—_—_—_——_—$—$—$S$—$—$———————— rs<br>{'1<br>!' ' \ '<br>! i son fiyatlar 0 0 !<br>{I<br>!1 ' \ !<br>1{I''!'eee!SSE 'portfolio_updated' 1 HH<br>\' \ \ H<br>\ 1 f \ }<br>Te<br>\ \ 1<br>Kullanici islem yaptiysa 1 saniye baklenmez: portféy hemen génderilin,<br>' 1 '<br><!-- End of picture text -->

_Şekil 3 — Fiyatın Binance'tan ekrana gelişi: veri anında alınır, ekrana saniyede bir gönderilir._ 

##### **5.4 Binance bağlantısı koparsa ne olur?** 



<!-- Start of picture text -->
esuewvon erie KAPAL<br><!-- End of picture text -->

_Şekil 4 — Binance bağlantı durumları. Emirler yalnızca SAĞLIKLI durumda açıktır._ 

**Kural:** Bağlantı yokken **asla** uydurma fiyat üretmeyiz. Emir butonu kilitlenir ve ekranda "Canlı veri alınamıyor, emirler geçici olarak kapalı" yazar. 

##### **5.5 Veritabanı tabloları** 

CEN317 · 3 kişilik ekip · 4 hafta 

7 

Sanal Portföy · Proje Uygulama Rehberi 



<!-- Start of picture text -->
orders<br>id ww<br>trades<br>side suriseLt<br>quantity numeric | price, aty, fee numeric<br>Sige ask cans<br>Adempotency key unique .<br>- cash entries<br>status quote received at tinestemots | ~~ ~~ | ‘anount +<br>kind wimiayauviseu<br>4<br>__<br>users ott _ tradeid ne<br>id wus<br>email unique useridash numeri28) ¢ portfolio snapshots<br>password_hash sigon2id taken_at timestamotz<br>currency uso<br>positions<br>symbol Px<br>assets<br>‘quantity. numene<br>symbol cost basis numere<br>step_sizetick size realizedpnt numeric<br>sin_notional<br>Y candies_im<br>symbol, open_tine Px<br><!-- End of picture text -->

_Şekil 5 — Veritabanı tabloları. Mavi: K1'in, turuncu: K3'ün sorumluluğunda._ 

**Tablo sahipliği:** `users` , `accounts` , `orders` , `trades` , `cash_entries` → **K1** . `assets` , `positions` , `candles_1m` , `portfolio_snapshots` → **K3** . 

##### **5.6 4 haftalık takvim** 



<!-- Start of picture text -->
HAFTA 1 HAFTA 2 HAFTA 3 HAFTA 4<br>Hesap & islemLaSAE Repo, Cl, Docker, giris sistemi HHf]Hl — Emir motoru, komisyon HIfH HHfH Kurulum, belge, hata dizeltme HlyH<br>Ls Hf Emir formu, islem gecmisi ff Portféy, grafikler, E2E testler Kullanilabilirlik, demo H<br>Arayiiz H H i H<br>Piyasai  & Degerlemeserie Binance baglantist HH]Hl QuoteGuard, porttéy hesabi HfiH Mum gecmisi, kesinti, REPLAY H|H Dogruluk kaniti, rapor HH<br>t i i i i t<br>API sézlesmesiSa itk demoo ‘Alig-satis° OK Gzellikodondurma ° Testiof<br>Teslim aday!<br>5 Eki 12 ki 19 Eki 26 Eki 1 kas<br><!-- End of picture text -->

_Şekil 6 — 4 haftalık takvim ve kilometre taşları (G1 = 5 Ekim 2026)._ 

CEN317 · 3 kişilik ekip · 4 hafta 

8 

Sanal Portföy · Proje Uygulama Rehberi 

## **6  Kim ne yapıyor? Üçe bölünme ve adalet** 

##### **6.1 Neden "biri backend, biri frontend, biri rapor" DEĞİL?** 

Çünkü: 

- Raporu yazan kişi kod yazmamış olur. Hem öğrenemez hem sunumda hocanın sorularına cevap veremez. 

- Tek backend kişisi herkesi bekletir (darboğaz). O hastalanırsa proje durur. 

- Hoca "kim ne yaptı?" diye sorduğunda cevap dengesiz görünür. 

##### **6.2 Bunun yerine: her kişi bir alanın sahibi** 

###### **K1 — Hesap ve İşlem ("bankacı")** 

- Yaptığı: kayıt/giriş, bakiye, alış-satış motoru, veritabanı kuruluşu, GitHub/CI kurulumu. 

- Sorumlu olduğu tehlike: "Aynı para iki kez harcandı" veya "para düştü ama coin eklenmedi." 

- Kod klasörü: `backend/app/auth/` , `backend/app/orders/` , `backend/alembic/` . 

###### **K2 — Arayüz ("vitrinci")** 

- Yaptığı: tüm ekranlar, canlı fiyatın ekrana gelmesi, emir formu, grafikler, uçtan uca testler, demo senaryosu. 

- Sorumlu olduğu tehlike: "Eski fiyat canlıymış gibi göründü" veya "kullanıcı hata mesajını anlamadı." 

- Kod klasörü: `frontend/` . 

###### **K3 — Piyasa Verisi ve Değerleme ("borsacı")** 

- Yaptığı: Binance bağlantısı, fiyat hafızası, bağlantı kopunca ne olacağı, portföy ve kâr/zarar hesabı. 

- Sorumlu olduğu tehlike: "Binance koptu ve kimse fark etmedi" veya "kâr/zarar yanlış hesaplandı." 

- Kod klasörü: `backend/app/market/` , `backend/app/portfolio/` , `backend/app/stream/` . 

##### **6.3 Adalet nasıl sağlanıyor?** 



<!-- Start of picture text -->
Planii is saati (4 hafta) Zorluk tid (1-5, ekip ici tahmin)<br>40 saat 40 saat 40 saat mks me<br>Ea Ea | me | 45<br>H3-10sa<br>3<br>1<br>H1- 10s H1- 10s H1- 10s<br>o<br>Kl Hesap K2 Arayiz K3 Piyasa Teknik Entegrasyon Belirsizlik Demo<br>keith gérainurlaga<br><!-- End of picture text -->

_Şekil 8 — Solda herkesin eşit saati, sağda farklı ama dengeli zorluk türleri._ 

**Saat olarak:** Her kişi 4 hafta boyunca haftada ~10 saat planlı iş yapar, toplamda **40 saat** . Bunun üstüne herkese haftada 2,5 saat toplantı/inceleme ve 2,5 saat yedek süre ayrılır. Kişi başı haftalık yük: ~15 saat. 

|**Hafta**|**K1**|**K2**|**K3**|
|---|---|---|---|
|1|10 sa|10 sa|10 sa|
|2|10 sa|10 sa|10 sa|
|3|10 sa|10 sa|10 sa|
|4|10 sa|10 sa|10 sa|
|**Toplam**|**40 sa**|**40 sa**|**40 sa**|



**Zorluk türü olarak:** Yükler farklı türde ama eşit ağırlıkta. 

CEN317 · 3 kişilik ekip · 4 hafta 

9 

Sanal Portföy · Proje Uygulama Rehberi 

- K1'in işi **teknik olarak kritik** : para hatası affedilmez. 

- K2'nin işi **en görünür ve entegrasyonu en çok olan** iş: herkesin kodunu ekranda birleştirir. 

- K3'ün işi **en belirsiz** iş: dış servise bağımlı. Bu yüzden K3'ün yükü hafifletildi; komisyon ve gerçekleşme fiyatı K1'e, grafik ekranları K2'ye verildi. 

###### **Herkes aynı şeyleri de yapar:** 

- Kendi kodunun testini yazar. 

- Kendi alanının rapor bölümünü yazar. 

- Başka birinin kodunu inceler (Bölüm 9.7). 

- Sprint Review'da kendi kısmını kendisi gösterir. 

**Dengesizlik kuralı:** Bir iş planlanan sürenin 1,5 katını geçerse Daily'de söylenir. Başka biri yardım eder ve daha az önemli bir iş o haftadan çıkarılır. İki hafta üst üste birinin yükü diğerlerinden %20 fazla çıkarsa görevler yeniden dağıtılır. Herkes her hafta harcadığı saati `docs/saatler.md` dosyasına yazar. Bu hem adaleti ölçer hem rapora kanıt olur. 

##### **6.4 Yan roller (dönüşümlü)** 

|**Rol**|**Ne yapar?**|**Hafta**|**Hafta**|
|---|---|---|---|
|||**1–2**|**3–4**|
|**Product Owner**<br>**(PO)**|İşlerin önceliğini belirler, "bu yeterli mi?" kararını verir|K2|K2|
|**Scrum Master**|Toplantıları başlatır, süreyi tutar, engelleri takip eder|K1|K3|
|**(SM)**||||
|**Son editör**|Raporu tek biçimde birleştirir (yazmaz, birleştirir)|K2|K2|



K2'nin iki yan rolü var ama PO rolü haftada ~30 dakika sürer, editörlük de sadece 4. haftada 2 saat alır. Bu süreler K2'nin 40 saatinin içinde hesaplandı. 

## **7  Proje klasör yapısı** 

Tek repo (monorepo) kullanıyoruz. Backend ve frontend aynı repoda, ayrı klasörlerde duruyor. 

CEN317 · 3 kişilik ekip · 4 hafta 

10 

Sanal Portföy · Proje Uygulama Rehberi 



<!-- Start of picture text -->
sanal-portfoy/<br>├── backend/                      ← Python / FastAPI<br>│   ├── app/<br>│   │   ├── main.py               ← uygulamanın giriş noktası (K1)<br>│   │   ├── config.py             ← .env ayarlarını okur (K1)<br>│   │   ├── db.py                 ← veritabanı bağlantısı (K1)<br>│   │   ├── money.py              ← Decimal yuvarlama kuralı, TEK yerde (K3)<br>│   │   ├── auth/                 ← kayıt, giriş (K1)<br>│   │   ├── orders/               ← emir motoru (K1)<br>│   │   ├── market/               ← Binance adaptörü, QuoteGuard (K3)<br>│   │   ├── portfolio/            ← kâr/zarar hesabı (K3)<br>│   │   └── stream/               ← SSE yayını (K3)<br>│   ├── alembic/                  ← veritabanı migration dosyaları (K1, K3)<br>│   ├── tests/<br>│   │   ├── fixtures/             ← kaydedilmiş gerçek Binance verisi (K3)<br>│   │   ├── test_auth.py<br>│   │   ├── test_orders.py<br>│   │   └── test_portfolio.py<br>│   ├── scripts/<br>│   │   └── record_quotes.py      ← Binance verisini kaydeden araç (K3)<br>│   ├── requirements.txt<br>│   ├── requirements-dev.txt<br>│   └── Dockerfile<br>├── frontend/                     ← React + TypeScript (K2)<br>│   ├── src/<br>│   │   ├── pages/                ← Login, Register, Market, Portfolio, History<br>│   │   ├── components/           ← OrderForm, PriceTable, StatusBadge, Charts<br>│   │   ├── api/                  ← backend'e istek atan fonksiyonlar<br>│   │   └── hooks/                ← useLiveStream (SSE)<br>│   ├── e2e/                      ← Playwright testleri<br>│   ├── package.json<br>│   └── Dockerfile<br>├── docs/<br>│   ├── api.md                    ← API sözleşmesi (G2'de dondurulur)<br>│   ├── adr/                      ← karar kayıtları<br>│   ├── spike-binance.md          ← Binance erişim testi sonucu (K3)<br>│   ├── saatler.md                ← herkesin haftalık saati<br>│   └── rapor/                    ← rapor bölümleri<br>├── .github/<br>│   ├── workflows/ci.yml          ← otomatik testler<br>│   └── pull_request_template.md<br>├── docker-compose.yml<br>├── .env.example                  ← örnek ayarlar (gerçek .env ASLA repoya girmez)<br>├── .gitignore<br>└── README.md<br><!-- End of picture text -->

**Neden bu yapı önemli?** Herkes çoğunlukla kendi klasöründe çalışır. Böylece aynı dosyayı iki kişinin değiştirmesi (merge conflict) nadiren olur. 

## **8  İlk gün kurulumu (herkes)** 

Her ekip üyesi kendi bilgisayarına şunları kurar: 

1. **Git** → https://git-scm.com. Kurunca terminalde `git --version` çalışmalı. 

2. **Docker Desktop** → https://www.docker.com/products/docker-desktop. `docker compose version` çalışmalı. 

3. **Python 3.12** → `python --version` 

4. **Node.js 20 LTS veya üstü** → `node --version` 

5. **VS Code** ve şu eklentiler: Python, ESLint, Prettier, Docker, GitLens, Markdown Preview Mermaid Support. 

6. **GitHub hesabı.** Öğrenciyseniz **GitHub Student Developer Pack** 'e başvurun (ücretsiz GitHub Pro verir, Bölüm 9.2'de neden gerektiği açıklanıyor). 

Git'e kim olduğunu söyle (bir kez yapılır): 

```
git config --global user.name "Ad Soyad"
git config --global user.email "github-hesabindaki@eposta.com"
```

Kurulum sonrası kontrol: repoyu klonla (Bölüm 9.4) ve çalıştır: 

CEN317 · 3 kişilik ekip · 4 hafta 

11 

Sanal Portföy · Proje Uygulama Rehberi 

```
cp .env.example .env
docker compose up --build
```

- http://localhost:5173 → web sitesi açılmalı. 

- http://localhost:8000/docs → API dokümantasyonu açılmalı. 

İkisi açılıyorsa kurulumun tamam. 

CEN317 · 3 kişilik ekip · 4 hafta 

12 

Sanal Portföy · Proje Uygulama Rehberi 

## **9  GitHub: birlikte nasıl çalışacağız?** 

##### **9.1 Temel fikir (bunu anla, gerisi kolay)** 

1. `main` , projenin **her zaman çalışan** hâlidir. 

2. Bir iş yapacaksan `main` 'den kendine bir **branch** (kopya) açarsın. 

3. Kopyanda istediğin kadar denersin, bozarsın, düzeltirsin. Bu sırada kimseyi etkilemezsin. 

4. İş bitince **Pull Request (PR)** açarsın: "Bunu main'e eklemek istiyorum." 

5. GitHub testleri otomatik çalıştırır (CI). **Bir arkadaşın** kodu inceler ve onaylar. 

6. Onay gelince PR `main` 'e eklenir (merge). Branch silinir. 

Bu yönteme **GitHub Flow** denir. İnternette göreceğin `develop` , `release` , `hotfix` branch'li **Git Flow** 3 kişilik 4 haftalık proje için gereksiz karmaşık. **Kullanmıyoruz.** 



<!-- Start of picture text -->
main — her zaman calisan kod, direkt push YASAK<br>PR + onay + Cl PR + onay + Cl PR + onay + Cl<br>feat/k1-register-ldgin L feat/k3-binance-adapter<br>feat/k2-market-list<br>main’deki yenilikleri kendi branch’ine al (git merge origin/main)<br><!-- End of picture text -->

_Şekil 7 — GitHub Flow: herkes kendi branch'inde çalışır, main'e sadece onaylı PR ile girilir._ 

##### **9.2 Repo kurulumu (sadece K1, G1'de, ~30 dakika)** 

1. GitHub'da **New repository** → isim: `sanal-portfoy` . 

2. **Public mi private mı?** 

   - Main branch'i korumak (Bölüm 9.3) GitHub'ın ücretsiz planında **public** repolarda çalışır. Private repoda korumak için repo sahibinin GitHub Pro olması gerekir; Student Pack bunu ücretsiz verir. 

   - Hocanız kodun gizli olmasını istiyorsa: private repo + K1'in hesabı Student Pack ile Pro olmalı. 

   - İstemiyorsa: public repo, sorun yok. (Repoya şifre veya gizli bilgi koymadığımız sürece.) 

3. **Settings → Collaborators → Add people** → K2 ve K3'ü ekle. Onlar gelen daveti kabul etsin. 

4. Bölüm 7'deki klasörleri, `.gitignore` , `.env.example` , `docker-compose.yml` , CI dosyası ve PR şablonunu ekle (hepsi Bölüm 17'de hazır). 

5. **Projects** sekmesi → **New project** → **Board** şablonu. Kolonlar: `Yapılacak` , `Yapılıyor` , `İncelemede` , `Bitti` . 

6. Bölüm 11'deki her görevi bir **Issue** olarak aç. Başlık örneği: `[K1] 1.3 Kayıt/giriş API` . Issue'yu sahibine ata ve board'a ekle. 

##### **9.3 Main branch'i koruma (K1, ~5 dakika)** 

**Settings → Branches → Add branch protection rule** (veya **Rulesets** ), branch adı `main` : 

- ✓ **Require a pull request before merging** 

   - ✓ **Require approvals: 1** 

- ✓ **Require status checks to pass before merging** → CI'daki `backend` ve `frontend` işlerini seç (CI bir kez çalıştıktan sonra listede görünür). 

- ✓ **Require branches to be up to date before merging** 

- ✓ **Block force pushes** 

- ✗ Do not allow bypassing: işaretleyin ki K1 dahil kimse kuralları atlayamasın. 

CEN317 · 3 kişilik ekip · 4 hafta 

13 

Sanal Portföy · Proje Uygulama Rehberi 

Bu kurallardan sonra kimse `main` 'e direkt push atamaz. Yanlışlıkla atmaya çalışan hata alır. Bu **iyi bir şey** . 

##### **9.4 Günlük çalışma: adım adım komutlar** 



<!-- Start of picture text -->
arkadasinceler andSquashmerge<br>main'i cek branch ac kodla + test push PRac Ci testieri<br>git pull featik1- commit (giinde =1) Closes #12 yesil mi?<br>we kirmizi + dizett,<br>meee lll _oue ee tekrar push<br><!-- End of picture text -->

_Şekil 9 — Bir işin başından main'e girişine kadar 8 adım._ 

**Sadece ilk sefer:** repoyu bilgisayarına indir. 

```
git clone https://github.com/KULLANICI/sanal-portfoy.git
cd sanal-portfoy
```

###### **Her yeni işe başlarken:** 

```
# 1) main'e geç ve en güncel hâlini çek
git checkout main
git pull origin main
# 2) yeni branch aç (isim kuralı aşağıda)
git checkout -b feat/k1-register-login
```

###### **Çalışırken (gün içinde birkaç kez):** 

```
git status                       # neler değişti?
git add backend/app/auth/        # değişen dosyaları ekle (git add . de olur ama önce status'e bak)
git commit -m "feat(auth): kayıt endpoint'i ve başlangıç bakiyesi"
git push -u origin feat/k1-register-login   # ilk push'ta -u, sonrakilerde sadece: git push
```

**Günde en az bir kez push at.** Bilgisayarın bozulsa bile kodun GitHub'da durur. 

###### **İş bitince:** 

1. GitHub'da repo sayfasına git. Sarı bir "Compare & pull request" butonu çıkar, bas. 

2. PR şablonunu doldur (Bölüm 17.5). Açıklamaya `Closes #12` yaz; 12 ilgili issue numarası. 

3. Sağ tarafta **Reviewers** kısmına inceleyecek kişiyi ekle (kim kimi inceler: Bölüm 9.7). 

4. CI'ın yeşil olmasını bekle. Kırmızıysa tıkla, hatayı oku, düzelt, tekrar push at. 

5. İnceleyen onaylayınca **Squash and merge** butonuna bas. Tüm commit'lerin tek bir commit olarak main'e girer; tarih temiz kalır. 

6. **Delete branch** butonuna bas. 

7. Kendi bilgisayarında: 

```
git checkout main
git pull origin main
git branch -d feat/k1-register-login
```

##### **9.5 İsim kuralları** 

**Branch adı:** `tür/kişi-kısa-açıklama` 

- `feat/k1-order-engine` → yeni özellik 

- `fix/k2-login-error-message` → hata düzeltme 

- `test/k3-portfolio-fixtures` → sadece test 

- `docs/k2-user-guide` → sadece belge 

- `chore/k1-ci-setup` → ayar, kurulum 

**Commit mesajı:** `tür(alan): ne yaptın` , kısa ve Türkçe olabilir. 

- `feat(orders): alış emrinde komisyon hesabı` 

CEN317 · 3 kişilik ekip · 4 hafta 

14 

Sanal Portföy · Proje Uygulama Rehberi 

- `fix(market): yeniden bağlanmada abonelik kaybı` 

- `test(portfolio): 6.2 örneğinin birim testi` 

"düzeltme", "asdf", "son hali", "son hali 2" gibi mesajlar **yasak** . Raporda commit geçmişini kanıt olarak göstereceğiz. 

##### **9.6 PR kuralları** 

- **Küçük PR:** mümkünse 400 satırı geçmesin. Büyük PR'ı kimse düzgün inceleyemez. 

- **Bir PR = bir iş:** "Login + grafik + bir de hata düzeltmesi" olmaz. 

- **İnceleme süresi:** PR açıldıktan sonra en geç **24 saat** içinde incelenir. İnceleyen müsait değilse ekipteki diğer kişi inceler. 

- **İnceleyen neye bakar?** 

   1. Kod çalışıyor mu? Branch'i kendi bilgisayarında açıp denemek en iyisi. 

   2. Test var mı? Hata durumları test edilmiş mi? 

   3. Anlamadığım bir yer var mı? Varsa yorum olarak sor. 

- **Yorumlar kibar ve somut olur:** "Bu yanlış" değil, "Bakiye 0 olursa burası hata veriyor gibi, bir bakar mısın?" 

##### **9.7 Kim kimin PR'ını inceler?** 



<!-- Start of picture text -->
K1iin PR'int K2'nin PRint<br>K2 inceler K3 inceler<br>K1<br>Hesap& Islem seK3'Un PR'ini<br>K1 inceler<br><!-- End of picture text -->

_Şekil 10 — Çapraz inceleme döngüsü._ 

- **K1** 'in PR'ını → **K2** inceler (K2, API'yi kullanacak kişi olduğu için). 

- **K2** 'nin PR'ını → **K3** inceler (fiyat ve kâr/zarar ekranda doğru mu görünüyor?). 

- **K3** 'ün PR'ını → **K1** inceler (hesap mantığı doğru mu?). 

Böylece herkes herkesin kodunu tanır. Biri hastalanırsa işi başkası devam ettirebilir. 

##### **9.8 Merge conflict (çakışma) olursa** 

Çakışma, iki kişinin aynı dosyanın aynı satırını değiştirmesi demek. Panik yok. 

```
# kendi branch'indeyken:
git fetch origin
git merge origin/main
# Git "CONFLICT in dosya.py" derse, dosyayı VS Code'da aç.
```

VS Code çakışan yerleri renkli gösterir ve üstünde şu butonlar çıkar: **Accept Current** (seninki), **Accept Incoming** (main'deki), **Accept Both** (ikisi). Doğru olanı seç. Emin değilsen dosyanın sahibine sor. 

```
git add dosya.py
git commit -m "merge: main ile çakışma çözüldü"
git push
```

Çakışmayı azaltmanın yolları: 

CEN317 · 3 kişilik ekip · 4 hafta 

15 

Sanal Portföy · Proje Uygulama Rehberi 

- Her gün `git merge origin/main` ile main'deki değişiklikleri kendi branch'ine al. 

- Kendi klasörün dışındaki dosyaya dokunacaksan önce ekip kanalına yaz. 

- Ortak dosyalar ( `main.py` , `docker-compose.yml` , `docs/api.md` ) değişecekse küçük, ayrı bir PR aç. 

##### **9.9 Asla repoya girmeyecekler** 

- `.env` dosyası (şifreler). `.env.example` girer, `.env` girmez. 

- `node_modules/` , `__pycache__/` , `.venv/` 

- Büyük veri dosyaları. Fixture'lar küçük tutulur (her biri 1 MB'tan az). 

`.gitignore` bunları otomatik engeller (Bölüm 17.1). Yanlışlıkla şifre push'lanırsa: şifreyi hemen değiştirin. Git geçmişinden silmek yetmez. 

## **10  CI/CD gerekli mi?** 

##### **Kısa cevap** 

- **CI (Continuous Integration): EVET, gerekli.** Kurulumu tek dosya, yaklaşık 1 saat. Bir kez kurulur, bir daha uğraşılmaz. 

- **CD (Continuous Deployment): HAYIR, gerekmez.** Demo kendi bilgisayarımızda Docker Compose ile yapılacak. 

##### **CI ne işe yarar?** 



<!-- Start of picture text -->
backend isi<br>PostgreSQL. (ee) ruff alembic pytest 7 yesiledilebilir> merge<br>main’ePR acildipush/ tsc a“. CED5<br><!-- End of picture text -->

_Şekil 11 — CI hattı: iki iş paralel çalışır, biri kırmızıysa merge engellenir._ 

Her PR açıldığında GitHub'ın bilgisayarı: 

1. Kodu indirir. 

2. Backend testlerini çalıştırır (gerçek bir PostgreSQL ile). 

3. Frontend'i derler ve testlerini çalıştırır. 

4. Hepsi geçerse ✓ yeşil, biri bile geçmezse ✗ kırmızı gösterir. 

**Kırmızı PR main'e giremez** (Bölüm 9.3). Böylece: 

- "Benim bilgisayarımda çalışıyordu" bahanesi biter. 

- Birinin değişikliği başkasının kodunu bozarsa hemen anlaşılır. 

- Raporda "her değişiklik otomatik test edildi" diyebilirsiniz. Hocalar bunu sever. 

##### **Çok mu komplike?** 

Hayır. Tüm CI dosyası Bölüm 17.4'te, hazır ve yaklaşık 60 satır. K1 ilk hafta repoya koyar, o kadar. 

**Tek kritik kural:** CI'daki testler **Binance'a bağlanmaz** . Kaydedilmiş veri (fixture) kullanır. Çünkü: 

- Binance yavaş cevap verirse ya da erişilemezse testler sebepsiz yere kırmızı olur. 

- Canlı fiyatla yazılan test her seferinde farklı sonuç verir. 

##### **CD neden gerekmiyor?** 

CD, her main değişikliğinde kodun otomatik olarak bir sunucuya yüklenmesi demek. Bunun için sunucu kiralamak, gizli anahtar yönetmek ve dağıtım betikleri yazmak gerekir. Hoca canlı bir link istemedikçe bu 4 haftada sadece zaman yer. 

CEN317 · 3 kişilik ekip · 4 hafta 

16 

Sanal Portföy · Proje Uygulama Rehberi 

Hoca link isterse 4. haftada **elle** bir kez bir sunucuya kurulur (Render, Railway, Azure gibi). Bunun için CD pipeline'ı kurmaya gerek yok. 

**Opsiyonel güzel ek:** `main` 'e her merge'de GitHub'da otomatik "release" oluşturmak. Gerekmez, vakit kalırsa yapılır. 

CEN317 · 3 kişilik ekip · 4 hafta 

17 

Sanal Portföy · Proje Uygulama Rehberi 

## **11  Hafta hafta yapılacaklar ve kabul koşulları** 

##### **Nasıl okunur?** 

- Her görevin: numarası, **ne yapılacağı** , **nasıl yapılacağına dair ipucu** ve **tahmini süresi** var. 

- **Kabul koşulları** = bu hafta biterken **kontrol edilecek maddeler** . Hepsi ✓ değilse iş bitmemiştir. 

- **Bağımlılık** = başlamak için başka birinin işini beklemen gereken yer. Beklerken ne yapacağın da yazıyor. 

CEN317 · 3 kişilik ekip · 4 hafta 

18 

Sanal Portföy · Proje Uygulama Rehberi 

#### **HAFTA 1 (G1–G7 · 5–11 Ekim)** 

"Giriş yapılıyor ve gerçek fiyatlar ekranda akıyor" 

###### **Ortak işler (üç kişi birlikte)** 

- ☐ **G1 · Başlangıç toplantısı (60 dk):** Bu belgeyi birlikte oku. İsimleri K1/K2/K3'e yaz. GitHub kullanıcı adlarını paylaş. İletişim kanalını seç (WhatsApp/Discord). Toplantı saatlerini sabitle. 

- ☐ **G2 · API sözleşmesi toplantısı (45 dk):** `docs/api.md` dosyasına tüm endpoint'ler, istek ve cevap örnekleri yazılır (başlangıç şablonu Bölüm 17.6'da). **Bu toplantıdan sonra API değişikliği sadece üç kişinin onayıyla olur.** 

   - Neden önemli: K2, backend hazır olmadan bu örnek cevaplarla ekranı yapmaya başlayabilir. Kimse kimseyi beklemez. 

- ☐ **G2 · Karar:** Binance erişim testi (K3.1) başarılı mı? Başarısızsa bu toplantıda B planı konuşulur (Bölüm 14). 

##### **K1 — Hesap ve İşlem (10 saat)** 

- ☐ **1.1 Repo ve iskelet (2 sa)** 

   - Bölüm 9.2 ve 9.3'teki repo kurulumu ve main koruması. 

   - Bölüm 7'deki klasörler; Bölüm 17'deki `.gitignore` , `.env.example` , `docker-compose.yml` , `Dockerfile` 'lar, PR şablonu. 

   - FastAPI'de boş bir `GET /health` endpoint'i → `{"status":"ok"}` döner. 

- ☐ **1.2 CI (1 sa)** 

   - `.github/workflows/ci.yml` (Bölüm 17.4). Boş bir test ( `def test_health(): ...` ) ile yeşil olduğunu gör. 

###### ☐ **1.3 Veritabanı ve ilk tablolar (2 sa)** 

   - SQLAlchemy 2 (async) + Alembic kurulumu. 

   - Migration: `users` , `accounts` , `cash_entries` . 

   - Para ve miktar sütunları `NUMERIC(28,8)` , **asla float değil** . Zaman sütunları `timestamptz` . 

   - Kısıt: `CHECK (cash >= 0)` , `email UNIQUE` . 

- ☐ **1.4 Kayıt ve giriş (3 sa)** 

   - `POST /auth/register` : e-posta ve şifre alır. Şifre **Argon2id** ile hashlenir ( `argon2-cffi` veya `passlib[argon2]` ). Aynı transaction içinde `accounts` satırı ve `cash_entries` 'e `+10000.00000000` , `kind='INITIAL'` yazılır. 

   - `POST /auth/login` : doğruysa **httpOnly, SameSite=Lax** çerez ile oturum verir; `Secure` bayrağı `.env` 'deki `COOKIE_SECURE` ile açılır (yerelde `false` , HTTPS'li sunucuda `true` ). Token localStorage'a **konmaz** . 

   - `POST /auth/logout` , `GET /me` (giriş yapılmamışsa 401). 

   - CORS: sadece `http://localhost:5173` , `allow_credentials=True` . 

###### ☐ **1.5 Testler (2 sa)** 

- Başarılı kayıt, aynı e-postayla ikinci kayıt (409), yanlış şifre (401), çerezsiz `/me` (401), kayıttan sonra bakiyenin 10000 olması. 

###### **✓ Kabul koşulları — K1 Hafta 1** 

- ☐ Temiz klonda `cp .env.example .env && docker compose up --build` ile 3 servis de ayağa kalkıyor. 

- ☐ Kayıt olan kullanıcının `accounts.cash` değeri tam `10000.00000000` ve `cash_entries` 'te tek bir `INITIAL` satırı var. 

- ☐ Şifre veritabanında düz metin değil, `$argon2id$...` ile başlıyor. 

- ☐ Aynı e-posta ikinci kez → 409. Yanlış şifre → 401. Oturumsuz `/me` → 401. 

- ☐ `main` 'e direkt push reddediliyor. CI bir PR'da yeşil oldu. 

CEN317 · 3 kişilik ekip · 4 hafta 

19 

Sanal Portföy · Proje Uygulama Rehberi 

##### **K2 — Arayüz (10 saat)** 

###### ☐ **2.1 React iskeleti (3 sa)** 

   - `npm create vite@latest frontend -- --template react-ts` 

   - React Router ile sayfalar: `/login` , `/register` , `/market` , `/portfolio` , `/history` . Girişsiz kullanıcı korumalı sayfalardan `/login` 'e yönlendirilir. 

   - Basit bir üst menü. CSS için Tailwind veya düz CSS; ekip hangisini biliyorsa. 

- ☐ **2.2 API istemcisi (1 sa)** 

   - `src/api/client.ts` : tüm istekler `credentials: "include"` ile gider (çerez için). 

   - **Para ve miktar değerleri string gelir** (örn. `"10000.00000000"` ). Ekranda gösterirken biçimlendir, **hesaplama yapma** . 

- ☐ **2.3 Giriş ve kayıt ekranları (2 sa)** 

   - Form, hata mesajı ("E-posta veya şifre hatalı"), yükleniyor durumu, başarılı girişte `/market` 'e yönlendirme. 

- ☐ **2.4 Piyasa listesi (2 sa)** 

   - Kolonlar: Coin, Alış (ask), Satış (bid), Spread, "x sn önce güncellendi". 

   - **Bağımlılık:** K3'ün gerçek SSE'si G5–G6'da gelir. O zamana kadar `docs/api.md` 'deki örnek veriyle (mock) çalış. 

- ☐ **2.5 Canlı bağlantı ve uyarılar (2 sa)** 

   - `useLiveStream` hook'u: `new EventSource("/api/stream", { withCredentials: true })` . `quote` ve `market_status` olaylarını dinler. 

   - Durum rozeti: ● Canlı / ● Kontrol ediliyor / ● Bağlantı yok. 

   - Her sayfanın üstünde sabit uyarı bandı: **"Sanal bakiye — gerçek para ve varlık yoktur — yatırım tavsiyesi değildir. Veri kaynağı: Binance."** 

###### **✓ Kabul koşulları — K2 Hafta 1** 

- ☐ Gerçek backend'e kayıt olup giriş yapılabiliyor. Sayfa yenilenince oturum düşmüyor. 

- ☐ Yanlış şifrede anlaşılır Türkçe hata mesajı çıkıyor. 

- ☐ G7'de piyasa listesi **gerçek** fiyatlarla, saniyede bir güncelleniyor. 

- ☐ Backend durdurulunca rozet ● oluyor, açılınca kendiliğinden ●'ye dönüyor. 

- ☐ Telefon görünümünde (375 px) tablo taşmıyor; gerekirse yatay kaydırılıyor. 

##### **K3 — Piyasa Verisi (10 saat)** 

- ☐ **3.1 Binance erişim testi — SPIKE (2 sa, G1–G2'de mutlaka biter)** 

   - Tek dosyalık bir Python betiği yaz: 

      - REST: `GET https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT` → cevap geliyor mu? 

      - WebSocket: 

`wss://data-stream.binance.vision/stream?streams=btcusdt@bookTicker/ethusdt@bookTicker` → 30 saniye mesaj geliyor mu? 

   - Bu adresler yalnızca piyasa verisi içindir. Çalışmazsa `api.binance.com` ve `stream.binance.com:9443` ile de dene. 

- Betiği **üç kişinin bilgisayarında ve demo yapılacak okul ağında** çalıştır. 

- Bir bookTicker mesajının tam içeriğini kaydet: hangi alanlar var, zaman alanı var mı? 

- Sonucu `docs/spike-binance.md` 'ye yaz. Binance API kullanım koşullarındaki veri gösterimi kısmını oku ve bir paragrafla özetle. 

###### ☐ **3.2 Semboller ve borsa kuralları (2 sa)** 

- Sembol listesi koda gömülmez, `.env` içindeki `SYMBOLS` 'tan okunur. 

CEN317 · 3 kişilik ekip · 4 hafta 

20 

Sanal Portföy · Proje Uygulama Rehberi 

- Açılışta `exchangeInfo` 'dan her sembol için fiyat adımı ( `tickSize` ), miktar adımı ( `stepSize` ) ve minimum tutar okunur, `assets` tablosuna yazılır. Migration'ı K1 ile koordineli yap. 

###### ☐ **3.3 Binance adaptörü ve fiyat hafızası (3 sa)** 

- Tek WebSocket bağlantısı, tüm semboller için birleşik (combined) stream. 

- Gelen mesaj ortak bir `Quote` nesnesine çevrilir: `symbol, bid, ask, bid_qty, ask_qty, received_at` . Sayılar `Decimal(str)` ile, **asla float ile değil** . `received_at` = bizim sunucunun mesajı aldığı UTC zaman. 

- Son fiyatlar bellekte bir sözlükte tutulur: `{symbol: Quote}` . 

- Adaptör bir arayüzün ( `MarketDataProvider` ) arkasında. İleride REPLAY ve başka borsa buraya takılacak. 

###### ☐ **3.4 Yeniden bağlanma ve yayın (2 sa)** 

   - Bağlantı koparsa 1, 2, 4, 8… en fazla 30 saniye bekleyerek (rastgele küçük gecikmeyle) tekrar bağlan. Ping/pong'u kütüphanenin otomatik yaptığını doğrula. 

   - `GET /markets` → tüm semboller, son fiyat ve durum. 

   - `GET /stream` (SSE) → saniyede bir `quote` olayı. 

- ☐ **3.5 Kayıt aracı (1 sa)** 

   - `scripts/record_quotes.py` : 10 dakika gerçek bookTicker mesajı toplayıp 

      - `tests/fixtures/quotes_*.jsonl` dosyasına yazar. Testler hep bu dosyayı kullanacak. 

###### **✓ Kabul koşulları — K3 Hafta 1** 

- ☐ `docs/spike-binance.md` G2'de repoda ve 3 bilgisayar + okul ağı sonucu yazılı. 

- ☐ Backend açılınca 5 sembolün fiyatı 5 saniye içinde `/markets` 'te görünüyor. 

- ☐ İnternet 20 saniye kesilip geri gelince sistem **kendiliğinden** yeniden bağlanıyor, elle yeniden başlatmak gerekmiyor. 

- ☐ `assets` tablosunda 5 satır ve her birinde adım/minimum değerleri var. 

- ☐ Repoda 1 MB'tan küçük en az bir fixture dosyası var. 

###### **✓ Hafta 1 Sprint Review'da (Pazar akşamı) gösterilecek** 

Yeni bir kullanıcı kayıt olur, giriş yapar, bakiyesini (10.000 USDT) görür, **gerçek ve canlı** fiyatları izler. İnternet kesilince rozet kırmızıya döner, geri gelince yeşile döner. 

CEN317 · 3 kişilik ekip · 4 hafta 

21 

Sanal Portföy · Proje Uygulama Rehberi 

#### **HAFTA 2 (G8–G14 · 12–18 Ekim)** 

"Alış ve satış gerçekten çalışıyor" 

###### **Ortak işler** 

- ☐ **Pazartesi Planning'de karar:** K1'in emir motoru, K3'ten fiyatı hangi fonksiyonla alacak? Önerilen arayüz: 

```
  # backend/app/market/guard.py  (K3 yazar, K1 kullanır)
  class QuoteStale(Exception): ...
  def get_tradeable_quote(symbol: str) -> Quote:
```

```
      """Taze ve bağlantısı sağlıklı fiyatı döner; değilse QuoteStale fırlatır."""
```

K3 gerçeğini yazana kadar K1 testlerde sahte (fake) bir versiyon kullanır. 

##### **K1 — Emir Motoru (10 saat)** 

- ☐ **1.6 Tablolar (1 sa):** `orders` , `trades` migration'ları. `UNIQUE(account_id, idempotency_key)` . `positions` tablosunu K3 ile birlikte tanımla (şema K3'ün, yazma K1'in transaction'ında). 

- ☐ **1.7** `execute_order` **servisi (3 sa)** — sistemin kalbi, adım adım: 

   1. Transaction başlat. 

   2. `SELECT ... FROM accounts WHERE id = :id FOR UPDATE` → hesap satırını kilitle. Aynı hesaba gelen ikinci istek bu işlem bitene kadar bekler. 

   3. Aynı `idempotency_key` ile daha önce işlem var mı? Varsa **eski sonucu aynen döndür** , yeni işlem yapma. 

   4. `get_tradeable_quote(symbol)` → fiyatı al. `QuoteStale` gelirse 409 dön. 

   5. Kontroller (aşağıda 1.8). 

   6. `orders` + `trades` + `cash_entries` + `positions` yaz; `accounts.cash` 'i güncelle. 

   7. Commit. Herhangi bir hata olursa rollback olur ve hiçbir şey yazılmaz. 

- ☐ **1.8 Fiyat, komisyon ve kurallar (3 sa)** 

   - Alış fiyatı = **ask** . Satış fiyatı = **bid** . 

   - Komisyon = tutar × `FEE_RATE` (.env'den, varsayılan 0.001). 

   - Alışta: nakit azalışı = miktar × ask + komisyon. Satışta: nakit artışı = miktar × bid − komisyon. 

   - Miktar, `stepSize` 'a **aşağı** yuvarlanır. Tutar minimumun altındaysa reddedilir. 

   - Miktar, o anki en iyi kademedeki miktardan ( `ask_qty` / `bid_qty` ) büyükse reddedilir. 

   - Hata kodları: `INSUFFICIENT_FUNDS` , `INSUFFICIENT_POSITION` , `FILTER_VIOLATION` , `DEPTH_EXCEEDED` (hepsi 422), `QUOTE_STALE` (409). 

   - `trades` satırına **o anki bid, ask ve** `received_at` **de yazılır** . Her işlem hangi fiyatla yapıldığının kanıtını taşır. 

- ☐ **1.9 Endpoint ve testler (3 sa)** 

   - `POST /orders` (header'da `Idempotency-Key` zorunlu), `GET /trades?cursor=...` . 

   - Testler: başarılı alış, başarılı satış, her hata kodu, **aynı anahtarla iki istek → tek işlem** , reddedilen emirde veritabanının hiç değişmemesi. 

   - Rapordaki çalışılmış örneğin (bkz. Hafta 2 K3 kabul koşulları) nakit kısmı birebir test edilir. 

###### **✓ Kabul koşulları — K1 Hafta 2** 

- ☐ 0,01 BTC alışta bakiye tam olarak `0,01 × ask × 1,001` kadar azalıyor (Decimal, kuruşu kuruşuna). 

- ☐ Yetersiz bakiyede 422 dönüyor ve `orders` , `trades` , `cash_entries` tablolarında **yeni satır yok** . 

- ☐ Aynı `Idempotency-Key` ile iki kez istek → sadece **bir** işlem kaydı, iki cevap birebir aynı. 

- ☐ Elinde olmayan coini satmak → 422 `INSUFFICIENT_POSITION` . 

- ☐ Her `trades` satırında bid, ask ve fiyatın alınma zamanı dolu. 

CEN317 · 3 kişilik ekip · 4 hafta 

22 

Sanal Portföy · Proje Uygulama Rehberi 

##### **K2 — Emir Ekranları (10 saat)** 

###### ☐ **2.6 Emir formu (4 sa)** 

   - AL / SAT sekmesi, coin seçimi, miktar girişi. 

   - **Önizleme:** "Yaklaşık fiyat: X · Komisyon: Y · Toplam: Z · Kalan bakiye: W". Bu sadece tahmindir, kesin sonuç sunucudan gelir. Önizleme hesabında `decimal.js` kullan, JavaScript `number` ile para hesabı yapma. 

   - Girilen miktar adım büyüklüğüne yuvarlanıyorsa kullanıcıya göster: "0,0123456 → 0,01234 olarak işlenecek". 

   - "Şu an en iyi fiyattan en fazla X alınabilir" bilgisi. 

- ☐ **2.7 Gönderim ve sonuç (3 sa)** 

   - Her form açılışında `crypto.randomUUID()` ile yeni bir `Idempotency-Key` üret. Aynı gönderimde tekrar denemede **aynı** anahtar kullanılır. 

   - Butona basınca buton kilitlenir (çift tıklama engeli). 

   - Başarıda: "0,01 BTC 100.010 USDT'den alındı. Komisyon: 1,0001 USDT." 

   - Hata kodlarının her biri için anlaşılır Türkçe mesaj. Örnek: `DEPTH_EXCEEDED` → "Bu miktar şu an piyasada mevcut değil, daha küçük bir miktar deneyin." 

   - Bağlantı ● ise emir butonu kapalı ve üstünde nedeni yazıyor. 

- ☐ **2.8 İşlem geçmişi (3 sa)** 

   - Tablo: Tarih (Türkiye saatiyle), Coin, Yön, Miktar, Fiyat, Komisyon, Toplam. 

   - Sayfalama ("Daha fazla yükle"). 

###### **✓ Kabul koşulları — K2 Hafta 2** 

- ☐ Önizlemedeki toplam ile sunucunun döndüğü toplam arasındaki fark, sadece o arada fiyat değişmesinden kaynaklanıyor. Aynı fiyatta birebir eşit. 

- ☐ Butona hızlı hızlı 5 kez basınca sadece **bir** işlem oluşuyor. 

- ☐ Her hata kodu için ayrı ve anlaşılır bir mesaj çıkıyor. 

- ☐ İşlem geçmişi yeni işlemden sonra sayfayı yenilemeden güncelleniyor. 

##### **K3 — Fiyat Güvenliği ve Portföy Hesabı (10 saat)** 

- ☐ **3.6 QuoteGuard (4 sa)** 

   - Bölüm 5.4'teki durum makinesini kod olarak yaz. 

   - Her sembol için "son fiyat ne zaman geldi?" tutulur. Belirli bir süre (örnek başlangıç: **5 sn** ; ölçerek ayarlayın) mesaj gelmezse önce REST ile taze fiyat istenir. Gelmezse sembol "işleme kapalı" olur. 

   - **Dikkat:** Sakin piyasada mesaj gelmemesi bağlantının koptuğu anlamına gelmez. Bağlantı sağlığı ve sembol tazeliği ayrı ayrı takip edilir. 

   - `get_tradeable_quote()` fonksiyonu burada. Durum değişince SSE ile `market_status` olayı gönderilir. 

- ☐ **3.7 Portföy hesabı (4 sa)** 

   - `backend/app/money.py` : tüm yuvarlama tek fonksiyonda (8 ondalık, `ROUND_HALF_EVEN` ). 

   - **Ağırlıklı ortalama maliyet:** alış komisyonu maliyete eklenir. 

   - Satışta: satılan kısmın maliyeti = kalan maliyet × (satılan miktar / eldeki miktar). 

   - Gerçekleşmiş kâr/zarar = net satış geliri − satılan kısmın maliyeti. 

   - Gerçekleşmemiş kâr/zarar = eldeki miktar × **bid** − kalan maliyet (satış komisyonu hariç; ekranda yazılır). 

   - Toplam portföy = nakit + tüm coinlerin eldeki miktar × bid değeri. 

   - `GET /portfolio` . 

- ☐ **3.8 Canlı portföy (1 sa)** 

   - Her saniye, bağlı her kullanıcı için portföy hesaplanır ve SSE `portfolio_updated` olayı gönderilir. 

CEN317 · 3 kişilik ekip · 4 hafta 

23 

Sanal Portföy · Proje Uygulama Rehberi 

   - K1'in emir motoru işlem bitince bir olay tetikler → o kullanıcıya **beklemeden** gönderilir. 

- ☐ **3.9 Testler (1 sa)** 

   - Fixture ve sahte saat ( `Clock` arayüzü) ile. Bu testler internetsiz çalışmalı. 

###### **✓ Kabul koşulları — K3 Hafta 2** 

- ☐ Şu çalışılmış örnek **birebir** birim testinde geçiyor (başlangıç 10.000 USDT, komisyon %0,1): 

- `1) 0,05 BTC al @ ask 100.010 → nakit 4.994,4995      maliyet 5.005,5005` 

- `2) 0,03 BTC al @ ask 102.010 → nakit 1.931,1392      maliyet 8.068,8608  (0,08 BTC)` 

- `3) 0,04 BTC sat @ bid 103.000 → nakit 6.047,0192     gerçekleşmiş K/Z +81,4496 4) Değerleme @ bid 101.500    → gerçekleşmemiş +25,5696   toplam 10.107,0192 Kontrol: 81,4496 + 25,5696 = 107,0192 = 10.107,0192 − 10.000  ✓` 

- ☐ Binance bağlantısı kesilince eşik süresi içinde emirler 409 dönmeye başlıyor. Bağlantı gelince, fiyat doğrulandıktan sonra açılıyor. 

- ☐ Testler internet kapalıyken de geçiyor. 

###### **✓ Hafta 2 Sprint Review'da gösterilecek** 

Kullanıcı 0,01 BTC alır. Fiyat değiştikçe gerçekleşmemiş kâr/zararın saniyede bir değiştiği görülür. Sonra satar ve gerçekleşmiş kâr/zarar oluşur. Yetersiz bakiye hatası da gösterilir. 

CEN317 · 3 kişilik ekip · 4 hafta 

24 

Sanal Portföy · Proje Uygulama Rehberi 

#### **HAFTA 3 (G15–G21 · 19–25 Ekim)** 

"Sağlam, eksiksiz ve kesintiye dayanıklı" 

###### **⚠ G21 (25 Ekim Pazar) akşamından sonra YENİ ÖZELLİK EKLENMEZ.** Sadece hata düzeltilir. 

##### **K1 — Güvenlik ve Tutarlılık (10 saat)** 

- ☐ **1.10 Eşzamanlılık testi (3 sa)** 

   - Bakiyesi sadece 3 alışa yeten bir hesapla **aynı anda 50 alış isteği** gönder ( `asyncio.gather` ile, farklı idempotency anahtarları). 

   - Beklenen: tam 3 başarılı, 47 `INSUFFICIENT_FUNDS` ; bakiye asla negatif değil. 

- ☐ **1.11 Güvenlik (3 sa)** 

   - **İstek sınırlama:** girişte dakikada 5, emirde saniyede 5 istek (örneğin `slowapi` ). 

   - **CSRF koruması:** durum değiştiren isteklerde (POST) kontrol. 

   - **Başkasının hesabı testi:** A kullanıcısı B'nin işlem numarasıyla istek atarsa 404 alır. Hesap kimliği her zaman oturumdan alınır, istekten asla. 

###### ☐ **1.12 Mutabakat ve destek (4 sa)** 

- `python -m app.reconcile` komutu: her hesap için `accounts.cash == SUM(cash_entries.amount)` ve pozisyonların işlemlerle tutarlılığı. Tutarsızlık varsa ekrana basar ve hata koduyla çıkar. 

- Kalan süre: backlog'daki hatalar ve K3'e destek (yedek süre). 

###### **✓ Kabul koşulları — K1 Hafta 3** 

- ☐ 50 paralel istek testi 10 kez üst üste çalıştırıldığında her seferinde geçiyor. 

- ☐ Giriş denemesi sınırı aşılınca 429 dönüyor. 

- ☐ Başka kullanıcının verisine erişim testleri geçiyor. 

- ☐ Hafta 2–3 boyunca yapılan tüm testlerden sonra mutabakat komutu "0 tutarsızlık" diyor. 

##### **K2 — Portföy Ekranı ve Uçtan Uca Testler (10 saat)** 

- ☐ **2.9 Portföy ve grafikler (5 sa)** 

   - Portföy ekranı: nakit, toplam değer, toplam kâr/zarar (yeşil/kırmızı), pozisyon listesi (coin, miktar, ortalama maliyet, güncel değer, kâr/zarar ve yüzdesi). 

   - Coin dağılımı (pasta grafiği). 

   - Mum grafiği: **TradingView Lightweight Charts** kütüphanesi; K3'ün `GET /markets/{sym}/candles` endpoint'i. Lisansı gereği sayfada küçük bir atıf olur. 

   - Portföy değeri çizgi grafiği: K3'ün `GET /portfolio/history` endpoint'i. 

   - **Bağımlılık:** K3'ün 3.10 ve 3.11 işleri. Beklerken önce ekran düzenini örnek veriyle yap. 

- ☐ **2.10 Kesinti deneyimi (2 sa)** 

   - Bağlantı ● veya sembol "işleme kapalı" ise ilgili satırda ve emir formunda açıklama. 

   - REPLAY modunda tüm ekranlarda sabit turuncu bant: **"REPLAY — kayıtlı veri, canlı değil."** 

- ☐ **2.11 Playwright testleri (3 sa)** 

   - Akış 1: kayıt → giriş → BTC al → portföyde görün → sat → geçmişte görün. 

   - Akış 2: yetersiz bakiyeyle alış → hata mesajı. 

   - Akış 3: backend REPLAY modunda başlatılır → kesinti simüle edilir → emir butonu kilitlenir. 

CEN317 · 3 kişilik ekip · 4 hafta 

25 

Sanal Portföy · Proje Uygulama Rehberi 

###### **✓ Kabul koşulları — K2 Hafta 3** 

- ☐ Portföy ekranındaki değerler `GET /portfolio` cevabıyla birebir aynı (ekranda hesaplama yok). 

- ☐ 3 Playwright akışı yerel makinede yeşil. 

- ☐ Tüm sayfalar telefon görünümünde kullanılabilir. 

##### **K3 — Geçmiş Veri ve Dayanıklılık (10 saat)** 

###### ☐ **3.10 Mum geçmişi (3 sa)** 

- Açılışta her sembol için REST `klines` ile son 300 adet 1 dakikalık mum çekilir ve `candles_1m` 'e yazılır. 

- Sonrasında WebSocket `kline_1m` akışından **kapanmış** mumlar eklenir. 

- `GET /markets/{symbol}/candles?limit=300` 

###### ☐ **3.11 Portföy anlık görüntüleri (2 sa)** 

- Dakikada bir, her hesap için toplam değer `portfolio_snapshots` 'a yazılır. 

- `GET /portfolio/history?range=1d` 

###### ☐ **3.12 Kesinti testleri ve REPLAY (3 sa)** 

- `ReplayProvider` : fixture dosyasındaki gerçek kayıtları sırayla oynatır. `.env` 'de `MARKET_SOURCE=replay` ile açılır. 

- REPLAY'de yapılan işlemler `source='replay'` olarak işaretlenir. 

- Test: `docker network disconnect` ile backend'in internetini kes → emirler kapansın → bağla → doğrulamadan sonra açılsın. 

###### ☐ **3.13 Opsiyonel (2 sa, sadece her şey yolundaysa)** 

- TRX, DOGE, ADA eklemek ( `.env` 'de `SYMBOLS` değişikliği + test), **veya** 

- Binance'a alternatif ikinci bir borsa adaptörü. 

###### **✓ Kabul koşulları — K3 Hafta 3** 

- ☐ Sayfa yenilenince mum grafiği son 300 dakikayla dolu geliyor. 

- ☐ Portföy değeri grafiğinde en az son 1 saatin noktaları var. 

- ☐ İnternet kesme testi geçiyor ve sonuçları (kaç saniyede kapandı, kaç saniyede açıldı) kayıtlı. 

- ☐ `MARKET_SOURCE=replay` ile sistem internetsiz çalışıyor ve ekranda REPLAY bandı görünüyor. 

###### **✓ Hafta 3 Sprint Review'da gösterilecek** 

Tam ürün: grafikler, portföy, geçmiş. Canlı demoda internet kesilir ve sistemin tepkisi gösterilir. 50 paralel istek testinin çıktısı da gösterilir. 

CEN317 · 3 kişilik ekip · 4 hafta 

26 

Sanal Portföy · Proje Uygulama Rehberi 

#### **HAFTA 4 (G22–G28 · 26 Ekim–1 Kasım)** 

"Teslime hazır" 

**Bu hafta yeni özellik YOK.** 28 Ekim yarım gün, 29 Ekim tatil. Teslim adayı **28 Ekim sabahına** kadar hazır olur. 

##### **K1 — Kurulum ve Teknik Belge (10 saat)** 

- ☐ **1.13 Temiz kurulum (4 sa)** 

   - Hiç kurulum yapılmamış bir bilgisayarda (veya ekip dışından bir arkadaşın bilgisayarında) README'yi adım adım takip et. Takıldığın her yeri README'ye yaz. 

   - README'de olacaklar: gereksinimler, kurulum komutları, test çalıştırma, REPLAY modu, sık hatalar. 

- ☐ **1.14 Hata avı ve güvenlik kontrolü (4 sa)** 

   - `.env` repoda yok mu? Şifreler hashli mi? CORS doğru mu? Hata mesajlarında iç detay (stack trace) sızıyor mu? 

   - Açık hataların hepsi kapatılır ya da "bilinen sınırlama" olarak rapora yazılır. 

- ☐ **1.15 Rapor bölümleri (2 sa)** → `docs/rapor/` : veri modeli, transaction ve tutarlılık yaklaşımı, güvenlik önlemleri. 

- **✓ Kabul koşulları — K1 Hafta 4** 

- ☐ Ekip dışı biri README ile 15 dakikada sistemi çalıştırabildi. 

- ☐ Kritik veya büyük açık hata yok. 

##### **K2 — Kullanılabilirlik ve Demo (10 saat)** 

- ☐ **2.12 Kullanılabilirlik testi (4 sa)** 

   - Ekip dışından 3 kişiye görev ver: "Kayıt ol, 100 USDT'lik ETH al, kâr/zararını bul." Konuşmadan izle ve takıldıkları yeri not et. 

   - Bulunan sorunları listele, kritik olanları düzelt. Liste rapora girer. 

- ☐ **2.13 Demo ve kılavuz (4 sa)** 

   - 7–8 dakikalık demo senaryosu (kim ne gösterecek, dakika dakika). 

   - Kullanıcı kılavuzu (ekran görüntüleriyle, 2–3 sayfa). 

   - B planı: demo sırasında internet giderse REPLAY'e geçiş adımları. 

- ☐ **2.14 Rapor birleştirme (2 sa)** → herkesin bölümlerini tek biçime getir, kaynakçayı tek listede topla, şekil numaralarını düzelt. 

- **✓ Kabul koşulları — K2 Hafta 4** 

- ☐ Demo provası (G27) süresi 8 dakikayı geçmiyor. 

- ☐ Rapor tek dosyada, tutarlı biçimde; her bölümün yazarı belli. 

##### **K3 — Doğruluk Kanıtları (10 saat)** 

- ☐ **3.14 Doğruluk tablosu (3 sa)** 

   - 10 farklı senaryo (tek alış, çoklu alış, kısmi satış, tam satış, zararla satış…). Her biri için **elle hesap** (Excel) ile **sistemin sonucu** yan yana. Hepsi eşleşmeli. 

- ☐ **3.15 Bağlantı ve gecikme raporu (3 sa)** 

   - 10 dakika boyunca: Binance'tan mesajın geliş anı ile ekrana gönderilme anı arasındaki süre ölçülür (log ile). Ortalama ve en kötü değer grafikle verilir. 

   - Kesinti testinin sonuçları. 

- ☐ **3.16 Rapor ve hata düzeltme (4 sa)** → veri kaynağı seçimi (neden Binance?), gerçekleşme modeli ve varsayımları ("piyasa etkisi yok, tek kademe"), ölçüm sonuçları. 

CEN317 · 3 kişilik ekip · 4 hafta 

27 

Sanal Portföy · Proje Uygulama Rehberi 

###### **✓ Kabul koşulları — K3 Hafta 4** 

- ☐ 10 senaryonun 10'u kuruşu kuruşuna eşleşiyor. 

- ☐ Gecikme ölçümü grafiği rapora eklendi. 

###### **Ortak — kapanış** 

- ☐ **G24 (28 Ekim sabahı):** Teslim adayı. `main` donduruldu. 

- ☐ **G27 (31 Ekim):** Üç kişi birlikte tam demo provası. Herkes kendi kısmını anlatıyor. 

- ☐ **G28 (1 Kasım):** GitHub'da `v1.0.0` etiketi ve Release oluşturulur. Rapor, kod linki, test kanıtları ve kurulum belgesi teslim edilir. 

```
git checkout main && git pull
git tag -a v1.0.0 -m "Teslim sürümü"
git push origin v1.0.0
```

## **12  Toplantılar** 



<!-- Start of picture text -->
Sprint Planning| Daily - can Daily + yazil Daily - canli Daily + yazilt Review<br>35 dk 10 dk 3 satir 10 dk 3 satir 30 dk<br>feknik gérisme Retrospektif<br>15 dk 20 dk<br><!-- End of picture text -->

_Şekil 12 — Haftalık toplantı ritmi._ 

|**Gün**|**Toplantı**|**Süre**|**Ne olur?**|
|---|---|---|---|
|Pazartesi|**Sprint Planning**|35 dk|Haftanın hedefi; issue'lar sahiplere atanır|
|Salı|**Daily (canlı)**|10 dk|Herkes: dün ne yaptım, bugün ne yapacağım, engelim var<br>mı?|
|Çarşamba|**Daily (yazılı)**+**Teknik**<br>**görüşme**|15 dk|Yazılı: kanala 3 satır. Teknik: API/şema değişiklikleri|
|Perşembe|**Daily (canlı)**|10 dk|Aynı 3 soru|
|Cuma|**Daily (yazılı)**|—|Kanala 3 satır|
|Pazar|**Review + Retrospektif**|30 + 20|Çalışan ürün gösterilir; "gelecek hafta neyi daha iyi yaparız?"|
|akşamı||dk|sorusuna**tek**somut cevap|



###### Yazılı daily örneği: 

```
K3 · Çarşamba
Dün: QuoteGuard durum makinesi bitti, PR #14 açık
Bugün: REST doğrulaması
Engel: K1'in 1.7 PR'ını bekliyorum, fake ile devam ediyorum
```

###### **Kurallar:** 

- Daily'de hata ayıklama yapılmaz. "Konuşalım" denir, toplantıdan sonra ilgili iki kişi devam eder. 

- **1 günden uzun süren engel** ekibin ortak sorunudur ve hemen konuşulur. 

- API, veritabanı veya mimari kararları `docs/adr/0001-karar-adi.md` dosyalarına yazılır. Yarım sayfa yeterli: "Ne karar verdik, neden, alternatifler neydi?" Bunlar raporda kanıt olur. 

CEN317 · 3 kişilik ekip · 4 hafta 

28 

Sanal Portföy · Proje Uygulama Rehberi 

## **13  "Bitti" ne demek? (Definition of Done)** 

Bir iş **ancak şunların hepsi doğruysa** "Bitti" kolonuna taşınır: 

- ☐ Kabul koşulları sağlanıyor. 

- ☐ Hem başarılı hem hatalı durumlar için test yazıldı. 

- ☐ CI yeşil. 

- ☐ Bir ekip arkadaşı inceledi ve onayladı. 

- ☐ `main` 'e birleşti ve `docker compose up` ile ortak ortamda çalışıyor. 

- ☐ API veya veritabanı değiştiyse `docs/api.md` , migration ve gerekiyorsa ADR güncellendi. 

- ☐ Pazar Review'ında gösterilebilir durumda. 

"Kodu yazdım ama test etmedim" = **bitmedi.** "Benim bilgisayarımda çalışıyor ama PR açmadım" = **bitmedi.** 

## **14  Bir şey ters giderse ne yapılır?** 

**Binance'a erişilemiyor (G2 testi başarısız).** Hemen toplantı. Seçenekler: (1) diğer Binance adreslerini dene, (2) başka bir borsanın açık veri API'sini kullan (adaptör yapısı buna hazır), (3) son çare olarak hocayla konuş. Ders tanımı rastgele fiyat algoritmasına da izin veriyor; bu durumda REPLAY + açıkça etiketlenmiş simülasyon kullanılır. 

**Demo günü internet gitti.** `.env` 'de `MARKET_SOURCE=replay` yapıp yeniden başlat. Ekranda REPLAY bandı çıkar; hocaya dürüstçe "canlı veri yok, kayıtlı gerçek veriyle gösteriyoruz" denir. Telefon hotspot'u da yedek. 

**Biri geride kaldı (sınav, hastalık).** Daily'de söylesin, saklamasın. İnceleyen kişi o kodu zaten tanıyor; işi o devralır ya da destek olur. Bölüm 11'deki opsiyonel işler kapsamdan çıkarılır. 

###### **Süre yetmiyor. Kapsamdan çıkarma sırası:** 

1. Opsiyonel işler (fazladan coin, ikinci borsa) 

2. Coin dağılımı pasta grafiği 

3. Portföy değeri grafiği 

4. Coin sayısı 5'ten 3'e 

**Asla çıkarılmayanlar:** işlem doğruluğu, güvenlik, kesintide emir kapatma, testler, kurulum belgesi. **Merge conflict'i çözemedim.** Bölüm 9.8'i uygula. Olmazsa dosyanın sahibiyle 10 dakikalık bir görüntülü görüşme yap. `git push --force` **asla** kullanma. 

**İki kişi bir konuda anlaşamıyor.** PO (K2) karar verir ve karar ADR'ye yazılır. Teknik bir konuysa o modülün sahibi karar verir. 

CEN317 · 3 kişilik ekip · 4 hafta 

29 

Sanal Portföy · Proje Uygulama Rehberi 

## **15  Yapma listesi** 

- ✗ `main` 'e direkt push. (Zaten engelli.) 

- ✗ Para hesabında `float` veya JavaScript `number` kullanmak. Her zaman `Decimal` / `NUMERIC` / string. 

- ✗ Frontend'de kâr/zarar hesaplamak. Hesap backend'in işidir; frontend gösterir. 

- ✗ Binance bağlantısı koptuğunda rastgele fiyat uydurmak. 

- ✗ `.env` dosyasını veya şifreleri repoya koymak. 

- ✗ Testlerde canlı Binance'a bağlanmak. 

- ✗ Uvicorn'u `--workers 2` veya fazlasıyla çalıştırmak. Her işçi ayrı fiyat görür; biz **tek işçi** kullanıyoruz. 

- ✗ 1.000 satırlık dev PR açmak. 

- ✗ "Son gün hallederiz." Her hafta sonunda çalışan bir ürün olmalı. 

- ✗ Yapılmamış işi raporda yapılmış gibi göstermek. 

## **16  Teslim günü kontrol listesi** 

- ☐ `main` CI'da yeşil. 

- ☐ `v1.0.0` etiketi ve GitHub Release oluşturuldu. 

- ☐ README ile temiz kurulum ekip dışı biriyle test edildi. 

- ☐ Mutabakat komutu 0 tutarsızlık veriyor. 

- ☐ Doğruluk tablosu (10 senaryo) rapora eklendi. 

- ☐ Gecikme ve kesinti ölçümleri rapora eklendi. 

- ☐ Kullanılabilirlik testi bulguları rapora eklendi. 

- ☐ `docs/saatler.md` dolu (herkesin haftalık saatleri). 

- ☐ Raporda herkesin yazdığı bölümler belli. 

- ☐ Demo senaryosu ve REPLAY B planı hazır. 

- ☐ Sunum bilgisayarında Docker açık, sistem bir kez çalıştırılıp denendi. 

CEN317 · 3 kişilik ekip · 4 hafta 

30 

