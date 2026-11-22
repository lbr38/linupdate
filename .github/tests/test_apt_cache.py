"""Unit tests for the apt backend: packages cache, packages lists and packages update."""

import io
import subprocess
from types import SimpleNamespace
from typing import Callable, Iterator

import pytest

from src.controllers.linupdate_exception import LinupdateException
from src.controllers.package import apt as apt_module
from src.controllers.package.apt import Apt

# Package files a version comes from (apt_pkg.PackageFile), and the index of each one (SourceList.find_index())
STATUS_FILE = '/var/lib/dpkg/status'
REPO_FILE = '/var/lib/apt/lists/reposerver.example.com_repo_myrepo_prod_dists_bookworm_main_binary-amd64_Packages'
REPO_URL = 'https://reposerver.example.com/repo/myrepo/prod'


class FakeIndex:
    """Minimal apt_pkg.IndexFile"""
    def __init__(self, uri) -> None:
        self.uri = uri

    def archive_uri(self, path) -> str:
        """Return the URL of a file of the repository"""
        return self.uri + path


INDEXES = {REPO_FILE: FakeIndex(REPO_URL + '/')}


class FakeVersion:
    """Minimal apt.package.Version"""
    def __init__(self, version, package_files=()) -> None:
        self.version = version
        self.origins = []
        self._cand = SimpleNamespace(file_list=[(package_file, 0) for package_file in package_files])


class FakePackage:
    """Minimal apt.package.Package"""
    def __init__(self, name, installed=None, candidate=None) -> None:
        self.name = name
        self.installed = installed
        self.candidate = candidate
        self.is_installed = installed is not None
        self.is_upgradable = installed is not None and candidate is not None and installed.version != candidate.version
        self.versions = {version.version: version for version in (installed, candidate) if version}


class FakeCache:
    """Minimal apt.Cache"""
    def __init__(self, packages=(), changes=()) -> None:
        self.packages = {package.name: package for package in packages}
        self.changes = list(changes)
        self.upgrade_calls = []
        self.closed = False
        self._list = SimpleNamespace(find_index=INDEXES.get)

    def __contains__(self, name) -> bool:
        return name in self.packages

    def __getitem__(self, name) -> FakePackage:
        return self.packages[name]

    def __iter__(self) -> Iterator[FakePackage]:
        return iter(self.packages.values())

    def upgrade(self, dist_upgrade=False) -> None:
        """Simulate an upgrade"""
        self.upgrade_calls.append(dist_upgrade)

    def get_changes(self) -> list:
        """Return the packages changed by the simulated upgrade"""
        return self.changes

    def close(self) -> None:
        """Close the cache"""
        self.closed = True


class FakeCommands:
    """Replacement for subprocess.run(), records the commands and returns the configured results"""
    def __init__(self) -> None:
        self.calls = []
        # 'command line' => (returncode, stdout, stderr)
        self.results = {}

    def run(self, command, **_kwargs) -> subprocess.CompletedProcess:
        """Replacement for subprocess.run()"""
        self.calls.append(command)
        returncode, stdout, stderr = self.results.get(' '.join(command), (0, '', ''))
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


@pytest.fixture(autouse=True)
def fixture_no_dpkg_lock(monkeypatch) -> None:
    """Do not wait for the dpkg lock (it can only be checked as root)"""
    monkeypatch.setattr(Apt, 'wait_for_dpkg_lock', lambda self, timeout=60: None)


@pytest.fixture(name='use_cache')
def fixture_use_cache(monkeypatch) -> Callable:
    """Return a function making apt.Cache() return the given fake cache"""
    def use(cache) -> FakeCache:
        monkeypatch.setattr(apt_module.apt, 'Cache', lambda: cache)
        return cache

    return use


@pytest.fixture(name='commands')
def fixture_commands(monkeypatch) -> FakeCommands:
    """Replace subprocess.run()"""
    commands = FakeCommands()
    monkeypatch.setattr(apt_module.subprocess, 'run', commands.run)
    return commands


@pytest.fixture(name='popen')
def fixture_popen(monkeypatch) -> type:
    """Replace subprocess.Popen() (apt-get install), the class attribute returncode sets the result of the command"""
    class FakePopen:
        """Minimal subprocess.Popen"""
        returncode = 0
        instances = []

        def __init__(self, command, **_kwargs) -> None:
            self.command = command
            self.returncode = FakePopen.returncode
            self.stdout = io.StringIO('Reading package lists...\n')
            FakePopen.instances.append(self)

        def __enter__(self) -> 'FakePopen':
            return self

        def __exit__(self, *_args) -> None:
            self.stdout.close()

    monkeypatch.setattr(apt_module.subprocess, 'Popen', FakePopen)
    return FakePopen


