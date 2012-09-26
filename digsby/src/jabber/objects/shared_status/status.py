from jabber.objects.shared_status import SHARED_STATUS_NS
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.iq import Iq
import jabber
import libxml2
import util
from util.primitives.error_handling import try_this as try_

class StatusList(StanzaPayloadObject, list):
    show = None
    xml_element_name = "status-list"
    xml_element_namespace = SHARED_STATUS_NS

    def __init__(self, xmlnode_or_sequence, show=None):
        list.__init__(self)
        if isinstance(xmlnode_or_sequence, libxml2.xmlNode):
            self.__from_xml(xmlnode_or_sequence)
        else:
            if show:
                self.show = show
            self[:] = xmlnode_or_sequence

    def complete_xml_element(self, xmlnode, doc):
        if self.show is not None:
            xmlnode.setProp("show", self.show.encode("utf-8"))

        for status in self:
            xmlnode.newTextChild(None, "status", status.encode("utf-8"))

    def __from_xml(self, xmlnode, *a, **k):
        show_l = jabber.jabber_util.xpath_eval(xmlnode, "@show", namespaces={'gss': SHARED_STATUS_NS})
        if show_l:
            show = show_l[0]
            self.show = show.getContent().decode('utf-8')

        self[:] = (node.getContent().decode('utf-8') for node in
                   jabber.jabber_util.xpath_eval(xmlnode, "gss:status/text()", namespaces={'gss': SHARED_STATUS_NS}))

class SharedStatus(StanzaPayloadObject, util.primitives.mapping.odict):
    xml_element_name = 'query'
    xml_element_namespace = SHARED_STATUS_NS
    version = 2

    status_max               = None
    status_list_max          = None
    status_list_contents_max = None
    status_min_ver           = None

    invisible                = None

    def __init__(self, xmlnode):
        util.primitives.mapping.odict.__init__(self)
        if isinstance(xmlnode,libxml2.xmlNode):
            self.__from_xml(xmlnode)
        else:
            #not sure
            pass

    def __from_xml(self, xmlnode, *a, **k):
        sls = [StatusList(node) for node in
               jabber.jabber_util.xpath_eval(xmlnode, "gss:query/gss:status-list[@show]",
                                  namespaces={'gss': SHARED_STATUS_NS})]
        self.update((l.show, l) for l in sls)

        status = jabber.jabber_util.xpath_eval(xmlnode, "gss:query/gss:status/text()",
                                               namespaces={'gss': SHARED_STATUS_NS})
        show   = jabber.jabber_util.xpath_eval(xmlnode, "gss:query/gss:show/text()",
                                               namespaces={'gss': SHARED_STATUS_NS})
        self.status = status[0].getContent() if status else None
        self.show   = show[0].getContent() if show else None
        query_l = jabber.jabber_util.xpath_eval(xmlnode, "gss:query",
                                  namespaces={'gss': SHARED_STATUS_NS})
        query = query_l[0] if query_l else None

        if query is not None:
            self.status_max               = try_((lambda: int(query.prop("status-max"))), None)
            self.status_list_max          = try_((lambda: int(query.prop("status-list-max"))), None)
            self.status_list_contents_max = try_((lambda: int(query.prop("status-list-contents-max"))), None)
            self.status_min_ver           = try_((lambda: int(query.prop("status-min-ver"))), None)

        invis = jabber.jabber_util.xpath_eval(xmlnode, "gss:query/gss:invisible/@value",
                                               namespaces={'gss': SHARED_STATUS_NS})
        self.node = xmlnode
        self.invisible = invis[0].getContent() == 'true' if invis else None

    def complete_xml_element(self, xmlnode, doc):
        xmlnode.setProp("version", unicode(self.version).encode('utf-8'))

        if self.status is not None:
            xmlnode.newTextChild(None, 'status', self.status[:self.status_max or None].encode('utf-8'))
        if self.show is not None:
            xmlnode.newTextChild(None, 'show', self.show.encode('utf-8'))
        else:
            xmlnode.newTextChild(None, 'show', u'default'.encode('utf-8'))

        for status_list in self.values():
            status_list.as_xml(xmlnode, doc)

        for attr in ("status-max", "status-list-max", "status-list-contents-max", "status-min-ver"):
            val = getattr(self, attr.replace('-', '_'), None)
            if val is not None:
                xmlnode.setProp(attr, str(val))

        invis = xmlnode.newChild(None, 'invisible', None)
        invis.setProp('value', str(bool(self.invisible)).lower())

    def make_push(self, gtalk_protocol):
        iq=Iq(stanza_type="set")
        self.as_xml(parent=iq.xmlnode)
        return iq

