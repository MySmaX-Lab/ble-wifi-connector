#!/bin/bash

SERVICE_NAME="ble-wifi-connector"

sudo systemctl stop $SERVICE_NAME.service
sudo systemctl disable $SERVICE_NAME.service
sudo rm /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload
sudo rm -rf /usr/local/joi/$SERVICE_NAME
