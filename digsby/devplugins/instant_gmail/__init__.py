#__LICENSE_GOES_HERE__

from logging import getLogger
from peak.util.addons import AddOn
import traceback
import jabber.objects.gmail as gobjs
log = getLogger('plugins.instant_gmail')

class Digsby_IGmail(AddOn):
    def __init__(self, subject):
        self.protocol = subject
        super(Digsby_IGmail, self).__init__(subject)

    def setup(self, stream):
        self.stream = stream
        log.debug('setting up geoip')
        stream.set_iq_set_handler('new-mail', gobjs.GOOGLE_MAIL_NOTIFY_NS, self.gmail_notify)
        self.stream.send(gobjs.make_get(self.protocol))

    def gmail_notify(self, _stanza):
        try:
            from services.service_provider import get_provider_for_account
            p = get_provider_for_account(self.protocol.account)
            e = p.accounts.get('email')
            if e and e.enabled:
                e.update_now()
        except Exception:
            traceback.print_exc()

def session_started(protocol, stream, *_a, **_k):
    Digsby_IGmail(protocol).setup(stream)

