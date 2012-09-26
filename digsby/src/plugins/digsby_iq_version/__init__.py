from decimal import Decimal
from logging import getLogger
from peak.util.addons import AddOn
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.utils import to_utf8
from pyxmpp.xmlextra import get_node_ns_uri
import hooks
import libxml2
import traceback
import sys

log = getLogger('plugins.digsby_geoip')

DIGSBY_VERSION_NS = 'digsby:iq:version'

class Digsby_IqVersion(AddOn):
    def __init__(self, subject):
        self.protocol = subject
        super(Digsby_IqVersion, self).__init__(subject)

    def setup(self, stream):
        self.stream = stream
        log.debug('setting up digsby:iq:version')
        stream.set_iq_get_handler('query', DIGSBY_VERSION_NS, self.version_get)

    def version_get(self, iq):
        iq = iq.make_result_response()
        q = iq.new_query(DIGSBY_VERSION_NS)
        q.newTextChild( q.ns(), "name", "Digsby Client" )
        q.newTextChild( q.ns(), "version", ('%s' % (getattr(sys, 'REVISION', '?') or '?')))
        for k in ('TAG', 'BRAND'):
            v = getattr(sys, k, None)
            if v:
                q.newTextChild( q.ns(), k.lower(), str(v))
        if not self.protocol.hide_os:
            import platform
            platform_string = platform.platform()
            # for some reason, on my XP box, platform.platform() contains both
            # the platform AND release in platform.platform(). On Ubuntu, OS X,
            # and I believe older versions of Windows, this does not happen,
            # so we need to add the release in all other cases.
            if platform_string.find("XP") == -1:
                platform_string += " " + platform.release()

            q.newTextChild( q.ns(), "os", platform_string )
        self.protocol.send(iq)
        return True

def session_started(protocol, stream, *a, **k):
    Digsby_IqVersion(protocol).setup(stream)

def initialized(protocol, *a, **k):
    protocol.register_feature(DIGSBY_VERSION_NS)
