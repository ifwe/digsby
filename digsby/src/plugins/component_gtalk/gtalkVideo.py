from logging import getLogger
from peak.util.addons import AddOn
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.iq import Iq



log = getLogger('plugins.gtalk_video')
GTALK_SESSION_NS = 'http://www.google.com/session'
GTALK_VIDEO_SESSION_NS = 'http://www.google.com/session/video'



class gtalk_iq_video_initiate(AddOn):
    def __init__(self, subject):
        self.protocol = subject
        super(gtalk_iq_video_initiate, self).__init__(subject)

    def setup(self, stream):
        self.stream = stream
        log.debug('setting up iq session')
        stream.set_iq_set_handler('session', GTALK_SESSION_NS, self.video_initiate)

    def video_initiate(self, iq):
        d = dict(ses = GTALK_SESSION_NS,
                 vid = GTALK_VIDEO_SESSION_NS)

        vid_initiates = iq.xpath_eval("ses:session[@type='initiate']/vid:description", d)

        if vid_initiates:

            sessions = iq.xpath_eval("ses:session", d)

            iq_from = iq.get_from()

            if sessions:
                session = sessions[0]
                session_id = session.prop('id')
                if not session_id:
                    log.error('No ID found for videochat session initiation request')

                session_initiator = session.prop('initiator')
                if not session_initiator:
                    log.error('No initiator found for videochat session initiation request')

            def vidoechat_response_callback(accepted = False):
                if not accepted:
                    self.protocol.send_iq(GoogleSessionReject(session_id, session_initiator).make_set(iq_from))
                else:
                    log.error("Video Session accepted? But we don't support that yet!")


            self.protocol.convo_for(iq.get_from()).received_native_videochat_request(vidoechat_response_callback)

        self.protocol.send_iq(iq.make_result_response())

        return True

class GoogleSessionReject(StanzaPayloadObject):
    xml_element_name = 'session'
    xml_element_namespace = GTALK_SESSION_NS

    def __init__(self, id, initiator):
        self.id = id
        self.initiator = initiator

#    def __from_xml(self, node):
#        pass

    def complete_xml_element(self, xmlnode, doc):
        xmlnode.setProp("type", "reject")
        xmlnode.setProp("initiator", self.initiator)
        xmlnode.setProp("id", self.id)

    def make_set(self, to):
        iq = Iq(stanza_type="set")
        iq.set_to(to)
        self.as_xml(parent=iq.get_node())
        return iq



def session_started(protocol, stream, *a, **k):
    if getattr(protocol, 'name', None) != 'gtalk':
        return
    log.debug('registering "%s" feature', GTALK_SESSION_NS)
    gtalk_iq_video_initiate(protocol).setup(stream)

def initialized(protocol, *a, **k):
    if getattr(protocol, 'name', None) != 'gtalk':
        return
    protocol.register_feature(GTALK_SESSION_NS)
