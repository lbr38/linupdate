#!/usr/bin/env bash
#
# Package tests, run in a container running systemd (see start-systemd-container.sh):
#   - upgrade: install the latest released package, configure linupdate, then upgrade to
#     the tested package: the configuration is kept and the service is restarted
#   - systemd service: CPU priority, memory limit and OOM score, reposerver agent,
#     restart request, stop
#   - uninstall
#
# Usage: run-package-tests.sh <tested package file> <directory containing the latest released package>
#
# Configurable via environment variables:
#   REPOSITORY_TEST_URL   : reposerver URL (provided via CI secrets).
#   REPOSITORY_TEST_TOKEN : reposerver API key (provided via CI secrets).
#                           If set, the host is registered and the reposerver agent connection is tested.

set -e

# Shared helpers (OS family, linupdate wrapper, assertions...)
# shellcheck source-path=SCRIPTDIR source=test-helpers.sh
. "$(dirname "$0")/test-helpers.sh"

NEW_PACKAGE="$1"
OLD_PACKAGE_DIR="$2"
SERVICE_UNIT="/lib/systemd/system/linupdate.service"

if [ -n "$REPOSITORY_TEST_URL" ] && [ -n "$REPOSITORY_TEST_TOKEN" ]; then
    WITH_REPOSERVER=true
else
    WITH_REPOSERVER=false
    echo "::notice::REPOSITORY_TEST_URL or REPOSITORY_TEST_TOKEN is not set, skipping the reposerver agent connection test"
fi

if [ "$OS_FAMILY" = "debian" ]; then
    OLD_PACKAGE=$(find "$OLD_PACKAGE_DIR" -name '*.deb' | head -n 1)
else
    OLD_PACKAGE=$(find "$OLD_PACKAGE_DIR" -name '*.rpm' | head -n 1)
fi

[ -f "$NEW_PACKAGE" ] || fail "tested package not found: ${NEW_PACKAGE}"
[ -f "$OLD_PACKAGE" ] || fail "released package not found in ${OLD_PACKAGE_DIR}"

# Version of a package file
file_version() {
    if [ "$OS_FAMILY" = "debian" ]; then
        dpkg-deb -f "$1" Version
    else
        rpm -qp --qf '%{VERSION}' "$1"
    fi
}

install_package_file() {
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-get install -y "$1"
    else
        dnf --nogpgcheck install -y "$1"
    fi
}

reinstall_package_file() {
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-get install -y --reinstall "$1"
    else
        dnf --nogpgcheck reinstall -y "$1"
    fi
}

# Wait for a command to succeed.
# Usage: wait_for <timeout in seconds> <description> <command...>
wait_for() {
    local timeout="$1"
    local description="$2"
    shift 2

    for _ in $(seq 1 "$timeout"); do
        if "$@"; then
            echo "Assertion OK: ${description}"
            return 0
        fi
        sleep 1
    done

    fail "timeout (${timeout}s): ${description}"
}

service_invocation() {
    systemctl show -p InvocationID --value linupdate
}

service_property() {
    systemctl show -p "$1" --value linupdate
}

# Return 0 if the service has been restarted since the given invocation
service_restarted_since() {
    systemctl is-active --quiet linupdate && [ "$(service_invocation)" != "$1" ]
}

assert_service_running() {
    systemctl is-enabled --quiet linupdate || fail "linupdate service is not enabled"
    systemctl is-active --quiet linupdate || fail "linupdate service is not active"
    echo "Assertion OK: linupdate service is enabled and active"
}

# Processes of the linupdate service (main service and module agents)
service_processes() {
    python3 - << 'EOF'
import os
import psutil

for process in psutil.process_iter(['pid', 'cmdline']):
    cmdline = ' '.join(process.info['cmdline'] or [])
    if process.info['pid'] != os.getpid() and '/opt/linupdate/service.py' in cmdline:
        print(str(process.info['pid']) + ' ' + cmdline)
EOF
}

no_service_process() {
    [ -z "$(service_processes)" ]
}

# Return 0 if the service journal (without colors) since the given date matches the pattern
journal_matches() {
    journalctl -u linupdate --since "$1" --no-pager --all | sed 's/\x1b\[[0-9;]*m//g' | grep -qE "$2"
}

# Check a service property after a linupdate command.
# Usage: assert_service_property <property> <expected value>
assert_service_property() {
    local value
    value=$(service_property "$1")

    [ "$value" = "$2" ] || fail "service property $1: expected $2, got ${value}"
    echo "Assertion OK: service property $1=$2"
}

