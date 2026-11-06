#!/usr/bin/env bash
#
# Common linupdate test suite shared across all CI install-and-test jobs.
#
# This script centralizes the test commands that were previously duplicated in
# every per-OS workflow/job. Each calling job only needs to handle its own
# OS-specific setup (repositories, package install) and then run this script.
#
# Besides checking exit codes, the tests check the resulting state (configuration
# files, installed package versions, repository files) and that invalid arguments
# are rejected.
#
# Configurable via environment variables:
#   LINUPDATE_CMD         : see test-helpers.sh.
#   LINUPDATE_PROFILE     : profile to switch to (default: "ci-default").
#   REPOS_CONFIG_DIR      : directory of the repository configuration files.
#   REPOSITORY_TEST_URL   : reposerver URL (provided via CI secrets).
#   REPOSITORY_TEST_TOKEN : reposerver API key (provided via CI secrets).
#                           If the URL or the API key is empty (local run, pull request
#                           from a fork), the tests needing a reposerver are skipped.

set -e

# Shared helpers (OS family, linupdate wrapper, assertions...)
# shellcheck source-path=SCRIPTDIR source=test-helpers.sh
. "$(dirname "$0")/test-helpers.sh"

LINUPDATE_PROFILE="${LINUPDATE_PROFILE:-ci-default}"

# Local repository providing dummy packages, to test exclusions without depending on
# the updates available on the distribution. The packages are installed in version 1.0
# and the repository provides:
#   linupdate-ci-excluded : 1.1 (always excluded)
#   linupdate-ci-major    : 2.0 (major update, excluded on major update)
#   linupdate-ci-minor    : 1.1 (minor update, matches the major update exclusions but must be installed)
#   linupdate-ci-held     : 1.1 (excluded by the administrator with apt-mark hold or in dnf.conf, must never be updated)
CI_REPO_DIR="/tmp/linupdate-ci-repo"
DUMMY_PACKAGES="linupdate-ci-excluded linupdate-ci-major linupdate-ci-minor linupdate-ci-held"
DUMMY_PACKAGES_LIST="linupdate-ci-excluded,linupdate-ci-major,linupdate-ci-minor,linupdate-ci-held"

# List of all installed packages with their version.
installed_packages() {
    if [ "$OS_FAMILY" = "debian" ]; then
        dpkg-query -W -f '${Package} ${Version}\n' | sort
    else
        rpm -qa --qf '%{NAME} %{EPOCH}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | sort
    fi
}

# Package exclusions set at system level (apt holds, dnf.conf exclusions).
exclusions_snapshot() {
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-mark showhold | sort
    else
        grep -E '^(exclude|excludepkgs) *=' /etc/dnf/dnf.conf || true
    fi
}

# Exclusions set by the administrator (updated when the CI sets some)
ADMIN_EXCLUSIONS=$(exclusions_snapshot)

# Check that linupdate removed its own exclusions and kept the administrator ones.
assert_exclusions_restored() {
    local current
    current=$(exclusions_snapshot)

    [ "$current" = "$ADMIN_EXCLUSIONS" ] || fail "package exclusions are not restored. Expected: '${ADMIN_EXCLUSIONS}', got: '${current}'"
    echo "Assertion OK: package exclusions restored ('${ADMIN_EXCLUSIONS}')"
}

# Exclude a package the way an administrator would.
admin_exclude() {
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-mark hold "$1"
    else
        sed -i "/^\[main\]/a exclude=$1" /etc/dnf/dnf.conf
    fi
    ADMIN_EXCLUSIONS=$(exclusions_snapshot)
}

admin_unexclude() {
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-mark unhold "$1"
    else
        sed -i "/^exclude=$1\$/d" /etc/dnf/dnf.conf
    fi
    ADMIN_EXCLUSIONS=$(exclusions_snapshot)
}

