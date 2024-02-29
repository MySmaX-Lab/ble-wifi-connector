import subprocess
import asyncio

from big_thing_py.utils import *


def validate_broker_address(address: str) -> bool:
    pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$')
    return bool(pattern.match(address))


class WiFiManager:
    def __init__(self, ssid: str = '', password: str = ''):
        self._ssid = ssid
        self._password = password

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
            MXLOG_DEBUG(f"Failed to get connected WiFi: {e}")
        return ''

    async def find_ssid(self, ssid: str, timeout: int = 10) -> bool:
        end_time = asyncio.get_event_loop().time() + timeout
        while True:
            process = await asyncio.create_subprocess_shell(
                "sudo nmcli dev wifi list --rescan yes", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if ssid in stdout.decode():
                MXLOG_DEBUG(f"Found SSID: {ssid}")
                return True
            elif asyncio.get_event_loop().time() > end_time:
                MXLOG_DEBUG("Timeout: SSID not found within the given time.")
                return False
            await asyncio.sleep(1)  # 잠시 대기 후 다시 시도합니다.

    async def connect_to(self, ssid: str, password: str) -> bool:
        try:
            await asyncio.create_subprocess_shell("nmcli --version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except OSError:
            MXLOG_DEBUG("nmcli is not installed. Please install NetworkManager to use this function.")
            return False

        ssid_found = await self.find_ssid(ssid)
        if not ssid_found:
            MXLOG_DEBUG(f"SSID {ssid} not found. Cannot attempt to connect.")
            return False

        connect_cmd = f'sudo nmcli dev wifi connect "{ssid}" password "{password}"'
        try:
            process = await asyncio.create_subprocess_shell(connect_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                MXLOG_DEBUG("WiFi connection attempt: success")
                return True
            else:
                MXLOG_DEBUG(f"WiFi connection attempt: failed\n{stderr.decode()}")
                return False
        except OSError as e:
            MXLOG_DEBUG(f"Error executing nmcli command: {e}")
            return False

    async def connect(self) -> bool:
        return await self.connect_to(self._ssid, self._password)

    def check_connection(self) -> bool:
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            active_connections = [line for line in result.stdout.split('\n') if line.startswith('yes:')]
            if active_connections:
                MXLOG_DEBUG("WiFi connection status: connected")
                return True
            else:
                MXLOG_DEBUG("WiFi connection status: not connected")
                return False
        except subprocess.CalledProcessError:
            MXLOG_DEBUG("Failed to check WiFi connection status")
            return False


if __name__ == '__main__':
    import asyncio

    START_LOGGER()

    async def ble_run():
        from big_thing_py.core.ble_advertiser import BLEAdvertiser

        ble_advertiser = BLEAdvertiser()
        await ble_advertiser.start()
        ssid, pw, broker, error_code = await ble_advertiser.wait_until_wifi_credentials_set()
        MXLOG_DEBUG(f'WiFi credentials set: ssid: {ssid}, pw: {pw}, broker: {broker}, error_code: {error_code}')
        await ble_advertiser.stop()
        return ssid, pw, broker, error_code

    async def wifi_run(ssid, pw):
        wifi_manager = WiFiManager(ssid, pw)
        MXLOG_DEBUG(f'current wifi: {wifi_manager.get_connected_wifi_ssid()}')
        await wifi_manager.connect_to(ssid, pw)
        MXLOG_DEBUG(f'current wifi: {wifi_manager.get_connected_wifi_ssid()}')

    ssid, pw, broker, error_code = asyncio.run(ble_run())
    asyncio.run(wifi_run(ssid, pw))
