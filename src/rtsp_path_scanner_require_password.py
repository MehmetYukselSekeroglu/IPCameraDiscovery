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
    "rtsp://{ip}:{port}/onvif/profile",
    
    # ONVIF H264
    "rtsp://{ip}:{port}/h264_ulaw.sdp",
    "rtsp://{ip}:{port}/h264.sdp",
    "rtsp://{ip}:{port}/h264",
    "rtsp://{ip}:{port}/h264/media.amp",
    
    # General RTSP patterns
    "rtsp://{ip}:{port}/live",
    "rtsp://{ip}:{port}/1",
    "rtsp://{ip}:{port}/2", 
    "rtsp://{ip}:{port}/live/ch00_0",
    "rtsp://{ip}:{port}/live/ch01_0",
    "rtsp://{ip}:{port}/live/ch02_0",
    "rtsp://{ip}:{port}/live/main",
    "rtsp://{ip}:{port}/live/sub",
    "rtsp://{ip}:{port}/live/mobile",
    "rtsp://{ip}:{port}/11",
    "rtsp://{ip}:{port}/12",
    "rtsp://{ip}:{port}/13",
    "rtsp://{ip}:{port}/media/video1",
    "rtsp://{ip}:{port}/media/video2",
    "rtsp://{ip}:{port}/media/video3",
    "rtsp://{ip}:{port}/profile1",
    "rtsp://{ip}:{port}/profile2", 
    "rtsp://{ip}:{port}/profile3",
    "rtsp://{ip}:{port}/stream1",
    "rtsp://{ip}:{port}/stream2",
    "rtsp://{ip}:{port}/stream3",
    
    # Hikvision
    "rtsp://{ip}:{port}/Streaming/Channels/101",
    "rtsp://{ip}:{port}/Streaming/Channels/102",
    "rtsp://{ip}:{port}/Streaming/Channels/103",
    "rtsp://{ip}:{port}/Streaming/Channels/201",
    "rtsp://{ip}:{port}/Streaming/Channels/202",
    "rtsp://{ip}:{port}/h264/ch1/main/av_stream",
    "rtsp://{ip}:{port}/h264/ch1/sub/av_stream",
    "rtsp://{ip}:{port}/h264/ch2/main/av_stream",
    "rtsp://{ip}:{port}/h264/ch2/sub/av_stream",
    
    # Dahua
    "rtsp://{ip}:{port}/cam/realmonitor?channel=1&subtype=0",
    "rtsp://{ip}:{port}/cam/realmonitor?channel=1&subtype=1",
    "rtsp://{ip}:{port}/cam/realmonitor?channel=2&subtype=0",
    "rtsp://{ip}:{port}/cam/realmonitor?channel=2&subtype=1",
    "rtsp://{ip}:{port}/video1",
    "rtsp://{ip}:{port}/video2",
    "rtsp://{ip}:{port}/video3",
    
    # Axis
    "rtsp://{ip}:{port}/axis-media/media.amp",
    "rtsp://{ip}:{port}/mpeg4/media.amp",
    "rtsp://{ip}:{port}/axis-media/media.3gp",
    "rtsp://{ip}:{port}/axis-media/media.mp4",
    
    # Vivotek
    "rtsp://{ip}:{port}/live.sdp",
    "rtsp://{ip}:{port}/live1.sdp",
    "rtsp://{ip}:{port}/live2.sdp",
    "rtsp://{ip}:{port}/live3.sdp",
    "rtsp://{ip}:{port}/rtsp_tunnel",
    "rtsp://{ip}:{port}/video.3gp",
    
    # Bosch
    "rtsp://{ip}:{port}/rtsp_tunnel",
    "rtsp://{ip}:{port}/video1",
    "rtsp://{ip}:{port}/video2",
    "rtsp://{ip}:{port}/video3",
    "rtsp://{ip}:{port}/h264",
    "rtsp://{ip}:{port}/h264/stream1",
    
    # Panasonic
    "rtsp://{ip}:{port}/MediaInput/h264",
    "rtsp://{ip}:{port}/MediaInput/mpeg4",
    "rtsp://{ip}:{port}/nphMpeg4/nil-640x480",
    "rtsp://{ip}:{port}/nphMpeg4/nil-320x240",
    
    # Samsung
    "rtsp://{ip}:{port}/profile1/media.smp",
    "rtsp://{ip}:{port}/profile2/media.smp",
    "rtsp://{ip}:{port}/profile3/media.smp",
    
    # Sony
    "rtsp://{ip}:{port}/video1",
    "rtsp://{ip}:{port}/video2",
    "rtsp://{ip}:{port}/video3",
    
    # Mobotix
    "rtsp://{ip}:{port}/mobotix",
    "rtsp://{ip}:{port}/mobotix/stream",
    
    # ACTi
    "rtsp://{ip}:{port}/track1",
    "rtsp://{ip}:{port}/track2",
    "rtsp://{ip}:{port}/mpeg4/media.amp",
    
    # Arecont
    "rtsp://{ip}:{port}/h264",
    "rtsp://{ip}:{port}/mjpeg",
    
    # Pelco
    "rtsp://{ip}:{port}/stream1",
    "rtsp://{ip}:{port}/stream2",
    "rtsp://{ip}:{port}/stream3"
]

