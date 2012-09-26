'''
A partial translation/implementation of hotmail's object heirarchy RPC system.
Original source: http://gfx6.hotmail.com/mail/13.1.0132.0805/wlmcore{N}.js (for N from 1-4)
'''

import random
import logging
import digsbysite
import common.asynchttp as asynchttp
import re
import util
import util.net as net
import util.primitives.funcs as funcs
import util.callbacks as callbacks
import weakref

import uuid

def ntok():
    return str(random.randint(0, 0x7fffffff))

log = logging.getLogger('hotmail.ajax')

def Flags(*args):
    return util.Storage(zip(args[::2], args[1::2]))

# Known released builds:
#  1 - indicates anything prior to 13.3.3227.0707
#  13.3.3227.0707
#  15.1.3020.0910
#  15.3.2495.0616        # Unreleased outside of microsoft as far as we know
#  15.3.2506.0629        # Windows Live Mail / Bing
#  15.4.0327.1028        # Detected on 2010-Nov-03. No changes to API.
#  15.4.0332.1110        # Detected on 2010-Nov-18. No changes to API.
#  15.4.3057.0112        # Detected on 2011-Jan-20. No changes to API.
#  15.4.3079.0223        # Detected on 2011-Mar-25. No changes to API.
#  15.4.3096.0406        # Detected on 2011-Apr-18. No changes to API.
#  16.0.1635.0608        # Detected on 2011-Jun-17. Lots of changes
#  16.2.2978.1206        # Detected on 2011-Dec-16. There don't seem to be any changes to the API, but the content of the page has changed.
#  16.2.4514.0219        # Detected on 2012-Mar-21.
#  16.2.6151.0801        # Detected on 2012-Sep-13. No changes to API


XMLPost = 0
null = None

import collections
_versioned_classes = collections.defaultdict(dict)

def ForBuild(buildnum, clsname = None):
    def decorator(cls):
        _versioned_classes[clsname or cls.__name__][buildnum] = cls
        return cls
    return decorator

class FppParamType(object):
    String = "_string",
    Date = "_date",
    Array = "_array",
    oArray = "_oArray",
    Primitive = "_primitive",
    Object = "_object",
    Enum = "_enum",
    Custom = "_custom"

class TypeSystem(object):
    _isFppObject = True
    _default = None
    def __init__(self, name_or_type, name=None, val=None):
        if name is not None:
            type = name_or_type
            name = name
        else:
            type = FppParamType.Custom
            name = name_or_type

        self.name = name
        self.type = type
        self.value = val

    @staticmethod
    def escape(instance):
        f = {'_string'    : FppProxy.escape,
             '_date'      : lambda a: a, #FppProxy.dateToISO8601,
             '_array'     : FppProxy.arrayToString,
             '_oArray'    : FppProxy.objToStringImpl,
             '_object'    : FppProxy.objToStringImpl,
             '_primitive' : FppProxy.primitiveToString,
             '_enum'      : lambda a: str(a), }.get(funcs.get(instance, 'type', None), FppProxy.objToString)

        escaped_val = f(funcs.get(instance, 'value', None))
        if escaped_val is None:
            return 'null'
        return escaped_val

    def __str__(self):
        return '<TypeSystem %r>' % self.name

    def toString(self):
        return TypeSystem.escape(self)

    @classmethod
    def default(cls):
        x = cls('')
        if cls._default is None:
            x.value = None
        else:
            x.value = type(cls._default)(cls._default)
        return x

class NamedTypeSystem(TypeSystem):
    def __init__(self, name, val = None):
        TypeSystem.__init__(self, type(self).__name__, name, val)

class _string(NamedTypeSystem):
    _default = ''
class _array(NamedTypeSystem):
    _default = []
class _enum(NamedTypeSystem):
    _default = 0
class _primitive(NamedTypeSystem):
    _default = False
class _oArray(NamedTypeSystem):
    _default = {}
class _object(NamedTypeSystem):
    _default = {}
_custom = TypeSystem

class FppProperty(object):
    def __init__(self, name, typ, default = Sentinel):
        self._name = name
        self._type = typ

        if default is not Sentinel:
            self._default = FppMetaclass._classes[self._type](name)
            self._default.value = default # or .value = default

    def __get__(self, obj, objtype):
        default = getattr(self, '_default', FppMetaclass._classes[self._type].default())
        if obj is None: # Getting the attribute from a class (not instance). Return default
            return default

        if not hasattr(obj, '_field_%s' % self._name):
            setattr(obj, '_field_%s' % self._name, default)

        val = getattr(obj, '_field_%s' % self._name)
        if getattr(val, 'type', None) != self._type:
            if val is None or val._isFppObject:
                return val
            raise ValueError("%r has an invalid %r (with type = %r, value = %r)", obj, self._name, val.type, val.value)
        return val

    def __set__(self, obj, val):
        if (val is not None and getattr(val, 'value', None) is not None) and hasattr(val, 'type'):
            if val.type != self._type:
                raise TypeError("%r must have type %r for the %r field. Got %r (value = %r) instead.",
                                obj, self._type, self._name, val.type, val.value)
        elif val is None or getattr(val, '_isFppObject', False):
            pass
        else:
            x = FppMetaclass._classes[self._type].default()
            x.value = val
            val = x

        setattr(obj, '_field_%s' % self._name, val)

class FppMetaclass(type):
    _classes = {'_enum' : _enum,
                '_string': _string,
                '_array' : _array,
                '_primitive': _primitive,
                '_object' : _object,
                '_oArray' : _oArray,
                '_custom' : TypeSystem,
                }
    def __init__(cls, name, bases, dict):
        for field in cls._fields_:
            setattr(cls, field[0], FppProperty(*field))

        @classmethod
        def default(_cls):
            i = cls()
            for _field in i._fields_:
                if len(_field) == 2:
                    _default = FppMetaclass._classes[_field[1]].default()
                elif len(_field) == 3:
                    if _field[2] is None:
                        _default = None
                    else:
                        _default = FppMetaclass._classes[_field[1]](_field[2])
                setattr(i, _field[0], _default)
            return i

        dict['default'] = default
        FppMetaclass._classes[name] = cls
        cls.default = default
        cls._isFppObject = True
        type.__init__(cls, name, bases, dict)

class FppClass(object):
    _fields_ = []
    __metaclass__ = FppMetaclass

    def __init__(self, *args, **kwds):
        fieldnames = []
        for field in self._fields_:
            if len(field) == 3:
                setattr(self, field[0], field[2])
            else:
                setattr(self, field[0], FppMetaclass._classes[field[1]].default())

            fieldnames.append(field[0])

        for i in range(len(args)):
            setattr(self, self._fields_[i][0], args[i])

        for key in kwds:
            setattr(self, key, kwds[key])

    def __str__(self):
        res = ['{']
        for field in self._fields_:
            cls = FppMetaclass._classes[field[1]]
            val = getattr(self, field[0])
            if val is None:
                res.append('null')
            else:
                res.append(cls.escape(val))
            res.append(',')
        if res[ - 1] == ',':
            res.pop(- 1)

        res.append('}')
        return ''.join(res)

    toString = escape = __str__
    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, ' '.join('%s=%r' % (entry[0], getattr(self, entry[0], None)) for entry in self._fields_))

class FppError(FppClass):
    _fields_ = [
        ('ErrorCode', '_string'),
        ('Message', '_string'),
        ('ErrorObj', '_object'),
        ('StackTrace', '_string'),
        ]

class FppReturnPackage(FppClass):
    _fields_ = [
        ('Status', '_enum'),
        ('Value', '_object'),
        ('OutRefParams', '_oArray'),
        ('Error', 'FppError'),
        ('ProfilingInfo', '_object'),
        ]

@ForBuild('1')
class InboxUiData(FppClass):
    _fields_ = [
        ('FolderListHtml', '_string'),
        ('MessageListHtml', '_string'),
        ('MessageHtml', '_string'),
        ('RedirectUrl', '_string'),
        ]

@ForBuild('13.3.3227.0707')
class InboxUiData(FppClass):
    _fields_ = [
        ('FolderListHtml', '_string'),
        ('MessageListHtml', '_string'),
        ('MessageHtml', '_string'),
        ('InfoPaneHtml', '_string'),
        ('RedirectUrl', '_string'),
    ]

@ForBuild("15.3.2495.0616")
class InboxUiData(FppClass):
    _fields_ = [
        ('FolderListHtml', '_string'),
        ('QuickViewListHtml', '_string'),
        ('MessageListHtml', '_string'),
        ('MessageHtml', '_string'),
        ('SuggestionHtml', '_string'),
        ('BatchInfo', 'BatchInfo'),
        ('MltRootHtml', '_string'),
        ('MltSubHtml', '_string'),
        ('InfoPaneHtml', '_string'),
        ('RedirectUrl', '_string'),
        ('Content', '_object'),
        ('BiciJsonConfig', '_string')
    ]

@ForBuild("16.0.1635.0608")
class InboxUiData(FppClass):
    _fields_ = [
        ('FolderListHtml', '_string'),
        ('QuickViewListHtml', '_string'),
        ('MessageListHtml', '_string'),
        ('MessageHtml', '_string'),
        ('ItemInfo', 'ItemResponseInfo'),
        ('SuggestionHtml', '_string'),
        ('BatchInfo', 'BatchInfo'),
        ('MltRootHtml', '_string'),
        ('MltSubHtml', '_string'),
        ('InfoPaneHtml', '_string'),
        ('RedirectUrl', '_string'),
        ('Content', '_object'),
        ('BiciJsonConfig', '_string'),
        ]

@ForBuild('16.2.2978.1206')
class InboxUiData(FppClass):
    _fields_ = [
        ('FolderListHtml', '_string'),
        ('QuickViewListHtml', '_string'),
        ('MessageListHtml', '_string'),
        ('MessageHtml', '_string'),
        ('ItemInfo', 'ItemResponseInfo'),
        ('SuggestionHtml', '_string'),
        ('BatchInfo', 'BatchInfo'),
        ('MltRootHtml', '_string'),
        ('MltSubHtml', '_string'),
        ('Categories', '_array'),
        ('InfoPaneHtml', '_string'),
        ('RedirectUrl', '_string'),
        ('Content', '_object'),
        ('BiciJsonConfig', '_string'),
        ]

class HmCandidacyInfo(FppClass):
    _fields_ = [
        ('Status', '_enum'),
        ('Guid', '_string'),
        ('ShowMakeLiveContact', '_enum'),
        ]

