set -x
set -e

export LC_ALL=C

source /common.sh
install_cleanup_trap

# Install QEMU and libvirt packages
apt-get install -y qemu-system-x86 qemu-utils libvirt-daemon-system libvirt-clients

# Enable and start libvirtd service
systemctl enable libvirtd
