set -x
set -e

export LC_ALL=C

source /common.sh
install_cleanup_trap


DEST_IMG="/var/lib/libvirt/images/7500FastXP"
DEST_XML="/etc/libvirt/qemu/7500FastXP.xml"

mkdir -p $DEST_DIR
cp /files/vm/7500FastXP.xml $DEST_XML
cp /files/vm/7500FastXP $DEST_IMG

# Set appropriate permissions
chmod 660 $DEST_XML
chmod 660 $DEST_IMG
chown root:libvirt-qemu $DEST_XML
chown root:libvirt-qemu $DEST_IMG

virsh autostart 7500FastXP
