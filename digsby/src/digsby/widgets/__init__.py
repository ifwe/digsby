from pyxmpp.iq import Iq
DIGSBY_WIDGETS_NS     = 'digsby:widgets'
import widget
from widget import Widget
from widgets import Widgets

def create():
    'Opens the "create widget" page in a web browser.'
    from digsby.web.weblogin import autologin
    from common import profile

    autologin(profile.username, profile.password,
              'http://widget.digsby.com')

def make_get(digsby_protocol):
    iq = Iq(stanza_type="get")
    iq.set_to(digsby_protocol.jid.domain)
    q = iq.new_query(DIGSBY_WIDGETS_NS)
    return iq