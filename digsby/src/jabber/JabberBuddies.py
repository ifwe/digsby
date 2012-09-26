from jabber import JID
from util.observe import observable_dict
from traceback import print_exc

import jabber
import logging
log = logging.getLogger('jabber.buddies')

class JabberBuddies(observable_dict):
    def __init__(self, protocol):
        observable_dict.__init__(self)
        self.protocol = protocol

    def __getitem__(self, jid):
        unique = JID(jid).bare()
        try:
            return dict.__getitem__(self, unique)
        except KeyError:
            return self.setdefault(unique, self.protocol.buddy_class(self.protocol, jid))

    def update_presence(self, presence_stanza):
        jid = presence_stanza.get_from()
        log.debug('update_presence for %r', jid)

        try:
            buddy = self[jid]
        except Exception, e:
            log.warning('update_presence, "buddy = self[jid]": %r', e)
            print_exc()
            return False

        try:
            buddy.update_presence(presence_stanza)
        except Exception, e:
            log.warning('update_presence, "buddy.update_presence(presence_stanza)": %r' %e )
            print_exc()
            return False

        return True
