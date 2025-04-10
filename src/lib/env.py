
APPLICATION_AUTHOR = "Mehmet Yüksel Şekeroğlu"
APPLICATION_VERSION = "1.0.0"
APPLICATION_NAME = "Camera Identification Tool"

DEFAULT_PORTS = [80,  # HTTP
                 443,  # HTTPS
                 8080, # HTTP
                 8443, # HTTPS
                 37777, # Dahua
                 34567, # Hikvision
                 9001, # Axis
                 9002, # Axis
                 8899, # Mobotix
                 8899, # Vivotek
                 8000, # Avigilon
                 7001, # Arecont
                 8091, # Panasonic
                 8999, # Sony
                 8086  # Geovision
                ]
URL_PATHS = [
    "/doc/page/login.asp", # Hikvision
    "/", # Generic 
]
SUB_THREAD_COUNT = 10