@ForBuild('1')
class HmAuxData(FppClass):
    QueryArgName = 'Aux'
    _fields_ = [
        ('Value', '_string'),
        ("LiveContactCandidacyInfo", 'HmCandidacyInfo')
        ]

    @classmethod
    def for_msg(cls, msg):
        return cls(Value = msg._mad.replace('||', '|'),
                   LiveContactCandidacyInfo = None)

@ForBuild('15.1.3020.0910')
class HmAuxData(FppClass):
    QueryArgName = 'Aux'
    _fields_ = [
        ('Value', '_string'),
        ]

    @classmethod
    def for_msg(cls, msg):
        if msg._mad in (None, ""):
            return ""
        return cls(Value = msg._mad)

@ForBuild('16.0.1635.0608')
class ItemResponseInfo(FppClass):
    _fields_ = [
        ('IsConversation', '_primitive'),
        ('View', '_enum'),
        ('ConversationId', '_string'),
        ('MessageId', '_string'),
        ('MessageIds', '_array'),
        ('SenderEmails', '_array'),
        ('IsDedup', '_primitive'),
        ('IdentityContext', '_string'),
        ('PsaType', '_enum'),
        ('PsaUrl', '_string'),
        ('ReadInstrumentation', '_object'),
        ('Html', '_string'),
        ]

@ForBuild('1') # I don't know the build number of the old version of livemail, but this will let the class get used correctly (if it's still necessary)
class MessageRenderingInfo(FppClass):
    _fields_ = [
        ('MessageId', '_string'),
        ('FolderId', '_string'),
        ('OpenMessageBody', '_primitive', True),
        ('AllowUnsafeContent', '_primitive', False),
        ('OverrideCodepage', '_primitive', -1,),
        ('HmAuxData', "HmAuxData"),
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive', False),
        ('Action', '_enum'),
        ]

    def __init__(self, **k):

        if 'AuxData' in k:
            k['HmAuxData'] = k.pop('AuxData')

        FppClass.__init__(self, **k)

@ForBuild('13.3.3227.0707')
class MessageRenderingInfo(FppClass):
    _fields_ = [
        ('MessageId', '_string'),
        ('FolderId', '_string'),
        ('OpenMessageBody', '_primitive', True),
        ('AllowUnsafeContent', '_primitive', False),
        ('OverrideCodepage', '_primitive', -1),
        ('UnknownArgument', '_primitive', None),          # recently added
        ('HmAuxData', "HmAuxData"),
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive'),
        ('Action', '_enum'),
        ('UnknownArgument2', '_primitive', True),         # recently added
        ]

    def __init__(self, **k):

        if 'AuxData' in k:
            k['HmAuxData'] = k.pop('AuxData')

        FppClass.__init__(self, **k)

@ForBuild("15.3.2495.0616")
class MessageRenderingInfo(FppClass):
    _fields_ = [
       ('MessageId', '_string'),
       ('AllowUnsafeContent', '_primitive'),
       ('OverrideCodepage', '_primitive', -1),
       ('MtLang', '_string'),
       ('AuxData', 'HmAuxData'),
       ('ConversationUpsell', '_primitive'),
       ('FolderId', '_string'),
       ('MarkAsRead', '_primitive', True),
       ('SenderEmail', '_string')
       ]

    def __init__(self, **k):

        if 'HmAuxData' in k:
            k['AuxData'] = k.pop('HmAuxData')

        FppClass.__init__(self, **k)

@ForBuild('15.3.2495.0616')
class AdvancedSearch(FppClass):

    _fields_ = [
        ('Keywords', '_string'),
        ('From', '_string'),
        ('To', '_string'),
        ('Subject', '_string'),
        ('Folder', '_string'),
        ('DateBegin', '_string'),
        ('DateEnd', '_string'),
        ('HasAttachment', '_primitive')
        ]

@ForBuild('1')
class MessageListRenderingInfo(FppClass):
    _fields_ = [
        ('FolderId', '_string'),
        ('PageSize', '_primitive', 25),
        ('PageDirection', '_enum', 'FirstPage'),
        ('PageSkip', '_primitive', 0),
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive'),
        ('AnchorMessageId', '_string', str(uuid.UUID(int=0))),
        ('AnchorMessageDate', '_string'),
        ('PageNumCurrent', '_primitive', 1),
        ('PageNumMidStart', '_primitive', 2),
        ('IsSearchResults', '_primitive'),
        ('SearchKeyword', '_string'),
        ('IsRtl', '_primitive'),
        ('MessageCount', '_primitive', 99),
        ]

@ForBuild('13.3.3227.0707')
class MessageListRenderingInfo(FppClass):
    _fields_ = [
        ('FolderId', '_string'),
        ('PageDirection', '_enum', 'FirstPage'),
        ('PageSkip', '_primitive', 0),
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive'),
        ('AnchorMessageId', '_string', str(uuid.UUID(int=0))),
        ('AnchorMessageDate', '_string'),
        ('PageNumCurrent', '_primitive', 1),
        ('PageNumMidStart', '_primitive', 2),
        ('IsSearchResults', '_primitive'),
        ('SearchKeyword', '_string'),
        ('MessageCount', '_primitive', 99),
        ('AutoSelectMessageIndex', '_primitive', -1),
        ('ReadingPaneLocation', '_enum', 'None'),
        ]


@ForBuild("15.3.2495.0616")
class MessageListRenderingInfo(FppClass):
    _fields_ = [
        ('FolderId', '_string'),
        ('QuickViewId', '_primitive', None),
        ('FilterId', '_primitive', None),
        ('PageDirection', '_enum', 'FirstPage'),
        ('ExtraFetchCount', '_primitive', 99),
        ('PageNumCurrent', '_primitive', 1),
        ('AnchorId', '_string', str(uuid.UUID(int=0))),
        ('AnchorDate', '_string', ""),
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive', False),
        ('IsSearchResults', '_primitive', False),
        ('SearchKeyword', '_string', ""),
        ('AdvancedSearch', 'AdvancedSearch', None),
        ('AutoSelectMessageIndex', '_primitive', -1),
        ('ReadingPaneLocation', '_enum', 'Off'),
        ('MessageCount', '_primitive', -1),
        ('BulkSelectAllTimestamp', '_string', None),
        ('LastUpdateTimestamp', '_string', None)
        ]

@ForBuild("15.4.0317.0921")
class MessageListRenderingInfo(FppClass):
    _fields_ = [
        ('FolderId', '_string'),
        ('QuickViewId', '_primitive', null),
        ('FilterId', '_primitive', null),
        ('PageDirection', '_enum', 'FirstPage'),
        ('ExtraFetchCount', '_primitive', 5),
        ('PageNumCurrent', '_primitive', 1),
        ('AnchorId', '_string', str(uuid.UUID(int=0))),
        ('AnchorDate', '_string', null),
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive', False),
        ('IsSearchResults', '_primitive'),
        ('SearchKeyword', '_string', null),
        ('AdvancedSearch', 'AdvancedSearch', null),
        ('AutoSelectMessageIndex', '_primitive', -1),
        ('ReadingPaneLocationMember', '_enum', 'Off'),
        ('NumberOfMessages', '_primitive', -1),
        ('BulkSelectAllTimestamp', '_string', null),
        ('LastUpdateTimestamp', '_string', null),
        ('IsFavoriteSelected', '_primitive', False),
        ]

@ForBuild('16.0.1635.0608')
class MessageListRenderingInfo(FppClass):
    _fields_ = [
        ('FolderId', '_string'),
        ('QuickViewId', '_primitive', null),
        ('FilterId', '_primitive', null),
        ('PageDirection', '_enum', 'FirstPage'),
        ('ExtraFetchCount', '_primitive', 5),
        ('PageNumCurrent', '_primitive', 1),
        ('AnchorId', '_string', str(uuid.UUID(int=0))),
        ('AnchorDate', '_string', ''),
        ('JumpToAnchor', '_string', null),        # New
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive', False),
        ('IsSearchResults', '_primitive', False),
        ('SearchKeyword', '_string', ''),
        ('AdvancedSearch', 'AdvancedSearch', null),
        ('AutoSelectMessageIndex', '_primitive', -1),
        ('ReadingPaneLocationMember', '_enum', 'Right'),
        ('NumberOfMessages', '_primitive', -1),
        ('BulkSelectAllTimestamp', '_string', null),
        ('LastUpdateTimestamp', '_string', null),
        ('IsFavoriteSelected', '_primitive', True),
        ]

@ForBuild('16.2.2978.1206')
class MessageListRenderingInfo(FppClass):
    _fields_ = [
        ('FolderId', '_string'),
        ('QuickViewId', '_primitive', null),
        ('FilterId', '_primitive', null),
        ('PageDirection', '_enum', 'FirstPage'),
        ('ExtraFetchCount', '_primitive', 5),
        ('PageNumCurrent', '_primitive', 1),
        ('AnchorId', '_string', str(uuid.UUID(int=0))),
        ('AnchorDate', '_string', ''),
        ('JumpToAnchor', '_string', null),        # New
        ('SortKey', '_enum', 'Date'),
        ('SortAsc', '_primitive', False),
        ('IsSearchResults', '_primitive', False),
        ('SearchKeyword', '_string', ''),
        ('AdvancedSearch', 'AdvancedSearch', null),
        ('AutoSelectMessageIndex', '_primitive', -1),
        ('ServerAutoSelectMessageIndex', "_primitive", -1),
        ('InitializeAutoSelectIndexesToFirstMessage', '_primitive', False),
        ('ReadingPaneLocationMember', '_enum', 'Right'),
        ('NumberOfMessages', '_primitive', -1),
        ('BulkSelectAllTimestamp', '_string', null),
        ('LastUpdateTimestamp', '_string', null),
        ('IsFavoriteSelected', '_primitive', True),
        ]

class HmSimpleMsg(FppClass):
    _fields_ = [
        ('IsBlocking', '_primitive'),
        ('YesCode', '_primitive'),
        ('NoCode', '_primitive'),
        ('Message', '_string'),
        ]

class __2(FppClass):
    _fields_ = [
        ('IsBlocking', '_primitive'),
        ('YesCode', '_primitive'),
        ('NoCode', '_primitive'),
        ('Message', '_string'),
        ]

class __5(FppClass):
    _fields_ = [
      ("ExistingContacts", "_array"),
      ("PotentialContacts", "_array"),
      ("HasExistingContacts", "_primitive"),
      ("HasPotentialContacts", "_primitive"),
      ]

class __0(FppClass):
    _fields_ = [
('Url', '_string'), ('CommandCode', '_primitive'), ('Text', '_string')]

