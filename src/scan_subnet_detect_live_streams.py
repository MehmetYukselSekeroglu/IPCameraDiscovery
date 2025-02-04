import argparse
import ipaddress
import socket
import threading
import requests
import colorama
from datetime import datetime
import time
import cv2
import os
import logging
import resource
from queue import Queue, Empty
from urllib.parse import urlparse
import urllib3
import concurrent.futures

# Increase system limits for open files
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))

# Hide OpenCV and RTSP warnings/errors
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
logging.getLogger("cv2").setLevel(logging.CRITICAL)
logging.getLogger("libav").setLevel(logging.CRITICAL)
logging.getLogger("rtsp").setLevel(logging.CRITICAL)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Hide RTSP error messages
cv2.setLogLevel(0)

colorama.init()

# Common IP camera ports and manufacturer-specific ports
COMMON_PORTS = list(set([
    80, 81, 82, 83, 84, 85, 88, 443,
    8000, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8088, 9000,
    37777,  # Dahua
    34567,  # Hikvision 
    9001, 9002,  # Axis
    8899,  # Mobotix
    8899,  # Vivotek
    8000,  # Avigilon
    7001,  # Arecont
    8091,  # Panasonic
    8999,  # Sony
    8086   # Geovision
]))

# RTSP ports
RTSP_PORTS = list(set([554, 8554, 10554]))

# Vendor identification patterns
VENDOR_PATTERNS = {
    'hikvision': [
        '/ISAPI/',
        'Hikvision',
        '/Streaming/Channels/',
        'webui'
    ],
    'dahua': [
        'cam/realmonitor',
        'cgi-bin/snapshot.cgi',
        'Dahua',
        'lechange'
    ],
    'axis': [
        'axis-cgi',
        'axis-media',
        'view/viewer',
        'axis'
    ],
    'mobotix': [
        'control/faststream',
        'mobotix',
        'MxPEG'
    ],
    'vivotek': [
        'viewer/video',
        'vivotek',
        'live.sdp'
    ],
    'panasonic': [
        'nphMotionJpeg',
        'panasonic',
        'i-pro'
    ],
    'sony': [
        'image/jpeg.cgi',
        'sony',
        'snc'
    ],
    'bosch': [
        'rtsp_tunnel',
        'bosch',
        'rcp'
    ],
    'arecont': [
        'mjpeg?res=',
        'arecont',
        'av_stream'
    ],
    'geovision': [
        'PictureCatch',
        'geovision',
        'JPGStream'
    ]
}

# Stream URL patterns - Most common patterns
STREAM_PATTERNS = [
    # ONVIF
    "/onvif/device_service",
    "/onvif/media_service",
    "/onvif/snapshot",
    
    # General formats
    "/video.mjpg", "/video.cgi", "/mjpg/video.mjpg",
    "/cgi-bin/mjpg/video.cgi", "/axis-cgi/mjpg/video.cgi",
    "/nphMotionJpeg", "/live.mjpg", "/live/mjpeg",
    "/live/stream", "/live_stream", "/stream.mjpg",
    "/videostream.cgi", "/video/mjpg", "/video.mp4",
    "/live/main", "/live/sub", "/live/ch1", "/live/ch2",
    "/live.jpg", "/live.h264", "/live.mp4", "/live.flv",
    
    # Hikvision
    "/ISAPI/Streaming/channels/101/httpPreview",
    "/ISAPI/Streaming/channels/102/httpPreview",
    "/PSIA/Streaming/channels/1",
    "/PSIA/Streaming/channels/2",
    
    # Dahua
    "/cgi-bin/snapshot.cgi",
    "/cgi-bin/mjpg/video.cgi?channel=1&subtype=1", 
    "/cgi-bin/snapshot.cgi?channel=1",
    "/cgi-bin/snapshot.cgi?channel=2",
    
    # Axis
    "/axis-cgi/jpg/image.cgi",
    "/axis-cgi/mjpg/video.cgi?camera=1",
    "/axis-cgi/mjpg/video.cgi",
    "/view/viewer_index.shtml",
    
    # Mobotix
    "/control/faststream.jpg?stream=full",
    "/cgi-bin/faststream.jpg?stream=full",
    "/control/faststream.jpg?stream=preview",
    "/faststream.jpg",
    
    # Vivotek
    "/video.mjpg",
    "/cgi-bin/viewer/video.jpg",
    "/cgi-bin/video.jpg",
    "/videostream.cgi",
    
    # Panasonic
    "/nphMotionJpeg?Resolution=640x480&Quality=Standard",
    "/cgi-bin/camera",
    "/SnapshotJPEG?Resolution=640x480",
    "/nphMotionJpeg",
    
    # Sony
    "/image/jpeg.cgi",
    "/image",
    "/oneshotimage.jpg",
    "/jpg/image.cgi",
    
    # Bosch
    "/rtsp_tunnel",
    "/snap.jpg",
    "/jpg/image.jpg",
    "/video",
    
    # Arecont
    "/mjpeg?res=half&doublescan=0&fps=15&compression=1",
    "/mjpeg?res=full&fps=0",
    "/image?res=half",
    "/image",
    
    # Geovision
    "/PictureCatch.cgi",
    "/JPGStream.cgi",
    "/streaming/channels",
    "/videostream.asf",
    
    # Less common patterns (commented out)
    "/view/index.shtml",
    # "/control/faststream.jpg?stream=full&fps=12", 
    # "/cgi-bin/faststream.jpg?stream=preview",
    "/video/mjpg",
    # "/cgi-bin/nphMotionJpeg",
    "/live/jpeg.cgi",
    # "/command/inquiry.cgi?inq=system",
    # "/video1", "/video2",
    # "/image?res=full",
    "/mjpeg",
    # "/GetData.cgi",
    # "/StreamingSetting"
]

