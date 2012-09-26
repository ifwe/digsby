import traceback

import uuid
import simplejson as json
import logging

import util
import util.net as net
import util.network.soap as soap
import util.primitives.structures as structures

log = logging.getLogger('msn.ab')

import msn.SOAP.services as SOAPServices
import msn.SOAP.pysoap_util as pysoap

class MemberRole:
    Allow = "Allow"
    Block = "Block"
    Reverse = "Reverse"
    Pending = "Pending"
    Admin = "Admin"
    Contributor = "Contributor"
    ProfileGeneral = "ProfileGeneral"
    ProfilePersonalContact = "ProfilePersonalContact"
    ProfileProfessionalContact = "ProfileProfessionalContact"
    ProfileSocial = "ProfileSocial"
    ProfileExpression = "ProfileExpression"
    ProfileEducation = "ProfileEducation"
    OneWayRelationship = "OneWayRelationship"
    TwoWayRelationship = "TwoWayRelationship"
    ApplicationRead = "ApplicationRead"
    ApplicationWrite = "ApplicationWrite"

class MessengerContactType:
    Me = "Me"
    Regular = "Regular"
    Messenger = "Messenger"
    Live = "Live"
    LivePending = "LivePending"
    LiveRejected = "LiveRejected"
    LiveDropped = "LiveDropped"
    Circle = "Circle"

class PropertyString:
    PropertySeparator = " "
    Email = "Email"
    IsMessengerEnabled = "IsMessengerEnabled"
    Capability = "Capability"
    Number = "Number"
    Comment = "Comment"
    DisplayName = "DisplayName"
    Annotation = "Annotation"
    IsMessengerUser = "IsMessengerUser"
    MessengerMemberInfo = "MessengerMemberInfo"
    ContactType = "ContactType"
    ContactEmail = "ContactEmail"
    ContactPhone = "ContactPhone"
    GroupName = "GroupName"
    HasSpace = "HasSpace"

class AddressBookType:
    Group = "Group"
    Individual = "Individual"

class AnnotationNames:
    MSN_IM_InviteMessage = "MSN.IM.InviteMessage"
    MSN_IM_MPOP = "MSN.IM.MPOP"
    MSN_IM_BLP = "MSN.IM.BLP"
    MSN_IM_GTC = "MSN.IM.GTC"
    MSN_IM_RoamLiveProperties = "MSN.IM.RoamLiveProperties"
    MSN_IM_MBEA = "MSN.IM.MBEA"
    MSN_IM_Display = "MSN.IM.Display"
    MSN_IM_BuddyType = "MSN.IM.BuddyType"
    AB_NickName = "AB.NickName"
    AB_Profession = "AB.Profession"
    Live_Locale = "Live.Locale"
    Live_Profile_Expression_LastChanged = "Live.Profile.Expression.LastChanged"
    Live_Passport_Birthdate = "Live.Passport.Birthdate"

class Role(structures.EnumValue, pysoap.Serializable):
    def __init__(self, str, int, role):
        structures.EnumValue.__init__(self, str, int, role = role)
        pysoap.Serializable.__init__(self)

    def serialize(self):
        return str(int(self))

class MSNList(structures._Enum):
    ValueType = Role

    Forward =   (1,  'FL')
    Allow =     (2,  'AL')
    Block =     (4,  'BL')
    Reverse =   (8,  'RL')
    Pending =   (16, 'PL')
    Hidden =    (64, 'HL')

MSNList = MSNList()

class MembershipType:
    Passport = 'Passport'
    Email = 'Email'
    Phone = 'Phone'
    Role = 'Role'
    Service = 'Service'
    Everyone = 'Everyone'
    Partner = 'Partner'
    Domain = 'Domain'
    Circle = 'Circle'

class DomainIds:
    WLDomain = 1
    ZUNEDomain = 3
    FBDomain = 7
    LinkedIn = 8
    Myspace = 9

class RelationshipTypes:
    IndividualAddressBook = 3
    CircleGroup = 5

class RelationshipStates:
    NONE = 'None'
    WaitingResponse = 'WaitingResponse'
    Left = 'Left'
    Accepted = 'Accepted'
    Rejected = 'Rejected'

    @classmethod
    def from_int(cls, i):
        return {
                0 : cls.NONE,
                1 : cls.WaitingResponse,
                2 : cls.Left,
                3 : cls.Accepted,
                4 : cls.Rejected,
                }.get(i)

class Scenario:
    NONE = 0
    Restore = 1
    Initial = 2
    DeltaRequest = 4
    NewCircles = 8
    ModifiedCircles = 16
    SendInitialContactsADL = 32
    SendInitialCirclesADL = 64
    ContactServeAPI = 128
    InternalCall = 256

class CirclePersonalMembershipRole:
    NONE = 'None'
    Admin = 'Admin'
    AssistantAdmin = 'AssistantAdmin'
    Member = 'Member'
    StatePendingOutbound = "StatePendingOutbound"

    @classmethod
    def from_int(cls, i):
        return {
                0: 'None',
                1: 'Admin',
                2: 'AssistantAdmin',
                3: 'Member',
                4: 'StatePendingOutbound',
                }.get(i)

    @classmethod
    def to_int(cls, s):
        return {
                'None': 0,
                'Admin': 1,
                'AssistantAdmin': 2,
                'Member': 3,
                'StatePendingOutbound': 4,
                }.get(s)

class IMAddressInfoType:
    NONE = 0
    WindowsLive = 1
    OfficeCommunicator = 2
    Telephone = 4
    MobileNetwork = 8
    Circle = 9
    TemporaryGroup = 10
    Cid = 11
    Connect = 13
    RemoteNetwork = 14
    Smtp = 16
    Yahoo = 32

class _ClientType(structures.EnumValue, pysoap.Serializable):
    def __init__(self, name, int, *equivs):
        structures.EnumValue.__init__(self, name, int, **dict(('equiv%d' % i, e) for i,e in enumerate(equivs)))
        pysoap.Serializable.__init__(self)

    def serialize(self):
        return str(int(self))

class ClientType(structures._Enum):
    ValueType = _ClientType
    NONE = 0
    Passport = (1, MessengerContactType.Me,
                   MessengerContactType.Messenger,
                   MessengerContactType.Live,
                   MessengerContactType.LivePending,
                   MessengerContactType.LiveRejected,
                   MessengerContactType.LiveDropped)
    LCS = 2
    Phone = 4
    Circle = 9
    Chat = 10
    Email = (32, MessengerContactType.Regular)

ClientType = ClientType()
ClientType.PassportMember = ClientType.Passport
ClientType.EmailMember    = ClientType.Email
ClientType.PhoneMember    = ClientType.Phone
ClientType.CircleMember   = ClientType.Circle
ClientType.ChatMember     = ClientType.Chat

class ServiceFilters:
    Messenger = "Messenger"
    Invitation = "Invitation"
    SocialNetwork = "SocialNetwork"
    Profile = "Profile"
    Folder = "Folder"
    Event = "Event"
    OfficeLiveWebNotification = "OfficeLiveWebNotification"
    CommunityQuestionAnswer = "CommunityQuestionAnswer"

class Service(pysoap.Serializable):

#    def __init__(self, id, type, lastChange, foreign_id):
#        pysoap.Serializable.__init__(self, id = id, type = type, lastChange = lastChange, foreign_id = foreign_id)

    #lastChange = pysoap.DateAttr('lastChange')
    pass

class Annotation(pysoap.Serializable):
    pass

class MemberLocation(pysoap.Serializable):
    '''Attributes:
        Id
        isPassportNameHidden
        CID
    '''

class GroupInfo(pysoap.Serializable):
    groupType = "C8529CE2-6EAD-434d-881F-341E17DB3FF8"
    name = None

    annotations = [Annotation]
    '''Attributes:
        annotations
        groupType
        name
        IsNotMobileVisible
        IsNotMobileVisibleSpecified
        IsPrivate
        IsPrivateSpecified
        IsFavorite
        IsFavoriteSpecified
        fMessenger
        fMessengerSpecified
    '''

class Group(pysoap.Serializable):
    groupInfo = GroupInfo

class Member(pysoap.Serializable):
    nonserialize_attributes = ['States']
    class States:
        Accepted = 'Accepted'
        Pending = 'Pending'
        Removed = 'Removed'

    location = MemberLocation
    Annotations = [Annotation]

    #joinedDate = pysoap.DateAttr("joinedDate")
    #expirationDate = pysoap.DateAttr("expirationDate")
    #lastChange = pysoap.DateAttr("lastChange")

    '''Attributes:
        membershipId
        type
        location
        displayName
        state
        annotations
        deleted
        lastChange
        joinedDate
        expirationDate
        changes
    '''

    @classmethod
    def deserialize(cls, s):
        self = pysoap.Serializable.deserialize(s)
        if hasattr(self, 'PassportName'):
            newtype = PassportMember
        elif hasattr(self, 'Email'):
            newtype = EmailMember
        elif hasattr(self, 'PhoneNumber'):
            newtype = PhoneMember
        elif hasattr(self, 'CircleId'):
            newtype = CircleMember
        elif hasattr(self, 'DomainName'):
            newtype = DomainMember
        else:
            return self

        return newtype(**vars(self))

    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        cls = {
               MembershipType.Passport : PassportMember,
               MembershipType.Email : EmailMember,
               MembershipType.Phone : PhoneMember,
               MembershipType.Domain : DomainMember,
               MembershipType.Circle : CircleMember,
               }.get(obj.Type, cls)

        attrs = pysoap.extract_zsi_properties(obj)
        attrs.update(kwds)

        attrs['Annotations'] = map(Annotation.from_zsi, getattr(attrs.get('Annotations'), 'Annotation', None) or [])
        attrs['location'] = MemberLocation.from_zsi(attrs.get('location'))

        return cls(**attrs)

    def GetAnnotation(self, key, default = None):
        for anno in self.Annotations:
            if type(anno) is Annotation:
                name, value = anno.Name, anno.Value
            else:
                assert type(anno) is dict
                name, value = anno.get('Name'), anno.get('Value')

            if name == key:
                return value

        return default

class PassportMember(Member):
    '''Attributes:
        PassportName
        IsPassportNameHidden
        IsPassportNameHiddenSpecified
        PassportId
        PassportIdSpecified
        CID
        CIDSpecified
        PassportChanges
    '''

class EmailMember(Member):
    '''Attributes:
        Email
    '''

class PhoneMember(Member):
    '''Attributes:
        PhoneNumber
    '''

class CircleMember(Member):
    '''Attributes:
        CircleId
    '''

class DomainMember(Member):
    '''Attributes:
        DomainName
    '''