test_install_previous_release() {
    OLD_VERSION=$(file_version "$OLD_PACKAGE")
    NEW_VERSION=$(file_version "$NEW_PACKAGE")
    echo "Latest release: ${OLD_VERSION}, tested package: ${NEW_VERSION}"

    install_package_file "$OLD_PACKAGE"

    assert_version linupdate "$OLD_VERSION"
    wait_for 30 "linupdate service started" systemctl is-active --quiet linupdate
    assert_service_running
}

test_configure() {
    linupdate --profile ci-upgrade
    linupdate --exclude "kernel.*"
    linupdate --mail-recipient test@mail.com
    linupdate --mod-enable reposerver
    linupdate --mod-configure reposerver --url "${REPOSITORY_TEST_URL:-http://127.0.0.1:1}"

    if [ "$WITH_REPOSERVER" = true ]; then
        linupdate --mod-configure reposerver --api-key "$REPOSITORY_TEST_TOKEN" --register
    fi

    REPOSERVER_ID=$(python3 -c "import yaml; print(yaml.safe_load(open('${REPOSERVER_CONF}'))['client']['auth']['id'])")
    INVOCATION_BEFORE_UPGRADE=$(service_invocation)
}

# The configuration is kept and the service is restarted
test_upgrade() {
    if [ "$OLD_VERSION" = "$NEW_VERSION" ]; then
        warn "the latest release has the same version (${NEW_VERSION}) as the tested package: reinstalling it instead of upgrading"
        reinstall_package_file "$NEW_PACKAGE"
    else
        install_package_file "$NEW_PACKAGE"
    fi

    assert_version linupdate "$NEW_VERSION"

    # Configuration kept
    assert_yaml "$LINUPDATE_CONF" "conf['main']['profile'] == 'ci-upgrade'"
    assert_yaml "$LINUPDATE_CONF" "conf['main']['mail']['recipient'] == ['test@mail.com']"
    assert_yaml "$LINUPDATE_CONF" "'reposerver' in conf['modules']['enabled']"
    assert_yaml "$UPDATE_CONF" "conf['update']['packages']['exclude']['always'] == ['kernel.*']"
    assert_yaml "$REPOSERVER_CONF" "conf['reposerver']['url'] == '${REPOSITORY_TEST_URL:-http://127.0.0.1:1}'"
    assert_yaml "$REPOSERVER_CONF" "str(conf['client']['auth']['id']) == '${REPOSERVER_ID}'"

    # Configuration backups made during the upgrade are restored (and never made in /tmp)
    [ ! -e /opt/linupdate/tmp/upgrade-backup ] || fail "configuration backups left in /opt/linupdate/tmp/upgrade-backup"
    if compgen -G "/tmp/*.debsave" > /dev/null || compgen -G "/tmp/*.rpmsave" > /dev/null; then
        fail "configuration backups found in /tmp: $(ls /tmp/*save)"
    fi

    # Controllers directories of linupdate <= 3.17.4 (renamed to lowercase) removed, python cache included
    for dir in App Module Package Service; do
        [ ! -e "/opt/linupdate/src/controllers/${dir}" ] || fail "old controllers directory left: /opt/linupdate/src/controllers/${dir}"
    done

    # Service restarted with the new version
    wait_for 30 "linupdate service restarted by the upgrade" service_restarted_since "$INVOCATION_BEFORE_UPGRADE"
    assert_service_running

    for option in CPUQuota CPUWeight MemoryMax OOMScoreAdjust; do
        grep -q "^${option}=" "$SERVICE_UNIT" || fail "${option} missing in ${SERVICE_UNIT}"
    done

    linupdate --version | grep -qF "$NEW_VERSION" || fail "linupdate --version does not print ${NEW_VERSION}"
}

test_cpu_priority() {
    local priority
    local weight
    local quota

    for setting in low:50:500ms medium:75:750ms high:100:1s; do
        IFS=: read -r priority weight quota <<< "$setting"

        linupdate --cpu-priority "$priority"
        assert_service_property CPUWeight "$weight"
        assert_service_property CPUQuotaPerSecUSec "$quota"
        linupdate --cpu-priority | grep -q "$priority" || fail "--cpu-priority does not print ${priority}"
    done
}

test_memory_limit() {
    linupdate --memory-limit 512M
    assert_service_property MemoryMax 536870912
    linupdate --memory-limit | grep -qF 512M || fail "--memory-limit does not print 512M"
}

test_oom_score() {
    linupdate --oom-score 300
    assert_service_property OOMScoreAdjust 300
    linupdate --oom-score | grep -qF 300 || fail "--oom-score does not print 300"
}

