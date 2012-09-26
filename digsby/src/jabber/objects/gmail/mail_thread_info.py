#tid     The thread id of this thread.
#participation     A number indicating the user's participation level in this thread: 0 indicates that the user has not participated; 1 indicates that the user is one of many recipients listed in the thread; 2 indicates that the user is the sole recipient for messages in this thread.
#messages     The number of messages in the thread.
#date     A timestamp of the most recent message, in milliseconds since the UNIX epoch.
#url     The URL linking to this thread
#
#<senders>
#<labels>
#<subject>
#<snippet>
from jabber.objects.gmail.senders import Senders
from pyxmpp.utils import from_utf8
from jabber.jabber_util.functions import xpath_eval
from pyxmpp.xmlextra import get_node_ns_uri
from jabber.objects.gmail import GOOGLE_MAIL_NOTIFY_NS
from pyxmpp.objects import StanzaPayloadObject

class MailThreadInfo(StanzaPayloadObject):
    xml_element_name = 'mail-thread-info'
    xml_element_namespace = GOOGLE_MAIL_NOTIFY_NS

    def __init__(self, xmlnode):
        self.__from_xml(xmlnode)

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not a %s element (not en element)" % self.xml_element_name
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not an %s element" % self.xml_element_name

        labelss = xpath_eval(node, 'g:labels',{'g':GOOGLE_MAIL_NOTIFY_NS})
        labels = labelss[0].getContent() if labelss else None
        self.labels = from_utf8(labels).split('|') if labels else []

        senderss = xpath_eval(node, 'g:senders',{'g':GOOGLE_MAIL_NOTIFY_NS})
        self.senders = Senders(senderss[0]) if senderss else []

        subjects = xpath_eval(node, 'g:subject',{'g':GOOGLE_MAIL_NOTIFY_NS})
        self.subject = from_utf8(subjects[0].getContent()) if subjects else None

        snippets = xpath_eval(node, 'g:snippet',{'g':GOOGLE_MAIL_NOTIFY_NS})
        self.snippet = from_utf8(snippets[0].getContent()) if snippets else None

        self.tid = int(from_utf8(node.prop("tid")))
        self.participation = int(from_utf8(node.prop("participation")))
        self.messages = int(from_utf8(node.prop("messages")))
        self.date = int(from_utf8(node.prop("date")))
        self.url = from_utf8(node.prop("date"))

