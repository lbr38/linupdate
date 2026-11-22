#!/usr/bin/env bash
#
# Prepare a container before installing linupdate: package repositories needed by
# linupdate dependencies and system update.
#
# Usage: setup-system.sh [--no-update]
#   --no-update: only configure the repositories, do not update the system
#
# Debian based images are not updated on purpose: the test suite needs packages to update.

set -e

UPDATE=true
if [ "$1" = "--no-update" ]; then
    UPDATE=false
fi

# shellcheck source=/dev/null
. /etc/os-release
MAJOR_VERSION="${VERSION_ID%%.*}"

case "$ID" in
    debian|ubuntu)
        apt-get update -y
        ;;

    centos)
        # CentOS 8 is EOL: use the archive (vault) repositories
        # The original repository files are overwritten (same names), so that they are not
        # restored when the centos-linux-repos package is updated
        if [ "$MAJOR_VERSION" = "8" ]; then
            for repo in AppStream:AppStream:appstream BaseOS:BaseOS:baseos Extras:extras:extras; do
                IFS=: read -r file_name path section <<< "$repo"

                cat > "/etc/yum.repos.d/CentOS-Linux-${file_name}.repo" << EOF
[${section}]
name=CentOS Linux \$releasever - ${file_name}
baseurl=http://vault.centos.org/\$contentdir/\$releasever/${path}/\$basearch/os/
gpgcheck=1
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial
EOF
            done
        fi

        dnf install -y epel-release
        dnf clean all

        if [ "$UPDATE" = true ]; then
            dnf update -y --exclude=centos-release
        fi

        # Required by python3-rich on CentOS 8
        dnf install -y python3-dataclasses python3-typing-extensions
        ;;

    almalinux|rocky)
        dnf install -y epel-release

        # CRB repository is required to install python3-pygments (python3-rich dependency) on EL9
        if [ "$MAJOR_VERSION" = "9" ]; then
            dnf config-manager --set-enabled crb
        fi

        if [ "$UPDATE" = true ]; then
            dnf update -y
        fi
        ;;

    fedora)
        if [ "$UPDATE" = true ]; then
            dnf update -y
        fi
        ;;

    *)
        echo "Unsupported OS: ${ID}"
        exit 1
        ;;
esac
