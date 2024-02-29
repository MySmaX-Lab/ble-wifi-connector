#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit
fi

systemctl stop ble-wifi-connector.service
systemctl disable ble-wifi-connector.service
rm /etc/systemd/system/ble-wifi-connector.service
systemctl daemon-reload
rm -rf /usr/local/myssix/ble-wifi-connector