# RTSP URL patterns
RTSP_PATTERNS = [
    # ONVIF
    "rtsp://{ip}:{port}/onvif/device_service",
    "rtsp://{ip}:{port}/onvif/media",
    "rtsp://{ip}:{port}/onvif/live",
    
    # ONVIF H264
    "rtsp://{ip}:{port}/h264_ulaw.sdp",
    "rtsp://{ip}:{port}/h264.sdp",
    
    # General RTSP patterns
    "rtsp://{ip}:{port}/live",
    "rtsp://{ip}:{port}/1"
    "rtsp://{ip}:{port}/live/ch00_0",
    "rtsp://{ip}:{port}/live/ch01_0", 
    "rtsp://{ip}:{port}/live/main",
    "rtsp://{ip}:{port}/live/sub",
    "rtsp://{ip}:{port}/11",
    "rtsp://{ip}:{port}/12",
    "rtsp://{ip}:{port}/media/video1",
    "rtsp://{ip}:{port}/media/video2",
    "rtsp://{ip}:{port}/profile1",
    "rtsp://{ip}:{port}/profile2",
    "rtsp://{ip}:{port}/stream1",
    "rtsp://{ip}:{port}/stream2",
    "rtsp://{ip}:{port}/live",
    
    # Hikvision
    "rtsp://{ip}:{port}/Streaming/Channels/101",
    "rtsp://{ip}:{port}/Streaming/Channels/102",
    "rtsp://{ip}:{port}/h264/ch1/main/av_stream",
    "rtsp://{ip}:{port}/h264/ch1/sub/av_stream",
    
    # Dahua
    "rtsp://{ip}:{port}/cam/realmonitor?channel=1&subtype=0",
    "rtsp://{ip}:{port}/cam/realmonitor?channel=1&subtype=1",
    "rtsp://{ip}:{port}/video1",
    "rtsp://{ip}:{port}/video2",
    
    # Axis
    "rtsp://{ip}:{port}/axis-media/media.amp",
    "rtsp://{ip}:{port}/mpeg4/media.amp",
    "rtsp://{ip}:{port}/axis-media/media.3gp",
    
    # Vivotek
    "rtsp://{ip}:{port}/live.sdp",
    "rtsp://{ip}:{port}/live1.sdp",
    "rtsp://{ip}:{port}/live2.sdp",
    "rtsp://{ip}:{port}/rtsp_tunnel",
    
    # Bosch
    "rtsp://{ip}:{port}/rtsp_tunnel",
    "rtsp://{ip}:{port}/video1",
    "rtsp://{ip}:{port}/video2",
    "rtsp://{ip}:{port}/h264",
    
    # Panasonic
    "rtsp://{ip}:{port}/MediaInput/h264",
    "rtsp://{ip}:{port}/nphMpeg4/nil-640x480",
    
    # Reolink
    "rtsp://{ip}:{port}/h264Preview_01_main",
    "rtsp://{ip}:{port}/h264Preview_01_sub",
    
    # Less common patterns (commented out)
    "rtsp://{ip}:{port}/h264_pcmu.sdp",
    "rtsp://{ip}:{port}/h264_basic.sdp",
    "rtsp://{ip}:{port}/live/h264",
    "rtsp://{ip}:{port}/live/mpeg4",
    "rtsp://{ip}:{port}/video1+audio1",
    "rtsp://{ip}:{port}/Streaming/Channels/201",
    "rtsp://{ip}:{port}/Streaming/Channels/202",
    "rtsp://{ip}:{port}/h264/ch2/main/av_stream",
    "rtsp://{ip}:{port}/h264/ch2/sub/av_stream",
    "rtsp://{ip}:{port}/cam/realmonitor?channel=2&subtype=0",
    "rtsp://{ip}:{port}/cam/realmonitor?channel=2&subtype=1",
    "rtsp://{ip}:{port}/axis-media/mpeg4/media.amp",
    "rtsp://{ip}:{port}/mpeg4/1/media.amp",
    "rtsp://{ip}:{port}/video.3gp",
    "rtsp://{ip}:{port}/video.mp4",
    "rtsp://{ip}:{port}/mpeg4",
    "rtsp://{ip}:{port}/stream1"
]

