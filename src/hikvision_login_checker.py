#! /usr/bin/env python3
# Licensed under the MIT License

import argparse
import requests
import selenium
from datetime import datetime
from colorama import Fore, Back, Style, init
import os
import time

import selenium.webdriver
from selenium.webdriver.common.by import By
# Initialize colorama
init()

DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 10
DEFAULT_PATH = "/doc/page/login.asp"
DEFAULT_PROTOCOL = "http"
DEFAULT_LOGIN_CREDENTIALS_HIKVISION = [
    {"Username": "admin", "Password": "12345"},
    {"Username": "admin", "Password": "123456"}, 
    {"Username": "admin", "Password": "hikvision"},
]

DEFAULT_LOGIN_CREDENTIALS_NEUTRON = [
    {"Username": "admin", "Password": "12345"},
    {"Username": "admin", "Password": "123456"},
    {"Username": "admin", "Password": "admin"},
]







def main(args):
    
    with open(args.file, "r") as f:
        while True:
            try:
                line = f.readline()
                if not line:
                    break
            
                if line.strip() == "" or len(line.strip()) == 0:
                    print(f"{Fore.RED}[{timestamp}] Empty line, skipping{Style.RESET_ALL}")
                    continue
                
                url = line.strip()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"{Fore.YELLOW}[{timestamp}] Checking {url}{Style.RESET_ALL}")

                webdriver = selenium.webdriver.Chrome()
                webdriver.set_page_load_timeout(DEFAULT_TIMEOUT)
                webdriver.maximize_window()
                webdriver.get(url)
                time.sleep(2)    

                have_success = False

                is_default_hikvision = webdriver.find_elements(By.CSS_SELECTOR, "#login > table > tbody > tr > td.login-m > div")
                is_default_neutron = webdriver.find_elements(By.CSS_SELECTOR, "#login_body > div.login_fullPage.login_min_height_width > div.login_form")
                is_unknown_hikvision = webdriver.find_elements(By.CSS_SELECTOR, "#container > div.loginbg")


                if len(is_default_hikvision) != 0:
                    for credential in DEFAULT_LOGIN_CREDENTIALS_HIKVISION:
                        login_username = webdriver.find_element(By.ID, "username")
                        login_password = webdriver.find_element(By.ID, "password")
                        login_button__1 = webdriver.find_elements(By.CSS_SELECTOR, "#login > table > tbody > tr > td.login-m > div > div.login-item.bottom > button")
                        login_button__2 = webdriver.find_elements(By.CSS_SELECTOR, "#login > table > tbody > tr > td.login-m > div > div:nth-child(5) > button")

                        login_username.send_keys(credential["Username"])
                        login_password.send_keys(credential["Password"])


                        if len(login_button__1) != 0:
                            login_button = login_button__1[0]
                        elif len(login_button__2) != 0:
                            login_button = login_button__2[0]
                        else:
                            print(f"{Fore.RED}[{timestamp}] Error: No login button found{Style.RESET_ALL}")
                            continue
                        
                        login_button.click()

                        time.sleep(2)
                        error_message = webdriver.find_elements(By.CSS_SELECTOR, "#login > table > tbody > tr > td.login-m > div > div.login-error > div > label")
                        if len(error_message) == 0:
                            print(f"{Fore.GREEN}[{timestamp}] Success: Found camera at {url} (Username: {credential['Username']}, Password: {credential['Password']}){Style.RESET_ALL}")
                            have_success = True
                            break
                        webdriver.refresh()
                        time.sleep(2)

                elif len(is_default_neutron) != 0:
                    for credential in DEFAULT_LOGIN_CREDENTIALS_NEUTRON:
                        login_username = webdriver.find_element(By.ID, "szUserName")
                        login_password = webdriver.find_element(By.ID, "szUserPasswdSrc")
                        login_button = webdriver.find_element(By.CSS_SELECTOR, "#login > span.custom-btn-center.ellipsis.width70")

                        login_username.send_keys(credential["Username"])
                        login_password.send_keys(credential["Password"])
                        login_button.click()
                        time.sleep(2)
                        error_message = webdriver.find_elements(By.ID, "ErrorMsg")
                        if len(error_message) == 0:
                            print(f"{Fore.GREEN}[{timestamp}] Success: Found camera at {url} (Username: {credential['Username']}, Password: {credential['Password']}){Style.RESET_ALL}")
                            have_success = True
                            break
                        webdriver.refresh()
                        time.sleep(2)
                else:
                    print(f"{Fore.RED}[{timestamp}] Error: No default login page found{Style.RESET_ALL}")


                webdriver.quit()
            except Exception as e:
                print(f"{Fore.RED}[{timestamp}] Error Handling{Style.RESET_ALL}")
                webdriver.quit()
                continue
            
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True)
    args = parser.parse_args()
    main(args)