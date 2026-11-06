#!/usr/bin/env bash
#
# Helpers shared by the linupdate CI test scripts (sourced, not executed).
#
# Configurable via environment variables:
#   LINUPDATE_CMD : command used to invoke linupdate
#                   (default: "python3 /opt/linupdate/linupdate.py").
#                   Set to "sudo python3 /opt/linupdate/linupdate.py" where sudo
#                   is required (e.g. latest Ubuntu).

# Variables are used by the scripts sourcing this file
# shellcheck disable=SC2034

LINUPDATE_CMD="${LINUPDATE_CMD:-python3 /opt/linupdate/linupdate.py}"

# Configuration files
LINUPDATE_CONF="/etc/linupdate/linupdate.yml"
UPDATE_CONF="/etc/linupdate/update.yml"
REPOSERVER_CONF="/etc/linupdate/modules/reposerver.yml"

# Directory of the linupdate locks
LOCK_DIR="/opt/linupdate/locks"

# Get OS family (either "debian" or "rhel")
OS_FAMILY=""
if [ -f /etc/os-release ]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    case "$ID" in
        ubuntu|debian)
            OS_FAMILY="debian"
            ;;
        centos|rocky|almalinux|fedora)
            OS_FAMILY="rhel"
            ;;
        *)
            echo "Unsupported OS: $ID"
            exit 1
            ;;
    esac
fi

# Wrapper that runs linupdate using the configured command (allowing a sudo
# prefix). Word-splitting on LINUPDATE_CMD is intentional here.
linupdate() {
    # shellcheck disable=SC2086
    $LINUPDATE_CMD "$@"
}

# Run a single named test, grouped in the CI logs for readability.
run_test() {
    local title="$1"
    shift
    echo "::group::Run test: ${title}"
    "$@"
    echo "::endgroup::"
}

# Print an error and stop the test suite.
fail() {
    echo "::endgroup::"
    echo "::error::$*"
    exit 1
}

# Print a warning without stopping the test suite.
warn() {
    echo "::warning::$*"
}

# Check a Python expression on the content of a YAML file, loaded as 'conf'.
# Usage: assert_yaml <file> <python expression>
assert_yaml() {
    local file="$1"
    local expression="$2"

    python3 - "$file" "$expression" <<'EOF' || fail "assertion failed on ${file}: ${expression}"
import sys
import yaml

with open(sys.argv[1], encoding='utf-8') as stream:
    conf = yaml.safe_load(stream)

if not eval(sys.argv[2], {'conf': conf}):
    print('Content of ' + sys.argv[1] + ':')
    print(yaml.safe_dump(conf, default_flow_style=False))
    sys.exit(1)
EOF

    echo "Assertion OK (${file}): ${expression}"
}

# Run linupdate and check that it fails with exit code 1, prints the expected error
# message and no Python traceback.
# Usage: expect_fail <expected message> <linupdate arguments...>
expect_fail() {
    local expected="$1"
    local output
    local rc=0
    shift

    output=$(linupdate "$@" 2>&1) || rc=$?
    echo "$output"

    [ "$rc" -eq 1 ] || fail "linupdate $*: expected exit code 1, got ${rc}"
    grep -qF -- "$expected" <<< "$output" || fail "linupdate $*: expected error message not found: ${expected}"
    if grep -q "Traceback" <<< "$output"; then
        fail "linupdate $*: unexpected Python traceback"
    fi
}

# Checksum of all linupdate configuration files.
config_checksum() {
    find /etc/linupdate -type f -name '*.yml' -exec md5sum {} + | sort
}

# Version of an installed package.
pkg_version() {
    if [ "$OS_FAMILY" = "debian" ]; then
        dpkg-query -W -f '${Version}' "$1"
    else
        rpm -q --qf '%{VERSION}' "$1"
    fi
}

# Check the version of an installed package.
# Usage: assert_version <package> <expected version>
assert_version() {
    local version
    version=$(pkg_version "$1")

    [ "$version" = "$2" ] || fail "$1: expected version $2, got ${version}"
    echo "Assertion OK: $1 is in version $2"
}

# Hold a linupdate lock from another process, as another linupdate process would do.
# The PID of the holding process is stored in HOLDER_PID.
# Usage: hold_lock <lock name> [duration in seconds]
hold_lock() {
    local ready
    ready=$(mktemp -u)
    mkdir -p "$LOCK_DIR"

    python3 - "${LOCK_DIR}/$1.lock" "${2:-600}" "$ready" <<'EOF' &
import fcntl
import os
import sys
import time

fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o640)
fcntl.flock(fd, fcntl.LOCK_EX)
open(sys.argv[3], 'w').close()
time.sleep(int(sys.argv[2]))
EOF
    HOLDER_PID=$!

    # Wait until the lock is held
    for _ in $(seq 1 100); do
        [ -f "$ready" ] && break
        sleep 0.1
    done
    [ -f "$ready" ] || fail "could not hold the $1 lock"
    rm -f "$ready"
    echo "Lock $1 held by process ${HOLDER_PID}"
}

# Return 0 if a linupdate lock is held by a process.
# Usage: lock_is_held <lock name>
lock_is_held() {
    python3 - "${LOCK_DIR}/$1.lock" <<'EOF'
import fcntl
import os
import sys

fd = os.open(sys.argv[1], os.O_RDONLY)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(0)
sys.exit(1)
EOF
}
