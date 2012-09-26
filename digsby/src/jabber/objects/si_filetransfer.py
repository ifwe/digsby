from pyxmpp.jabber.dataforms import DATAFORM_NS
from pyxmpp.jabber.dataforms import Form
from pyxmpp.jabber import dataforms
from pyxmpp.utils import to_utf8
from pyxmpp.xmlextra import common_doc
from pyxmpp.utils import from_utf8
from pyxmpp.xmlextra import get_node_ns_uri
import libxml2

from si import * #@UnusedWildImport
SI_FILETRANSFER_NS = SI_NS + "/profile/file-transfer"
FEATURE_NEG_NS = "http://jabber.org/protocol/feature-neg"

class SI_FileTransfer(SI):
    '''
    Stream initiation file transfer stanza.
    '''

    def __init__(self, xmlnode_or_id=None, mime_type=None):
        '''

        :Parameters:
            - `xmlnode_or_id`:
            - `mime_type`:
        :Types:
            - `xmlnode_or_id`: `libxml2.xmlNode` or `unicode`
            - `mime_type`: `unicode`
        '''

        SI.__init__(self, xmlnode_or_id=xmlnode_or_id, mime_type=mime_type,
                    profile_ns=SI_FILETRANSFER_NS)
        self.file = None
        self.feature = None
        if isinstance(xmlnode_or_id,libxml2.xmlNode):
            self.from_xml(xmlnode_or_id)

    def from_xml(self,node,strict=True):
        """Initialize SI_FileTransfer from XML node."""
        n=node.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=SI_FILETRANSFER_NS and ns!=FEATURE_NEG_NS:
                n=n.next
                continue
            if n.name=="file":
                try:
                    self.file = File(n)
                except ValueError:
                    if strict:
                        raise
            elif n.name =="feature":
                try:
                    self.feature = Feature(n)
                except ValueError:
                    if strict:
                        raise
            n=n.next

    def complete_xml_element(self, xmlnode, _unused):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `_unused`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `_unused`: `libxml2.xmlDoc`"""
        SI.complete_xml_element(self, xmlnode, _unused)
        self.file.as_xml(xmlnode, _unused) if self.file else None
        self.feature.as_xml(xmlnode, _unused) if self.feature else None

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r


class File(StanzaPayloadObject):
    xml_element_name = 'file'
    xml_element_namespace = SI_FILETRANSFER_NS
    def __init__(self, xmlnode_or_name=None, size=None, hash=None, date=None,
                 desc=None, length=None, offset=None):
        """
        :Types:
            - `xmlnode_or_name`: `libxml2.xmlNode` or `unicode`
            - `size`: `int`
            - `hash`: `unicode` #skipping this for now
            - `date`: #skipping this for now
        """
        if isinstance(xmlnode_or_name,libxml2.xmlNode):
            self.from_xml(xmlnode_or_name)
        else:
            self.name = xmlnode_or_name
            self.size = size
            self.hash = hash
            self.date = date
            self.length = length
            self.desc   = desc
            self.offset = offset

    def from_xml(self,node):
        """Initialize File from XML node."""
        if node.type!="element":
            raise ValueError,"XML node is not a file element (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=SI_FILETRANSFER_NS or node.name!="file":
            raise ValueError,"XML node is not a file element"
        name = node.prop("name")
        self.name = from_utf8(name) if name else None
        size = node.prop("size")
        self.size = int(from_utf8(size)) if size else None
        hash = node.prop("hash")
        date = node.prop("date")
        self.hash = from_utf8(hash) if hash else None
        self.date = from_utf8(date) if date else None
        desc = None
        length = None
        offset = None
        n=node.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=SI_FILETRANSFER_NS:
                n=n.next
                continue
            if n.name =="desc":
                desc = n.getContent()
            elif n.name == "range":
                offset = n.prop("offset")
                length = n.prop("length")
            n=n.next
        self.desc   = from_utf8(desc)        if desc   else None
        self.offset = int(from_utf8(offset)) if offset else None
        self.length = int(from_utf8(length)) if length else None

    def complete_xml_element(self, xmlnode, _unused):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `_unused`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `_unused`: `libxml2.xmlDoc`"""
        xmlnode.setProp("name",to_utf8(self.name)) if self.name else None
        xmlnode.setProp("size",to_utf8(str(self.size))) if self.size else None
        xmlnode.setProp("hash",to_utf8(self.hash)) if self.hash else None
#        xmlnode.setProp("date",to_utf8(self.date)) if self.date else None
        if self.length or self.offset:
            range = xmlnode.newChild(None, 'range', None)
            range.setProp("length",to_utf8(str(self.length))) if self.length else None
            range.setProp("offset",to_utf8(str(self.offset))) if self.offset else None
        xmlnode.newTextChild(None, "desc", to_utf8(self.desc)) if self.desc else None

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

class Feature(StanzaPayloadObject):
    xml_element_name = 'feature'
    xml_element_namespace = FEATURE_NEG_NS

    def __init__(self, xmlnode=None, possible_streams=None, selected_stream=None):
        if isinstance(xmlnode,libxml2.xmlNode):
            self.from_xml(xmlnode)
        else:
            self.possible_streams = possible_streams
            self.selected_stream = selected_stream

    def from_xml(self,node):
        """Initialize Feature from XML node."""
        if node.type!="element":
            raise ValueError,"XML node is not a feature element (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=FEATURE_NEG_NS or node.name!="feature":
            raise ValueError,"XML node is not a feature element"
        possible_streams = []
        self.selected_stream = None
        n=node.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=DATAFORM_NS or n.name!="x":
                n=n.next
                continue
            form=dataforms.Form(n, strict=False)
            if not form.type:
                form.type = "form"
            try:
                field = form['stream-method']
            except KeyError:
                n=n.next
                continue
            else: #if new_streams:
                self.selected_stream = field.value
                possible_streams.extend(field.options)
            n=n.next
        self.possible_streams = [v for o in possible_streams for v in o.values] or None

    def complete_xml_element(self, xmlnode, _unused):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `_unused`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `_unused`: `libxml2.xmlDoc`"""
        if self.possible_streams:
            field = dataforms.Field(name='stream-method', field_type='list-single',
                                    options=[dataforms.Option(n)
                                             for n in self.possible_streams])
            f = dataforms.Form(xmlnode_or_type='form', fields=[field])
        else:
            f = Form(xmlnode_or_type="submit")
            f.add_field(name='stream-method', value=self.selected_stream)
        f.as_xml(xmlnode, _unused)

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r