class ServiceMembership(pysoap.Serializable):
    Service = Service
    Memberships = {'' : {'' : Member}}

    def __init__(self, Service = None, Memberships = None):
        pysoap.Serializable.__init__(self, Service = Service, Memberships = Memberships)
        if self.Memberships is type(self).Memberships:
            self.Memberships = {}

class ContactEmail(pysoap.Serializable):
    nonserialize_attributes = ['Types']
    class Types:
        Personal = 'ContactEmailPersonal'
        Business = 'ContactEmailBusiness'
        Other = 'ContactEmailOther'
        Messenger = 'ContactEmailMessenger'
        Messenger2 = 'Messenger2'
        Messenger3 = 'Messenger3'
        Messenger4 = 'Messenger4'
        Passport = 'Passport'

#                 type = None, email = None, isMessengerEnabled = None,
#                 capability = None, messengerEnabledExternally = None, propertiesChanged = None):


class ContactPhone(pysoap.Serializable):
    nonserialize_attributes = ['Types']
    class Types:
        Personal = 'ContactPhonePersonal'
        Business = 'ContactPhoneBusiness'
        Mobile = 'ContactPhoneMobile'
        Page = 'ContactPhonePager'
        Other = 'ContactPhoneOther'
        Fax = 'ContactPhoneFax'
        Personal2 = 'Personal2'
        Business2 = 'Business2'
        BusinessFax = 'BusinessFax'
        BusinessMobile = 'BusinessMobile'

#        type = None, number = None, isMessengerEnabled = None, propertiesChanged = None):

class ContactLocation(pysoap.Serializable):
    nonserialize_attributes = ['Types']
    class Types:
        Personal = 'ContactLocationPersonal'
        Business = 'ContactLocationBusiness'

#                 type = None, name = None, street = None, city = None, state = None,
#                 country = None, postalCode = None, department = None, changes = None):

class ContactWebsite(pysoap.Serializable):
    nonserialize_attributes = ['Types']
    class Types:
        Personal = 'ContactWebSitePersonal'
        Business = 'ContactWebSiteBusiness'

#    def __init__(self, type = None, webURL = None):

class NetworkInfo(pysoap.Serializable):
    '''
    Attributes:
        domainId
        domainTag
        displayName
        userTileURL
        profileURL
        relationshipType
        relationshipState
        relationshipStateDate
        relationshipRole
        nDRCount
        inviterName
        inviterMessage
        inviterCID
        inviterEmail
        createDate
        lastChange
        propertiesChanged
        sourceId

        domainIdSpecified
        relationshipTypeSpecified
        relationshipStateSpecified
        relationshipRoleSpecified
        nDRCountSpecified
        inviterCIDSpecified
    '''

    @property
    def DomainIdSpecified(self):
        return hasattr(self, 'DomainId')
    @property
    def RelationshipTypeSpecified(self):
        return hasattr(self, 'RelationshipType')
    @property
    def RelationshipStateSpecified(self):
        return hasattr(self, 'RelationshipState')
    @property
    def RelationshipRoleSpecified(self):
        return hasattr(self, 'RelationshipRole')
    @property
    def NDRCountSpecified(self):
        return hasattr(self, 'NDRCount')
    @property
    def InviterCIDSpecified(self):
        return hasattr(self, 'InviterCID')

class MessengerMemberInfo(pysoap.Serializable):
    pendingAnnotations = [Annotation]

#    def __init__(self, pendingAnnotations = None, displayName = None):

class ContactInfo(pysoap.Serializable):
    emails = [ContactEmail]
    phones = [ContactPhone]
    locations = [ContactLocation]
    webSites = [ContactWebsite]
    annotations = [Annotation]
    NetworkInfoList = [NetworkInfo]
    messengerMemberInfo = [MessengerMemberInfo]

    isMessengerUser = False

    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        attrs = pysoap.extract_zsi_properties(obj)

        attrs['webSites']        = [ContactWebsite.from_zsi(x) for x in getattr(attrs.get('webSites'), 'ContactWebsite', [])]
        attrs['emails']          = [ContactEmail.from_zsi(x) for x in getattr(attrs.get('emails'), 'ContactEmail', [])]
        attrs['locations']       = [ContactLocation.from_zsi(x) for x in getattr(attrs.get('locations'), 'ContactLocation', [])]
        attrs['annotations']     = [Annotation.from_zsi(x) for x in getattr(attrs.get('annotations'), 'Annotation', [])]
        attrs['phones']          = [ContactPhone.from_zsi(x) for x in getattr(attrs.get('phones'), 'ContactPhone', [])]
        attrs['NetworkInfoList'] = [NetworkInfo.from_zsi(x) for x in getattr(attrs.get('NetworkInfoList'), 'NetworkInfo', None) or []]
        attrs['groupIds']        = [str(x) for x in getattr(attrs.get('groupIds', None), 'Guid', [])]
        attrs['groupIdsDeleted'] = [str(x) for x in getattr(attrs.get('groupIdsDeleted', None), 'Guid', [])]

        attrs.update(kwds)

        return cls(**attrs)


    '''
    Attributes:
        emails
        phones
        locations
        websites
        annotations
        network
        messenger_info
        groupIds
        groupIdsDeleted
        contactType
        quickName
        firstName
        MiddleName
        lastName
        Suffix
        NameTitle
        passportName
        IsPassportNameHidden
        IsPassportNameHiddenSpecified
        displayName
        puid
        puidSpecified
        CID
        CIDSpecified
        BrandIdList
        comment
        IsNotMobileVisible
        IsNotMobileVisibleSpecified
        isMobileIMEnabled
        isMobileIMEnabledSpecified
        isMessengerUser
        isMessengerUserSpecified
        isFavorite
        isFavoriteSpecified
        isSmtp
        isSmtpSpecified
        hasSpace
        hasSpaceSpecified
        spotWatchState
        birthdate
        primaryEmailType
        primaryEmailTypeSpecified
        PrimaryLocation
        PrimaryLocationSpecified
        PrimaryPhone
        PrimaryPhoneSpecified
        IsPrivate
        IsPrivateSpecified
        Anniversary
        Gender
        TimeZone
        PublicDisplayName
        IsAutoUpdateDisabled
        IsAutoUpdateDisabledSpecified
        PropertiesChanged
        clientErrorData
        IsHidden
        IsHiddenSpecified
    '''

import util.Events as Events
class Contact(pysoap.Serializable, Events.EventMixin):
    DirectBridge = None

    serialize_attributes = ['type']
    nonserialize_attributes = ['client', '_type', 'EndPointData',
                               'ADLCount', 'events', 'handlers',
                               'DirectBridge', 'P2PVersionSupported',
                               'dcType', 'dcPlainKey', 'dcLocalHashedNonce',
                               'dcRemoteHashedNonce',
                               ]

    contactInfo = ContactInfo
    ADLCount = 1

    dcPlainKey = uuid.UUID(int = 0)
    dcLocalHashedNonce = uuid.UUID(int = 0)
    dcRemoteHashedNonce = uuid.UUID(int = 0)
    dcType = 0

    events = Events.EventMixin.events | set((
        'DirectBridgeEstablished',
    ))

    def __repr__(self):
        return "%s(%r, type = %r)" % (type(self).__name__, self.account, str(self.type))

    def _get_P2PVersionSupported(self):
        import msn.P2P as P2P
        if not self.EndPointData:
            return P2P.Version.V1

        if int(self.SelectRandomEPID()) == 0:
            return P2P.Version.V1
        else:
            return P2P.Version.V2

    def _set_P2PVersionSupported(self, val):
        pass

    P2PVersionSupported = property(_get_P2PVersionSupported, _set_P2PVersionSupported)

    def SelectRandomEPID(self):
        for epid in self.EndPointData:
            if epid != uuid.UUID(int = 0):
                return epid

        return uuid.UUID(int = 0)

    def SelectBestEndPointId(self):
        for epid in self.EndPointData:
            if int(epid) == 0:
                continue

            epdata = self.EndPointData[epid]['PE']
            try:
                client_caps = int(str(epdata.Capabilities).split(':')[0])
            except Exception:
                continue

            if client_caps == 0:
                continue

            return epid

        return uuid.UUID(int = 0)


    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        attrs = pysoap.extract_zsi_properties(obj)
        attrs['contactInfo'] = ContactInfo.from_zsi(attrs['contactInfo'])
        attrs.update(kwds)

        return cls(**attrs)

    def __init__(self, abid = None, account = None, type = None, client = None, **kw):
        if type is None:
            raise Exception
        self.EndPointData = {}
        self.fDeleted = False
        Lists = set()
        type = ClientType(type)
        l = locals()
        self = l.pop('self')
        l.update(l.pop('kw'))
        pysoap.Serializable.__init__(self, **l)

        if self.contactInfo is Contact.contactInfo:
            self.contactInfo = ContactInfo()
        elif isinstance(self.contactInfo, dict):
            self.contactInfo = ContactInfo.deserialize(self.contactInfo)

        self.Lists = set(self.Lists)

        Events.EventMixin.__init__(self)
        self.GenerateNewDCKeys()

    def GenerateNewDCKeys(self):
        import msn.P2P.P2PSession as P2PS
        import msn.MSNUtil as MSNU
        self.dcType = P2PS.DCNonceType.Sha1
        self.dcPlainKey = uuid.uuid4()
        self.dcLocalHashedNonce = MSNU.HashNonce(self.dcPlainKey)
        self.dcRemoteHashedNonce = uuid.UUID(int=0)
        log.info("Generated new nonce keys for %r: plainKey = %r, hashedKey = %r", self.account, self.dcPlainKey, self.dcLocalHashedNonce)

