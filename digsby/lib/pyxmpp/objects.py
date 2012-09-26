#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# pylint: disable-msg=W0232, E0201

"""General base classes for PyXMPP objects."""

__revision__="$Id: objects.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import libxml2
from pyxmpp.xmlextra import common_doc

class StanzaPayloadObject(object):
    """Base class for objects that may be used as XMPP stanza payload and don't keep
    internal XML representation, only parsed values.

    Provides `as_xml` method. Derived classes must override `xml_element_name` and
    `xml_element_namespace` class attributes and the `complete_xml_element` method.

    Please note that not all classes derived from `StanzaPayloadObject` should be
    used directly as stanza payload. Some of them are parts of higher level objects.

    :Cvariables:
        - `xml_element_name`: name for the XML element provided by the class.
        - `xml_element_namespace`: namespace URI for the XML element provided
          by the class.
    :Types:
        - `xml_element_name`: `unicode`
        - `xml_element_namespace`: `unicode`
    """
    xml_element_name = None
    xml_element_namespace = None

    def as_xml(self, parent = None, doc = None):
        """Get the XML representation of `self`.

        New document will be created if no `parent` and no `doc` is given.

        :Parameters:
            - `parent`: the parent for the XML element.
            - `doc`: the document where the element should be created. If not
              given and `parent` is provided then autodetection is attempted.
              If that fails, then `common_doc` is used.
        :Types:
            - `parent`: `libxml2.xmlNode`
            - `doc`: `libxml2.xmlDoc`
        :return: the new XML element or document created.
        :returntype: `libxml2.xmlNode` or `libxml2.xmlDoc`"""
        if parent:
            if not doc:
                n = parent
                while n:
                    if n.type == "xml_document":
                        doc = n
                        break
                    n = n.parent
                if not doc:
                    doc = common_doc
            try:
                ns = parent.searchNsByHref(doc, self.xml_element_namespace)
            except libxml2.treeError:
                ns = None
            xmlnode = parent.newChild(ns,self.xml_element_name,None)
            if not ns:
                ns = xmlnode.newNs(self.xml_element_namespace,None)
                xmlnode.setNs(ns)
            doc1 = doc
        else:
            if doc:
                doc1 = doc
            else:
                doc1 = libxml2.newDoc("1.0")
            xmlnode = doc1.newChild(None,self.xml_element_name, None)
            ns = xmlnode.newNs(self.xml_element_namespace, None)
            xmlnode.setNs(ns)

        self.complete_xml_element(xmlnode, doc1)

        if doc or parent:
            return xmlnode
        doc1.setRootElement(xmlnode)
        return doc1

    def complete_xml_element(self, xmlnode, doc):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `doc`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `doc`: `libxml2.xmlDoc`"""
        pass

class StanzaPayloadWrapperObject(object):
    """Base class for objects that may be used as XMPP stanza payload and maintain
    an internal XML representation of self.

    Provides `as_xml` method. Objects of derived classes must have the `xmlnode` attribute.

    Please note that not all classes derived from `StanzaPayloadWrapperObject` should be
    used directly as stanza payload. Some of them are parts of higher level objects.

    :Ivariables:
        - `xmlnode`: XML node of the object.
    :Types:
        - `xmlnode`: `libxml2.xmlNode`
    """

    def as_xml(self, parent = None, doc = None):
        """Get the XML representation of `self`.

        New document will be created if no `parent` and no `doc` is given.

        :Parameters:
            - `parent`: the parent for the XML element.
            - `doc`: the document where the element should be created. If not
              given and `parent` is provided then autodetection is attempted.
              If that fails, then `common_doc` is used.
        :Types:
            - `parent`: `libxml2.xmlNode`
            - `doc`: `libxml2.xmlDoc`

        :return: the new XML element (copy of `self.xmlnode`) or document
            created (containg the copy as the root element).
        :returntype: `libxml2.xmlNode` or `libxml2.xmlDoc`"""
        if parent:
            if not doc:
                n = parent
                while n:
                    if n.type == "xml_document":
                        doc = n
                        break
                    n = n.parent
                if not doc:
                    doc = common_doc
            copy=self.xmlnode.docCopyNode(doc,True)
            parent.addChild(copy)
            return copy
        else:
            if not doc:
                doc1=libxml2.newDoc("1.0")
            else:
                doc1=doc
            xmlnode=doc1.addChild(self.xmlnode.docCopyNode(doc,True))
            doc1.setRootElement(xmlnode)
            if doc:
                return xmlnode
            return doc1

# vi: sts=4 et sw=4
