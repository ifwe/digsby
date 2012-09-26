from __future__ import with_statement
import logging

from util.primitives.funcs import get, isint
from util.xml_tag import tag

import msn
from msn import Message
from msn.p8 import Notification as Super


log = logging.getLogger('msn.p9.ns')

defcb = dict(trid=True, callback=sentinel)

class MSNP9Notification(Super):

    events = Super.events | set((
        'recv_sms',
        'contact_icon_info',
    ))

    versions = ['MSNP9']
    def _set_buddy_icon(self, status, clientid, icon_data, callback):
        if icon_data is not None:

            import hashlib
            hash = hashlib.sha1(icon_data).digest()

            import random
            fn = 'temp%d.dat' % random.randint(1,1000)
            self.icon_obj = msn.MSNObject(Creator=self.self_buddy.name,
                                          Type='3',
                                          Location=fn,
                                          Size=len(icon_data),
                                          SHA1D=hash)
            self.self_buddy.msn_obj = self.icon_obj
            self.self_buddy.notify('icon_hash')
            log.debug('setting icon obj')
        self.send_chg(status, clientid, callback=callback)

    def _get_buddy_icon(self, name, callback):
        log.info('get buddy icon: %s',name)
#        return
#        b = self.buddies[bname]
#        if not b.online:
#            log.info('Not retrieving buddy icon for %s -- they are offline', bname)
#            return
#
##        c = self.conv_class(self, bname, success=self.conv_class.get_buddy_icon)
##        self.icon_requests.append(c)
#        c = BuddyIconGetter(self, b)
#        c.connect()

#    def _send_file(self, buddy, file):
#        #TODO: scrap this and only use P2P objects
#        c = FileSender(self, buddy, fstruct=file)
#        c.connect()
##        c = self.convo_for(buddy)#, self.conv_class.send_file, fstruct=file)
##        c.on_connect = lambda x:x.send_file(buddy.name, fstruct=file)


    def _parse_iln_nln(self, msg):
        log.debug('got iln/nln')
        args = Super._parse_iln_nln(self, msg)

        iconinfo = msn.util.url_decode(get(msg.args, 4, ''))

        msnobj = None
        if '<' in iconinfo and '>' in iconinfo:
            try:
                msnobj = msn.MSNObject.parse(iconinfo)
            except Exception, e:
                log.error('Error parsing msn object (%r). here\'s data: %r', e, iconinfo)

        return args, msnobj

    def recv_iln(self, msg):
        args, msnobj = self._parse_iln_nln(msg)

        name = args[0]

        self.event('contact_online_initial', *args)
        self.event('contact_icon_info', name, msnobj)

    def recv_nln(self, msg):
        args, msnobj = self._parse_iln_nln(msg)

        name = args[0]

        self.event('contact_online', *args)
        self.event('contact_icon_info', name, msnobj)

    def recv_chg(self, msg):
        Super.recv_chg(self, msg)
        if not msg.args:
            self.icon_obj = None
        else:
            msnobj = msg.args[-1]
            self.icon_obj = msn.MSNObject.parse(msn.util.url_decode(msnobj))

        self.event('contact_icon_info', self._username, self.icon_obj)

    def recv_ipg(self, msg):
        log.debug('Received IPG command')
        log.debug(str(msg))

        n = tag(msg.payload)

        sender  = n.FROM['name']
        message = n.MSG.BODY.TEXT

        if sender.startswith('tel:+'):
            sender = sender[4:]

        self.event('recv_sms', sender, unicode(message))

    def send_png(self):
        log.debug('ping')

        self.socket.send(Message('PNG'))
        log.info('pinged')

    def send_chg(self, code, client_id, callback=None):

        if code.lower() == 'fln':
            code = 'HDN'

        iconobj = getattr(self, 'icon_obj', None)
        if iconobj:
            msnobj = msn.util.url_encode(iconobj.to_xml())
        else:
            msnobj = ''

        self.socket.send(Message('CHG', code, str(client_id), msnobj),
                         trid=True, callback=(callback or sentinel))