class __1(FppClass):
    _fields_ = [
                ('MessageType', '_enum'),
                ('InfoCode', '_primitive'),
                ('Message', '_string'),
                ('ExtendedMessage', '_string'),
                ('PSValue', '_string')
                ]

class __3(FppClass):
    _fields_ = [
                ('FileName', '_string'),
                ('FileId', '_string'),
                ('Success', '_primitive'),
                ('ShowMessage', '_primitive'),
                ('ErrorCode', '_primitive')]

class ABContact(FppClass):
    _fields_ = [
                ('DisplayName', '_string'),
                ('PreferredEmail', '_string'),
                ('ContactType', '_enum'),
                ('PassportName', '_string'),
                ('Guid', '_string'),
                ('IsMessengerUser', '_primitive'),
                ('IsFavorite', '_primitive'),
                ('Cid', '_string'),
                ('Emails', '_array'),
                ('GleamState', '_enum')]

class ABDetailedContact(FppClass):
    _fields_ = [
                ('ContactType', '_enum'),
                ('FirstName', '_string'),
                ('LastName', '_string'),
                ('PassportName', '_string'),
                ('NickName', '_string'),
                ('Comment', '_string'),
                ('IsMessengerUser', '_primitive'),
                ('IsSmtpContact', '_primitive'),
                ('IsFavorite', '_primitive'),
                ('Emails', '_array'),
                ('Phones', '_array'),
                ('Locations', '_array'),
                ('WebSites', '_array'),
                ('Dates', '_array'),
                ('Guid', '_string'),
                ('Cid', '_string')]

class ABGroup(FppClass):
    _fields_ = [
                ('Guid', '_string'),
                ('QuickName', '_string')
                ]

class ABDetailedGroup(FppClass):
    _fields_ = [('Guid', '_string'), ('QuickName', '_string'), ('Count', '_primitive')]

class __4(FppClass):
    _fields_ = [
                ('Groups', '_array'),
                ('Contacts', '_array'),
                ('FileAs', '_enum'),
                ('SelectedGuid', '_string'),
                ("SelectedGroup", 'ABDetailedGroup'),
                ('SelectedContact', 'ABDetailedContact'),
                ('HasSelectedGuid', '_primitive'),
                ('HasSelectedGroup', '_primitive')]

class ABEmail(FppClass):
    _fields_ = [('Type', '_enum'), ('Email', '_string')]

class ABPhone(FppClass):
    _fields_ = [('Type', '_enum'), ('Phone', '_string')]

class ABLocation(FppClass):
    _fields_ = [
                ('Name', '_string'),
                ('Street', '_string'),
                ('City', '_string'),
                ('State', '_string'),
                ('Country', '_string'),
                ('PostalCode', '_string')]

class ABDate(FppClass):
    _fields_ = [('Day', '_string'), ('Month', '_string')]

class ABWebSite(FppClass):
    _fields_ = []

class __6(FppClass):
    _fields_ = [('MailboxSize', '_string'), ('MailboxQuota', '_string')]

class __7(FppClass):
    _fields_ = [
                ('FolderId', '_string'),
                ('Name', '_string'),
                ('Icon', '_string'),
                ('UnreadMessagesCount', '_primitive'),
                ('TotalMessagesCount', '_primitive'),
                ('Size', '_string'),
                ('IsSystem', '_primitive'),
                ('IsHidden', '_primitive'),
                ('FolderType', '_enum'),
                ('SystemFolderType', '_enum')]


class __8(FppClass):
    _fields_ = [('Name', '_string'), ('Address', '_string'), ('EncodedName', '_string')]

class __9(FppClass):
    _fields_ = [('Name', '_string')]

class __10(FppClass):
    _fields_ = [
                ('SenderIDResult', '_enum'),
                ('SenderEmail', '__8'),
                ('IsKnownSender', '_primitive'),
                ('ListUnsubscribeEmail', '_string'),
                ('IsSenderInContactList', '_primitive')]

class __12(FppClass):
    _fields_ = [
                ('DidSenderIDPass', '_primitive'),
                ('DidSenderIDFail', '_primitive'),
                ('IsBlockAvailableInBL', '_primitive'),
                ('IsSameDomainInBL', '_primitive'),
                ('IsSafeListDomain', '_primitive'),
                ('IsMailingList', '_primitive'),
                ('IsSenderHeaderPresent', '_primitive'),
                ('IsListUnsubscribePresent', '_primitive'),
                ('IsListUnsubscribeInEmailFormat', '_primitive'),
                ('HasReachedMaxFilterLimit', '_primitive'),
                ('IsNeverAllowOrBlockDomain', '_primitive'),
                ('IsBlockSenderException', '_primitive')]

class __13(FppClass):
    _fields_ = [
                ('IsFromPRAOnBlockList', '_primitive'),
                ('HasReachedSafeListLimit', '_primitive'),
                ('HasEntriesFromSameDomainInSafeList', '_primitive'),
                ('IsDomainSafe', '_primitive'),
                ('IsSingleToAndNotRecipient', '_primitive'),
                ('HasFilterToJunkToAddress', '_primitive'),
                ('IsRecipientAddressRFCCompliant', '_primitive'),
                ('HasReachedMailingListLimit', '_primitive'),
                ('IsNeverAllowOrBlockDomain', '_primitive'),
                ('IsInContacts', '_primitive')]

class __14(FppClass):
    _fields_ = [
                ('Action', '_enum'),
                ('Reason', '_string'),
                ('CalendarEventUrl', '_string'),
                ('Subject', '_string'),
                ('To', '_string'),
                ('Where', '_string'),
                ('When', '_string')]

class __16(FppClass):
    _fields_ = [
        ('Header', '__22'),
        ('Body', '_string'),
        ('Attachments', '_array'),
        ('ToLineString', '_string'),
        ('CCLineString', '_string'),
        ('BccLineString', '_string'),
        ('Rfc822References', '_string'),
        ('Rfc822MessageId', '_string'),
        ('Rfc822InReplyTo', '_string'),
        ('DateSentLocal', '_string'),
        ('DateReceivedLocal', '_string'),
        ('SafetyLevel', '_enum'),
        ("MailSenderInfo", '__10'),
        ("MeetingResponseInfo", '__14'),
        ('MeetingIcalId', '_string'),
        ('ReplyFromAddress', '_string'),
        ('HasPhishingLinks', '_primitive'),
        ('IsVerifiedMail', '_primitive'),
        ('AllowUnsafeContentOverride', '_primitive'),
        ('UnsafeContentFiltered', '_primitive'),
        ('UnsafeImagesFiltered', '_primitive'),
        ('DetectedCodePages', '_array'),
        ('CurrentCodePage', '_primitive'),
        ('DraftId', '_string')
        ]

class __17(FppClass):
    _fields_ = [
        ('ContentType', '_string'),
        ('Name', '_string'),
        ('Size', '_string'),
        ('BodyIndex', '_primitive'),
        ('AttachmentIndex', '_primitive'),
        ('ForwardId', '_string')
        ]

class __18(FppClass):
    _fields_ = [('EOF', '_primitive')]

class __19(FppClass):
    _fields_ = [('Prefix', '_string'), ('Text', '_string')]

class __21(FppClass):
    _fields_ = [
        ('MessageId', '_string'),
        ('IsRead', '_primitive'),
        ('TimeStamp', '_string'),
        ('IsDraft', '_primitive'),
        ('CP', '_primitive'),
        ('AllowUnsafeContent', '_primitive'),
        ('IsVoicemail', '_primitive'),
        ('IsCalllog', '_primitive'),
        ('IsPrivateVoicemail', '_primitive'),
        ('IsMeetingReq', '_primitive')]

class __22(FppClass):
    _fields_ = [
        ('AuxData', 'HmAuxData'),
        ('MessageId', '_string'),
        ('OriginalMessageId', '_string'),
        ('FolderId', '_string'),
        ('ExtendedType', '_enum'),
        ('TypeData', '_enum'),
        ('IsRead', '_primitive'),
        ('PopSettingIndex', '_primitive'),
        ('OriginalReplyState', '_enum'),
        ('IsInWhiteList', '_primitive'),
        ('SentState', '_enum'),
        ('MessageSize', '_string'),
        ('HasAttachments', '_primitive'),
        ('From', '__8'),
        ('Subject', '__19'),
        ('DateReceivedUTC', '_date'),
        ('DateReceived', '_date'),
        ('Importance', '_enum'),
        ('IsDraft', '_primitive'),
        ('Marker', '__18'),
        ('MessageSizeString', '_string'),
        ('DateReceivedLocal', '_string'),
        ('TimeStamp', '_string')]


class BootstrapSeed(FppClass):
    _fields_ = [
        ('Mode', '_enum'),
        ('FolderId', '_string'),
        ('messageId', '_string'),
        ('count', '_primitive'),
        ('ascendingOrder', '_primitive'),
        ('pageSize', '_primitive'),
        ('totalMessages', '_primitive'),
        ('renderHtml', '_primitive'),
        ('returnHeaders', '_primitive'),
        ('sortBy', '_enum')]

class __23(FppClass):
    _fields_ = [
        ('User', '_string'),
        ('UserName', '_string'),
        ('Timestamp', '_string'),
        ('Configuration', '__26'),
        ('Folders', '_array'),
        ('MessageInfo', '__24'),
        ('TodayPage', '_string')]


class __24(FppClass):
    _fields_ = [
        ('MessageListHtml', '_string'),
        ('Headers', '_array'),
        ('HeaderTags', '_array'),
        ('MessageHtml', '_string'),
        ('SelectedFolderId', '_string'),
        ('SelectedMessageIndex', '_primitive'),
        ('IsPlainText', '_primitive'),
        ('OverrideCodePage', '_primitive'),
        ('AllowUnsafeContent', '_primitive')]

class __25(FppClass):
    _fields_ = [
        ('Signature', '_string'), ('FromAddresses', '_array')]

