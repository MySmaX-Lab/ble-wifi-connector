import asyncio
from bless import BlessServer, BlessGATTCharacteristic, GATTCharacteristicProperties, GATTAttributePermissions

from termcolor import cprint
from typing import Any, List, Tuple
from enum import Enum
from utils import get_mac_address


class BLEErrorCode(Enum):
    NO_ERROR = 0
    FAIL = -1
    WIFI_PASSWORD_ERROR = -2
    WIFI_CONNECT_TIMEOUT = -3
    ALREADY_CONNECTED = -4
    WIFI_NOT_FOUND = -5
    WIFI_CREDENTIAL_NOT_SET = -6
    BROKER_NOT_SET = -7


class Characteristic:
    def __init__(self, uuid: str, properties: GATTCharacteristicProperties, permissions: GATTAttributePermissions, value: bytearray = None):
        self.uuid = uuid
        self.properties = properties
        self.permissions = permissions
        self.value = value


class Service:
    def __init__(self, uuid: str, characteristics: List[Characteristic]):
        self.uuid = uuid
        self.characteristics = characteristics


class HubWifiService(Service):
    UUID = '540F0000-0000-0000-0000-000000000000'

    class SetWifiSSIDCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='540F0001-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.write,
                permissions=GATTAttributePermissions.writeable,
            )

    class SetWifiPWCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='540F0002-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.write,
                permissions=GATTAttributePermissions.writeable,
            )

    class ConnectWifiCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='540F0003-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.write,
                permissions=GATTAttributePermissions.writeable,
            )

    class HubIDCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='540F0004-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.read,
                permissions=GATTAttributePermissions.readable,
                value=self.get_middleware_identifier('/usr/local/myssix/middleware/middleware.cfg').encode(),
            )

        def get_middleware_identifier(self, config_path) -> str:
            with open(config_path, 'r') as file:
                for line in file:
                    stripped_line: str = line.split('//')[0].strip()
                    if stripped_line.startswith('middleware_identifier'):
                        return f'''{stripped_line.split('=')[1].strip().strip('"')}_{get_mac_address().replace(':', '').upper()}'''

    class ErrorCodeCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='540F0005-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.read,
                permissions=GATTAttributePermissions.readable,
            )

    def __init__(self):
        characteristics = [
            self.SetWifiSSIDCharacteristic(),
            self.SetWifiPWCharacteristic(),
            self.ConnectWifiCharacteristic(),
            self.HubIDCharacteristic(),
            self.ErrorCodeCharacteristic(),
        ]
        super().__init__(HubWifiService.UUID, characteristics)


