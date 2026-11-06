"""Unit tests for the trigger files used to request actions from the linupdate service."""

from src.controllers.app.trigger import Trigger


def test_trigger_files_are_not_in_tmp() -> None:
    """Trigger files are created by root: they must not be in /tmp, writable by any user"""
    assert not Trigger().trigger_path.startswith('/tmp/')


def test_create_exists_remove(tmp_path) -> None:
    """A trigger can be created, checked and removed, its directory is created if needed"""
    trigger = Trigger()
    trigger.trigger_path = str(tmp_path / 'tmp' / 'trigger')

    assert not trigger.exists('package-info')

    trigger.create('package-info')
    trigger.create('package-info')
    assert trigger.exists('package-info')
    assert (tmp_path / 'tmp' / 'trigger.package-info').is_file()

    trigger.remove('package-info')
    trigger.remove('package-info')
    assert not trigger.exists('package-info')
