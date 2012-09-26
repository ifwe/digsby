"""
Functionality common to more than one protocol goes here.

Of course, everything should be as generic as possible in this folder.
"""

import util
callsback = util.callsback
Timer = util.Timer
from logging import getLogger; log = getLogger('common'); info = log.info

def setfakeprefs(userprefs):
    'Set a fake prefs dict and defaults dict for use in test applications.'
    from common import profile
    _prefs.update(userprefs)

castables = (int, float, long, unicode)

_prefs = {}
_defaultprefs = {}

def set_active_prefs(prefs, defaults=None):
    '''
    Sets the dictionary pref() will find prefs in.
    '''
    if defaults is None:
        defaults = {}
    global _prefs, _defaultprefs
    _prefs = prefs
    _defaultprefs = defaults

def pref(pref, default=sentinel, type=sentinel):
    '''
    Lookup a pref.
    '''

    global _prefs, _defaultprefs

    if default is sentinel:
        default = _defaultprefs.get(pref, default)

    if default is sentinel:
        val = _prefs[pref]
    else:
        val = _prefs.get(pref, default)

    if type is sentinel or val.__class__ is type:
        return val

    if type in castables:
        try: val = type(val)
        except ValueError:
            if default is sentinel: raise TypeError('pref val was incorrect type: %r' % val)
            else: return default
        else:
            return val

    elif not isinstance(val, type):
        if default is sentinel: raise TypeError('pref val was incorrect type: %r' % val)
        else: return default

    return val

class prefprop(object):
    'Read only class property always returning the current value of "pref"'

    __slots__ = ('pref', 'default', 'type')

    def __init__(self, pref, default = sentinel, type = sentinel):
        self.pref = pref
        self.default = default
        self.type = type

    def __repr__(self):
        try:
            msg = repr(self.pref)

            if self.default is not sentinel:
                msg += ', default=%r' % self.default
            if self.type is not sentinel:
                msg += ', type=%r' % self.type
        except Exception:
            msg = '???'

        return '<prefprop %s>' % msg

    def __get__(self, obj, objtype=None):
        try:
            return profile.prefs[self.pref]
        except KeyError:
            if self.default is sentinel:
                raise
            else:
                return self.default

@callsback
def netcall(callable, callback = None):
    from AsyncoreThread import call_later
    call_later(callable, callback = callback)


class _profile_proxy(object):
    '''
    Unfortunately, we use the DigsbyProfile object as a big bad global object
    to store tons of state. Because of this (questionable) design, import
    dependencies get really circular between the digsbyprofile module and just
    about everything else.

    To avoid these problems, most of the codebase does "from common import
    profile" and uses this object (which forwards getattr lookups) as if it
    were actually the digsbyprofile.profile global.
    '''

    def __getattr__(self, attr):
        import digsbyprofile
        globals()['digsbyprofile'] = digsbyprofile
        object.__setattr__(self, '__getattr__',
                           lambda attr, dp=digsbyprofile: getattr(dp.profile, attr))
        return getattr(digsbyprofile.profile, attr)

    def __setattr__(self, key, val):
        raise NotImplementedError()

    def __call__(self):
        from digsbyprofile import profile
        return profile

    def __nonzero__(self):
        from digsbyprofile import profile
        return profile is not None

profile = _profile_proxy()

def setpref(pref, val):
    from digsbyprofile import profile
    prefs = getattr(profile, 'prefs', {})

    prefs[pref] = val

def setprefif(pref, val):
    from digsbyprofile import profile
    prefs = getattr(profile, 'prefs', {})
    if prefs.get(pref, sentinel) != val:
        setpref(pref, val)
        return True

    return False

def delpref(pref):
    from digsbyprofile import profile
    prefs = getattr(profile, 'prefs', {})

    prefs.pop(pref, None)

def silence_notifications(connection, duration=None):
    info('Silencing notifications from %r', connection)

    connection._notifyquiet = True
    def afterTimeout():
        connection._notifyquiet = False
        info('Unsilencing notifications from %r', connection)

    if duration is None:
        duration = pref('notifications.quiet_time', 5)
    timer = Timer(duration, afterTimeout)
    timer.start()
    return timer

from inspect import getargspec

def bind(actionname):
    assert isinstance(actionname, basestring)

    def wrap(func):
        args = getargspec(func)[0]

        # TODO: use inspect to do this correctly.
        # if the function expects self, give it the window that emitted the event.
        if len(args) == 1 and args[0] == 'self':
            def cb(win, func=func):
                return func(win)
        else:
            def cb(win, func=func):
                return func()

        from gui.input import add_action_callback
        add_action_callback(actionname, cb)
        return func

    return wrap

from .hashacct import HashedAccount
from Protocol import Protocol as protocol
from Protocol import StateMixin
from AsyncSocket import AsyncSocket as socket
from Buddy import Buddy as buddy
from Buddy import write_hashes, get_bname
from Conversation import Conversation
from actions import ActionMeta, action, Action, ActionError
from timeoutsocket import TimeoutSocket, TimeoutSocketOne
from hydrasocket import HydraSocket
from filetransfer import FileTransfer, OutgoingFileTransfer, \
    IncomingFileTransfer, IncomingHTTPFileTransfer

from accountbase import AccountBase, FromNetMixin
from statusmessage import StatusMessage, StatusMessageException, acct_reduce
from UpdateMixin import UpdateMixin
from notifications import fire

import commandline

try:
    from contacts.Contact import ContactCapabilities as caps
except ImportError:
    pass

