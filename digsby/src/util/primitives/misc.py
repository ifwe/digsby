import subprocess
import calendar
import datetime
import time

#import logging
#log = logging.getLogger('util.primitives.misc')

def clamp(number, min_=None, max_=None):

    if None not in (min_, max_) and (min_ > max_):
        max_ = min_

    if min_ is not None:
        number = max(min_, number)

    if max_ is not None:
        number = min(max_, number)

    return number

def backtick(cmd, check_retcode = True):
    '''
    Returns the standard output of a spawned subprocess.

    Like `perl`.
    '''
    proc = subprocess.Popen(cmd.split(' '), stdout = subprocess.PIPE)
    proc.wait()

    if check_retcode and proc.returncode != 0:
        raise Exception('subprocess returned nonzero: %s' % cmd)

    return proc.stdout.read()

class ysha(object):
    h0 = 0x67452301
    h1 = 0xEFCDAB89
    h2 = 0x98BADCFE
    h3 = 0x10325476
    h4 = 0xC3D2E1F0

def fromutc(t):
    '''
    Takes a UTC datetime and returns a localtime datetime
    '''
    return datetime.datetime(*time.localtime(calendar.timegm(t.timetuple()))[:-2])

def toutc(t):
    '''
    takes a localtime datetime and returns a UTC datetime
    '''
    return datetime.datetime(*time.gmtime(time.mktime(t.timetuple()))[:-2])

#see TODO in NonBool; sentinel would be used for the default
#try:
#    sentinel
#except NameError:
#    sentinel = object()

class NonBool(object):
    def __nonzero__(self):
        raise TypeError('NonBool cannot be bool()ed, use ==/is CONSTANT')
    #TODO: add a value that can be compared.  NonBool(5) == 5
