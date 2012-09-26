from pyxmpp.iq import Iq
SHARED_STATUS_NS = 'google:shared-status'

def make_get(gtalk_protocol):
    iq = Iq(stanza_type="get")
    q = iq.new_query(SHARED_STATUS_NS)
    q.setProp("version", '2')
    return iq
