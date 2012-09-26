# XXX: shouldn't this be in util? or common?
from __future__ import division
import sys, time
if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time

time = time.time

class RateMonitor(object):
    time_threshold = .5 # Must have collected data for at least .5 seconds before a BPS value can be calc'd

    def __init__(self, processor):
        '''
        Keeps track of how fast data is being processed by 'processor'
        '''

        self.f_process        = processor

        self.bytecounts     = []
        self.written        = 0
        self._bps           = 0

    def handle_data(self, data):
        self._process(len(data))
        self.f_process(data)

    def _process(self, num_bytes):
        if num_bytes > 0:
            self._add_byte_data(time(), self.written + num_bytes)

    @property
    def bps(self):
        '''
        Bytes per second.
        '''
        now = time()

        self._add_byte_data(now, self.written)

        if len(self.bytecounts) <= 1:
            self._add_byte_data(now, self.written)
            self._bps = 0
            return self._bps


        oldest, lowest  = self.bytecounts[0]
        newest, highest = self.bytecounts[-1]

        time_diff = newest - oldest
        byte_diff = highest - lowest

        if byte_diff and (time_diff > self.time_threshold):
            self._bps = byte_diff/time_diff
        else:
            self._bps = 0

        return self._bps

    def _add_byte_data(self, tstamp, bytecount):
        self.written = bytecount

        tstamp     = tstamp
        bytecounts = self.bytecounts

        if not bytecounts:
            bytecounts.append((tstamp, bytecount))

        oldtime, oldcount = bytecounts[-1]

        if oldcount == bytecount:
            bytecounts[-1] = (tstamp, bytecount)
        elif tstamp > oldtime:
            bytecounts.append((tstamp, bytecount))
        elif tstamp == oldtime:
            bytecounts[-1] = (tstamp, bytecount)

        now = time()

        while bytecounts and ((now - bytecounts[0][0]) > self.window):
            bytecounts.pop(0)


class RateLimiter(RateMonitor):
    def __init__(self, processor, limit, window=1):
        '''
        limit: bytes per second
        window: how large of a sliding window to use to compute speed

        Calls self.too_fast(data) when data is being sent too fast.
        '''

        RateMonitor.__init__(self, processor)
        self.limit            = limit
        self.window           = window
        self._called_too_fast = False

    def handle_data(self, data):
        self._process(len(data))

        if self.bps > self.limit:
            if not self._called_too_fast:
                self.too_fast(data)
                self._called_too_fast = True
            return False
        else:
            self.f_process(data)
            self._called_too_fast = False
            return True

if __name__ == '__main__':
    class TooFastPrinter(RateLimiter):
        def too_fast(self, data):
            print ('was sending %d bytes too fast!' % len(data)), self._bps

    rl = TooFastPrinter(lambda d: None, 20480, 1)

    for i in xrange(2048):
        rl.write('a')
    print len(rl.bytecounts), rl.bps, rl.written
