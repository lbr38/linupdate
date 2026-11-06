"""Unit tests for the flock(2) based inter-process lock."""

import subprocess
import sys
import textwrap
import threading
import time
from typing import Callable, Iterator

import pytest

from src.controllers.lock import Lock
from src.controllers.linupdate_exception import LinupdateException

# Small program holding a lock until it is killed, to simulate another linupdate process
HOLDER_SCRIPT = textwrap.dedent('''
    import fcntl, os, sys, time
    fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o640)
    fcntl.flock(fd, fcntl.LOCK_SH if sys.argv[2] == 'shared' else fcntl.LOCK_EX)
    print('locked', flush=True)
    time.sleep(60)
''')


@pytest.fixture(name='hold_lock')
def fixture_hold_lock(lock_dir) -> Iterator[Callable]:
    """Return a function holding a lock from another process (killed at the end of the test)"""
    processes = []

    def hold(name, mode='exclusive') -> subprocess.Popen:
        lock_dir.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(  # pylint: disable=consider-using-with
            [sys.executable, '-c', HOLDER_SCRIPT, str(lock_dir / (name + '.lock')), mode],
            stdout=subprocess.PIPE,
            universal_newlines=True
        )
        processes.append(process)
        assert process.stdout.readline().strip() == 'locked'
        return process

    yield hold

    for process in processes:
        process.kill()
        process.wait()
        process.stdout.close()


@pytest.mark.usefixtures('lock_dir')
def test_is_locked_without_lock_file() -> None:
    """A lock that was never taken is not locked"""
    assert not Lock.is_locked('missing')


def test_acquire_and_release(lock_dir) -> None:
    """The lock file is created on acquire and kept after release"""
    lock = Lock('test').acquire()
    assert (lock_dir / 'test.lock').is_file()
    assert Lock.is_locked('test')

    lock.release()
    assert not Lock.is_locked('test')

    # Lock files must never be deleted (deleting a flock file breaks mutual exclusion)
    assert (lock_dir / 'test.lock').is_file()


@pytest.mark.usefixtures('lock_dir')
def test_release_without_acquire_is_noop() -> None:
    """Releasing a lock that is not held does nothing"""
    Lock('test').release()
    assert not Lock.is_locked('test')


@pytest.mark.usefixtures('lock_dir')
def test_context_manager_releases_on_exception() -> None:
    """The lock is released when an exception leaves the 'with' block"""
    with pytest.raises(ValueError):
        with Lock('test'):
            assert Lock.is_locked('test')
            raise ValueError('boom')

    assert not Lock.is_locked('test')


@pytest.mark.usefixtures('lock_dir')
def test_lock_is_reentrant_in_same_thread() -> None:
    """The lock is only released when every acquire has been released"""
    outer = Lock('test').acquire()
    inner = Lock('test').acquire()

    inner.release()
    assert Lock.is_locked('test')

    outer.release()
    assert not Lock.is_locked('test')


@pytest.mark.usefixtures('lock_dir')
def test_cannot_upgrade_shared_lock_to_exclusive() -> None:
    """A thread holding a shared lock cannot take it exclusively"""
    shared = Lock('test', shared=True).acquire()

    try:
        with pytest.raises(LinupdateException, match='cannot upgrade shared lock'):
            Lock('test').acquire()
    finally:
        shared.release()

    assert not Lock.is_locked('test')


def test_exclusive_lock_held_elsewhere_fails_without_waiting(hold_lock) -> None:
    """With timeout=0 (linupdate run lock), acquire fails at once if another process holds the lock"""
    hold_lock('test')

    start = time.time()
    with pytest.raises(LinupdateException, match='could not acquire lock'):
        Lock('test', timeout=0).acquire()

    assert time.time() - start < 1


def test_lock_released_when_holder_process_dies(hold_lock) -> None:
    """A killed process cannot leave a stale lock behind"""
    holder = hold_lock('test')
    assert Lock.is_locked('test')

    holder.kill()
    holder.wait()

    assert not Lock.is_locked('test')
    Lock('test', timeout=0).acquire().release()


def test_acquire_waits_until_lock_is_released(hold_lock) -> None:
    """With a timeout, acquire waits for the other process to release the lock"""
    holder = hold_lock('test')
    timer = threading.Timer(1.5, holder.kill)
    timer.start()

    try:
        start = time.time()
        lock = Lock('test', timeout=30).acquire()
        elapsed = time.time() - start
        lock.release()
    finally:
        timer.cancel()

    assert elapsed >= 1


def test_shared_lock_allows_several_readers(hold_lock) -> None:
    """Shared locks can be held by several processes but block exclusive ones"""
    hold_lock('test', 'shared')

    reader = Lock('test', shared=True, timeout=0).acquire()
    assert Lock.is_locked('test')
    assert not Lock.is_locked('test', exclusive_only=True)
    reader.release()

    with pytest.raises(LinupdateException, match='could not acquire lock'):
        Lock('test', timeout=0).acquire()


def test_exclusive_only_detects_exclusive_holder(hold_lock) -> None:
    """is_locked(exclusive_only=True) is True when another process holds the lock exclusively"""
    hold_lock('test')
    assert Lock.is_locked('test', exclusive_only=True)
