import logging
log = logging.getLogger("msn.soap.services")
import time, datetime
import urlparse
import uuid
import util
import util.net as net
import util.callbacks as callbacks
import util.network.soap as soap

import MSNSecurityTokenService.SecurityTokenService_client as STS_Client
import MSNSecurityTokenService.SecurityTokenService_types as STS_Types

import msn.SOAP.xml.wsa as wsa
#import msn.SOAP.xml.soapwsa as wsa
import msn.SOAP.xml.wst as wst
import msn.SOAP.xml.wsse as wsse
import msn.SOAP.xml.wsu_oasis as wsu
import msn.SOAP.xml.soapenv as soapenv

import ZSI.schema as Schema
import ZSI.wstools.Namespaces as NS
import msn.SOAP.Namespaces as MSNS

def strtime_highres(t = None):
    if t is None:
        t = time.time()
    return time.strftime('%Y-%m-%dT%H:%M:%S.0000000' +
                          ('%+03d:%02d' % divmod(-(time.altzone if time.daylight else time.timezone), 60*60)),
                          time.gmtime(t))

def strptime_highres(s):
    tz_delim, direction = ('+', 1) if '+' in s else ('-', -1)
    tstamp, tz_str = s.rsplit(tz_delim, 1)
    if 'T' in tz_str:
        # There is no TZ portion.
        tz_offset = 0
    else:
        tz_struct = time.strptime(tz_str, '%H:%M')
        tz_offset = (60 * 60 * tz_struct.tm_hour) + (60 * tz_struct.tm_min) * direction
        s = tstamp

    if '.' in s:
        s, micro = s.split('.', 1)

    ts = time.strptime(s, '%Y-%m-%dT%H:%M:%S')
    if ts.tm_year < 1971:
        # Out of range for time.mktime.
        return 0

    return time.mktime(ts) + tz_offset

class SsoDomains:
    Clear     = 'messengerclear.live.com'
    STS       = 'http://Passport.NET/tb'
    WhatsUp   = 'sup.live.com'
    Messenger = 'messenger.msn.com'
    Storage   = 'storage.msn.com'
    OfflineIM = 'messengersecure.live.com'
    Contacts  = 'contacts.msn.com'
    Spaces    = 'spaces.live.com'
    Web       = 'messenger.msn.com'
    Profiles  = 'profile.live.com'

class AppIDs:
    STS         = uuid.UUID("7108E71A-9926-4FCB-BCC9-9A9D3F32E423")
    WhatsUp     = uuid.UUID('3B119D87-1D76-4474-91AD-0D7267E86D04')
    #AddressBook = uuid.UUID("09607671-1C32-421F-A6A6-CBFAA51AB5F4")
    AddressBook = uuid.UUID("CFE80F9D-180F-4399-82AB-413F33A1FA11")
    Sharing     = uuid.UUID("AAD9B99B-58E6-4F23-B975-D9EC1F9EC24A")
    Storage     = "Messenger Client 15"
    Spaces      = 'Messenger Client 8.0'
    RSIService  = 'RSIService'
    Profiles    = uuid.UUID('F679201A-DBC9-4011-B81B-3D05F0797EA9')

class PartnerScenario:
    NONE = 'None'
    Initial = 'Initial'
    Timer ='Timer'
    BlockUnblock = 'BlockUnblock'
    GroupSave = 'GroupSave'
    GeneralDialogApply = 'GeneralDialogApply'
    ContactSave = 'ContactSave'
    ContactMsgrAPI = 'ContactMsgrAPI'
    MessengerPendingList = 'MessengerPendingList'
    PrivacyApply = 'PrivacyApply'
    NewCircleDuringPull = 'NewCircleDuringPull'
    CircleInvite = 'CircleInvite'
    CircleIdAlert = 'CircleIdAlert'
    CircleStatus = 'CircleStatus'
    CircleSave = 'CircleSave'
    CircleLeave = 'CircleLeave'
    JoinedCircleDuringPush = 'JoinedCircleDuringPush'
    ABChangeNotifyAlert = 'ABChangeNotifyAlert'
    RoamingSeed = 'RoamingSeed'
    RoamingIdentityChanged = 'RoamingIdentityChanged'
    SyncChangesToServer = 'LivePlatform!SyncChangesToServer(0)'

class MSNServiceBase(object):
    def __init__(self, transport = None, **k):
        self.Transport = transport

class SSOService(MSNServiceBase):
    SSO = True
    SSO_Domain = None
    SSO_PolicyRef = None

    @callbacks.callsback
    def CheckAuth(self, client, callback = None):
        if client.is_ticket_expired(self.SSO_Domain):
            return client.renew_auth(success = lambda new_tickets: callback.success(),
                                     error = callback.error)

        return callback.success()

    def _CheckError(self, client, msg, response, **k):
        if not (hasattr(response, 'typecode') and response.typecode.pname == 'Fault'):
            return

        fault = response
        code = fault.get_element_Code()
        if code is not None:
            value = eval(code.get_element_Value(), {}, {})
            if value == (MSNS.PPCRL.IDS, "BadContextToken"):
                log.error("SSO Token expired. Must authenticate and send request again!")

                client.clearservice_auth(client._username, client._password, )

class ClearService(SSOService):
    SSO_Domain = SsoDomains.Clear