# Build a dummy package.
# Usage: build_dummy_package <name> <version> <output directory>
build_dummy_package() {
    local name="$1"
    local version="$2"
    local output_dir="$3"
    local build_dir
    build_dir=$(mktemp -d)

    if [ "$OS_FAMILY" = "debian" ]; then
        mkdir -p "${build_dir}/DEBIAN"
        chmod 755 "$build_dir" "${build_dir}/DEBIAN"
        cat > "${build_dir}/DEBIAN/control" << EOF
Package: ${name}
Version: ${version}
Architecture: all
Maintainer: linupdate CI <ci@linupdate.invalid>
Description: Dummy package used by linupdate CI tests
EOF
        dpkg-deb --build "$build_dir" "${output_dir}/${name}_${version}_all.deb"
    else
        cat > "${build_dir}/dummy.spec" << EOF
Name: ${name}
Version: ${version}
Release: 1
Summary: Dummy package used by linupdate CI tests
License: GPL-3.0
BuildArch: noarch

%description
Dummy package used by linupdate CI tests

%files
EOF
        rpmbuild --quiet -bb --define "_topdir ${build_dir}" "${build_dir}/dummy.spec"
        find "${build_dir}/RPMS" -name '*.rpm' -exec cp {} "$output_dir" \;
    fi

    rm -rf "$build_dir"
}

install_test_dependencies() {
    if [ "$OS_FAMILY" = "debian" ]; then
        apt-get install -y cowsay
    elif [ "$OS_FAMILY" = "rhel" ]; then
        dnf install -y cowsay
        # To build the dummy packages and their repository
        dnf install -y rpm-build createrepo_c
    fi
}

