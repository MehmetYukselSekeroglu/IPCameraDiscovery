try:
    import sys
    import os
    import threading
    import time
    import numpy as np
    import socket
    import platform
    import ipaddress
    import requests
    import tkinter as tk
    from datetime import datetime
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QLineEdit, QPushButton, QGridLayout, QScrollArea, 
                                QFrame, QSplitter, QTextEdit, QComboBox, QTabWidget, QMessageBox,
                                QProgressBar, QGroupBox)
    from PyQt5.QtGui import QPixmap, QImage, QFont, QPalette, QColor, QIcon
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
except ImportError as e:
    import tkinter as tk
    root = tk.Tk()
    root.title("Eksik Paketler")
    root.geometry("400x200")
    
    label = tk.Label(root, text="Aşağıdaki paketleri yüklemeniz gerekiyor:", pady=10)
    label.pack()
    
    cmd = "pip install numpy PyQt5 requests opencv-python"
    cmd_label = tk.Label(root, text=f"Komut: {cmd}")
    cmd_label.pack()
    
    def copy_cmd():
        root.clipboard_clear()
        root.clipboard_append(cmd)
        
    copy_btn = tk.Button(root, text="Komutu Kopyala", command=copy_cmd)
    copy_btn.pack(pady=20)
    
    root.mainloop()
    sys.exit(1)

APP_NAME = "RTSP Viewer "
APP_VERSION = "1.0"
APP_AUTHOR = "IPCameraDiscovery"

class DarkTheme:
    BG_COLOR = "#121212"
    PANEL_COLOR = "#1E1E1E"
    ACCENT_COLOR = "#BB86FC"
    ERROR_COLOR = "#CF6679"
    SUCCESS_COLOR = "#03DAC5"
    TEXT_COLOR = "#FFFFFF"
    SECONDARY_TEXT = "#B0B0B0"
    BUTTON_COLOR = "#2D2D2D"
    BUTTON_HOVER = "#3D3D3D"
    BORDER_COLOR = "#333333"
    NUMERIC_COLOR = "#E0E0FF"  # Sayısal değerler için daha parlak renk

class RTSPStreamWorker(QThread):
    update_frame = pyqtSignal(np.ndarray)
    update_status = pyqtSignal(str, str)
    
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.running = True
        self.fps = 0
        self.last_time = time.time()
        self.frame_count = 0
    
    def run(self):
        import cv2
        try:
            cap = cv2.VideoCapture(self.url)
            if not cap.isOpened():
                self.update_status.emit("error", f"Bağlantı kurulamadı: {self.url}")
                return
                
            self.update_status.emit("success", f"Bağlantı başarılı: {self.url}")
            
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    self.update_status.emit("error", "Akış kesildi")
                    break
                
                self.frame_count += 1
                current_time = time.time()
                if (current_time - self.last_time) > 1.0:
                    self.fps = self.frame_count / (current_time - self.last_time)
                    self.frame_count = 0
                    self.last_time = current_time
                    self.update_status.emit("info", f"FPS: {self.fps:.2f}")
                
                self.update_frame.emit(frame)
                time.sleep(0.01)
                
            cap.release()
        except Exception as e:
            self.update_status.emit("error", f"Hata: {str(e)}")
    
    def stop(self):
        self.running = False
        #self.wait()

