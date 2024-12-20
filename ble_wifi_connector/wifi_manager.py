__all__ = ['WiFiManager', 'validate_broker_address']


from ble_wifi_connector.utils import *

import subprocess
import asyncio
import re


def validate_broker_address(address: str) -> bool:
    pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')
    return bool(pattern.match(address))


class WiFiManager:
    def __init__(self, ssid: str = '', password: str = ''):
        self._ssid = ssid
        self._password = password
        self._connected = False
        self._logger = Logger().get_logger()

    @property
    def ssid(self) -> str:
        return self._ssid

    @ssid.setter
    def ssid(self, ssid: str) -> None:
        self._ssid = ssid

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, password: str) -> None:
        self._password = password

    def set_wifi(self, ssid: str, password: str) -> None:
        self._ssid = ssid
        self._password = password

    def get_connected_wifi_ssid(self) -> str:
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            active_connections = [line for line in result.stdout.split('\n') if line.startswith('yes:')]
            return active_connections[0].split(':')[1]
        except subprocess.CalledProcessError as e:
            self._logger.debug(f"Failed to get connected WiFi: {e}")
        return ''

    async def find_ssid(self, ssid: str, timeout: int = 10) -> bool:
        end_time = asyncio.get_event_loop().time() + timeout
        while True:
            process = await asyncio.create_subprocess_shell(
                "sudo nmcli dev wifi list --rescan yes", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if ssid in stdout.decode():
                self._logger.debug(f"Found SSID: {ssid}")
                return True
            elif asyncio.get_event_loop().time() > end_time:
                self._logger.debug("Timeout: SSID not found within the given time.")
                return False
            await asyncio.sleep(1)  # 잠시 대기 후 다시 시도합니다.

    async def connect_to(self, ssid: str, password: str) -> bool:
        try:
            await asyncio.create_subprocess_shell("nmcli --version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except OSError:
            self._logger.debug("nmcli is not installed. Please install NetworkManager to use this function.")
            return False

        ssid = ssid.strip()
        password = password.strip()

        # 현재 연결된 Wi-Fi SSID 확인
        current_ssid = await self.get_current_ssid()
        if current_ssid == ssid:
            self._logger.debug(f"Already connected to {ssid}. Skipping connection process.")
            return True

        ssid_found = await self.find_ssid(ssid)
        if not ssid_found:
            self._logger.debug(f"SSID {ssid} not found. Cannot attempt to connect.")
            return False

        connect_cmd = f'sudo nmcli dev wifi connect "{ssid}" password "{password}"'
        try:
            process = await asyncio.create_subprocess_shell(connect_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                self._logger.debug("WiFi connection attempt: success")
                return True
            else:
                self._logger.debug(f"WiFi connection attempt: failed\n{stderr.decode()}")
                return False
        except OSError as e:
            self._logger.debug(f"Error executing nmcli command: {e}")
            return False

    async def get_current_ssid(self) -> str:
        try:
            cmd = "nmcli -t -f active,ssid dev wifi | egrep '^yes:' | cut -d: -f2"
            process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                self._logger.debug(f"Error getting current SSID: {stderr.decode()}")
                return ""
        except OSError as e:
            self._logger.debug(f"Error executing nmcli command: {e}")
            return ""

    async def connect(self) -> bool:
        self._connected = await self.connect_to(self._ssid, self._password)
        return self._connected

    def check_connection(self) -> bool:
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            active_connections = [line for line in result.stdout.split('\n') if line.startswith('yes:')]
            if active_connections:
                if not self._connected:
                    self._logger.debug("WiFi connection status: connected")
                self._connected = True
                return True
            else:
                if self._connected:
                    self._logger.debug("WiFi connection status: not connected")
                self._connected = False
                return False
        except subprocess.CalledProcessError:
            self._logger.debug("Failed to check WiFi connection status")
            return False


if __name__ == '__main__':
    import asyncio

    logger = Logger().get_logger()

    async def ble_run():
        from big_thing_py.core.ble_advertiser import BLEAdvertiser

        ble_advertiser = BLEAdvertiser(server_name=f'JOI Hub {get_mac_address()}')
        await ble_advertiser.start()
        ssid, pw, broker, error_code = await ble_advertiser.wait_until_wifi_credentials_set()
        logger.debug(f'WiFi credentials set: ssid: {ssid}, pw: {pw}, broker: {broker}, error_code: {error_code}')
        await ble_advertiser.stop()
        return ssid, pw, broker, error_code

    async def wifi_run(ssid, pw):
        wifi_manager = WiFiManager(ssid, pw)
        logger.debug(f'current wifi: {wifi_manager.get_connected_wifi_ssid()}')
        await wifi_manager.connect_to(ssid, pw)
        logger.debug(f'current wifi: {wifi_manager.get_connected_wifi_ssid()}')

    ssid, pw, broker, error_code = asyncio.run(ble_run())
    asyncio.run(wifi_run(ssid, pw))
