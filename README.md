# Ble Wifi Connector

## Installation

```bash
pip install .
```

## Usage

### Set hub wifi credentials

```bash
ble-wifi-connector -m set_hub -ssid SSID -pw PASSWORD -n HUB_NAME
```

### Set thing wifi credentials

```bash
ble-wifi-connector -m set_smart_device -ssid SSID -pw PASSWORD -n DEVICE_NAME -b BROKER_HOST
```

### Run as a daemon

#### Install systemd service

```bash
./install_systemd.sh
```

#### Uninstall systemd service

```bash
./uninstall_systemd.sh
```
