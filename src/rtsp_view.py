import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                            QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

class RTSPThread(QThread):
    frame_signal = pyqtSignal(QImage)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = True
        
    def run(self):
        import cv2
            
        cap = cv2.VideoCapture(self.url)
        while self.running:
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.frame_signal.emit(qt_image)
        cap.release()
        
    def stop(self):
        self.running = False

class RTSPViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.rtsp_thread = None
        
    def initUI(self):
        self.setWindowTitle('RTSP Stream Viewer')
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create input fields
        input_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('RTSP URL')
        input_layout.addWidget(self.url_input)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Username')
        input_layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Password')
        self.password_input.setEchoMode(QLineEdit.Password)
        input_layout.addWidget(self.password_input)
        
        layout.addLayout(input_layout)
        
        # Create buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton('Start')
        self.start_button.clicked.connect(self.start_stream)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop_stream)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        
        # Create video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label)
        
    def start_stream(self):
        url = self.url_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        
        if username and password:
            # Insert credentials into URL
            parsed_url = url.split('://')
            url = f"{parsed_url[0]}://{username}:{password}@{parsed_url[1]}"
            
        self.rtsp_thread = RTSPThread(url)
        self.rtsp_thread.frame_signal.connect(self.update_frame)
        self.rtsp_thread.start()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def stop_stream(self):
        if self.rtsp_thread:
            self.rtsp_thread.stop()
            self.rtsp_thread.wait()
            self.rtsp_thread = None
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.video_label.clear()
        
    def update_frame(self, qt_image):
        scaled_image = qt_image.scaled(self.video_label.size(), Qt.KeepAspectRatio)
        self.video_label.setPixmap(QPixmap.fromImage(scaled_image))
        
    def closeEvent(self, event):
        self.stop_stream()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = RTSPViewer()
    viewer.show()
    sys.exit(app.exec_())
