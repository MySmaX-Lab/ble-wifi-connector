#!/bin/bash

SERVICE_NAME="ble-wifi-connector"

echo "Stopping and disabling $SERVICE_NAME service..."
sudo systemctl stop $SERVICE_NAME.service
sudo systemctl disable $SERVICE_NAME.service
sudo rm /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload

echo "Removing service directory (including virtual environment)..."
sudo rm -rf /usr/local/joi/$SERVICE_NAME

echo "Service uninstalled successfully."
