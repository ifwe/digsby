from pyxmpp.iq import Iq
GOOGLE_MAIL_NOTIFY_NS ='google:mail:notify'

def make_get(gtalk_protocol):
    iq = Iq(stanza_type="get")
    _q = iq.new_query(GOOGLE_MAIL_NOTIFY_NS)
    return iq
