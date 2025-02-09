set -x
set -e

export LC_ALL=C

source /common.sh
install_cleanup_trap

# PUT YOUR SCRIPT HERE

# 1. Lock and disable login for the raspbian user
USERS_TO_REMOVE=("pi", "zymbit")

remove_user() {
    local username="$1"
    if id "$username" &>/dev/null; then
        echo "Locking the $username user..."
        usermod -L "$username"         # Lock password
        usermod -s /usr/sbin/nologin "$username"  # Disable shell (no login)

        # 2. Revoke privileges from known groups (just in case)
        for grp in sudo adm; do
            if getent group "$grp" | grep -q "$username"; then
                deluser "$username" "$grp" || true
            fi
        done

        # 3. Kill any processes using the user
        echo "Killing running processes for $username..."
        pkill -u "$username" || true

        # 4. Now remove user entirely
        echo "Removing $username user and home..."
        deluser --remove-home "$username"
    fi
}

# Remove each user in the array
for user in "${USERS_TO_REMOVE[@]}"; do
    remove_user "$user"
done
