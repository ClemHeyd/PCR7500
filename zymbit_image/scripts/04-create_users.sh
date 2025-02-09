set -x
set -e

export LC_ALL=C

source /common.sh
install_cleanup_trap


###
# Harmless
###

USERNAME="7500Fast"
useradd -m -s /usr/sbin/nologin "$USERNAME"

USER_HOME=$(eval echo "~$USERNAME")
SSH_DIR="$USER_HOME/.ssh"

# Create .ssh directory with proper permissions
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
chown "$USERNAME:$USERNAME" "$SSH_DIR"

# Set proper permissions for authorized_keys
touch "$SSH_DIR/authorized_keys"
chmod 600 "$SSH_DIR/authorized_keys"
chown "$USERNAME:$USERNAME" "$SSH_DIR/authorized_keys"

# Create custom sshd config for this user
cat > "/etc/ssh/sshd_config.d/${USERNAME}.conf" << 'EOF'
Match User ${USERNAME}
    PasswordAuthentication no
    PubkeyAuthentication yes
    AllowTcpForwarding yes
    X11Forwarding no
    PermitTTY no
    PermitTunnel no
    AllowAgentForwarding no
    ForceCommand echo 'This account can only be used for port forwarding'
    PermitOpen localhost:5900
EOF

# Set proper permissions for the SSH config
chmod 644 "/etc/ssh/sshd_config.d/${USERNAME}.conf"
chown root:root "/etc/ssh/sshd_config.d/${USERNAME}.conf"

###
# WiFi Setup
###

NMTUI_USER="wifi_setup"

# Create nmtui-shell script
cat << 'EOF' > "/usr/local/bin/nmtui-shell"
#!/bin/bash
exec /usr/bin/nmtui
EOF

# Make the shell executable
chmod 755 "/usr/local/bin/nmtui-shell"

# Add the shell to allowed shells
echo "/usr/local/bin/nmtui-shell" >> /etc/shells

# Create user with restricted shell
useradd -m -s /usr/local/bin/nmtui-shell "$NMTUI_USER"
usermod -a -G netdev "$NMTUI_USER"

###
# Results Publishing
###

# Create results publishing user and group
RESULTS_OWNER="result_editor"
RESULTS_READER="harmless_reader"
RESULTS_GROUP="result_readers"
RESULTS_DIR="/var/lib/attestation_results"
KEYS_DIR="/var/lib/pcr_attestation_keys"

# Create the group
groupadd "$RESULTS_GROUP"

# Create users with no shell access
useradd -M -s /usr/sbin/nologin "$RESULTS_READER"
useradd -M -s /usr/sbin/nologin "$RESULTS_OWNER"

# Add results reader to results group
usermod -a -G "$RESULTS_GROUP" "$RESULTS_READER"

# Forbid SSH access to results owner
cat << 'EOF' > "/etc/ssh/sshd_config.d/${RESULTS_OWNER}.conf"
DenyUsers ${RESULTS_OWNER}

Match User ${RESULTS_OWNER}
    AllowTCPForwarding no
    X11Forwarding no
EOF

# Set proper permissions on SSH config
chmod 644 "/etc/ssh/sshd_config.d/${RESULTS_OWNER}.conf"
chown root:root "/etc/ssh/sshd_config.d/${RESULTS_OWNER}.conf"

# Create results directory
mkdir -p "$KEYS_DIR"
mkdir -p "$RESULTS_DIR"

# Set ownership and permissions
# - Owner (results user) has read/write
# - Group (results_readers) has read-only
# - Others have no access
chown "$RESULTS_OWNER:$RESULTS_GROUP" "$RESULTS_DIR"
chmod 750 "$RESULTS_DIR"

# Set ownership and permissions
# - Owner (results user) has read/write
# - Group (results_readers) has read-only
# - Others have no access
chown "$RESULTS_OWNER:$RESULTS_GROUP" "$KEYS_DIR"
chmod 700 "$KEYS_DIR"

# Create an SSH configuration snippet to restrict this user to SFTP-only,
# chrooted into /var/lib/attestation_results for read-only access
cat << 'EOF' > "/etc/ssh/sshd_config.d/${RESULTS_READER}.conf"
Match User ${RESULTS_READER}
    ChrootDirectory ${RESULTS_DIR}
    ForceCommand internal-sftp
    AllowTCPForwarding no
    X11Forwarding no
EOF

# Secure permissions on the SSH config snippet
chmod 644 "/etc/ssh/sshd_config.d/${RESULTS_READER}.conf"
chown root:root "/etc/ssh/sshd_config.d/${RESULTS_READER}.conf"
