"""Unit tests for the main linupdate configuration (linupdate.yml and update.yml)."""

import shutil
from pathlib import Path

import pytest
import yaml

from src.controllers.app.config import Config
from src.controllers.linupdate_exception import LinupdateException
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / 'templates'


@pytest.fixture(name='app_config')
def fixture_app_config(tmp_path) -> Config:
    """Return a Config controller working on copies of the default configuration templates"""
    config = Config.__new__(Config)
    config.config_file = str(tmp_path / 'linupdate.yml')
    config.update_file = str(tmp_path / 'update.yml')
    shutil.copy(str(TEMPLATES_DIR / 'linupdate.template.yml'), config.config_file)
    shutil.copy(str(TEMPLATES_DIR / 'update.template.yml'), config.update_file)
    return config


def read_yaml(path) -> dict:
    """Return the content of a YAML file"""
    with open(path, encoding='utf-8') as file:
        return yaml.safe_load(file)


def edit_yaml(path, edit) -> None:
    """Apply edit() to the content of a YAML file"""
    content = read_yaml(path)
    edit(content)
    with open(path, 'w', encoding='utf-8') as file:
        yaml.safe_dump(content, file)


def test_templates_are_valid(app_config) -> None:
    """The default templates pass the configuration checks"""
    app_config.check_conf()

    assert app_config.get_profile() == 'host'
    assert app_config.get_environment() == 'prod'


def test_configuration_stays_split_in_two_files(app_config) -> None:
    """Writing the configuration keeps main/modules and update/post_update in their own file"""
    app_config.set_profile('web-servers')

    assert set(read_yaml(app_config.config_file)) == {'main', 'modules'}
    assert set(read_yaml(app_config.update_file)) == {'update', 'post_update'}
    assert app_config.get_profile() == 'web-servers'


def test_set_exclusion_appends_without_duplicates(app_config) -> None:
    """Exclusions are appended once, 'None' clears them"""
    app_config.set_exclusion('kernel.*,nginx')
    app_config.set_exclusion('nginx,mysql.*')
    assert app_config.get_exclusion() == ['kernel.*', 'nginx', 'mysql.*']

    app_config.set_exclusion('None')
    assert app_config.get_exclusion() == []


def test_set_major_exclusion(app_config) -> None:
    """Exclusions on major update are appended once, 'None' clears them"""
    app_config.set_major_exclusion('nginx,mysql.*')
    app_config.set_major_exclusion('nginx')
    assert app_config.get_major_exclusion() == ['nginx', 'mysql.*']

    app_config.set_major_exclusion('None')
    assert app_config.get_major_exclusion() == []


def test_set_mail_recipient(app_config) -> None:
    """Recipients are appended once, 'None' clears them"""
    app_config.set_mail_recipient('a@example.com,b@example.com')
    app_config.set_mail_recipient('b@example.com')
    assert app_config.get_mail_recipient() == ['a@example.com', 'b@example.com']

    app_config.set_mail_recipient('None')
    assert app_config.get_mail_recipient() == []


def test_set_log_retention_days(app_config) -> None:
    """A valid retention period is stored as an integer"""
    app_config.set_log_retention_days('30')

    assert app_config.get_log_retention_days() == 30
    assert read_yaml(app_config.config_file)['main']['log_retention_days'] == 30


@pytest.mark.parametrize('days, error', [
    ('abc', 'must be an integer'),
    ('-1', 'must be >= 0'),
])
def test_set_log_retention_days_rejects_invalid_values(app_config, days, error) -> None:
    """An invalid retention period is rejected and the configuration is left untouched"""
    with pytest.raises(LinupdateException, match=error):
        app_config.set_log_retention_days(days)

    assert app_config.get_log_retention_days() == 180


def test_check_conf_adds_missing_defaults(app_config) -> None:
    """Optional keys missing from an old configuration file are added with their default value"""
    def remove_optional_keys(content) -> None:
        del content['main']['mail']['smtp_host']
        del content['main']['mail']['smtp_port']
        del content['main']['log_retention_days']

    edit_yaml(app_config.config_file, remove_optional_keys)

    app_config.check_conf()

    main = read_yaml(app_config.config_file)['main']
    assert main['mail']['smtp_host'] == 'localhost'
    assert main['mail']['smtp_port'] == 25
    assert main['log_retention_days'] == 180


@pytest.mark.parametrize('key', ['profile', 'environment'])
@pytest.mark.parametrize('value', [None, ''])
def test_check_conf_rejects_empty_profile_or_environment(app_config, key, value) -> None:
    """An empty profile or environment (no value or empty string) is a fatal configuration error"""
    def empty_key(content) -> None:
        content['main'][key] = value

    edit_yaml(app_config.config_file, empty_key)

    with pytest.raises(LinupdateException, match='main.' + key + ' key is empty'):
        app_config.check_conf()


def test_check_conf_rejects_missing_update_file(app_config, tmp_path) -> None:
    """A missing update.yml is a fatal configuration error"""
    app_config.update_file = str(tmp_path / 'missing.yml')

    with pytest.raises(LinupdateException, match='is missing'):
        app_config.check_conf()