def test_is_installed_only_for_installed_packages(use_cache) -> None:
    """A package only available from the repositories is not installed"""
    cache = use_cache(FakeCache([
        FakePackage('nginx', installed=FakeVersion('1.0')),
        FakePackage('cowsay', candidate=FakeVersion('3.0', [REPO_FILE])),
    ]))

    apt = Apt()

    assert apt.is_installed('nginx') is True
    assert apt.is_installed('cowsay') is False
    assert apt.is_installed('unknown') is False
    assert cache.closed


def test_current_and_available_versions(use_cache) -> None:
    """Versions of installed packages, empty string when not installed or without candidate"""
    use_cache(FakeCache([
        FakePackage('nginx', installed=FakeVersion('1.0', [STATUS_FILE]), candidate=FakeVersion('2.0', [REPO_FILE])),
        FakePackage('cowsay', candidate=FakeVersion('3.0', [REPO_FILE])),
        FakePackage('pinned', installed=FakeVersion('1.0', [STATUS_FILE])),
    ]))

    apt = Apt()

    assert apt.get_current_version('nginx') == '1.0'
    assert apt.get_available_version('nginx') == '2.0'
    assert apt.get_current_version('cowsay') == ''
    assert apt.get_available_version('cowsay') == ''
    assert apt.get_available_version('pinned') == ''

    with pytest.raises(LinupdateException, match='unknown'):
        apt.get_current_version('unknown')


def test_version_repository_is_the_first_repository_index() -> None:
    """The dpkg status file (installed version) is skipped, the URL has no trailing slash"""
    version = FakeVersion('1.0', [STATUS_FILE, REPO_FILE])

    assert Apt().get_version_repository(FakeCache(), version) == REPO_URL


def test_version_repository_unknown() -> None:
    """Version only installed (e.g. from a local .deb file), or unexpected python-apt object: never blocking"""
    assert Apt().get_version_repository(FakeCache(), FakeVersion('1.0', [STATUS_FILE])) == 'Unknown'
    assert Apt().get_version_repository(FakeCache(), object()) == 'Unknown'


def test_source_repository_of_a_package_version(use_cache) -> None:
    """Repository of a given version of a package"""
    use_cache(FakeCache([
        FakePackage('nginx', installed=FakeVersion('1.0', [STATUS_FILE]), candidate=FakeVersion('2.0', [REPO_FILE])),
    ]))

    apt = Apt()

    assert apt.get_source_repository('nginx', '2.0') == REPO_URL
    assert apt.get_source_repository('nginx', '3.0') == 'Unknown'
    assert apt.get_source_repository('unknown', '1.0') == 'Unknown'


def test_available_packages_lists_upgraded_packages_only(use_cache) -> None:
    """Packages removed or newly installed by the upgrade are not listed, the list is sorted by name"""
    cache = use_cache(FakeCache(changes=[
        FakePackage('zlib1g', installed=FakeVersion('1.2', [STATUS_FILE]), candidate=FakeVersion('1.3', [REPO_FILE])),
        FakePackage('curl', installed=FakeVersion('7.0', [STATUS_FILE]), candidate=FakeVersion('8.0', [REPO_FILE])),
        FakePackage('removed', installed=FakeVersion('1.0', [STATUS_FILE]), candidate=FakeVersion('1.0', [STATUS_FILE])),
        FakePackage('new-dependency', candidate=FakeVersion('1.0', [REPO_FILE])),
    ]))

    packages = Apt().get_available_packages(True)

    assert packages == [
        {'name': 'curl', 'current_version': '7.0', 'target_version': '8.0', 'repository': REPO_URL, 'security': False},
        {'name': 'zlib1g', 'current_version': '1.2', 'target_version': '1.3', 'repository': REPO_URL, 'security': False},
    ]
    assert cache.upgrade_calls == [True]
    assert cache.closed


def test_update_cache_prints_apt_warnings(commands, capsys) -> None:
    """apt-get update succeeds when a repository is unreachable (its previous lists are kept): this must be visible"""
    commands.results['apt-get update'] = (
        0,
        'Err:1 https://reposerver.example.com/repo/myrepo/prod bookworm InRelease\n',
        'W: Failed to fetch https://reposerver.example.com/repo/myrepo/prod/dists/bookworm/InRelease\n'
        'W: Some index files failed to download. They have been ignored, or old ones used instead.\n'
    )

    Apt().update_cache()

    assert commands.calls == [['apt-get', 'update']]
    assert 'W: Some index files failed to download' in capsys.readouterr().out


