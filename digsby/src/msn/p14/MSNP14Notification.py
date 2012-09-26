from logging import getLogger
log = getLogger('msn.p14.ns')

from util.primitives.funcs import get

import msn
from msn.p13 import Notification as Super



class MSNP14Notification(Super):
    versions = ['MSNP14']
    client_chl_id = challenge_id = "PROD0112J1LW7%NB"
    client_chl_code = "RH96F{PHI8PPX_TJ"

    events = Super.events | set((
         'fed_message',
    ))

    def recv_iln(self, msg):
        'ILN 8 NLN digsby09@hotmail.com 1 digsby09@hotmail.com 1073791028 0'

        log.debug('got iln')

        (status, name, btype, nick, client_id), __args = msg.args[:5], (msg.args[5:] or [])

        nick = nick.decode('url').decode('fuzzy utf8') or None
        btype = int(btype)
        client_id = self.parse_caps(client_id)

        iconinfo = msn.util.url_decode(get(__args, 0, ''))

        if '<' in iconinfo and '>' in iconinfo:
            msnobj = msn.MSNObject.parse(iconinfo)
        else:
            msnobj = None

        self.event('contact_online_initial', name, nick, status, client_id)
        self.event('contact_icon_info', name, msnobj)

        self.event('contact_btype', name, btype)

    def recv_nln(self, msg):
        'NLN IDL digsby09@hotmail.com 1 digsby09@hotmail.com 1073791028 0 \r\n'
        log.debug('got nln')

        (status, name, btype, nick, client_id), __args = msg.args[:5], (msg.args[5:] or [])

        nick = nick.decode('url').decode('fuzzy utf8') or None
        btype = int(btype)
        client_id = self.parse_caps(client_id)

        iconinfo = msn.util.url_decode(get(__args, 0, ''))

        if '<' in iconinfo and '>' in iconinfo:
            msnobj = msn.MSNObject.parse(iconinfo)
        else:
            msnobj = None

        self.event('contact_online', name, nick, status, client_id)
        self.event('contact_icon_info', name, msnobj)

        self.event('contact_btype', name, btype)

#    def recv_fln(self, msg):
#        pass

    def recv_ubx(self, msg):
        bname, btype = msg.args
        msg.args = [bname]

        self.event('contact_btype', bname, int(btype))

        Super.recv_ubx(self, msg)

    def recv_ubm(self, msg):
        name = msg.args[0]
        self.event('fed_message', name, msg)