# Install the dummy packages in version 1.0 and publish their new version in a local repository.
setup_ci_repository() {
    local old_dir
    old_dir=$(mktemp -d)
    rm -rf "$CI_REPO_DIR"
    mkdir -p "$CI_REPO_DIR"

    build_dummy_package linupdate-ci-excluded 1.0 "$old_dir"
    build_dummy_package linupdate-ci-major 1.0 "$old_dir"
    build_dummy_package linupdate-ci-minor 1.0 "$old_dir"
    build_dummy_package linupdate-ci-held 1.0 "$old_dir"
    build_dummy_package linupdate-ci-excluded 1.1 "$CI_REPO_DIR"
    build_dummy_package linupdate-ci-major 2.0 "$CI_REPO_DIR"
    build_dummy_package linupdate-ci-minor 1.1 "$CI_REPO_DIR"
    build_dummy_package linupdate-ci-held 1.1 "$CI_REPO_DIR"

    if [ "$OS_FAMILY" = "debian" ]; then
        # Flat repository index
        (
            cd "$CI_REPO_DIR"
            for deb in *.deb; do
                dpkg-deb -f "$deb"
                echo "Filename: ./${deb}"
                echo "Size: $(stat -c %s "$deb")"
                echo "SHA256: $(sha256sum "$deb" | cut -d ' ' -f 1)"
                echo
            done > Packages
        )
        echo "deb [trusted=yes] file:${CI_REPO_DIR} ./" > /etc/apt/sources.list.d/linupdate-ci.list
        apt-get update -y
        apt-get install -y "$old_dir"/*.deb
    else
        createrepo_c "$CI_REPO_DIR"
        cat > /etc/yum.repos.d/linupdate-ci.repo << EOF
[linupdate-ci]
name=linupdate CI dummy packages
baseurl=file://${CI_REPO_DIR}
enabled=1
gpgcheck=0
EOF
        dnf --nogpgcheck install -y "$old_dir"/*.rpm
    fi

    rm -rf "$old_dir"

    admin_exclude linupdate-ci-held

    for package in $DUMMY_PACKAGES; do
        assert_version "$package" 1.0
    done
}

remove_ci_repository() {
    admin_unexclude linupdate-ci-held

    if [ "$OS_FAMILY" = "debian" ]; then
        # shellcheck disable=SC2086
        apt-get purge -y $DUMMY_PACKAGES
        rm -f /etc/apt/sources.list.d/linupdate-ci.list
    else
        # shellcheck disable=SC2086
        dnf remove -y $DUMMY_PACKAGES
        rm -f /etc/yum.repos.d/linupdate-ci.repo
    fi

    rm -rf "$CI_REPO_DIR"
}

# Only one linupdate can run at a time: a second one fails at once, without releasing
# the lock of the first one. A killed linupdate does not leave a stale lock.
test_run_lock() {
    local start
    local elapsed

    hold_lock linupdate

    start=$(date +%s)
    LINUPDATE_CMD="timeout 120 ${LINUPDATE_CMD}" expect_fail "linupdate is already running" --check-updates
    elapsed=$(( $(date +%s) - start ))
    [ "$elapsed" -lt 60 ] || fail "linupdate waited ${elapsed}s instead of failing at once"

    lock_is_held linupdate || fail "the second linupdate released the lock of the first one"
    echo "Assertion OK: the lock is still held by the first linupdate"

    # Simulate a crash of the first linupdate
    kill -9 "$HOLDER_PID"
    wait "$HOLDER_PID" 2> /dev/null || true

    if lock_is_held linupdate; then
        fail "the lock is still held after its holder was killed"
    fi
    echo "Assertion OK: the lock is released when its holder dies"

    linupdate --check-updates
}

# linupdate waits for the package manager lock held by another process, then runs
test_package_lock_wait() {
    local start
    local elapsed

    hold_lock package 8

    start=$(date +%s)
    timeout 300 bash -c "${LINUPDATE_CMD} --check-updates"
    elapsed=$(( $(date +%s) - start ))

    wait "$HOLDER_PID" || true
    [ "$elapsed" -ge 5 ] || fail "linupdate did not wait for the package lock (ran in ${elapsed}s)"
    echo "Assertion OK: linupdate waited ${elapsed}s for the package lock"
}

# --check-updates must not change anything
test_check_updates() {
    local before
    before=$(installed_packages)

    linupdate --check-updates

    [ "$(installed_packages)" = "$before" ] || fail "installed packages changed with --check-updates"
    assert_exclusions_restored
}

# --dry-run must not change anything, even when ignoring exclusions
test_dry_run() {
    local before
    local output
    before=$(installed_packages)

    output=$(linupdate --update "$DUMMY_PACKAGES_LIST" --ignore-exclusions --dry-run --assume-yes 2>&1)
    echo "$output"
    # Without colors, to check the messages
    # shellcheck disable=SC2001
    output=$(sed 's/\x1b\[[0-9;]*m//g' <<< "$output")

    [ "$(installed_packages)" = "$before" ] || fail "installed packages changed with --dry-run"
    grep -q "packages would be updated, 0 packages would fail" <<< "$output" || fail "dry run summary not found"
    if grep -qE "packages updated,|updated successfully" <<< "$output"; then
        fail "dry run claims that packages were updated"
    fi
    # Versions are printed as they are (1.0 must not be printed as 1)
    grep -qE "linupdate-ci-major +1\.0[^ ]* +2\.0" <<< "$output" || fail "versions of linupdate-ci-major not printed as 1.0 => 2.0"
    for package in $DUMMY_PACKAGES; do
        assert_version "$package" 1.0
    done
    assert_exclusions_restored
}

# Excluded packages and major updates matching the major update exclusions must not be installed
test_exclusions() {
    linupdate --update "$DUMMY_PACKAGES_LIST" --assume-yes

    assert_version linupdate-ci-excluded 1.0
    assert_version linupdate-ci-major 1.0
    assert_version linupdate-ci-minor 1.1
    assert_version linupdate-ci-held 1.0
    assert_exclusions_restored
}

# --ignore-exclusions must install excluded packages, but not the ones excluded by the administrator
test_ignore_exclusions() {
    linupdate --update "$DUMMY_PACKAGES_LIST" --ignore-exclusions --assume-yes

    assert_version linupdate-ci-excluded 1.1
    assert_version linupdate-ci-major 2.0
    assert_version linupdate-ci-minor 1.1
    assert_version linupdate-ci-held 1.0
    assert_exclusions_restored
}

# A full update must not update the packages excluded by the administrator
test_full_update_keeps_admin_exclusions() {
    linupdate --assume-yes

    assert_version linupdate-ci-held 1.0
    assert_exclusions_restored
}

# Repositories retrieved from the reposerver: existing ones removed, new ones in the configured format
check_reposerver_repositories() {
    local file
    local key

    ls -l "$REPOS_CONFIG_DIR"/

    [ ! -e "${REPOS_CONFIG_DIR}/${REPO_MARKER_FILE}" ] || fail "existing repositories were not removed (${REPO_MARKER_FILE} still exists)"

    if [ "$OS_FAMILY" = "debian" ]; then
        [ ! -s /etc/apt/sources.list ] || fail "/etc/apt/sources.list was not emptied"

        compgen -G "${REPOS_CONFIG_DIR}/*.sources" > /dev/null || fail "no deb822 .sources file in ${REPOS_CONFIG_DIR}"
        if compgen -G "${REPOS_CONFIG_DIR}/*.list" > /dev/null; then
            fail "legacy .list files found while deb822 format is configured"
        fi

        for file in "$REPOS_CONFIG_DIR"/*.sources; do
            echo "--- ${file}"
            cat "$file"
            grep -q '^Types: deb$' "$file" || fail "${file}: missing 'Types: deb'"
            grep -q '^URIs: ' "$file" || fail "${file}: missing 'URIs:'"
            key=$(sed -n 's/^Signed-By: //p' "$file" | head -n 1)
            if [ -z "$key" ] || [ ! -f "$key" ]; then
                fail "${file}: GPG key '${key}' does not exist"
            fi
        done
    else
        compgen -G "${REPOS_CONFIG_DIR}/*.repo" > /dev/null || fail "no .repo file in ${REPOS_CONFIG_DIR}"

        for file in "$REPOS_CONFIG_DIR"/*.repo; do
            echo "--- ${file}"
            cat "$file"
            grep -q '^baseurl=' "$file" || fail "${file}: missing baseurl"
            grep -q '^gpgcheck=1$' "$file" || fail "${file}: gpgcheck is not enabled"
        done
    fi

    if grep -rq '__ENV__' "$REPOS_CONFIG_DIR"; then
        fail "__ENV__ placeholder not replaced in repository files"
    fi

    echo "Assertion OK: repositories configured from the reposerver"
}


#
# Basic commands
#

run_test "install test dependencies" install_test_dependencies

run_test "print help" \
    linupdate --help

run_test "print configuration" \
    linupdate --show-config

run_test "print version" \
    linupdate --version

#
# Configuration
#

run_test "switch profile" \
    linupdate --profile "$LINUPDATE_PROFILE"
assert_yaml "$LINUPDATE_CONF" "conf['main']['profile'] == '${LINUPDATE_PROFILE}'"

run_test "switch environment" \
    linupdate --env prod
assert_yaml "$LINUPDATE_CONF" "conf['main']['environment'] == 'prod'"

run_test "disable mail" \
    linupdate --mail-enable false
assert_yaml "$LINUPDATE_CONF" "conf['main']['mail']['enabled'] is False"

run_test "set mail recipient" \
    linupdate --mail-recipient test@mail.com,test2@mail.com
assert_yaml "$LINUPDATE_CONF" "conf['main']['mail']['recipient'] == ['test@mail.com', 'test2@mail.com']"

run_test "set mail smtp host" \
    linupdate --mail-smtp-host localhost
assert_yaml "$LINUPDATE_CONF" "conf['main']['mail']['smtp_host'] == 'localhost'"

run_test "get mail smtp host" \
    linupdate --mail-smtp-host

run_test "set mail smtp port" \
    linupdate --mail-smtp-port 25
assert_yaml "$LINUPDATE_CONF" "conf['main']['mail']['smtp_port'] == 25"

run_test "get mail smtp port" \
    linupdate --mail-smtp-port

run_test "set log retention days" \
    linupdate --log-retention-days 30
assert_yaml "$LINUPDATE_CONF" "conf['main']['log_retention_days'] == 30"

run_test "enable exit on package update error" \
    linupdate --exit-on-package-update-error true
assert_yaml "$UPDATE_CONF" "conf['update']['exit_on_package_update_error'] is True"

run_test "set package exclusions" \
    linupdate --exclude "kernel.*,linupdate-ci-excluded"
assert_yaml "$UPDATE_CONF" "conf['update']['packages']['exclude']['always'] == ['kernel.*', 'linupdate-ci-excluded']"

run_test "get package exclusions" \
    linupdate --exclude

run_test "set package exclusions on major update" \
    linupdate --exclude-major "nginx,mysql.*,linupdate-ci-major,linupdate-ci-minor"
assert_yaml "$UPDATE_CONF" "conf['update']['packages']['exclude']['on_major_update'] == ['nginx', 'mysql.*', 'linupdate-ci-major', 'linupdate-ci-minor']"

run_test "get package exclusions on major update" \
    linupdate --exclude-major

run_test "set services to reload after update" \
    linupdate --service-reload "php-fpm"
assert_yaml "$UPDATE_CONF" "conf['post_update']['services']['reload'] == ['php-fpm']"

run_test "set services to restart after update" \
    linupdate --service-restart "nginx,mysql"
assert_yaml "$UPDATE_CONF" "conf['post_update']['services']['restart'] == ['nginx', 'mysql']"

run_test "get services to restart after update" \
    linupdate --service-restart

#
# Invalid arguments: exit code 1, an error message, and the configuration left untouched
#

CONFIG_CHECKSUM=$(config_checksum)

run_test "reject unknown argument" \
    expect_fail "Unknown argument(s)" --this-option-does-not-exist

run_test "reject unknown module (enable)" \
    expect_fail "does not exist" --mod-enable linupdate-ci-no-such-module

run_test "reject unknown module (configure)" \
    expect_fail "does not exist" --mod-configure linupdate-ci-no-such-module --url http://localhost

run_test "reject module configuration without arguments" \
    expect_fail "requires additional arguments" --mod-configure

run_test "reject non-integer log retention days" \
    expect_fail "must be an integer" --log-retention-days abc

run_test "reject negative log retention days" \
    expect_fail "must be >= 0" --log-retention-days=-5

run_test "reject non-integer smtp port" \
    expect_fail "Could not set mail SMTP port" --mail-smtp-port abc

run_test "reject invalid cpu priority" \
    expect_fail "Priority must be low, medium or high" --cpu-priority extreme

run_test "reject out of range OOM score" \
    expect_fail "OOM score must be between -1000 and 1000" --oom-score 5000

run_test "reject --update without package" \
    expect_fail "Package(s) name must be specified" --update

[ "$(config_checksum)" = "$CONFIG_CHECKSUM" ] || fail "configuration files changed after rejected arguments"
echo "Assertion OK: configuration unchanged after rejected arguments"

#
# Locks
#

run_test "only one linupdate can run at a time" test_run_lock

run_test "wait for the package manager lock" test_package_lock_wait

#
# Packages update
#

run_test "check updates" test_check_updates

run_test "setup CI repository with dummy packages" setup_ci_repository

run_test "dry run does not update anything" test_dry_run

run_test "excluded packages are not updated" test_exclusions

run_test "ignore exclusions" test_ignore_exclusions

run_test "update specific packages" \
    linupdate --update "curl,wget,nginx" --assume-yes
assert_exclusions_restored

run_test "update all packages" test_full_update_keeps_admin_exclusions

run_test "remove CI repository and dummy packages" remove_ci_repository

#
# Reposerver module
#

run_test "list available modules" \
    linupdate --mod-list

run_test "enable reposerver module" \
    linupdate --mod-enable reposerver
assert_yaml "$LINUPDATE_CONF" "'reposerver' in conf['modules']['enabled']"
assert_yaml "$REPOSERVER_CONF" "conf['reposerver']['url'] == ''"

# Without CI secrets, use a dummy URL for the tests that do not reach the reposerver
REPOSERVER_URL="${REPOSITORY_TEST_URL:-http://127.0.0.1:1}"

run_test "configure reposerver module" \
    linupdate --mod-configure reposerver --url "$REPOSERVER_URL"
assert_yaml "$REPOSERVER_CONF" "conf['reposerver']['url'] == '${REPOSERVER_URL%/}'"

CONFIG_CHECKSUM=$(config_checksum)

run_test "reject reposerver URL without http(s) scheme" \
    expect_fail "reposerver URL must start with http:// or https://" --mod-configure reposerver --url ftp://reposerver.example.com

run_test "reject unknown source repository format" \
    expect_fail "source repo format must be set to" --mod-configure reposerver --source-repo-format foo

run_test "reject unknown reposerver argument" \
    expect_fail "Unknown argument(s)" --mod-configure reposerver --this-option-does-not-exist

run_test "reject register without API key" \
    expect_fail "you must specify an API key" --mod-configure reposerver --register

run_test "reject register with invalid IP" \
    expect_fail "invalid IP address" --mod-configure reposerver --register --api-key dummy --ip not-an-ip

run_test "reject unregister when not registered" \
    expect_fail "no auth Id found in configuration" --mod-configure reposerver --unregister

[ "$(config_checksum)" = "$CONFIG_CHECKSUM" ] || fail "configuration files changed after rejected reposerver arguments"
echo "Assertion OK: configuration unchanged after rejected reposerver arguments"

if [ -z "$REPOSITORY_TEST_URL" ] || [ -z "$REPOSITORY_TEST_TOKEN" ]; then
    echo "::notice::REPOSITORY_TEST_URL or REPOSITORY_TEST_TOKEN is not set, skipping the tests needing a reposerver"
else
    run_test "register to reposerver" \
        linupdate --mod-configure reposerver --api-key "${REPOSITORY_TEST_TOKEN}" --register
    assert_yaml "$REPOSERVER_CONF" "conf['client']['auth']['id'] and conf['client']['auth']['token']"

    run_test "send all informations to reposerver" \
        linupdate --mod-configure reposerver --send-all-info

    run_test "enable reposerver module to get packages configuration from reposerver" \
        linupdate --mod-configure reposerver --get-packages-conf-from-reposerver true
    assert_yaml "$REPOSERVER_CONF" "conf['client']['get_packages_conf_from_reposerver']['enabled'] is True"

    run_test "enable reposerver module to get repositories configuration from reposerver" \
        linupdate --mod-configure reposerver --get-repos-from-reposerver true
    assert_yaml "$REPOSERVER_CONF" "conf['client']['get_repos_from_reposerver']['enabled'] is True"

    run_test "enable reposerver module to remove existing repositories before adding new ones" \
        linupdate --mod-configure reposerver --remove-existing-repos true
    assert_yaml "$REPOSERVER_CONF" "conf['client']['get_repos_from_reposerver']['remove_existing_repos'] is True"

    run_test "use deb822 format for deb repository configuration files" \
        linupdate --mod-configure reposerver --source-repo-format deb822
    assert_yaml "$REPOSERVER_CONF" "conf['client']['get_repos_from_reposerver']['format'] == 'deb822'"

    # Marker file that must be removed with the existing repositories
    if [ "$OS_FAMILY" = "debian" ]; then
        REPO_MARKER_FILE="linupdate-ci-marker.list"
    else
        REPO_MARKER_FILE="linupdate-ci-marker.repo"
    fi
    echo "# linupdate CI marker, must be removed by --remove-existing-repos" > "${REPOS_CONFIG_DIR}/${REPO_MARKER_FILE}"

    run_test "launch linupdate with reposerver module enabled" \
        linupdate --assume-yes
    assert_exclusions_restored

    run_test "check repositories retrieved from reposerver" check_reposerver_repositories

    run_test "unregister from reposerver" \
        linupdate --mod-configure reposerver --unregister
    assert_yaml "$REPOSERVER_CONF" "conf['client']['auth']['id'] == '' and conf['client']['auth']['token'] == ''"
fi

run_test "disable reposerver module" \
    linupdate --mod-disable reposerver
assert_yaml "$LINUPDATE_CONF" "'reposerver' not in conf['modules']['enabled']"

echo "All tests passed."