# Vendor specific auth combinations
AUTH_COMBINATIONS = {
    'hikvision': [
        ('admin', '12345'),
        ('admin', 'admin12345'),
        ('admin', 'Admin12345'),
        ('admin', 'hikvision'),
        ('admin', 'hik12345')
    ],
    'dahua': [
        ('admin', 'admin'),
        ('admin', 'Admin123'),
        ('888888', '888888'),
        ('admin', 'dahua'),
        ('admin', 'dh123456')
    ],
    'axis': [
        ('root', 'pass'),
        ('admin', 'admin'),
        ('admin', 'axis2023'),
        ('root', 'axis'),
        ('admin', 'axis123')
    ],
    'mobotix': [
        ('admin', 'meinsm'),
        ('admin', 'admin'),
        ('admin', 'mobotix'),
        ('admin', 'mx123'),
        ('service', 'meinsm')
    ],
    'vivotek': [
        ('root', 'root'),
        ('admin', 'admin'),
        ('vivotek', 'vivotek'),
        ('admin', 'vivo123'),
        ('root', 'vivo1234')
    ],
    'panasonic': [
        ('admin', '12345'),
        ('admin', 'admin'),
        ('pana', 'pana'),
        ('admin', 'panasonic'),
        ('service', 'service')
    ],
    'sony': [
        ('admin', 'admin'),
        ('root', 'sony'),
        ('admin', 'sony1234'),
        ('admin', 'sony123'),
        ('service', 'service')
    ],
    'bosch': [
        ('service', 'service'),
        ('admin', 'admin'),
        ('live', 'live'),
        ('admin', 'bosch'),
        ('service', 'bosch123')
    ],
    'arecont': [
        ('admin', 'admin'),
        ('arecont', 'arecont'),
        ('admin', 'arecont123'),
        ('admin', 'are123'),
        ('service', 'arecont')
    ],
    'geovision': [
        ('admin', 'admin'),
        ('supervisor', 'supervisor'),
        ('admin', 'geo123'),
        ('admin', 'geovision'),
        ('service', 'geo1234')
    ],
    'general': [
        ('admin', 'admin'),
        ('admin', ''),
        ('admin', '12345'),
        ('admin', 'password'),
        ('root', 'root'),
        ('admin', '123456'),
        ('admin', '9999'),
        ('admin', 'camera'),
        ('admin', '1234'),
        ('admin', 'system')
    ]
    
    # Less common auth combinations (commented out)
    # 'mobotix': [
    #     ('admin', 'meinsm'),
    #     ('admin', 'admin'),
    #     ('admin', 'mobotix'),
    #     ('admin', 'mx123'),
    #     ('service', 'meinsm')
    # ],
    # 'vivotek': [
    #     ('root', 'root'),
    #     ('admin', 'admin'),
    #     ('vivotek', 'vivotek'),
    #     ('admin', 'vivo123'),
    #     ('root', 'vivo1234')
    # ],
    # 'panasonic': [
    #     ('admin', '12345'),
    #     ('admin', 'admin'),
    #     ('pana', 'pana'),
    #     ('admin', 'panasonic'),
    #     ('service', 'service')
    # ]
}

