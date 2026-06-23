#!/usr/bin/env bash
#
# Common linupdate test suite shared across all CI install-and-test jobs.
#
# This script centralizes the test commands that were previously duplicated in
# every per-OS workflow/job. Each calling job only needs to handle its own
# OS-specific setup (repositories, package install) and then run this script.
#
# Configurable via environment variables:
#   LINUPDATE_CMD : command used to invoke linupdate
#                   (default: "python3 /opt/linupdate/linupdate.py").
#                   Set to "sudo python3 /opt/linupdate/linupdate.py" where sudo
#                   is required (e.g. latest Ubuntu).
#   REPOSITORY_TEST_URL   : reposerver URL (provided via CI secrets).
#   REPOSITORY_TEST_TOKEN : reposerver API key (provided via CI secrets).

set -e

LINUPDATE_CMD="${LINUPDATE_CMD:-python3 /opt/linupdate/linupdate.py}"
LINUPDATE_PROFILE="${LINUPDATE_PROFILE:ci-default}"

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

run_test "print help" \
    linupdate --help

run_test "print configuration" \
    linupdate --show-config

run_test "print version" \
    linupdate --version

run_test "switch profile" \
    linupdate --profile $LINUPDATE_PROFILE

run_test "switch environment" \
    linupdate --env prod

run_test "disable mail" \
    linupdate --mail-enable false

run_test "set mail recipient" \
    linupdate --mail-recipient test@mail.com,test2@mail.com

run_test "set mail smtp host" \
    linupdate --mail-smtp-host localhost

run_test "get mail smtp host" \
    linupdate --mail-smtp-host

run_test "set mail smtp port" \
    linupdate --mail-smtp-port 25

run_test "get mail smtp port" \
    linupdate --mail-smtp-port

run_test "set package exclusions" \
    linupdate --exclude "kernel.*"

run_test "get package exclusions" \
    linupdate --exclude

run_test "set package exclusions on major update" \
    linupdate --exclude-major "nginx,mysql.*"

run_test "get package exclusions on major update" \
    linupdate --exclude-major

run_test "set services to reload after update" \
    linupdate --service-reload "php-fpm"

run_test "set services to restart after update" \
    linupdate --service-restart "nginx,mysql"

run_test "get services to restart after update" \
    linupdate --service-restart

run_test "check updates" \
    linupdate --check-updates

run_test "update specific packages" \
    linupdate --update "curl,wget,nginx" --assume-yes

run_test "update all packages" \
    linupdate --assume-yes

run_test "list available modules" \
    linupdate --mod-list

run_test "enable reposerver module" \
    linupdate --mod-enable reposerver

run_test "configure reposerver module" \
    linupdate --mod-configure reposerver --url "${REPOSITORY_TEST_URL}"

run_test "register to reposerver" \
    linupdate --mod-configure reposerver --api-key "${REPOSITORY_TEST_TOKEN}" --register

run_test "send all informations to reposerver" \
    linupdate --mod-configure reposerver --send-all-info

run_test "enable reposerver module to get packages configuration from reposerver" \
    linupdate --mod-configure reposerver --get-packages-conf-from-reposerver true

run_test "enable reposerver module to get repositories configuration from reposerver" \
    linupdate --mod-configure reposerver --get-repos-from-reposerver true

run_test "enable reposerver module to remove existing repositories before adding new ones" \
    linupdate --mod-configure reposerver --remove-existing-repos true

run_test "use deb822 format for deb repository configuration files" \
    linupdate --mod-configure reposerver --source-repo-format deb822

run_test "launch linupdate with reposerver module enabled" \
    linupdate --assume-yes

run_test "show repository config files" \
    ls -l $REPOS_CONFIG_DIR/

run_test "show repository config files content" \
    cat $REPOS_CONFIG_DIR/*

run_test "unregister from reposerver" \
    linupdate --mod-configure reposerver --unregister

echo "All tests passed."
