from util import default_timer, TimeOut

class IdleLoopTimer(TimeOut):
    def __init__(self, seconds, func, *a, **k):
        self.seconds = seconds
        self.func = func
        self.a = a
        self.k = k
        TimeOut.__init__(self)

    def start(self):
        self.done_at = default_timer() + self.seconds
        TimeOut.start(self)

    def compute_timeout(self):
        self._last_computed = self.done_at - default_timer()
        return self._last_computed

    def process(self):
        self.func(*self.a, **self.k)
        self.done_at = default_timer() + self.seconds