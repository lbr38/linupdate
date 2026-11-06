# Changelog

<!--
Release notes of each version, the most recent first, under a "## <version>" heading matching the version file.
The section of the current version is used by the CI as the GitHub release notes and as the deb and rpm packages changelog
(see .github/scripts/generate-changelog.sh). Format: "**Section**" lines followed by "- item" lines.
-->

## 3.17.5

**Reposerver module**

- Added `--behind-nat` and `--public-ip` parameters to declare a host behind a NAT, its public IP (set manually or retrieved automatically) is then sent to the reposerver along with its local IP (Repomanager 6.3.0 required)
- Network information sent to the reposerver now includes all addresses of each interface and identifies the main interface

**Packages update**

- Packages held (`apt-mark hold`) or excluded (`dnf.conf`) by the administrator are now respected and kept: linupdate only removes the exclusions it has set itself, and never modifies `/etc/dnf/dnf.conf` anymore. These packages are never updated, even with `--ignore-exclusions`
- Package exclusion patterns now support the `*` wildcard (e.g. `php*`), for `--exclude`, `--exclude-major` and exclusions retrieved from a reposerver profile. The legacy regex syntax `.*` (e.g. `php.*`) is still supported
- When the packages configuration is retrieved from the reposerver (`get_packages_conf_from_reposerver` enabled), the execution summary and `--exclude` / `--exclude-major` now warn that the local exclusions will be replaced by the reposerver profile ones before the update
- An empty profile or environment (`profile: ''` or `environment: ''`) in `/etc/linupdate/linupdate.yml` is now a configuration error

**Packaging**

- Package removal now stops and disables the linupdate service, and removes the systemd unit file, the `/usr/bin/linupdate` symlink and the files created at runtime in `/opt/linupdate`. The configuration and the logs are kept, purging the deb package (`apt purge linupdate`) also removes `/etc/linupdate` and `/var/log/linupdate`
- Security: linupdate and the package scripts do not create files in `/tmp` anymore (configuration backup during an upgrade, service restart request, packages update log, trigger files), they now use `/opt/linupdate/tmp`, only accessible by root
- The packages now include a changelog (`/usr/share/doc/linupdate/changelog.gz` for deb, `rpm -q --changelog linupdate` for rpm)

**Other changes**

- Code refactoring (snake_case files and modules, pylint compliance)