#    create_date = pysoap.DateAttr('create_date')
#    lastChange = pysoap.DateAttr('lastChange')

    @classmethod
    def MakeHash(cls, account, type, abid = uuid.UUID(int=0)):
        return "%s:%s;via=%s" % (int(ClientType(type)), account.lower(), str(abid).lower())

    @property
    def Hash(self):
        return type(self).MakeHash(self.account, self.type, self.abid)

    def SetName(self, name):
        self.DisplayName = name

    def HasLists(self, lists):
        # self.Lists contains RL, AL, etc. (not ints or long-names)
        if not util.isiterable(lists):
            lists = [lists]

        return all(str(MSNList(x)) in self.Lists for x in lists)

    def HasList(self, list):
        return self.HasLists([list])

    def RemoveFromList(self, list):
        list = str(MSNList(list))
        self.Lists.discard(list)
        self.client.contact_remove(self.account, list, None)

    def AddToList(self, list):
        self.Lists.add(str(MSNList(list)))

    @classmethod
    def GetConflictLists(self, current, newlists):
        if isinstance(newlists, basestring):
            newlists = [newlists]

        conflict = set()
        if MSNList.Allow in current and MSNList.Block in newlists:
            conflict.add(str(MSNList.Allow))

        if MSNList.Block in current and MSNList.Allow in newlists:
            conflict.add(str(MSNList.Block))

        return conflict

    @property
    def Mail(self):
        return self.account.lower()

    def _get_type(self):
        return self._type
    def _set_type(self, val):
        self._type = ClientType(val)

    type = property(_get_type, _set_type)

    def RemoveFromGroup(self, g_id):
        if g_id in self.contactInfo.groupIds:
            self.contactInfo.groupIds.remove(g_id)
        self.client.contact_remove(self.account, str(MSNList.Forward), g_id)

    def _get_OnAllowedList(self):
        return self.HasList(MSNList.Allow)

    def _set_OnAllowedList(self, value):
        if value == self.OnAllowedList:
            return

        if value:
            self.Blocked = False
        elif not self.OnReverseList:
            self.client.RemoveContactFromList(self, MSNList.Allow)

    OnAllowedList = property(_get_OnAllowedList, _set_OnAllowedList)

    def _get_OnBlockedList(self):
        return self.HasList(MSNList.Block)
    def _set_OnBlockedList(self, value):
        if value == self.OnBlockedList:
            return

        if value:
            self.Blocked = True
        elif not self.OnReverseList:
            self.client.RemoveContactFromList(self, MSNList.Block)

    OnBlockedList = property(_get_OnBlockedList, _set_OnBlockedList)

    def _get_OnForwardList(self):
        return self.HasList(MSNList.Forward)

    def _set_OnForwardList(self, value):
        if self.OnForwardList == value:
            return

        if value:
            self.client.AddContactToList(self, MSNList.Forward)
        else:
            self.client.RemoveContactFromList(self, MSNList.Forward)

    OnForwardList = property(_get_OnForwardList, _set_OnForwardList)

    def _get_OnReverseList(self):
        return self.HasList(MSNList.Reverse)

    OnReverseList = property(_get_OnReverseList)

    def _get_OnPendingList(self):
        return self.HasList(MSNList.Pending)
    def _set_OnPendingList(self, value):
        if value != self.OnPendingList and value == False:
            self.client.RemoveContactFromList(self, MSNList.PL)

    OnPendingList = property(_get_OnPendingList, _set_OnPendingList)

    def _get_IsMessengerUser(self):
        return self.contactInfo.isMessengerUser
    def _set_IsMessengerUser(self, value):
        guid_empty = str(uuid.UUID(int=0))
        guid = getattr(self, 'Guid', getattr(self, 'contactId', guid_empty))
        if guid != guid_empty and value != self.IsMessengerUser:
            self.contactInfo.isMessengerUser = value
            if getattr(self, 'client', None) is not None:
                self.client.UpdateContact(self, getattr(self, 'abid', guid_empty))

    IsMessengerUser = property(_get_IsMessengerUser, _set_IsMessengerUser)

    def getCID(self):
        return getattr(self, 'CID', getattr(getattr(self, 'contactInfo', None), 'CID', 0))

class CircleInviter(Contact):
    def __init__(self, account, invite_message, client, **kw):
        Contact.__init__(self, abid = str(uuid.UUID(int=0)), account = account, type = ClientType.PassportMember, client = client, **kw)
        self.invite_message = invite_message

class ContentHandle(pysoap.Serializable):
    '''Attributes:
        Id
    '''

class ContentInfo(pysoap.Serializable):
    '''Attributes:
        domain
        hostedDomain
        type
        membershipAccess
        isPresenceEnabled
        requestMembershipOption
        displayName
        profileLastUpdated
        changes
        createDate
        lastChange
    '''

#    createDate = pysoap.DateAttr('createDate')
#    lastChange = pysoap.DateAttr('lastChange')

class Content(pysoap.Serializable):
    Handle = ContentHandle
    Info = ContentInfo

    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        attrs = pysoap.extract_zsi_properties(obj)
        attrs.update(kwds)

        attrs['Info'] = cls.Info.from_zsi(attrs['Info'])
        attrs['Handle'] = cls.Handle.from_zsi(attrs['Handle'])

        return cls(**attrs)

class CirclePersonalMembership(pysoap.Serializable):
    '''Attributes:
        Role
        State
    '''

class MembershipInfo(pysoap.Serializable):
    CirclePersonalMembership = CirclePersonalMembership

    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        attrs = pysoap.extract_zsi_properties(obj)
        attrs.update(kwds)

        attrs['CirclePersonalMembership'] = cls.CirclePersonalMembership.from_zsi(attrs['CirclePersonalMembership'])

        return cls(**attrs)

class PersonalInfo(pysoap.Serializable):
    '''Attributes:
        MembershipInfo
        Name
        IsNotMobileVisible
        IsFavorite
        IsFamily
        Changes
    '''
    MembershipInfo = MembershipInfo

    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        attrs = pysoap.extract_zsi_properties(obj)
        attrs.update(kwds)

        attrs['MembershipInfo'] = cls.MembershipInfo.from_zsi(attrs['MembershipInfo'])

        return cls(**attrs)

class CircleInverseInfo(pysoap.Serializable):
    Content = Content
    PersonalInfo = PersonalInfo
#    def __init__(self, content = None, personalInfo = None, deleted = None):

    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        attrs = pysoap.extract_zsi_properties(obj)
        attrs.update(kwds)

        attrs['PersonalInfo'] = cls.PersonalInfo.from_zsi(attrs['PersonalInfo'])
        attrs['Content'] = cls.Content.from_zsi(attrs['Content'])

        return cls(**attrs)

class CircleInfo(pysoap.Serializable):
    circle_member = Contact
    circle_result = CircleInverseInfo
#    def __init__(self, member_role = None, circle_member = None, circle_result = None):

class ProfileField(pysoap.Serializable):
#    def __init__(self, date_modified, resource_id):

#    DateModified = pysoap.DateAttr('DateModified')
    pass

class ProfilePhoto(ProfileField):
#    def __init__(self, pre_auth_url = None, name = None, image = None):
    pass

class OwnerProfile(ProfileField):
    photo = ProfilePhoto
    expression = ProfileField
#    def __init__(self, display_name = None, message = None, photo = None, has_expression = False, expression = None):
    pass

class Owner(Contact):
    def __init__(self, abid = None, account = None, client = None, **kw):
        kw.pop('type', None)
        Contact.__init__(self, abid = abid, account = account, type = ClientType.PassportMember, client = client, **kw)

class ABInfo(pysoap.Serializable):
    name = None
    ownerPuid = None
    OwnerCID = 0
    ownerEmail = None
    fDefault = None
    joinedNamespace = None
    IsBot = None
    IsParentManaged = None
    SubscribeExternalPartner = None
    NotifyExternalPartner = None
    AddressBookType = None
    MessengerApplicationServiceCreated = None
    IsBetaMigrated = None
    MigratedTo = 0
#    lastChange = pysoap.DateAttr('lastChange')

class ABFindContactsPagedResult(pysoap.Serializable):
    abId = None
    abInfo = ABInfo
#    lastChange = pysoap.DateAttr('lastChange')
#    DynamicItemLastChanged = pysoap.DateAttr('DynamicItemLastChanged')
#    RecentActivityItemLastChanged = pysoap.DateAttr('RecentActivityItemLastChanged')
#    createDate = pysoap.DateAttr('createDate')
    propertiesChanged = ''

class ContactList(pysoap.Serializable):
    nonserialize_attributes = ['client']
    #serialize_attributes
    contacts = {'' : Contact}
    groups = {'' : Group}
    abid = None

    owner = Owner

    def __init__(self, client = None, abid = None, contacts = None, groups = None, **kw):
        self.client = client

        super(ContactList, self).__init__(abid = str(abid).lower(), contacts = contacts or {}, groups = groups or {}, **kw)
        if self.owner is ContactList.owner:
            self.owner = None
        if self.contacts is ContactList.contacts:
            self.contacts = {}
        if self.groups is ContactList.groups:
            self.groups = {}

    def GetContact(self, account, type = None):
        type = ClientType(type)
        if type == ClientType.CircleMember:
            return self.client.GetCircle(account)

        if type is None:
            for type in (ClientType.PassportMember, ClientType.EmailMember, ClientType.PhoneMember, ClientType.LCS):
                if self.HasContact(account, type = type):
                    return self.GetContact(account, type = type)

                circle = self.client.GetCircle(account)
                if circle is not None:
                    return circle

            return None

        hash = Contact.MakeHash(account, type, self.abid)
        if hash in self.contacts:
            contact = self.contacts[hash]
        else:
            contact = self.contacts[hash] = Contact(self.abid, account, type, self.client)

        if contact.client is None:
            contact.client = self.client
        return contact

    def HasContact(self, account, type = None):
        if type is None:
            return any(self.HasContact(account, type) for type in (ClientType.PassportMember, ClientType.EmailMember, ClientType.PhoneMember, ClientType.LCS))
        else:
            return Contact.MakeHash(account, type, self.abid) in self.contacts

    def GetGroup(self, id):
        return self.groups.get(id, None)

    def GroupAdded(self, name, id, is_favorite):
        self.groups[id] = Group(name = name, id = id, groupInfo = GroupInfo(IsFavorite = is_favorite))
        self.client.group_receive(name.decode('utf8'), id)

    def GroupRemoved(self, group):
        self.groups.pop(group.id, None)
        self.client.group_remove(group.id)

    def GetContactByGuid(self, id):
        id = str(id).lower()
        for contact in self.contacts.values():
            if getattr(contact, 'contactId', sentinel) == id:
                return contact

        return None

    def ContactAdded(self, contact, list_id, groups = None):
        groups = groups or []
        if contact.account is None:
            return

        if getattr(contact, 'client', None) is None:
            contact.client = self.client

        role = MSNList(list_id)
        contact.AddToList(role)
        conflict_lists = Contact.GetConflictLists(contact.Lists, role)
        contact.Lists.update(conflict_lists)
        conflict_lists.add(str(role))
        list_flags = 0
        for list in conflict_lists:
            list_flags |= int(role)

        self.client.contact_btype(contact.account, contact.type)
        self.client.recv_contact(contact.account.decode('utf8'),
                                 list_flags,
                                 groups if str(MSNList.Forward) in conflict_lists else None,
                                 id = getattr(contact, 'contactId', getattr(contact, 'CID', 0) or contact.account))

    def ContactRemoved(self, contact, list_id, groups = None):
        if getattr(contact, 'client', None) is None:
            contact.client = self.client

        if groups is not None and list_id == MSNList.Forward:
            for group in groups:
                contact.RemoveFromGroup(group)

        if not groups:
            messengerServiceMembership = self.client.address_book.SelectTargetMemberships(ServiceFilters.Messenger)

            role = MSNList(list_id).role

            if messengerServiceMembership is not None and role is not None:
                roleMembers = messengerServiceMembership.Memberships.get(role, {})
                log.info("Removing %r from role %r", contact.Hash, role)
                roleMembers.pop(contact.Hash, None)

            contact.RemoveFromList(list_id)

    def OnCreateCircle(self, circle):
        log.info("Circle created: %r", circle)

