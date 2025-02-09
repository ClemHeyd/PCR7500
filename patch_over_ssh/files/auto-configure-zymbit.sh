#!/bin/bash

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root"
    exit 1
fi

# Check if running on Debian
if [ ! -f /etc/debian_version ]; then
    echo "This script only works on Debian-based systems"
    exit 1
fi

# Create working directory
WORK_DIR=$(mktemp -d)

# Copy script to working directory
cp -r ./script.py "$WORK_DIR/script.py"
mkdir -p "$WORK_DIR/zymbit_image"
cp -r ./zymbit_image "$WORK_DIR/zymbit_image"

# Enter working directory
cd "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

# Define custopi directory
CUSTOPI_DIR="$WORK_DIR/zymbit_image"

mkdir -p "$WORK_DIR/build"

# Build script arguments
SCRIPT_ARGS="--scripts-dir $CUSTOPI_DIR/scripts/ --build-dir $WORK_DIR/build"

# Run script
apt update
apt install -y python3 python3-click
python3 ./script.py $SCRIPT_ARGS

echo "Setup Complete!"
