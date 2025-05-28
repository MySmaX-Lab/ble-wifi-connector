__all__ = ['get_mac_address', 'Logger']


import os
import getmac
import logging
import threading
import subprocess
import re


def get_wifi_mac_address():
    mac_address = getmac.get_mac_address()
    return mac_address


def get_ble_mac_address() -> str:
    try:
        output = subprocess.check_output(['hciconfig']).decode('utf-8')
        matches = re.findall(r'BD Address: ([0-9A-F:]+)', output)
        if matches:
            return matches[0]
        else:
            return None
    except Exception as e:
        print("에러 발생: ", e)
        return None


def get_mac_address(ble: bool = True) -> str:
    if ble:
        mac_address = get_ble_mac_address()
    else:
        mac_address = get_wifi_mac_address()

    if mac_address:
        mac_address = mac_address.replace(':', '').upper()
        return mac_address
    else:
        return None


class Logger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, name: str = "MyLogger", log_file: str = "./log/ble_wifi_manager.log", level=logging.DEBUG):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Logger, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, name: str = "MyLogger", log_file: str = "./log/ble_wifi_manager.log", level=logging.DEBUG):
        if self._initialized:
            return

        log_dir = os.path.dirname(log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 콘솔 핸들러 생성
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # 파일 핸들러 생성
        file_handler = logging.FileHandler(
            log_file,
        )
        file_handler.setLevel(level)

        # 포맷터 생성
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # 핸들러를 로거에 추가
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        self._initialized = True

    def get_logger(self):
        return self.logger
