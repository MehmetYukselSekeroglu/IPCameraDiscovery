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

# Increase system limits for open files
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))

# Hide OpenCV and RTSP warnings/errors
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
logging.getLogger("cv2").setLevel(logging.CRITICAL)
logging.getLogger("libav").setLevel(logging.CRITICAL)
logging.getLogger("rtsp").setLevel(logging.CRITICAL)

# Hide RTSP error messages
cv2.setLogLevel(0)

colorama.init()

# RTSP ports
RTSP_PORTS = [554, 8554, 10554]

# RTSP URL patterns (top 10)
RTSP_PATTERNS = [
    "rtsp://{ip}:{port}/live/ch00_0",
    "rtsp://{ip}:{port}/live/ch01_0",
    "rtsp://{ip}:{port}/1",
    "rtsp://{ip}:{port}/live/main",
    "rtsp://{ip}:{port}/live/sub",
    "rtsp://{ip}:{port}/11",
    "rtsp://{ip}:{port}/12",
    "rtsp://{ip}:{port}/h264_ulaw.sdp",
    "rtsp://{ip}:{port}/h264.sdp",
    "rtsp://{ip}:{port}/Streaming/Channels/101",
    "rtsp://{ip}:{port}/                    ",
]

# Common auth combinations (top 5)
AUTH_COMBINATIONS = [
    ('admin', 'admin'),
    ('admin', ''),
    ('admin', '12345'),
    ('admin', '123456'),
    ('admin', '1234567'),
    ('admin', '12345678'),
    ('admin', '123456789'),
    ('admin', '1234567890'),
    
]

# Global variables
total_ips = 0
scanned_ips = 0
scan_lock = threading.Lock()
found_streams = set()
file_lock = threading.Lock()
ip_queue = Queue()
socket_semaphore = threading.BoundedSemaphore(1000)

SOCKET_TIMEOUT = 5
MAX_WORKERS = 50
MAX_AUTH_WORKERS = 5

def write_to_file(filename, content):
    """Thread-safe file writing function"""
    try:
        with file_lock:
            with open(filename, "a") as f:
                f.write(f"{content}\n")
    except Exception as e:
        print(f"File writing error: {str(e)}")

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
    try:
        with socket_semaphore:
            url = pattern.format(ip=ip, port=port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(SOCKET_TIMEOUT)
            result = sock.connect_ex((str(ip), port))
            sock.close()
            
            if result == 0:
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_AUTH_WORKERS) as auth_executor:
                    auth_futures = []
                    
                    # Try without auth first
                    auth_futures.append(auth_executor.submit(verify_rtsp_stream_rtsp, url, None))
                    
                    # Then try auth combinations
                    for auth in AUTH_COMBINATIONS:
                        auth_futures.append(auth_executor.submit(verify_rtsp_stream_rtsp, url, auth))
                    
                    # Check results
                    for future in concurrent.futures.as_completed(auth_futures):
                        try:
                            if future.result():
                                auth_idx = auth_futures.index(future) - 1
                                auth_used = None if auth_idx < 0 else AUTH_COMBINATIONS[auth_idx]
                                
                                if url not in found_streams:
                                    found_streams.add(url)
                                    auth_str = f" (Auth: {auth_used[0]}:{auth_used[1]})" if auth_used else ""
                                    print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                          f"Verified RTSP stream found: {url}{auth_str}" + colorama.Fore.RESET)
                                    write_to_file("rtsp_streams.txt", f"{url}{auth_str}")
                                    return True
                        except Exception:
                            continue
    except Exception as e:
        pass
    return False

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
        open_ports = []
        
        # Check RTSP ports
        for port in RTSP_PORTS:
            if check_port(ip, port):
                open_ports.append(port)
                print(colorama.Fore.YELLOW + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Open RTSP port found: {ip}:{port}" + colorama.Fore.RESET)
        
        if open_ports:
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting RTSP detection for {ip}" + colorama.Fore.RESET)
            
            # Create thread pool per port
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(open_ports)) as port_executor:
                port_futures = []
                
                for port in open_ports:
                    # Check patterns in parallel for each port
                    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pattern_executor:
                        pattern_futures = []
                        for pattern in RTSP_PATTERNS:
                            future = pattern_executor.submit(check_rtsp, ip, port, pattern)
                            pattern_futures.append(future)
                            
                            # Check if stream found
                            try:
                                if future.result():
                                    # Stream found, stop checking other patterns
                                    pattern_executor.shutdown(wait=False)
                                    return
                            except Exception:
                                continue
                                
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] RTSP detection completed for {ip}" + colorama.Fore.RESET)
            
        with scan_lock:
            scanned_ips += 1
            if total_ips > 0:
                progress = (scanned_ips / total_ips) * 100
                print(colorama.Fore.CYAN + f"\rScan progress: {progress:.2f}% ({scanned_ips}/{total_ips} IP)", end="")
            
    except Exception as e:
        print(f"IP scan error {ip}: {str(e)}")

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

def scan_from_file(filename):
    global total_ips
    try:
        with open(filename, 'r') as f:
            ips = [line.strip() for line in f if line.strip()]
        
        total_ips = len(ips)
        for ip in ips:
            ip_queue.put(ip)
            
        # Start worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker) for _ in range(min(MAX_WORKERS, len(ips)))]
            concurrent.futures.wait(futures)
            
    except Exception as e:
        print(f"File reading error: {str(e)}")

def main():
    global total_ips
    
    parser = argparse.ArgumentParser(description='RTSP Stream Scanner')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--subnet', help='Subnet to scan (e.g: 192.168.1.0/24)')
    group.add_argument('--ip', help='Single IP to scan')
    group.add_argument('--file', help='File containing IPs to scan (one per line)')
    parser.add_argument('--threads', type=int, default=MAX_WORKERS, help='Thread count')
    args = parser.parse_args()

    try:
        if args.subnet:
            network = ipaddress.ip_network(args.subnet)
            total_ips = network.num_addresses - 2  # Exclude network and broadcast addresses
            
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Starting scan of {total_ips} IPs in subnet {args.subnet}" + colorama.Fore.RESET)

            # Add IPs to queue
            for ip in network.hosts():
                ip_queue.put(str(ip))

            # Start worker threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = [executor.submit(worker) for _ in range(min(args.threads, total_ips))]
                concurrent.futures.wait(futures)
                
        elif args.ip:
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Starting scan of IP {args.ip}" + colorama.Fore.RESET)
            scan_ip(args.ip)
            
        else:  # args.file
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Starting scan of IPs from file {args.file}" + colorama.Fore.RESET)
            scan_from_file(args.file)

        print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Scan completed. RTSP streams saved to rtsp_streams.txt" + colorama.Fore.RESET)
    
    except KeyboardInterrupt:
        print("\nScan interrupted by user...")
    except Exception as e:
        print(colorama.Fore.RED + f"Unexpected error: {str(e)}" + colorama.Fore.RESET)

if __name__ == "__main__":
    main()