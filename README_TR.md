# 🛡️ ScrapeGuard — Otomatik Yapısal Bütünlük Gözlemcisi

> Hedef URL'leri periyodik olarak tarayan, çekilen verileri dinamik Pydantic şemalarına karşı doğrulayan ve yapısal değişiklikleri gerçek zamanlı Streamlit panosu üzerinden raporlayan, üretime hazır bir Python gözlemci sistemi.

---

## 📋 İçindekiler

1. [Özet](#-özet)
2. [Kullanılan Teknolojiler](#-kullanılan-teknolojiler)
3. [Mimari Yapı](#-mimari-yapı)
4. [Metodoloji ve Mekanikler](#-metodoloji-ve-mekanikler)
5. [Kurulum Adımları](#-kurulum-adımları)
6. [Lisans](#-lisans)

---

## 🎯 Özet

**ScrapeGuard**, web veri hatları için tasarlanmış bir yapısal bütünlük izleme aracıdır. Yapılandırılmış hedef URL'leri sürekli izler ve bir web sitesinin DOM yapısının, veri çekme mantığınızı bozacak şekilde değişip değişmediğini tespit eder.

**Temel Özellikler:**
- 🔄 **Otomatik Zamanlama** — Her hedef için ayrı yapılandırılabilir tarama aralıkları
- 🛡️ **Dinamik Şema Doğrulama** — JSON konfigürasyonundan çalışma zamanında üretilen Pydantic modelleri
- 🎨 **Gerçek Zamanlı Panel** — Hedef sağlığını bir bakışta gösteren premium Streamlit arayüzü
- 📊 **Yapılandırılmış Loglama** — Rotasyon ve saklama politikasıyla Loguru (disk şişmesi yok)
- 🕶️ **Anti-Ban Önlemleri** — Dinamik bekleme, User-Agent rotasyonu, geri çekilmeli yeniden deneme
- 🧪 **Tam Test Kapsamı** — Sahte HTTP yanıtlarıyla pytest test paketi

---

## 🛠️ Kullanılan Teknolojiler

| Teknoloji | Sürüm | Amaç |
|---|---|---|
| **Python** | 3.11+ | Çekirdek çalışma ortamı |
| **Requests** | 2.31+ | HTTP istemcisi |
| **BeautifulSoup4** | 4.12+ | HTML ayrıştırma ve CSS seçici çıkarımı |
| **lxml** | 5.1+ | Hızlı HTML ayrıştırıcı arka ucu |
| **Pydantic** | 2.5+ | Dinamik veri doğrulama ve tip kontrolü |
| **Loguru** | 0.7+ | Rotasyonlu yapılandırılmış loglama |
| **Streamlit** | 1.30+ | Etkileşimli web panosu |
| **Schedule** | 1.2+ | Hafif görev zamanlayıcı |
| **pytest** | 8.0+ | Test çerçevesi |
| **responses** | 0.25+ | Testler için HTTP yanıt simülasyonu |

---

## 🏗️ Mimari Yapı

```
ScrapeGuard/
├── config/
│   ├── targets.json          # Hedef URL'ler, CSS seçiciler, tip kuralları
│   └── settings.py           # Genel yapılandırma sabitleri
├── src/
│   ├── core/
│   │   ├── scraper.py        # HTTP çekme + CSS çıkarım motoru
│   │   ├── validator.py      # Pydantic doğrulama kontrol noktası
│   │   └── logger.py         # Loguru rotasyon/saklama kurulumu
│   ├── schemas/
│   │   └── base.py           # Dinamik Pydantic model fabrikası
│   ├── app.py                # Streamlit panosu (salt okunur görüntüleyici)
│   └── main_engine.py        # Arka plan orkestratörü / zamanlayıcı
├── tests/
│   ├── test_scraper.py       # Scraper birim testleri
│   └── test_validator.py     # Doğrulayıcı birim testleri
├── logs/                     # Otomatik oluşturulur, git-ignored
├── .gitignore
├── requirements.txt
├── README.md                 # İngilizce dokümantasyon
└── README_TR.md              # Bu dosya
```

### Sorumluluk Ayrımı

| Bileşen | Sorumluluk |
|---|---|
| `main_engine.py` | Bağımsız zamanlayıcı — arka planda tarama döngülerini çalıştırır |
| `app.py` | Salt görüntüleyici — diskten JSON sonuçlarını ve log dosyalarını okur |
| `validator.py` | Scraper çıktısı ↔ dinamik Pydantic modelleri arasında köprü |
| `base.py` | `targets.json`'dan çalışma zamanında Pydantic modelleri üreten fabrika |

---

## ⚙️ Metodoloji ve Mekanikler

### 1. Dinamik Şema Üretimi
`targets.json` içindeki hedef tanımları, beklenen tiplerle birlikte CSS seçicileri belirtir. Çalışma zamanında `base.py`, `pydantic.create_model()` kullanarak tipli modelleri dinamik olarak oluşturur.

### 2. Anti-Ban Tarama
- **Dinamik gecikmeler**: İstekler arasında `time.sleep(random.uniform(2, 5))`
- **User-Agent rotasyonu**: Her istekte rastgele seçilen 6 tarayıcı benzeri UA
- **Üstel geri çekilme**: Geçici hatalarda artan gecikmelerle yeniden deneme
- **Zarif hata yönetimi**: Timeout, ConnectionError ve HTTP hataları yakalanır — scraper asla çökmez

### 3. Doğrulama Hattı
```
Scraper → Ham Dict → Tip Dönüşümü → Dinamik Pydantic Model → Sonuç
                                                                ├── ✅ SAĞLIKLI
                                                                ├── ❌ ŞEMA BOZUK
                                                                └── ⚠️ BAĞLANTI HATASI
```

### 4. Ayrık Mimari
Motor (`main_engine.py`) sonuçları `latest_results.json` dosyasına yazar. Panel (`app.py`) yalnızca bu dosyayı okur. Bu, arayüzün ağ G/Ç işlemlerinde asla bloklanmamasını sağlar.

### 5. Log Yönetimi
Loguru, **10 MB rotasyon** ve **7 gün saklama** ile yapılandırılmıştır. Eski loglar `.zip` olarak sıkıştırılır. `enqueue=True` ile iş parçacığı güvenliği sağlanır.

---

## 🚀 Kurulum Adımları

### Ön Koşullar
- Python 3.11 veya üzeri
- pip paket yöneticisi

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/yourusername/ScrapeGuard.git
cd ScrapeGuard
```

### 2. Sanal Ortam Oluşturun
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Hedefleri Yapılandırın
`config/targets.json` dosyasını düzenleyerek hedef URL'lerinizi ve CSS seçicilerinizi ekleyin.

### 5. Motoru Çalıştırın (Arka Plan)
```bash
python -m src.main_engine
```

### 6. Panoyu Başlatın
```bash
streamlit run src/app.py
```

### 7. Testleri Çalıştırın
```bash
pytest tests/ -v
```

---

## 📄 Lisans

Bu proje **MIT Lisansı** altında lisanslanmıştır.

```
MIT License

Copyright (c) 2026 ScrapeGuard

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