# Global variables
total_ips = 0
scanned_ips = 0
scan_lock = threading.Lock()
found_streams = set()  # To prevent duplicate streams
file_lock = threading.Lock() # Lock for file writing operations
ip_queue = Queue() # Queue for IP addresses
socket_semaphore = threading.BoundedSemaphore(1000) # Limit concurrent socket connections

SOCKET_TIMEOUT = 5
MAX_WORKERS = 50 # Limit max worker threads
MAX_AUTH_WORKERS = 5 # Limit auth check threads
MAX_PATTERN_WORKERS = 10 # Limit pattern check threads

def write_to_file(filename, content):
    """Thread-safe file writing function"""
    try:
        with file_lock:
            with open(filename, "a") as f:
                f.write(f"{content}\n")
    except Exception as e:
        print(f"File writing error: {str(e)}")

def verify_rtsp_stream(url, auth=None):
    """Verify if RTSP stream is actually working using OpenCV"""
    try:
        if auth:
            url = url.replace("rtsp://", f"rtsp://{auth[0]}:{auth[1]}@")
        
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5 second timeout

        if not cap.isOpened():
            return False
            
        ret, frame = cap.read()
        cap.release()
        
        return ret and frame is not None and frame.size > 0
    except:
        return False

def detect_vendor(response, url):
    """Detect vendor from response headers and content"""
    headers = response.headers
    content = response.text.lower()
    
    # Check server header
    server = headers.get('server', '').lower()
    
    # Check all vendor patterns
    for vendor, patterns in VENDOR_PATTERNS.items():
        # Check URL
        if any(pattern.lower() in url.lower() for pattern in patterns):
            return vendor
            
        # Check server header
        if any(pattern.lower() in server for pattern in patterns):
            return vendor
            
        # Check response content
        if any(pattern.lower() in content for pattern in patterns):
            return vendor
            
        # Check other headers
        for header in headers.values():
            if any(pattern.lower() in header.lower() for pattern in patterns):
                return vendor
                
    return 'general'

def check_rtsp(ip, port, pattern):
    try:
        with socket_semaphore:
            url = pattern.format(ip=ip, port=port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            result = sock.connect_ex((str(ip), port))
            sock.close()
            
            if result == 0:
                vendor = 'general'
                for v, patterns in VENDOR_PATTERNS.items():
                    if any(p.lower() in pattern.lower() for p in patterns):
                        vendor = v
                        break
                        
                auth_to_try = AUTH_COMBINATIONS[vendor] + AUTH_COMBINATIONS['general']
                
                # İç thread havuzu oluştur
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_AUTH_WORKERS) as auth_executor:
                    auth_futures = []
                    
                    # Önce auth olmadan dene
                    auth_futures.append(auth_executor.submit(verify_rtsp_stream, url, None))
                    
                    # Sonra auth kombinasyonlarını dene
                    for auth in auth_to_try:
                        auth_futures.append(auth_executor.submit(verify_rtsp_stream, url, auth))
                    
                    # Sonuçları kontrol et
                    for future in concurrent.futures.as_completed(auth_futures):
                        try:
                            result = future.result()
                            if result and url not in found_streams:
                                found_streams.add(url)
                                auth_idx = auth_futures.index(future) - 1  # -1 for None auth
                                auth = None if auth_idx < 0 else auth_to_try[auth_idx]
                                auth_str = f" (Auth: {auth[0]}:{auth[1]})" if auth else ""
                                print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                      f"Verified RTSP stream found: {url}{auth_str} [Vendor: {vendor}]" + colorama.Fore.RESET)
                                write_to_file("rtsp_streams.txt", f"{url} {auth_str} [Vendor: {vendor}]")
                                return url
                        except Exception:
                            continue
    except Exception as e:
        pass
    return None

