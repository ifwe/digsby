import logging
log = logging.getLogger('msn.p2p.msnobj')
import hashlib
import sys
import io
import random
import uuid
import msn.P2P as P2P
import msn.MSNObject as MSNObject
import msn.P2P.P2PApplication as P2PApp
import msn.P2P.P2PMessage as P2PMessage

@P2PApp.P2PApplication.RegisterApplication
class ObjectTransfer(P2PApp.P2PApplication):
    AppId = 12
    EufGuid = uuid.UUID("A4268EEC-FEC5-49E5-95C3-F126696BDBF6")

    sending = False
    msnObject = None

    def _get_AutoAccept(self):
        return True

    def _get_InvitationContext(self):
        return (str(self.msnObject) + '\0').encode('b64')

    def __init__(self, session = None, obj = None, remote = None):
        if session is not None:
            # We're sending
            super(ObjectTransfer, self).__init__(session = session)
            self.msnObject = MSNObject.parse(self.P2PSession.Invitation.BodyValues['Context'].decode('b64').strip('\0'))
            if self.msnObject.type == '3':
                self.msnObject = self.client.self_buddy.msn_obj
                self.data_buffer = self.client.self_buddy.icon_path.open('rb')

            self.sending = True
            AppId = self.P2PSession.Invitation.BodyValues.get('AppID', None)
            if AppId is not None:
                self.AppId = int(AppId)

        else:
            super(ObjectTransfer, self).__init__(ver = remote.P2PVersionSupported, remote = remote, remoteEP = remote.SelectRandomEPID())
            self.msnObject = obj
            self.data_buffer = io.BytesIO()
            if obj.type == '3':
                self.AppId = 12

            self.sending = False

    def SetupInviteMessage(self, slp):
        slp.BodyValues['RequestFlags'] = '18'
        super(ObjectTransfer, self).SetupInviteMessage(slp)

    def ValidateInvitation(self, invite):
        ret = super(ObjectTransfer, self).ValidateInvitation(invite)
        if not ret:
            return ret

        return MSNObject.parse(invite.BodyValues['Context'].decode('b64').strip('\0')).type == '3'

    def Start(self):
        if not super(ObjectTransfer, self).Start():
            return False

#        if self.Remote.DirectBridge is None:
#            log.error("Don't have a direct bridge (MSNObject)")
#            return False

        if self.sending:
            log.info("Starting send for %r", self)
            self.P2PSession.Bridge.packageNumber += 1
            packNum = self.P2PSession.Bridge.packageNumber
            prepData = P2PMessage.P2PDataMessage(self.version)
            prepData.WritePreparationBytes()

            if self.version == P2P.Version.V2:
                prepData.Header.TFCombination = P2P.TFCombination.First

            def after_data_prep_send(ack = None):
                allData = self.data_buffer.read()
                self._close_data_buffer()

                msg = P2PMessage.P2PDataMessage(self.version)
                if self.version == P2P.Version.V1:
                    msg.Header.Flags = P2P.Flags.Data
                    msg.Header.AckSessionId = random.randint(50, sys.maxint)
                else:
                    msg.Header.TFCombination = P2P.TFCombination.MsnObject | P2P.TFCombination.First
                    msg.Header.PackageNumber = packNum

                msg.InnerBody = allData

                if self.version == P2P.Version.V1:
                    log.info("Sending data message for (V1) %r", self)
                    self.SendMessage(msg, success = lambda ack: self.OnTransferFinished())
                else:
                    log.info("Sending data message for (V2) %r", self)

                    def after_data_send(ack = None):
                        rak = P2PMessage.P2PMessage(self.version)
                        rak.SetRAK()
                        log.info("Sending RAK message for (V2). rak = %r, app = %r", rak, self)
                        self.SendMessage(rak, success = lambda ack: self.OnTransferFinished())

                    self.SendMessage(msg, success = after_data_send)

            log.info("Sending data prep message for %r", self)

            self.SendMessage(prepData, after_send = after_data_prep_send)

        else:
            log.info("Starting receive for %r", self)
            self.data_buffer = io.BytesIO()

    def ProcessData(self, bridge, data, reset):
        if hasattr(data, 'getvalue'):
            data = data.getvalue()

        log.info('ProcessData: bridge = %r, data = %r, reset = %r', bridge, data, reset)
        if self.sending:
            return False

        if reset:
            self.data_buffer = io.BytesIO()

        if len(data):
            self.data_buffer.write(data)

            log.info("Got %s/%s bytes", self.data_buffer.tell(), self.msnObject.size)
            if str(self.data_buffer.tell()) == self.msnObject.size:
                log.info("\t finished!")
                allData = self.data_buffer.getvalue()
                dataSha = hashlib.sha1(allData).digest()
                if dataSha.encode('b64') != self.msnObject.sha1d:
                    log.error("dataSha = %r, expectedSha = %r", dataSha.encode('b64'), self.msnObject.sha1d)
                    return False

                self.data_buffer = io.BytesIO()
                self.OnTransferFinished(allData)
                if self.P2PSession:
                    self.P2PSession.Close() # Sends BYE

        return True

    def _close_data_buffer(self):
        if self.sending:
            getattr(getattr(self, 'data_buffer', None), 'close', lambda:None)()

    def OnTransferFinished(self, *a):
        self._close_data_buffer()
        super(ObjectTransfer, self).OnTransferFinished(*a)

    def OnTransferAborted(self, who):
        self._close_data_buffer()
        super(ObjectTransfer, self).OnTransferAborted(who)

    def OnTransferError(self):
        self._close_data_buffer()
        super(ObjectTransfer, self).OnTransferError()

