'''
simple animation class
'''

from time import time
from wx import PyTimer as timer

class Listenable(object):
    __slots__ = ('listeners',)

    def __init__(self):
        self.listeners = []

    def add_listener(self, listener):
        self.listeners.append(listener)

    def remove_listener(self, listener):
        self.listeners.remove(listener)

    def _notify_listeners(self):
        for listener in self.listeners:
            listener()

class Animation(Listenable):
    __slots__ = ('frames', 'frame_delays', 'timer', 'index', 'started')

    def __init__(self, frames = None, frame_delays = None):
        Listenable.__init__(self)

        if frames is None:
            frames = []
        if frame_delays is None:
            frame_delays = []

        self.frames = frames
        self.frame_delays = frame_delays
        self.index = 0
        
        self.timer = timer(self._on_timer)

    def set_frames(self, frames, delays):
        assert all(isinstance(d, int) for d in delays)

        if self.frames:
            frame, delay = self.current_frame, self.current_frame_delay
        else:
            frame, delay = None, None

        old_frame_len = len(self.frames)

        assert frames, repr(frames)
        assert delays, repr(delays)

        self.frames = frames[:]
        self.frame_delays = delays[:]
        self.update_frame()

        # notify if our current frame is different
        if frame != self.current_frame:
            self._notify_listeners()

        # start if we only had one frame before, or if
        # the current delay is different.
        if (old_frame_len == 1 and len(frames) > 1) or \
                delay != self.current_frame_delay:

            if frame is None or old_frame_len == 1:
                self.start()
            else:
                diff = self.current_frame_delay - delay
                self.start(delay - abs(diff))

        # stop if only one frame
        if len(self.frames) == 1:
            self.stop()

    def start(self, delay = None):
        if delay is None:
            delay = self.current_frame_delay

        self.started = time()
        self.timer.Start(delay, True)

    def stop(self):
        self.timer.Stop()

    def increment_frame(self):
        self.index += 1
        self.update_frame()

    def update_frame(self):
        if self.index > len(self.frames)-1:
            self.index = 0

    @property
    def current_frame_delay(self):
        return self.frame_delays[self.index]

    @property
    def current_frame(self):
        return self.frames[self.index]

    def set_frame(self, i, frame):
        self.frames[i] = frame
        if self.index == i:
            self._notify_listeners()

    def _on_timer(self):
        self.increment_frame()
        self._notify_listeners()
        self.start()

