'A vector with n components.'

from __future__ import division
from itertools import izip
import math

class vector(list):
    def __init__(self, *a):
        if len(a) == 1: list.__init__(self, *a)
        else:           list.__init__(self, iter(a))

    def __getslice__(self, i, j): return vector(list.__getslice__(i,j))

    def __add__(self, v): return vector(x+y for x,y in izip(self, v))
    def __neg__(self): return vector(-x for x in self)
    def __sub__(self, v): return vector(x-y for x,y in izip(self, v))
    def __mul__(self, o):
        try:    iter(o)
        except: return vector(x*o for x in self)
        else:   return vector(x*y for x,y in izip(o))

    def div(self, o):
        try:    iter(o)
        except: return vector(x/o for x in self)
        else:   return vector(x*y for x,y in izip(o))

    def __repr__(self): return 'vec' + repr(tuple(self))

    @classmethod
    def distance(cls, v1, v2):
        return sum((y-x)**2 for x,y in izip(v1, v2)) ** 0.5

    def to(self, other):
        return vector.distance(self, other)

    @property
    def length(self):
        return vector.distance(self, (0,)*len(self))

    @property
    def normal(self):
        try:
            return self.div(self.length)
        except ZeroDivisionError:
            return vector((0,)*len(self))

    @staticmethod
    def zero(n = 2):
        return vector((0,) * n)

    @property
    def angle(self):
        try:
            return abs(math.atan(self[1] / self[0]) * 180.0 / math.pi)
        except ZeroDivisionError:
            return 90
