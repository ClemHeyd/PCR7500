set -x
set -e

export LC_ALL=C

source /common.sh
install_cleanup_trap

# Install Tailscale
curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list

# Update package lists again and install Tailscale
apt-get update
apt-get install -y tailscale

# Enable Tailscale service
systemctl enable tailscaled