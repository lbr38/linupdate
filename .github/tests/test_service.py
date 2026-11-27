"""Unit tests for the conditional services reload and restart (service:package) after an update."""

from unittest.mock import MagicMock

import pytest

from src.controllers.service import service as service_module
from src.controllers.service.service import Service

UPDATED = {'php8.2-fpm': {}, 'curl': {}}


@pytest.mark.parametrize('pattern, expected', [
    ('php8.2-fpm', True),    # exact package name
    ('php*', True),          # wildcard
    ('php.*', True),         # legacy regex wildcard
    ('php*-fpm', True),      # wildcard in the middle
    ('php', False),          # the pattern must match the whole package name
    ('cur', False),          # a prefix of an updated package is not enough
    ('nginx*', False),       # no updated package matches
])
def test_is_package_updated(pattern, expected) -> None:
    """The package pattern must match the whole name of at least one updated package"""
    assert Service.is_package_updated(pattern, UPDATED) is expected


def run_service(method, services, monkeypatch, capsys) -> str:
    """Run Service.reload() or Service.restart() in dry-run mode and return the printed output"""
    controller = Service.__new__(Service)
    controller.config = MagicMock()
    controller.config.get_service_to_reload.return_value = services
    controller.config.get_service_to_restart.return_value = services

    # Pretend systemctl is installed
    monkeypatch.setattr(service_module, 'Path', lambda path: MagicMock(is_file=lambda: True))

    summary = {'update': {'success': {'packages': UPDATED, 'count': len(UPDATED)}}}
    getattr(controller, method)(summary, dry_run=True)

    return capsys.readouterr().out


@pytest.mark.parametrize('method, verb', [('reload', 'reload'), ('restart', 'restart')])
def test_conditional_services(method, verb, monkeypatch, capsys) -> None:
    """Only services whose package condition matches an updated package are reloaded or restarted"""
    output = run_service(method, ['httpd:php*', 'nginx:nginx*', 'postfix:cur', 'cron'], monkeypatch, capsys)

    assert 'Would ' + verb + ' ' in output
    assert 'httpd' in output
    assert 'cron' in output
    assert 'nginx' not in output
    assert 'postfix' not in output
