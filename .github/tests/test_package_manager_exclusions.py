"""Unit tests for the exclusions set by linupdate with apt (hold) and dnf (--exclude)."""

import subprocess
from pathlib import Path

import pytest

from src.controllers.package import apt as apt_module
from src.controllers.package.apt import Apt
from src.controllers.package.dnf import Dnf


class FakeAptMark:
    """Simulate apt-mark hold, unhold and showhold"""
    def __init__(self, held=()) -> None:
        self.held = list(held)
        self.calls = []

    def run(self, command, **_kwargs) -> subprocess.CompletedProcess:
        """Replacement for subprocess.run()"""
        self.calls.append(command)
        stdout = ''

        if command[:2] == ['apt-mark', 'showhold']:
            stdout = ''.join(package + '\n' for package in self.held)
        elif command[:2] == ['apt-mark', 'hold']:
            if command[2] not in self.held:
                self.held.append(command[2])
        elif command[:2] == ['apt-mark', 'unhold']:
            self.held.remove(command[2])
        else:
            raise AssertionError('unexpected command: ' + str(command))

        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr='')

    def actions(self, action) -> list:
        """Return the packages passed to an apt-mark action"""
        return [call[2] for call in self.calls if call[1] == action]


@pytest.fixture(name='apt_mark')
def fixture_apt_mark(monkeypatch) -> FakeAptMark:
    """Replace apt-mark with a simulation, the administrator holds 'admin-held'"""
    fake = FakeAptMark(held=['admin-held'])
    monkeypatch.setattr(apt_module.subprocess, 'run', fake.run)
    return fake


@pytest.fixture(name='holds_file')
def fixture_holds_file(tmp_path) -> Path:
    """Path of the file recording the packages held by linupdate"""
    return tmp_path / 'tmp' / 'apt-holds'


def make_apt(holds_file) -> Apt:
    """Return an Apt controller recording its holds in holds_file"""
    apt = Apt()
    apt.holds_file = str(holds_file)
    return apt


@pytest.mark.usefixtures('apt_mark')
def test_apt_exclude_holds_and_records_package(holds_file) -> None:
    """An excluded package is held and recorded"""
    apt = make_apt(holds_file)

    apt.exclude('nginx')

    assert 'nginx' in apt.get_exclusion()
    assert apt.get_linupdate_holds() == ['nginx']


def test_apt_remove_all_exclusions_keeps_administrator_holds(apt_mark, holds_file) -> None:
    """Only the packages held by linupdate are released"""
    apt = make_apt(holds_file)
    apt.exclude('nginx')
    apt.exclude('mysql-server')

    apt.remove_all_exclusions()

    assert apt_mark.held == ['admin-held']
    assert sorted(apt_mark.actions('unhold')) == ['mysql-server', 'nginx']
    assert not holds_file.exists()


def test_apt_package_held_by_administrator_is_left_as_it_is(apt_mark, holds_file) -> None:
    """A package already held by the administrator is neither held again, nor recorded, nor released"""
    apt = make_apt(holds_file)

    apt.exclude('admin-held')
    apt.remove_all_exclusions()

    assert not apt_mark.actions('hold')
    assert not apt_mark.actions('unhold')
    assert apt_mark.held == ['admin-held']


def test_apt_holds_of_an_interrupted_run_are_released_by_the_next_one(apt_mark, holds_file) -> None:
    """The record survives the process, so the next run releases the packages held by an interrupted run"""
    make_apt(holds_file).exclude('nginx')

    make_apt(holds_file).remove_all_exclusions()

    assert apt_mark.held == ['admin-held']


def test_apt_recorded_package_not_held_anymore_is_skipped(apt_mark, holds_file) -> None:
    """A recorded package which is not held anymore (e.g. removed) does not make the release fail"""
    holds_file.parent.mkdir(parents=True)
    holds_file.write_text('removed-package\n', encoding='utf-8')

    make_apt(holds_file).remove_all_exclusions()

    assert not apt_mark.actions('unhold')
    assert not holds_file.exists()


@pytest.mark.usefixtures('apt_mark')
def test_apt_remove_all_exclusions_without_record(holds_file) -> None:
    """Nothing to do when linupdate has not held any package"""
    make_apt(holds_file).remove_all_exclusions()

    assert not holds_file.exists()


@pytest.fixture(name='dnf')
def fixture_dnf(tmp_path) -> Dnf:
    """Return a Dnf controller using a temporary dnf.conf"""
    dnf = Dnf()
    dnf.dnf_conf_file = str(tmp_path / 'dnf.conf')
    return dnf


@pytest.mark.parametrize('content, expected', [
    ('[main]\ngpgcheck=1\n', []),
    ('[main]\nexclude=kernel* php-fpm\n', ['kernel*', 'php-fpm']),
    ('[main]\nexcludepkgs=mysql*,nginx\n', ['mysql*', 'nginx']),
    ('[main]\nexclude=kernel*\nexcludepkgs=nginx, php*\n', ['kernel*', 'nginx', 'php*']),
    # '%' must not be interpreted
    ('[main]\nexclude=kernel*\nproxy_password=50%off\n', ['kernel*']),
])
def test_dnf_get_exclusion(dnf, content, expected) -> None:
    """Administrator exclusions are read from the 'exclude' and 'excludepkgs' options of dnf.conf"""
    with open(dnf.dnf_conf_file, 'w', encoding='utf-8') as file:
        file.write(content)

    assert dnf.get_exclusion() == expected


def test_dnf_get_exclusion_without_dnf_conf(dnf) -> None:
    """A missing dnf.conf means no exclusion"""
    assert not dnf.get_exclusion()


def test_dnf_exclusions_are_passed_on_the_command_line(dnf) -> None:
    """Excluded packages are passed to dnf with --exclude, dnf.conf is never modified"""
    content = '[main]\n# administrator comment\nexclude=kernel*\n'
    with open(dnf.dnf_conf_file, 'w', encoding='utf-8') as file:
        file.write(content)

    dnf.exclude('nginx')
    dnf.exclude('mysql-server')
    dnf.exclude('nginx')
    command = dnf.get_update_command({'name': 'curl', 'target_version': '8.5.0-1.el9'})

    assert command.endswith(' update curl-8.5.0-1.el9 -y --exclude=nginx --exclude=mysql-server')

    dnf.remove_all_exclusions()
    assert '--exclude' not in dnf.get_update_command({'name': 'curl', 'target_version': '8.5.0-1.el9'})

    with open(dnf.dnf_conf_file, encoding='utf-8') as file:
        assert file.read() == content


def test_dnf_dry_run_command(dnf) -> None:
    """A dry run only tests the transaction"""
    command = dnf.get_update_command({'name': 'curl', 'target_version': '8.5.0-1.el9'}, dry_run=True)

    assert command.endswith(' --setopt tsflags=test')
