"""Unit tests for the package exclusion rules applied before an update."""

from unittest.mock import MagicMock

import pytest

from src.controllers.package.package import Package

EXCLUDED = '✕ (excluded)'


def pkg(name, current='1.0.0-1', target='1.0.1-1', **extra) -> dict:
    """Build a package entry as returned by the package manager controllers"""
    package = {'name': name, 'current_version': current, 'target_version': target}
    package.update(extra)
    return package


def run_exclude(packages, always=(), on_major_update=(), ignore_exclusions=False, system_exclusions=()) -> tuple:
    """Run Package.exclude() on packages and return {name: package} and the names passed to the package manager"""
    controller = Package.__new__(Package)
    controller.app_config_controller = MagicMock()
    controller.app_config_controller.get_conf.return_value = {
        'update': {
            'packages': {
                'exclude': {
                    'always': list(always),
                    'on_major_update': list(on_major_update)
                }
            }
        }
    }
    controller.my_package_manager_controller = MagicMock()
    controller.my_package_manager_controller.get_exclusion.return_value = list(system_exclusions)
    controller.packages_to_update_list = packages

    controller.exclude(ignore_exclusions)

    excluded = [call[0][0] for call in controller.my_package_manager_controller.exclude.call_args_list]

    return {package['name']: package for package in controller.packages_to_update_list}, excluded


def test_no_exclusion() -> None:
    """Without exclusion rules every package is installed"""
    result, excluded = run_exclude([pkg('curl'), pkg('nginx')])

    assert all(package['install'] for package in result.values())
    assert all(package['install_decision_message'] == '' for package in result.values())
    assert not excluded


def test_always_exclusion_supports_regex() -> None:
    """'always' patterns are regular expressions"""
    result, excluded = run_exclude([pkg('kernel-core'), pkg('kernel-modules'), pkg('curl')], always=['kernel.*'])

    assert not result['kernel-core']['install']
    assert not result['kernel-modules']['install']
    assert result['kernel-core']['install_decision_message'] == EXCLUDED
    assert result['curl']['install']
    assert excluded == ['kernel-core', 'kernel-modules']


def test_exclusion_pattern_must_match_whole_name() -> None:
    """A pattern must match the whole package name: 'nginx' does not exclude 'nginx-common'"""
    result, excluded = run_exclude([pkg('nginx'), pkg('nginx-common'), pkg('libnginx-mod-http')], always=['nginx'])

    assert not result['nginx']['install']
    assert result['nginx-common']['install']
    assert result['libnginx-mod-http']['install']
    assert excluded == ['nginx']


def test_exclusion_pattern_with_wildcard() -> None:
    """'.*' is needed to exclude every package starting with a name"""
    result, _ = run_exclude([pkg('nginx'), pkg('nginx-common'), pkg('libnginx-mod-http')], always=['nginx.*'])

    assert not result['nginx']['install']
    assert not result['nginx-common']['install']
    assert result['libnginx-mod-http']['install']


def test_major_update_pattern_must_match_whole_name() -> None:
    """'on_major_update' patterns must also match the whole package name"""
    result, _ = run_exclude([pkg('php', '7.4', '8.2'), pkg('php-fpm', '7.4', '8.2')], on_major_update=['php'])

    assert not result['php']['install']
    assert result['php-fpm']['install']


def test_several_always_patterns() -> None:
    """Several patterns can be combined"""
    result, _ = run_exclude([pkg('mysql-server'), pkg('php8.2-fpm'), pkg('curl')], always=['mysql.*', 'php.*'])

    assert not result['mysql-server']['install']
    assert not result['php8.2-fpm']['install']
    assert result['curl']['install']


@pytest.mark.parametrize('current, target, install', [
    ('1.22.1-9', '1.24.0-1', True),         # minor update
    ('1.22.1-9', '2.0.0-1', False),         # major update
    ('1:9.18.24-1', '1:9.18.28-1', True),   # same epoch and major
    ('1:9.18.24-1', '1:10.0.1-1', False),   # major update with epoch
])
def test_major_update_exclusion(current, target, install) -> None:
    """'on_major_update' patterns only exclude updates where the first version digit changes"""
    result, excluded = run_exclude([pkg('nginx', current, target)], on_major_update=['nginx'])

    assert result['nginx']['install'] is install
    assert excluded == ([] if install else ['nginx'])


def test_major_update_exclusion_ignores_other_packages() -> None:
    """A major update of a package not matching 'on_major_update' is installed"""
    result, excluded = run_exclude([pkg('curl', '7.88.1-10', '8.5.0-2')], on_major_update=['mysql.*'])

    assert result['curl']['install']
    assert not excluded


def test_ignore_exclusions() -> None:
    """ignore_exclusions disables every rule"""
    result, excluded = run_exclude([pkg('curl', '7.0', '8.0')], always=['curl'], on_major_update=['curl'], ignore_exclusions=True)

    assert result['curl']['install']
    assert not excluded


def test_package_already_marked_not_to_install_is_kept() -> None:
    """A package already marked as not to install keeps its decision"""
    package = pkg('nginx', install=False, install_decision_message='✕ Package is not installed')
    result, excluded = run_exclude([package], always=['nginx'])

    assert not result['nginx']['install']
    assert result['nginx']['install_decision_message'] == '✕ Package is not installed'
    assert not excluded


@pytest.mark.parametrize('ignore_exclusions', [False, True])
def test_package_excluded_by_system_is_never_updated(ignore_exclusions) -> None:
    """A package held by the administrator is not updated, even with ignore_exclusions, and linupdate does not exclude it again"""
    result, excluded = run_exclude([pkg('nginx'), pkg('curl')], system_exclusions=['nginx'], ignore_exclusions=ignore_exclusions)

    assert not result['nginx']['install']
    assert result['nginx']['install_decision_message'] == '✕ (excluded by system)'
    assert result['curl']['install']
    assert not excluded


@pytest.mark.parametrize('system_exclusion', [
    'kernel*',          # dnf.conf glob
    'kernel-core',      # exact name
    'kernel-core:i386', # apt-mark showhold foreign architecture
])
def test_system_exclusion_formats(system_exclusion) -> None:
    """System exclusions can be globs (dnf.conf) or names with an architecture (apt-mark showhold)"""
    result, _ = run_exclude([pkg('kernel-core'), pkg('curl')], system_exclusions=[system_exclusion])

    assert not result['kernel-core']['install']
    assert result['curl']['install']