class Circle(Contact):
    contactList = None
    hostDomain = 'live.com'
    segmentCounter = 0
    meContact = None
    hiddenRep = None
    abinfo = None
    contactList = ContactList
    circleInfo = CircleInverseInfo

    @property
    def HostDomain(self):
        return self.hostDomain

    @property
    def ContactList(self):
        return self.contactList

    @property
    def LastChanged(self):
        if self.abinfo is None:
            return soap.MinTime
        else:
            return self.abinfo.lastChange

    def __init__(self, meContact = None, hiddenRep = None, circleInfo = None, client = None, **kw):
        if isinstance(circleInfo, dict):
            circleInfo = CircleInverseInfo.deserialize(circleInfo)
        if isinstance(meContact, dict):
            meContact = Contact.deserialize(meContact)
        if isinstance(hiddenRep, dict):
            hiddenRep = Contact.deserialize(hiddenRep)

        Contact.__init__(self,
                         abid = kw.pop('abid', circleInfo.Content.Handle.Id.lower()),
                         account = kw.pop('account', circleInfo.Content.Handle.Id.lower() + '@' + circleInfo.Content.Info.HostedDomain.lower()),
                         type = kw.pop('type', IMAddressInfoType.Circle),
                         CID = kw.pop('CID', meContact.contactInfo.CID),
                         client = kw.pop('client', client),
                         circleInfo = circleInfo,
                         **kw)
        self.meContact = meContact
        self.hiddenRep = hiddenRep
        self.hostDomain = circleInfo.Content.Info.HostedDomain.lower()

        self.CircleRole = getattr(CirclePersonalMembershipRole, circleInfo.PersonalInfo.MembershipInfo.CirclePersonalMembership.Role)
        self.SetName(circleInfo.Content.Info.DisplayName)
        self.SetNickName(self.Name)
        self.contactList = ContactList(abid = self.abid,
                                       owner = Owner(abid = self.abid,
                                                     account = meContact.contactInfo.passportName,
                                                     CID = meContact.contactInfo.CID,
                                                     client = client),
                                                 client = client)

        self.AddToList(MSNList.Allow)
        self.AddToList(MSNList.Forward)

    @property
    def AddressBookId(self):
        return self.abid

    def SetName(self, name):
        self.Name = name

    def SetNickName(self, nick):
        self.NickName = nick

    @classmethod
    def MakeHash(cls, abid_or_mail, domain = hostDomain):
        if abid_or_mail.startswith("9:"):
            abid_or_mail = abid_or_mail[2:]

        try:
            email = net.EmailAddress(abid_or_mail)
        except (TypeError, ValueError):
            abid = abid_or_mail
        else:
            abid = email.name
            domain = email.domain

        abid = str(abid).lower()
        circleMail = abid + '@' + domain
        circleHash = Contact.MakeHash(circleMail, ClientType.CircleMember, abid)
        return circleHash

    @property
    def Hash(self):
        return type(self).MakeHash(self.abid, self.hostDomain)

    @property
    def MemberNames(self):
        return [x.account for x in self.GetContactsForState(RelationshipStates.Accepted)]

    @property
    def PendingNames(self):
        return [x.account for x in self.GetContactsForState(RelationshipStates.WaitingResponse)]

    def GetContactsForState(self, relState):
        ab = self.client.address_book
        contacts = []
        for contact in ab.AddressBookContacts[self.AddressBookId].values():
            if ab.GetCircleMemberRelationshipStateFromNetworkInfo(contact.contactInfo.NetworkInfoList) == relState:
                contacts.append(contact)

        return contacts

    def GetContactsForRole(self, relRole):
        ab = self.client.address_book
        contacts = []
        for contact in ab.AddressBookContacts[self.AddressBookId].values():
            if ab.GetCircleMemberRoleFromNetworkInfo(contact.contactInfo.NetworkInfoList) == relRole:
                contacts.append(contact)

        return contacts

class AddressBook(pysoap.Serializable):
    nonserialize_attributes = ['initialized', 'client', 'MyProperties', 'PendingAcceptionCircleList']

    MembershipList = {'' : ServiceMembership}
    groups = {'' : Group}

    AddressBookContacts = {'' : {'' : Contact}}
    AddressBooksInfo = {'' : ABInfo}
    CircleResults = {'' : CircleInverseInfo}

    def Save(self):
        try:
            if self.client.address_book is self:
                self.client.address_book = self
        except Exception:
            import traceback; traceback.print_exc()

    def __init__(self, client = None, **kw):
        self.client = client
        self.initialized = False
        self.request_circle_count = 0;
        self.WLConnections = {}
        self.WLInverseConnections = {}
        self.MyProperties = {
                             AnnotationNames.MSN_IM_MBEA : '0',
                             AnnotationNames.MSN_IM_GTC: '1',
                             AnnotationNames.MSN_IM_BLP : '0',
                             AnnotationNames.MSN_IM_MPOP : '1',
                             AnnotationNames.MSN_IM_RoamLiveProperties : '1',
                             AnnotationNames.Live_Profile_Expression_LastChanged: soap.MinTime,
                             }

        if self.groups is AddressBook.groups:
            self.groups = {}

        if self.AddressBookContacts is AddressBook.AddressBookContacts:
            self.AddressBookContacts = {}

        self.contactTable = {}

        if self.MembershipList is AddressBook.MembershipList:
            self.MembershipList = {}

        if self.AddressBooksInfo is AddressBook.AddressBooksInfo:
            self.AddressBooksInfo = {}

        if self.CircleResults is AddressBook.CircleResults:
            self.CircleResults = {}

        pysoap.Serializable.__init__(self, **kw)

        self.PendingAcceptionCircleList = {}

        if not hasattr(self, 'PendingCreateCircleList'):
            self.PendingCreateCircleList = {}

    def load_from_file(self, filename):
        pass

    def initialize(self):
        if getattr(self, 'initialized', False):
            return

        intialized = True
        service_ms = self.SelectTargetMemberships(ServiceFilters.Messenger)
        if service_ms is not None:
            ms = service_ms.Memberships
        else:
            ms = None

        if ms is not None:
            for role in ms.keys():
                msnlist = getattr(MSNList, role, None)

                for member in ms[role].values():
                    cid = 0
                    account = None
                    type = None

                    if isinstance(member, PassportMember):
                        if not getattr(member, 'IsPassportNameHidden', False):
                            account = member.PassportName
                        cid = getattr(member, 'CID', 0)
                        type = 'Passport'
                    elif isinstance(member, EmailMember):
                        type = 'Email'
                        account = member.Email
                    elif isinstance(member, PhoneMember):
                        type = 'Phone'
                        account = member.PhoneNumber

                    if account is not None and type is not None:
                        contact = self.client.contact_list.GetContact(account, type)
                        contact.CID = cid
                        self.client.contact_list.ContactAdded(contact, msnlist)

        for group in self.groups.values():
            self.client.contact_list.GroupAdded(group.groupInfo.name, group.id, group.groupInfo.IsFavorite)

        for abId in self.AddressBookContacts.keys():
            self.SaveContactTable(self.AddressBookContacts[abId].values())

        self.RestoreWLConnections()
        for State in (RelationshipStates.Accepted, RelationshipStates.WaitingResponse):
            CIDs = self.FilterWLConnections(self.WLConnections.keys(), State)
            log.info("Restoring Circles: %r, %r", CIDs, State)
            self.RestoreCircles(CIDs, State)

        default_id = str(uuid.UUID(int=0))
        default_page = self.AddressBookContacts.get(default_id, None)

        if default_page is not None:
            for contactType in default_page.values():
                self.UpdateContact(contactType)

    def UpdateContact(self, contact, abid = uuid.UUID(int=0), circle = None):
        info = getattr(contact, 'contactInfo', None)
        if info is None:
            return

        log.debug("Updating contactInfo: %r", contact)

        type = IMAddressInfoType.WindowsLive

        account = info.passportName
        displayName = info.displayName
        nickname = self.GetContactNickName(contact)
        userTileUrl = self.GetUserTileURLFromWindowsLiveNetworkInfo(contact)
        isMessengerUser = info.isMessengerUser or False
        lowerid = str(abid).lower()
        fDeleted = contact.fDeleted

        isDefaultAddressBook = lowerid == str(uuid.UUID(int=0)).lower()

        if info.emails is not None and account is None:
            for ce in info.emails:
                log.info("process email: %r", ce)
                if ce.contactEmailType == info.primaryEmailType or account is None:
                    log.info("using email as primary: %r", ce)
                    type = ClientType(int(ce.Capability))
                    if account is None:
                        account = ce.email
                    isMessengerUser |= ce.isMessengerEnabled
                    displayName = account

        if info.phones is not None and account is None:
            type = ClientType.PhoneMember
            for cp in info.phones:
                log.info("process phone: %r", cp)
                if cp.contactPhoneType == info.PrimaryPhone or account is None:
                    log.info("using phone as primary: %r", cp)
                    if account is None:
                        account = cp.number
                    isMessengerUser |= cp.isMessengerEnabled
                    displayName = account

        if account is not None:
            account = account.lower()
            if info.contactType != MessengerContactType.Me:
                if isDefaultAddressBook:
                    contactList = self.client.contact_list
                    contact = contactList.GetContact(account, type=type)
                else:
                    if circle is not None:
                        mRole = self.GetCircleMemberRoleFromNetworkInfo(info.NetworkInfoList)
                        contactList = circle.contactList
                        contact = contactList.GetContact(account, type=type)
                        contact.CircleRole = mRole
                        nickname = self.GetCircleMemberDisplayNameFromNetworkInfo(info.NetworkInfoList) or nickname

                contact.CID = info.CID
                contact.type = type
                contact.hasSpace = info.hasSpace
                contact.IsMessengerUser = isMessengerUser
                contact.UserTileURL = userTileUrl
                contact.NickName = nickname
                self.SetContactPhones(contact, info)

                if True or contact.IsMessengerUser:
                    contact.AddToList(MSNList.Forward)
                    log.debug("Forcing %r to forward list", contact)
                    contactList.ContactAdded(contact, MSNList.Forward, getattr(contact.contactInfo, 'groupIds', []))

                needsDelete = False
                relState = self.GetCircleMemberRelationshipStateFromNetworkInfo(info.NetworkInfoList)
                if (relState in (RelationshipStates.Rejected, RelationshipStates.NONE)) and not isDefaultAddressBook:
                    needsDelete = True

                if getattr(info, 'IsHidden', False):
                    needsDelete = True

                owner = self.client.contact_list.owner
