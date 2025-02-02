#! /usr/bin/env python3
# Licensed under the MIT License

import argparse
import socket
import struct
import ipaddress
import threading
import requests
from typing import List, Dict
import time
from datetime import datetime
from colorama import Fore, Back, Style, init
import os
import urllib3
from bs4 import BeautifulSoup
from tqdm import tqdm

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize colorama
init()


DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_PORTS = [80] #, 81, 82, 83, 88, 443, 554, 8000, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 9000]
DEFAULT_TIMEOUT = 5
DEFAULT_PATHS = [
    "/",
    "/doc/page/login.asp",
    "/ISAPI/Security/userCheck",
    "/login.asp", 
    "/login.html",
    "/login",
    "/view/index.shtml",
    "/view/indexFrame.html",
    "/cgi-bin/webui",
    "/web/index.html",
    "/webadmin.html",
    "/doc/html/index.html",
    "/dvr/html",
    "/index.asp",
    "/index.htm",
    "/ipcam/index.asp",
    "/live/index.html",
    "/live.htm",
    "/camera"
]

CAMERA_FINGERPRINTS = [
    "Hikvision",
    "DVRDVS-Webs",
    "DNVRS-Webs",
    "App-webs",
    "WebServer",
    "Dahua",
    "DVR Components",
    "RTSP",
    "IPCamera",
    "Network Camera", 
    "IPC",
    "NVR",
    "DVR",
    "Axis",
    "Sony",
    "Panasonic",
    "Samsung",
    "Bosch",
    "Pelco",
    "Avigilon",
    "Arecont",
    "ACTi",
    "Vivotek",
    "Mobotix",
    "Geovision",
    "Foscam",
    "D-Link",
    "Trendnet",
    "Ubiquiti",
    "Amcrest",
    "Reolink",
    "Lorex",
    "Swann",
    "Uniview",
    "Tiandy",
    "TVT",
    "Kedacom",
    "Sunell",
    "Milesight"
]

def check_ip_port(ip: str, port: int, results: List) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = {"ip": ip, "port": port, "is_camera": False, "url": "", "confidence": 0}
    
    for path in DEFAULT_PATHS:
        try:
            for protocol in ["http", "https"]:
                url = f"{protocol}://{ip}:{port}{path}"
                response = requests.get(url, timeout=DEFAULT_TIMEOUT, verify=False, headers={"User-Agent": DEFAULT_USER_AGENT})
                
                # Check response headers and content
                headers = str(response.headers).lower()
                content = response.text.lower()
                
                # Increase confidence based on fingerprints
                for fingerprint in CAMERA_FINGERPRINTS:
                    if fingerprint.lower() in headers:
                        result["confidence"] += 2
                    if fingerprint.lower() in content:
                        result["confidence"] += 1
                        
                # Check for common camera HTML elements
                soup = BeautifulSoup(response.text, 'html.parser')
                camera_elements = [
                    "login", "username", "password", "channel", "preview", 
                    "playback", "ptz", "stream", "camera", "nvr", "dvr",
                    "ipcam", "videoin", "surveillance"
                ]
                
                for element in camera_elements:
                    if soup.find(id=element):
                        result["confidence"] += 2
                    if soup.find(class_=element):
                        result["confidence"] += 1

                # Check for video/streaming related elements
                if soup.find("video") or soup.find("object", type="application/x-vlc-plugin"):
                    result["confidence"] += 3

                # If confidence threshold met, mark as camera
                if result["confidence"] >= 4:
                    result["is_camera"] = True
                    result["url"] = url
                    print(f"{Fore.GREEN}[{timestamp}] Found camera at {url} (Confidence: {result['confidence']}){Style.RESET_ALL}")
                    results.append(result)
                    return
                        
        except requests.exceptions.RequestException:
            continue
        except Exception as e:
            print(f"{Fore.RED}[{timestamp}] Error checking {url}: {str(e)}{Style.RESET_ALL}")
            continue

def scan_subnet(subnet: str):
    network = ipaddress.ip_network(subnet)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.YELLOW}[{timestamp}] Scanning subnet {subnet}{Style.RESET_ALL}")
    
    results = []
    threads = []
    
    counter = 0 
    total_tasks = len(list(network.hosts())) * len(DEFAULT_PORTS)
    for ip in network.hosts():
        for port in DEFAULT_PORTS:
            thread = threading.Thread(target=check_ip_port, args=(str(ip), port, results))
            thread.daemon = True
            threads.append(thread)
            thread.start()
            
            counter += 1
            print(f"{Fore.YELLOW}[{timestamp}] Submitting {counter}/{total_tasks} tasks...{Style.RESET_ALL}", end="\r")
            # Limit concurrent threads
            while len([t for t in threads if t.is_alive()]) >= 100:
                time.sleep(0.1)
                
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Log found cameras
    with open("found_raw_cameras.txt", "a") as f:
        for result in results:
            if result["is_camera"]:
                f.write(f"{result['url']} (Confidence: {result['confidence']})\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="IP address or subnet to scan (e.g. 192.168.1.0/24)")
    args = parser.parse_args()
    
    try:
        # If single IP provided, convert to subnet
        if "/" not in args.target:
            ip = ipaddress.ip_address(args.target)
            subnet = f"{ip.network_address}/24"
        else:
            subnet = args.target
            
        scan_subnet(subnet)
        
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
