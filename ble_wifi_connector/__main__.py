from ble_wifi_connector.utils import *

import asyncio
from enum import Enum, auto

from ble_wifi_connector.ble_advertiser import BLEAdvertiser, BLEErrorCode
from ble_wifi_connector.wifi_manager import WiFiManager
from termcolor import cprint, colored
import json
import subprocess


EVENT_LOOP_TIME_OUT = 0.01
CONNECT_RETRY = 3
MATTER_CONFIG_PATH = '/usr/local/joi/plugins/matter_manager/config.json'


class BLEWiFiConnectorState(Enum):
    RESET = auto()
    BLE_ADVERTISE = auto()
    NETWORK_SETUP = auto()
    NETWORK_CONNECTED = auto()
    NETWORK_LOST = auto()
    NETWORK_RECONNECTED = auto()
    SHUTDOWN = auto()


async def main_event_loop():
    connect_try = CONNECT_RETRY
    state = BLEWiFiConnectorState.RESET
    ble_advertiser = BLEAdvertiser(server_name=f'JOI Hub {get_mac_address()}')
    wifi_manager = WiFiManager()
    logger = Logger().get_logger()

    ssid = ''
    pw = ''

    def set_matter_config(dataset: str = '') -> None:
        try:
            with open(MATTER_CONFIG_PATH, 'r') as config_file:
                config = json.load(config_file)
                config['ssid'] = wifi_manager.ssid
                config['password'] = wifi_manager.password
                config['dataset'] = dataset
            with open(MATTER_CONFIG_PATH, 'w') as config_file:
                json.dump(config, config_file, indent=4)
            logger.debug(colored(f'Matter config loaded. SSID: {wifi_manager.ssid}', 'green'))
        except Exception as e:
            logger.debug(colored(f'Error reading config file: {e}', 'red'))

    def restart_service(service_name: str) -> None:
        try:
            subprocess.run(["sudo", "service", service_name, "restart"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logger.debug(colored(f"Service '{service_name}' restarted successfully.", "green"))
        except subprocess.CalledProcessError as e:
            logger.debug(colored(f"Failed to restart service '{service_name}'. Error: {e.stderr}", "red"))

    while True:
        try:
            await asyncio.sleep(EVENT_LOOP_TIME_OUT * 100)

            if state == BLEWiFiConnectorState.RESET:
                state = BLEWiFiConnectorState.BLE_ADVERTISE
            elif state == BLEWiFiConnectorState.BLE_ADVERTISE:
                # BLE Advertise
                await ble_advertiser.start()
                if not await ble_advertiser.is_advertising():
                    logger.debug(colored(f'BLE Advertiser start failed...', 'red'))
                    await ble_advertiser.stop()
                    state = BLEWiFiConnectorState.RESET
                    continue

                # Save WiFi, Broker info
                logger.debug(colored(f'Wait for WiFi credentials from BLE...', 'yellow'))
                wifi_credential = await ble_advertiser.wait_until_wifi_credentials_set(timeout=None)
                ssid = wifi_credential[0]
                pw = wifi_credential[1]
                error = wifi_credential[2]

                if error != BLEErrorCode.NO_ERROR:
                    logger.debug(colored(f'Something getting wrong while BLE setup! error code: {error}', 'red'))
                    await ble_advertiser.stop()
                    state = BLEWiFiConnectorState.RESET
                    continue

                await ble_advertiser.stop()
                state = BLEWiFiConnectorState.NETWORK_SETUP
            elif state == BLEWiFiConnectorState.NETWORK_SETUP:
                # WiFi Connect
                wifi_manager.set_wifi(ssid=ssid, password=pw)
                await wifi_manager.connect()
                if wifi_manager.check_connection():
                    logger.debug(colored(f'WiFi connection success. SSID: {wifi_manager.get_connected_wifi_ssid()}', 'green'))
                    state = BLEWiFiConnectorState.NETWORK_CONNECTED
                else:
                    if connect_try > 0:
                        logger.debug(colored(f'Connect to SSID {wifi_manager.ssid} failed... (try: {connect_try})', 'yellow'))
                        connect_try -= 1
                        state = BLEWiFiConnectorState.NETWORK_SETUP
                    else:
                        logger.debug(colored(f'WiFi connection failed... Go back to BLE setup.', 'red'))
                        connect_try = CONNECT_RETRY
                        state = BLEWiFiConnectorState.RESET

                set_matter_config()
                restart_service("MatterManager")
            elif state == BLEWiFiConnectorState.NETWORK_CONNECTED:
                if not wifi_manager.check_connection():
                    logger.debug(colored(f'WiFi connection lost...', 'yellow'))
                    state = BLEWiFiConnectorState.NETWORK_LOST
            elif state == BLEWiFiConnectorState.NETWORK_LOST:
                if not ssid == '' and not pw == '':
                    state = BLEWiFiConnectorState.NETWORK_SETUP
                else:
                    state = BLEWiFiConnectorState.RESET
            elif state == BLEWiFiConnectorState.SHUTDOWN:
                if await ble_advertiser.is_advertising():
                    await ble_advertiser.stop()

                return 0
        except asyncio.CancelledError:
            logger.debug("main_event_loop cancelled")
            state = BLEWiFiConnectorState.SHUTDOWN
        except KeyboardInterrupt:
            logger.debug("main_event_loop cancelled")
            state = BLEWiFiConnectorState.SHUTDOWN


if __name__ == "__main__":
    asyncio.run(main_event_loop())
