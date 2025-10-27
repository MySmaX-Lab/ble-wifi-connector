#!/bin/bash

current_user="${SUDO_USER:-$(whoami)}"
current_uid=$(id -u "$current_user")

SERVICE_NAME="ble-wifi-connector"
INSTALL_DIR="/usr/local/joi/$SERVICE_NAME"
VENV_DIR="$INSTALL_DIR/.venv"

# Check if uv is installed, if not install it
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this script
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# Ensure uv is available for sudo commands
UV_PATH=$(command -v uv)
if [ -z "$UV_PATH" ]; then
    echo "Error: uv not found after installation. Please install uv manually."
    exit 1
fi

echo "Setting up service files..."
sudo mkdir -p /usr/local/joi
sudo cp -r . /usr/local/joi/$SERVICE_NAME

# Set proper ownership and permissions
sudo chown -R root:root /usr/local/joi/$SERVICE_NAME
sudo chmod +x /usr/local/joi/$SERVICE_NAME/ble_wifi_connector/__main__.py

echo "Creating virtual environment with uv..."
cd $INSTALL_DIR
sudo $UV_PATH venv $VENV_DIR

echo "Installing Python dependencies in virtual environment..."
sudo $UV_PATH pip install --python $VENV_DIR/bin/python .

sudo cp $SERVICE_NAME.service /etc/systemd/system/$SERVICE_NAME.service

echo "Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME.service
sudo systemctl restart $SERVICE_NAME.service

echo "Service '${SERVICE_NAME}.service' installed and enabled successfully."
echo "Check status with: sudo systemctl status $SERVICE_NAME.service"
echo "View logs with: journalctl -u $SERVICE_NAME.service -f"
