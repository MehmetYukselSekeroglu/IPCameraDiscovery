import argparse
import ipaddress
import socket
import threading
import colorama
from datetime import datetime
import cv2
import os
import logging
import resource
from queue import Queue, Empty
import concurrent.futures
from urllib.parse import urlparse
import time
import sys
import signal

scan_started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
scan_started_at_text = f"--- Scan started at: {scan_started_at} ---\n"

with open("rtsp_streams.txt", "a+") as f:
    f.write(scan_started_at_text)


# Sistem limitlerini açık dosyalar için artır
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))

# OpenCV ve RTSP uyarılarını/hatalarını gizle
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
logging.getLogger("cv2").setLevel(logging.CRITICAL)
logging.getLogger("libav").setLevel(logging.CRITICAL)
logging.getLogger("rtsp").setLevel(logging.CRITICAL)

# RTSP hata mesajlarını gizle
cv2.setLogLevel(0)

colorama.init()

# RTSP portları (genişletilmiş)
RTSP_PORTS = [554]
#, 555, 8554, 8555, 10554, 1935, 5000, 5554, 7070, 8000, 8080, 8888, 10000, 1024, 1025, 1026, 1027, 1028, 1029, 1030]

# RTSP URL kalıpları (genişletilmiş)
RTSP_PATTERNS = [
    "rtsp://{ip}:{port}/live/ch00_0",
    "rtsp://{ip}:{port}/live/ch01_0",
    "rtsp://{ip}:{port}/1",
    "rtsp://{ip}:{port}/live/main",
    "rtsp://{ip}:{port}/live/sub",
    "rtsp://{ip}:{port}/11",
    "rtsp://{ip}:{port}/12",
    """
    "rtsp://{ip}:{port}/h264_ulaw.sdp",
    "rtsp://{ip}:{port}/h264.sdp",
    "rtsp://{ip}:{port}/Streaming/Channels/101",
    "rtsp://{ip}:{port}/Streaming/Channels/102",
    "rtsp://{ip}:{port}/Streaming/Channels/201",
    "rtsp://{ip}:{port}/Streaming/Channels/202",
    "rtsp://{ip}:{port}/",
    """
]

"""
    "rtsp://{ip}:{port}/cam/realmonitor",
    "rtsp://{ip}:{port}/cam1/h264",
    "rtsp://{ip}:{port}/cam2/h264",
    "rtsp://{ip}:{port}/onvif1",
    "rtsp://{ip}:{port}/onvif2",
    "rtsp://{ip}:{port}/profile1",
    "rtsp://{ip}:{port}/profile2",
    "rtsp://{ip}:{port}/mpeg4/media.amp",
    "rtsp://{ip}:{port}/stream1",
    "rtsp://{ip}:{port}/stream2",
    "rtsp://{ip}:{port}/video1",
    "rtsp://{ip}:{port}/video2",
    "rtsp://{ip}:{port}/av0_0",
    "rtsp://{ip}:{port}/av0_1",
    "rtsp://{ip}:{port}/ch0",
    "rtsp://{ip}:{port}/ch1",

"""


# Yaygın kimlik doğrulama kombinasyonları (genişletilmiş)
AUTH_COMBINATIONS = [
    ('admin', 'admin'),
    ('admin', ''),
    ('admin', '12345'),
    ('admin', '123456'),
    ('admin', '1234567'),
    ('admin', '12345678'),
    ('admin', '123456789'),
    ('admin', '1234567890'),
    ('admin', 'password'),
    ('admin', 'pass'),
    ('admin', 'admin123'),
    ('admin', 'admin1234'),
    ('admin', 'admin12345'),
    ('admin', 'admin123456'),
    """
    ('root', 'root'),
    ('root', ''),
    ('root', '12345'),
    ('root', '123456'),
    ('root', 'password'),
    ('user', 'user'),
    ('user', 'password'),
    ('user', '12345'),
    ('user', '123456'),
    ('guest', 'guest'),
    ('guest', ''),
    ('guest', '12345'),
    ('guest', '123456'),
    ('operator', 'operator'),
    ('supervisor', 'supervisor'),
    ('hikvision', 'hikvision'),
    ('dahua', 'dahua'),
    ('service', 'service'),
    ('support', 'support'),
    ('system', 'system'),
    ('default', 'default'),
    ('camera', 'camera'),
    ('ipcam', 'ipcam'),
    ('dvr', 'dvr'),
    ('nvr', 'nvr'),
    ('ubnt', 'ubnt'),
    ('admin', 'admin1'),
    ('admin', 'admin2'),
    ('admin', 'admin01'),
    ('admin', 'admin02'),
    ('admin', '1111'),
    ('admin', '11111'),
    ('admin', '111111'),
    ('admin', '0000'),
    ('admin', '00000'),
    ('admin', '000000'),
    """
]

