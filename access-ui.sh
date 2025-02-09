#!/bin/bash

set -xe

# Check for required commands
if ! command -v ssh &> /dev/null; then
    echo "ssh is not installed. Please install using:"
    echo "sudo apt-get install openssh-client"
    exit 1
fi

if ! command -v remote-viewer &> /dev/null; then
    echo "remote-viewer is not installed. Please install using:"
    echo "sudo apt-get install virt-viewer"
    exit 1
fi

# Get SSH URL from user
read -p "Enter SSH URL (user@remote-server): " ssh_url

# Validate SSH URL format (user@host)
if [ -z "$ssh_url" ]; then
    echo "SSH URL cannot be empty"
    exit 1
fi

if ! [[ "$ssh_url" =~ ^[a-zA-Z0-9_-]+@[a-zA-Z0-9_.-]+$ ]]; then
    echo "Invalid SSH URL format. Must be in the form: user@host"
    exit 1
fi

# Start SSH tunnel in background
ssh -N -L 5900:localhost:5900 "$ssh_url" &
ssh_pid=$!

# Wait a moment for tunnel to establish
sleep 5

# Start remote viewer
remote-viewer spice://localhost:5900

# Clean up SSH tunnel when remote-viewer exits
kill $ssh_pid
