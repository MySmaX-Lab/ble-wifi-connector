__all__ = ['BLEAdvertiser', 'BLEErrorCode']


import asyncio
import sys, click
from typing import Any, List, Tuple
from enum import Enum
from contextlib import asynccontextmanager

from termcolor import colored
from bless import BlessServer, BlessGATTCharacteristic, GATTCharacteristicProperties, GATTAttributePermissions
from bleak import BleakClient, BleakScanner

from .common.utils import *
from .common.models import DiscoveredBleDevice


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
                value=self.get_middleware_identifier('/usr/local/joi/middleware/middleware.cfg').encode(),
            )

        def get_middleware_identifier(self, config_path) -> str:
            try:
                with open(config_path, 'r') as file:
                    for line in file:
                        stripped_line: str = line.split('//')[0].strip()
                        if stripped_line.startswith('middleware_identifier'):
                            return f'''{stripped_line.split('=')[1].strip().strip('"')} {get_mac_address().replace(':', '').upper()}'''
                return f"DEFAULT {get_mac_address().replace(':', '').upper()}"
            except FileNotFoundError:
                return f"DEFAULT {get_mac_address().replace(':', '').upper()}"

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


class DeviceWifiService(Service):
    UUID = '640F0000-0000-0000-0000-000000000000'

    class SetWifiSSIDCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='640F0001-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.write,
                permissions=GATTAttributePermissions.writeable,
            )

    class SetWifiPWCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='640F0002-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.write,
                permissions=GATTAttributePermissions.writeable,
            )

    class SetBrokerInfoCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='640F0003-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.write,
                permissions=GATTAttributePermissions.writeable,
            )

    class ConnectWifiCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='640F0004-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.write,
                permissions=GATTAttributePermissions.writeable,
            )

    class ThingIDCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='640F0005-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.read,
                permissions=GATTAttributePermissions.readable,
            )

    class ErrorCodeCharacteristic(Characteristic):
        def __init__(self):
            super().__init__(
                uuid='640F0006-0000-0000-0000-000000000000',
                properties=GATTCharacteristicProperties.read,
                permissions=GATTAttributePermissions.readable,
            )

    def __init__(self):
        characteristics = [
            self.SetWifiSSIDCharacteristic(),
            self.SetWifiPWCharacteristic(),
            self.SetBrokerInfoCharacteristic(),
            self.ConnectWifiCharacteristic(),
            # self.ThingIDCharacteristic(), # this characteristic should be added, after thing id is set
            self.ErrorCodeCharacteristic(),
        ]
        super().__init__(DeviceWifiService.UUID, characteristics)