# Global değişkenler
total_ips = 0
scanned_ips = 0
scan_lock = threading.Lock()
found_streams = set()
file_lock = threading.Lock()
ip_queue = Queue()
socket_semaphore = threading.BoundedSemaphore(1000)
start_time = None
custom_auth_file = None
custom_patterns_file = None
verbose_mode = False
scan_running = True

SOCKET_TIMEOUT = 5
MAX_WORKERS = 50
MAX_AUTH_WORKERS = 15

def signal_handler(sig, frame):
    """Ctrl+C işleyicisi"""
    global scan_running
    print(colorama.Fore.YELLOW + "\n\nTarama durduruldu. Mevcut işlemler tamamlanıyor..." + colorama.Fore.RESET)
    scan_running = False
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def load_custom_auth(filename):
    """Özel kimlik doğrulama kombinasyonlarını dosyadan yükle"""
    auth_list = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if ':' in line:
                    username, password = line.split(':', 1)
                    auth_list.append((username, password))
        print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"{len(auth_list)} özel kimlik doğrulama kombinasyonu yüklendi" + colorama.Fore.RESET)
        return auth_list
    except Exception as e:
        print(colorama.Fore.RED + f"Kimlik doğrulama dosyası yükleme hatası: {str(e)}" + colorama.Fore.RESET)
        return []

def load_custom_patterns(filename):
    """Özel RTSP kalıplarını dosyadan yükle"""
    patterns = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
        print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"{len(patterns)} özel RTSP kalıbı yüklendi" + colorama.Fore.RESET)
        return patterns
    except Exception as e:
        print(colorama.Fore.RED + f"Kalıp dosyası yükleme hatası: {str(e)}" + colorama.Fore.RESET)
        return []

def format_time(seconds):
    """Saniyeyi okunabilir zaman formatına dönüştür"""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def write_to_file(filename, content):
    """Thread-safe dosya yazma fonksiyonu"""
    try:
        with file_lock:
            with open(filename, "a") as f:
                f.write(f"{content}\n")
    except Exception as e:
        print(f"Dosya yazma hatası: {str(e)}")

def verify_rtsp_stream_rtsp(url, auth=None):
    """RTSP stream doğrulamasını hızlı ve güvenilir şekilde gerçekleştirir."""
    try:
        # Auth bilgisini URL'e ekle
        if auth:
            url = url.replace("rtsp://", f"rtsp://{auth[0]}:{auth[1]}@")

        # URL parsing işlemini optimize et
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 554

        # Socket bağlantısını kur ve OPTIONS isteği gönder
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            s.connect((host, port))
            
            # İlk olarak OPTIONS isteği gönder
            options_request = f"OPTIONS {url} RTSP/1.0\r\nCSeq: 1\r\n\r\n"
            s.sendall(options_request.encode())
            
            options_response = s.recv(512).decode(errors='ignore')
            
            # OPTIONS yanıtını kontrol et
            if "RTSP/1.0 200 OK" not in options_response:
                return False

            # DESCRIBE isteği gönder
            describe_request = (
                f"DESCRIBE {url} RTSP/1.0\r\n"
                f"CSeq: 2\r\n"
                f"Accept: application/sdp\r\n\r\n"
            )
            s.sendall(describe_request.encode())
            
            # DESCRIBE yanıtını al
            describe_response = s.recv(1024).decode(errors='ignore')
            
            # Unauthorized durumunda false dön
            if "401 Unauthorized" in describe_response:
                return False
                
            # Başarılı DESCRIBE yanıtı ve SDP içeriği kontrol et
            if ("RTSP/1.0 200 OK" in describe_response and 
                "Content-Type: application/sdp" in describe_response and
                "m=video" in describe_response):
                return True
                
        return False
        
    except (socket.timeout, socket.error, Exception):
        return False

