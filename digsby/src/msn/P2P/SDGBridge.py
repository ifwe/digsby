import logging
log = logging.getLogger('msn.p2p.sdg')
import util.callbacks as callbacks
import msn.P2P.P2PBridge as Bridge
import msn.MSNCommands as MSNC

class SDGBridge(Bridge.P2PBridge):
    BridgeType = 'SDGBridge'
    nsHandler = None

    def _get_IsOpen(self):
        return self.nsHandler is not None and self.nsHandler.CONNECTED

    def _get_MaxDataSize(self):
        return 11748

    def _get_Synced(self):
        return False

    def SuitableFor(self, session):
        return True

    def _get_Remote(self):
        raise Exception()

    def Dispose(self):
        super(SDGBridge, self).Dispose()
        self.client = self.nsHandler = None

    def __init__(self, client):
        self.client = self.nsHandler = client
        super(SDGBridge, self).__init__(queueSize = 8)

    def SendOnePacket(self, session, remote, remoteGuid, message, callback = None):
        message = self.SetSequenceNumberAndRegisterAck(session, remote, message, callback)

        to = "%d:%s;epid={%s}" % (int(remote.type), remote.account, remoteGuid)
        owner = self.nsHandler.contact_list.owner
        from_ = '%d:%s;epid={%s}' % (int(owner.type), owner.account, self.nsHandler.get_machine_guid())

        if message.Header.Identifier == 0:
            log.error("Sending message with no identifier: %r", message)

        slp = message.InnerMessage if message.IsSLPData else None
        if slp is not None and slp.ContentType in ("application/x-msnmsgr-transreqbody",
                                                   "application/x-msnmsgr-transrespbody",
                                                   "application/x-msnmsgr-transdestaddrupdate"):
            content = (('Message-Type', 'Signal/P2P'),
                       ('Content-Type', 'text/plain; charset=UTF-8'),
                       )
            body = slp.GetBytes(False)
        else:
            content = (
                ('Content-Type', 'application/x-msnmsgrp2p'),
                ('Content-Transfer-Encoding', 'binary'),
                ('Message-Type', 'Data'),
                ('Pipe', str(self.packageNumber)),
                ('Bridging-Offsets', '0'),
            )

            body = message.GetBytes(True)

        mmMessage = MSNC.MultiPartMime((
                                       (('Routing', '1.0'),
                                        ('To', to),
                                        ('From', from_),
                                        ('Service-Channel', 'PE'),
                                        ('Options', '0'),
                                        ),

                                        (
                                         ('Reliability', '1.0'),
                                         ),

                                        (('Messaging', '2.0'),)
                                         + content,
                                        ),

                                        body = body,
                                       )

        def success(*a, **k):
            self.FireSendCompleted(message, session)

        callback.success += success
        self.nsHandler.socket.send(MSNC.SDG(payload = str(mmMessage)), trid = True, callback = callback)

    SendOnePacket = callbacks.callsback(SendOnePacket, ('success', 'error', 'after_send', 'progress'))

    def FireSendCompleted(self, message, session):
        self.OnBridgeSent(session, message)
