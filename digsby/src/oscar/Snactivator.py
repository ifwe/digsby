'''

Snactivator.py

'''
from __future__ import with_statement
from itertools import count
from traceback import print_exc
from util import TimeOut
from util.primitives.structures import PriorityQueue, EmptyQueue

import logging
log = logging.getLogger('oscar.snactivator')

class Snactivator(TimeOut):
    'Rate limiting SNAC consumer.'

    ids = count()
    def __init__(self, socket):
        TimeOut.__init__(self)
        self.socket = socket
        # create a PriorityQueue for each rate class
        self.queues = [PriorityQueue()
                       for __ in xrange(len(socket.rate_classes))]

    def send_snac(self, snac, priority = 5):
        if self.finished():
            log.error('Snactivator can\'t send this snac, because it\'s finished: %r', snac)
            return
        rclass = self.socket.snac_rate_class(*snac)
        if not rclass:
            return self.socket._send_snac(snac)

        with self._cv:
            queue = self.queues[self.socket.rate_classes.index(rclass)]
            queue.append(snac, priority)
            self._cv.notify()

    send_snac_first = send_snac

    def compute_timeout(self):
        if self.finished():
            self._last_computed = -1
            self.socket = None
        else:
            # Find the smallest time to wait.
            times = []
            for q in (queue for queue in self.queues if queue):
                snac = q.peek()
                t = self.socket.time_to_send(snac)
                times.append(t)

            self._last_computed = min(times or [5])

        return self._last_computed

    def process(self):
        for q in self.queues:
            if not q: continue

            try:
                snac = q.peek()
            except EmptyQueue:
                continue
            t = self.socket.time_to_send(snac)

            # If any snacs are ready to send, send them.
            if t == 0 and not self.finished():
                try:
                    snac = q.next()
                except Exception:
                    return
                else:
                    try:
                        self.socket._send_snac(snac)
                    except Exception:
                        print_exc()
                        self.socket.test_connection()