def check_rtsp(ip, port, pattern):
    if not scan_running:
        return False
        
    try:
        with socket_semaphore:
            url = pattern.format(ip=ip, port=port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            result = sock.connect_ex((str(ip), port))
            sock.close()
            
            if result == 0:
                # Kullanılacak kimlik doğrulama kombinasyonlarını belirle
                auth_list = AUTH_COMBINATIONS
                if custom_auth_file:
                    auth_list = load_custom_auth(custom_auth_file)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_AUTH_WORKERS) as auth_executor:
                    auth_futures = []
                    
                    # Önce kimlik doğrulama olmadan dene
                    auth_futures.append(auth_executor.submit(verify_rtsp_stream_rtsp, url, None))
                    
                    # Sonra kimlik doğrulama kombinasyonlarını dene
                    for auth in auth_list:
                        if not scan_running:
                            return False
                        auth_futures.append(auth_executor.submit(verify_rtsp_stream_rtsp, url, auth))
                    
                    # Sonuçları kontrol et
                    for future in concurrent.futures.as_completed(auth_futures):
                        if not scan_running:
                            return False
                        try:
                            if future.result():
                                auth_idx = auth_futures.index(future) - 1
                                auth_used = None if auth_idx < 0 else auth_list[auth_idx]
                                
                                if url not in found_streams:
                                    found_streams.add(url)
                                    
                                    # rtsp://user:pass@ip/path formatını oluştur
                                    formatted_url = url
                                    if auth_used:
                                        parsed_url = urlparse(url)
                                        formatted_url = f"rtsp://{auth_used[0]}:{auth_used[1]}@{parsed_url.netloc}{parsed_url.path}"
                                    
                                    # Hem konsola hem dosyaya aynı formatta yaz
                                    print("\n" + colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                          f"Doğrulanmış RTSP akışı bulundu: {formatted_url}" + colorama.Fore.RESET)
                                    write_to_file("rtsp_streams.txt", formatted_url)
                                    
                                    return True
                        except Exception:
                            continue
    except Exception as e:
        if verbose_mode:
            print(colorama.Fore.RED + f"RTSP kontrol hatası {ip}:{port}: {str(e)}" + colorama.Fore.RESET)
    return False

def check_port(ip, port):
    """Portun açık olup olmadığını socket kullanarak kontrol et"""
    try:
        with socket_semaphore:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((str(ip), port))
            sock.close()
            return result == 0
    except:
        return False

def scan_ip(ip):
    global scanned_ips
    
    if not scan_running:
        return
    
    try:
        open_ports = []
        
        # RTSP portlarını kontrol et
        for port in RTSP_PORTS:
            if not scan_running:
                return
            if check_port(ip, port):
                open_ports.append(port)
                print("\n" + colorama.Fore.YELLOW + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Açık RTSP portu bulundu: {ip}:{port}" + colorama.Fore.RESET)
        
        if open_ports:
            print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {ip} için RTSP tespiti başlatılıyor" + colorama.Fore.RESET)
            
            # Kullanılacak kalıpları belirle
            patterns = RTSP_PATTERNS
            if custom_patterns_file:
                custom_patterns = load_custom_patterns(custom_patterns_file)
                if custom_patterns:
                    patterns = custom_patterns
            
            # Her port için thread havuzu oluştur
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(open_ports)) as port_executor:
                port_futures = []
                
                for port in open_ports:
                    if not scan_running:
                        return
                    # Her port için kalıpları paralel olarak kontrol et
                    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pattern_executor:
                        pattern_futures = []
                        for pattern in patterns:
                            if not scan_running:
                                return
                            future = pattern_executor.submit(check_rtsp, ip, port, pattern)
                            pattern_futures.append(future)
                            
                            # Akış bulundu mu kontrol et
                            try:
                                if future.result():
                                    # Akış bulundu, diğer kalıpları kontrol etmeyi durdur
                                    pattern_executor.shutdown(wait=False)
                                    return
                            except Exception:
                                continue
                                
            print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {ip} için RTSP tespiti tamamlandı" + colorama.Fore.RESET)
            
        with scan_lock:
            scanned_ips += 1
            if total_ips > 0:
                progress = (scanned_ips / total_ips) * 100
                elapsed = time.time() - start_time
                remaining = (elapsed / scanned_ips) * (total_ips - scanned_ips) if scanned_ips > 0 else 0
                print(colorama.Fore.CYAN + f"\rTarama ilerlemesi: %{progress:.2f} ({scanned_ips}/{total_ips} IP) | "
                      f"Geçen süre: {format_time(elapsed)} | Kalan süre: {format_time(remaining)}", end="")
            
    except Exception as e:
        if verbose_mode:
            print(f"IP tarama hatası {ip}: {str(e)}")

def worker():
    while scan_running:
        try:
            ip = ip_queue.get_nowait()
            scan_ip(ip)
            ip_queue.task_done()
        except Empty:
            break
        except Exception as e:
            if verbose_mode:
                print(f"İşçi hatası: {str(e)}")
            continue

def scan_from_file(filename):
    global total_ips
    try:
        with open(filename, 'r') as f:
            ips = [line.strip() for line in f if line.strip()]
        
        total_ips = len(ips)
        for ip in ips:
            ip_queue.put(ip)
            
        # İşçi thread'leri başlat
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker) for _ in range(min(MAX_WORKERS, len(ips)))]
            concurrent.futures.wait(futures)
            
    except Exception as e:
        print(f"Dosya okuma hatası: {str(e)}")

