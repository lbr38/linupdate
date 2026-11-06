"""Shared pytest configuration: import path, optional system modules and common fixtures."""

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
from typing import Iterator

import pytest

# Make the 'src' package importable from the repository root
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

# Some modules are only available as distribution packages (python3-apt) or are broken on
# recent Python versions when installed from PyPI (pyinotify). Stub them when missing so
# that the pure logic can be tested anywhere.
for module_name in ('apt', 'pyinotify'):
    try:
        importlib.import_module(module_name)
    except Exception:
        sys.modules[module_name] = MagicMock()

# Imported after the stubs above on purpose
from src.controllers.lock import Lock  # pylint: disable=wrong-import-position


@pytest.fixture(name='lock_dir')
def fixture_lock_dir(tmp_path, monkeypatch) -> Iterator[Path]:
    """Redirect lock files to a temporary directory and drop locks left by a failed test"""
    path = tmp_path / 'locks'
    monkeypatch.setattr(Lock, 'LOCK_DIR', str(path))

    yield path

    held = Lock._held_locks()  # pylint: disable=protected-access
    for lock in held.values():
        os.close(lock['fd'])
    held.clear()
