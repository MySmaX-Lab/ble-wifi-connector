#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

pip install .

mkdir -p /usr/local/myssix
cp -r . /usr/local/myssix/ble-wifi-connector
cp ble-wifi-connector.service /etc/systemd/system/ble-wifi-connector.service
chmod 644 /etc/systemd/system/ble-wifi-connector.service

systemctl daemon-reload
systemctl enable ble-wifi-connector.service
systemctl start ble-wifi-connector.service
# journalctl -u ble-wifi-connector.service