class IPInfoWorker(QThread):
    update_info = pyqtSignal(dict)
    
    def __init__(self, ip, parent=None):
        super().__init__(parent)
        self.ip = ip
    
    def run(self):
        info = {}
        try:
            info["ip"] = self.ip
            info["hostname"] = self.get_hostname(self.ip)
            info["os"] = platform.system()
            info["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            common_ports = [80, 443, 554, 8000, 8080, 8554, 8888, 9000, 9554]
            open_ports = []
            for port in common_ports:
                if self.check_port(self.ip, port):
                    open_ports.append(port)
            info["open_ports"] = open_ports
            
            try:
                response = requests.get(f"http://ip-api.com/json/{self.ip}", timeout=3)
                if response.status_code == 200:
                    geo_data = response.json()
                    if geo_data.get("status") == "success":
                        info["country"] = geo_data.get("country", "Bilinmiyor")
                        info["city"] = geo_data.get("city", "Bilinmiyor")
                        info["isp"] = geo_data.get("isp", "Bilinmiyor")
            except:
                pass
                
            self.update_info.emit(info)
        except Exception as e:
            info["error"] = str(e)
            self.update_info.emit(info)
    
    def get_hostname(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return "Bilinmiyor"
    
    def check_port(self, ip, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

class RTSPViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        
        # İkon varsa yükle
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.apply_dark_theme()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)  # Kenar boşluklarını ayarla
        self.main_layout.setSpacing(10)  # Widget'lar arası boşluk
        
        self.create_header()
        
        self.content_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.content_splitter, 1)
        
        # Video paneli oluştur
        self.video_panel = QWidget()
        self.video_layout = QVBoxLayout(self.video_panel)
        self.video_layout.setContentsMargins(5, 5, 5, 5)
        self.video_layout.setSpacing(8)
        self.create_video_panel()
        self.content_splitter.addWidget(self.video_panel)
        
        # Bilgi paneli oluştur
        self.info_panel = QWidget()
        self.info_layout = QVBoxLayout(self.info_panel)
        self.info_layout.setContentsMargins(5, 5, 5, 5)
        self.info_layout.setSpacing(8)
        self.create_info_panel()
        self.content_splitter.addWidget(self.info_panel)
        
        # Panellerin boyutlarını ayarla (video paneli daha geniş olsun)
        self.content_splitter.setSizes([700, 300])
        
        self.statusBar().showMessage("Hazır")
        
        self.stream_workers = {}
        self.stream_worker = None
        self.ip_info_worker = None
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
    
    def apply_dark_theme(self):
        app = QApplication.instance()
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(DarkTheme.BG_COLOR))
        palette.setColor(QPalette.WindowText, QColor(DarkTheme.TEXT_COLOR))
        palette.setColor(QPalette.Base, QColor(DarkTheme.PANEL_COLOR))
        palette.setColor(QPalette.AlternateBase, QColor(DarkTheme.BG_COLOR))
        palette.setColor(QPalette.ToolTipBase, QColor(DarkTheme.PANEL_COLOR))
        palette.setColor(QPalette.ToolTipText, QColor(DarkTheme.TEXT_COLOR))
        palette.setColor(QPalette.Text, QColor(DarkTheme.TEXT_COLOR))
        palette.setColor(QPalette.Button, QColor(DarkTheme.BUTTON_COLOR))
        palette.setColor(QPalette.ButtonText, QColor(DarkTheme.TEXT_COLOR))
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(DarkTheme.ACCENT_COLOR))
        palette.setColor(QPalette.Highlight, QColor(DarkTheme.ACCENT_COLOR))
        palette.setColor(QPalette.HighlightedText, QColor(DarkTheme.BG_COLOR))
        app.setPalette(palette)
        
        # Uygulama genelinde kullanılacak font ayarı
        app_font = QFont("Segoe UI", 10)  # Daha okunabilir bir font ve boyut
        app.setFont(app_font)
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {DarkTheme.BG_COLOR}; color: {DarkTheme.TEXT_COLOR}; }}
            QFrame, QGroupBox {{ 
                background-color: {DarkTheme.PANEL_COLOR}; 
                border: 1px solid {DarkTheme.BORDER_COLOR}; 
                border-radius: 4px; 
                padding: 8px;
            }}
            QPushButton {{ 
                background-color: {DarkTheme.BUTTON_COLOR}; 
                color: {DarkTheme.TEXT_COLOR}; 
                border: 1px solid {DarkTheme.BORDER_COLOR}; 
                border-radius: 4px; 
                padding: 5px 10px; 
                min-height: 25px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {DarkTheme.BUTTON_HOVER}; }}
            QPushButton:pressed {{ background-color: {DarkTheme.ACCENT_COLOR}; color: black; }}
            QLineEdit, QTextEdit, QComboBox {{ 
                background-color: {DarkTheme.BG_COLOR}; 
                color: {DarkTheme.TEXT_COLOR}; 
                border: 1px solid {DarkTheme.BORDER_COLOR}; 
                border-radius: 4px; 
                padding: 5px; 
                min-height: 20px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 10pt;
                font-weight: 500;
                letter-spacing: 0.5px;
            }}
            QTabWidget::pane {{ 
                border: 1px solid {DarkTheme.BORDER_COLOR}; 
                background-color: {DarkTheme.PANEL_COLOR}; 
                border-radius: 4px;
            }}
            QTabBar::tab {{ 
                background-color: {DarkTheme.BUTTON_COLOR}; 
                color: {DarkTheme.TEXT_COLOR}; 
                border: 1px solid {DarkTheme.BORDER_COLOR}; 
                padding: 6px 12px; 
                margin-right: 2px; 
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{ 
                background-color: {DarkTheme.ACCENT_COLOR}; 
                color: black; 
            }}
            QScrollBar {{ 
                background-color: {DarkTheme.BG_COLOR}; 
                width: 12px; 
                height: 12px; 
            }}
            QScrollBar::handle {{ 
                background-color: {DarkTheme.BUTTON_COLOR}; 
                border-radius: 6px; 
                min-height: 30px;
            }}
            QScrollBar::handle:hover {{ 
                background-color: {DarkTheme.BUTTON_HOVER}; 
            }}
            QLabel#title {{ 
                color: {DarkTheme.ACCENT_COLOR}; 
                font-size: 18px; 
                font-weight: bold; 
                padding: 5px;
            }}
            QLabel#subtitle {{ 
                color: {DarkTheme.SECONDARY_TEXT}; 
                font-size: 12px; 
                padding: 2px;
            }}
            QLabel#status_success {{ 
                color: {DarkTheme.SUCCESS_COLOR}; 
                padding: 2px;
                font-weight: 500;
            }}
            QLabel#status_error {{ 
                color: {DarkTheme.ERROR_COLOR}; 
                padding: 2px;
                font-weight: 500;
            }}
            QGroupBox {{
                font-weight: bold;
                margin-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            /* Sayısal değerler için özel stil */
            QLabel#numeric {{
                color: {DarkTheme.NUMERIC_COLOR};
                font-family: 'Consolas', 'Courier New', monospace;
                font-weight: bold;
                font-size: 11pt;
                letter-spacing: 0.8px;
            }}
            /* IP adresi ve port girişleri için özel stil */
            QLineEdit#numeric_input {{
                font-family: 'Consolas', 'Courier New', monospace;
                font-weight: bold;
                font-size: 11pt;
                letter-spacing: 0.8px;
                color: {DarkTheme.NUMERIC_COLOR};
            }}
        """)
    def create_header(self):
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_label = QLabel(APP_NAME)
        title_label.setObjectName("title")
        
        subtitle_label = QLabel(f"Sürüm {APP_VERSION} | {APP_AUTHOR}")
        subtitle_label.setObjectName("subtitle")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        self.time_label = QLabel()
        self.time_label.setObjectName("numeric")  # Sayısal stil uygula
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setMinimumWidth(180)  # Saat için biraz daha geniş alan
        header_layout.addWidget(self.time_label)
        
        self.main_layout.addWidget(header_frame)
    
    def create_video_panel(self):
        # Video gösterimi için frame
        self.video_frame = QLabel()
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setMinimumSize(640, 480)
        self.video_frame.setStyleSheet(f"background-color: black; border: 1px solid {DarkTheme.BORDER_COLOR};")
        self.video_frame.setText("Video yok")
        
        # Kontroller için layout
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setSpacing(10)
        
        # URL girişi
        url_layout = QVBoxLayout()
        url_layout.setSpacing(5)
        
        url_label = QLabel("RTSP URL:")
        url_label.setFixedHeight(20)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("rtsp://kullanıcı:şifre@ip:port/yol")
        self.url_input.setMinimumHeight(30)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        
        # Butonlar için layout
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)
        
        self.connect_btn = QPushButton("Bağlan")
        self.connect_btn.setMinimumHeight(30)
        self.connect_btn.clicked.connect(self.connect_to_stream)
        
        self.disconnect_btn = QPushButton("Bağlantıyı Kes")
        self.disconnect_btn.setMinimumHeight(30)
        self.disconnect_btn.clicked.connect(self.disconnect_stream)
        self.disconnect_btn.setEnabled(False)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        
        # Layoutları birleştir
        controls_layout.addLayout(url_layout, 3)  # URL kısmına daha fazla yer ayır
        controls_layout.addLayout(button_layout, 1)
        
        # Durum göstergesi
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 5, 5, 5)
        
        status_label = QLabel("Durum:")
        status_label.setFixedWidth(50)
        
        self.stream_status = QLabel("Hazır")
        self.stream_status.setObjectName("status_success")
        
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.stream_status, 1)
        
        # Ana layout'a ekle
        self.video_layout.addWidget(self.video_frame, 1)
        self.video_layout.addWidget(controls_frame)
        self.video_layout.addWidget(status_frame)
    
    def create_info_panel(self):
        tabs = QTabWidget()
        tabs.setDocumentMode(True)  # Daha modern görünüm
        
        # Bağlantı sekmesi
        connection_tab = QWidget()
        connection_layout = QVBoxLayout(connection_tab)
        connection_layout.setContentsMargins(8, 8, 8, 8)
        connection_layout.setSpacing(10)
        
        # Hızlı bağlantı grubu
        quick_connect_group = QGroupBox("Hızlı Bağlantı")
        quick_connect_layout = QGridLayout(quick_connect_group)
        quick_connect_layout.setContentsMargins(10, 15, 10, 10)
        quick_connect_layout.setSpacing(8)
        quick_connect_layout.setVerticalSpacing(10)
        
        # IP Adresi
        ip_label = QLabel("IP Adresi:")
        self.ip_input = QLineEdit()
        self.ip_input.setObjectName("numeric_input")  # Sayısal stil uygula
        self.ip_input.setMinimumHeight(25)
        quick_connect_layout.addWidget(ip_label, 0, 0)
        quick_connect_layout.addWidget(self.ip_input, 0, 1)
        
        # Port
        port_label = QLabel("Port:")
        self.port_input = QLineEdit("554")
        self.port_input.setObjectName("numeric_input")  # Sayısal stil uygula
        self.port_input.setMinimumHeight(25)
        quick_connect_layout.addWidget(port_label, 1, 0)
        quick_connect_layout.addWidget(self.port_input, 1, 1)
        
        # Kullanıcı adı
        username_label = QLabel("Kullanıcı Adı:")
        self.username_input = QLineEdit()
        self.username_input.setMinimumHeight(25)
        quick_connect_layout.addWidget(username_label, 2, 0)
        quick_connect_layout.addWidget(self.username_input, 2, 1)
        
        # Şifre
        password_label = QLabel("Şifre:")
        self.password_input = QLineEdit()
        self.password_input.setMinimumHeight(25)
        self.password_input.setEchoMode(QLineEdit.Password)
        quick_connect_layout.addWidget(password_label, 3, 0)
        quick_connect_layout.addWidget(self.password_input, 3, 1)
        
        # Yol
        path_label = QLabel("Yol:")
        self.path_input = QLineEdit()
        self.path_input.setMinimumHeight(25)
        self.path_input.setPlaceholderText("Örn: /Streaming/Channels/101")
        quick_connect_layout.addWidget(path_label, 4, 0)
        quick_connect_layout.addWidget(self.path_input, 4, 1)
        
        # Bağlan butonu - grid layoutta kendi satırına yerleştir
        quick_connect_btn = QPushButton("Bağlan")
        quick_connect_btn.setMinimumHeight(30)
        quick_connect_btn.clicked.connect(self.quick_connect)
        quick_connect_layout.addWidget(quick_connect_btn, 5, 0, 1, 2)
        
        # Yaygın kombinasyonlar grubu
        common_combos_group = QGroupBox("Yaygın Kombinasyonlar")
        common_combos_layout = QVBoxLayout(common_combos_group)
        common_combos_layout.setContentsMargins(10, 15, 10, 10)
        common_combos_layout.setSpacing(10)
        
        # Kombinasyon listesi
        self.combo_list = QComboBox()
        self.combo_list.setMinimumHeight(30)
        self.combo_list.addItems([
            "Hikvision: admin:12345",
            "Hikvision: admin:admin",
            "Dahua: admin:admin",
            "Dahua: admin:admin123",
            "Axis: root:pass",
            "Axis: admin:admin",
            "Samsung: admin:4321",
            "Samsung: admin:admin",
            "Sony: admin:admin",
            "Bosch: service:service",
            "Panasonic: admin:12345",
            "Vivotek: root:root",
            "Mobotix: admin:meinsm",
            "Arecont: admin:admin",
            "Uniview: admin:123456",
            "Geovision: admin:admin",
            "Trendnet: admin:admin"
        ])
        
        # Seçili kombinasyonu kullan butonu
        use_combo_btn = QPushButton("Seçili Kombinasyonu Kullan")
        use_combo_btn.setMinimumHeight(30)
        use_combo_btn.clicked.connect(self.use_selected_combo)
        
        common_combos_layout.addWidget(self.combo_list)
        common_combos_layout.addWidget(use_combo_btn)
        
        connection_layout.addWidget(quick_connect_group)
        connection_layout.addWidget(common_combos_group)
        connection_layout.addStretch()
        
        # IP Bilgileri sekmesi
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(10)
        
        self.ip_info_text = QTextEdit()
        self.ip_info_text.setReadOnly(True)
        
        get_info_btn = QPushButton("IP Bilgilerini Getir")
        get_info_btn.setMinimumHeight(30)
        get_info_btn.clicked.connect(self.get_ip_info)
        
        info_layout.addWidget(self.ip_info_text)
        info_layout.addWidget(get_info_btn)
        
        # Sekmeleri ekle
        tabs.addTab(connection_tab, "Bağlantı")
        tabs.addTab(info_tab, "IP Bilgileri")
        
        self.info_layout.addWidget(tabs)
    
    def update_time(self):
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.time_label.setText(current_time)
    
    def connect_to_stream(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Hata", "RTSP URL'si boş olamaz!")
            return
        
        self.disconnect_stream()
        
        try:
            # URL'den IP adresini çıkarmaya çalış
            parts = url.split("@")
            if len(parts) > 1:
                ip_part = parts[1].split("/")[0].split(":")[0]
            else:
                ip_part = parts[0].split("/")[2].split(":")[0]
            
            self.ip_input.setText(ip_part)
        except:
            pass
        
        self.stream_worker = RTSPStreamWorker(url)
        self.stream_worker.update_frame.connect(self.update_video_frame)
        self.stream_worker.update_status.connect(self.update_stream_status)
        self.stream_worker.start()
        
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.stream_status.setText("Bağlanıyor...")
        self.stream_status.setObjectName("status_success")
        self.stream_status.setStyleSheet("")
    
    def disconnect_stream(self):
        if hasattr(self, 'stream_worker') and self.stream_worker:
            self.stream_worker.stop()
            self.stream_worker = None
        
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.video_frame.setText("Video yok")
        self.video_frame.setPixmap(QPixmap())
        self.stream_status.setText("Bağlantı kesildi")
        self.stream_status.setObjectName("status_error")
        self.stream_status.setStyleSheet("")
    
    def update_video_frame(self, frame):
        import cv2
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_image)
        
        # Video frame'in mevcut boyutlarını al
        frame_width = self.video_frame.width()
        frame_height = self.video_frame.height()
        
        # Boyutlandırmayı oranı koruyarak yap
        pixmap = pixmap.scaled(frame_width, frame_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.video_frame.setPixmap(pixmap)
    
    def update_stream_status(self, status_type, message):
        if status_type == "error":
            self.stream_status.setObjectName("status_error")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
        elif status_type == "success":
            self.stream_status.setObjectName("status_success")
        elif status_type == "info":
            # FPS bilgisi için sayısal stil uygula
            self.stream_status.setObjectName("numeric")
        else:
            self.stream_status.setObjectName("")
        
        self.stream_status.setText(message)
        self.stream_status.setStyleSheet("")
    
    def quick_connect(self):
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        path = self.path_input.text().strip()
        
        if not ip:
            QMessageBox.warning(self, "Hata", "IP adresi boş olamaz!")
            return
        
        if username and password:
            url = f"rtsp://{username}:{password}@{ip}:{port}{path}"
        else:
            url = f"rtsp://{ip}:{port}{path}"
        
        self.url_input.setText(url)
        self.connect_to_stream()
    
    def use_selected_combo(self):
        combo_text = self.combo_list.currentText()
        try:
            credentials = combo_text.split(": ")[1]
            username, password = credentials.split(":")
            
            self.username_input.setText(username)
            self.password_input.setText(password)
            
            if self.ip_input.text().strip():
                self.quick_connect()
            else:
                QMessageBox.information(self, "Bilgi", "Lütfen önce bir IP adresi girin.")
            
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Kombinasyon ayrıştırılamadı: {str(e)}")
    
    def get_ip_info(self):
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Hata", "IP adresi boş olamaz!")
            return
        
        try:
            ipaddress.ip_address(ip)
            
            self.ip_info_text.setText("Bilgiler toplanıyor...")
            self.ip_info_worker = IPInfoWorker(ip)
            self.ip_info_worker.update_info.connect(self.display_ip_info)
            self.ip_info_worker.start()
            
        except ValueError:
            QMessageBox.warning(self, "Hata", "Geçersiz IP adresi!")
    
    def display_ip_info(self, info):
        if "error" in info:
            self.ip_info_text.setText(f"Hata: {info['error']}")
            return
        
        # HTML içinde sayısal değerler için özel stil tanımla
        text = f"""
        <style>
        .numeric {{
            color: {DarkTheme.NUMERIC_COLOR};
            font-family: 'Consolas', 'Courier New', monospace;
            font-weight: bold;
            letter-spacing: 0.8px;
        }}
        </style>
        <h3>IP Bilgileri</h3>
        <p><b>IP Adresi:</b> <span class="numeric">{info.get('ip', 'Bilinmiyor')}</span></p>
        <p><b>Hostname:</b> {info.get('hostname', 'Bilinmiyor')}</p>
        <p><b>İşletim Sistemi:</b> {info.get('os', 'Bilinmiyor')}</p>
        <p><b>Tarih/Saat:</b> <span class="numeric">{info.get('time', 'Bilinmiyor')}</span></p>
        
        <h3>Ağ Bilgileri</h3>
        <p><b>Açık Portlar:</b> <span class="numeric">{', '.join(map(str, info.get('open_ports', []))) or 'Bulunamadı'}</span></p>
        """
        
        if "country" in info:
            text += f"""
            <h3>Coğrafi Bilgiler</h3>
            <p><b>Ülke:</b> {info.get('country', 'Bilinmiyor')}</p>
            <p><b>Şehir:</b> {info.get('city', 'Bilinmiyor')}</p>
            <p><b>ISP:</b> {info.get('isp', 'Bilinmiyor')}</p>
            """
        
        self.ip_info_text.setHtml(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RTSPViewerApp()
    window.show()
    sys.exit(app.exec_())