def main():
    global total_ips, start_time, custom_auth_file, custom_patterns_file, verbose_mode, MAX_WORKERS
    
    parser = argparse.ArgumentParser(description='RTSP Akış Tarayıcı')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--subnet', help='Taranacak alt ağ (örn: 192.168.1.0/24)')
    group.add_argument('--ip', help='Taranacak tek IP')
    group.add_argument('--file', help='Taranacak IP\'leri içeren dosya (her satırda bir IP)')
    parser.add_argument('--threads', type=int, default=MAX_WORKERS, help='Thread sayısı')
    parser.add_argument('--timeout', type=int, default=SOCKET_TIMEOUT, help='Socket zaman aşımı (saniye)')
    parser.add_argument('--auth-file', help='Özel kimlik doğrulama kombinasyonlarını içeren dosya (kullanıcı:şifre formatında)')
    parser.add_argument('--patterns-file', help='Özel RTSP kalıplarını içeren dosya')
    parser.add_argument('--output', default='rtsp_streams.txt', help='Bulunan akışların kaydedileceği dosya')
    parser.add_argument('--verbose', action='store_true', help='Ayrıntılı çıktı modu')
    args = parser.parse_args()

    # Global değişkenleri güncelle
    MAX_WORKERS = args.threads
    custom_auth_file = args.auth_file
    custom_patterns_file = args.patterns_file
    verbose_mode = args.verbose
    start_time = time.time()

    print(colorama.Fore.CYAN + "=" * 80 + colorama.Fore.RESET)
    print(colorama.Fore.CYAN + "                      RTSP AKIŞ TARAYICI - GELİŞMİŞ SÜRÜM" + colorama.Fore.RESET)
    print(colorama.Fore.CYAN + "=" * 80 + colorama.Fore.RESET)
    print(colorama.Fore.YELLOW + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tarama başlatılıyor..." + colorama.Fore.RESET)
    print(colorama.Fore.YELLOW + f"Thread sayısı: {MAX_WORKERS}" + colorama.Fore.RESET)
    print(colorama.Fore.YELLOW + f"Socket zaman aşımı: {args.timeout} saniye" + colorama.Fore.RESET)
    
    if custom_auth_file:
        print(colorama.Fore.YELLOW + f"Özel kimlik doğrulama dosyası: {custom_auth_file}" + colorama.Fore.RESET)
    
    if custom_patterns_file:
        print(colorama.Fore.YELLOW + f"Özel kalıp dosyası: {custom_patterns_file}" + colorama.Fore.RESET)
    
    print(colorama.Fore.YELLOW + f"Çıktı dosyası: {args.output}" + colorama.Fore.RESET)
    print(colorama.Fore.CYAN + "=" * 80 + colorama.Fore.RESET)

    try:
        if args.subnet:
            network = ipaddress.ip_network(args.subnet)
            total_ips = network.num_addresses - 2  # Ağ ve yayın adreslerini hariç tut
            
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"{args.subnet} alt ağındaki {total_ips} IP taranmaya başlanıyor" + colorama.Fore.RESET)

            # IP'leri kuyruğa ekle
            for ip in network.hosts():
                ip_queue.put(str(ip))

            # İşçi thread'leri başlat
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = [executor.submit(worker) for _ in range(min(args.threads, total_ips))]
                concurrent.futures.wait(futures)
                
        elif args.ip:
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"{args.ip} IP'si taranmaya başlanıyor" + colorama.Fore.RESET)
            scan_ip(args.ip)
            
        else:  # args.file
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"{args.file} dosyasındaki IP'ler taranmaya başlanıyor" + colorama.Fore.RESET)
            scan_from_file(args.file)

        elapsed = time.time() - start_time
        print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Tarama tamamlandı. Toplam süre: {format_time(elapsed)}" + colorama.Fore.RESET)
        print(colorama.Fore.CYAN + f"RTSP akışları {args.output} dosyasına kaydedildi" + colorama.Fore.RESET)
        print(colorama.Fore.GREEN + f"Bulunan toplam akış sayısı: {len(found_streams)}" + colorama.Fore.RESET)
    
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print("\n" + colorama.Fore.YELLOW + f"Tarama kullanıcı tarafından durduruldu. Toplam süre: {format_time(elapsed)}" + colorama.Fore.RESET)
        print(colorama.Fore.GREEN + f"Bulunan toplam akış sayısı: {len(found_streams)}" + colorama.Fore.RESET)
    except Exception as e:
        print(colorama.Fore.RED + f"Beklenmeyen hata: {str(e)}" + colorama.Fore.RESET)

if __name__ == "__main__":
    main()
