'''
Adds a status message showing your currently playing song from one of
several media players.
'''
from common.statusmessage import StatusMessage
from common import profile, pref

import platform, wx
from gui import skin

from logging import getLogger; log = getLogger('promote_status')

# a unicode character showing two eighth notes joined by a bar
PROMOTE_STATUS_PREF = 'plugins.promotestatus.initial_status'

def PROMOTE_STATUS_STRING():
    import branding
    url = branding.get('digsby.promote.url', 'digsby_promote', 'http://im.digsby.com')
    return u'I use Digsby to manage IM + Email + Social Networks - ' + url

class PromoteStatus(StatusMessage):
    __slots__ = StatusMessage.__slots__[:]
    __slots__.remove('message')

    # this indicates to status GUI that the message is not editable
    edit_toggle = False

    def __init__(self, message = None, status = None, editable = None, **kws):
        StatusMessage.__init__(self,
                               title    = u'Promote Digsby!',
                               status   ='available' if status is None else status,
                               message  = None,
                               editable = False,
                               edit_toggle = kws.get('edit_toggle', self.edit_toggle))

    message = property(lambda self: PROMOTE_STATUS_STRING(), lambda self, val: None)

    @property
    def icon(self):
        return skin.get('statusicons.promote', None)

# Add a status message to the global list.
def status_factory():
    '''
    Yes, a factory.
    '''
    import common
    if common.pref('social.use_global_status', default = False, type = bool):
        return

    start_status = pref(PROMOTE_STATUS_PREF, 'available')
    if start_status == 'idle':
        start_status = 'available'
    return PromoteStatus(status = start_status)

def on_before_status_change(status):
    '''
    Invoked when the profile's status message changes.
    '''
    log.info('on_status_change')

    if isinstance(status, PromoteStatus):
        s = status.status
        if pref(PROMOTE_STATUS_PREF, type = str, default = 'available') != s:
            profile.prefs.__setitem__(PROMOTE_STATUS_PREF, s.lower())
    return status

#def initialize():
#    import common
#    if common.pref('social.use_global_status', default = False, type = bool):
#        return
#
#    from peak.util.plugins import Hook
#    Hook('digsby.im.statusmessages', 'promote').register(status_factory)
#    Hook('digsby.im.statusmessages.set.pre', 'promote').register(on_before_status_change)

#initialize()