class BLEAdvertiser:
    def __init__(self, server_name: str = f'JOI Hub {get_mac_address()}') -> None:
        self._server_name = server_name
        self._server: BlessServer = None
        self._trigger = asyncio.Event()
        self._logger = Logger().get_logger()

    def _read_request(self, characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
        self._logger.debug(f'Reading {characteristic.value}')
        return characteristic.value

    def _write_request(self, characteristic: BlessGATTCharacteristic, value: Any, **kwargs):
        self._logger.debug(f'Write event - UUID: {characteristic.uuid.upper()}, Value: {characteristic.value}')

        try:
            uuid = characteristic.uuid.upper()
            char = self._server.get_characteristic(uuid)
            char.value = value or self._server.get_characteristic(uuid).value
            if uuid == HubWifiService.SetWifiSSIDCharacteristic().uuid:
                self._logger.debug(f'WiFi SSID set: {self._server.get_characteristic(uuid).value}')
            elif uuid == HubWifiService.SetWifiPWCharacteristic().uuid:
                self._logger.debug(f'WiFi PW set: {self._server.get_characteristic(uuid).value}')
            elif uuid == HubWifiService.ConnectWifiCharacteristic().uuid:
                ssid = self._server.get_characteristic(HubWifiService.SetWifiSSIDCharacteristic().uuid).value
                pw = self._server.get_characteristic(HubWifiService.SetWifiPWCharacteristic().uuid).value
                if ssid is None or pw is None:
                    self._logger.debug(f'WiFi credentials not set... ssid: {ssid}, pw: {pw}')
                    self._server.update_value(
                        HubWifiService.ErrorCodeCharacteristic().uuid, BLEErrorCode.WIFI_CREDENTIAL_NOT_SET.value.to_bytes(2, 'little')
                    )
                    return
                else:
                    self._logger.debug(colored(f'wifi credentials is set! ssid: {ssid}, pw: {pw}', 'green'))
                    self._trigger.set()
        except Exception as e:
            self._logger.debug(colored(f'Error occurred while writing characteristic: {e}', 'red'))
            self._server.update_value(HubWifiService.ErrorCodeCharacteristic().uuid, BLEErrorCode.FAIL.value.to_bytes(2, 'little'))

    async def _add_service(self, service: Service):
        await self._server.add_new_service(service.uuid)
        for char in service.characteristics:
            await self._server.add_new_characteristic(service.uuid, char.uuid, char.properties, char.value, char.permissions)

    async def start(self):
        self._logger.debug('Starting BLE advertiser...')
        self._trigger.clear()
        self._server = BlessServer(name=self._server_name)
        self._server.read_request_func = self._read_request
        self._server.write_request_func = self._write_request

        await self._add_service(HubWifiService())

        await self._server.start()
        self._logger.debug(f'BLE Advertising started with name {self._server_name}...')

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
            self._logger.debug(colored(f'wifi credentials is set finally! ssid: {ssid}, pw: {pw}, error: {error_code}', 'green'))
            return (ssid, pw, error_code)

        try:
            ssid, pw, error_code = await asyncio.wait_for(wrapper(), timeout)
            return (ssid, pw, error_code)
        except asyncio.TimeoutError:
            return ('', '', '', BLEErrorCode.WIFI_CONNECT_TIMEOUT)

    async def stop(self):
        await self._server.stop()
        self._logger.debug('BLE Advertising stopped...')

    async def is_connected(self):
        return await self._server.is_connected()


@click.command()
@click.option(
    '--mode',
    '-m',
    type=click.Choice(['run_hub', 'set_hub', 'set_smart_device'], case_sensitive=False),
    required=True,
    help="Mode to run: 'run_hub', 'set_hub', 'set_smart_device'.",
)
@click.option('--ssid', '-ssid', type=str, required=True, help="WiFi SSID.")
@click.option('--pw', '-pw', type=str, required=True, help="WiFi password.")
@click.option('--device-name', '-n', type=str, required=True, help="device name")
@click.option('--broker-host', '-b', type=str, required=False, help="Broker host <IP:PORT> (only required for 'smart_device').")
def main(mode: str, ssid: str, pw: str, broker_host: str, device_name: str):
    asyncio.run(async_main(mode, ssid, pw, broker_host, device_name))


@asynccontextmanager
async def connect_to_device(discovered_device: 'DiscoveredBleDevice'):
    while True:
        try:
            async with BleakClient(discovered_device.address) as client:
                click.echo(f"Connected to {discovered_device}")
                yield client
                break
        except Exception as e:
            click.echo(f"Error connecting to {discovered_device}: {e}")


async def async_main(mode: str, ssid: str, pw: str, broker_host: str, device_name: str):
    """
    CLI to run BLE Advertiser in hub or smart_device mode.
    """

    if mode == 'run_hub':
        if broker_host or device_name:
            click.echo("Error: 'broker_host' and 'device_name' are not valid options for 'hub' mode.")
            return

        ble_advertiser = BLEAdvertiser(server_name=f'JOI Hub {get_mac_address()}')
        await ble_advertiser.start()
        click.echo(f"BLE Hub Advertiser started with SSID: {ssid}, PW: {pw}")

        ssid, pw, error_code = await ble_advertiser.wait_until_wifi_credentials_set()
        click.echo(f"WiFi credentials set: SSID: {ssid}, PW: {pw}, Error Code: {error_code}")

        await ble_advertiser.stop()
    elif mode == 'set_hub':
        if device_name is None:
            device_name = f'JOI Hub {get_mac_address()}'

        await set_hub_bleak(device_name, ssid, pw)
    elif mode == 'set_smart_device':
        if not broker_host or not device_name:
            click.echo("Error: 'broker_host' and 'device_name' are required options for 'smart_device' mode.")
            sys.exit(1)

        await set_smart_device_bleak(device_name, ssid, pw, broker_host)
    else:
        click.echo("Invalid mode. Use 'hub' or 'smart_device'.")


async def set_hub_bleak(device_name: str, ssid: str, pw: str):
    """bleak를 사용한 허브 설정 (기존 로직)"""
    if (discovered_device := await ble_discover(device_name)) is None:
        click.echo(f"Error: Device {device_name} not found.")
        sys.exit(1)

    ssid_characteristic_uuid = HubWifiService.SetWifiSSIDCharacteristic().uuid
    pw_characteristic_uuid = HubWifiService.SetWifiPWCharacteristic().uuid
    connect_wifi_characteristic_uuid = HubWifiService.ConnectWifiCharacteristic().uuid

    ssid_value = ssid.encode()
    pw_value = pw.encode()

    async with connect_to_device(discovered_device) as client:
        # Wait for the client to be fully connected
        await asyncio.sleep(1)

        # Get the Hub WiFi service and its characteristics
        hub_service = None
        for service in client.services:
            if service.uuid.upper() == HubWifiService.UUID.upper():
                hub_service = service
                break

        if not hub_service:
            click.echo(f"Error: Hub WiFi service not found")
            return

        # Find characteristics within the Hub WiFi service
        ssid_char = None
        pw_char = None
        connect_char = None

        for char in hub_service.characteristics:
            if char.uuid.upper() == ssid_characteristic_uuid.upper():
                ssid_char = char
            elif char.uuid.upper() == pw_characteristic_uuid.upper():
                pw_char = char
            elif char.uuid.upper() == connect_wifi_characteristic_uuid.upper():
                connect_char = char

        if not all([ssid_char, pw_char, connect_char]):
            click.echo(f"Error: Required characteristics not found")
            return

        # Write characteristics with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await client.write_gatt_char(ssid_char, ssid_value)
                click.echo("WiFi SSID set")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    click.echo(f"Error setting WiFi SSID after {max_retries} attempts: {e}")
                    return
                await asyncio.sleep(0.5)

        for attempt in range(max_retries):
            try:
                await client.write_gatt_char(pw_char, pw_value)
                click.echo("WiFi password set")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    click.echo(f"Error setting WiFi password after {max_retries} attempts: {e}")
                    return
                await asyncio.sleep(0.5)

        for attempt in range(max_retries):
            try:
                await client.write_gatt_char(connect_char, bytearray([0x00]))
                click.echo("WiFi connection attempt")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    click.echo(f"Error triggering WiFi connection after {max_retries} attempts: {e}")
                    return
                await asyncio.sleep(0.5)


async def set_smart_device_bleak(device_name: str, ssid: str, pw: str, broker_host: str):
    """bleak를 사용한 스마트 디바이스 설정 (기존 로직)"""
    if (discovered_device := await ble_discover(device_name)) is None:
        click.echo(f"Error: Device {device_name} not found.")
        sys.exit(1)

    ssid_value = ssid.encode()
    pw_value = pw.encode()
    broker_host_value = broker_host.encode()

    async with connect_to_device(discovered_device) as client:
        # Wait for the client to be fully connected
        await asyncio.sleep(1)

        # Get the Device WiFi service and its characteristics
        device_service = None
        for service in client.services:
            if service.uuid.upper() == DeviceWifiService.UUID.upper():
                device_service = service
                break

        if not device_service:
            click.echo(f"Error: Device WiFi service not found")
            return

        # Find characteristics within the Device WiFi service
        ssid_char = None
        pw_char = None
        broker_char = None
        connect_char = None

        ssid_uuid = DeviceWifiService.SetWifiSSIDCharacteristic().uuid
        pw_uuid = DeviceWifiService.SetWifiPWCharacteristic().uuid
        broker_uuid = DeviceWifiService.SetBrokerInfoCharacteristic().uuid
        connect_uuid = DeviceWifiService.ConnectWifiCharacteristic().uuid

        for char in device_service.characteristics:
            if char.uuid.upper() == ssid_uuid.upper():
                ssid_char = char
            elif char.uuid.upper() == pw_uuid.upper():
                pw_char = char
            elif char.uuid.upper() == broker_uuid.upper():
                broker_char = char
            elif char.uuid.upper() == connect_uuid.upper():
                connect_char = char

        if not all([ssid_char, pw_char, broker_char]):
            click.echo(f"Error: Required characteristics not found")
            return

        # Write characteristics with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await client.write_gatt_char(ssid_char, ssid_value)
                click.echo("WiFi SSID set")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    click.echo(f"Error setting WiFi SSID after {max_retries} attempts: {e}")
                    return
                await asyncio.sleep(0.5)

        for attempt in range(max_retries):
            try:
                await client.write_gatt_char(pw_char, pw_value)
                click.echo("WiFi password set")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    click.echo(f"Error setting WiFi password after {max_retries} attempts: {e}")
                    return
                await asyncio.sleep(0.5)

        for attempt in range(max_retries):
            try:
                await client.write_gatt_char(broker_char, broker_host_value)
                click.echo("Broker info set")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    click.echo(f"Error setting broker info after {max_retries} attempts: {e}")
                    return
                await asyncio.sleep(0.5)

        if connect_char:
            for attempt in range(max_retries):
                try:
                    await client.write_gatt_char(connect_char, bytearray([0x00]))
                    click.echo("WiFi connection attempt")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        click.echo(f"Error triggering WiFi connection after {max_retries} attempts: {e}")
                        return
                    await asyncio.sleep(0.5)


async def ble_discover(name: str, timeout: float = 30) -> DiscoveredBleDevice:
    """BLE 디바이스 검색"""

    async def discover_device():
        while True:
            devices = await BleakScanner.discover(timeout=1)
            for device in devices:
                if device.name == name:
                    click.echo(f'Found BLE server! Name: {device.name}, Address: {device.address}')
                    return DiscoveredBleDevice(name=device.name, address=device.address)
                else:
                    click.echo(f'{device.name} | {device.address}')
            click.echo(f"Discovering device with name: {name}, retrying...")

    try:
        return await asyncio.wait_for(discover_device(), timeout)
    except asyncio.TimeoutError:
        click.echo(f"Timeout: Could not find device {name} within {timeout} seconds")
        return None


if __name__ == '__main__':
    main()