class CacheKeyService(MSNServiceBase):
    CacheKeyName = None

    def __init__(self, **k):
        super(CacheKeyService, self).__init__(**k)
        self.SessionId = None
        self.PreferredHostName = None

    def add_cachekey(self, client, appheader):
        cachekey = client.get_cachekey(self.CacheKeyName)
        if cachekey is not None:
            appheader.CacheKey = cachekey

    def handleHeaders(self, client, headers):
        serviceHeader = headers.get((MSNS.MSWS.ADDRESS, 'ServiceHeader'), None)
        if serviceHeader is None:
            return

        if serviceHeader.CacheKeyChanged:
            client.set_cachekey(self.CacheKeyName, str(serviceHeader.CacheKey))

        self.SessionId = serviceHeader.SessionId or self.SessionId
        self.PreferredHostName = serviceHeader.PreferredHostName or self.PreferredHostName

    def getPort(self, *a, **k):
        client = k.get('client')
        name = k.get('soapName')
        locator = k.get('locator')
        getPort = getattr(locator, 'get%sPort' % name, lambda *a, **k: None)
        default_port = getPort(**k)
        default_port_url = getattr(getattr(default_port, 'binding', None), 'url', None)

        if client.get_cachekey(self.CacheKeyName) is None:
            parsed = urlparse.urlparse(default_port_url)
            cachekeyurl = urlparse.urlunparse(('https', self.CacheKeyDomain) + parsed[2:])

            log.info("Changing endpoint of request from %r to %r for cachekey", default_port_url, cachekeyurl)
            k.pop('url', None)
            return getPort(cachekeyurl, **k)
        else:
            return default_port

class SecurityTokenService(SSOService):
    AppName = 'SecurityTokenService'
    AppId = AppIDs.STS
    Soap = STS_Client
    Locator = STS_Client.SecurityTokenServiceLocator

    SSO_Domain = SsoDomains.STS

    @callbacks.callsback
    def CheckAuth(self, client, callback = None):
        callback.success()

    def serviceurl_for_user(self, username):
        if username.endswith('msn.com'):
            return 'https://msnia.login.live.com/RST2.srf'

        # returning None will allow the service to use its default URL as defined in the WSDL,
        # "https://login.live.com/RST2.srf"

    def getCredProperty(self, key):
        return getattr(self, 'credProperties', {}).get(key, None)

    def handleHeaders(self, client, headers):
        self.credProperties = credprops = getattr(self, 'credProperties', {})

        pp = headers.get((MSNS.PPCRL.FAULT, 'pp'), None)
        if pp is not None:
            log.info("SecurityTokenService got pp header: %r", pp)
            for cp in pp.CredProperties.CredProperty:
                name = cp.get_attribute_Name()
                log.info("\tcredProperty: %s = %r", name, str(cp))
                credprops[name] = str(cp)

        # TODO: extProperties ? anything useful in there?

    def serviceHeaders(self,
                       client,
                       actionValue = 'http://schemas.xmlsoap.org/ws/2005/02/trust/RST/Issue',
                       toValue = "HTTPS://login.live.com:443//RST2.srf",
                       *a, **k):
        ai = STS_Types.ps.AuthInfo_Dec().pyclass()
        ai.set_attribute_Id("PPAuthInfo")
        ai.HostingApp = "{" + str(self.AppId).upper() + "}"
        ai.BinaryVersion = 5
        ai.Cookies = ''
        ai.UIVersion = 1
        # ai.RequestParams   = "AQAAAAIAAABsYwQAAAAyMDUy"
        ai.RequestParams = 'AQAAAAIAAABsYwQAAAAxMDMz' # Observed from msnc14

        sec = wsse.Security()
        sec.UsernameToken = sec.new_UsernameToken()
        sec.UsernameToken.set_attribute_Id('user')
        sec.UsernameToken.Username = sec.UsernameToken.new_Username(client.get_username())
        password = client.get_password() # set it to a local so it can be discovered and removed by the traceback printer if anything happens.
        sec.UsernameToken.Password = sec.UsernameToken.new_Password(password)

        now = datetime.datetime.utcnow().replace(microsecond = 0)

        ts = sec.Timestamp = sec.new_Timestamp()
        ts.set_attribute_Id("Timestamp")
        ts.Created = ts.new_Created(now.isoformat() + 'Z')
        ts.Expires = ts.new_Expires((now + datetime.timedelta(minutes=60)).isoformat() + 'Z')

        messageid = wsa.MessageID(str(int(time.time())))

        mustunderstand_attrs = {
            (soapenv.wssoapenv.targetNamespace, 'mustUnderstand') : '1',
        }

        class Action:
            typecode = wsa.wsa.Action_Dec(mixed = True)
            _attrs = mustunderstand_attrs
            _text = actionValue

        class To:
            typecode = wsa.wsa.To_Dec(mixed = True)
            _attrs = mustunderstand_attrs
            _text = toValue

        return Action, To, messageid, ai, sec

    def rst_for_service(self, msg, client, service, id):
        domain = service.SSO_Domain
        policyref = service.SSO_PolicyRef

        rtok = msg.new_RequestSecurityToken()
        rtok.set_attribute_Id(id)
        rtok.RequestType = NS.WSTRUST.ISSUE

        # wsp:AppliesTo
        at = rtok.AppliesTo = rtok.new_AppliesTo()
        at.EndpointReference = at.new_EndpointReference()
        at.EndpointReference.Address = at.EndpointReference.new_Address(domain)


        if policyref is not None:
            rtok.PolicyReference = rtok.new_PolicyReference()
            rtok.PolicyReference.set_attribute_URI(policyref)

        return rtok

    @soap.soapcall(STS_Client)
    def RequestSecurityToken(self,
                             msg,
                             client,
                             actionValue = "",
                             toValue = "HTTPS://login.live.com:443//RST2.srf",
                             service = None,
                             *a, **k):
        if service is None:
            service = self

        msg.RequestSecurityToken = rst_for_service(msg, client, service, "RST1")

    @soap.soapcall(STS_Client)
    def RequestMultipleSecurityTokens(self,
                                      msg,
                                      client,
                                      actionValue = 'http://schemas.xmlsoap.org/ws/2005/02/trust/RST/Issue',
                                      toValue = "HTTPS://login.live.com:443//RST2.srf",
                                      services = None,
                                      *a, **k):
        msg.set_attribute_Id('RSTS')
        tokens = []

        for i, service in enumerate(services or client.getSsoServices()):

            #SecurityToken = http://Passport.NET/tb, ""
            #Web = messenger.msn.com, ?id=507
            #Storage = storage.msn.com, MBI
            #Clear = messengerclear.live.com, ?? ## make it a prop of the service that can change at runtime. comes from the ticket token
            #OIM = messengersecure.live.com, MBI_SSL
            #Contact = contacts.msn.com, MBI
            #WhatsUp = sup.live.com, MBI

            rtok = self.rst_for_service(msg, client, service, id = "RST" + str(i))
            tokens.append(rtok)

        msg.RequestSecurityToken = tokens


