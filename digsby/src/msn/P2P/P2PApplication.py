import logging
log = logging.getLogger('msn.p2p.app')

import msn.P2P as P2P
import uuid
import util.Events as Events
import util.callbacks as callbacks
import util.primitives.funcs as funcs

class AppStatus(object):
    Waiting = 0
    Active = 1
    Finished = 2
    Aborted = 3
    Error = 4

class P2PApp(object):
    def __init__(self, EufGuid, AppId, Type):
        self.EufGuid = EufGuid
        self.AppId = AppId
        self.Type = Type

    def __eq__(self, other):
        return self.EufGuid == getattr(other, 'EufGuid', None) and \
                self.AppId == getattr(other, 'AppId', None) and \
                self.Type == getattr(other('Type', None))

class P2PApplication(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'TransferStarted',
        'TransferFinished',
        'TransferAborted',
        'TransferError',
    ))

    AppId = 0
    EufGuid = uuid.UUID(int = 0)

    localEP = uuid.UUID(int = 0)
    remoteEP = uuid.UUID(int = 0)

    status = AppStatus.Waiting
    version = P2P.Version.V1

    client = None
    session = None
    remote = None
    local = None

    def __init__(self, session = None, ver = None, remote = None, remoteEP = None):
        Events.EventMixin.__init__(self)
        if session is not None:
            self.client = session.protocol
            self.P2PSession = session
            self.version = session.Version
            self.remote = self.session.Remote
        else:
            self.client = remote.client
            self.version = ver
            self.remote = getattr(remote, 'contact', remote)
            self.remoteEP = remoteEP

        self.local = self.client.self_buddy.contact
        self.localEP = self.client.get_machine_guid()

    def _get_P2PVersion(self):
        return self.version
    def _set_P2PVersion(self, val):
        raise AttributeError("Not settable")
    P2PVersion = funcs.iproperty("_get_P2PVersion", "_set_P2PVersion")

    InvitationContext = funcs.iproperty("_get_InvitationContext", "_set_InvitationContext")

    def _get_AutoAccept(self):
        return False
    def _set_AutoAccept(self, val):
        raise AttributeError("Not settable")
    AutoAccept = funcs.iproperty("_get_AutoAccept", "_set_AutoAccept")

    def _get_ApplicationId(self):
        if self.AppId == 0:
            self.AppId = type(self).FindApplicationId(self)
        return self.AppId

    def _set_ApplicationId(self, val):
        raise AttributeError("Not settable")
    ApplicationId = funcs.iproperty("_get_ApplicationId", "_set_ApplicationId")

    def _get_ApplicationEufGuid(self):
        if self.EufGuid == uuid.UUID(int = 0):
            self.EufGuid = type(self).FindApplicationEufGuid(self)
        return self.EufGuid

    def _set_ApplicationEufGuid(self, val):
        raise AttributeError("Not settable")
    ApplicationEufGuid = funcs.iproperty("_get_ApplicationEufGuid", "_set_ApplicationEufGuid")

    def _get_ApplicationStatus(self):
        return self.status
    ApplicationStatus = funcs.iproperty("_get_ApplicationStatus", "_set_ApplicationStatus")

    @property
    def Local(self):
        return self.local
    @property
    def Remote(self):
        return self.remote
    @property
    def Version(self):
        return self.version

    def _get_P2PSession(self):
        return self.session

    def _set_P2PSession(self, val):
        if self.session is not None:
            self.session.unbind_event('Closing', self.P2PSessionClosing)
            self.session.unbind_event('Closed', self.P2PSessionClosed)
            self.session.unbind_event('Error', self.P2PSessionError)

        self.session = val
        if self.session is not None:
            self.session.bind_event('Closing', self.P2PSessionClosing)
            self.session.bind_event('Closed', self.P2PSessionClosed)
            self.session.bind_event('Error', self.P2PSessionError)

    P2PSession = funcs.iproperty("_get_P2PSession", "_set_P2PSession")

    def SetupInviteMessage(self, slp):
        slp.BodyValues['EUF-GUID'] = ('{%s}' % self.ApplicationEufGuid).upper()
        slp.BodyValues['AppID'] = str(self.ApplicationId)
        slp.BodyValues['Context'] = self.InvitationContext

    def ValidateInvitation(self, invitation):
        ret = invitation.ToEmailAccount.lower() == self.local.account.lower()

        if ret and self.version == P2P.Version.V2:
            ret = invitation.ToEndPoint == self.localEP

        return ret

    def ProcessData(self, bridge, data, reset):
        return NotImplemented

    def SendMessage(self, message, callback = None):
        assert message.Version == self.version

        if self.P2PSession is None:
            callback.error()
            log.error("No session to send message with! message = %r", message)
            return

        message.Header.SessionId = self.P2PSession.SessionId
        if (message.Version == P2P.Version.V1) and ((message.Header.Flags & P2P.Flags.Ack) != P2P.Flags.Ack):
            message.Footer = self.ApplicationId

        self.P2PSession.Send(message, callback = callback)

    SendMessage = callbacks.callsback(SendMessage, ('success', 'error', 'after_send', 'progress'))

    def BridgeIsReady(self):
        return

    def Start(self):
        if self.status in (AppStatus.Finished, AppStatus.Aborted, AppStatus.Error):
            return False

        if self.status == AppStatus.Active:
            log.error("Can't start app again! %r", self)
            return False
        self.OnTransferStarted()
        return True

    def Accept(self):
        if self.P2PSession is None:
            return
        self.P2PSession.Accept()

    def Decline(self):
        if self.P2PSession is None:
            return
        self.P2PSession.Decline()

    def Abort(self):
        self.OnTransferAborted(self.local)
        if self.P2PSession is None:
            return
        self.P2PSession.Close()

    def Dispose(self):
        if self.P2PSession is not None:
            self.P2PSession.KillTimeoutTimer()

        if self.status not in (AppStatus.Aborted, AppStatus.Finished, AppStatus.Error):
            self.OnTransferError()

        self.P2PSession = None

    def OnTransferStarted(self):
        log.info("TransferStarted: %r", self)
        self.status = AppStatus.Active
        self.TransferStarted(self)

    def OnTransferFinished(self, *a):
        if self.status not in (AppStatus.Aborted, AppStatus.Finished, AppStatus.Error):
            log.info("TransferFinished: %r", self)
            self.status = AppStatus.Finished
            if self.P2PSession is not None:
                self.P2PSession.KillTimeoutTimer()
                self.P2PSession = None
            self.TransferFinished(self, *a)

    def OnTransferAborted(self, who):
        if self.status not in (AppStatus.Aborted, AppStatus.Finished, AppStatus.Error):
            log.info("TransferAborted: %r, %r", self, who)
            self.status = AppStatus.Aborted
            if self.P2PSession is not None:
                self.P2PSession.KillTimeoutTimer()
                self.P2PSession = None
            self.TransferAborted(self, who)

    def OnTransferError(self):
        if self.status not in (AppStatus.Aborted, AppStatus.Finished, AppStatus.Error):
            log.info("TransferError: %r, session = %r", self, self.P2PSession)
            self.status = AppStatus.Error
            if self.P2PSession is not None:
                self.P2PSession.KillTimeoutTimer()
                self.P2PSession.Close()
                self.P2PSession = None
            self.TransferError(self)

    def P2PSessionClosing(self, session, contact):
        if self.status in (AppStatus.Waiting, AppStatus.Active):
            self.OnTransferAborted(contact)

    def P2PSessionClosed(self, session, contact):
        if self.status in (AppStatus.Waiting, AppStatus.Active):
            self.OnTransferAborted(contact)

    def P2PSessionError(self, session):
        if self.status != AppStatus.Error:
            self.OnTransferError()

    # Class methods
    _known_apps = {}

    @classmethod
    def IsRegistered(cls, euf, appid):
        if euf.int != 0 and euf in cls._known_apps:
            if appid != 0:
                for app in cls._known_apps[euf]:
                    if appid == app.AppId:
                        return True
            return True
        return False

    @classmethod
    def CreateInstance(cls, euf, appid, session):
        if session is not None and euf.int != 0 and euf in cls._known_apps:
            if appid != 0:
                for app in cls._known_apps[euf]:
                    if appid == app.AppId:
                        return app.Type(session)

            return cls._known_apps[euf][0].Type(session)

        return None

    @classmethod
    def RegisterApplication(cls, Type):
        if Type is None:
            raise Exception("no app type provided")

        if not issubclass(Type, P2PApplication):
            raise Exception("Must be subclass of P2PApplication")

        added = False

        if Type.EufGuid not in cls._known_apps:
            cls._known_apps[Type.EufGuid] = []

        app = P2PApp(Type.EufGuid, Type.AppId, Type)

        if app not in cls._known_apps[app.EufGuid]:
            cls._known_apps[app.EufGuid].append(app)
            added = True

        return Type

    @classmethod
    def FindApplicationId(cls, p2papp):
        for app_list in cls._known_apps.values():
            for app in app_list:
                if app.Type is type(p2papp):
                    return app.AppId

        return 0

    @classmethod
    def FindApplicationEufGuid(cls, p2papp):
        for app_list in cls._known_apps.values():
            for app in app_list:
                if app.Type is type(p2papp):
                    return app.EufGuid

        return uuid.UUID(int = 0)