class BLEAdvertiser:
    def __init__(self, server_name: str = f'JOI Hub {get_mac_address()}') -> None:
        self._server_name = server_name
        self._server: BlessServer = None
        self._trigger = asyncio.Event()

    def _read_request(self, characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
        cprint(f'Reading {characteristic.value}')
        return characteristic.value

    def _write_request(self, characteristic: BlessGATTCharacteristic, value: Any, **kwargs):
        try:
            characteristic.value = value
            uuid = characteristic.uuid.upper()
            if uuid == HubWifiService.SetWifiSSIDCharacteristic().uuid:
                cprint(f'WiFi SSID set: {self._server.get_characteristic(HubWifiService.SetWifiSSIDCharacteristic().uuid).value}')
            elif uuid == HubWifiService.SetWifiPWCharacteristic().uuid:
                cprint(f'WiFi PW set: {self._server.get_characteristic(HubWifiService.SetWifiPWCharacteristic().uuid).value}')
            elif uuid == HubWifiService.ConnectWifiCharacteristic().uuid:
                ssid = self._server.get_characteristic(HubWifiService.SetWifiSSIDCharacteristic().uuid).value
                pw = self._server.get_characteristic(HubWifiService.SetWifiPWCharacteristic().uuid).value
                if ssid is None or pw is None:
                    cprint(f'WiFi credentials not set... ssid: {ssid}, pw: {pw}')
                    self._server.update_value(
                        HubWifiService.ErrorCodeCharacteristic().uuid, BLEErrorCode.WIFI_CREDENTIAL_NOT_SET.value.to_bytes(2, 'little')
                    )
                    return
                else:
                    cprint('wifi credentials is set!', 'green')
                    self._trigger.set()
        except Exception as e:
            cprint(f'Error occurred while writing characteristic: {e}', 'red')
            self._server.update_value(HubWifiService.ErrorCodeCharacteristic().uuid, BLEErrorCode.FAIL.value.to_bytes(2, 'little'))

    async def _add_service(self, service: Service):
        await self._server.add_new_service(service.uuid)
        for char in service.characteristics:
            await self._server.add_new_characteristic(service.uuid, char.uuid, char.properties, char.value, char.permissions)

    async def start(self):
        cprint('Starting BLE advertiser...')
        self._trigger.clear()
        self._server = BlessServer(name=self._server_name)
        self._server.read_request_func = self._read_request
        self._server.write_request_func = self._write_request

        await self._add_service(HubWifiService())

        await self._server.start()
        cprint('BLE Advertising started...')

    async def is_advertising(self) -> bool:
        if self._server is None:
            return False

        return await self._server.is_advertising()

    async def wait_until_wifi_credentials_set(self, timeout: float = 30) -> Tuple[str, str, str, BLEErrorCode]:

        async def wrapper() -> Tuple[str, str, str, BLEErrorCode]:
            await self._trigger.wait()
            ssid = self._server.get_characteristic(HubWifiService.SetWifiSSIDCharacteristic().uuid).value.decode()
            pw = self._server.get_characteristic(HubWifiService.SetWifiPWCharacteristic().uuid).value.decode()
            error_code = BLEErrorCode(int.from_bytes(self._server.get_characteristic(HubWifiService.ErrorCodeCharacteristic().uuid).value, 'little'))
            return (ssid, pw, error_code)

        try:
            ssid, pw, error_code = await asyncio.wait_for(wrapper(), timeout)
            return (ssid, pw, error_code)
        except asyncio.TimeoutError:
            return ('', '', '', BLEErrorCode.WIFI_CONNECT_TIMEOUT)

    async def stop(self):
        await self._server.stop()
        cprint('BLE Advertising stopped...')

    async def is_connected(self):
        return await self._server.is_connected()


if __name__ == '__main__':

    async def run():
        ble_advertiser = BLEAdvertiser(server_name=f'JOI Hub {get_mac_address()}')
        await ble_advertiser.start()
        ssid, pw, error_code = await ble_advertiser.wait_until_wifi_credentials_set()
        cprint(f'WiFi credentials set: ssid: {ssid}, pw: {pw}, error_code: {error_code}')
        await ble_advertiser.stop()

    async def test_middleware(server_name: str = f'JOI Hub {get_mac_address()}'):
        '''
        NOTE: this test function should be run on a separate device
        '''
        from bleak import BleakClient, BleakScanner

        device_address = None

        devices = await BleakScanner.discover()
        for device in devices:
            if device.name == server_name:
                print(f'Found BLE server! name: {device.name}, address: {device.address}')
                device_address = device.address
                break
        else:
            print(f"Cannot find {server_name}")
            return

        ssid_characteristic_uuid = HubWifiService.SetWifiSSIDCharacteristic().uuid
        pw_characteristic_uuid = HubWifiService.SetWifiPWCharacteristic().uuid
        connect_wifi_characteristic_uuid = HubWifiService.ConnectWifiCharacteristic().uuid

        ssid_value = b"MySmaX-office5G"
        pw_value = b"/PeaCE/#1"

        async with BleakClient(device_address) as client:
            if client.is_connected:
                print(f"Connected to {device_address}")

                await client.write_gatt_char(ssid_characteristic_uuid, ssid_value)
                print("WiFi SSID set")

                await client.write_gatt_char(pw_characteristic_uuid, pw_value)
                print("WiFi password set")

                await client.write_gatt_char(connect_wifi_characteristic_uuid, bytearray([0x00]))
                print("WiFi connection attempt")

    asyncio.run(test_middleware())