#                if account == owner.Mail.lower() and info.NetworkInfoList and type == owner.type and not isDefaultAddressBook:
#                    needsDelete = True

                if fDeleted:
                    needsDelete = True

                if needsDelete and len(contact.Lists) == 0:
                    log.debug("Contact %r needs delete", contact)
                    contactList.contacts.pop(contact.Hash, None)

            else:
                owner = None
                if not isDefaultAddressBook:
                    if circle is None:
                        log.info("Can't update owner %r in addressbook: %r", account, abid)
                        return
                    owner = circle.contactList.owner
                    mRole = self.GetCircleMemberRoleFromNetworkInfo(info.NetworkInfoList)
                    contactList = circle.contactList
                    contact.CircleRole = mRole
                    if contact.account == self.client.self_buddy.name:
                        circle.CircleRole = mRole
                        log.info("Got new circle role for mRole = %r, circle %r", mRole, circle)
                    nickname = self.GetCircleMemberDisplayNameFromNetworkInfo(info.NetworkInfoList) or nickname

                else:
                    owner = self.client.contact_list.owner
                    if owner is None:
                        owner = Owner()
                        owner.__dict__.update(vars(contact))
                        owner.abid = lowerid
                        owner.account = info.passportName
                        owner.CID = int(info.CID)
                        owner.client = self.client
                        log.info("Set owner for contact list: %r", owner)
                        self.client.contact_list.owner = owner

                if displayName == owner.Mail and bool(owner.name):
                    displayName == owner.name

                owner.Guid = str(uuid.UUID(contact.contactId)).lower()
                owner.CID = int(info.CID)
                owner.contactType = info.contactType

                if nickname and not getattr(owner, 'NickName', ''):
                    owner.NickName = nickname

                owner.UserTileURL = userTileUrl
                self.SetContactPhones(owner, info)

                if info.annotations and isDefaultAddressBook:
                    for anno in info.annotations:
                        self.MyProperties[anno.Name] = anno.Value

    def SaveContactTable(self, contacts):
        if not contacts:
            return

        for contact in contacts:
            if contact.contactInfo is not None:
                self.contactTable[contact.contactInfo.CID] = contact.contactId

    def RestoreWLConnections(self):
        self.WLInverseConnections = {}

        for CID in self.WLConnections.keys():
            self.WLInverseConnections[self.WLConnections[CID]] = CID

    def FilterWLConnections(self, cids, state):
        to_return = []
        for cid in cids:
            if self.HasWLConnection(cid) and self.HasContact(cid):
                contact = self.SelectContact(cid)
                if state == RelationshipStates.NONE:
                    to_return.append(cid)
                else:
                    repRelState = self.GetCircleMemberRelationshipStateFromNetworkInfo(contact.contactInfo.NetworkInfoList)
                    if repRelState == state:
                        to_return.append(cid)

        return to_return

    def RestoreCircles(self, cids, state):
        for cid in cids:
            self.RestoreCircleFromAddressBook(self.SelectWLConnectionByCID(cid), self.SelectContact(cid), state)

    def SelectWLConnectionByCID(self, CID):
        if not self.HasWLConnection(CID):
            return None
        return self.WLConnections.get(CID)

    def SelectWLConnectionByAbId(self, abid):
        abid = abid.lower()
        if not self.HasWLConnection(abid):
            return None
        return self.WLInverseConnections.get(abid)

    SelectWLConnection = SelectWLConnectionByAbId

    def SelectWLConnectionsByCIDs(self, CIDs, state = RelationshipStates.NONE):
        abids = []
        for CID in CIDs:
            if self.HasWLConnection(CID) and self.HasContact(CID):
                abid = self.WLConnections.get(CID)
                contact = self.SelectContact(CID)
                if state == RelationshipStates.NONE:
                    abids.append(abid)
                else:
                    cid_state = self.GetCircleMemberRelationshipStateFromNetworkInfo(contact.contactInfo.NetworkInfoList)
                    if cid_state == state:
                        abids.append(abid)

        return abids

    def RestoreCircleFromAddressBook(self, abId, hidden, state):
        lowerid = abId.lower()
        if lowerid == str(uuid.UUID(int=0)).lower():
            log.error("AddressBook is not a circle")
            return True

        if not self.HasAddressBook(lowerid):
            log.error("Don't have circle with ID = %r", lowerid)
            return False

        if not lowerid in self.AddressBookContacts:
            log.error("Don't have circle contact with ID = %r", lowerid)
            return False

        me = self.SelectMeFromContactList(self.AddressBookContacts[lowerid].values())
        inverseInfo = self.SelectCircleInverseInfo(lowerid)

        if me is None:
            log.error("Don't have a 'me' contact for %r", lowerid)
            return False
        if hidden is None:
            log.error("Need a hidden contact for %r", lowerid)
            return False
        if inverseInfo is None:
            log.error("No circle info for %r", lowerid)
            return False

        circleHash = Circle.MakeHash(lowerid, inverseInfo.Content.Info.HostedDomain)

        if self.client.CircleList.get(circleHash, None) is None:
            log.error("No circle object found for %r", circleHash)
            return False

        circle = self.CreateCircle(me, hidden, inverseInfo)
        if circle is None:
            log.error("Incorrect info to create circle")
            return False
        self.UpdateCircleMembersFromAddressBookContactPage(circle, Scenario.Restore)

        CPMR = CirclePersonalMembershipRole
        if circle.CircleRole in (CPMR.Admin, CPMR.AssistantAdmin, CPMR.Member):
            self.AddCircleToCircleList(circle)
        elif circle.CircleRole == CPMR.StatePendingOutbound:
            self.FireJoinCircleInvitationReceivedEvents(circle)
        else:
            raise Exception("Unknown circleRole: %r", circle.CircleRole)

    def SelectTargetMemberships(self, servicefilter):
        return self.MembershipList.get(servicefilter, None)

    def SelectCircleInverseInfo(self, abid):
        if not abid:
            return None

        abid = abid.lower()

        return self.CircleResults.get(abid, None)

    def SelectContact(self, cid):
        guid = self.contactTable.get(cid, cid)
        if guid is None:
            return None

        for abid in sorted(self.AddressBookContacts.keys()):
            if guid in self.AddressBookContacts[abid]:
                return self.AddressBookContacts[abid][guid]

        return None

    def Merge(self, fmresult):
        self.initialize()

        if fmresult is None:
            return

        for serviceType in fmresult.Services.Service:
            oldService = self.SelectTargetService(serviceType.Info.Handle.Type)
            if oldService is None or (oldService.lastChange <= serviceType.LastChange):
                log.debug("Merging service %r", serviceType.Info.Handle.Type)
                if serviceType.Deleted:
                    self.MembershipList.pop(serviceType.Info.Handle.Type, None)
                else:
                    updatedService = Service(id     = int(serviceType.Info.Handle.Id),
                                             type   = serviceType.Info.Handle.Type,
                                             lastChange = serviceType.LastChange,
                                             foreign_id = serviceType.Info.Handle.ForeignId)

                    if oldService is None:
                        self.MembershipList[updatedService.type] = ServiceMembership(Service = updatedService)

                    if serviceType.Memberships:
                        if updatedService.type == ServiceFilters.Messenger:
                            self.ProcessMessengerServiceMemberships(serviceType, updatedService)
                        else:
                            self.ProcessOtherMemberships(serviceType, updatedService)

                    self.MembershipList[updatedService.type].Service = updatedService
            else:
                log.debug("Service %r is up to date (%r >= %r)",
                          serviceType.Info.Handle.Type,
                          oldService.lastChange,
                          serviceType.LastChange)

    def ProcessMessengerServiceMemberships(self, service, clone):
        for mship in service.Memberships.Membership:
            if mship.Members and mship.Members.Member:
                role = mship.MemberRole
                log.info("Processing Membership: %r", role)
                members = list(mship.Members.Member)
                members = map(Member.from_zsi, members)
                log.info("ProcessMessengerServiceMemberships: Role = %r, members = %r", role, members)

                for bm in sorted(members, key = lambda x: getattr(x, 'lastChange', soap.MinTime)):
                    cid = 0
                    account = None
                    type = ClientType.NONE

                    if isinstance(bm, PassportMember):
                        type = ClientType.PassportMember
                        if not bm.IsPassportNameHidden:
                            account = bm.PassportName
                        cid = bm.CID
                    elif isinstance(bm, EmailMember):
                        type = ClientType.EmailMember
                        account = bm.Email
                    elif isinstance(bm, PhoneMember):
                        type = ClientType.PhoneMember
                        account = bm.PhoneNumber
                    elif isinstance(bm, CircleMember):
                        type = ClientType.CircleMember
                        account = bm.CircleId
                        self.circlesMembership.setdefault(role, []).append(bm)

                    if account is not None and type != ClientType.NONE:
                        #log.info("\t%r member: %r", role, account)
                        account = account.lower()
                        ab = self.client.getService(SOAPServices.AppIDs.AddressBook)
                        cl = self.client.contact_list
                        msnlist = getattr(MSNList, role, None)

                        if type == ClientType.CircleMember:
                            continue


                        if bm.Deleted:
                            if self.HasMembership(clone.ServiceType, account, type, role):
                                contact = self.MembershipList[clone.type].Memberships[role][Contact.MakeHash(account, type)]
                                contact_lastChange = contact.lastChange
                                if contact_lastChange < bm.lastChange:
                                    self.RemoveMembership(clone.type, account, type, role, Scenario.DeltaRequest)

                            if cl.HasContact(account, type):
                                contact = ab.GetContact(account, type = type)
                                contact.CID = cid
                                if contact.HasLists(msnlist):
                                    contact.RemoveFromList(msnlist)
                                    #if msnlist == 'RL':
                                    #    ab.OnReverseRemoved(contact)

                                    self.OnContactRemoved(contact, msnlist)
                        else:
                            contact_lastChange = getattr((self.MembershipList[clone.type].Memberships or {})
                                                         .get(role, {}) # might not have this role
                                                         .get(Contact.MakeHash(account, type), None), # or this contact
                                                         'LastChanged', soap.MinTime) # and so we might not have this value
                            if getattr(bm, 'LastChanged', soap.MinTime) >= contact_lastChange:
                                self.AddMembership(clone.type, account, type, role, bm, Scenario.DeltaRequest)

                            displayname = bm.DisplayName or account
                            contact = cl.GetContact(account, type)
                            contact.CID = cid
                            self.client.contact_list.ContactAdded(contact, msnlist)

    def ProcessOtherMemberships(self, service, clone):
        for mship in service.Memberships:
            if mship.Members and mship.Members.Member:
                role = mship.MemberRole

                for bm in sorted(mship.Members.Member, key = lambda x: x.lastChange):
                    account = None
                    type = ClientType.NONE

                    if bm.Type == MembershipType.Passport:
                        type = ClientType.PassportMember
                        if not bm.IsPassportNameHidden:
                            account = bm.PassportName
                    elif bm.Type == MembershipType.Email:
                        type = ClientType.EmailMember
                        account = bm.Email
                    elif bm.Type == MembershipType.Phone:
                        type = ClientType.PhoneMember
                        account = bm.PhoneNumber
                    elif bm.Type in (MembershipType.Role, MembershipType.Service, MembershipType.Everyone, MembershipType.Partner):
                        account = bm.Type + "/" + bm.MembershipId
                    elif bm.Type == MembershipType.Domain:
                        account = bm.DomainName
                    elif bm.Type == MembershipType.Circle:
                        type = ClientType.CircleMember
                        account = bm.CircleId

                    if account is not None and type != ClientType.NONE:
                        if bm.Deleted:
                            self.RemoveMembership(clone.type, account, type, role, Scenario.DeltaRequest)
                        else:
                            self.AddMembership(clone.type, account, type, role, bm, Scenario.DeltaRequest)

    def AddMembership(self, servicetype, account, type, memberrole, member, scene):
        #log.debug("AddMembership(%r, %r, %r, %r, %r, %r)", servicetype, account, type, memberrole, member, scene)
        service = self.SelectTargetMemberships(servicetype)
        ms = service.Memberships
        if not ms:
            ms = service.Memberships = {}
        if memberrole not in ms:
            ms[memberrole] = {}
        ms[memberrole][Contact.MakeHash(account, type)] = member

        if scene == Scenario.DeltaRequest:
            if memberrole == MemberRole.Allow:
                self.RemoveMembership(servicetype, account, type, MemberRole.Block, Scenario.InternalCall)

            if memberrole == MemberRole.Block:
                self.RemoveMembership(servicetype, account, type, MemberRole.Allow, Scenario.InternalCall)

        contact = self.client.contact_list.GetContact(account, type = type)
        msnlist = getattr(MSNList, memberrole, None)
        #log.info("AddMembership: role = %r, contact = %r", memberrole, contact)
        self.client.contact_list.ContactAdded(contact, msnlist)

    def RemoveMembership(self, servicetype, account, type, role, scenario = None):
        ms = self.SelectTargetMemberships(servicetype).Memberships
        if ms:
            hash = Contact.MakeHash(account, type)
            ms.get(role, {}).pop(hash, None)

    def RemoveContactFromAddressBook(self, abid, contactid):
        abid = str(abid).lower()
        return self.AddressBookContacts.get(abid, {}).pop(contactid, None)

    def RemoveContactFromContacttable(self, cid):
        return self.contactTable.pop(cid, None)

    def RemoveAddressBookInfo(self, abid):
        return self.AddressBooksInfo.pop(str(abid).lower(), None)

    def RemoveAddressBookContactPage(self, abid):
        return self.AddressBookContacts.pop(str(abid).lower(), None)

    def SetContactToAddressBookContactPage(self, abid, contact):
        abid = str(abid).lower()
        ab_created = False

        if abid not in self.AddressBookContacts:
            self.AddressBookContacts[abid] = {}
            ab_created = True

        log.debug("SetContactToAddressBookContactPage: %r", contact)
        self.AddressBookContacts[abid][str(uuid.UUID(contact.contactId)).lower()] = contact

        return ab_created

    def SetAddressBookInfoToABInfoList(self, abid, ab):
        abid = str(abid).lower()
        if self.AddressBooksInfo is None:
            return False

        abinfo = ab.AbInfo

        self.AddressBooksInfo[abid] = ABInfo(id = ab.AbId,
                                             lastChange = ab.LastChange,
                                             name = abinfo.Name,
                                             ownerPuid = abinfo.OwnerPuid,
                                             OwnerCID = abinfo.OwnerCID,
                                             ownerEmail = abinfo.OwnerEmail,
                                             fDefault = abinfo.FDefault,
                                             joinedNamespace = abinfo.JoinedNamespace,
                                             IsBot = abinfo.IsBot,
                                             IsParentManaged = abinfo.IsParentManaged,
                                             SubscribeExternalPartner = abinfo.SubscribeExternalPartner,
                                             NotifyExternalPartner = abinfo.NotifyExternalPartner,
                                             AddressBookType = abinfo.AddressBookType,
                                             MessengerApplicationServiceCreated = abinfo.MessengerApplicationServiceCreated,
                                             IsBetaMigrated = abinfo.IsBetaMigrated,
                                             MigratedTo = abinfo.MigratedTo,
                                             )
        return True

    def HasContact(self, abid = None, guid = None):
        return self.SelectContactFromAddressBook(abid, guid) is not None

    def HasWLConnection(self, cid_or_abid):
        return (cid_or_abid in self.WLConnections) or (str(cid_or_abid).lower() in self.WLInverseConnections)

    def HasAddressBook(self, abid):
        if self.AddressBooksInfo is None:
            return False

        return str(abid).lower() in self.AddressBooksInfo

    def HasAddressBookContactPage(self, abid):
        abid = str(abid).lower()
        if self.AddressBookContacts is None:
            return False

        return self.AddressBookContacts.get(abid, None) is not None

    def HasMembership(self, servicetype, account, type, role):
        return self.SelectBaseMember(servicetype, account, type, role) is not None

    def SelectTargetService(self, servicetype):
        return getattr(self.MembershipList.get(servicetype, None), 'Service', None)

    def SelectBaseMember(self, servicetype, account, type, role):
        hash = Contact.MakeHash(account, type)
        ms = self.SelectTargetMemberships(servicetype)

        return ms.Memberships.get(role, {}).get(hash, None)

    def SelectContactFromAddressBook(self, abid, guid = None):
        if guid is None:
            guid = abid
            return self.SelectContact(guid)
        else:
            contact = self.AddressBookContacts.get(str(abid).lower(), {}).get(guid, None)
            if contact is None:
                return self.SelectContact(guid)

    def Add(self, range):
        for svc in range:
            for role in range[svc]:
                for hash in range[svc][role]:
                    if svc.type not in self.mslist:
                        self.mslist[svc.type] = ServiceMembership(svc)

                    if role not in self.mslist[svc.type].Memberships:
                        self.mslist[svc.type].Memberships[role] = {}

                    if hash in self.mslist[svc.type].Memberships[role]:
                        if mslist[svc.type].Memberships[role][hash].lastChange < range[svc][role][hash].lastChange:
                            mslist[svc.type].Memberships[role][hash] = range[svc][role][hash]
                    else:
                        mslist[svc.type].Memberships[role][hash] = range[svc][role][hash]

    def GetAddressBookLastChange(self, abid = uuid.UUID(int=0)):
        abid = str(abid).lower()
        if self.HasAddressBook(abid):
            return self.AddressBooksInfo[abid].lastChange

        return soap.MinTime

    def SetAddressBookInfo(self, abid, abHeader):
        abid = str(abid).lower()
        mytime = self.GetAddressBookLastChange(abid)
        newtime = abHeader.LastChange
        if mytime > newtime:
            return

        self.SetAddressBookInfoToABInfoList(abid, abHeader)

    def IsContactTableEmpty(self):
        ct = getattr(self, 'contactTable', None)
        if ct is None:
            ct = self.contactTable = {}
        return len(ct) == 0

    def MergeIndividualAddressBook(self, forwardList):
        log.debug("MergeIndividualAddressBook")
        if forwardList.Ab is None:
            log.debug("\tNo AddressBook information in result")
            return

        if SOAPServices.strptime_highres(self.GetAddressBookLastChange(forwardList.Ab.AbId)) > \
            SOAPServices.strptime_highres(forwardList.Ab.LastChange):
            log.debug("\tAddressBook information is out of date (%r > %r)", self.GetAddressBookLastChange(forwardList.Ab.AbId), forwardList.Ab.LastChange)
            return

        if str(forwardList.Ab.AbId).lower() != str(uuid.UUID(int=0)).lower():
            log.debug("\tWrong address book ID")
            return

        scene = Scenario.NONE

        if self.IsContactTableEmpty():
            scene = Scenario.Initial
        else:
            scene = Scenario.DeltaRequest

        # Process groups
        groups = getattr(getattr(forwardList, 'Groups', None), 'Group', [])
        for group in groups:
            key = str(uuid.UUID(str(group.GroupId))).lower()
            if group.FDeleted:
                self.groups.pop(key, None)
                contact_group = self.client.contact_list.GetGroup(group.GroupId)
                if contact_group is not None:
                    self.client.contact_list.GroupRemoved(contact_group)
            else:

                contact_group = Group(id = key,
                                      groupInfo = GroupInfo(name = group.GroupInfo.Name,
                                                            groupType = group.GroupInfo.GroupType,
                                                            IsNotMobileVisible = getattr(group.GroupInfo, 'IsNotMobileVisible', None),
                                                            IsPrivate = getattr(group.GroupInfo, 'IsPrivate', None),
                                                            IsFavorite = getattr(group.GroupInfo, 'IsFavorite', None),
                                                            fMessenger = getattr(group.GroupInfo, 'FMessenger', None),
                                                            )
                )

                self.groups[key] = contact_group
                self.client.contact_list.GroupAdded(group.GroupInfo.Name, group.GroupId, group.GroupInfo.IsFavorite)

        circle_infos = getattr(getattr(getattr(forwardList, 'CircleResult', None), 'Circles', None), 'CircleInverseInfo', None) or []
        modifiedConnections = {}
        newInverseInfos = {}
        newCIDList = {}
        for info in circle_infos:
            abId = str(info.Content.Handle.Id).lower()
            CID = self.SelectWLConnection(abId)
            info = CircleInverseInfo.from_zsi(info)
            if self.HasWLConnection(abId):
                if CID is not None and CID not in modifiedConnections:
                    log.info("Modified connection found: %r", info)
                    modifiedConnections[CID] = info
            else:
                log.info("New circle info found: %r", info)
                newInverseInfos[abId] = info

        transformed_contacts = []

        CL = self.client.contact_list

        for cx in getattr(getattr(forwardList, 'Contacts', None), 'Contact', []):
            contact = self.TransformZSIContact(CL, cx, forwardList.Ab.AbId)
            if contact is None:
                continue
            transformed_contacts.append(contact)

            self.SetContactToAddressBookContactPage(forwardList.Ab.AbId, contact)
            CID = contact.contactInfo.CID
            if self.HasWLConnection(CID):
                modifiedConnections[CID] = self.SelectCircleInverseInfo(self.SelectWLConnectionByCID(CID))
                savedContact = self.SelectContact(CID)
                if savedContact.contactInfo.contactType == MessengerContactType.Circle:
                    if contact.contactInfo.contactType != MessengerContactType.Circle:
                        # Owner deleted circles found
                        log.info("Deleted circles found: %r", savedContact)

                    else:
                        # Removed from the circle
                        log.info("Circle removal found: %r", savedContact)
            else:
                if contact.contactInfo.contactType == MessengerContactType.Circle:
                    state = self.GetCircleMemberRelationshipStateFromNetworkInfo(contact.contactInfo.NetworkInfoList)
                    if state in (RelationshipStates.Accepted, RelationshipStates.WaitingResponse):
                        newCIDList[CID] = str(uuid.UUID(int=CID)).lower()

            if getattr(contact, 'fDeleted', False):
                log.debug("Deleted contact: %r", contact)
                old_contact = self.RemoveContactFromAddressBook(forwardList.Ab.AbId, uuid.UUID(contact.contactId))
                if old_contact is not None:
                    old_contact.RemoveFromList(MSNList.Forward)
                    self.client.contact_list.contact_remove(old_contact, str(MSNList.Forward))
                    old_contact.Guid = uuid.UUID(int=0)
                    old_contact.isMessengerUser = False
                    old_contact.status = 'offline'
                    if not len(old_contact.Lists):
                        self.client.contact_list.Remove(old_contact.Mail, old_contact.ClientType)

            else:

                self.UpdateContact(contact)
                for list in contact.Lists:
                    self.client.contact_list.ContactAdded(contact, list)

        if forwardList.Ab is not None:
            self.SetAddressBookInfo(forwardList.Ab.AbId, forwardList.Ab)

        self.SaveContactTable(transformed_contacts)
        inverse_info = getattr(getattr(getattr(forwardList, 'CircleResult', None), 'Circles', None), 'CircleInverseInfo', None)
        if inverse_info is not None:
            self.SaveCircleInverseInfo(inverse_info)

        log.info("ProcessCircles(%r, %r, %r, %r)", modifiedConnections, newCIDList, newInverseInfos, scene)
        self.ProcessCircles(modifiedConnections, newCIDList, newInverseInfos, scene)

    def TransformZSIContact(self, CL, cx, abid):
        if cx.ContactInfo is None:
            return None

        abid = str(abid).lower()

        info = cx.ContactInfo
        guid = uuid.UUID(cx.ContactId)
        contact = CL.GetContactByGuid(guid)
        if contact is None:
            contact_type = info.ContactType
            clitype = ClientType(contact_type)

            contact_account_name = info.PassportName
            if contact_account_name is None:
                primaryEmailType = info.PrimaryEmailType
                emails = getattr(info.Emails, 'ContactEmail', [])
                for email in emails:
                    if email.ContactEmailType == primaryEmailType:
                        contact_account_name = email.Email
                        break

                    if email.IsMessengerEnabled:
                        contact_account_name = email.Email

                if contact_account_name is None:
                    for email in emails:
                        if email.ContactEmailType in (ContactEmail.Types.Messenger,
                                                      ContactEmail.Types.Messenger2,
                                                      ContactEmail.Types.Messenger3,
                                                      ContactEmail.Types.Messenger4):
                            contact_account_name = email.Email
                            break

                if contact_account_name is None:
                    contact = Contact.from_zsi(cx,
                           abid = abid,
                           account = contact_account_name,
                           type = clitype,
                           client = self.client)

                    log.info("No idea what the contact's account name is is for %r", contact)
                    return

                clitype = ClientType.EmailMember

            contact = Contact.from_zsi(cx,
                                       abid = abid,
                                       account = contact_account_name,
                                       type = clitype,
                                       client = self.client)

            log.info("Got contact: %r", contact)
            CL.contacts[contact.Hash] = contact
        else:
            contact.contactInfo = ContactInfo.from_zsi(info)

        contact.fDeleted = getattr(cx, 'FDeleted', False)

        return contact


    def MergeGroupAddressBook(self, forwardList):

        log.debug("MergeGroupAddressBook(%r)", forwardList)

        if forwardList.Ab is None:
            return
        if forwardList.Ab.AbId == str(uuid.UUID(int=0)):
            return
        if forwardList.Ab.AbInfo.AddressBookType != AddressBookType.Group:
            return
        if SOAPServices.strptime_highres(self.GetAddressBookLastChange(forwardList.Ab.AbId)) > \
            SOAPServices.strptime_highres(forwardList.Ab.LastChange):
            log.debug("\tAddressBook information is out of date (%r > %r)", self.GetAddressBookLastChange(forwardList.Ab.AbId), forwardList.Ab.LastChange)
            return

        self.SetAddressBookInfo(forwardList.Ab.AbId, forwardList.Ab)
        self.SaveAddressBookContactPage(forwardList.Ab.AbId, forwardList.Contacts.Contact)

        circle = self.UpdateCircleFromAddressBook(forwardList.Ab.AbId)

        if circle is None:
            self.RemoveCircleInverseInfo(forwardList.Ab.AbId)
            self.RemoveAddressBookContactPage(forwardList.Ab.AbId)
            self.RemoveAddressBookInfo(forwardList.Ab.AbId)
            return

        log.debug("UpdateCircleMembersFromAddressBookContactPage: circle = %r", circle)
        self.UpdateCircleMembersFromAddressBookContactPage(circle, Scenario.Initial)

        if circle.CircleRole in (CirclePersonalMembershipRole.Admin,
                                 CirclePersonalMembershipRole.AssistantAdmin,
                                 CirclePersonalMembershipRole.Member):
            self.AddCircleToCircleList(circle)
        elif circle.CircleRole == CirclePersonalMembershipRole.StatePendingOutbound:
            self.FireJoinCircleInvitationReceivedEvents(circle)
        else:
            raise Exception("Unknown circleRole: %r", circle.CircleRole)

        if self.IsPendingCreateConfirmCircle(circle.AddressBookId):
            self.FireCreateCircleCompletedEvent(circle)


        log.debug("Got Non-default AddressBook:")
        log.debug("\tId: %r", forwardList.Ab.AbId)
        log.debug("\tName: %r", forwardList.Ab.AbInfo.Name)
        log.debug("\tType: %r", forwardList.Ab.AbInfo.AddressBookType)
        log.debug("\tMembers:")

        transformed_contacts = []
        for contact in forwardList.Contacts.Contact:

            contact = self.TransformZSIContact(circle.contactList, contact, forwardList.Ab.AbId)

            if contact is None:
                log.info("Got none for contact: %r", contact)
                continue
            transformed_contacts.append(contact)

            log.debug("\t\t%r", contact.Hash)

        self.SaveContactTable(transformed_contacts)

    def IsPendingCreateConfirmCircle(self, abid):
        return abid in self.PendingCreateCircleList

    def FireCreateCircleCompletedEvent(self, circle):
        self.RemoveABIdFromPendingCreateCircleList(circle.AddressBookId)
        self.client.contact_list.OnCreateCircle(circle)

    def RemoveABIdFromPendingCreateCircleList(self, abid):
        self.PendingCreateCircleList.pop(abid, None)

    def UpdateCircleMembersFromAddressBookContactPage(self, circle, scene):
        abid = str(circle.AddressBookId).lower()

        if not self.HasAddressBookContactPage(abid):
            return

        newContactList = {}
        oldContactInverseList = {}
        oldContactList = []

        isRestore = bool(scene & Scenario.Restore)

        if not isRestore:
            oldContactList[:] = circle.ContactList.contacts.values()[:]

            for contact in oldContactList:
                oldContactInverseList[contact.getCID()] = contact

        page = self.AddressBookContacts[abid]
        for contact in page.values():
            if not isRestore:
                newContactList[contact.getCID()] = contact

            self.UpdateContact(contact, abid, circle)

        if isRestore:
            return True

        for contact in newContactList.values():
            if contact.contactInfo is None:
                continue

            if contact.getCID() not in oldContactInverseList and \
                circle.contactList.HasContact(contact.contactInfo.passportName, IMAddressInfoType.WindowsLive):

                log.info("CircleMember joined: %r, %r", circle, contact.contactInfo.passportName)
                self.client.on_circle_member_joined(circle, circle.contactList.GetContact(contact.contactInfo.passportName, type = IMAddressInfoType.WindowsLive))

        for contact in oldContactList:
            if contact.getCID() not in newContactList:
                circle.ContactList.remove(contact.Mail, contact.type)
                log.info("CircleMember left: %r, %r", circle, contact.contactInfo.PassportName)
                self.client.on_circle_member_left(circle, contact)

    def SaveAddressBookContactPage(self, abid, contacts):
        abid = str(abid).lower()

        old_contacts = self.AddressBookContacts.get(abid, {})
        new_contacts = self.AddressBookContacts[abid] = {}

        abc = self.AddressBookContacts[abid]

        for c_node in contacts:
            ctype = ClientType(c_node.ContactInfo.ContactType)
            contact = Contact.from_zsi(c_node, abid = abid,
                                       account = c_node.ContactInfo.PassportName,
                                       type = ctype,
                                       client = self.client)
            abc[c_node.ContactId] = contact

