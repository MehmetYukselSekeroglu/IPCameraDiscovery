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
    "rtsp://{ip}:{port}/1",
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
    "rtsp://{ip}:{port}/nphMpeg4/nil-640x480"
]

# Common auth combinations
AUTH_COMBINATIONS = [
    ('admin', 'admin'),
    ('admin', ''),
    ('admin', '12345'),
    ('admin', 'password'),
    ('root', 'root'),
    ('admin', '123456'),
    ('admin', '9999'),
    ('admin', 'camera'),
    ('admin', '1234'),
    ('admin', 'system'),
    ('admin', 'admin12345'),
    ('admin', 'Admin12345'),
    ('admin', 'hikvision'),
    ('admin', 'hik12345'),
    ('888888', '888888'),
    ('admin', 'dahua'),
    ('admin', 'dh123456'),
    ('root', 'pass'),
    ('admin', 'axis2023'),
    ('root', 'axis'),
    ('admin', 'axis123')
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

def verify_rtsp_stream_socket(url, auth=None):
    """Verify RTSP stream using socket connection"""
    try:
        if auth:
            url = url.replace("rtsp://", f"rtsp://{auth[0]}:{auth[1]}@")
        
        # Parse URL
        url = url.replace("rtsp://", "")
        if "@" in url:
            url = url.split("@")[1]
        host = url.split("/")[0]
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        else:
            port = 554
            
        # Try socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0
        
    except:
        return False

def verify_rtsp_stream_opencv(url, auth=None):
    """Verify RTSP stream using OpenCV"""
    try:
        if auth:
            url = url.replace("rtsp://", f"rtsp://{auth[0]}:{auth[1]}@")
        
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        if not cap.isOpened():
            return False
            
        ret, frame = cap.read()
        cap.release()
        
        return ret and frame is not None and frame.size > 0
    except:
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
                    auth_futures.append(auth_executor.submit(verify_rtsp_stream_socket, url, None))
                    
                    # Then try auth combinations
                    for auth in AUTH_COMBINATIONS:
                        auth_futures.append(auth_executor.submit(verify_rtsp_stream_socket, url, auth))
                    
                    # Check results
                    for future in concurrent.futures.as_completed(auth_futures):
                        try:
                            result = future.result()
                            if result:
                                # Socket connection successful, verify with OpenCV
                                auth_idx = auth_futures.index(future) - 1
                                auth = None if auth_idx < 0 else AUTH_COMBINATIONS[auth_idx]
                                
                                if verify_rtsp_stream_opencv(url, auth):
                                    if url not in found_streams:
                                        found_streams.add(url)
                                        auth_str = f" (Auth: {auth[0]}:{auth[1]})" if auth else ""
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
                        pattern_futures = [
                            pattern_executor.submit(check_rtsp, ip, port, pattern)
                            for pattern in RTSP_PATTERNS
                        ]
                        
                        # Wait for first successful result or all to complete
                        for future in concurrent.futures.as_completed(pattern_futures):
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

def main():
    global total_ips
    
    parser = argparse.ArgumentParser(description='RTSP Stream Scanner')
    parser.add_argument('--subnet', required=True, help='Subnet to scan (e.g: 192.168.1.0/24)')
    parser.add_argument('--threads', type=int, default=MAX_WORKERS, help='Thread count')
    args = parser.parse_args()

    try:
        network = ipaddress.ip_network(args.subnet)
        total_ips = network.num_addresses - 2  # Exclude network and broadcast addresses
        
        print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Starting scan of {total_ips} IPs in subnet {args.subnet}" + colorama.Fore.RESET)

        # Add IPs to queue
        for ip in network.hosts():
            ip_queue.put(str(ip))

        # Start worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            try:
                futures = [executor.submit(worker) for _ in range(min(args.threads, ip_queue.qsize()))]
                concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
            except KeyboardInterrupt:
                print("\nScan interrupted by user...")
                executor.shutdown(wait=False)
                return

        print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Scan completed. RTSP streams saved to rtsp_streams.txt" + colorama.Fore.RESET)
    
    except Exception as e:
        print(colorama.Fore.RED + f"Unexpected error: {str(e)}" + colorama.Fore.RESET)

if __name__ == "__main__":
    main()