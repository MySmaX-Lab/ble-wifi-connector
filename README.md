# Ble Wifi Connector

## Installation

### Manual installation (for development)

```bash
pip install .
```

### Service installation (for production)

The service installation uses `uv` to create an isolated virtual environment.

```bash
./install_systemd.sh
```

This will:
- Install `uv` if not already installed
- Create a virtual environment at `/usr/local/joi/ble-wifi-connector/.venv`
- Install all dependencies in the virtual environment
- Set up and start the systemd service

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