#        for old in self.AddressBookContacts:
#            if old not in new_contacts:
#                self.OnContactLeaveCircle(abid, old)

#    def OnContactLeaveCircle(self, abid, contact_id):
#        pass

    def SaveCircleInverseInfo(self, inverseInfoList):
        iil = inverseInfoList
        if iil is not None:
            for circle in iil:
                lowerid = str(circle.Content.Handle.Id).lower()
                #class CircleInverseInfo(pysoap.Serializable):
                #    content = Content
                #    personalInfo = PersonalInfo
                self.CircleResults[lowerid] = CircleInverseInfo.from_zsi(circle)

    def RemoveCircleInverseInfo(self, abid):
        self.CircleResults.pop(str(abid).lower(), None)

    def UpdateCircleFromAddressBook(self, abid):
        abid = str(abid).lower()

        if abid == str(uuid.UUID(int = 0)):
            return

        meContact = self.SelectMeContactFromAddressBookContactPage(abid)
        hiddenCID = self.SelectWLConnection(abid)
        hidden = self.SelectContact(hiddenCID)
        inverseInfo = self.SelectCircleInverseInfo(abid)

        if hidden is None:
            log.warning("Cannot create circle since hidden representative not found in addressbook. ABID = %r", abid)
            return None

        if meContact is None:
            log.warning("Cannot create circle since Me not found in addressbook. ABID = %r", abid)
            return None

        if inverseInfo is None:
            log.warning("Cannot create circle since inverse info not found in circle result list. ABID = %r", abid)
            return None

        circleHash = Circle.MakeHash(abid, inverseInfo.Content.Info.HostedDomain)

        circle = self.client.CircleList.get(circleHash, None)
        if circle is None:
            log.info("Creating circle: %r", circleHash)
            circle = self.CreateCircle(meContact, hidden, inverseInfo)
            self.client.CircleList[circle.Hash] = circle

