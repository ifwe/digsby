import uuid
import msn.P2P as P2P
import msn.P2P.P2PApplication as P2PApp
import msn.P2P.P2PMessage as P2PMessage

@P2PApp.P2PApplication.RegisterApplication
class P2PActivity(P2PApp.P2PApplication):
    AppId = 0
    EufGuid = uuid.UUID("6A13AF9C-5308-4F35-923A-67E8DDA40C2F")

    sending = False
    ActivityData = ''
    ActivityName = ''

    def __init__(self, session = None, ver = None, remote = None, remoteEP = None, activityName = '', activityData = ''):
        self.ActivityName = activityName
        self.ActivityData = activityData

        if session is None:
            super(P2PActivity, self).__init__(ver = remote.P2PVersionSupported, remote = remote, remoteEP = remote.SelectRandomEPID())
            self.sending = True
        else:
            super(P2PActivity, self).__init__(ver = session.Version, remote = session.Remote, remoteEP = session.RemoteContactEndPointID)

            try:
                activityUrl = session.Invitation.BodyValues['Context'].decode('base64').decode('utf-16-le')
                activityProperties = filter(None, activityUrl.split(';'))
                if len(activityProperties) > 3:
                    AppId = int(activityProperties[0])
                    self.ActivityName = activityProperties[2]

            except Exception:
                pass

            self.sending = False

    def _get_InvitationContext(self):
        return (self.AppId + ';1;' + self.ActivityName).encode('utf-16-le').encode('base64')

    def ValidateInvitation(self, invitation):
        ret = super(P2PActivity, self).ValidateInvitation(invitation)

        if not ret:
            return ret

        try:
            ret = len(filter(None, invitation.BodyValues['Context'].decode('base64').decode('utf-16-le').split(';'))) > 3
        except Exception:
            pass

        return ret

    def Start(self):
        if not super(P2PActivity, self).Start():
            return False

        if not self.sending:
            return

        if not self.ActivityData:
            return

        self.ActivityData += u'\0'
        urlLength = len(self.ActivityData.encode('utf-16-le'))

        prepData = P2PMessage.P2PDataMessage(self.version)
        if self.version == P2P.Version.V1:
            header = '\x80\0\0\0'
        else:
            header = '\x80\x3f\x14\x05'

        data = ''+header
        data += struct.pack('<H', 8)
        data += struct.pack('<I', urlLength)
        data += self.ActivityData.encode('utf-16-le')

        prepData.InnerBody = urlData

        if self.version == P2P.Version.V2:
            prepData.Header.TFCombination = P2P.TFCombination.First

        self.SendMessage(prepData)

    def ProcessData(self, bridge, data, reset):
        return True