def test_update_cache_is_quiet_without_warning(commands, capsys) -> None:
    """Nothing is printed when apt-get update has no warning"""
    Apt().update_cache()

    assert commands.calls == [['apt-get', 'update']]
    assert capsys.readouterr().out == ''


def test_update_cache_fails_on_error(commands) -> None:
    """An apt-get update error stops the update"""
    commands.results['apt-get update'] = (100, '', 'E: The repository does not have a Release file.\n')

    with pytest.raises(LinupdateException, match='does not have a Release file'):
        Apt().update_cache()


def test_clear_cache_removes_lists_but_keeps_lock(tmp_path, commands) -> None:
    """Packages lists and Release files are removed, the lock file and directories are kept"""
    lists_dir = tmp_path / 'lists'
    (lists_dir / 'partial').mkdir(parents=True)
    (lists_dir / 'auxfiles').mkdir()
    for name in ('lock', 'reposerver_dists_bookworm_InRelease', 'reposerver_dists_bookworm_main_binary-amd64_Packages'):
        (lists_dir / name).write_text('')

    apt = Apt()
    apt.lists_dir = str(lists_dir)
    apt.clear_cache()

    assert commands.calls == [['apt-get', 'clean']]
    assert sorted(path.name for path in lists_dir.iterdir()) == ['auxfiles', 'lock', 'partial']


def test_clear_cache_stops_if_apt_clean_fails(tmp_path, commands) -> None:
    """Packages lists are not removed if apt-get clean fails"""
    lists_dir = tmp_path / 'lists'
    lists_dir.mkdir()
    (lists_dir / 'reposerver_dists_bookworm_InRelease').write_text('')
    commands.results['apt-get clean'] = (100, '', 'E: Could not get lock /var/cache/apt/archives/lock\n')

    apt = Apt()
    apt.lists_dir = str(lists_dir)

    with pytest.raises(LinupdateException, match='Could not get lock'):
        apt.clear_cache()

    assert (lists_dir / 'reposerver_dists_bookworm_InRelease').exists()


def make_updater(tmp_path, monkeypatch, current_version) -> Apt:
    """Return an Apt controller writing its update log in tmp_path, nginx being installed in current_version"""
    apt = Apt()
    apt.update_log = str(tmp_path / 'update-package.log')
    monkeypatch.setattr(apt, 'get_current_version', lambda package: current_version)
    return apt


def nginx_update() -> list:
    """Return the list of packages to update: nginx 1.0 => 2.0"""
    return [{'name': 'nginx', 'current_version': '1.0', 'target_version': '2.0', 'install': True}]


def test_update_package(tmp_path, monkeypatch, popen) -> None:
    """The package is updated to the target version"""
    apt = make_updater(tmp_path, monkeypatch, '1.0')
    apt.update(nginx_update())

    assert apt.summary['update']['success']['count'] == 1
    assert popen.instances[0].command.startswith('DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get install nginx=2.0 -y')
    assert popen.instances[0].stdout.closed


def test_update_failed_package_is_skipped(tmp_path, monkeypatch, popen) -> None:
    """When exit_on_package_update_error is disabled, a failed package is recorded and the update goes on"""
    popen.returncode = 100

    apt = make_updater(tmp_path, monkeypatch, '1.0')
    apt.update(nginx_update(), exit_on_package_update_error=False)

    assert apt.summary['update']['failed']['count'] == 1
    assert apt.summary['update']['success']['count'] == 0
    assert popen.instances[0].stdout.closed


def test_update_failed_package_stops_the_update(tmp_path, monkeypatch, popen) -> None:
    """When exit_on_package_update_error is enabled, a failed package stops the update"""
    popen.returncode = 100

    apt = make_updater(tmp_path, monkeypatch, '1.0')

    with pytest.raises(LinupdateException, match='Error while updating nginx'):
        apt.update(nginx_update())


def test_update_packages_already_up_to_date(tmp_path, monkeypatch, popen) -> None:
    """A package already updated meanwhile (e.g. as a dependency) is not updated again, and this is not an error"""
    apt = make_updater(tmp_path, monkeypatch, '2.0')
    apt.update(nginx_update())

    assert apt.summary['update']['success']['count'] == 1
    assert apt.summary['update']['success']['packages']['nginx']['log'] == 'Already up to date (updated with another package).'
    assert not popen.instances
