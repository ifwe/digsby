from __future__ import with_statement
'''
Msnifier.py
'''
__author__ = 'dotSyntax'

import itertools
from time import sleep
from types import GeneratorType as generator
import logging

from util import TimeOut, default_timer
from util.primitives.structures import PriorityQueue

log = logging.getLogger('msn.msnifier')
#log.setLevel(logging.DEBUG)

class Msnifier(TimeOut):
    'Rate limiting MSN packet consumer.'

    def __init__(self, socket):
        TimeOut.__init__(self)
        self.to_send = None
        self.socket = socket

        # create a PriorityQueue for packets
        self.queue = PriorityQueue()

    def send_pkt(self, pkt, priority=5, **kw):

        with self._cv:
            self.queue.append((pkt, kw), priority)
            #self._cv.notifyAll()

    def compute_timeout(self):
        if self._finished:
            self._last_computed = -1
        else:
            self._last_computed = 5
            (pkt, kw) = self.next_pkt()
            if pkt is not None:
                self._last_computed = self.socket.time_to_send(str(pkt))
                self.queue.append((iter([pkt]), kw), priority=1)

        return self._last_computed

    def process(self):
        pkt, kw = self.next_pkt()

        if pkt is not None:
            callback = kw.pop('callback', None)
            if not self.socket._send(str(pkt), **kw):
                getattr(callback, 'error', lambda: None)()
            else:
                log.warning("calling after_send: %r", getattr(callback, 'after_send', None))
                getattr(callback, 'after_send', lambda: None)()

    def next_pkt(self):
        pkt = None
        kw = {}
        q = self.queue
        while pkt is None and q:
            try:
                x, kw = q.peek()
                try:
                    pkt = x.next()
                except AttributeError:
                    pkt, kw = q.next() # this is x, but now we are removing it from the queue
            except (GeneratorExit, StopIteration, ValueError):
                # head of q is a completed generator, remove it
                q.next()

        return pkt, kw
