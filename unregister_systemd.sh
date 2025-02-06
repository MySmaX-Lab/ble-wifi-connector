#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

SERVICE_NAME="ble-wifi-connector"

systemctl stop $SERVICE_NAME.service
systemctl disable $SERVICE_NAME.service
rm /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload
rm -rf /usr/local/joi/$SERVICE_NAME
