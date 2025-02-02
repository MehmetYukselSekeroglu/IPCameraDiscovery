#! /usr/bin/env python3
# Licensed under the MIT License

import argparse
import socket
import struct
import ipaddress
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import time
from datetime import datetime
from colorama import Fore, Back, Style, init
import os
import urllib3
from bs4 import BeautifulSoup

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize colorama
init()

DEFAULT_PORT = 80 
DEFAULT_TIMEOUT = 5  # Increased timeout for more reliable detection
DEFAULT_PATHS = [
    "/doc/page/login.asp",  # Default Hikvision path
    "/ISAPI/Security/userCheck",  # Alternative login path
]
DEFAULT_PROTOCOL = "http"
DEFAULT_LOGIN_CREDENTIALS = [
    {"Username": "admin", "Password": "12345"},
    {"Username": "admin", "Password": "123456"}, 
    {"Username": "admin", "Password": "admin"},
    {"Username": "admin", "Password": ""},  # Empty password is common
    {"Username": "admin", "Password": "hikvision"},
]

HIKVISION_FINGERPRINTS = [
    "Hikvision",
    "DVRDVS-Webs",
    "DNVRS-Webs", 
    "App-webs",
    "WebServer",
    "ui/css/ui.css",  # Common Hikvision UI file
    "loginController",  # Hikvision login controller
    "seajs/seajs",  # Hikvision uses SeaJS
]

def log_success(result: Dict):
    with open("found_cameras.txt", "a") as f:
        f.write(f"{result['url']}\n")

def is_hikvision_device(response) -> bool:
    headers = response.headers
    content = response.text.lower()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for Hikvision-specific HTML elements
    hikvision_elements = [
        "#login",
        ".login-part",
        ".login-user", 
        ".icon-user",
        ".icon-pass",
        "#username",
        "#password",
        "#language_list",
        ".login-body",
        ".login-m",
        ".logindiv",
        ".loginbtn",
        "#seajsnode",
        ".login-error"
    ]
    
    for element in hikvision_elements:
        if soup.select(element):
            return True

    # Check for Hikvision fingerprints in text
    for fingerprint in HIKVISION_FINGERPRINTS:
        if fingerprint.lower() in response.text.lower():
            return True     
    
    # Check headers for Hikvision signatures
    for fingerprint in HIKVISION_FINGERPRINTS:
        if fingerprint.lower() in str(headers).lower():
            return True
            
    # Check content for Hikvision-specific elements
    hikvision_indicators = [
        "hikvision",
        "dvrdvs",
        "dnvrs", 
        "webdvr",
        "ipcam",
        "sea-config.js",
        "logincontroller",
        "login-body",
        "seajs/seajs",
        "ui/css/ui.css",
        "loginController",
        "ng-controller=\"loginController\"",
        "class=\"login-body\"",
        "id=\"language_list\""
    ]
    
    for indicator in hikvision_indicators:
        if indicator in content:
            return True
            
    return False

def scan_ip(ip: str, paths: List[str] = DEFAULT_PATHS, port: int = DEFAULT_PORT, timeout: int = DEFAULT_TIMEOUT) -> Dict:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for path in paths:
        try:
            url = f"{DEFAULT_PROTOCOL}://{ip}:{port}{path}"
            response = requests.get(url, timeout=timeout, verify=False)
            
            if response.status_code == 200 and is_hikvision_device(response):
                result = {
                    "ip": ip,
                    "status_code": response.status_code,
                    "url": url,
                    "device_type": "Hikvision"
                }
                
                # Try to extract model and firmware information
                try:
                    info_url = f"{DEFAULT_PROTOCOL}://{ip}:{port}/ISAPI/System/deviceInfo"
                    info_response = requests.get(info_url, timeout=timeout, verify=False)
                    if info_response.status_code == 200:
                        if "model" in info_response.text.lower():
                            result["model"] = info_response.text
                        if "firmwareVersion" in info_response.text.lower():
                            result["firmware"] = info_response.text
                except:
                    pass
                
                print(f"{Fore.GREEN}[{timestamp}] Success: Found Hikvision camera at {url}{Style.RESET_ALL}")
                log_success(result)
                return result
                
        except Exception as e:
            continue
            
    return None

def calculate_subnet(ip: str) -> str:
    try:
        ip_interface = ipaddress.ip_interface(ip)
        network = ip_interface.network
        return str(network)
    except ValueError as e:
        print(f"{Fore.RED}Invalid IP address: {e}{Style.RESET_ALL}")
        return None

def scan_subnet(ip_or_subnet: str, paths: List[str] = DEFAULT_PATHS, max_workers: int = 50) -> List[Dict]:
    if '/' not in ip_or_subnet:
        subnet = calculate_subnet(ip_or_subnet + '/24')
        if not subnet:
            return []
    else:
        subnet = ip_or_subnet

    network = ipaddress.ip_network(subnet)
    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"{Fore.CYAN}[{timestamp}] Starting Hikvision camera scan of subnet {subnet} with {max_workers} workers{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Total IPs to scan: {network.num_addresses - 2}{Style.RESET_ALL}")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(scan_ip, str(ip), paths) for ip in network.hosts()]
        completed = 0
        total = len(futures)
        for future in futures:
            result = future.result()
            completed += 1
            progress = (completed / total) * 100
            print(f"\rProgress: {progress:.1f}%", end="", flush=True)
            if result:
                results.append(result)
                print()  # New line after finding a camera
    
    print()  # New line after progress bar
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.CYAN}[{timestamp}] Scan completed. Found {len(results)} Hikvision cameras{Style.RESET_ALL}")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scan network for Hikvision IP cameras')
    parser.add_argument("--ip", type=str, required=True, help="IP address or subnet (e.g. 192.168.1.1 or 192.168.1.0/24)")
    parser.add_argument("--max_workers", type=int, default=50, help="Maximum number of concurrent workers")
    args = parser.parse_args()
    scan_subnet(args.ip, DEFAULT_PATHS, args.max_workers)