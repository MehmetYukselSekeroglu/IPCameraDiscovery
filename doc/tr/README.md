![Logo](../../img/logo.webp)

# IP Kamera Keşif Aracı

## Giriş

**IPCameraDiscovery**, IP tabanlı güvenlik kameralarını tespit etmek, port durumlarını kontrol etmek ve varsayılan kimlik bilgileriyle giriş denemeleri gerçekleştirmek için geliştirilmiş kapsamlı bir araçtır. 

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
- Hikvision, HAIKON, Sanetron, Longse, Dahura gibi yaygın markaları tanıyabilir.
- Belirlenen kamera modeline özel bruteforce denemeleri için hazırlık yapar.

### ⚡ Bruteforce Saldırıları
- `lib/bruteforce.py` içinde bulunan fonksiyonlarla, varsayılan oturum açma bilgileriyle giriş testleri yapar.
- Tespit edilen kamera modeline uygun belirlenmiş kimlik bilgilerini dener.
- Başarılı oturumları `found_devices.txt` dosyasına kaydeder.

### 🛠 Headless Tarayıcı Kullanımı
- Selenium WebDriver yardımıyla otomatik giriş testleri yapar.
- Verimli çalışma için tarayıcıyı görünmez (headless) modda çalıştırır.

### ⚙ Paralel İşlem (Multi-threading)
- `threading` ve `concurrent.futures` kullanarak ağ taramalarını hızlandırır.
- Geniş IP aralıklarında verimli çalışmayı sağlar.
- En iyi performans için yapılandırılabilir iş parçacığı sayısı.

---

## Proje Yapısı

### Ana Dosyalar
- **main.py** → Ana yürütücü betik. Tarama ve bruteforce işlerini sırasıyla gerçekleştirir.
- **only_rtsp_scanner.py** → RTSP akışlarını taramak için özelleştirilmiş araç.
- **rtsp_path_scanner_require_password.py** → Kimlik doğrulama gerektiren RTSP yollarını taramak için araç.
- **rtsp_view.py** → RTSP akışlarını görüntülemek için yardımcı program.
- **scan_subnet_detect_live_streams.py** → Bir alt ağda canlı akışları tespit etmek için araç.

### Kütüphane Dosyaları
- **lib/identify.py** → HTTP yanıtlarından CSS seçiciler kullanılarak kamera modelini tespit eder.
- **lib/bruteforce.py** → Farklı kameralar için oturum açma denemelerini yönetir.
- **lib/env.py** → Portlar, URL yolları ve uygulama bilgileri gibi sabitleri tanımlar.
- **lib/user_agent_tools.py** → HTTP istekleri için rastgele User-Agent seçimi yapar.

### Veri Dosyaları
- **rtsp_streams.txt** → Keşfedilen RTSP akışları hakkında bilgi içerir.
- **found_devices.txt** → Başarılı giriş kimlik bilgilerini kaydeder.
- **rtsp_path_wordlist.txt** → Tarama için yaygın RTSP yollarını içerir.

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

### 📃 Dosya Üzerinden Tarama
```sh
python main.py --file ip_list.txt --threads 10
```

### 🎦 RTSP Taraması
```sh
python only_rtsp_scanner.py --subnet 192.168.1.0/24
```

### 🔑 Kimlik Doğrulamalı RTSP Yolu Taraması
```sh
python rtsp_path_scanner_require_password.py --ip 192.168.1.100 --username admin --password 123456
```

---

## İşleyiş Prensibi

1. **IP Tarama ve Port Kontrolü**: Ağdaki cihazlar belirlenir, açık portlar taranır.
2. **Kamera Tanımlama**: HTTP yanıtlarından CSS seçiciler kullanılarak model bilgisi çıkarılır.
3. **Bruteforce Denemeleri**: Tespit edilen modele uygun giriş testleri uygulanır.
4. **Sonuç Kayıtları**: Başarılı bulunan kimlik bilgileri found_devices.txt dosyasına kaydedilir.

---

## Gereksinimler ve Kurulum

- **Python Sürümü**: Python 3.x
- **Gerekli Paketler:**
  ```sh
  pip install -r requirements.txt
  ```
  veya paketleri tek tek kurma:
  ```sh
  pip install argparse requests beautifulsoup4 colorama urllib3 selenium tqdm ipaddress
  ```
- **Ek Gereksinimler:**
  - Selenium için uygun WebDriver (ChromeDriver, GeckoDriver vb.) sisteminizde bulunmalıdır.

---

## ⚠️ Güvenlik Uyarısı

Bu aracı yalnızca yetkili erişim iznine sahip sistemlerde test amaçlı kullanın. Yetkisiz erişim yasal sorumluluklar doğurabilir. Tüm kullanım sorumluluğu size aittir.

---

## 🌟 Lisans ve Katkı

Bu proje MIT lisansı altında sunulmaktadır.

© 2023-2024 Mehmet Yüksel Şekeroğlu