#        circle.CircleRole = self.GetCircleMemberRoleFromNetworkInfo(circle.contactInfo.networkInfoList)

        return circle

    def CreateCircle(self, me, hidden, inverseInfo):
        if hidden.contactInfo is None:
            log.error("No contact info for hidden contact")
            return
        if len(hidden.contactInfo.NetworkInfoList) == 0:
            log.error("No network info in hidden contact")
            return
        if hidden.contactInfo.contactType != MessengerContactType.Circle:
            log.error("Not a circle contact!")
            return

        return Circle(me, hidden, inverseInfo, self.client)

    def SelectSelfContactGuid(self, abid):
        me = self.SelectSelfContactFromAddressBookContactPage(abid)
        if me is None:
            return None

        return me.contactId

    def SelectSelfContactFromAddressBookContactPage(self, abid):
        return self.SelectSelfContactFromContactList(self.AddressBookContacts.get(abid, {}).values(), self.client.contact_list.owner.Mail)

    def SelectSelfContactFromContactList(self, contacts, username):
        for contact in contacts:
            if getattr(contact, 'contactInfo', None) is None:
                continue

            if getattr(contact.contactInfo, 'passportName', None) == username:
                return contact

        return None

    def SelectMeContactFromAddressBookContactPage(self, abid):
        if not self.HasAddressBookContactPage(abid):
            return None
        return self.SelectMeFromContactList(self.AddressBookContacts[abid].values())

    def SelectMeFromContactList(self, contacts):
        for contact in contacts:
            if getattr(contact, 'contactInfo', None) is not None:
                if contact.contactInfo.contactType == MessengerContactType.Me:
                    return contact

        return None

    def ProcessCircles(self, modifiedConnections, newCIDList, newInverseInfos, scene):
        self.ProcessModifiedCircles(modifiedConnections, scene | Scenario.ModifiedCircles)
        self.ProcessNewConnections(newCIDList, newInverseInfos, scene | Scenario.NewCircles)

    def ProcessNewConnections(self, newCIDs, newInfos, scene):
        added = 0
        pending = 0

        if not newCIDs:
            return added, pending

        CIDs, infos = zip(*dict((x, newInfos.get(newCIDs[x], None)) for x in newCIDs.keys()).items())
        CIDs = filter(None, CIDs)
        infos = filter(None, infos)

        self.SaveWLConnection(CIDs, infos)

        abIds = self.SelectWLConnectionsByCIDs(newCIDs, RelationshipStates.Accepted)
        self.RequestCircles(abIds, RelationshipStates.Accepted, scene)
        added = len(abIds)

        abIds = self.SelectWLConnectionsByCIDs(newCIDs, RelationshipStates.WaitingResponse)
        self.RequestCircles(abIds, RelationshipStates.WaitingResponse, scene)
        pending = len(abIds)

        return added, pending

    def ProcessModifiedCircles(self, modifiedConnections, scene):
        deleted = 0
        reAdded = 0

        connectionClone = modifiedConnections.copy()
        for CID in modifiedConnections.keys():
            hidden = self.SelectContact(CID)
            if (modifiedConnections[CID].Deleted or # User deleted circle
                hidden.contactInfo.contactType != MessengerContactType.Circle or # Circle owner deleted circle
                self.GetCircleMemberRelationshipStateFromNetworkInfo(hidden.contactInfo.NetworkInfoList) == RelationshipStates.Left): # Circle owner removed this user

                self.RemoveCircle(CID, modifiedConnections[CID].Content.Handle.Id)
                connectionClone.pop(CID, None)
                deleted += 1

        if len(connectionClone):
            CIDs, infos = zip(*connectionClone.items())
            self.SaveWLConnection(CIDs, infos)

            abIds = self.SelectWLConnectionsByCIDs(CIDs, RelationshipStates.Accepted)
            self.RequestCircles(abIds, RelationshipStates.Accepted, scene)
            reAdded = len(abIds)

        return deleted, reAdded

    def RemoveCircle(self, CID, circleId):
        if not self.HasWLConnection(CID):
            return

        self.RemoveAddressBookContactPage(circleId)
        self.RemoveAddressBookInfo(circleId)
        self.RemoveCircleInverseInfo(circleId)
        self.BreakWLConnection(CID)

        self.client.circle_removed(Circle.MakeHash(circleId))

    def BreakWLConnection(self, CID):
        if not self.HasWLConnection(CID):
            return
        abid = self.SelectWLConnectionByCID(CID)

        self.WLConnections.pop(CID, None)
        self.WLInverseConnections.pop(abid, None)

    def SaveWLConnection(self, CIDs, inverseList):
        log.info("SaveWLConnection(%r, %r)", CIDs, inverseList)
        if not inverseList:
            return

        if len(CIDs) != len(inverseList):
            return

        for cid, info in zip(CIDs, inverseList):
            self.WLConnections[cid] = str(info.Content.Handle.Id).lower()
            self.WLInverseConnections[self.WLConnections[cid]] = cid

    def GetContactNickName(self, contact):
        annotations = getattr(getattr(getattr(contact, 'ContactInfo', None), 'Annotations', None), 'Annotation', [])
        for anno in annotations:
            if anno.Name == AnnotationNames.AB_NickName:
                return anno.Value

        return u''

    def GetUserTileURLFromWindowsLiveNetworkInfo(self, contact, domainId = 1):
        netinfos = getattr(getattr(getattr(contact, 'ContactInfo', None), 'NetworkInfoList', None), 'NetworkInfo', [])
        for info in netinfos:
            if info.DomainIdSpecified and info.DomainId == domainId:
                if info.UserTileURL:
                    return info.UserTileURL

        return u''

    def GetCircleMemberRelationshipStateFromNetworkInfo(self, infoList, domain = DomainIds.WLDomain, relationship = RelationshipTypes.CircleGroup):
        if not infoList:
            return RelationshipStates.NONE

        for info in infoList:
            if info.RelationshipTypeSpecified and info.DomainIdSpecified and info.RelationshipStateSpecified:
                if info.DomainId == domain and info.RelationshipType == relationship:
                    return RelationshipStates.from_int(info.RelationshipState)

        return RelationshipStates.NONE

    def GetCircleMemberRoleFromNetworkInfo(self, netInfoList):
        return CirclePersonalMembershipRole.from_int(self.GetContactRelationshipRoleFromNetworkInfo(netInfoList, DomainIds.WLDomain, RelationshipTypes.CircleGroup))

    def GetContactRelationshipRoleFromNetworkInfo(self, netInfoList, domainId, relationshipType):
        if not netInfoList:
            return CirclePersonalMembershipRole.NONE

        for info in netInfoList:
            if info.RelationshipTypeSpecified and info.DomainIdSpecified and info.RelationshipRoleSpecified:
                if info.DomainId == domainId and info.RelationshipType == relationshipType:
                    return info.RelationshipRole

