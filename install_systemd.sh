#!/bin/bash

current_user="${SUDO_USER:-$(whoami)}"
current_uid=$(id -u "$current_user")

SERVICE_NAME="ble-wifi-connector"

sudo mkdir -p /usr/local/joi
sudo cp -r . /usr/local/joi/$SERVICE_NAME
sudo cp $SERVICE_NAME.service /etc/systemd/system/$SERVICE_NAME.service

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME.service
sudo systemctl restart $SERVICE_NAME.service

echo "Service '${SERVICE_NAME}.service' installed and enabled successfully."
