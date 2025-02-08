![Logo](../../img/logo.webp)

## Introduction

**IPCameraDiscovery** is a comprehensive tool developed to detect IP-based security cameras, check port statuses, and perform login attempts using default credentials.

This project combines test scenarios such as network scanning, port analysis, camera identification, and brute force attacks, offering cybersecurity professionals and penetration testers a fast and effective solution.

This document explains the project's fundamental principles, file structure, and usage in detail.

---

## Features

### 🔎 IP Scanning and Port Checking
- Scans a single IP, a subnet, or IP addresses listed in a file.
- Identifies active devices and their open ports.
- Analyzes HTTP responses by sending requests to ports.

### 👁 Camera Model Identification
- Detects camera models using CSS selectors in `lib/identify.py`.
- Recognizes popular brands such as Hikvision, HAIKON, Sanetron, and Longse.
- Monitors for brute force attempts tailored to the camera model.

### ⚡ Brute Force Attacks
- Performs login tests with default credentials using functions in `lib/bruteforce.py`.
- Attempts credentials specific to the detected camera model.
- Saves successful login attempts in the `found_devices.txt` file.

### 🛠 Headless Browser Usage
- Automates login tests using Selenium WebDriver.
- Operates the browser in headless mode.

### ⚙ Parallel Processing (Multi-threading)
- Accelerates network scanning using `threading` and `concurrent.futures`.
- Efficiently handles large ranges of IP addresses.

---

## Project Structure

- **main.py** → The main execution script. Sequentially performs scanning and brute force tasks.
- **lib/identify.py** → Identifies the camera model from HTTP responses.
- **lib/bruteforce.py** → Manages login attempts for different camera models.
- **lib/env.py** → Defines constants such as ports and URL paths.
- **lib/user_agent_tools.py** → Randomly selects User-Agent strings for HTTP requests.

---

## Usage

### 👀 Single IP Scan
```sh
python main.py --ip 192.168.1.100 --threads 10
```

### 🌍 Subnet Scan
```sh
python main.py --subnet 192.168.1.0/24 --threads 10
```

### 📃 File-based Scan
```sh
python main.py --file ip_list.txt --threads 10
```

---

## Operation Principle

1. **IP Scanning and Port Checking**: Devices are identified on the network and their open ports are scanned.
2. **Camera Identification**: Model information is extracted from HTTP responses.
3. **Brute Force Attempts**: Login tests tailored to the detected model are executed.
4. **Recording Results**: Successful credential attempts are logged.

---

## Requirements and Setup

- **Python Version**: Python 3.x
- **Required Packages:**
  ```sh
  pip install requests selenium beautifulsoup4 colorama
  ```
- **Additional Requirements:**
  - A compatible WebDriver (ChromeDriver, GeckoDriver, etc.) must be installed for Selenium.

---

## ⚠️ Security Warning

Use this tool only on systems where you have authorized access. Unauthorized access may lead to legal repercussions. All usage is your sole responsibility.

---

## 🌟 License and Contributions

This project is distributed under the MIT License.