import MSNABSharingService as MSNABSS
import MSNABSharingService.SharingService_client as Sharing_Client
import MSNABSharingService.SharingService_types as Sharing_Types

# msnab_sharingservice.wsdl
# SharingService_client.py

class WhatsUpService(SSOService):
    AppName = "WhatsUpService"
    AppId = AppIDs.WhatsUp
    Soap = Sharing_Client
    Locator = Sharing_Client.WhatsUpServiceLocator

    SSO_Domain = SsoDomains.WhatsUp
    SSO_PolicyRef = 'MBI'

    def serviceHeaders(self, client, *a, **k):
        '''
        <soap:Header>
            <WNApplicationHeader>
                <ApplicationId>
                    3B119D87-1D76-4474-91AD-0D7267E86D04
                </ApplicationId>
            </WNApplicationHeader>
            <WNAuthHeader>
                <TicketToken>
                    t=EwCYAebpAwAUXYHvLVryvkoZZmChP4TpdQV2xi2AAHGTaHqADpfC+4DlHVPURA4KhB0LQXd9qlo80h3pZpjUSZALqMApTC4rrYvvG+14K1LrBSsa5pR5Cp07GxynXRqObdNNa7czt/VV17I4wQ5M74QTy0hpNpZbRIRfIi/Sa39qtq3wf6YSXjLqRiTWy770gTTgkRJnhBPJsu8/91ZVA2YAAAjRQDTT6OxfH+gApUj0LRT6c2jsxqxJHb7Ufcv5s9QoWooL/6NhGUtlXUW7onuhrP+kkfHmFYVRrDS9ObRio8i3hxOB67PusWCY4+eSOWmcX3t1E1zXPfjIjWjrdJQutYsYaSqAv2++3iEeYfazgW4pGV3MyI9x7025zHjW9FjuSi/jHOt+Be+fueSQ8CaPTpp1dJ8aBS9/uVHL6I/HxQ1sBwkG/b/tGRD2ZyAt3MZHTCXtEIQDnLeadR72HDOGGtL8YI/oxhme3eETgUKsNaJaFN7tXrxDzUtJiXzbQfFxYUWS5o8/K8rrxs+sf+vsgWupug8B&amp;p=
                </TicketToken>
            </WNAuthHeader>
        </soap:Header>
        '''
        app = Sharing_Types.WNApplicationHeader()
        app.ApplicationId = app.new_ApplicationId(str(self.AppId).upper())

        auth = Sharing_Types.WNAuthHeader()
        auth.TicketToken = client.get_ticket(self.SSO_Domain).token

        return (app, auth)

    @soap.soapcall(Sharing_Client)
    def GetContactsRecentActivity(self, msg, client, cid, count = 10, locales = ["en-US"]):
        '''
        <GetContactsRecentActivity>
            <entityHandle>
                <Cid>-3649768326646796772</Cid>
            </entityHandle>
            <locales>
                <string>en-US</string>
            </locales>
            <count>50</count>
        </GetContactsRecentActivity>
        '''
        msg.EntityHandle = msg.new_entityHandle()
        msg.EntityHandle.Cid = cid

        msg.Locales = msg.new_locales()
        msg.Locales.String.extend(locales)

        msg.Count = count

        return True


class SharingServiceBase(CacheKeyService):
    CacheKeyName = 'omega'
    CacheKeyDomain = 'byrdr.omega.contacts.msn.com'

    def handleHeaders(self, client, headers):
        super(SharingServiceBase, self).handleHeaders(client = client, headers = headers)
        self._recv_headers = headers

    def serviceHeaders(self, client, *a, **k):
        ticket = client.get_ticket(SsoDomains.Contacts)

        app = Schema.GED(MSNS.MSWS.ADDRESS,"ABApplicationHeader").pyclass()

        # tried using self.AppId for this but it failed for addressbook requests.
        app.ApplicationId = app.new_ApplicationId(str(AppIDs.Sharing).upper())
        app.IsMigration = False
        app.PartnerScenario = getattr(PartnerScenario, k.get('PartnerScenario', 'Initial'), 'Initial')
        app.BrandId = getattr(ticket, "BrandId", 'MSFT')

        self.add_cachekey(client, app)

        auth = Schema.GED(MSNS.MSWS.ADDRESS,"ABAuthHeader").pyclass()
        auth.TicketToken = ticket.token
        auth.ManagedGroupRequest = False

        return app, auth

class SharingService(SharingServiceBase, SSOService):
    AppName = "SharingService"
    AppId = AppIDs.Sharing
    Soap = Sharing_Client
    Locator = Sharing_Client.SharingServiceLocator

    SSO_Domain = SsoDomains.Contacts
    SSO_PolicyRef = 'MBI'

    @soap.soapcall()
    def FindMembership(self, msg, client, view = 'Full', deltasOnly = False, lastChange = 0, **k):
        msg.View = view
        msg.DeltasOnly = deltasOnly