class __26(FppClass):
    _fields_ = [
        ('DefaultMsgsInListView', '_primitive'),
        ('KeyboardPressesDelay', '_primitive'),
        ('CachePagesOfMessageHeaders', '_primitive'),
        ('EnableReadingPane', '_primitive'),
        ('HasAcceptedJunkReporting', '_primitive'),
        ('JunkReportingUISeen', '_primitive'),
        ('DefaultContactsInListview', '_primitive'),
        ('SpacesContactBindingEnabled', '_primitive'),
        ('DoSpellCheckAsYouType', '_primitive'),
        ('SpellCheckEnabledInLocale', '_primitive'),
        ('ReadingPaneConfiguration', '_enum'),
        ('AutoSelectMessage', '_primitive'),
        ('MinimumIntervalBetweenSpellChecks', '_primitive'),
        ('UserThemeID', '_primitive'),
        ('SaveSentMessages', '_primitive'),
        ('BalloonTipsEnabled', '_primitive'),
        ('BalloonTipUserPreference', '_primitive'),
        ('IsBigInbox', '_primitive'),
        ('IsAdsDown', '_primitive'),
        ('ForwardingOn', '_primitive')]

class __27(FppClass):
    _fields_ = [('ErrorCode', '_string'), ('Folders', '_array'), ('Headers', '_array')]

@ForBuild("15.3.2495.0616")
class BatchInfo(FppClass):
    _fields_ = [
        ('AnchorDate', '_string'),
        ('AnchorId', '_string'),
        ('ProcessedCount', '_primitive'),
        ('IsLastBatch', '_primitive'),
        ('Timestamp', '_string'),
        ('SenderSearch', '_string')
        ]

@ForBuild("15.3.2495.0616")
class ConversationRenderingInfo(FppClass):
    _fields_ = [
        ('ConversationId', '_string'),
        ('MessageId', '_string'),
        ('FolderId', '_string'),
        ('MarkAsRead', '_primitive', True),
        ('SenderEmail', '_string')
        ]

@ForBuild("15.3.2495.0616")
class MessagePartsUiData(FppClass):
    _fields_ = [
        ('MessagePartData', '_object'),
        ('IdentityContext', '_string'),
        ('InfoPaneHtml', '_string'),
        ('RedirectUrl', '_string'),
        ('Content', '_object'),
        ('BiciJsonConfig', '_string')
        ]

@ForBuild('15.3.2495.0616')
class HMLiveViewRequestObject(FppClass):
    _fields_ = [
        ('Id', '_string'),
        ('Sender', '_string'),
        ('Type', '_string'),
        ('SubType', '_string'),
        ('Data', '_string')
        ]

@ForBuild("15.4.0317.0921")
class HMLiveViewRequestObject(FppClass):
    _fields_ = [
        ('Id', '_string'),
        ('Sender', '_string'),
        ('Type', '_string'),
        ('SubType', '_string'),
        ('Data', '_string'),
        ('ExtraData', '_string'),
        ]

@ForBuild('15.3.2495.0616')
class HMLiveViewResponseObject(FppClass):
    _fields_ = [
        ('Id', '_string'),
        ('StatusCode', '_enum'),
        ('Html', '_string')
        ]

@ForBuild('15.3.2495.0616')
class SandboxRequest(FppClass):
    _fields_ = [
        ('ID', '_string'),
        ('Uri', '_string'),
        ('Provider', '_string'),
        ('PostBody', '_string'),
        ('AuthOption', '_enum'),
        ('AuthParam', '_string')
        ]

@ForBuild('15.3.2495.0616')
class SandboxResponse(FppClass):
    _fields_ = [
        ('ID', '_string'),
        ('Status', '_primitive'),
        ('HttpStatusCode', '_primitive'),
        ('Body', '_string'),
        ('AuthOption', '_enum'),
        ('AuthParam', '_string')
        ]

@ForBuild('16.0.1635.0608')
class MiniCalendarUiObject(FppClass):
    _fields_ = [
        ('HTML', '_string'),
        ('DateString', '_string'),
        ('TargetDate', '_oArray'),
        ('IsVisible', '_primitive'),
        ('PrevMonthString', '_string'),
        ('NextMonthString', '_string'),
        ('TodayString', '_string'),
        ('Type', '_enum'),
        ]

@ForBuild('16.0.1635.0608')
class MiniCalendarOptions(FppClass):
    _fields_ = [
        ('NumberOfPastObjects', '_primitive'),
        ('NumberOfFutureObjects', '_primitive'),
        ('NeedAdditionalDateStrings', '_primitive'),
        ('DateStart', '_string'),
        ('DateEnd', '_string'),
        ]

@ForBuild('16.0.1635.0608')
class ComposeData(FppClass):
    _fields_ = [
        ('AttachmentIdHeaders', '_array'),
        ('InlineIdHeaders', '_array'),
        ('MessageBody', '_string'),
        ('Subject', '_string'),
        ('To', '_string'),
        ('CC', '_string'),
        ('BCC', '_string'),
        ('From', '_string'),
        ('DraftId', '_string'),
        ('MeetingIcalId', '_string'),
        ('MessageId', '_string'),
        ('OriginalMessageId', '_string'),
        ('Priority', '_primitive'),
        ('SentState', '_enum'),
        ('Rfc822InReplyTo', '_string'),
        ('Rfc822MessageId', '_string'),
        ('Rfc822References', '_string'),
        ]

@ForBuild('16.0.1635.0608')
class MessagePrefetchData(FppClass):
    _fields_ = [
        ('Data', '_array'),
        ]


class FppProxy(object):
    @staticmethod
    def escape(b):
        if b is None: return b
        a = "";
        def slash_escape(m):
            return '\\' + m.group(0)

        if isinstance(b, unicode):
            _b, b = b, b.encode('utf-8')

        a = ''.join(['"', str(b), '"'])
        a = re.sub(r'([\{|\}\[|\]\,\\:])', slash_escape, a).encode('url')
        return a

    @staticmethod
    def objToStringImpl(a):
        t = type(a)

        if t is unicode:
            a = a.encode('utf-8')
            t = str

        if (a is None):
            return 'null'
        elif t is str:
            return FppProxy.escape(a)
        elif t is list:
            return FppProxy.arrayToString(a)
        elif t is dict or hasattr(a, 'toString') or getattr(a, '_isFppObject', False):
            return a.toString()
        else:
            return FppProxy.objToString(a)

    @staticmethod
    def primitiveToString(a):
        if a in ("", None, null, Null):
            return 'null'

        return str(a).lower()

    @staticmethod
    def arrayToString(a):
        res = ['[']
        for x in a:
            res.append(FppProxy.objToStringImpl(x))
            res.append(',')

        if a:
            res.pop() # remove last ','

        res.append(']')
        return ''.join(res)

    @staticmethod
    def objToString(c):
        if c is None:
            return 'null'
        a = ['{']
        for field in getattr(c, '_fields_'):
            #a.append(FppProxy.escape(name))
            #a.append(':')
            a.append(FppProxy.objToStringImpl(getattr(c, field[0])))
            a.append(',')
        a[ - 1] = '}'
        return ''.join(a)

