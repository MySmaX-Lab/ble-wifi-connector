#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

SERVICE_NAME="ble-wifi-connector"

mkdir -p /usr/local/joi
cp -r . /usr/local/joi/$SERVICE_NAME
cp $SERVICE_NAME.service /etc/systemd/system/$SERVICE_NAME.service

systemctl daemon-reload
systemctl enable $SERVICE_NAME.service
systemctl restart $SERVICE_NAME.service

echo "Service '${SERVICE_NAME}.service' installed and enabled successfully."
