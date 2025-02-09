#!/usr/bin/env bash
#
#  Automatic SSH key generation (ed25519) and SSH server hardening.
#

set -e  # Exit on any error

# Check if SSH is installed
if ! command -v ssh &> /dev/null; then
    echo "SSH client is not installed. Installing..."
    apt-get update
    apt-get install -y openssh-client
fi

# Create .ssh directory if it doesn't exist
if [ ! -d "$HOME/.ssh" ]; then
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
fi

read -rp "Enter the SSH key name: " BASE_KEY_NAME

###############################################################################
# CONFIGURATION
###############################################################################
# Path for the new SSH key.
KEY_NAME="$HOME/.ssh/${BASE_KEY_NAME}_ed25519"

# SSH port for the remote server (default 22)
SSH_PORT=22

###############################################################################
# USER INPUTS
###############################################################################
read -rp "Enter the remote server username: " REMOTE_USER
read -rp "Enter the remote server IP or hostname: " REMOTE_HOST

# Check inputs
if [[ -z "$REMOTE_USER" || -z "$REMOTE_HOST" ]]; then
  echo "ERROR: Remote username and hostname/IP must not be empty."
  exit 1
fi

###############################################################################
# 1) GENERATE SSH KEY PAIR (Ed25519)
###############################################################################
echo "--------------------------------------------------------------------"
echo "Step 1: Generating a new SSH key pair (ed25519): $KEY_NAME"
echo "--------------------------------------------------------------------"
# -t: key type
# -f: file to save key
# -N: passphrase (empty for no passphrase; consider using one for better security)
# -C: comment
ssh-keygen -t ed25519 -f "$KEY_NAME" -N "" -C "$BASE_KEY_NAME"
echo "Key generation complete."

###############################################################################
# 2) COPY THE PUBLIC KEY TO THE REMOTE SERVER
###############################################################################
echo "--------------------------------------------------------------------"
echo "Step 2: Copying the public key to the remote server."
echo "--------------------------------------------------------------------"
ssh-copy-id -i "${KEY_NAME}.pub" -p "$SSH_PORT" "$REMOTE_USER@$REMOTE_HOST"

echo "Public key installed on $REMOTE_HOST."

###############################################################################
# 3) DISABLE PASSWORD-BASED AUTH ON REMOTE SERVER & ENABLE PUBKEY AUTH
###############################################################################
echo "--------------------------------------------------------------------"
echo "Step 3: Updating SSH server configuration to disable password auth."
echo "--------------------------------------------------------------------"

ssh -p "$SSH_PORT" "$REMOTE_USER@$REMOTE_HOST" bash -s <<'ENDCONFIG'
  set -e

  # Use sudo for editing system config
  SSHD_CFG="/etc/ssh/sshd_config"

  # Remove all instances of the settings and add new ones
  sudo sed -i '/^[[:space:]]*#*[[:space:]]*(PasswordAuthentication|ChallengeResponseAuthentication|PubkeyAuthentication|PermitRootLogin)/d' "$SSHD_CFG"

  # Add the new settings at the end
  {
    echo "PasswordAuthentication no"
    echo "ChallengeResponseAuthentication no" 
    echo "PubkeyAuthentication yes"
    echo "PermitRootLogin no"
  } | sudo tee -a "$SSHD_CFG" >/dev/null
ENDCONFIG

###############################################################################
# 4) RESTART SSH SERVICE
###############################################################################
echo "--------------------------------------------------------------------"
echo "Step 4: Restarting SSH service on the remote server."
echo "--------------------------------------------------------------------"
ssh -p "$SSH_PORT" "$REMOTE_USER@$REMOTE_HOST" "sudo systemctl restart sshd"

echo "--------------------------------------------------------------------"
echo "SSH hardening complete!"
echo "Password-based login is disabled. Test your new key before logging out."
echo "Connect with:  ssh -i $KEY_NAME $REMOTE_USER@$REMOTE_HOST"
echo "--------------------------------------------------------------------"