class Network_Type(object):
    configuration = None

    def __init__(self, b, opener=None, start_config = {}):
        self._isIE = False
        self._isMoz = True
        self._requests = []
        self.configuration = b
        self.opener = opener
        self.configuration.__dict__.update(start_config)
        self.configuration.SessionId = self.configuration.SessionId.decode('url')
        self.HM = None

    def set_HM(self, hm):
        self.HM = hm

    def set_base_url(self, baseurl):
        self.base_url = baseurl

    def createRequest(self, url, callback, verb):
        return HM_Request(url, callback, self, self.opener, verb)

    @util.callsback
    def process_response(self, resp, callback):
        data = resp.read()
        log.info('Processing hotmail response: %r', data)

        if ((resp.code // 100) != 2):
            e = Exception("%r was not successful (code = %r)", resp, resp.code)
            log.info('%r', e)
            return callback.error(e)

        result = None
        try:
            data, _data = data.replace('new HM.', ' HM.'), data
            d = dict(HM = self.HM, true = True, false = False, null = None)
            exec "result = " + data in d, d
            result = d['result']
        except Exception, e:
            log.info("Could not process javascript response: %r", _data)
            log.info("\terror was: %r", e)
            data = _data
            return self._process_response_re(data, callback)

        if result.Status.value == 0:
            return callback.success(result.Value)
        else:
            log.error("Got a non-zero status code (%r). Here\'s the whole response: %r", result.Status.value, _data)
            return callback.error(result.Error)

    def _process_response_re(self, data, callback):
        match = re.search(r'new HM\.FppReturnPackage\((\S+?),', data)
        if match is None:
            e = Exception('Response has unknown status code: %r', data)
            log.info('%r', e)
            return callback.error(e)

        status = match.group(1)
        log.info('Got status code %r for hotmail request. data was: %r', status, data)

        try:
            status = int(status)
        except (ValueError, TypeError):
            e = Exception('Status code could not be int()\'d. it was %r (the whole response was %r)', status, data)
            log.info('%r', e)
            return callback.error(e)

        if status != 0:
            e = Exception('Got a non-zero status code (%r). Here\'s the whole response: %r', status, data)
            log.info('%r', e)
            return callback.error(e)

        return callback.success(data)

class HM_Request(object):
    def __init__(self, url, cb, network, opener, verb=None):
        self.url = url
        self.callback = cb
        self.verb = verb or 'GET'
        self.postString = self.context = None
        self.headers = {}
        self.opener = weakref.ref(opener)
        self.network = network

    def send(self, context):
        self.context = context
        r = asynchttp.HTTPRequest(self.url, self.postString, self.headers, method=self.verb, adjust_headers = False)
        log.debug('opening request: method=%r url=%r post_data=%r headers=%r', self.verb, self.url, self.postString, self.headers)
        cbargs = dict(success=self.on_response, error=self.on_error)
        if self.opener is None:
            asynchttp.httpopen(r, **cbargs)
        else:
            opener = self.opener()
            if opener is None:
                log.info('weakref\'d opener is gone, not doing request %r', self.url)
                return
            opener.open(r, **cbargs)
#            util.threaded(lambda: opener.open(r))(**cbargs)

    def on_response(self, req_or_resp = None, resp=None):
        network = getattr(self, 'network', None)
        resp = resp or req_or_resp
        if network is not None:
            log.info('Got response for %r: %r', self, resp)
            self.network.process_response(resp, callback=self.callback)
            self.abort()
        else:
            log.warning('This request (%r) already got response, so not doing anything with this response: %r', self, resp)

    def on_error(self, e=None, resp = None):
        log.error('Error in hotmail request: %r', e)
        self.callback.error(resp or e)
        self.abort()

    def abort(self):
        self.__dict__.clear()
        self.__getattr__ = Null

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, ' '.join('%s=%r' % (x, getattr(self, x)) for x in ('verb', 'url', 'postString')))

class FPPConfig(object):
    RequestHandler = 'mail.fpp'
    FppVersion = '1'
    SessionId = ''
    AuthUser = ''
    CanaryToken = 'mt'
    Version = '1'
    PartnerID = ''

    def __init__(self, hotmail):

        self.hotmail = weakref.ref(hotmail)

    @property
    def CanaryValue(self):
        hm = self.hotmail()
        if hm is None:
            return None

        return hm.get_cookie(self.CanaryToken, domain = '.mail.live.com')

class PageInfo(object):
    fppCfg = None
    SELF_PATH = '/mail/InboxLight.aspx'
    queryString = {'nonce' : "2122195423"}

def get_build_for(my_build, builds):
    build = None
    for build in reversed(sorted(builds)):
        if my_build >= build:
            return build

    return build

class FppMethod(object):
    def __init__(self, impls):
        # impls: a str->tuple dictionary mapping build numbers to an FppMethod interface
        self.impls = impls

    def __get__(self, obj, objtype):
        my_build = obj.build

        build = get_build_for(my_build, self.impls.keys())
        details = self.impls.get(build)

        if details is None:
            raise AttributeError("not valid for build %r" % my_build)

        return FppMethodImpl(obj, *details)

class FppMethodImpl(object):
    def __init__(self, HM, params, method_name, tm, g, namespace):
        self.HM = HM
        self.method_name = self.name = method_name

        new_params = []
        for param in params:
            if isinstance(param, tuple):
                name, typ = param
                cls = FppMetaclass._classes[typ]
                if type(cls) is FppMetaclass:
                    new_params.append(_custom(name))
                else:
                    new_params.append(cls(name))
            else:
                new_params.append(param)

        self.params = new_params
        self.tm = tm
        self.g = g
        self.namespace = namespace

    def __call__(self, *args, **kwargs):
        arg_names = [x.name for x in self.params]
        arg_names.extend(('cb', 'ctx', 'cbError'))

        vals = dict(zip(arg_names, args))
        vals.update(kwargs)

        cb = ctx = cbError = None

        if 'callback' in kwargs:
            cb = kwargs.get('callback')
        if 'cbError' in kwargs:
            cbError = kwargs.get('cbError')
        if 'ctx' in kwargs:
            ctx = kwargs.get('ctx')

        for remaining in args[len(vals):]:
            if cb is None:
                cb = remaining
                continue
            if ctx is None:
                ctx = remaining
                continue
            if cbError is None:
                cbError = remaining
                continue

        Network = self.HM.Network

        prev = getattr(Network, '_fppPrevious', None)
        if prev is not None and prev._request is not None:
            prev._request.abort()

        f = FppMethodInvocation(self.namespace, self.method_name, cb, cbError, self.HM.build)
        f.Network = self.HM.Network
        f.Network._fppPrevious = f
        for param in self.params:
            if param.name not in vals:
                vals[param.name] = FppMetaclass._classes[param.type].default().value
            f.addParameter(param.type, vals[param.name])

        f.invoke(ctx)

class FppMethodInvocation(object):
    _HTTP_HEADERS = {
        "X-FPP-Command": "0",
        "Accept" : "text/html,application/xhtml+xml,application/xml,application/x-javascript",
        "Accept-Charset" : "utf-8",
        "Accept-Encoding" : "gzip,identity",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
    def __init__(self, className, methodName, cb, cbError, build):
        self.className = className
        self.methodName = methodName
        self.callback = cb
        self.callbackError = cbError
        self.context = None
        self._request = None
        self._isInvoked = False
        self._params = []
        self.build = build

    def addParameter(self, a, b):
        self._params.append({'fppType' : a, 'value' : b})

    def invoke(self, context):
        self.context = context

        if not self.Network.configuration:
            raise Exception("Network is not configured")
        if self._isInvoked:
            raise Exception("FppMethod %r already used", self)

        self._isInvoked = True

        argstring = ''
        netconfig = self.Network.configuration

        if self._params:
            param_buffer = []
            escape = TypeSystem.escape
            for param in self._params:
                escaped = escape({'type' : param['fppType'], 'value' : param['value']})
                param_buffer.append(escaped)
                param_buffer.append(",")
            argstring = ''.join(param_buffer[: - 1]) # don't include the last comma

        url = net.UrlQuery(util.httpjoin(self.Network.base_url, netconfig.RequestHandler),
                     cnmn = self.className + '.'  + self.methodName,
                     a = netconfig.SessionId,
                     au = netconfig.AuthUser,
                     ptid = netconfig.PartnerID or '0')
        post_data = dict(cn = self.className, mn = self.methodName, d = argstring, v = netconfig.FppVersion)
        hdrs = self._HTTP_HEADERS.copy()

        if self.build >= "15.3.2506.0629":
            hdrs[netconfig.CanaryToken] = netconfig.CanaryValue
        else:
            post_data[netconfig.CanaryToken] = netconfig.CanaryValue

        def clear_request(resp):
            self._request = None
            self._isInvoked = False

        if self.callback is not None:
            self.callback.error.append(clear_request)
            self.callback.success.append(clear_request)

        b = self._request = self.Network.createRequest(url, self.callback, 'POST')
        b.headers = hdrs
        b.postString = '&'.join('%s=%s' % i for i in post_data.items())
        b.send(self)

        del self.Network, self._params

class HM_Type(FppProxy):
    namespace = 'HM'
    SortBy = Flags("Sender", 0,
                   "Subject", 1,
                   "Size", 2,
                   "Type", 3,
                   "Date", 4)

    FppStatus = Flags("SUCCESS", 0,
                      "ERR_HTTP_MISCONFIGURATION", - 7,
                      "ERR_HTTP_PARSE_FAILURE", - 6,
                      "ERR_HTTP_CONNECT_FAILURE", - 5,
                      "ERR_HTTP_TIMEOUT", - 4,
                      "ERR_SERVER_UNCAUGHT", - 3,
                      "ERR_APP_SPECIFIC", - 2,
                      "ERR_FPP_PROTOCOL", - 1)

    ListNavigateDirection = Flags("FirstPage", 0,
                                  "LastPage", 1,
                                  "NextPage", 2,
                                  "PreviousPage", 3,
                                  "CurrentPage", 4)

    MessageBodyType = Flags('Part', 0,
                            'Full', 1)

    ItemView = Flags('Normal', 0,
                     'Deleted', 1,
                     'Junk', 2,
                     'Delayed', 3)

    PsaType = Flags('None', 0,
                    'Upsell', 1,
                    'Fre', 2,
                    'Auth', 3)

    FilterType = Flags("None", 0,
                       "Unread", 1,
                       "Contacts", 2,
                       "Flagged", 3,
                       "Photos", 4,
                       "Social", 5,
                       "Video", 6,
                       "File", 7,
                       "MailingList", 8,
                       "Shipping", 9,
                       "Other", 10,
                       "ResponsesToMe", 11,
                       "DocumentPlus", 12)

    JmrType = Flags("Junk", 0,
                    "NotJunk", 1,
                    "AV", 2,
                    "SVMOptInOptOut", 3,
                    "SVMClassification", 4,
                    "Phish", 5,
                    "Unsubscribe", 6,
                    'Compromised', 7,
                    "Unknown", - 1)

    ReadMessageOperation = Flags("GetMessage", 0,
                                 "NextMessage", 1,
                                 "PreviousMessage", 2,
                                 "MarkAsNotJunk", 3,
                                 "Unsubscribe", 4,
                                 "AddContact", 5,
                                 "None", 6)

    RemoveSenderFromListOption = Flags("None", 0,
                                       "KeepContact", 1,
                                       "RemoveContact", 2,
                                       "KeepSafeSender", 3,
                                       "RemoveSafeSender", 4)

    ImportanceType = Flags('NORMAL', 0,
                           'LOW', 1,
                           'HIGH', 2)

    MessageSentStateType = Flags("NOACTION", 0,
                                 "REPLIED", 1,
                                 "FORWARDED", 2)

    MiniCalendarUiType = Flags("Month", 0,
                               "Day", 1)

    MessageActionType = Flags("ViewMessage", 0,
                              "Reply", 1,
                              "ReplyAll", 2,
                              "Forward", 3,
                              "ResumeDraft", 4,
                              "GetAttachment", 5,
                              "MarkAsJunkOrNotJunk", 6,
                              "Accept", 7,
                              "Decline", 8,
                              "Tentative", 9,
                              "AcceptExchangeSharing", 10,
                              "DeclineExchangeSharing", 11,
                              "Prefetch", 12,
                              "None", 13)

    NounEnum = Flags("SendersEmailAddress", 97, "SendersName", 110, "Subject", 115, "ToOrCCHeader", 116, "HasAttachments", 104)
    MessagePartDataType = Flags("Body", 0, "ToList", 1, "Message", 2)
    HMLiveViewResultCode = Flags("Success", 0, "Failure", 1)
    SandboxAuthenticationOption = Flags("None", 0, "Oauth", 1);

    ReadingPaneLocation = Flags("None", 0, "Off", 1, "Right", 2, "Bottom", 3);

    __11 = Flags("Passed", 0, "Failed", 1, "Unknown", 2, "SoftFail", 3)
    __15 = Flags("Ok", 0, "OverQuota", 1, "DoesntExist", 2, "Error", 3, "AccountDoesntExist", 4, "AccountError", 5)
    __20 = Flags("Unknown", 0, "MakeLiveContact", 1, "AddLiveContact", 2, "DontShow", 3)
    MailActionType = Flags("Move", 0, "Mark", 1, "Flag", 2, "Forward", 3, "AssignCategory", 4, "RemoveCategory", 5)

    @property
    def FppReturnPackage(self):
        return self.GetFppTypeConstructor('FppReturnPackage')

    @property
    def FppError(self):
        return self.GetFppTypeConstructor('FppError')

    @property
    def HmSimpleMsg(self):
        return self.GetFppTypeConstructor('HmSimpleMsg')

    @property
    def InboxUiData(self):
        return self.GetFppTypeConstructor('InboxUiData')

    @property
    def Category(self):
        return self.GetFppTypeConstructor('Category')

    @property
    def build(self):
        return self.app_info.get('BUILD')

    def GetFppTypeConstructor(self, clsname):
        if clsname not in _versioned_classes:
            return globals()[clsname]

        try:
            cls_impls = _versioned_classes.get(clsname, None)
            if not cls_impls:
                raise Exception("Class %r not found for build %r. here's known classes: %r", clsname, self.build, _versioned_classes)

            build = get_build_for(self.build, cls_impls.keys())

            if build is None:
                raise Exception("Build %r not found for cls = %r. here's known classes: %r", self.build, clsname, _versioned_classes)
            cls = cls_impls[build]

            log.debug('Found class %r for version %r (my version is %r)', clsname, build, self.build)
            return cls

        except KeyError, e2:
            log.error('Error looking for versioned class %r: %r', clsname, e2)
            raise e

    def __init__(self, network, base_url, app_info):
        self.Network = network
        self.app_info = app_info
        self.set_base_url(base_url)
        self.Network.set_HM(self)

    def set_base_url(self, hostname):
        self.base_url = 'https://%s/mail/' % hostname
        self.Network.set_base_url(self.base_url)

    AddContactFromMessagePart = FppMethod({
       "15.3.2506.0629": (
        [('conversationId', '_string'),
         ('folderId', '_string'),
         ('startingMid', '_string'),
         ('numParts', '_primitive'),
         ('mpIndexMap', '_object'),
         ('messageRenderingInfo', 'MessageRenderingInfo'),
         ('contactName', '_string'),
         ('contactEmail', '_string'),
         ('demandLoadContentValues', '_array')],
        'AddContactFromMessagePart',
        XMLPost,
        'abortable',
        'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),

       })

    GetInboxData = FppMethod({
       "1": (
        [_primitive("fetchFolderList"),
         _primitive("fetchMessageList"),
         _custom("messageListRenderingInfo"),
         _primitive("fetchMessage"),
         _custom("messageRenderingInfo")],
        'GetInboxData',
        XMLPost,
        "abortable",
        "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),
       '15.1.3020.0910' : (
        [("fetchFolderList", '_primitive'),
         ("renderUrlsInFolderList", '_primitive'),
         ("fetchMessageList", '_primitive'),
         ("messageListRenderingInfo", '_custom'),
         ("fetchMessage", '_primitive'),
         ("messageRenderingInfo", '_custom')],
        'GetInboxData',
        XMLPost,
        'abortable',
        'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    ClearFolder = FppMethod({
        "1": (
         [_string("clearFolderId"),
          _custom("messageListRenderingInfo")],
         "ClearFolder",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),
    })

    MoveMessagesToFolder = FppMethod({
        "1": (
         [_string("fromFolderId"),
          _string("toFolderId"),
          _array("messageList"),
          _array("messageAuxData"),
          _custom("messageListRenderingInfo"),
          _custom("messageRenderingInfo")],
         "MoveMessagesToFolder",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),
        '13.3.3227.0707' : (
         [_string("fromFolderId"),
          _string("toFolderId"),
          _array("messageList"),
          _array("messageAuxData"),
          _custom("messageListRenderingInfo"),],
         "MoveMessagesToFolder",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),
        '15.3.2495.0616' : (
         [('fromFolderId', '_string'),
          ('toFolderId', '_string'),
          ('messageList', '_array'),
          ('messageAuxData', '_array'),
          ('batchInfo', '_custom'),
          ('messageListRenderingInfo', '_custom'),
          ('fetchMessageList', '_primitive'),
          ('refreshFolderAndQuickViewLists', '_primitive'),
          ('folderNameForRuleSuggestion', '_string'),
          ('messageRenderingInfo', '_custom'),
          ('conversationRenderingInfo', '_custom'),
          ('fetchItem', '_primitive')],
         'MoveMessagesToFolder',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),

        '15.4.0317.0921' : (
         [('fromFolderId', '_string'),
          ('toFolderId', '_string'),
          ('messageList', '_array'),
          ('messageAuxData', '_array'),
          ('batchInfo', 'BatchInfo'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('fetchMessageList', '_primitive'),
          ('refreshFolderAndQuickViewLists', '_primitive'),
          ('folderNameForRuleSuggestion', '_string'),
          ('messageRenderingInfo', 'MessageRenderingInfo'),
          ('conversationRenderingInfo', 'ConversationRenderingInfo'),
          ('fetchItem', '_primitive'),
          ('blockIfDelete', '_primitive')],
          'MoveMessagesToFolder',
          XMLPost,
          null,
          'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),

        '16.2.2978.1206' : (
         [('fromFolderId', '_string'),
          ('toFolderId', '_string'),
          ('messageList', '_array'),
          ('messageAuxData', '_array'),
          ('batchInfo', 'BatchInfo'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('fetchMessageList', '_primitive'),
          ('refreshFolderAndQuickViewLists', '_primitive'),
          ('folderNameForRuleSuggestion', '_string'),
          ('messageRenderingInfo', 'MessageRenderingInfo'),
          ('conversationRenderingInfo', 'ConversationRenderingInfo'),
          ('fetchItem', '_primitive'),
          ('blockIfDelete', '_primitive'),
          ("unpinOnMove", '_primitive'),
          ("markMessagesAsRead", '_primitive')],
          'MoveMessagesToFolder',
          XMLPost,
          null,
          'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    ViewAllFromSender = FppMethod({
        '15.3.2495.0616' : (
         [('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('senderEmail', '_string')],
         'ViewAllFromSender',
         XMLPost,
         'abortable',
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    RestoreHiddenTrash = FppMethod({
        '16.0.1635.0608' : (
              [('messageListRenderingInfo', 'messageListRenderingInfo')],
              'RestoreHiddenTrash',
              XMLPost,
              None,
              'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    MarkMessagesForJmr = FppMethod({
        "1": (
         [_string("folderId"),
          _array("messages"),
          _array("auxData"),
          _enum("jmrType"),
          _primitive("reportToJunk"),
          _custom("messageListRenderingInfo"),
          _custom("messageRenderingInfo")],
         "MarkMessagesForJmr",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),

        '15.3.2495.0616' : (
         [('folderId', '_string'),
          ('messages', '_array'),
          ('auxData', '_array'),
          ('BatchInfo', 'BatchInfo'),
          ('jmrType', '_enum'),
          ('setReportToJunkOK', '_primitive'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('messageRenderingInfo', 'MessageRenderingInfo'),
          ('refreshFolderAndQuickViewLists', '_primitive'),
          ('removeFromList', '_enum'),
          ('suppressListTransition', '_primitive'),
          ('markSenderAsSafe', '_primitive')],
         'MarkMessagesForJmr',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),

        '16.0.1635.0608' : (
         [('folderId', '_string'),
          ('messagesParam', '_array'),
          ('auxData', '_array'),
          ('BatchInfo', 'BatchInfo'),
          ('jmrType', '_enum'),
          ('setReportToJunkOK', '_primitive'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('messageRenderingInfo', 'MessageRenderingInfo'),
          ('refreshMessagesList', '_primitive'),
          ('refreshFolderAndQuickViewLists', '_primitive'),
          ('removeFromList', '_enum'),
          ('suppressListTransition', '_primitive'),
          ('markSenderAsSafe', '_primitive')],
         'MarkMessagesForJmr',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    ReportError = FppMethod({
        "1": (
         [_string("message")],
         "ReportError",
         XMLPost,
         "abortable",
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),
    })

    AddContactFromMessage = FppMethod({
        "1" : (
         [_custom("messageRenderingInfo"),
          _string("contactName"),
          _string("contactEmail")],
         "AddContactFromMessage",
         XMLPost,
         "abortable",
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),

        '15.3.2495.0616' : (
         [('messageRenderingInfo', 'MessageRenderingInfo'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('contactName', '_string'),
          ('contactEmail', '_string'),
          ('demandLoadContentValues', '_array')],
         'AddContactFromMessage',
         XMLPost,
         'abortable',
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),

    })

    SvmFeedback = FppMethod({
       "1": (
         [_string("svmUrl"),
          _custom("messageRenderingInfo"),
          _custom("messageListRenderingInfo")],
         "SvmFeedback",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),
    })

    MarkMessagesReadState = FppMethod({
        "1": (
         [_primitive("readState"),
          _array("messages"),
          _custom("messageListRenderingInfo")],
         "MarkMessagesReadState",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),
        '15.1.3020.0910' : (
         [_primitive("readState"),
          _array("messages"),
          _array("HmAuxData"), #_custom("HmAuxData"),
          _custom("messageListRenderingInfo")],
         "MarkMessagesReadState",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),

        '15.3.2495.0616' : (
         [('readState', '_primitive'),
          ('messages', '_array'),
          ('auxData', '_array'),
          ('batchInfo', '_custom'),
          ('messageListRenderingInfo', '_custom'),
          ('refreshFolderAndQuickViewLists', '_primitive')],
         'MarkMessagesReadState',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),

        '16.2.2978.1206' : (
         [('readState', '_primitive'),
          ('messages', '_array'),
          ('auxData', '_array'),
          ('batchInfo', '_custom'),
          ('markFolderId', '_string'),
          ('messageListRenderingInfo', '_custom'),
          ('refreshFolderAndQuickViewLists', '_primitive')],
         'MarkMessagesReadState',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    MarkMessagesFlagState = FppMethod({
        '15.3.2495.0616' : (
         [('flagState', '_primitive'),
          ('messages', '_array'),
          ('auxData', '_array'),
          ('batchInfo', 'BatchInfo'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('refreshFolderAndQuickViewLists', '_primitive')],
         'MarkMessagesFlagState',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    MarkMessagesFlagState = FppMethod({
        '15.3.2495.0616' : (
         [('flagState', '_primitive'),
          ('messages', '_array'),
          ('auxData', '_array'),
          ('batchInfo', 'BatchInfo'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('refreshFolderAndQuickViewLists', '_primitive')],
         'MarkMessagesFlagState',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    SaveVoicemailOnPhone = FppMethod({
        '15.3.2495.0616' : (
         [('messageIdList', '_array')],
         'SaveVoicemailOnPhone',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    DeleteVoicemailOnPhone = FppMethod({
        '15.3.2495.0616' : (
         [('messageIdList', '_array')],
         'DeleteVoicemailOnPhone',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    GetConversationInboxData = FppMethod({
        '15.3.2495.0616' : (
         [('fetchFolderList', '_primitive'),
          ('renderUrlsInFolderList', '_primitive'),
          ('fetchConversationList', '_primitive'),
          ('conversationListRenderingInfo', 'conversationListRenderingInfo'),
          ('fetchConversation', '_primitive'),
          ('conversationRenderingInfo', 'ConversationRenderingInfo')],
         'GetConversationInboxData',
         XMLPost,
         'abortable',
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    GetSingleMessagePart = FppMethod({
        '15.3.2495.0616' : (
         [('conversationId', '_string'),
          ('folderId', '_string'),
          ('messageRenderingInfo', 'MessageRenderingInfo'),
          ('messagePartIndex', '_primitive'),
          ('showUnsubscribeLink', '_primitive')],
         'GetSingleMessagePart',
         XMLPost,
         'abortable',
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    GetManyMessageParts = FppMethod({
        '15.3.2495.0616' : (
         [('conversationId', '_string'),
          ('folderId', '_string'),
          ('startingMessageId', '_string'),
          ('numParts', '_primitive'),
          ('messageIdToIndexMap', '_object'),
          ('showUnsubscribeLink', '_primitive')],
         'GetManyMessageParts',
         XMLPost,
         'abortable',
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    GetFullMessagePart = FppMethod({
        '15.3.2495.0616' : (
         [('messageRenderingInfo', 'MessageRenderingInfo'),
          ('messagePartIndex', '_primitive'),
          ('showUnsubscribeLink', '_primitive')],
         'GetFullMessagePart',
         XMLPost,
         'abortable',
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    MarkMessagePartForJmr = FppMethod({
        '15.3.2495.0616' : (
         [('fetchConversation', '_primitive'),
          ('cid', '_string'),
          ('fid', '_string'),
          ('startingMid', '_string'),
          ('numParts', '_primitive'),
          ('mpIndexMap', '_object'),
          ('messageListRenderingInfo', 'MessageListRenderingInfo'),
          ('mpMids', '_array'),
          ('mpAuxDatas', '_array'),
          ('mpFid', '_string'),
          ('jmrType', '_enum'),
          ('setReportToJunkOK', '_primitive'),
          ('removeFromList', '_enum'),
          ('markSenderAsSafe', '_primitive')],
         'MarkMessagePartForJmr',
         XMLPost,
         'abortable',
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    CreateMoveRule = FppMethod({
        '15.3.2495.0616' : (
         [('ruleNoun', '_enum'),
          ('matchingString', '_string'),
          ('fid', '_string')],
         'CreateMoveRule',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    CreateSendersMoveRules = FppMethod({
        '15.3.2495.0616' : (
         [('emails', '_array'),
          ('fid', '_string')],
         'CreateSendersMoveRules',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    CreateRecipientMoveRule = FppMethod({
        "15.4.0317.0921" :(
         [('recipientEmail', '_string'),
          ('folderId', '_string'),
          ('folderName', '_string')],
         'CreateRecipientMoveRule',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox')
    })
    BlockSenders = FppMethod({
        '15.3.2495.0616' : (
         [('emails', '_array')],
         'BlockSenders',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    DemandLoad = FppMethod({
        '15.3.2495.0616' : (
         [('demandLoadContentValues', '_array')],
         'DemandLoad',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    UndoSenderMoveToBlockList = FppMethod({
        '15.3.2495.0616' : (
         [('senderAddress', '_string')],
         'UndoSenderMoveToBlockList',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    ThrowError = FppMethod({
        '16.2.6151.0801' : (
         [('code', '_string'),
          ('message', '_string')],
         'ThrowError',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })

    GetHMLiveViews = FppMethod({
        '15.3.2495.0616' : (
         [('requests', '_array')],
         'GetHMLiveViews',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    DispatchSandboxRequests = FppMethod({
        '15.3.2495.0616' : (
         [('requests', '_array')],
         'DispatchSandboxRequests',
         XMLPost,
         null,
         'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })
    SendMessage_ec = FppMethod({
        "1": (
         [_string("to"),
          _string("from"),
          _string("cc"),
          _string("bcc"),
          _enum("priority"),
          _string("subject"),
          _string("message"),
          _array("attachments"),
          _string("draftId"),
          _string("draftFolderId"),
          _string("originalMessageId"),
          _string("rfc822MessageId"),
          _string("rfc822References"),
          _string("rfc822InReplyTo"),
          _enum("sentState"),
          _primitive("sendByPlainTextFormat"),
          _array("ignoredWordsFromSpellCheck"),
          _string("hipAnswer"),
          _string("hipMode"),
          _string("meetingIcalId")],
         "SendMessage_ec",
         XMLPost,
         null,
         "Microsoft.Msn.Hotmail.Ui.Fpp.MailBox"),

        '15.1.3020.0910' : None,
        "15.4.0317.0921" : (
         [('to', '_string'),
          ('from', '_string'),
          ('cc', '_string'),
          ('bcc', '_string'),
          ('ImportanceType', '_enum'),
          ('subject', '_string'),
          ('message', '_string'),
          ('messageForPlainTextConversion', '_string'),
          ('attachments', '_array'),
          ('draftId', '_string'),
          ('draftFolderId', '_string'),
          ('originalMessageId', '_string'),
          ('rfc822MessageId', '_string'),
          ('rfc822References', '_string'),
          ('rfc822InReplyTo', '_string'),
          ('MessageSentStateType', '_enum'),
          ('sendByPlainTextFormat', '_primitive'),
          ('ignoredWordsFromSpellCheck', '_array'),
          ('hipAnswer', '_string'),
          ('hipMode', '_string'),
          ('meetingIcalId', '_string')],
        'SendMessage_ec',
        XMLPost,
        None,
        'Microsoft.Msn.Hotmail.Ui.Fpp.MailBox'),
    })




class MailFolder(list):
    def __init__(self, account):
        list.__init__(self)
        self.account = account
        self.cur_page = 0
        self.more_pages = True

    def open(self):
        log.info("you clicked the inbox too soon")
        return

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, list.__repr__(self))


class LivemaiLFolderBase(MailFolder):
    domain = 'mail.live.com'
    PAGECOUNT = 25

    def __init__(self, account, **k):
        MailFolder.__init__(self, account)
        self.count = 0

        util.autoassign(self, k)

        if getattr(self, 'link', None) is None:
            self.link = self.link_from_fid(self.id)

        self.link = self.link + '&InboxSortAscending=False&InboxSortBy=Date'

    def link_from_fid(self, fid):
        return util.UrlQuery(util.httpjoin(self.account.base_url, 'InboxLight.aspx'),
                 FolderID=fid)

    def relative_url(self):
        return util.UrlQuery('/mail/InboxLight.aspx', FolderID = self.id)

    def login_link(self):
        return net.UrlQuery('https://login.live.com/login.srf',
                            wa = 'wsignin1.0',
                            id = '23456',
                            lc = '1033',
                            ct = '1278964289',
                            mkt = 'en-us',
                            rpsnv = '11',
                            rver = '6.0.5285.0',
                            wp   = 'MBI',
                            wreply = self.link)

    @classmethod
    def from_doc(cls, doc, account):
        li = doc
        id = uuid.UUID(li.get('id'))
        try:
            count = int(li.get('count'))
        except Exception, _e:
            pass

        link = util.UrlQuery(doc.base_url or account.base_url, FolderID = id)

        caption_span = doc.find(cls._caption_xpath)
        if caption_span is not None:
            name = caption_span.text.strip()

        log.info('Folder %r for %s has %d new messages', name, account.name, count)

        return cls(account, id = id, name = name, link = link, count = count)

    def link_for_page(self, pagenum):
        return util.UrlQuery(self.link,
                             InboxPage = 'Next',
                             Page = pagenum,
                             InboxPageAnchor = getattr(self, 'last_seen_message', ''),
                             NotAutoSelect = '',
                             n = ntok())

    @util.callsback
    def open(self, callback = None):
        return callback.error('deprecated')

    def process_one_page(self, doc):
        max_ = self.count
        num_pages = self.get_num_pages(doc) or (max_//self.PAGECOUNT)+1
        self.more_pages = (self.cur_page < num_pages)

        log.info('Parsing page %d of %d of folder %s', self.cur_page, num_pages, self.name)

        last_id_on_page = ''
        unreadcount = 0
        all_msgs = doc.findall('.//tr[@id]')

        for msg in all_msgs:
            if 'staticItem' in msg.attrib.get('class', ''):
                continue
            msg = self.account.HM.GetFppTypeConstructor('LivemailMessage').from_doc(msg, self)

            unread = self.process_message(msg)
            if unread:
                unreadcount += 1
                self.append(msg)

            msgid = msg.id
            if msgid is not None:
                last_id_on_page = msgid or last_id_on_page

        self.last_seen_message = last_id_on_page
        return unreadcount

    def process_message(self, msg):
        return not msg.opened

    def get_num_pages(self, doc):
        num_pages = None
        try:
            lastpage_li = doc.find('.//*[@pndir="LastPage"]')
            if lastpage_li is not None:
                lastpage_num_str = lastpage_li.get('pncur', None)
                try:
                    num_pages = int(lastpage_num_str)
                except (TypeError, ValueError):
                    pass
        except Exception:
            traceback.print_exc()
        return num_pages

@ForBuild("1")
class LivemailFolder(LivemaiLFolderBase):
    _caption_xpath = './/span[@class="Caption"]'

@ForBuild('16.2.2978.1206')
class LivemailFolder(LivemaiLFolderBase):
    _caption_xpath = './/span[@class="FolderLabel"]'

import mail
class LivemailMessageBase(mail.emailobj.Email):

    def parsedate(self, datestring):
        return datestring

    @classmethod
    def from_doc(cls, doc, folder):
        raise NotImplementedError

    def __init__(self, folder, **k):
        self.folder = folder
        self.account = folder.account

        util.autoassign(self, k)

        mail.emailobj.Email.__init__(self,
                                     id=self.id,
                                     fromname=self.sender,
                                     sendtime=self.parsedate(self.date),
                                     subject=self.subject,
                                     attachments=self.attach)

        self.set_link()
        self.opened = False

    def set_link(self):
        self.link = util.UrlQuery(util.httpjoin(self.account.base_url, 'InboxLight.aspx'),
                                  Aux=self._mad, ReadMessageId=self.id, n = ntok())


    def mark_as_read(self):
        self.open()

    def open(self):
        log.info('Opening %r for %s', self, self.account.name)
        if self.opened:
            return

        try:
            response = self.account.http.open(self.link)
            response.read()
            response.close()
        except Exception:
            pass
        self.opened = True

        log.info('Done opening %r for %s', self, self.account.name)

        return self.link

    def delete(self):
        log.info('Deleting %r', self)
        self.mark_as_read()

    def spam(self):
        log.info('Marking %r as spam', self)
        self.open() # to mark as read

    @callbacks.callsback
    def Messages_remove(self, messageList, messageAuxData, callback = None):
        self.Messages_move(messageList, messageAuxData, self.folder.id, self.account.trash.id, callback = callback)

    @callbacks.callsback
    def Messages_move(self, messageList, messageAuxData, fromFolderId, toFolderId, callback = None):
        messageIds = [str(self.id)]
        messageListRenderingInfo = self.make_mlri()
        messageRenderingInfo = None

        kwargs = dict(
            fromFolderId             = fromFolderId,
            toFolderId               = toFolderId,
            messageList              = messageList,
            messageAuxData           = messageAuxData,
            messageListRenderingInfo = messageListRenderingInfo,
            messageRenderingInfo     = messageRenderingInfo,
            callback                 = callback,
        )

        self.account.HM.MoveMessagesToFolder(**kwargs)

    @callbacks.callsback
    def MarkMessagesReadState(self, callback = None):
        messageListRenderingInfo = self.make_mlri()

        mad = self.make_message_aux_data()
        self.account.HM.MarkMessagesReadState(
                                              readState = True,             # readState
                                              messages = [str(self.id)],    # messages
                                              HmAuxData = [mad],              # HMAuxData
                                              messageListRenderingInfo = messageListRenderingInfo,
                                              markFolderId = self.folder.id,
                                              callback  = callback,             # callback
                                              )

    def login_link(self):
        return '/cgi-bin/getmsg?msg=%s' % (str(self.id).upper())

@ForBuild("1", "LivemailMessage")
class LivemailMessageOld(LivemailMessageBase):
    @classmethod
    def from_doc(cls, doc, folder):
        id = doc.get('id')
        mad = doc.get('mad', "")

        opened = "InboxContentItemUnread" not in doc.get('class', '')

        attach = ()
        if doc.find('.//img[@class="i_attach"]') is not None:
            attach = (True,)

        if doc.find('.//*[@class="SubjectCol"]') is not None:
            kws = cls.process_new_doc(doc, folder, 'Col')
            old = False
        elif doc.find('.//*[@class="SubjectBox"]') is not None:
            kws = cls.process_new_doc(doc, folder, 'Box')
            old = False
        elif doc.find('.//*[@class="Sbj"]') is not None:
            kws = cls.process_new_doc_short(doc, folder)
            old = False
        else:
            kws = cls.process_old_doc(doc, folder)
            old = True

        msg = cls(folder, id = id, _mad = mad, attach = attach, **kws)
        msg._is_old = old
        msg.opened = opened
        return msg

    @classmethod
    def process_old_doc(cls, doc, folder):
        tds = doc.findall('.//td')
        if len(tds) < 8:
            log.warning('Not sure if [4:7] are the right TDs to get from this TR: %r', HTML.tostring(doc))

        snd, sub, date = tds[4:7]
        try:
            sender = snd.find('a').text.strip()
        except Exception:
            sender = None

        try:
            subject = sub.find('a').text.strip()
        except Exception:
            subject = None

        return dict(date = date.text, sender = sender, subject = subject)

    @classmethod
    def process_new_doc_short(cls, doc, folder):
        def find_str(k):
            text_bits = doc.xpath('.//td[@class="%s"]//text()' % k, smart_strings = False)
            if len(text_bits) != 0:
                return text_bits[0]
            else:
                return None

        sender = find_str("Frm")
        subject = find_str('Sbj')
        date = find_str('Dat')

        return dict(date = date, sender = sender, subject = subject)

    @classmethod
    def process_new_doc(cls, doc, folder, style):
        date_div = doc.find('.//*[@class="Date%s"]' % style)
        subject_div = doc.find('.//*[@class="Subject%s"]' % style)
        from_div = doc.find('.//*[@class="From%s"]' % style)

        try:
            date = date_div.text.strip()
        except AttributeError:
            date = None

        try:
            subject = subject_div.find('a').text.strip()
        except AttributeError:
            subject = None

        try:
            elem = from_div.find('.//a')
            if elem is None:
                elem = from_div

            sender = elem.text.strip()
        except AttributeError:
            sender  = None

        return dict(sender = sender, subject = subject, date = date)

    def mark_as_read(self):
        LivemailMessageBase.mark_as_read(self)

        if self._is_old:
            messageRenderingInfo = self.account.make_mri(self, self._is_old)
            self.account.GetInboxData(message = True, mri = messageRenderingInfo)
        else:
            self.MarkMessagesReadState()

    @util.threaded
    def delete(self):
        LivemailMessageBase.delete(self)
        self.Messages_remove([self.id], [self.make_message_aux_data()])

        log.info('Done deleting %r', self)

    def make_message_aux_data(self):
        cls = self.account.HM.GetFppTypeConstructor('HmAuxData')
        return cls.for_msg(self)

    @callbacks.callsback
    def spam(self, callback = None):
        LivemailMessageBase.spam(self)
        messageIds = [str(self.id)]
        messageAuxData = [self.make_message_aux_data()]

        messageListRenderingInfo = self.make_mlri()
        messageRenderingInfo = None
        self.account.HM.MarkMessagesForJmr(folderId = self.folder.id,
                                           messagesParam = messageIds,
                                           messages = messageIds,
                                           auxData = messageAuxData,
                                           jmrType = 0, # HM.JmrType.Junk
                                           reportToJunk = True, # reportToJunk
                                           messageListRenderingInfo = messageListRenderingInfo,
                                           messageRenderingInfo = messageRenderingInfo,
                                           cb = callback, # For callback
                                           ctx = {"jmrType": 0 } # HM.JmrType.Junk
                                           )
        log.info('Done marking %r as spam', self)

    def make_mlri(self):
        return self.account.make_mlri(self.folder, timestamp = False)

@ForBuild("15.3.2495.0616")
class LivemailMessage(LivemailMessageOld):
    @classmethod
    def from_doc(cls, doc, folder):

        opened = "mlUnrd" not in doc.attrib.get("class", '')
        id = doc.attrib.get("id", None)
        mad = doc.attrib.get("mad", "")
        sender_el = doc.xpath(".//*[contains(@class, 'Fm')]//*[@email]", smart_strings = False)
        if sender_el is not None:
            sender_el = sender_el[0]

        fromemail = sender_el.attrib.get("email", None)
        fromname = (sender_el.text or '').strip()

        subject_el = doc.xpath(".//*[contains(@class, 'Sb')]/a/text()", smart_strings = False)

        if subject_el is not None:
            subject = subject_el[0].strip()
        else:
            subject = None

        date_el = doc.xpath(".//*[contains(@class, 'Dt')]//text()", smart_strings = False)
        if date_el is not None:
            date = date_el[0].strip()
        else:
            date = None

        attach_el = doc.xpath(".//*[contains(@class, 'At')]//*[contains(@class, 'i_att_s')]", smart_strings = False)
        attach = [True] if attach_el else []

        msg = cls(folder, id = id, _mad = mad, attach = attach, sender = fromname, subject = subject, date = date, is_conv = doc.attrib.get("conv", None) is not None)
        msg.fromemail = fromemail
        msg.opened = opened
        msg._is_old = False

        return msg

    def set_link(self):
        d = dict(baseurl = self.account.HM.base_url,
                 mad = self._mad,
                 id_name = "ReadConversationId" if self.is_conv else "ReadMessageId",
                 id = self.id,
                 ntok = ntok(),
                 inboxid = str(uuid.UUID(int=1)),
                 )

        self.link = "%(baseurl)sInboxLight.aspx?Aux=%(mad)s&%(id_name)s=%(id)s&n=%(ntok)s&FolderID=%(inboxid)s" % d

    def make_mlri(self):
        return self.account.make_mlri(self.folder, timestamp = True)

    @callbacks.callsback
    def MarkMessagesReadState(self, callback = None):
        messageListRenderingInfo = self.make_mlri()

        mad = self.make_message_aux_data()
        self.account.HM.MarkMessagesReadState(
                                              readState = True,             # readState
                                              messages = [str(self.id)],    # messages
                                              auxData = [mad],              # HMAuxData
                                              messageListRenderingInfo = messageListRenderingInfo,
                                              callback  = callback,             # callback
                                              )

    def mark_as_read(self):
        LivemailMessageBase.mark_as_read(self)
        self.MarkMessagesReadState()

    def conv_login_link(self):
        return net.UrlQuery('https://login.live.com/login.srf',
                            wa = 'wsignin1.0',
                            id = '23456',
                            lc = '1033',
                            ct = '1278964289',
                            mkt = 'en-us',
                            rpsnv = '11',
                            rver = '6.0.5285.0',
                            wp   = 'MBI',
                            wreply = self.link)
    def login_link(self):
        if self.is_conv:
            return self.conv_login_link()
        else:
            return LivemailMessageOld.login_link(self)

@ForBuild('16.2.2978.1206')
class LivemailMessage(LivemailMessage):
    def set_link(self):
        d = dict(baseurl = self.account.HM.base_url,
                 id_name = "mid",
                 id = self.id,
                 ntok = ntok(),
                 )

        self.link = "%(baseurl)sInboxLight.aspx?%(id_name)s=%(id)s&n=%(ntok)s" % d

    def login_link(self):
        return self.conv_login_link()

@ForBuild('16.2.2978.1206')
class Category(FppClass):
    _fields_ = [
        ('Id', '_primitive'),
        ("Name", '_string'),
        ("Visibility", '_enum'),
        ("IsCategorizable", '_primitive'),
        ("UnreadMessagesCount", '_primitive'),
        ("TotalMessagesCount", '_primitive'),
        ("ColorCode", '_string'),
        ("IsSenderBased", '_primitive'),
        ("IsReserved", '_primitive'),
    ]
# Added to suppress "new build" warnings.
@ForBuild('16.2.6151.0801')
class __BuildVersionDummy(FppClass):
    _fields_ = []

def get_classname(js):
    return re.search(r'HM\.registerFppClass\("(.+?)",', js).group(1)
def get_fields(js):
    fields_re = re.compile(r'Web\.Network\.FppProxy\._(_(?:.+?))\("(.+?)"\),')
    return [x[:: - 1] for x in fields_re.findall(js)]
def fppclass_to_python(js):
    from pprint import pformat
    cname = get_classname(js)
    fields = get_fields(js)
    return 'class %s(FppClass):\n    _fields_ = %s\n' % (cname, pformat(fields))

def main():
    print str(HmAuxData("10\\|0\\|8CA6DDB632DFE40\\|", null))

def main2():
    from tests.testapp import testapp
    a = testapp()

    Page = PageInfo()
    Page.fppCfg = FPPConfig(None)
    Network = Network_Type(Page.fppCfg)

    HM = HM_Type(Network)

    @util.callsback
    def doit(callback = None):
        HM.GetInboxData(True, True, None, True, None, Null, None, None)

    def success(resp):
        print 'success', resp
    def error(e):
        print 'error', e

    doit(success = success, error = error)

if __name__ == '__main__':
    main()
