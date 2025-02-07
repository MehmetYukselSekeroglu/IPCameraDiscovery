import bs4
import re







CAMERA_IDENTIFIERS = {
    
    "hikvision_red_login_page":{
        "default_credentials":[
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "123456"},
            {"username": "admin", "password": "888888"}
        ],
        "css_selector": ".loginbg"
    },
    "hikvision_default_login_page":{
        "default_credentials":[
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "123456"},
            {"username": "admin", "password": "12345"},
            {"username": "admin", "password": "hikvision"},
            {"username": "admin", "password": "admin123"},
        ],
        "css_selector": ".login-part",
    },
    "hikvision_haikon_login_page":{
        "default_credentials":[
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "12345"},
            {"username": "admin", "password": "888888"}
        ],  
        "css_selector": ".loginbar",
    },
    "sanetron_login_page":{
        "default_credentials":[
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "12345"},
            {"username": "admin", "password": "888888"}
        ],
        "css_selector": ".loginingtip",
    },
    "dahura_xvr_login_page":{
        "default_credentials":[
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "123456"},
            {"username": "admin", "password": "888888"}
        ],
        "css_selector": "#image-1010-img",
    },
    "oinone_login_page":{
        "default_credentials":[
            {"username": "admin", "password": "admin"},
            {"username": "admin", "password": "12345"},
            {"username": "admin", "password": "888888"}
        ],
        "css_selector": "#content",
    }
}




def identify_camera(response_text: str) -> str:
    soup = bs4.BeautifulSoup(response_text, "html.parser")

    for single_camera_type in list(CAMERA_IDENTIFIERS.keys()):
        if soup.select(CAMERA_IDENTIFIERS[single_camera_type]["css_selector"]):
            return single_camera_type
    return None