#        msg.LastChange = strtime_highres(lastChange)
        log.info("SharingService.FindMembership using lastChange = %r", lastChange)
        msg.LastChange = lastChange

        msg.ServiceFilter = msg.new_serviceFilter()
        msg.ServiceFilter.Types = msg.ServiceFilter.new_Types()
        msg.ServiceFilter.Types.ServiceType.append("Messenger")
        #msg.ServiceFilter.Types.ServiceType.extend(["Messenger", 'SocialNetwork', 'Space', 'Profile'])

    @soap.soapcall()
    def AddMember(self, msg, client, contact, role, **k):
        import msn.AddressBook as MSNAB

        messengerService = client.address_book.SelectTargetService(MSNAB.ServiceFilters.Messenger)

        msg.ServiceHandle = msg.new_serviceHandle()
        msg.ServiceHandle.Id = messengerService.id
        msg.ServiceHandle.Type = messengerService.type

        msg.Memberships = msg.new_memberships()
        mship = msg.Memberships.new_Membership()
        msg.Memberships.Membership.append(mship)

        mship.MemberRole = role.role
        ctype = contact.type
        if isinstance(contact.type, int):
            ctype = MSNAB.ClientType(ctype)

        if ctype == MSNAB.ClientType.PassportMember:
            member = MSNABSS.PassportMember()
            member.PassportName = contact.Mail
            member.State = MSNAB.RelationshipStates.Accepted
            member.Type = MSNAB.MembershipType.Passport
        elif ctype == MSNAB.ClientType.EmailMember:
            member = MSNABSS.EmailMember()
            member.State = MSNAB.RelationshipStates.Accepted
            member.Type = MSNAB.MembershipType.Email
            member.Email = contact.Mail
            member.Annotations = member.new_Annotations()
            anno = member.Annotations.new_Annotation()
            member.Annotations.Annotation.append(anno)
            anno.Name = MSNAB.AnnotationNames.MSN_IM_BuddyType
            anno.Value = '%d:' % int(ctype)
        elif ctype == MSNAB.ClientType.PhoneMember:
            member = MSNABSS.PhoneMember()
            member.State = MSNAB.RelationshipStates.Accepted
            member.Type = MSNAB.MembershipType.Phone
            member.PhoneNumber = contact.Mail
        elif ctype == MSNAB.ClientType.CircleMember:
            member = MSNABSS.CircleMember()
            member.Type = MSNAB.MembershipType.Circle
            member.State = MSNAB.RelationshipStates.Accepted
            member.CircleId = str(contact.AddressBookId)

        mship.Members = mship.new_Members()
        mship.Members.Member.append(member)

        return member

    @soap.soapcall()
    def DeleteMember(self, msg, client, contact_type, contact_mail, role = None, callback = None, **k):
        import msn.AddressBook as MSNAB
        messengerService = client.address_book.SelectTargetService(MSNAB.ServiceFilters.Messenger)
        msg.ServiceHandle = msg.new_serviceHandle()
        msg.ServiceHandle.Id = 0 #messengerService.id
        msg.ServiceHandle.Type = messengerService.type
        msg.ServiceHandle.ForeignId = messengerService.foreign_id + ' '

        msg.Memberships = msg.new_memberships()
        mship = msg.Memberships.new_Membership()
        role = MSNAB.MSNList(role)
        mship.MemberRole = role.role

        mship.Members = mship.new_Members()

        baseMember = client.address_book.SelectBaseMember(MSNAB.ServiceFilters.Messenger, contact_mail, contact_type, role.role)
        mship_id = 0
        if baseMember is not None and baseMember.MembershipId:
            try:
                mship_id = int(baseMember.MembershipId)
            except ValueError:
                pass

        deleteMember = None
        str_type = MSNAB.ClientType(contact_type)
        if str_type == MSNAB.ClientType.PassportMember:
            deleteMember = MSNABSS.PassportMember()
            deleteMember.Type = getattr(baseMember, 'Type', MSNAB.MembershipType.Passport)
            deleteMember.State = getattr(baseMember, 'State', MSNAB.RelationshipStates.Accepted)

            if mship_id == 0:
                deleteMember.PassportName = contact_mail

        elif str_type == MSNAB.ClientType.EmailMember:
            deleteMember = MSNABSS.EmailMember()
            deleteMember.Type = getattr(baseMember, 'Type', MSNAB.MembershipType.Email)
            deleteMember.State = getattr(baseMember, 'State', MSNAB.RelationshipStates.Accepted)

            if mship_id == 0:
                deleteMember.Email = contact_mail

        elif str_type == MSNAB.ClientType.PhoneMember:
            deleteMember = MSNABSS.PhoneMember()
            deleteMember.Type = getattr(baseMember, 'Type', MSNAB.MembershipType.Phone)
            deleteMember.State = getattr(baseMember, 'State', MSNAB.RelationshipStates.Accepted)

            if mship_id == 0:
                deleteMember.PhoneMember = contact_mail

        deleteMember.MembershipId = mship_id
        mship.Members.Member.append(deleteMember)
        msg.Memberships.Membership.append(mship)

    @soap.soapcall()
    def CreateCircle(self, msg, client, displayName = None, **k):
        assert displayName is not None
        import msn.AddressBook as MSNAB
        msg.Properties = msg.new_properties()
        msg.Properties.Domain = MSNAB.DomainIds.WLDomain        # 1
        msg.Properties.HostedDomain = MSNAB.Circle.hostDomain   # live.com
        msg.Properties.IsPresenceEnabled = True
        msg.Properties.DisplayName = displayName

        # The meaning of these values is unknown. Copied from captured WLM client operation
        msg.Properties.Type = 2
        msg.Properties.MembershipAccess = 0
        msg.Properties.RequestMembershipOption = 2

        msg.CallerInfo = msg.new_callerInfo()
        msg.CallerInfo.PublicDisplayName = client.contact_list.owner.contactInfo.displayName

