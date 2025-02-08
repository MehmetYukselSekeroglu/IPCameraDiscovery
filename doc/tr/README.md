![Logo](../../img/logo.webp)

## Giriş

**IPCameraDiscovery**, IP tabanlı güvenlik kameralarını tespit etmek, port durumlarını kontrol etmek ve varsayılan kimlik bilgileriyle giriş denemeleri gerçekleştirmek için geliştirilmiş kapsamılı bir aracıdır. 

Bu proje; ağ taraması, port analizi, kamera tanımlama ve bruteforce gibi test senaryolarını bir araya getirerek, siber güvenlik uzmanları ve pen-test çalışmaları yapan geliştiricilere hızlı ve etkili bir çözüm sunar. 

Bu doküman, projenin temel işleyiş prensiplerini, dosya yapısını ve nasıl kullanılacağını detaylı şekilde açıklamaktadır.

---

## Özellikler

### 🔎 IP Tarama ve Port Kontrolü
- Tek bir IP, bir alt ağ veya dosya içindeki IP adreslerini tarar.
- Aktif cihazları ve bunların açık portlarını belirler.
- HTTP portlarına istek göndererek yanıt içeriğini analiz eder.

### 👁 Kamera Modeli Tanımlama
- `lib/identify.py` içerisindeki CSS seçiciler ile kamera modelini algılar.
- Hikvision, HAIKON, Sanetron, Longse gibi yaygın markaları tanıyabilir.
- Kamera modeline özel bruteforce denemeleri için gözlem yapar.

### ⚡ Bruteforce Saldırıları
- `lib/bruteforce.py` içinde bulunan fonksiyonlarla, varsayılan oturum açma bilgileriyle giriş testleri yapar.
- Kamera modeline uygun belirlenmiş kimlik bilgilerini dener.
- Başarılı oturumları `found_devices.txt` dosyasına kaydeder.

### 🛠 Headless Tarayıcı Kullanımı
- Selenium WebDriver yardımıyla otomatik giriş testleri yapar.
- Tarayıcıyı görünmez (headless) modda çalıştırır.

### ⚙ Paralel İşlem (Multi-threading)
- `threading` ve `concurrent.futures` kullanarak ağ taramalarını hızlandırır.
- Geniş IP aralıklarında verimli çalışmayı sağlar.

---

## Proje Yapısı

- **main.py** → Ana yürütücü betik. Tarama ve bruteforce işlerini sırasıyla gerçekleştirir.
- **lib/identify.py** → Kamera modelini HTTP yanıtlarından tespit eder.
- **lib/bruteforce.py** → Farklı kameralar için oturum açma denemelerini yönetir.
- **lib/env.py** → Portlar, URL yolları gibi sabitleri tanımlar.
- **lib/user_agent_tools.py** → HTTP istekleri için rastgele User-Agent seçimi yapar.

---

## Kullanım

### 👀 Tek IP Taraması
```sh
python main.py --ip 192.168.1.100 --threads 10
```

### 🌍 Alt Ağ Taraması
```sh
python main.py --subnet 192.168.1.0/24 --threads 10
```

### 📃 Dosya Üzerinden Taraması
```sh
python main.py --file ip_list.txt --threads 10
```

---

## İşleyiş Prensibi

1. **IP Tarama ve Port Kontrolü**: Ağdaki cihazlar belirlenir, açık portlar taranır.
2. **Kamera Tanımlama**: HTTP yanıtlarından model bilgisi çıkarılır.
3. **Bruteforce Denemeleri**: Tespit edilen modele uygun giriş testleri uygulanır.
4. **Sonuç Kayıtları**: Başarılı bulunan kimlik bilgileri kaydedilir.

---

## Gereksinimler ve Kurulum

- **Python Sürümü**: Python 3.x
- **Gerekli Paketler:**
  ```sh
  pip install requests selenium beautifulsoup4 colorama
  ```
- **Ek Gereksinimler:**
  - Selenium için uygun WebDriver (ChromeDriver, GeckoDriver vb.) sisteminizde bulunmalıdır.

---

## ⚠️ Güvenlik Uyarısı

Bu aracı yalnızca yetkili erişim iznine sahip sistemlerde test amaçlı kullanın. Yetkisiz erişim yasal sorumluluklar doğurabilir. Tüm kullanım sorumluluğu size aittir.

---

## 🌟 Lisans ve Katkı

Bu proje MIT lisansı altında sunulmaktadır.