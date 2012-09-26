from threadpool2 import *
from timeout_thread import *

import contextlib
from ..Events import EventMixin
class InvertedSemaphore(EventMixin):
    events = EventMixin.events | set((
        'resource_release',
        'resource_acquire',
    ))

    def __init__(self, init = 0, lock = None):
        EventMixin.__init__(self)
        assert init >= 0
        self._value = init

        if lock is not None:
            assert hasattr(lock, '__enter__') and hasattr(lock, '__exit__')
            self.lock = lambda:lock

    def acquire(self):
        do_event = False
        with self.lock():
            self._value += 1

            if self._value == 1:
                do_event = True

        if do_event:
            self.event("resource_acquire")

    def release(self):
        do_event = False
        with self.lock():
            if self._value == 0:
                raise ValueError("Can't release when internal counter is at 0")

            self._value -= 1

            if self._value == 0:
                do_event = True

        if do_event:
            self.event("resource_release")

    @contextlib.contextmanager
    def lock(self):
        try:
            yield None
        finally:
            pass
