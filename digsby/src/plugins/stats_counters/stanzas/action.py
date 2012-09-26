from . import DIGSBY_STATS_COUNTER_NS
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.utils import from_utf8, to_utf8
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
import libxml2

SYNC_PROTOS = frozenset(['myspace', 'twitter', 'linkedin', 'facebook',
                         'gmail', 'ymail', 'hotmail', 'aolmail', 'pop', 'imap'])

WHITELISTED_TYPES = set([
                               'link_post',
                               'im_sent',
                               'im_received',
                               'emoticon_box_viewed',
                               'emoticon_chosen',
                               'video_chat_requested',
                               'sms_sent',
                               'log_viewed',
                               'prefs.prefs_opened',
                               'imwin.imwin_created',
                               'imwin.imwin_engage',
                               'contact_added',
                               'ui.dialogs.add_contact.created',
                               'ui.select_status',
                               'infobox.shown',
                               'feed_ad.citygrid.click_cents',
                               'research.run_time',
                               ])

class Action(StanzaPayloadObject):
    xml_element_name = 'action'
    xml_element_namespace = DIGSBY_STATS_COUNTER_NS

    def __init__(self, xmlnode_or_type=None, initial=None, value=None, result=None):
        # from an incoming XML node
        if isinstance(xmlnode_or_type, libxml2.xmlNode):
            return self.__from_xml(xmlnode_or_type)
        else:
            self.type = xmlnode_or_type
            self.initial = initial
            self.value = value
            self.result = result

        if self.type not in WHITELISTED_TYPES:
            raise ValueError("valid type required! (got %r)" % self.type)

    def __repr__(self):
        return '<Digsby.Action %s %r:%r:%r>' % (self.type, self.initial, self.value, self.result)

    def __from_xml(self, node):
        '''A libxml2 node to a digsby.action'''
        if node.type!="element":
            raise ValueError,"XML node is not an action element (not en element)"
        ns = get_node_ns_uri(node)
        if ns and ns != DIGSBY_STATS_COUNTER_NS or node.name != "action":
            raise ValueError,"XML node is not an action element"
        type = node.prop("type")
        self.type = from_utf8(type) if type is not None else None
        initial = node.prop("initial")
        self.initial = int(from_utf8(initial)) if initial is not None else None
        value = node.prop("value")
        self.value = int(from_utf8(value)) if value is not None else None
        result = node.prop("result")
        self.result = int(from_utf8(result)) if result is not None else None

    def complete_xml_element(self, xmlnode, _unused):
        'to xml'

        setProp(xmlnode, 'type', self.type)
        setProp(xmlnode, 'initial', self.initial)
        setProp(xmlnode, 'value', self.value)
        setProp(xmlnode, 'result', self.result)

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

def setProp(xmlnode, attr, value):
    if value is not None:
        xmlnode.setProp(attr, to_utf8(value))

