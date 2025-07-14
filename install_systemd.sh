#!/bin/bash

current_user="${SUDO_USER:-$(whoami)}"
current_uid=$(id -u "$current_user")

SERVICE_NAME="ble-wifi-connector"

echo "Installing Python dependencies system-wide..."
sudo pip install . --break-system-packages

echo "Setting up service files..."
sudo mkdir -p /usr/local/joi
sudo cp -r . /usr/local/joi/$SERVICE_NAME

# Set proper ownership and permissions
sudo chown -R root:root /usr/local/joi/$SERVICE_NAME
sudo chmod +x /usr/local/joi/$SERVICE_NAME/ble_wifi_connector/__main__.py

sudo cp $SERVICE_NAME.service /etc/systemd/system/$SERVICE_NAME.service

echo "Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME.service
sudo systemctl restart $SERVICE_NAME.service

echo "Service '${SERVICE_NAME}.service' installed and enabled successfully."
echo "Check status with: sudo systemctl status $SERVICE_NAME.service"
echo "View logs with: journalctl -u $SERVICE_NAME.service -f"
