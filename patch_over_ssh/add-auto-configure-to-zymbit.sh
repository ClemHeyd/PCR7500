#!/usr/bin/env bash

# Exit on any error
set -e

# Get absolute directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Check required arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <remote_user> <remote_host>"
    exit 1
fi

REMOTE_USER="$1"
REMOTE_HOST="$2"
REMOTE_DIR="/home/$REMOTE_USER/setup-zymbit-pcr"

# Create remote directory
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_DIR"

# Copy required files
echo "Copying files to $REMOTE_HOST:$REMOTE_DIR..."
scp "$SCRIPT_DIR/script.py" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"
scp "$SCRIPT_DIR/files/auto-configure-zymbit.sh" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# Copy zymbit_image contents to remote workspace directory
echo "Copying zymbit_image contents to $REMOTE_HOST:$REMOTE_DIR/workspace..."
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_DIR/workspace"
scp -r "$PARENT_DIR/zymbit_image/"* "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/workspace/"

echo "Files copied successfully to $REMOTE_HOST:$REMOTE_DIR"

# Execute the auto-configure script on the remote machine
echo "Running auto-configure script on $REMOTE_HOST..."
ssh "$REMOTE_USER@$REMOTE_HOST" "cd $REMOTE_DIR && chmod +x auto-configure-zymbit.sh && sudo ./auto-configure-zymbit.sh"

echo "Auto-configure script completed successfully on $REMOTE_HOST"