# The service restarts itself when a restart is requested (e.g. after linupdate has been updated by the agent)
test_restart_request() {
    local invocation
    local main_pid
    invocation=$(service_invocation)

    touch /opt/linupdate/tmp/restart-needed

    wait_for 60 "linupdate service restarted itself" service_restarted_since "$invocation"
    [ ! -f /opt/linupdate/tmp/restart-needed ] || fail "/opt/linupdate/tmp/restart-needed has not been removed"

    # The settings are applied to the restarted service
    main_pid=$(service_property MainPID)
    [ "$(cat "/proc/${main_pid}/oom_score_adj")" = "300" ] || fail "OOM score of the restarted service is not 300"
    echo "Assertion OK: OOM score applied to the restarted service"
}

# The service starts the reposerver agent, which connects to the reposerver
test_reposerver_agent() {
    local since
    since=$(date '+%Y-%m-%d %H:%M:%S')

    linupdate --mod-configure reposerver --agent-enable true
    linupdate --mod-configure reposerver --agent-listen-enable true

    wait_for 60 "reposerver agent started by the service" journal_matches "$since" "Starting reposerver module agent"

    if [ "$WITH_REPOSERVER" = true ]; then
        wait_for 120 "reposerver agent authenticated to the reposerver" journal_matches "$since" "Authentication successful"
    fi
}

# Stopping the service also stops the module agents
test_stop() {
    systemctl stop linupdate
    wait_for 30 "linupdate service and agents stopped" no_service_process

    systemctl start linupdate
    wait_for 30 "linupdate service started" systemctl is-active --quiet linupdate
}

test_uninstall() {
    if [ "$WITH_REPOSERVER" = true ]; then
        linupdate --mod-configure reposerver --unregister
    fi

    if [ "$OS_FAMILY" = "debian" ]; then
        apt-get remove -y linupdate
        # dpkg forgets the package once removed (no conffiles), dpkg-query then fails
        if dpkg-query -W -f '${Status}' linupdate 2> /dev/null | grep -q "ok installed"; then
            fail "linupdate package is still installed"
        fi
    else
        dnf remove -y linupdate
        if rpm -q linupdate; then
            fail "linupdate package is still installed"
        fi
    fi

    [ ! -e /opt/linupdate/linupdate.py ] || fail "/opt/linupdate/linupdate.py still exists"
    [ -f "$LINUPDATE_CONF" ] || fail "the configuration has been removed"
    echo "Assertion OK: package removed, configuration kept"

    # Service stopped and disabled, files created outside of the package files removed
    wait_for 15 "linupdate service and agents stopped" no_service_process
    if systemctl is-enabled --quiet linupdate 2> /dev/null; then
        fail "linupdate service is still enabled after the package removal"
    fi
    if [ -e /etc/systemd/system/multi-user.target.wants/linupdate.service ] || [ -L /etc/systemd/system/multi-user.target.wants/linupdate.service ]; then
        fail "linupdate service is still enabled (multi-user.target.wants) after the package removal"
    fi
    [ ! -e "$SERVICE_UNIT" ] || fail "${SERVICE_UNIT} is still present after the package removal"
    if [ -e /usr/bin/linupdate ] || [ -L /usr/bin/linupdate ]; then
        fail "/usr/bin/linupdate is still present after the package removal"
    fi
    if [ -e /opt/linupdate ]; then
        fail "/opt/linupdate is still present after the package removal: $(find /opt/linupdate -mindepth 1 -maxdepth 2 | tr '\n' ' ')"
    fi
    echo "Assertion OK: service stopped and disabled, unit file, symlink and runtime files removed"

    # Purge (deb only): the configuration and the logs are removed
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-get purge -y linupdate
        [ ! -e /etc/linupdate ] || fail "/etc/linupdate is still present after the package purge"
        [ ! -e /var/log/linupdate ] || fail "/var/log/linupdate is still present after the package purge"
        echo "Assertion OK: configuration and logs removed by the purge"
    fi
}

run_test "prepare system" bash "$(dirname "$0")/setup-system.sh" --no-update

run_test "install the latest release" test_install_previous_release

run_test "configure linupdate" test_configure

run_test "upgrade to the tested package" test_upgrade

run_test "service CPU priority" test_cpu_priority

run_test "service memory limit" test_memory_limit

run_test "service OOM score" test_oom_score

run_test "service restart request" test_restart_request

run_test "reposerver agent" test_reposerver_agent

run_test "stop the service" test_stop

run_test "uninstall" test_uninstall

echo "All package tests passed."