#        log.error("Couldn't get CircleMember RelationshipRole from NetworkInfo: %r, %r, %r", netInfoList, domainId, relationshipType)

        return 0

    def GetCircleMemberDisplayNameFromNetworkInfo(self, infoList):
        return self.GetContactDisplayNameFromNetworkInfo(infoList, DomainIds.WLDomain, RelationshipTypes.CircleGroup)

    def GetContactDisplayNameFromNetworkInfo(self, infoList, domainId, relationshipType):
        if not infoList:
            return ''

        for info in infoList:
            displayname = getattr(info, 'DisplayName', '')
            if info.RelationshipTypeSpecified and info.DomainIdSpecified and bool(displayname):
                return displayname

        return ''

    def RequestCircles(self, abids, relationshipState, scenario):
        log.info("RequestCircles: %r, %r, %r", abids, relationshipState, scenario)
        for abid in abids:
            self.client.RequestAddressBookById(abid, relationshipState, scenario)

    def FireJoinCircleInvitationReceivedEvents(self, circle):
        inviter = self.GetCircleInviterFromNetworkInfo(self.SelectContact(self.SelectWLConnection(circle.AddressBookId)))

        if inviter is None:
            log.error("Inviter for circle is None: %r", circle)
            return

        log.info("Inviter for circle found: %r (circle = %r)", inviter, circle)

        if circle.AddressBookId not in self.PendingAcceptionCircleList:
            self.PendingAcceptionCircleList[circle.AddressBookId] = circle
            self.client.OnCircleInvite(circle, inviter)
        else:
            log.info("Already asked about circle this session (%r)", circle.AddressBookId)

    def AddCircleToCircleList(self, circle):
        self.client.CircleList[circle.Hash] = circle
        if circle.AddressBookId in self.PendingAcceptionCircleList:
            self.client.OnJoinCircle(circle)
        else:
            self.client.OnRecvCircle(circle)

        if circle.ADLCount <= 0:
            circle.ADLCount = 1

        self.PendingAcceptionCircleList.pop(circle.AddressBookId, None)

    def SetContactPhones(self, contact, info):
        for phone in getattr(getattr(info, 'phones', None), 'phone', []):
            if phone.ContactPhoneType1 == ContactPhone.Types.Mobile:
                contact.MobilePhone = phone.number
            elif phone.ContactPhoneType1 == ContactPhone.Types.Personal:
                contact.HomePhone = phone.number
            elif phone.ContactPhoneType1 == ContactPhone.Types.Business:
                contact.WorkPhone = phone.number

    def GetCircleInviterFromNetworkInfo(self, contact):

        if len(contact.contactInfo.NetworkInfoList) == 0:
            return None

        for networkInfo in contact.contactInfo.NetworkInfoList:
            if networkInfo.DomainId != 1:
                continue
            InviterCID = getattr(networkInfo, 'InviterCID', None)
            if InviterCID is not None:
                inviter = self.SelectContact(InviterCID)
                if inviter is None:
                    return None
                inviterEmail = inviter.contactInfo.passportName
            else:
                inviterEmail = networkInfo.InviterEmail

            return CircleInviter(inviterEmail, networkInfo.InviterMessage, client = self.client)

        return None

def _main():
    class A(pysoap.Serializable):
        pass
    class B(pysoap.Serializable):
        a = A
    class C(pysoap.Serializable):
        b = [B]
    class D(pysoap.Serializable):
        x = {'' : {'' : A}}
        c = C

    data = \
    {"x":
     {"test": {"a-": {'foo':'bar'}, "this": {'spam':'eggs'}},
      "test2": {"another": {'steak': 'potatos'}}},
     "c":
      {"b":
       [{"a": {"y": 2, "x": 1, "z": 3},
         "fruit": True},
        {"a": {"vegetable": False}}],
       "whatever": "something"}}

    deserialized = D.deserialize(data)
    print deserialized
    serialized = deserialized.serialize()
    print serialized
    print json.loads(serialized) == data

if __name__ == '__main__':
    _main()
