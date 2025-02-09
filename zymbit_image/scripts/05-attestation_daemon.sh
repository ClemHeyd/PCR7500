set -x
set -e

export LC_ALL=C

source /common.sh
install_cleanup_trap


# Install Python dependencies
apt install python3-cryptography python3-asn1crypto

# Copy attestation daemon script
cp /files/attestation_daemon.py /usr/local/bin/attestation_daemon.py

# Create systemd service file for attestation daemon
cat << 'EOF' > /etc/systemd/system/attestation.service
[Unit]
Description=Attestation Daemon Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/attestation_daemon.py
Restart=always
User=result_editor

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable attestation.service
systemctl start attestation.service