class ABService(SharingServiceBase, SSOService):
    AppName = "ABService"
    AppId = AppIDs.AddressBook
    Soap = Sharing_Client
    Locator = Sharing_Client.ABServiceLocator

    abId = uuid.UUID(int=0)

    SSO_Domain = SsoDomains.Contacts
    SSO_PolicyRef = 'MBI'

    @soap.soapcall()
    def ABFindAll(self, msg, client, view = 'Full', deltas = False, lastChange = 0, **k):
        msg.set_element_abId(msg.new_abId(str(self.abId)))
        msg.AbView = view
        msg.DeltasOnly = deltas
        log.info("ABService.ABFindALl using lastChange = %r", lastChange)
        msg.LastChange = lastChange

    @soap.soapcall()
    def ABFindContactsPaged(self, msg, client, abid = None, view = 'Full', deltas = False, lastChange = 0, **k):
        msg.set_element_abView("MessengerClient8")

        if abid is None:
            abid = str(uuid.UUID(int=0))

        abid = str(abid).lower()

        if abid == str(self.abId):
            msg.set_element_extendedContent("AB AllGroups CircleResult")
            fo = msg.new_filterOptions()
            msg.set_element_filterOptions(fo)
            fo.set_element_ContactFilter(fo.new_ContactFilter())

            fo.DeltasOnly = deltas
            fo.LastChanged = lastChange
            fo.ContactFilter.IncludeHiddenContacts = True
            fo.ContactFilter.IncludeShellContacts = True

        else:
            msg.set_element_extendedContent("AB")
            handle = msg.new_abHandle()
            handle.ABId = abid
            handle.Cid = 0
            handle.Puid = 0

            msg.AbHandle = handle

        log.info("requesting AddressBook %r", abid)
        log.info("ABService.ABFindContactsPaged(%r) using lastChange = %r", abid, lastChange)

    @soap.soapcall()
    def ABContactAdd(self, msg, client, account, pending = False, invitation = None, network = None, otheremail = None, **k):
        import msn.AddressBook as MSNAB

        msg.AbId = self.abId
        msg.Contacts = msg.new_contacts()
        c = msg.Contacts.new_Contact()
        msg.Contacts.Contact.append(c)

        ci = c.ContactInfo = c.new_contactInfo()

        if isinstance(network, int):
            network = MSNAB.ClientType(network)

        if network == MSNAB.ClientType.PassportMember:
            ci.ContactType = MSNAB.MessengerContactType.Regular
            ci.PassportName = account
            ci.IsMessengerUser = True
            ci.IsMessengerUserSpecified = True
            mmi = ci.MessengerMemberInfo = ci.new_MessengerMemberInfo()

            if not pending and invitation:
                mmi.PendingAnnotations = mmi.new_PendingAnnotations()
                anno = mmi.PendingAnnotations.new_Annotation()
                mmi.PendingAnnotations.Annotation.append(anno)

                anno.Name = MSNAB.AnnotationNames.MSN_IM_InviteMessage
                anno.Value = invitation

            mmi.DisplayName = client.contact_list.owner.account
            msg.Options = msg.new_options()
            msg.Options.EnableAllowListManagement = True

        elif network == MSNAB.ClientType.EmailMember:
            emails = ci.Emails = ci.new_emails()

            if otheremail:
                email = emails.new_ContactEmail()
                emails.ContactEmail.append(email)
                email.ContactEmailType = MSNAB.ContactEmailType.ContactEmailOther
                email.Email = otheremail
                email.PropertiesChanged = MSNAB.PropertyString.Email
                email.IsMessengerEnabled = True
                email.MessengerEnabledExternally = False

            email = emails.new_ContactEmail()
            emails.ContactEmail.append(email)
            email.ContactEmailType = MSNAB.ContactEmail.Types.Messenger2
            email.Email = account
            email.IsMessengerEnabled = True
            email.Capability = int(network)
            email.MessengerEnabledExternally = False
            email.PropertiesChanged = MSNAB.PropertyString.PropertySeparator.join([
                                          MSNAB.PropertyString.Email,
                                          MSNAB.PropertyString.IsMessengerEnabled,
                                          MSNAB.PropertyString.Capability,
                                      ])

        elif network == MSNAB.ClientType.PhoneMember:
            ci.Phones = ci.new_phones()
            phone = ci.Phones.new_Phone()
            ci.Phones.Phone.append(phone)

            phone.ContactPhoneType1 = MSNAB.ContactPhoneType.ContactPhoneMobile
            phone.Number = account
            phone.IsMessengerEnabled = True
            phone.PropertiesChanged = ' '.join([MSNAB.PropertyString.Number,
                                                MSNAB.PropertyString.IsMessengerEnabled])

    @soap.soapcall()
    def ABContactDelete(self, msg, client, abid = None, contacts = None, **k):
        if abid is None:
            abid = self.abId

        msg.set_element_abId(str(abid).lower())

        if contacts is None:
            contact_ids = []
        else:
            contact_ids = [str(c.contactId).lower() for c in contacts]

        msg.Contacts = msg.new_contacts()
        for cid in contact_ids:
            c = msg.Contacts.new_Contact()
            c.set_element_contactId(c.new_contactId(cid))
            msg.Contacts.Contact.append(c)

    @soap.soapcall()
    def ABGroupAdd(self, msg, client, name, **k):
        import msn.AddressBook as MSNAB

        msg.AbId = self.abId
        opts = msg.GroupAddOptions = msg.new_groupAddOptions()
        opts.FRenameOnMsgrConflict = False
        opts.FRenameOnMsgrConflictSpecified = True

        msg.GroupInfo = msg.new_groupInfo()
        gi = msg.GroupInfo.GroupInfo = msg.GroupInfo.new_GroupInfo()
        gi.Name = name
        gi.FMessenger = False
        gi.FMessengerSpecified = True
        gi.GroupType = MSNAB.GroupInfo.groupType
        gi.Annotations = gi.new_annotations()
        anno = gi.Annotations.new_Annotation()
        gi.Annotations.Annotation.append(anno)
        anno.Name = MSNAB.AnnotationNames.MSN_IM_Display
        anno.Value = '1'

    @soap.soapcall()
    def ABGroupUpdate(self, msg, client, group_id, name, **k):
        msg.AbId = self.abId
        msg.Groups = msg.new_groups()
        g = msg.Groups.new_Group()
        msg.Groups.Group.append(g)

        g.GroupId = group_id
        g.PropertiesChanged = "GroupName"
        g.GroupInfo = g.new_groupInfo()
        g.GroupInfo.Name = name

    @soap.soapcall()
    def ABGroupDelete(self, msg, client, group_id, **k):
        msg.AbId = self.abId
        msg.GroupFilter = msg.new_groupFilter()
        msg.GroupFilter.GroupIds = msg.GroupFilter.new_groupIds()
        msg.GroupFilter.GroupIds.Guid.append(group_id)

    @soap.soapcall()
    def ABGroupContactAdd(self, msg, client, contact, group_id, **k):
        msg.AbId = self.abId
        msg.GroupFilter = msg.new_groupFilter()
        msg.GroupFilter.GroupIds = msg.GroupFilter.new_groupIds()
        msg.GroupFilter.GroupIds.Guid.append(group_id)

        msg.Contacts = msg.new_contacts()
        msg.Contacts.Contact.append(msg.Contacts.new_Contact())
        msg.Contacts.Contact[-1].ContactId = contact.contactId

    @soap.soapcall()
    def ABGroupContactDelete(self, msg, client, abid = None, contact = None, group_id = None, **k):
        msg.AbId = str(abid or self.abId).lower()
        msg.GroupFilter = msg.new_groupFilter()
        msg.GroupFilter.GroupIds = msg.GroupFilter.new_groupIds()
        msg.GroupFilter.GroupIds.Guid.append(group_id)
        msg.Contacts = msg.new_contacts()

        c = msg.Contacts.new_Contact()
        c.set_element_contactId(c.new_contactId(contact.contactId))
        msg.Contacts.Contact.append(c)

    @soap.soapcall()
    def ABContactUpdate(self, msg, client, old_contact, new_contact, **kw):
        import msn.AddressBook as MSNAB
        msg.AbId = self.abId
        msg.Contacts = msg.new_contacts()
        c = msg.Contacts.new_Contact()
        msg.Contacts.Contact.append(c)

        ci = c.ContactInfo = c.new_contactInfo()

        propertiesChanged = []

        ## Simple Properties
        if old_contact.contactInfo.comment != new_contact.contactInfo.comment:
            propertiesChanged.append(MSNAB.PropertyString.Comment)
            ci.Comment = new_contact.contactInfo.comment

        if old_contact.contactInfo.displayName != new_contact.contactInfo.displayName:
            propertiesChanged.append(MSNAB.PropertyString.DisplayName)
            ci.DisplayName = new_contact.contactInfo.displayName

        if old_contact.contactInfo.hasSpace != new_contact.contactInfo.hasSpace:
            propertiesChanged.append(MSNAB.PropertyString.HasSpace)
            ci.HasSpace = new_contact.contactInfo.hasSpace

        ## Annotations
        annotationsChanged = ci.new_annotations()
        oldAnnotations = {}
        for anno in getattr(old_contact.contactInfo, 'annotations', None) or []:
            oldAnnotations[anno.Name] = anno.Value

        oldNickName = oldAnnotations.get(MSNAB.AnnotationNames.AB_NickName, None)
        if new_contact.DisplayName != oldNickName:
            anno = annotationsChanged.new_Annotation()
            annotationsChanged.Annotation.append(anno)
            anno.Name = MSNAB.AnnotationNames.AB_NickName
            anno.Value = new_contact.DisplayName

        if len(annotationsChanged):
            propertiesChanged.Add(MSNAB.PropertyString.Annotation)
            ci.Annotations = annotationsChanged

        ## Client Type Changes

        ct = MSNAB.ClientType(old_contact.type)
        if ct == MSNAB.ClientType.PassportMember:
            if old_contact.contactInfo.isMessengerUser != new_contact.contactInfo.isMessengerUser:
                propertiesChanged.append(MSNAB.PropertyString.IsMessengerUser)
                ci.IsMessengerUser = new_contact.contactInfo.isMessengerUser
                ci.IsMessengerUserSpecified = True
                propertiesChanged.append(MSNAB.PropertyString.MessengerMemberInfo)
                mmi = ci.MessengerMemberInfo = ci.new_MessengerMemberInfo()
                mmi.DisplayName = client.contact_list.owner.account

            if old_contact.contactInfo.contactType != new_contact.contactInfo.contactType:
                propertiesChanged.append(MSNAB.PropertyString.ContactType)
                ci.ContactType = new_contact.contactInfo.contactType

        elif ct == MSNAB.ClientType.EmailMember:
            for em in getattr(old_contact.contactInfo, 'emails', None) or []:
                if em.email.lower() == new_contact.Mail.lower() and em.isMessengerEnabled and not new_contact.contactInfo.isMessengerUser:
                    propertiesChanged.append(MSNAB.PropertyString.ContactEmail)
                    ci.Emails = ci.new_emails()
                    email = ci.Emails.new_email()
                    ci.Emails.Email.append(email)
                    email.ContactEmalType1 = MSNAB.ContactEmailType.Messenger2
                    email.IsMessengerEnabled = new_contact.contactInfo.isMessengerUser
                    email.PropertiesChanged = MSNAB.PropertyString.IsMessengerEnabled
                    break

        elif ct == MSNAB.ClientType.PhoneMember:
            for ph in getattr(old_contact.contactInfo, 'phones', None) or []:
                if ph.number == contact.Mail and ph.isMessengerEnabled != new_contact.contactInfo.isMessengerUser:
                    propertiesChanged.append(MSNAB.PropertiesChanged.ContactPhone)
                    ci.Phones = ci.new_phones()
                    phone = ci.Phones.new_phone()
                    ci.Phones.Phone.append(phone)
                    phone.ContactPhoneType1 = MSNAB.ContactPhoneType.ContactPhoneMobile
                    phone.IsMessengerEnabled = new_contact.contactInfo.isMessengerUser
                    phone.PropertiesChanged = MSNAB.PropertyString.IsMessengerEnabled
                    break

        if len(propertiesChanged) == 0:
            return False

        c.PropertiesChanged = ' '.join(propertiesChanged)

    @soap.soapcall()
    def ABAdd(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def UpdateDynamicItem(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def CreateContact(self, msg, client, abid = abId, circleId = abId, email = None, **k):
        msg.AbHandle = msg.new_abHandle()
        msg.AbHandle.ABId = abid
        msg.AbHandle.Puid = 0
        msg.AbHandle.Cid = 0

        msg.ContactHandle = msg.new_contactHandle()
        msg.ContactHandle.Email = email
        msg.ContactHandle.Puid = 0
        msg.ContactHandle.Cid = 0
        msg.ContactHandle.CircleId = circleId

    @soap.soapcall()
    def ManageWLConnection(self, msg, client,
                           contactId,
                           connection,
                           presence,
                           action,
                           relationshipRole,
                           relationshipType,
                           Annotations = None,
                           abid = None,
                           **k):

        if Annotations is None:
            Annotations = []

        for name, value in Annotations:
            if getattr(msg, 'Annotations', None) is None:
                msg.Annotations = msg.new_annotations()

            anno = msg.Annotations.new_Annotation()
            anno.Name = name
            anno.Value = value
            msg.Annotations.Annotation.append(anno)

        msg.ContactId = contactId
        msg.Connection = connection
        msg.Presence = presence
        msg.Action = action
        msg.RelationshipRole = relationshipRole
        msg.RelationshipType = relationshipType

        if abid is not None:
            msg.AbHandle = msg.new_abHandle()
            msg.AbHandle.ABId = str(abid).lower()
            msg.AbHandle.Puid = 0
            msg.AbHandle.Cid = 0

    @soap.soapcall()
    def BreakConnection(self, msg, client, abid = None, contactId = None, block = False, delete = True, **k):
        if abid is not None:
            msg.AbHandle = msg.new_abHandle()
            msg.AbHandle.ABId = str(abid).lower()
            msg.AbHandle.Puid = 0
            msg.AbHandle.Cid = 0

        msg.ContactId = contactId
        msg.BlockContact = block
        msg.DeleteContact = delete

    @soap.soapcall()
    def AddDynamicItem(self, msg, client, **k):
        raise NotImplementedError

import MSNStorageService as MSNSS
import MSNStorageService.StorageService_client as Storage_Client
import MSNStorageService.StorageService_types as Storage_Types

class StorageService(CacheKeyService, SSOService):
    CacheKeyName = 'storage'
    CacheKeyDomain = 'tkrdr.storage.msn.com'

    SSO_PolicyRef = 'MBI'
    SSO_Domain = SsoDomains.Storage

    AppName = 'StorageService'
    AppId = AppIDs.Storage
    Soap = Storage_Client
    Locator = Storage_Client.StorageServiceLocator

    def serviceHeaders(self, client, scenario = "Initial", **k):
        App = Schema.GED(MSNS.MSWS.STORAGE,"StorageApplicationHeader").pyclass()
        User = Schema.GED(MSNS.MSWS.STORAGE,"StorageUserHeader").pyclass()
        Affinity = Schema.GED(MSNS.MSWS.STORAGE,"AffinityCacheHeader").pyclass()

        App.ApplicationID = self.AppId
        App.Scenario = scenario

        User.Puid = 0
        User.TicketToken = client.get_ticket(self.SSO_Domain).token

        self.add_cachekey(client, Affinity)

        return App, User, Affinity

    @soap.soapcall()
    def FindDocuments(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def CreateProfile(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def GetProfile(self, msg, client, scenario, **k):
        ph = msg.ProfileHandle = msg.new_profileHandle()
        alias = ph.Alias = ph.new_Alias()
        alias.NameSpace = "MyCidStuff"
        alias.Name = str(client.contact_list.owner.CID)
        ph.RelationshipName = 'MyProfile'

        pa = msg.ProfileAttributes = msg.new_profileAttributes()
        pa.ResourceID = True
        pa.DateModified = True
        expattr = pa.ExpressionProfileAttributes = pa.new_ExpressionProfileAttributes()

        for attr in ('DateModified',
                     'DateModifiedSpecified',
                     'DisplayName',
                     'DisplayNameLastModified',
                     'DisplayNameLastModifiedSpecified',
                     'DisplayNameSpecified',
                     'Flag',
                     'FlagSpecified',
                     'PersonalStatus',
                     'PersonalStatusLastModified',
                     'PersonalStatusLastModifiedSpecified',
                     'PersonalStatusSpecified',
                     'Photo',
                     'PhotoSpecified',
                     'Attachments',
                     'AttachmentsSpecified',
                     'ResourceID',
                     'ResourceIDSpecified',
                     'StaticUserTilePublicURL',
                     'StaticUserTilePublicURLSpecified',):
            setattr(expattr, attr, True)


    @soap.soapcall()
    def CreateRelationships(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def UpdateProfile(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def ShareItem(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def UpdateDocument(self, msg, client, resource_id = None, name = None, docstream = None, **k):
        msg.Document = msg.new_document()
        msg.Document.ResourceID = resource_id
        msg.Document.Name = name
        docs = msg.Document.DocumentStreams = msg.Document.new_DocumentStreams()

        doctype_name = docstream.get('xsitype')
        doctype = getattr(MSNSS, doctype_name, MSNSS.DocumentStream)

        doc = doctype()
        docs.DocumentStream.append(doc)

        doc.DocumentStreamType = docstream.get('type')
        doc.MimeType = docstream.get('mimetype')
        doc.Data = docstream.get('data')
        doc.DataSize = docstream.get('datasize', 0)

    @soap.soapcall()
    def CreateDocument(self, msg, client, **k):
        raise NotImplementedError

    @soap.soapcall()
    def DeleteRelationships(self, msg, client, **k):
        raise NotImplementedError

import MSNSpaceService.SpaceService_client as Spaces_Client
import MSNSpaceService.SpaceService_types as Spaces_Types

class SpacesService(SSOService):
#    CacheKeyDomain = 'spaces.live.com'
    AppName = "SpaceService"

    SSO_PolicyRef = 'MBI'
    SSO_Domain = SsoDomains.Spaces

    AppId = AppIDs.Spaces
    Soap = Spaces_Client
    Locator = Spaces_Client.SpaceServiceLocator

    def serviceHeaders(self, client, *a, **k):
        ticket = client.get_ticket(SsoDomains.Contacts)

        auth = Schema.GED(MSNS.MSWS.SPACES, 'AuthTokenHeader').pyclass()
        auth.Token = ticket.token
        #auth.AuthPolicy = self.SSO_PolicyRef

        return auth,

    @soap.soapcall()
    def GetXmlFeed(self, msg, client, CID, **k):
        ri = msg.RefreshInformation = msg.new_refreshInformation()
        ri.Cid = CID
        ri.StorageAuthCache = ''
        ri.Market = 'en-US' #'%s-%s' % (hub.language.lower(), hub.country.upper())
        ri.Brand = ''
        ri.MaxElementCount = 15
        ri.MaxCharacterCount = 200
        ri.MaxImageCount = 6
        ri.ApplicationId = 'Messenger Client 8.0'
        ri.UpdateAccessedTime = False

        import datetime
        yesterday = time.mktime((datetime.datetime.today() - datetime.timedelta(1)).timetuple())

        ri.SpaceLastViewed = yesterday
        ri.ProfileLastViewed = yesterday
        ri.ContactProfileLastViewed = yesterday

        ri.IsActiveContact = False

#        fs = ri.ForeignStore = ri.new_foreignStore()
#        fs.ItemType = 'Profile'
#        fs.ForeignId = 'MyProfile'
#        fs.LastChanged = yesterday.isoformat()
#        fs.LastViewed = yesterday.isoformat()


import MSNOIMStoreService.OIMStoreService_client as OIMStore_Client
import MSNOIMStoreService.OIMStoreService_types as OIMStore_Types

class OIMService(SSOService):
    last_message_number = -1

    Soap = OIMStore_Client
    AppName = "OIMService"
    SSO_PolicyRef = ""
    SSO_Domain = SsoDomains.OfflineIM

    def serviceHeaders(self, client, to = None, **k):
        To = Schema.GED(MSNS.HMNS.OIM, "To").pyclass()
        To.set_attribute_memberName(to)

        From = Schema.GED(MSNS.HMNS.OIM, "From").pyclass()
        From.set_attribute_memberName(client.self_buddy.name)
        From.set_attribute_proxy(client.ns.client_name)
        From.set_attribute_msnpVer(client.version)
        From.set_attribute_buildVer(client.ns.client_software_version)

        Ticket = Schema.GED(MSNS.HMNS.OIM, "Ticket").pyclass()
        Sequence = Schema.GED(NS.WSA.RM, "Sequence").pyclass()

        Sequence.Identifier = Sequence.new_Identifier('http://' + SsoDomains.Messenger)
        self.last_message_number = Sequence.MessageNumber = self.last_message_number + 1

        return To, From, Ticket, Sequence

    def handleHeaders(self, client, headers, **k):
        super(OIMService, self).handleHeaders(client = client, headers = headers)
        self._recv_headers = headers

    @soap.soapcall()
    def Store(self, msg, client, text = None, **k):
        pass

import MSNRSIService.RSIService_client as RSIService_client
import MSNRSIService.RSIService_types as RSIService_types

class RSIService(SSOService):
    Soap = RSIService_client
    AppName = 'RSIService'
    AppId = AppIDs.RSIService
    SSO_PolicyRef = '?id=507'
    SSO_Domain = SsoDomains.Web


    def serviceHeaders(self, client, to = None, **k):
        PC = Schema.GED(MSNS.HMNS.RSI, "PassportCookie").pyclass()
        ticket = client.get_ticket(self.SSO_Domain)

        token_parts = util.fmt_to_dict('&', '=')(ticket.token)

        PC.T = token_parts.get('t', '')
        PC.P = token_parts.get('p', '')

        return PC,


    @soap.soapcall()
    def GetMetadata(self, msg, client, **k):
        pass

    @soap.soapcall()
    def GetMessage(self, msg, client, message_id, markread = False, **k):

        msg.MessageId = message_id
        msg.AlsoMarkAsRead = markread

    @soap.soapcall()
    def DeleteMessages(self, msg, client, message_ids, **k):
        pass

class LiveAPIService(SSOService):
    # ? http://login.live.com/controls/WebAuth.htm
    SSO_PolicyRef = 'MBI' # Just a guess
    SSO_Domain = 'api.live.net'

    AppId = '1275182653'

    #def
