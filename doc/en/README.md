 // Start Generation Here
![Logo](../../img/logo.webp)

# IPCameraDiscovery

IPCameraDiscovery is a Python-based tool developed to detect IP cameras on your network and specifically identify the presence of Hikvision devices. This tool performs subnet scanning to find potential cameras, conducts authentication checks, and filters the results.

## Features

- **Subnet Scanning**: Automatically scans devices within specified IP ranges.
- **Hikvision Device Detection**: Advanced control mechanisms to identify Hikvision brand IP cameras.
- **Automatic Authentication**: Attempts automatic logins to cameras using default username and password combinations.
- **Result Filtering**: Filters and records the results of found cameras.
- **Colored Console Outputs**: Uses colored console outputs for easy readability.

## Installation

1. **Python Installation**: The tool works with Python version 3.6 or higher. You can download Python from [python.org](https://www.python.org/downloads/).

2. **Installing Required Packages**:
    ```bash
    pip install -r requirements.txt
    ```

3. **WebDriver Installation**:
    The tool utilizes Selenium for scanning. You need to install **Chromedriver**. Download the appropriate version for your operating system from [Download Chromedriver](https://sites.google.com/chromium.org/driver/) and add it to your system PATH.

## Usage

### General IP Camera Discovery Tool

To perform a subnet scan:
```bash
python general_ip_camera_finder.py --target 192.168.1.0/24
```

### Hikvision Camera Scanning

To perform a scan specifically for Hikvision devices:
```bash
python scan_subnet_find_hikvision_cameras.py --ip 192.168.1.0/24 --max_workers 50
```

### Filtering Raw Data

To filter the raw data of found cameras:
```bash
python raw_filter.py --input found_cameras.txt --output filtered_cameras.txt
```

### Hikvision Login Control

To perform login checks on found Hikvision cameras:
```bash
python hikvision_login_checker.py --file filtered_cameras.txt
```

## Project Structure

- `general_ip_camera_finder.py`: General IP camera scanning operations.
- `scan_subnet_find_hikvision_cameras.py`: Specifically scans for Hikvision cameras.
- `raw_filter.py`: Filters raw scanning results.
- `hikvision_login_checker.py`: Attempts automatic logins to found Hikvision cameras.
- `requirements.txt`: List of required Python packages.
- `img/logo.webp`: Project logo.
- `doc/tr/README.md`: Turkish README file.
- `doc/en/README.md`: English README file.

## License

This project is licensed under the [MIT License](../../LICENSE).
