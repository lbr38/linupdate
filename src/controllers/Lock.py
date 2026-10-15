# coding: utf-8

# Import libraries
import os
import fcntl
import time
import threading
from pathlib import Path

# Import classes
from src.controllers.Status import update_status, save_status, restore_status

#-----------------------------------------------------------------------------------------------
#
#   Inter-process lock based on flock(2)
#   The kernel releases the lock when the holding process dies, so no stale lock can remain.
#   Lock files are never deleted: deleting a flock file while others wait on it breaks mutual exclusion.
#
#-----------------------------------------------------------------------------------------------
class Lock:
    LOCK_DIR = '/opt/linupdate/locks'

    # Locks held by the current thread: {name: {'fd': int, 'count': int, 'shared': bool}}
    _thread_data = threading.local()

    def __init__(self, name: str, shared: bool = False, timeout: int = 3600, message: str = None):
        self.name = name
        self.shared = shared
        self.timeout = timeout
        self.message = message if message else 'Waiting for ' + name + ' lock to be released...'
        self.path = self.LOCK_DIR + '/' + name + '.lock'


    def __enter__(self):
        return self.acquire()


    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


    #-----------------------------------------------------------------------------------------------
    #
    #   Return locks held by the current thread
    #
    #-----------------------------------------------------------------------------------------------
    @classmethod
    def _held_locks(cls) -> dict:
        if not hasattr(cls._thread_data, 'locks'):
            cls._thread_data.locks = {}
        return cls._thread_data.locks


    #-----------------------------------------------------------------------------------------------
    #
    #   Acquire lock, waiting up to timeout seconds (None = wait forever, 0 = do not wait)
    #
    #-----------------------------------------------------------------------------------------------
    def acquire(self):
        held = self._held_locks()

        # Re-entrant within the same thread
        if self.name in held:
            if held[self.name]['shared'] and not self.shared:
                raise Exception('cannot upgrade shared lock ' + self.name + ' to exclusive')
            held[self.name]['count'] += 1
            return self

        try:
            Path(self.LOCK_DIR).mkdir(mode=0o750, parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o640)
        except Exception as e:
            raise Exception('could not open lock file ' + self.path + ': ' + str(e))

        mode = fcntl.LOCK_SH if self.shared else fcntl.LOCK_EX
        start_time = time.time()
        waiting = False

        try:
            while True:
                try:
                    fcntl.flock(fd, mode | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if self.timeout is not None and time.time() - start_time >= self.timeout:
                        raise Exception('could not acquire lock ' + self.path + ' within ' + str(self.timeout) + ' seconds')

                    if not waiting:
                        waiting = True
                        save_status()
                        update_status(self.message)

                    time.sleep(1)
        except BaseException:
            os.close(fd)
            raise
        finally:
            if waiting:
                restore_status()

        held[self.name] = {'fd': fd, 'count': 1, 'shared': self.shared}

        return self


    #-----------------------------------------------------------------------------------------------
    #
    #   Release lock (no-op if not held by the current thread)
    #
    #-----------------------------------------------------------------------------------------------
    def release(self):
        held = self._held_locks()

        if self.name not in held:
            return

        held[self.name]['count'] -= 1

        if held[self.name]['count'] > 0:
            return

        fd = held.pop(self.name)['fd']

        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


    #-----------------------------------------------------------------------------------------------
    #
    #   Return True if the lock is held by anyone (or only exclusively if exclusive_only is True)
    #
    #-----------------------------------------------------------------------------------------------
    @classmethod
    def is_locked(cls, name: str, exclusive_only: bool = False) -> bool:
        path = cls.LOCK_DIR + '/' + name + '.lock'

        if not Path(path).is_file():
            return False

        fd = os.open(path, os.O_RDONLY)

        try:
            fcntl.flock(fd, (fcntl.LOCK_SH if exclusive_only else fcntl.LOCK_EX) | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True
        finally:
            os.close(fd)
