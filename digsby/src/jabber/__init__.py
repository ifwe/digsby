status_state_map = {
    'available':      'normal',
    'away':           'away',
    'free for chat':  'chat',
    'do not disturb': 'dnd',
    'extended away':  'xa'
}

import disco
import filetransfer
import objects
import jabber_util
import threadstreamsocket
from util.primitives.structures import enum
from pyxmpp.jid import JID as JID
from pyxmpp.presence import Presence as Presence
from pyxmpp.jabber.vcard import VCard
from jabber.JabberResource import JabberResource as resource
from jabber.JabberConversation import JabberConversation as conversation
from jabber.JabberBuddy import JabberBuddy as jbuddy
from jabber.JabberContact import JabberContact as jcontact
from jabber.JabberBuddies import JabberBuddies as jbuddies
from jabber.JabberProtocol import JabberProtocol as protocol
from jabber.JabberChat import JabberChat as chat
from jabber.filetransfer.S5BFileXferHandler import SOCKS5Bytestream
from jabber.objects.si import SI_NS
from jabber.objects.bytestreams import BYTESTREAMS_NS
from jabber.objects.si_filetransfer import SI_FILETRANSFER_NS
from jabber.idle_loop import IdleLoopTimer

from PIL import Image #@UnresolvedImport

class JabberException(Exception):
    pass

show_types           = (None, u"away", u"xa", u"dnd", u"chat")
available_show_types = (None, u"chat", u'normal')



status_states = enum(["Online",
                      "Away",
                      "Extended Away",
                      "Do Not Disturb",
                      "Free For Chat"])

features_supported = ['http://jabber.org/protocol/disco#info',
                      BYTESTREAMS_NS,
                      SI_NS,
                      SI_FILETRANSFER_NS]

#### pyxmpp overrides ####
import pyxmpp.jabber.vcard as vcard
vcard.VCard.components.update({"FN": (vcard.VCardString,"optional"),
                               "N" : (vcard.VCardName,  "optional")})

import pyxmpp.streambase as streambase

def _process_node(self,xmlnode):
    """Process first level element of the stream.

    The element may be stream error or features, StartTLS
    request/response, SASL request/response or a stanza.

    :Parameters:
        - `xmlnode`: XML node describing the element
    """
    ns_uri=xmlnode.ns().getContent()
    if ns_uri=="http://etherx.jabber.org/streams":
        self._process_stream_node(xmlnode)
        return

    if ns_uri==self.default_ns_uri:
        stanza=streambase.stanza_factory(xmlnode, self)
        stanza.handler_frees = False
        self.lock.release()
        try:
            self.process_stanza(stanza)
        finally:
            self.lock.acquire()
            if not stanza.handler_frees:
                stanza.free()
    else:
        self.__logger.debug("Unhandled node: %r" % (xmlnode.serialize(),))

streambase.StreamBase._process_node = _process_node


class VCardPhotoData(vcard.VCardField, vcard.VCardImage):
    def __init__(self,value):
            vcard.VCardField.__init__(self,"PHOTO")
            self.image = value
            self.type = unicode(image_mimetype(value))
            self.uri=None

def image_mimetype(imgdata):
    'Returns the MIME type for image data.'
    import StringIO
    return 'image/' + Image.open(StringIO.StringIO(imgdata)).format.lower()

class VCardAdr(vcard.VCardField, vcard.VCardAdr):
    def __init__(self,value):
            vcard.VCardField.__init__(self,"PHOTO")
            (self.pobox,self.extadr,self.street,self.locality,
                self.region,self.pcode,self.ctry)=[""]*7
            self.type=[]

def rosterclone(self):
    return type(self)(self.jid, self.subscription, self.name, groups=tuple(self.groups))

import pyxmpp.roster
pyxmpp.roster.RosterItem.clone = rosterclone

from pyxmpp.client import Client
from pyxmpp.jabber.client import JabberClient
from pyxmpp.jabber.disco import DISCO_ITEMS_NS,DISCO_INFO_NS
from pyxmpp.jabber import disco as pyxmpp_disco
#this moves Client.authorized to the bottom, so that all handlers are set up
#before the session can start, since that's what requests it.
def authorized(self):
    """Handle "authorized" event. May be overriden in derived classes.
    By default: request an IM session and setup Disco handlers."""
    self.stream.set_iq_get_handler("query",DISCO_ITEMS_NS,self._JabberClient__disco_items)
    self.stream.set_iq_get_handler("query",DISCO_INFO_NS,self._JabberClient__disco_info)
    pyxmpp_disco.register_disco_cache_fetchers(self.cache,self.stream)
    Client.authorized(self)

JabberClient.authorized = authorized
