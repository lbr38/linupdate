"""Unit tests for the reposerver module configuration."""

import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from src.controllers.linupdate_exception import LinupdateException
from src.controllers.module.reposerver.config import Config

TEMPLATE = Path(__file__).resolve().parents[2] / 'templates' / 'modules' / 'reposerver.template.yml'


@pytest.fixture(name='reposerver_config')
def fixture_reposerver_config(tmp_path) -> Config:
    """Return a registered reposerver Config controller working on a copy of the template, with a mocked HTTP client"""
    config = Config.__new__(Config)
    config.config_file = str(tmp_path / 'reposerver.yml')
    shutil.copy(str(TEMPLATE), config.config_file)
    config.http_request_controller = MagicMock()

    config.set_url('https://repo.example.com/')
    config.set_id('host-id')
    config.set_token('host-token')

    return config


def read_auth(config) -> dict:
    """Return the auth section of the configuration file"""
    with open(config.config_file, encoding='utf-8') as file:
        return yaml.safe_load(file)['client']['auth']


def test_set_url_removes_final_slash(reposerver_config) -> None:
    """The final slash of the reposerver URL is removed"""
    assert reposerver_config.get_url() == 'https://repo.example.com'


def test_set_url_rejects_other_schemes(reposerver_config) -> None:
    """Only http:// and https:// URLs are accepted"""
    with pytest.raises(LinupdateException, match='must start with http'):
        reposerver_config.set_url('ftp://repo.example.com')

    assert reposerver_config.get_url() == 'https://repo.example.com'


def test_unregister_forgets_credentials(reposerver_config) -> None:
    """Once unregistered, the id and token (not valid anymore) are removed from the configuration"""
    reposerver_config.unregister()

    reposerver_config.http_request_controller.delete.assert_called_once_with(
        'https://repo.example.com/api/v2/host/registering', 'host-id', 'host-token')
    assert read_auth(reposerver_config) == {'id': '', 'token': ''}


def test_failed_unregister_keeps_credentials(reposerver_config) -> None:
    """If the reposerver could not unregister the host, the credentials are kept"""
    reposerver_config.http_request_controller.delete.side_effect = LinupdateException('HTTP 500')

    with pytest.raises(LinupdateException, match='Unregistering failed'):
        reposerver_config.unregister()

    assert read_auth(reposerver_config) == {'id': 'host-id', 'token': 'host-token'}


@pytest.mark.parametrize('repo_format', ['legacy', 'deb822'])
def test_set_source_repo_format(reposerver_config, repo_format) -> None:
    """legacy and deb822 formats are accepted"""
    reposerver_config.set_source_repo_format(repo_format)

    assert reposerver_config.get_source_repo_format() == repo_format


def test_set_source_repo_format_rejects_unknown_format(reposerver_config) -> None:
    """Unknown formats are rejected"""
    with pytest.raises(LinupdateException, match='source repo format must be set'):
        reposerver_config.set_source_repo_format('foo')
