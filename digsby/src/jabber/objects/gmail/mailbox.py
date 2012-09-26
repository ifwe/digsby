from jabber.objects.gmail.mail_thread_info import MailThreadInfo
from pyxmpp.utils import from_utf8
from jabber.jabber_util.functions import xpath_eval
from pyxmpp.xmlextra import get_node_ns_uri
from jabber.objects.gmail import GOOGLE_MAIL_NOTIFY_NS
from pyxmpp.objects import StanzaPayloadObject


#result-time     The time these results were generated, in milliseconds since the UNIX epoch. This value should be cached and sent as the newer-than-time attribute in the next email query.
#total-matched     The number of emails that matched the q attribute search string in the email query, or the number of unread emails if no query was specified. If total-estimate is 1, this will be just an estimate of the number of emails retrieved.
#total-estimate     A number indicating whether total-matched is just an estimate: 1 indicates it is; 0 or omitted indicates that it is not.
#url  The URL of the Gmail inbox.
#contains n    mail-thread-info

class Mailbox(StanzaPayloadObject, list):
    xml_element_name = 'mailbox'
    xml_element_namespace = GOOGLE_MAIL_NOTIFY_NS

    def __init__(self, xmlnode):
        self.__from_xml(xmlnode)

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not a %s element (not en element)" % self.xml_element_name
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not an %s element" % self.xml_element_name

        self.result_time = int(from_utf8(node.prop("result-time")))
        self.total_matched = int(from_utf8(node.prop("total-matched")))
        self.url = from_utf8(node.prop("url"))

        total_estimate = node.prop("messages")
        self.total_estimate = int(from_utf8(total_estimate)) if total_estimate else 0

        threads = xpath_eval(node, 'g:mail-thread-info',{'g':GOOGLE_MAIL_NOTIFY_NS})
        self.extend(MailThreadInfo(thread) for thread in threads)

