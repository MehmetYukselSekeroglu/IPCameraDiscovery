![Logo](img/logo.webp)

# IPCameraDiscovery

IPCameraDiscovery, ağınızdaki IP kameraları tespit etmek ve özellikle Hikvision cihazlarının varlığını belirlemek için geliştirilmiş bir Python tabanlı araçtır. Bu araç, subnet taraması yaparak potansiyel kameraları bulur, kimlik doğrulama kontrolleri gerçekleştirir ve sonuçları filtreler.

## Özellikler

- **Subnet Tarama**: Belirtilen IP aralıklarında otomatik olarak cihazları tarar.
- **Hikvision Cihaz Tespiti**: Özellikle Hikvision marka IP kameraları belirlemek için gelişmiş kontrol mekanizmaları.
- **Otomatik Kimlik Doğrulama**: Varsayılan kullanıcı adı ve şifre kombinasyonları ile kameralara otomatik giriş denemeleri.
- **Sonuçların Filtrelenmesi**: Bulunan kameraların sonuçlarını filtreleyerek kayıt altına alır.
- **Renkli Konsol Çıktıları**: Kolay okunabilirlik için renkli konsol çıktıları kullanır.

## Kurulum

1. **Python Kurulumu**: Araç Python 3.6 veya üzeri sürümlerle çalışmaktadır. Python'u [python.org](https://www.python.org/downloads/) adresinden indirebilirsiniz.

2. **Gerekli Paketlerin Yüklenmesi**:
    ```bash
    pip install -r requirements.txt
    ```

3. **WebDriver Kurulumu**:
    Araç, Selenium kullanarak tarama yapmaktadır. **Chromedriver** yüklemeniz gerekmektedir. [Chromedriver İndir](https://sites.google.com/chromium.org/driver/) sayfasından işletim sisteminize uygun sürümü indirip, sistem PATH'ine ekleyin.

## Kullanım

### Genel IP Kamera Keşif Aracı

Subnet taraması yapmak için:
```bash
python general_ip_camera_finder.py --target 192.168.1.0/24
```

### Hikvision Kamera Tarama

Hikvision özelinde tarama yapmak için:
```bash
python scan_subnet_find_hikvision_cameras.py --ip 192.168.1.0/24 --max_workers 50
```

### Ham Verilerin Filtrelenmesi

Bulunan kameraların ham verilerini filtrelemek için:
```bash
python raw_filter.py --input found_cameras.txt --output filtered_cameras.txt
```

### Hikvision Giriş Kontrolü

Bulunan Hikvision kameraların giriş kontrolünü yapmak için:
```bash
python hikvision_login_checker.py --file filtered_cameras.txt
```

## Proje Yapısı

- `general_ip_camera_finder.py`: Genel IP kamera tarama işlemleri.
- `scan_subnet_find_hikvision_cameras.py`: Özellikle Hikvision kameraları taramak için.
- `raw_filter.py`: Ham tarama sonuçlarını filtrelemek için.
- `hikvision_login_checker.py`: Bulunan Hikvision kameralarına otomatik giriş denemeleri yapmak için.
- `requirements.txt`: Gerekli Python paket listesi.
- `img/logo.webp`: Proje logosu.
- `doc/tr/README.md`: Türkçe README dosyası.
- `doc/en/README.md`: İngilizce README dosyası.
## Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

