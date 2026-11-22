"""Unit tests for apt history parsing (packages history sent to the reposerver)."""

import gzip

import pytest

from src.controllers.package.apt import Apt

# Excerpt of /var/log/apt/history.log, the last event is incomplete (still being written)
HISTORY = '''
Start-Date: 2024-05-02  10:00:01
Commandline: apt-get install -y cowsay
Install: cowsay:all (3.03+dfsg2-8), libtext-charwidth-perl:amd64 (0.04-11, automatic)
End-Date: 2024-05-02  10:00:05

Start-Date: 2024-05-03  11:00:01
Commandline: /usr/bin/apt-get -y upgrade
Requested-By: admin (1000)
Upgrade: libc6:amd64 (2.36-9+deb12u4, 2.36-9+deb12u7), curl:amd64 (7.88.1-10+deb12u5, 7.88.1-10+deb12u8)
End-Date: 2024-05-03  11:00:30

Start-Date: 2024-05-04  12:00:01
Commandline: apt-get purge -y cowsay
Purge: cowsay:all (3.03+dfsg2-8)
End-Date: 2024-05-04  12:00:02

Start-Date: 2024-05-05  13:00:01
Commandline: apt-get install -y nginx
'''

EXPECTED_EVENTS = [
    {
        'date_start': '2024-05-02', 'time_start': '10:00:01',
        'date_end': '2024-05-02', 'time_end': '10:00:05',
        'command': 'apt-get install -y cowsay',
        'installed': [
            {'name': 'cowsay', 'version': '3.03+dfsg2-8'},
            {'name': 'libtext-charwidth-perl', 'version': '0.04-11'}
        ]
    },
    {
        'date_start': '2024-05-03', 'time_start': '11:00:01',
        'date_end': '2024-05-03', 'time_end': '11:00:30',
        'command': '/usr/bin/apt-get -y upgrade',
        'upgraded': [
            {'name': 'libc6', 'version': '2.36-9+deb12u7'},
            {'name': 'curl', 'version': '7.88.1-10+deb12u8'}
        ]
    },
    {
        'date_start': '2024-05-04', 'time_start': '12:00:01',
        'date_end': '2024-05-04', 'time_end': '12:00:02',
        'command': 'apt-get purge -y cowsay',
        'purged': [
            {'name': 'cowsay', 'version': '3.03+dfsg2-8'}
        ]
    }
]


@pytest.mark.parametrize('line, action, expected', [
    # Single package
    ('nginx:amd64 (1.22.1-9)', 'remove', [('nginx', '1.22.1-9')]),
    # Several packages, the target version is the second one for upgrades
    ('libc6:amd64 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8), libc6-dev:amd64 (2.35-0ubuntu3.7, 2.35-0ubuntu3.8)', 'upgrade',
     [('libc6', '2.35-0ubuntu3.8'), ('libc6-dev', '2.35-0ubuntu3.8')]),
    # Automatically installed dependency
    ('cowsay:all (3.03+dfsg2-8), libtext-charwidth-perl:amd64 (0.04-11, automatic)', 'install',
     [('cowsay', '3.03+dfsg2-8'), ('libtext-charwidth-perl', '0.04-11')]),
    # Downgrade: the target version is the second one
    ('openssl:amd64 (3.0.13-1, 3.0.11-1)', 'downgrade', [('openssl', '3.0.11-1')]),
    # Architectures whose name starts with another architecture name
    ('libfoo:mips64el (1.0, 1.1), bar:powerpcspe (3.0, 3.1), baz:sparc64 (2.0, 2.1), qux:mipsel (4.0, 4.1)', 'upgrade',
     [('libfoo', '1.1'), ('bar', '3.1'), ('baz', '2.1'), ('qux', '4.1')]),
])
def test_parse_packages_line(line, action, expected) -> None:
    """Package name (without architecture) and version are extracted from a history line"""
    result = Apt().parse_packages_line_to_json(line, action)

    assert [(package['name'], package['version']) for package in result] == expected


def test_parse_history_plain_file(tmp_path) -> None:
    """Complete events are parsed, the incomplete last one is ignored"""
    history = tmp_path / 'history.log'
    history.write_text(HISTORY, encoding='utf-8')

    assert Apt().parse_history([str(history)], 999999) == EXPECTED_EVENTS


def test_parse_history_rotated_gzip_file(tmp_path) -> None:
    """Rotated (gzip compressed) history files are parsed the same way"""
    history = tmp_path / 'history.log.1.gz'
    with gzip.open(str(history), 'wt', encoding='utf-8') as file:
        file.write(HISTORY)

    assert Apt().parse_history([str(history)], 999999) == EXPECTED_EVENTS


def test_parse_history_several_files(tmp_path) -> None:
    """Events of every file are returned in the files order"""
    rotated = tmp_path / 'history.log.1.gz'
    with gzip.open(str(rotated), 'wt', encoding='utf-8') as file:
        file.write(HISTORY)
    current = tmp_path / 'history.log'
    current.write_text(HISTORY, encoding='utf-8')

    assert Apt().parse_history([str(rotated), str(current)], 999999) == EXPECTED_EVENTS * 2


def test_parse_history_ignores_empty_file(tmp_path) -> None:
    """An empty history file (just rotated) is ignored"""
    history = tmp_path / 'history.log'
    history.write_text('', encoding='utf-8')

    assert not Apt().parse_history([str(history)], 999999)


@pytest.mark.parametrize('entries_limit', [1, 2, 3])
def test_parse_history_entries_limit(tmp_path, entries_limit) -> None:
    """No more than entries_limit events are returned"""
    history = tmp_path / 'history.log'
    history.write_text(HISTORY, encoding='utf-8')

    assert Apt().parse_history([str(history)], entries_limit) == EXPECTED_EVENTS[:entries_limit]


def test_parse_history_entries_limit_across_files(tmp_path) -> None:
    """The limit applies to all the files, not to each file"""
    files = []
    for name in ('history.log', 'history.log.1'):
        history = tmp_path / name
        history.write_text(HISTORY, encoding='utf-8')
        files.append(str(history))

    assert len(Apt().parse_history(files, 4)) == 4