def check_stream(ip, port, pattern):
    """HTTP stream kontrolü"""
    try:
        url = f"http://{ip}:{port}{pattern}"
        #print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking stream: {url}" + colorama.Fore.RESET)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'close'
        }

        # İlk kontrol - auth olmadan
        try:
            response = requests.get(
                url, 
                timeout=3, 
                headers=headers, 
                verify=False, 
                allow_redirects=True,
                stream=True
            )
            
            # Content-Type kontrolü
            content_type = response.headers.get('content-type', '').lower()
            is_stream = any([
                'video' in content_type,
                'mjpeg' in content_type,
                'multipart' in content_type,
                'stream' in content_type,
                'image' in content_type,
                'application/octet-stream' in content_type,
                'binary' in content_type,
                'application/x-motion-jpeg' in content_type,
                'application/x-rtsp' in content_type
            ])

            # Response kontrolü
            if response.status_code == 200:
                # Content-Type stream ise
                if is_stream:
                    try:
                        chunk = next(response.iter_content(chunk_size=8192))
                        if chunk and len(chunk) > 100 and "404" not in response.text:
                            if url not in found_streams:
                                found_streams.add(url)
                                print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                      f"Active HTTP stream found: {url}" + colorama.Fore.RESET)
                                write_to_file("live_streams.txt", f"{url}")
                                return url
                    except:
                        pass
                
                # URL'de stream göstergeleri varsa
                elif any(x in url.lower() for x in ['mjpg', 'mjpeg', 'video', 'stream', 'live', 'camera', 'cam']):
                    try:
                        chunk = next(response.iter_content(chunk_size=8192))
                        if chunk and len(chunk) > 100 and "404" not in response.text:
                            # JPEG/Image marker kontrolü
                            if any(marker in chunk for marker in [b'JFIF', b'Exif', b'PNG', b'GIF', b'JPEG', b'\xff\xd8']):
                                if url not in found_streams:
                                    found_streams.add(url)
                                    print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                          f"Active HTTP stream found: {url}" + colorama.Fore.RESET)
                                    write_to_file("live_streams.txt", f"{url}")
                                    return url
                    except:
                        pass

        except requests.exceptions.RequestException:
            pass

        # Auth gerektiren stream'ler için kontrol
        vendor = detect_vendor(response, url) if 'response' in locals() else 'general'
        auth_to_try = AUTH_COMBINATIONS[vendor] + AUTH_COMBINATIONS['general']

        for auth in auth_to_try[:3]:  # İlk 3 auth kombinasyonunu dene
            try:
                response = requests.get(
                    url, 
                    timeout=3,
                    headers=headers,
                    auth=auth,
                    verify=False,
                    allow_redirects=True,
                    stream=True
                )

                content_type = response.headers.get('content-type', '').lower()
                is_stream = any([
                    'video' in content_type,
                    'mjpeg' in content_type,
                    'multipart' in content_type,
                    'stream' in content_type,
                    'image' in content_type,
                    'application/octet-stream' in content_type,
                    'binary' in content_type
                ])

                if response.status_code == 200:
                    if is_stream:
                        try:
                            chunk = next(response.iter_content(chunk_size=8192))
                            if chunk and len(chunk) > 100:
                                if url not in found_streams:
                                    found_streams.add(url)
                                    auth_str = f" (Auth: {auth[0]}:{auth[1]})"
                                    print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                          f"Active HTTP stream found: {url}{auth_str}" + colorama.Fore.RESET)
                                    write_to_file("live_streams.txt", f"{url}{auth_str}")
                                    return url
                        except:
                            continue

            except requests.exceptions.RequestException:
                continue

    except Exception as e:
        pass
        
    return None

