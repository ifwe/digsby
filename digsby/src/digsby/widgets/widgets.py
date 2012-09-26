from digsby.widgets.widget import Widget
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import get_node_ns_uri
from digsby.widgets import DIGSBY_WIDGETS_NS
from jabber.jabber_util import xpath_eval

class Widgets(StanzaPayloadObject, list):
    xml_element_name = 'query'
    xml_element_namespace = DIGSBY_WIDGETS_NS

    def __init__(self, xmlelem):
        self.__from_xml(xmlelem)

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not an Widgets element (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=DIGSBY_WIDGETS_NS or node.name!="query":
            raise ValueError,"XML node is not an Widgets element"
        widgets = xpath_eval(node, 'w:widget',{'w':DIGSBY_WIDGETS_NS})
        self.extend(Widget(widget) for widget in widgets)
