'''
A handler for the following xmpp stanza:

<message>
    <update xmlns="digsby:updater" />
</message>

When it's received over the digsby stream, it notifies the hook 'digsby.updater.pushed'. Under normal circumstances,
the updater module is listening for this hook and when received, it will begin the update check process.
'''
from peak.util.addons import AddOn
import hooks
import logging

log = logging.getLogger('d_updater.xmpp')

DIGSBY_UPDATER_NS = "digsby:updater"

class DigsbyUpdateMessageHandler(AddOn):
    def setup(self, stream):
        self.stream = stream
        log.debug('setting up "%s" message handler', DIGSBY_UPDATER_NS)
        stream.set_message_handler('normal', self.handle_message,
                              namespace = DIGSBY_UPDATER_NS,
                              priority = 90)

    def handle_message(self, stanza):
        log.debug('update pushed')
        hooks.notify('digsby.updater.pushed')
        return True

def session_started(protocol, stream, *a, **k):
    if getattr(protocol, 'name', None) != 'digsby':
        # TODO: move this check of here, maybe by using impl='digsby'
        # when notifying?
        return
    DigsbyUpdateMessageHandler(protocol).setup(stream)

def initialized(protocol, *a, **k):
    if getattr(protocol, 'name', None) != 'digsby':
        # TODO: move this check of here, maybe by using impl='digsby'
        # when notifying?
        return
    log.debug('registering "%s" feature', DIGSBY_UPDATER_NS)
    protocol.register_feature(DIGSBY_UPDATER_NS)

def send_update(protocol, name):
    '''
    Used to push an update stanza to all logged in digsby users.
    '''
    import pyxmpp
    m = pyxmpp.all.Message(to_jid=pyxmpp.all.JID(name, 'digsby.org'))
    update = m.xmlnode.newChild(None, 'update', None)
    update_ns = update.newNs(DIGSBY_UPDATER_NS, None)
    protocol.send(m)