# Common usernames to try
USERNAMES = ['admin', 'root', '888888']

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

def verify_rtsp_stream_socket(url, username, password):
    """Verify RTSP stream using socket connection"""
    try:
        url = url.replace("rtsp://", f"rtsp://{username}:{password}@")
        
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

def verify_rtsp_stream_opencv(url, username, password):
    """Verify RTSP stream using OpenCV"""
    try:
        url = url.replace("rtsp://", f"rtsp://{username}:{password}@")
        
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

def check_rtsp(ip, port, pattern, password):
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
                    
                    # Try each username with provided password
                    for username in USERNAMES:
                        auth_futures.append(auth_executor.submit(verify_rtsp_stream_socket, url, username, password))
                    
                    # Check results
                    for future, username in zip(concurrent.futures.as_completed(auth_futures), USERNAMES):
                        try:
                            result = future.result()
                            if result:
                                # Socket connection successful, verify with OpenCV
                                if verify_rtsp_stream_opencv(url, username, password):
                                    if url not in found_streams:
                                        found_streams.add(url)
                                        auth_str = f" (Auth: {username}:{password})"
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

def scan_ip(ip, password):
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
                            pattern_executor.submit(check_rtsp, ip, port, pattern, password)
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
            if total_ips > 0:
                progress = (scanned_ips / total_ips) * 100
                print(colorama.Fore.CYAN + f"\rScan progress: {progress:.2f}% ({scanned_ips}/{total_ips} IP)", end="")
            
    except Exception as e:
        print(f"IP scan error {ip}: {str(e)}")

def worker(password):
    while True:
        try:
            ip = ip_queue.get_nowait()
            scan_ip(ip, password)
            ip_queue.task_done()
        except Empty:
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            continue

def scan_from_file(filename, password):
    global total_ips
    try:
        with open(filename, 'r') as f:
            ips = [line.strip() for line in f if line.strip()]
        
        total_ips = len(ips)
        for ip in ips:
            ip_queue.put(ip)
            
        # Start worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker, password) for _ in range(min(MAX_WORKERS, len(ips)))]
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
    parser.add_argument('--password', required=True, help='Password to try')
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
                futures = [executor.submit(worker, args.password) for _ in range(min(args.threads, total_ips))]
                concurrent.futures.wait(futures)
                
        elif args.ip:
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Starting scan of IP {args.ip}" + colorama.Fore.RESET)
            scan_ip(args.ip, args.password)
            
        else:  # args.file
            print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Starting scan of IPs from file {args.file}" + colorama.Fore.RESET)
            scan_from_file(args.file, args.password)

        print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Scan completed. RTSP streams saved to rtsp_streams.txt" + colorama.Fore.RESET)
    
    except KeyboardInterrupt:
        print("\nScan interrupted by user...")
    except Exception as e:
        print(colorama.Fore.RED + f"Unexpected error: {str(e)}" + colorama.Fore.RESET)

if __name__ == "__main__":
    main()
