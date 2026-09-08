# Akakçe Samsung 990 EVO Plus Fiyat Takip & Alarm Sistemi

Bu uygulama, **Akakçe** üzerinden **Samsung 990 EVO Plus** (1TB, 2TB ve diğer modeller) için:
1. **Düzenli Fiyat Takibi (Otomatik / Zamanlanmış Görev):** Her gün saat 10:00'da en düşük liste fiyatını ve satıcısını kontrol eder, düne göre fiyat değişimini veya yeni bir kampanya/satıcı değişimini hesaplayarak özet bir rapor sunar.
2. **Fiyat Eşiği Alarmı (Koşullu Takip):** Fiyat belirlediğiniz eşik tutarının (örn. 1TB için 3.500 TL veya belirlediğiniz herhangi bir tutar) altına düştüğü anda doğrudan satıcı linki ve detaylı fiyat bilgisiyle anında bildirim gönderir.

---

## 🚀 Hızlı Başlangıç

### 1. Web Kontrol Panelini Başlatma (Önerilen)
Klasördeki **`baslat.bat`** dosyasına çift tıklayın.
- Arka planda sunucu ve otomatik zamanlayıcı başlar.
- Varsayılan tarayıcınızda otomatik olarak **`http://127.0.0.1:8000`** açılır.

### 2. Windows Görev Zamanlayıcısı'na Ekleme (Her gün 10:00'da Otomatik Çalışma)
Klasördeki **`kur_gorev_zamanlayici.bat`** dosyasına çift tıklayın.
- Bilgisayarınız açık olduğunda her sabah saat **10:00**'da arka planda Akakçe'yi otomatik tarar, dünkü fiyatla farkı hesaplar ve rapor bildirimi gönderir.
- İstediğinizde **`gorev_kaldir.bat`** ile görevi kolayca silebilirsiniz.

---

## 💻 Komut Satırından (CLI) Kullanım

İsterseniz terminalden de doğrudan çalıştırabilirsiniz:

```powershell
# Canlı fiyatları ve satıcıları şimdi kontrol et
.\.venv\Scripts\python.exe cli.py check

# Saat 10:00 Günlük Raporunu simüle et ve bildir
.\.venv\Scripts\python.exe cli.py report

# Örnek bir eşik alarmı testi yap (Windows Toast ve bildirimleri dener)
.\.venv\Scripts\python.exe cli.py test-alarm

# 1TB için eşik fiyatını 3.500 TL yap
.\.venv\Scripts\python.exe cli.py set-threshold 1tb 3500

# Akakçe'de ürün ara
.\.venv\Scripts\python.exe cli.py search "samsung 990 evo plus"
```

---

## 🔔 Bildirim Kanalları

Kontrol paneli üzerindeki **"Ayarlar"** menüsünden aşağıdaki kanalları kolayca yönetebilirsiniz:

1. **Windows 10/11 Masaüstü Bildirimi (Toast):**
   - Varsayılan olarak açıktır, ek bir kurulum veya API anahtarı gerektirmez.
   - Bildirimin üzerinde **"🛒 Satıcıya Git"** butonu bulunur. Tıkladığınızda doğrudan o anki en ucuz satıcının sayfası açılır.
2. **Telegram Botu:**
   - Bot Token ve Chat ID'nizi girip anında cep telefonunuza bildirim ve doğrudan satın alma butonu alabilirsiniz.
3. **Discord Webhook:**
   - Discord sunucunuzdaki kanal webhook adresini yapıştırarak zengin gömülü kart bildirimleri alabilirsiniz.

---

## 📁 Proje Dosya Yapısı

- `config.json` : Eşik tutarları, saat ayarları (10:00), kontrol sıklığı ve bildirim ayarları.
- `database.py` : SQLite veritabanı modeli (`akakce_tracker.db`), fiyat geçmişi, alarmlar ve günlük rapor kayıtları.
- `scraper.py` : Akakçe anti-bot (Cloudflare) korumasını aşan `curl_cffi` tabanlı veri çekici.
- `notifier.py` : Windows Toast, Telegram ve Discord bildirim motoru.
- `scheduler_service.py` : Her gün saat 10:00 raporu ve periyodik alarm denetleyicisi.
- `app.py` : FastAPI web sunucusu ve API endpointleri.
- `cli.py` : Komut satırı yönetim aracı.
- `run.py` : Web sunucusunu başlatıp tarayıcıyı otomatik açan ana betik.
- `templates/` & `static/` : Modern Glassmorphic Web Arayüzü (Chart.js fiyat grafikleri).
