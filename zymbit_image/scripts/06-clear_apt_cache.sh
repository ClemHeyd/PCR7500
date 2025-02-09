set -x
set -e

export LC_ALL=C

source /common.sh
install_cleanup_trap

# Clear package manager cache
apt-get clean
rm -rf /var/lib/apt/lists/*