def check_port(ip, port):
    """Check if port is open using socket"""
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
    
    try:
        all_ports = list(set(COMMON_PORTS + RTSP_PORTS))
        open_ports = []
        
        # Check each port using socket
        for port in all_ports:
            if check_port(ip, port):
                open_ports.append(port)
                print(colorama.Fore.YELLOW + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Open port found: {ip}:{port}" + colorama.Fore.RESET)
        
        if open_ports:
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting stream detection for {ip}" + colorama.Fore.RESET)
            
            # Port başına thread havuzu oluştur
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(open_ports)) as port_executor:
                port_futures = []
                
                if open_ports[0] in RTSP_PORTS:
                    open_ports.reverse()
                    
                for port in open_ports:
                    # Her port için pattern'ları paralel tara
                    if port in COMMON_PORTS:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PATTERN_WORKERS) as pattern_executor:
                            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking HTTP stream: {ip}:{port}" + colorama.Fore.RESET)
                            pattern_futures = [
                                pattern_executor.submit(check_stream, ip, port, pattern)
                                for pattern in STREAM_PATTERNS
                            ]
                            port_futures.extend(pattern_futures)
                    
                    if port in RTSP_PORTS:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PATTERN_WORKERS) as pattern_executor:
                            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking RTSP stream: {ip}:{port}" + colorama.Fore.RESET)
                            pattern_futures = [
                                pattern_executor.submit(check_rtsp, ip, port, pattern)
                                for pattern in RTSP_PATTERNS
                            ]
                            port_futures.extend(pattern_futures)
                
                # Tüm sonuçları bekle
                for future in concurrent.futures.as_completed(port_futures):
                    try:
                        result = future.result()
                        if result:
                            break
                    except Exception:
                        continue
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Stream detection completed for {ip}" + colorama.Fore.RESET)
            
        with scan_lock:
            scanned_ips += 1
            progress = (scanned_ips / total_ips) * 100
            print(colorama.Fore.CYAN + f"\rScan progress: {progress:.2f}% ({scanned_ips}/{total_ips} IP)", end="")
            
    except Exception as e:
        print(f"IP tarama hatası {ip}: {str(e)}")

def worker():
    while True:
        try:
            ip = ip_queue.get_nowait()
            scan_ip(ip)
            ip_queue.task_done()
        except Empty:
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            continue

def extract_base_urls(filename):
    base_urls = set()
    try:
        with open(filename, 'r') as f:
            for line in f:
                url = line.strip()
                if url:
                    parsed = urlparse(url)
                    if parsed.netloc:
                        # Split IP address and port
                        netloc_parts = parsed.netloc.split(':')
                        ip = netloc_parts[0]
                        base_urls.add(ip)
    except Exception as e:
        print(f"URL file reading error: {str(e)}")
    return base_urls

def main():
    global total_ips
    
    parser = argparse.ArgumentParser(description='IP Camera Stream Scanner')
    parser.add_argument('--subnet', help='Subnet to scan (e.g: 192.168.1.0/24)')
    parser.add_argument('--url-file', help='URL file')
    parser.add_argument('--threads', type=int, default=MAX_WORKERS, help='Thread count')
    args = parser.parse_args()

    if not args.subnet and not args.url_file:
        print(colorama.Fore.RED + "Subnet or URL file must be provided!" + colorama.Fore.RESET)
        return

    ips_to_scan = set()

    try:
        if args.subnet:
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Loading subnet {args.subnet}" + colorama.Fore.RESET)
            network = ipaddress.ip_network(args.subnet)
            ips_to_scan.update(network.hosts())

        if args.url_file:
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Loading URLs from {args.url_file}" + colorama.Fore.RESET)
            base_urls = extract_base_urls(args.url_file)
            for ip in base_urls:
                try:
                    ipaddress.ip_address(ip)
                    ips_to_scan.add(ipaddress.ip_address(ip))
                except ValueError:
                    print(f"Invalid IP address: {ip}")

        total_ips = len(ips_to_scan)
        if total_ips == 0:
            print(colorama.Fore.RED + "No IP addresses to scan!" + colorama.Fore.RESET)
            return

        print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Scan starting: {total_ips} IP address with {args.threads} threads" + colorama.Fore.RESET)

        for ip in ips_to_scan:
            ip_queue.put(ip)

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            try:
                futures = [executor.submit(worker) for _ in range(min(args.threads, ip_queue.qsize()))]
                concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
            except KeyboardInterrupt:
                print("\nScan interrupted by user...")
                executor.shutdown(wait=False)
                return

        print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Scan completed. HTTP streams saved to live_streams.txt, RTSP streams saved to rtsp_streams.txt" + 
              colorama.Fore.RESET)
    
    except Exception as e:
        print(colorama.Fore.RED + f"Unexpected error: {str(e)}" + colorama.Fore.RESET)

if __name__ == "__main__":
    main()
