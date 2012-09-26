import logging
_log = log = logging.getLogger('msn.p21.ns')

import traceback

import io
import time
import uuid
import hashlib
import sysident
import socket
import email
import rfc822
import copy
import operator

import lxml.etree as etree
import lxml.builder as B
import lxml.objectify as objectify

import hooks

import util
import util.net as net
import util.Events as Events
import util.cacheable as cacheable
import util.callbacks as callbacks
import util.network.soap as soap
import util.primitives.funcs as funcs
import util.primitives.strings as strings

import common
import common.asynchttp as asynchttp

import msn
import msn.MSNCommands as MSNC
import msn.MSNClientID as MSNClientID
import msn.P2P as P2P
import msn.P2P.P2PHandler as P2PHandler

from msn.p15 import Notification as Super

import mail.passport as passport

import msn.SOAP.services as SOAPServices

import msn.AddressBook as MSNAB
import msn.Storage as MSNStorage

defcb = dict(trid=True, callback=sentinel)
empty_guid = str(uuid.UUID(int=0))

def deprecated(f):
    def _deprecated(*a, **k):
        log.info("Deprecated method called: %s", f.func_name)
        return
    return _deprecated

def userinfo_edit(f):
    def wrapper(self, *args, **kwds):
        def edit_and_push(buddy, **k):
            f(self, buddy, *args, **kwds)
            self.put_userinfo(buddy, **k)
        self.event('needs_self_buddy', edit_and_push)
    return wrapper

@callbacks.callsback
def zsiparse(soap, locatorname, name, raw, callback = None):
    loc = getattr(soap, '%sLocator' % locatorname)()
    port = getattr(loc, 'get%sPort' % name)()
    binding = port.binding

    binding.reply_headers = util.Storage(type='text/xml')
    binding.data = raw
    response = util.Storage(body = io.StringIO(raw), headers = util.Storage(get_content_type = lambda : 'text/xml'))
    return binding.Receive(response, callback = callback)

class SSOTicket(object):
    domain = None
    token = None
    binarySecret = None
    created = 0
    expires = 0
#    type = None
    _timefmt = '%Y-%m-%dT%H:%M:%SZ'

    def __init__(self, domain, token, binarySecret, created, expires):
        if created is not None:
            created = time.mktime(time.strptime(created, self._timefmt))
        if expires is not None:
            expires = time.mktime(time.strptime(expires, self._timefmt))

        util.autoassign(self, locals())

class MSNP21Notification(Super):
    events = Super.events | set((
        'needs_self_buddy',
        'on_circle_member_joined',
        'circle_roster_recv',
        'circle_roster_remove',
        'P2PMessageReceived',
    ))

    versions = ['MSNP21']
    client_chl_id = challenge_id = "PROD0120PW!CCV9@"
    client_chl_code = "C1BX{V4W}Q3*10SM"

    def __init__(self, *a, **k):
        Super.__init__(self, *a, **k)

        self._authorizers = {
                             'default' : self.initial_auth,
                             }

        self.machine_guid = None

        self.init_http()

        self.services = []
        self.init_services()

        # Tokens is the old name but tickets is more accurate, especially for SOAP stuff
        self.tokens = self.tickets = {}
        self.cachekeys = {}
        if self.address_book is None:
            self.address_book = MSNAB.AddressBook(self)

        if getattr(self.address_book, 'client', None) is None:
            self.address_book.client = self

        if self.contact_list is None:
            self.contact_list = MSNAB.ContactList(self, uuid.UUID(int=0))

        if getattr(self.contact_list, 'client', None) is None:
            self.contact_list.client = self

        if self.profile is None:
            self.profile = MSNStorage.Profile(self)
            self.fetched_profile = False
        else:
            self.profile.client = self
            self.fetched_profile = True

        self.requestCircleCount = 0

        if self.CircleList is None:
            self.CircleList = {}

        self.PresenceScenario = 0
        self.sent_initial_adls = False

        self._abFindCallback = funcs.Delegate()

        self.pending_put = []

    address_book = cacheable.cproperty(None,
                                       lambda x: None if x is None else x.serialize(),
                                       lambda x: None if x is None else MSNAB.AddressBook.deserialize(x),
                                       user = True)

    contact_list = cacheable.cproperty(None,
                                       lambda x: None if x is None else x.serialize(),
                                       lambda x: None if x is None else MSNAB.ContactList.deserialize(x),
                                       user = True)

    profile = cacheable.cproperty(None,
                                  lambda x: None if x is None else x.serialize(),
                                  lambda x: None if x is None else MSNStorage.Profile.deserialize(x),
                                  user = True)

    CircleList = cacheable.cproperty(None,
                                     lambda x: None if x is None else dict((k, v.serialize()) for k,v in x.items()),
                                     lambda x: None if x is None else dict((k, MSNAB.Circle.deserialize(v)) for k,v in x.items()),
                                     user = True)

    @Events.event
    def on_contact_add(self, name, b_id, l_id, g_id):
        return name, b_id, l_id, g_id

    def init_http(self):
        self.http = asynchttp.cookiejartypes.CookieJarHTTPMaster()

    def _create_conv_invite(self, *a, **k):
        return self.protocol._create_conv_invite(*a, **k)

    def init_services(self):

        self.services.extend([SOAPServices.SecurityTokenService(transport = self.http),
                              SOAPServices.WhatsUpService(transport = self.http),
                              SOAPServices.SharingService(transport = self.http),
                              SOAPServices.ABService(transport = self.http),
                              SOAPServices.ClearService(transport = self.http),
#                              SOAPServices.SpacesService(transport = self.http),
                              SOAPServices.StorageService(transport = self.http),
                              SOAPServices.OIMService(transport = self.http),
                              SOAPServices.RSIService(transport = self.http),
                             ])

    def get_cachekey(self, key):
        return self.cachekeys.get(key, None)

    def set_cachekey(self, key, cachekey):
        self.cachekeys[key] = cachekey

    def getSsoService(self, domain):
        for s in self.getSsoServices():
            if s.SSO_Domain == domain:
                return s
        return None

    def getService(self, appid):
        for s in self.services:
            if getattr(s, 'AppId', None) == appid:
                return s
        return None

    def getSsoServices(self):
        return [x for x in self.services if getattr(x, 'SSO', False)]

    @callbacks.callsback
    def initial_auth(self, username, password, sso_data, callback = None):
        _policy_ref, nonce = self._sso_data = sso_data
        self.clearservice_auth(username, password, sso_data,
                               success = lambda new_tickets: self._after_initial_auth(nonce = nonce, new_tickets = new_tickets, callback = callback),
                               error = callback.error)

    @callbacks.callsback
    def clearservice_auth(self, username, password, sso_data, callback = None):
        clear = self.getSsoService(SOAPServices.SsoDomains.Clear)
        policy_ref, nonce = sso_data
        clear.SSO_PolicyRef = policy_ref
        log.info_s("SSO_Auth: %r, %r", username, sso_data)

        sts = self.getSsoService(SOAPServices.SsoDomains.STS)

        services = self.get_auth_required_services()
        client = util.Storage(get_username = lambda: username,
                              get_password = lambda: password,
                              getSsoServices = lambda: services)

        if not services:
            log.debug("No tickets need renewing. calling success")
            return callback.success([])

        sts.RequestMultipleSecurityTokens(client = client, services = services,
                                          success = lambda resp: self.process_tickets(resp, callback = callback),
                                          error = lambda *a: self.request_ticket_error(callback = callback, *a))

    @callbacks.callsback
    def _after_initial_auth(self, nonce, new_tickets, callback = None):
        clearticket = self.get_ticket(SOAPServices.SsoDomains.Clear)
        if clearticket is None:
            callback.error(Exception("No ticket for %r", SOAPServices.SsoDomains.Clear))
            return

        token = clearticket.token
        secret = clearticket.binarySecret

        callback.success(token, passport.mbi_crypt(secret, nonce), new_tickets)

    @callbacks.callsback
    def renew_auth(self, callback = None):
        return self.clearservice_auth(self._username, self._password, self._sso_data, callback = callback)

    def get_auth_required_services(self, force = None):
        if force is None:
            force = []

        required = []
        requesting_domains = set()
        for service in self.getSsoServices():
            if service in force:
                continue
            if not (self.has_current_ticket(service.SSO_Domain) or service.SSO_Domain in requesting_domains):
                requesting_domains.add(service.SSO_Domain)
                required.append(service)

        required.extend(force)

        return required

    @callbacks.callsback
    def process_tickets(self, tickets, callback = None):
        new_tickets = []
        for token in tickets.RequestSecurityTokenResponse:
            try:
                ticket = SSOTicket(token.AppliesTo.EndpointReference.Address,
                                   str(getattr(getattr(token, 'RequestedSecurityToken', ''), 'BinarySecurityToken', '')) or None,
                                   str(getattr(getattr(token, 'RequestedProofToken', ''), 'BinarySecret', '')) or None,
                                   str(getattr(getattr(token, 'Lifetime', ''), 'Created', '')) or None,
                                   str(getattr(getattr(token, 'Lifetime', ''), 'Expires', '')) or None,
                                   )

                self.set_ticket(ticket)
                new_tickets.append(ticket)
                log.info("Got ticket for domain %r", ticket.domain)
            except Exception:
                traceback.print_exc()

        callback.success(new_tickets)

    def complete_auth(self, token, mbi, tickets):
        self.send_usr_s(token, mbi, self.get_machine_guid())

    def get_machine_guid(self):
        if self.machine_guid is None:
            self.generate_machine_guid()

        return self.machine_guid

    def generate_machine_guid(self):
        self.machine_guid = uuid.UUID(bytes=hashlib.md5(sysident.sysident() + str(time.time())).digest())

    @callbacks.callsback
    def request_ticket_error(self, *a, **k):
        self._ticket_error = (a, k)
        k['callback'].error(Exception("No tickets"))

    def has_current_ticket(self, domain):
        if self.get_ticket(domain) is None:
            return False

        if self.is_ticket_expired(domain):
            return False

        return True

    def is_ticket_expired(self, domain):
        ticket = self.get_ticket(domain)
        if ticket is None:
            return True

        return ticket.expires < time.time()

    def get_ticket(self, domain):
        return self.tickets.get(domain, None)

    def set_ticket(self, ticket, domain = None):
        if domain is None:
            domain = ticket.domain

        self.tickets[domain] = ticket

    def recv_ubx(self, msg):
        msg.args = msg.args[0].split(':')[::-1]
        return Super.recv_ubx(self, msg)

    def _finish_connect(self):
        if not self.CONNECTED:

            def connected(*a, **k):
                if not self.CONNECTED:
                    self.CONNECTED = True
                    log.info("connected!")
                    self.event('on_connect')

            log.info('putting userinfo -> changing to connected')
            self.event('needs_self_buddy', lambda b: self.put_userinfo(b, success = connected))

        if self.sent_initial_adls:
            for content, callback in self.pending_put:
                self.send_put(content, callback = callback)

    @callbacks.callsback
    def _sync_addressbook(self, fullsync = False, abid = None, PartnerScenario = SOAPServices.PartnerScenario.Initial, callback = None):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)

        if abid is None:
            abid = str(uuid.UUID(int=0))

        if fullsync:
            lastchange = soap.MinTime
        else:
            lastchange = self.address_book.GetAddressBookLastChange(abid)

        self._abFindCallback += callback

        ab.ABFindContactsPaged(client = self,
                               abid = abid,
                               deltas = lastchange != soap.MinTime,
                               lastChange = lastchange,
                               PartnerScenario = PartnerScenario,
                               success = lambda resp: self._abFindSuccess(resp, callback = callback),
                               error   = lambda e: self._abFindError(e, callback = callback))

    @callbacks.callsback
    def _abFindSuccess(self, response, callback = None):
#        if response.UserState.PartnerScenario == MSNAB.Scenario.Initial:
#            log.info("Need to do a full sync")

        default_ab = lowerid = str(uuid.UUID(int=0))
        if response.ABFindContactsPagedResult.Ab is not None:
            lowerid = str(response.ABFindContactsPagedResult.Ab.AbId).lower()

        if self.address_book.client is None:
            self.address_book.client = self
        if self.contact_list.client is None:
            self.contact_list.client = self
        if lowerid == default_ab:
            self.address_book.MergeIndividualAddressBook(response.ABFindContactsPagedResult)
        else:
            self.address_book.MergeGroupAddressBook(response.ABFindContactsPagedResult)

            if self.requestCircleCount > 0:
                self.requestCircleCount -= 1

        if self.requestCircleCount == 0:
            if self.PresenceScenario and not self.sent_initial_adls:
                self.send_initial_adl(MSNAB.Scenario.SendInitialCirclesADL)

            self._abFindCallback.call_and_clear()

        # Force a cache save
        self.address_book = self.address_book
        self.contact_list = self.contact_list

        if not self.fetched_profile:
            self.sync_profile()

        ticket = getattr(getattr(response.ABFindContactsPagedResult, 'CircleResult', None), 'CircleTicket', None)
        if ticket is not None:
            self.socket.send(msn.Message('USR', 'SHA', 'A', ticket.encode('utf8').encode('b64')), trid = True)

    @callbacks.callsback
    def _abFindError(self, e, callback = None):
        log.info("abFindError: %r", e)
        import sys
        sys._abe = e
        if fault_check(e, "Full sync required") or fault_check(e, "Need to do full sync"):
            log.info("FullSyncRequired")
            self._sync_addressbook(fullsync = True, callback = callback)
            return

        if not self.CONNECTED:
            self.event('on_conn_error', self, e)

        callback.error(e)

    def _load_contact_list(self):
        self._sync_addressbook()
        self._sync_memberships()

        if self.address_book.GetAddressBookLastChange() != soap.MinTime:
            log.info("Logging on early since we have cached addressbook")
            self.address_book.initialize()
            self.send_initial_adl(MSNAB.Scenario.SendInitialContactsADL)
            self.send_initial_adl(MSNAB.Scenario.SendInitialCirclesADL)
            self._finish_connect()

    def _sync_memberships(self, fullsync = False, PartnerScenario = SOAPServices.PartnerScenario.Initial):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        if fullsync:
            lastchange = soap.MinTime
        else:
            lastchange = self.address_book.GetAddressBookLastChange()

        sharing = self.getService(SOAPServices.AppIDs.Sharing)
        sharing.FindMembership(client = self,
                               deltas = lastchange != soap.MinTime,
                               lastChange = lastchange,
                               PartnerScenario = PartnerScenario,
                               success = self._findMembershipSuccess,
                               error   = self._findMembershipError)

    def _findMembershipSuccess(self, response):
        result = response.FindMembershipResult
        self.address_book.Merge(result)

        # Force a cache save
        self.address_book = self.address_book
        self.contact_list = self.contact_list

        if self.contact_list is not None and self.contact_list.owner is not None:
            self.send_initial_adl(MSNAB.Scenario.SendInitialContactsADL)
            self.send_initial_adl(MSNAB.Scenario.SendInitialCirclesADL)
        else:
            raise Exception("contact list or owner is None")

    def _findMembershipError(self, e):
        log.info("findMembershipError: %r", e)

        if fault_check(e, "Full sync required") or fault_check(e, "Need to do full sync"):
            log.info("FullSyncRequired")
            self._sync_memberships(fullsync = True)
            return

        self.event('on_conn_error', self, e)

    def AddGroup(self, name, id, is_favorite):
        # todo: create groupid object out of id?
        self.event('group_receive', name, id)

    def recv_fln(self, msg):
        'FLN 1:urapns55@hotmail.com 0:0\r\n'
        log.debug('got fln')

        abc = self.get_ab_contact(msg.args[0])
        name = msg.args[0]
        nick = None
        status = 'FLN'
        client_id = 0
        self.event('contact_offline', abc.account, nick, status, client_id)

    def get_ab_contact(self, type_name):
        if ':' in type_name:
            type, name = type_name.split(':', 1)

        else:
            type = 1
            name = type_name

        return self.contact_list.GetContact(name, type = type)

    def recv_nln(self, msg):
        'NLN NLN 1:urapns55@hotmail.com Jeffrey 1074004004:2281833472 %3cmsnobj%20Creator%3d%22urapns55%40hotmail.com%22%20Size%3d%224767%22%20Type%3d%223%22%20Location%3d%22TFR2C2.tmp%22%20Friendly%3d%22AAA%3d%22%20SHA1D%3d%22R%2baq3gIarGx4uC%2frXBW32DgC5EE%3d%22%20SHA1C%3d%22Ne6p6df%2f%2fIwdO8gyKmooCiHocJg%3d%22%2f%3e\r\n'
        log.debug('got nln')

        (status, typename, nick, capab_ex), __args = msg.args[:4], (msg.args[4:] or [])

        abc = self.get_ab_contact(typename)
        abc.nickname = nick = nick.decode('url').decode('fuzzy utf8') or None
        client_id = self.parse_caps(capab_ex)

        msnobj = None
        if __args:
            iconinfo = msn.util.url_decode(__args[0])

            if '<' in iconinfo and '>' in iconinfo:
                msnobj = msn.MSNObject.parse(iconinfo)

        self.event('contact_btype', abc.account, abc.type)

        self.event('contact_online', abc.account, nick, status, client_id)
        self.event('contact_icon_info', abc.account, msnobj)

    def parse_caps(self, caps):
        return int(caps.split(':')[0])

    def _set_persist_blp(self, val):

        if self.contact_list.owner is None:
            return

        annos = self.contact_list.owner.contactInfo.annotations
        for anno in annos:
            if anno.Name == MSNAB.AnnotationNames.MSN_IM_BLP:
                break
        else:
            anno = MSNAB.Annotation(Name = MSNAB.AnnotationNames.MSN_IM_BLP)

        anno.Value = str(int(val))

        self.contact_list.owner.PropertiesChanged = "Annotation"
        #self.ABContactUpdate(self.contact_list.owner)

    def _get_profile(self, buddy, callback):
        log.info("get profile: %r", buddy)

    def disconnect(self, do_event = True):
        self.save_and_destroy_address_book()
        self.P2PHandler, P2PHandler = None, getattr(self, 'P2PHandler', None)
        if P2PHandler is not None:
            P2PHandler.Dispose()

        return Super.disconnect(self, do_event)

    def save_and_destroy_address_book(self):
        self.address_book = self.address_book
        self.contact_list = self.contact_list
        self.CircleList = self.CircleList

        for contact in self.contact_list.contacts.values():
            if contact.DirectBridge is not None:
                contact.DirectBridge.Shutdown()

        self.address_book.client = None
        self.contact_list.client = None

    def needs_login_timer(self):
        return False

    def sync_profile(self):
        storage = self.getSsoService(SOAPServices.SsoDomains.Storage)

        if ((not getattr(self.profile, 'DateModified', None)) or
            (self.profile.DateModified < self.address_book.MyProperties.get(MSNAB.AnnotationNames.Live_Profile_Expression_LastChanged, soap.MinTime))):
            scene = SOAPServices.PartnerScenario.Initial
        else:
            scene = SOAPServices.PartnerScenario.RoamingIdentityChanged

        storage.GetProfile(client = self, scenario = scene, success = self._profile_success, error = self._profile_error)

    def _profile_success(self, resp):
        self.fetched_profile = True
        log.info("Got profile: %r", resp)

        pr = getattr(resp, 'GetProfileResult', None)
        ep = getattr(pr, 'ExpressionProfile', None)
        if pr is None or ep is None:
            self._CreateProfile()
            return

        self.profile = MSNStorage.Profile.from_zsi(resp.GetProfileResult, client = self)

        if ep.DisplayName is not None:
            displayname = ep.DisplayName
            if isinstance(displayname, str):
                displayname = displayname.decode('utf8')
            self.contact_alias(self.self_buddy.name, displayname)

        if ep.PersonalStatus is not None:
            self.contact_status_msg(self.self_buddy.name, ep.PersonalStatus)

        if ep.StaticUserTilePublicURL is not None:
            self.contact_icon_info(self.self_buddy.name, ep.StaticUserTilePublicURL)

    def _profile_error(self, e):
        log.info("profile error: %r", e)
        self._profile_e = e

    def _CreateProfile(self):
        pass

    def send_uux(self, msg='', callback=sentinel):
        guid = self.get_machine_guid()

        doc = B.E("EndpointData",
                  B.E('Capabilities', '%d:0' % self.self_buddy.client_id))

        self.socket.send(msn.Message('UUX', payload=etree.tostring(doc)), trid=True, callback=callback)

        self_status = self.self_buddy.protocol.status_to_code.get(self.self_buddy.status, 'NLN')
        if self_status == "FLN":
            self_status = "HDN"

        doc = B.E("PrivateEndpointData",
                  B.E("EpName", socket.gethostname()),
                  B.E("Idle", str(common.profile().idle).lower()),
                  B.E("ClientType", "1"),
                  B.E("State", self_status),
                  )

        self.socket.send(msn.Message('UUX', payload=etree.tostring(doc)), trid=True, callback=callback)

    def recv_msg_notification(self, msg):
        #name, passport = msg.args
        if msg.name == 'Hotmail':
            MD = self.extract_oim_info(msg)
            self._oim_info = MD
            self.oims = [] #msn.oim.OIMMessages(self, MD)
        else:
            log.warning('unknown msg/notification')

    def extract_oim_info(self, oim_info_msg):
        msg_obj = rfc822.Message(oim_info_msg.payload.body())
        maildata = msg_obj['Mail-Data']
        if 'too-large' in maildata:
            MD = None
        else:
            MD = objectify.fromstring(maildata)

        return MD

    @userinfo_edit
    def send_chg(self, *a, **k):
        pass

    @userinfo_edit
    def _set_status(self, buddy, code, _client_id, _callback):
        buddy.status_code = code

    @callbacks.callsback
    def put_userinfo(self, buddy, callback = None, **k):

        message_headers = (
            (('Routing', '1.0'),
                 ('To', '%d:%s' % (MSNAB.IMAddressInfoType.WindowsLive, buddy.name)),
                 ('From', '%d:%s;epid={%s}'  % (MSNAB.IMAddressInfoType.WindowsLive, buddy.name, str(self.get_machine_guid()))),
              ),
              (('Reliability', '1.0'),
                 ('Stream', '1'),
                 #('Segment', '0'),
                 ('Flags', 'ACK'),
              ),
              (('Publication', '1.0'),
                 ('Uri', '/user'),
                 ('Content-Type', 'application/user+xml'),
              ),
        )

        if buddy.msn_obj is None:
            msnobj_txt = ''
        elif hasattr(buddy.msn_obj, 'to_xml'):
            msnobj_txt = buddy.msn_obj.to_xml()
        else:
            msnobj_txt = buddy.msn_obj

        body_doc = B.E("user",
                       B.E("s",
                           B.E("UserTileLocation", msnobj_txt),
                           B.E("FriendlyName", buddy.alias),
                           B.E("PSM", buddy.status_message),
                           #B.E("DDP", ''),
                           #B.E("Scene", ''),
                           #B.E("ASN", ''),
                           #B.E("ColorScheme", "-3"),
                           #B.E("BDG", ''),
                           B.E("RUM", ''),
                           #B.E("RUL", ''),
                           #B.E("RLT", "0"),
                           #B.E("RID", ''),
                           #B.E("SUL", ''),
                           B.E("MachineGuid", "{%s}" % self.get_machine_guid()),
                           n="PE",
                           ),
                       B.E("s",
                           B.E("Status", 'HDN' if buddy.status_code == 'FLN' else buddy.status_code),
                           B.E("CurrentMedia", ''), #buddy.current_media
                           n="IM",
                           ),
                       B.E("sep",
                           B.E("VER", "%s:%s" % (self.client_name, self.client_software_version)),
                           B.E("TYP", "1"),
                           B.E("Capabilities",
                               #"67108864:1074298880"),
                               '%s:%s' % (MSNClientID.PE_DEFAULT_CAPABILITIES, MSNClientID.PE_DEFAULT_CAPABILITIES_EX)),
                           n="PE",
                           ),
                       B.E("sep",
                           B.E("ClientType", '1'),
                           B.E("EpName", socket.gethostname()),
                           B.E("Idle", 'true' if buddy.idle else 'false'),
                           B.E("State", 'HDN' if buddy.status_code == 'FLN' else buddy.status_code),
                           n="PD",
                           ),
                       B.E("sep",
                           B.E("Capabilities",
                               #"2955186480:2609258384"),
                               '%s:%s' % (MSNClientID.IM_DEFAULT_CAPABILITIES, MSNClientID.IM_DEFAULT_CAPABILITIES_EX)),
                           n="IM",
                           ),
                       )

        body = etree.tostring(body_doc, encoding = 'utf8')

        payload = str(MSNC.MultiPartMime(message_headers, body = body))
        self.send_put(payload, callback = callback)

    @callbacks.callsback
    def send_put(self, content, callback = None):
        if self.sent_initial_adls:
            log.info("PUT content: %r", content)
            self.socket.send(msn.Message('PUT', payload = content), trid = True,
                             success = lambda sck, msg: callback.success(msg))
        else:
            self.pending_put.append((content, callback))

    def send_del(self, content):
        log.info("DEL content: %r", content)
        self.socket.send(msn.Message('DEL', payload = content), **defcb)

    def send_initial_adl(self, scene):
        first_adl_key = 0
        hashlist = {}

        adls = []
        pending_joins = []
        if (scene & MSNAB.Scenario.SendInitialContactsADL):
            log.warning("Prepping contact ADLS!")
            contacts = self.contact_list.contacts.values()
        elif (scene & MSNAB.Scenario.SendInitialCirclesADL):
            log.warning("Prepping circle ADLS!")
            contacts = self.CircleList.values()

            for c in contacts:
                if getattr(c, 'pending_join', False):
                    pending_joins.append(c)

            for c in contacts[:]:
                if c.CircleRole == MSNAB.CirclePersonalMembershipRole.StatePendingOutbound:
                    contacts.remove(c)

        for contact in contacts:
            if contact.ADLCount == 0:
                continue

            contact.ADLCount -= 1
            ch = contact.Hash
            l = 0

            if contact.IsMessengerUser or (contact.type == MSNAB.ClientType.CircleMember and contact.OnForwardList):
                l |= int(MSNAB.MSNList.Forward)
            if contact.OnAllowedList:
                l |= int(MSNAB.MSNList.Allow)
            elif contact.OnBlockedList:
                l |= int(MSNAB.MSNList.Block)
            if contact.HasList(MSNAB.MSNList.Hidden):
                l |= int(MSNAB.MSNList.Hidden)

            if l not in (0, int(MSNAB.MSNList.Block)) and ch not in hashlist:
                hashlist[ch] = hashlist.get(ch, 0) | l

        def success():
            for c in pending_joins:
                log.info("Completing delayed circle join for %r", c)
                self.JoinCircleConversation(c.abid + '@' + c.hostDomain)

            self.PresenceScenario |= scene
            log.info("PresenceScenario = %r", self.PresenceScenario)
            desired_scenario = (MSNAB.Scenario.SendInitialCirclesADL | MSNAB.Scenario.SendInitialContactsADL)
            if (self.PresenceScenario & desired_scenario) == desired_scenario and not self.sent_initial_adls:
                self.sent_initial_adls = True
                self._finish_connect()

        if hashlist:
            adls.extend(self.make_adls(hashlist, (scene & MSNAB.Scenario.SendInitialContactsADL) == MSNAB.Scenario.SendInitialContactsADL))
            log.info("got adls!: %r", adls)
            self.send_adl_sequence(adls, success = success)
        else:
            success()

    def send_rml_sequence(self, adls):
        return self.send_adl_sequence(adls, cmd = 'RML')

    @callbacks.callsback
    def send_adl_sequence(self, adls, cmd = 'ADL', callback = None):
        log.info("initiating send of %r %ss", len(adls), cmd)
        _adls = adls[:]
        def send_adl(*a):
            if not adls:
                log.info("All %ss sent", cmd)
                return callback.success()
            adl = adls.pop(0)
            self.socket.send(msn.Message(cmd, payload = adl), trid = True, success = send_adl, error = send_adl)
        send_adl()

    def make_adls(self, contacts, initial = False):
        mls = []
        ml = B.E("ml")

        if initial:
            ml.attrib['l'] = '1'

        domain_contact_count = 0
        currentDomain = None
        domtelElement = None

        log.debug("contacts.keys(): %r", contacts.keys())
        for contact_hash in sorted(contacts.keys(), cmp = cmp_contact_domain):
            split = split_contact_hash(contact_hash)
            sendlist = contacts[contact_hash] | int(MSNAB.MSNList.Forward)

            _type = MSNAB.ClientType.EmailMember

            if len(split) > 0:
                _type = MSNAB.ClientType(int(split[0]))

            try:
                _emailaddr = util.net.EmailAddress(split[1])
                name, domain = _emailaddr.name, _emailaddr.domain
            except Exception:
                domain = ''
                name = 'tel:' + split[1]
                if _type != MSNAB.ClientType.PhoneMember:
                    log.info("Non-phone member could not be parsed as email address: %r", contact_hash)
            else:
                if _type == MSNAB.ClientType.PhoneMember:
                    log.info("Phone member was parseable as email address: %r", contact_hash)

            if sendlist != 0:
                if currentDomain != domain:
                    currentDomain = domain
                    domain_contact_count = 0
                    if _type == MSNAB.ClientType.PhoneMember:
                        domtelElement = B.E("t")
                    else:
                        domtelElement = B.E("d")
                        domtelElement.attrib['n'] = currentDomain

                    ml.append(domtelElement)

                contactElement = B.E("c", n = name)
                if _type != MSNAB.ClientType.PhoneMember:
                    contactElement.attrib['t'] = str(int(_type))

                contact = self.contact_list.contacts.get(contact_hash)
                if contact is None:
                    contact = self.CircleList.get(contact_hash)

                epdata = getattr(contact, 'EndPointData', None)

                def s_el(n, sendlist):
                    el = B.E('s', l = str(sendlist), n = n)
                    for epid in epdata:
                        if n in epdata[epid]:
                            if int(epid) != 0:
                                el.attrib['epid'] = str(epid)
                            el.attrib['n'] = n

                    return el

                if split[1] == self.contact_list.owner.account:
                    sendlist = 3

                    contactElement.append(s_el('PD', sendlist))

                contactElement.append(s_el('IM', sendlist))

                if sendlist & int(MSNAB.MSNList.Hidden) == 0:
                    contactElement.append(s_el('PE', sendlist))

                    if _type != MSNAB.ClientType.PhoneMember:
                        contactElement.append(s_el('PF', sendlist))

                domtelElement.append(contactElement)
                domain_contact_count += 1

            serialized = etree.tostring(ml)
            if len(serialized) > 7300:
                ml.append(domtelElement)
                mls.append(etree.tostring(ml, encoding = 'utf-8'))

                ml = B.E('ml')
                if initial:
                    ml.attrib['l'] = '1'
                currentDomain = None
                domain_contact_count = 0

        if domain_contact_count > 0 and domtelElement is not None:
            ml.append(domtelElement)

        mls.append(etree.tostring(ml, encoding = 'utf-8'))

        return mls

#    def recv__241(self, msg):
#        log.info("Got 241 message. Echoing it back...")
#        self.socket.send(msn.Message("ADL", payload = msg.payload), **defcb)

    def recv_adl(self, msg):
        log.debug("Got ADL: %r", msg)

    def recv_nfy(self, msg):
        message = MSNC.MultiPartMime.parse(msg.payload)
        to = message.get('To')
        from_ = message.get('From')
        via = message.get('Via', None)
        if via is not None:
            circle = self.GetCircle(via)
        else:
            circle = None

        payload = message.get_payload()
        if message.get('Content-Type') in ('application/user+xml', 'application/circles+xml') and len(payload) != 0:
            payload = objectify.fromstring(payload)
        else:
            payload = None

        ctype, name = split_contact_hash(from_)[:2]
        ctype = int(ctype)
        if message.get('Uri') == '/user':
            if msg.args[0] == 'PUT' and payload is not None:
                return self.update_user_nfy(name, ctype, payload, full = message.get("NotifType", "Partial") == "Full", circle = circle)
            elif msg.args[0] == 'DEL':
                return self.delete_user_nfy(name, ctype, payload, circle = circle)
        elif message.get('Uri').startswith('/circle'):
            if msg.args[0] == 'PUT' and payload is not None:
                return self.update_circle_roster(name, ctype, payload, full = message.get('NotifType', 'Partial') == 'Full', circle = circle)
            elif msg.args[0] == 'DEL':
                return self.remove_circle_roster(name, ctype, message.get('Uri'), circle = circle)

        log.info("Unknown NFY command: %r / %r", msg.args, msg.payload)

    def remove_circle_roster(self, circle_name, ctype, uri, circle = None):
        if not uri.startswith ('/circle/roster(IM)/user('):
            return

        name = uri[len('/circle/roster(IM)/user('):-1]
        self.event('circle_roster_remove', circle_name, ctype, name)

    def update_circle_roster(self, circle_id, ctype, payload, full = False, circle = None):
        names = []
        pending_names = []
        nonpending_names = []
        roster = getattr(payload, 'roster', None)
        if roster is None:
            return

        for user in payload.roster.user:
            name = str(user.id)
            names.append(name)
            state = str(getattr(user, 'state', ''))
            if state == 'Pending':
                pending_names.append(name)
            else:
                nonpending_names.append(name)

        self.event('circle_roster_recv', circle_id, ctype, names, pending_names, nonpending_names, full)

    def update_user_nfy(self, name, ctype, payload, full, circle = None):
        contact = self.contact_list.GetContact(name, type = ctype)

        if full:
            contact.EndPointData.clear()

        tag = 'sep'
        for attr in ('IM', 'PE', "PF", 'PD'):
            new = payload.find(".//%s[@n='%s']" % (tag, attr))
            if new is None:
                continue

            epid = new.attrib.get('epid')
            if epid is None:
                continue

            epid = uuid.UUID(epid)

            if epid not in contact.EndPointData:
                contact.EndPointData[epid] = {}
            contact.EndPointData[epid][attr] = new

        self.update_user_presence(contact, payload, None, circle)

    def update_user_presence(self, contact, nfy, old_status, circle):
        log.info("Update user presence: %r %r", contact.account, etree.tostring(nfy, pretty_print = True))

        name = contact.account
        nick = status = None
        psm = None
        msnobj = None

        for s in nfy.iterfind('s'):
            _status = s.find('Status')
            if status is None and _status is not None:
                status = _status.text

            _nick = s.find("FriendlyName")
            if nick is None and _nick is not None:
                nick = _nick.text

            _psm = s.find('PSM')
            if psm is None and _psm is not None:
                # If the tag is present but empty, we need to clear the status message.
                psm = _psm.text or u''

            _msnobj = s.find('UserTileLocation')
            if msnobj is None and _msnobj is not None:
                msnobj = _msnobj.text

        log.debug("processing presence for %r", name)
        if None not in (name, status):
            log.debug("\tpresence: friendly-name=%r, status=%r", nick, status)
            if circle is None:
                self.event('contact_online', name, nick or name, status, 0)
            else:
                names = ['%d:%s' % (contact.type, contact.account)]
                self.event('circle_roster_recv', circle.account, contact.type, names, [], names, False)

        if psm is not None:
            log.debug("\tpsm: %r", psm)
            self.event('contact_status_msg', name, psm)

        if msnobj is not None:
            try:
                msnobj = msn.MSNObject.parse(msnobj)
            except Exception:
                msnobj = None

            log.debug("\ticon: %r", msnobj)
            self.event('contact_icon_info', name, msnobj)

    def delete_user_nfy(self, name, ctype, payload, circle = None):
        contact = self.contact_list.GetContact(name, type = ctype)

        if getattr(contact, 'IsMessengerUser', False) and \
            ctype != MSNAB.IMAddressInfoType.WindowsLive and \
            self.contact_list.HasContact(name, MSNAB.IMAddressInfoType.WindowsLive):

            log.info("Ignoring non-WindowsLive info about a windows live contact %r (contact = %r)", name, contact)
            return

        epdata = getattr(contact, 'EndPointData', None)

        if payload is None:
            log.info("Got no payload for NFY DEL: name = %r, ctype = %r, circle = %r", name, ctype, circle)
            return

        for child in payload.findall('.//sep'):
            epid_key = uuid.UUID(child.attrib['epid'])
            epid_data = contact.EndPointData.get(epid_key, {})

            if epid_data.pop(child.attrib['n'], None) is not None:
                log.debug("removed user %s's nfy node: %r", name, etree.tostring(child))

            if not epid_data:
                contact.EndPointData.pop(epid_key, None)

        if payload.find('.//s[@n="IM"]') is not None and circle is None:
            self.event('contact_offline', name, None, 'FLN', 0)

        elif circle is not None:
            self.event('circle_roster_remove', circle.account, ctype, name)

        if name == self.self_buddy.name:
            my_epid_nodes = payload.xpath('.//sep[@n="IM" and @epid="{%s}"]' % self.get_machine_guid())
            if my_epid_nodes:
                log.critical("Being sent offline by another endpoint")
                self.event('other_user')

    @deprecated
    def send_blp(self):
        # Deprecated
        return

    @deprecated
    def send_uux(self):
        # Deprecated
        return

    @deprecated
    def send_prp(self):
        return

    @deprecated
    def send_xfr(self):
        raise Exception()
        return

    def recv_sdg(self, sdg):
        msg = sdg.payload

        from_epid = msg.parts[0].get_param('epid', None, header = 'From')
        if from_epid is None:
            from_epid = uuid.UUID(int = 0)
        else:
            from_epid = uuid.UUID(from_epid)

        msg.parts[0].del_param('epid', header = 'From')
        from_ = msg.parts[0].get('From')
        from_type, from_name = from_.split(':', 1)
        from_type = int(from_type)

        contact = self.contact_list.GetContact(from_name, from_type)
        ver = P2P.Version.V1 if int(from_epid) == 0 else P2P.Version.V2

        mtype = sdg.payload.get('Message-Type')
        if mtype == 'Data':
            self.recv_sdg_data(sdg, contact, from_epid, ver)
        elif mtype == 'Signal/P2P':
            self.recv_sdg_signalp2p(sdg, contact, from_epid, ver)

        else:
            bname = sdg.payload.get('From').split(':', 1)[-1].split(';', 1)[0]
            self.event('fed_message', from_name, sdg)

    def recv_sdg_data(self, sdg, contact, from_epid, ver):
        msg = sdg.payload

        offsets = msg.get('Bridging-Offsets', None)
        if offsets is None:
            data_payloads = [msg.get_payload()]
        else:
            if offsets != '0':
                log.info("Splitting incoming message according to offsets: %r", offsets)

            total_payload = msg.get_payload()
            data_payloads = []
            offsets = map(int, offsets.split(','))
            start_end = zip(offsets, offsets[1:] + [-1])
            for start, end in start_end:
                data_payloads.append(total_payload[start:end])

            assert len(offsets) == len(data_payloads)

        pipe = msg.get('Pipe', None)
        if pipe is not None:
            try: pipe = int(pipe)
            except: pass
            else:
                self.SDGBridge.packageNumber = pipe

        for data_payload in data_payloads:
            p2pmessage = P2P.P2PMessage.P2PMessage(ver)
            p2pmessage.ParseBytes(data_payload)
            #_log.debug("Got P2PMessage: %r", p2pmessage)
            self.P2PHandler.ProcessP2PMessage(self.SDGBridge, contact, from_epid, p2pmessage)

    def recv_sdg_signalp2p(self, sdg, contact, from_epid, ver):
        msg = sdg.payload
        slp_data = msg.get_payload()
        import msn.P2P.MSNSLPMessages as SLP
        slp = SLP.SLPMessage.Parse(slp_data)

        if slp is None:
            log.error("Invalid SLP message in body: %r", str(msg))
            return

        if slp.ContentType in ("application/x-msnmsgr-transreqbody",
                               "application/x-msnmsgr-transrespbody",
                               "application/x-msnmsgr-transdestaddrupdate"):

            import msn.P2P.P2PSession as Session
            Session.ProcessDirectInvite(slp, self, None)

    def recv_not(self, msg):
        doc = etree.fromstring(msg.payload)
        body = getattr(doc.find('.//MSG/BODY'), 'text', None)
        if body is None:
            return

        doc = etree.fromstring(body)

        # Maybe there's a circle with new people in it:
        has_new_item = getattr(doc.find('./HasNewItem'), 'text', None) == 'true'
        circle_id = getattr(doc.find('./CircleId'), 'text', None)
        if has_new_item and circle_id is not None:
            log.info("Got notification about updated circle (id = %r). syncing addresbook...", circle_id)

            self.RequestAddressBookById(abid = circle_id)
            return

        elif getattr(doc.find('./Service'), 'text', None) == 'ABCHInternal':
            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.ABChangeNotifyAlert)
            return

        log.info("Unknown notification: %r", msg.payload)

    def request_sb(self):
        self.event('switchboard_request', None, None)

    @callbacks.callsback
    def AddNewContact(self, account, client_type = None, invitation = None, otheremail = None, callback = None):

        if client_type is None:
            otheremail = None
            client_type = self.determine_client_type(account)

        if self.contact_list.HasContact(account, client_type):
            contact = self.contact_list.GetContact(account, type = client_type)
            log.info("Already have this contact: %r = %r", account, contact)
            if contact.OnPendingList:
                self.AddPendingContact(contact, callback = callback)
            elif not getattr(contact, 'contactId', None) or contact.contactId == str(uuid.UUID(int=0)) or not contact.HasList(MSNAB.MSNList.Forward):
                self.AddNonPendingContact(account, client_type, invitation, otheremail, callback = callback)
            elif contact.contactId and contact.contactId != str(uuid.UUID(int=0)):
                if not contact.contactInfo.isMessengerUser:
                    log.info("Setting contact as messenger user")
                    contact.contactInfo.isMessengerUser = True
                if not contact.OnBlockedList:
                    log.info("Putting contact on AL")
                    contact.OnAllowedList = True
                self.contact_list.ContactAdded(contact, MSNAB.MSNList.Forward)
                callback.success()
            else:
                log.warning("Cannot add contact: %r", contact.Hash)
        else:
            self.AddNonPendingContact(account, client_type, invitation, otheremail, callback = callback)

    @callbacks.callsback
    def AddNonPendingContact(self, account, client_type, invitation = None, otheremail = None, callback = None):
        log.info("Adding non-pending account: %r, %r", account, client_type)
        ct = MSNAB.ClientType(client_type)
        if '@' in account and ct == MSNAB.ClientType.PassportMember:
            email = net.EmailAddress(account)
            fed_query = etree.tostring(
                                       B.E('ml',
                                           B.E('d',
                                               B.E('c', n = email.name),
                                               n = email.domain)
                                           )
                                       )
            self.socket.send(msn.Message('FQY', payload = fed_query), **defcb)

        def after_add_contact(resp = None, guid = None):
            contact = self.contact_list.GetContact(account, type = ct)

            if resp is not None:
                guid = resp.ABContactAddResult.Guid

            contact.contactId = guid
            log.info("Non-pending contact added: %r", contact)

            if not contact.HasList(MSNAB.MSNList.Block):
                # Add to AL
                if ct == MSNAB.ClientType.PassportMember:
                    adls = self.make_adls({contact.Hash : int(MSNAB.MSNList.Allow) | int(MSNAB.MSNList.Forward)})
                    self.send_adl_sequence(adls)
                else:
                    self.contact_list.ContactAdded(contact, MSNAB.MSNList.Allow)

            self.contact_list.ContactAdded(contact, MSNAB.MSNList.Forward)
            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.ContactSave, callback = callback)

        self.AddNewOrPendingContact(account, False, invitation, ct, otheremail, success = after_add_contact, error = callback.error)

    @callbacks.callsback
    def AddPendingContact(self, contact, callback = None):
        log.info("Adding pending contact: %r", contact)
        self.RemoveContactFromList(contact, MSNAB.MSNList.Pending)

        def after_add_contact_rl(resp = None):
            if not contact.OnBlockedList:
                if MSNAB.ClientType(contact.type) == MSNAB.ClientType.EmailMember:
                    contact.OnAllowedList = True
                else:
                    adls = self.make_adls({contact.Hash : int(MSNAB.MSNList.Allow)})
                    self.send_adl_sequence(adls)
                    self.contact_list.ContactAdded(contact, MSNAB.MSNList.Allow)

            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.ContactMsgrAPI, callback = callback)

        def after_add_contact_fl(resp = None, guid = None):
            if resp is None:
                assert guid is not None
                contact.contactId = guid
            else:
                assert guid is None
                contact.contactId = resp.ABContactAddResult.Guid

            contact.OnForwardList = True

            if not contact.OnReverseList:
                self.AddContactToList(contact,
                                      MSNAB.MSNList.Reverse,
                                      success = after_add_contact_rl)
            else:
                after_add_contact_rl(None)

        self.AddNewOrPendingContact(contact.Mail, True, None, MSNAB.ClientType(contact.type), None,
                                    success = after_add_contact_fl,
                                    error = callback.error)

    @callbacks.callsback
    def AddContactToList(self, contact, list_int, callback = None):
        role = MSNAB.MSNList(list_int)

        if role == MSNAB.MSNList.Pending:
            return

        if contact.HasList(role):
            return

        adls = self.make_adls({contact.Hash : int(role)})

        def send_adl_and_update_contact_list():
            if role in (MSNAB.MSNList.Allow, MSNAB.MSNList.Block, MSNAB.MSNList.Forward):
                self.send_adl_sequence(adls)
            self.contact_list.ContactAdded(contact, str(role))

            callback.success()

        if role == MSNAB.MSNList.Forward:
            return send_adl_and_update_contact_list()

        ps = SOAPServices.PartnerScenario.ContactMsgrAPI if role == MSNAB.MSNList.Reverse else SOAPServices.PartnerScenario.BlockUnblock

        member = None
        member_zsi = None

        def after_add(resp):
            if self.address_book.HasMembership(MSNAB.ServiceFilters.Messenger, contact.account, contact.type, role.role):
                log.warning("Contact already exists in %r. Not calling AddMembership")
                contact.AddToList(role)
                return send_adl_and_update_contact_list()

            self.contact_list.ContactAdded(contact, role)
            self.address_book.AddMembership(MSNAB.ServiceFilters.Messenger,
                                            contact.Mail,
                                            contact.type,
                                            role.role,
                                            member if member is not None else MSNAB.Member.from_zsi(member_zsi),
                                            MSNAB.Scenario.ContactServeAPI)
            self.on_contact_add(contact.account, getattr(contact, 'contactId', contact.account), int(role), None)
            ########
            send_adl_and_update_contact_list()

        def add_member_error(e):
            if fault_check(e, 'Member already exists'):
                log.debug("Member already exists on list %r. Calling succces", role)
                after_add(None)
            else:
                callback.error()

        if getattr(contact, 'contactId', None) is not None and self.address_book.HasContact(contact.contactId):
            log.warning("Already got this contact in the address book, not calling AddMember: %r")
            member = self.address_book.SelectBaseMember(MSNAB.ServiceFilters.Messenger, contact.account, contact.type, role.role)
            after_add(None)
        else:
            sharing = self.getService(SOAPServices.AppIDs.Sharing)
            member_zsi = sharing.AddMember(client = self, contact = contact, role = role, success = after_add, error = add_member_error)

    @callbacks.callsback
    def AddNewOrPendingContact(self, account, pending = False, invitation = None, network = None, otheremail = None, callback = None):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        ps = SOAPServices.PartnerScenario.ContactMsgrAPI if pending else SOAPServices.PartnerScenario.ContactSave

        def contact_add_error(e):
            if fault_check(e, "Contact Already Exists"):
                log.debug("Contact already exists. Calling succces")
                try:
                    guid = getattr(getattr(e, 'Detail', None), 'AdditionalDetails', None).ConflictObjectId
                except Exception:
                    try:
                        contact = self.contact_list.GetContact(account, type = self.determine_client_type(account, network))
                        guid = contact.contactId
                    except Exception:
                        guid = None

                callback.success(guid = guid)
            else:
                callback.error()

        ab.ABContactAdd(client = self,
                        account = account,
                        pending = pending,
                        invitation = invitation,
                        network = network,
                        otheremail = otheremail,
                        PartnerScenario = ps,
                        success = callback.success,
                        error = contact_add_error)

    @callbacks.callsback
    def RemoveContact(self, contact, callback = None):
        empty_guid = str(uuid.UUID(int=0))
        if getattr(contact, 'contactId', empty_guid) == empty_guid:
            return

        ab = self.getService(SOAPServices.AppIDs.AddressBook)

        def after_delete(resp):
            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.ContactSave, callback = callback)

        ab.ABContactDelete(client = self,
                           contacts = [contact],
                           PartnerScenario = SOAPServices.PartnerScenario.Timer,
                           success = after_delete,
                           error = callback.error)

    @callbacks.callsback
    def RemoveContactFromList(self, contact, list_int, callback = None):
        role = MSNAB.MSNList(list_int)

        sharing = self.getService(SOAPServices.AppIDs.Sharing)

        log.info("Removing contact from list: %r / %r", contact, role)

        if role == MSNAB.MSNList.Reverse:
            return

        if not contact.HasLists(role):
            self.contact_list.ContactRemoved(contact, role)
            return callback.success()

        rmls = self.make_adls({contact.Hash : int(role)}, False)

        def send_rml_and_update_contact_list():
            if role in (MSNAB.MSNList.Allow, MSNAB.MSNList.Block, MSNAB.MSNList.Forward, MSNAB.MSNList.Hidden):
                self.send_rml_sequence(rmls)

            self.contact_list.ContactRemoved(contact, role)

        if role == MSNAB.MSNList.Forward or role == MSNAB.MSNList.Hidden:
            log.info("No DeleteMember required for forward or hidden list. sending RML")
            send_rml_and_update_contact_list()
            callback.success()
            return

        def delete_member_error(e):
            log.info("Error calling DeleteMember: %r", e)

            if fault_check(e, "Member does not exist"):
                log.debug("Member already deleted. Calling succces")
                after_delete_member(None)
            else:
                callback.error()

        def after_delete_member(response):
            log.info("DeleteMember completed for %r. sending RML", contact)
            self.contact_list.ContactRemoved(contact, role)
            self.address_book.RemoveMembership(MSNAB.ServiceFilters.Messenger, contact.Mail, contact.type, role)
            send_rml_and_update_contact_list()
            callback.success()

        ps = SOAPServices.PartnerScenario.ContactMsgrAPI if (role == MSNAB.MSNList.Pending) else SOAPServices.PartnerScenario.BlockUnblock

        sharing = self.getService(SOAPServices.AppIDs.Sharing)
        sharing.DeleteMember(client = self,
                             contact_type = contact.type,
                             contact_mail = contact.account,
                             role = role.role,
                             PartnerScenario = ps,
                             success = after_delete_member,
                             error = delete_member_error)

    @callbacks.callsback
    def BlockContact(self, contact, callback = None):

        if contact.type == MSNAB.IMAddressInfoType.Circle:
            return self.BlockCircle(contact, callback = callback)

        def after_al_remove(resp = None):
            if not contact.OnBlockedList:
                self.AddContactToList(contact, MSNAB.MSNList.Block, callback = callback)
            else:
                callback.success()

        if contact.OnAllowedList:
            self.RemoveContactFromList(contact,
                                       MSNAB.MSNList.Allow,
                                       success = after_al_remove,
                                       error = callback.error)
        elif not contact.OnBlockedList:
            after_al_remove()

    @callbacks.callsback
    def _block_buddy(self, buddy, callback = None):
        contact = self.contact_list.GetContact(buddy.name, type = self.determine_client_type(buddy.name, buddy.service))
        if contact is None:
            log.error("No contact with name = %r found", buddy.name)
        else:
            return self.BlockContact(contact, callback = callback)

    @callbacks.callsback
    def UnblockContact(self, contact, callback = None):
        if contact.type == MSNAB.IMAddressInfoType.Circle:
            return self.UnblockCircle(contact, callback = callback)

        def after_bl_remove(resp = None):
            if not contact.OnAllowedList:
                self.AddContactToList(contact, MSNAB.MSNList.Allow, callback = callback)
            else:
                callback.success()

        if contact.OnBlockedList:
            self.RemoveContactFromList(contact,
                                       MSNAB.MSNList.Block,
                                       success = after_bl_remove,
                                       error = callback.error)

        elif not contact.OnAllowedList:
            after_bl_remove()

    @callbacks.callsback
    def _unblock_buddy(self, buddy, callback=None):
        contact = self.contact_list.GetContact(buddy.name, type = self.determine_client_type(buddy.name, buddy.service))
        if contact is None:
            log.error("No contact with name = %r found", buddy.name)
        else:
            return self.UnblockContact(contact, callback = callback)

    @callbacks.callsback
    def _authorize_buddy(self, buddy, authorize, callback=None):

        def after_block(*a):
            self.AddPendingContact(self.contact_list.GetContact(buddy.name, type = self.determine_client_type(buddy.name, buddy.service)), callback = callback)
            self.event('buddy_authed', buddy, authorize)

        if not authorize:
            self._block_buddy(buddy, success = after_block, error = after_block)
        else:
            after_block()

    @callbacks.callsback
    def BlockCircle(self, circle, callback = None):
        if circle.OnBlockedList:
            return

        def after_circle_block(resp):
            self.SendBlockCircleNSCommands(circle.AddressBookId, circle.HostDomain)
            self.contact_list.CircleRemoved(circle, MSNAB.MSNList.Allow)
            self.contact_list.CircleAdded(circle, MSNAB.MSNList.Block)
            self.contact_list.SetCircleStatus(circle, 'Offline')
            callback.success()

        self.AddContactToList(circle,
                              MSNAB.MSNList.BL,
                              success = after_circle_block,
                              error = callback.error)

    @callbacks.callsback
    def UnblockCircle(self, circle, callback = None):
        if not circle.OnBlockedList:
            return

        def after_circle_unblock(resp):
            self.SendUnblockCircleNSCommands(circle.AddressBookId, circle.HostDomain)
            self.contact_list.CircleRemoved(circle, MSNAB.MSNList.Block)
            self.contact_list.CircleAdded(circle, MSNAB.MSNList.Allow)
            callback.success()

        self.RemoveContactFromList(circle,
                                   MSNAB.MSNList.BL,
                                   success = after_circle_unblock,
                                   error = callback.error)

    def circle_removed(self, circleId):
        circle = self.CircleList.pop(circleId, None)
        if circle is None:
            return

        self.contact_remove(circle.account, str(MSNAB.MSNList.Forward), None)

    @callbacks.callsback
    def _add_buddy(self, lid, bname, bid, gid, service = 'msn', callback = None):
        # sharing.AddMember + call _add_buddy_to_list and/or _add_buddy_to_group
        bname = getattr(bname, 'name', bname)
        contact = self.contact_list.GetContact(bname, type = self.determine_client_type(bname, service))

        log.debug("_add_buddy(%r, %r, %r, %r)", lid, bname, bid, gid)

        if gid is not None:
            def after_add_member(resp = None):
                return self._add_buddy_to_group(bname, bid, gid, service = service, callback = callback)
        else:
            def after_add_member(resp = None):
                callback.success()

        def after_add_contact(resp = None):
            contact = self.contact_list.GetContact(bname, type = self.determine_client_type(bname, service = service))
            log.info("Contact successfully added to AddressBook. Adding to list=%r (contact = %r)", lid, contact)
            self.AddContactToList(contact,
                                  lid,
                                  success = after_add_member,
                                  error = callback.error)

        if lid in ('FL', 'Forward', 1, None):
            self._add_buddy_to_list(bname,
                                    service = service,
                                    success = after_add_member,
                                    error = callback.error)
        else:
            after_add_contact()

    def determine_client_type(self, bname, service = 'msn'):
        ctype = MSNAB.ClientType(service)
        if ctype is not None:
            return ctype

        if service == 'msn':
            if common.sms.validate_sms(bname):
                bname = common.normalize_sms(bname)
                return MSNAB.ClientType.PhoneMember
            else:
                return MSNAB.ClientType.PassportMember
        elif service == 'yahoo':
            return  MSNAB.ClientType.EmailMember

    @callbacks.callsback
    def _add_buddy_to_list(self, bname, service = 'msn', callback=None):
        # ab.ABContactAdd
        self.AddNewContact(bname, client_type = self.determine_client_type(bname, service), callback = callback)

    @callbacks.callsback
    def _add_buddy_to_group(self, bname, bid, gid, service = 'msn', callback = None):
        # ab.ABGroupContactAdd
        contact = self.contact_list.GetContact(bname, type = self.determine_client_type(bname, service))
        self.AddContactToGroup(contact, gid, callback = callback)

    @callbacks.callsback
    def _remove_buddy(self, lid, buddy, group, service = 'msn', callback=None):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        bname = getattr(buddy, 'name', buddy)
        contact = self.contact_list.GetContact(bname, type = self.determine_client_type(bname, service))

        role = MSNAB.MSNList(lid)

        def after_contact_remove(*a, **k):
            self.RemoveContactFromList(contact, int(role),
                                       success = lambda resp = None: self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.ContactSave, callback = callback),
                                       error = callback.error)

        if role != MSNAB.MSNList.Forward:
            # Removing from AL / BL / PL
            return after_contact_remove()

        def contact_remove_error(e):
            log.info("error removing buddy from contact list: %r", e)
            if fault_check(e, 'Contact Does Not Exist'):
                log.info("Got fault from ABContactDelete stating contact already deleted. Continuing remove process")
                return after_contact_remove()
            callback.error()

        def after_group_remove(*a, **k):
            log.info("buddy removed from group. now removing from contact list: %r", contact)
            self.RemoveContact(contact,
                               success = after_contact_remove,
                               error = contact_remove_error)

        if group is None:
            # Removing from contact list
            return after_group_remove()
        else:
            # removing from group
            self._remove_buddy_from_group(buddy, buddy.id, group, success = after_group_remove, error = callback.error)

#    @callbacks.callsback
#    def _remove_buddy_from_list(self, buddy, lid, callback = None):
#        log.info("remove buddy from list: %r, %r", contact, lid)
#        bname = getattr(buddy, 'name', buddy)
#        contact = self.contact_list.GetContact(bname, type = self.determine_client_type(bname, buddy.service))
#        self.RemoveContactFromList(contact, lid, callback = callback)

    @callbacks.callsback
    def _remove_buddy_from_group(self, name, bid, g_id, service = 'msn', callback = None):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)

        bname = getattr(name, 'name', name)
        contact = self.contact_list.GetContact(bname, type = self.determine_client_type(bname, service))

        def gcd_success(response):
            log.info("buddy removed from group. %r, %r", contact, g_id)
            if contact.client is None:
                contact.client = self
            self.contact_list.ContactRemoved(contact, MSNAB.MSNList.Forward, groups = [g_id])
            callback.success()

        if g_id is None:
            return gcd_success(None)

        def gcd_error(e, *a,**k):
            if fault_check(e, 'Contact Does Not Exist'):
                log.debug("Contact already removed from group.")
                return gcd_success(None)
            else:
                log.info("error removing buddy from group: %r, %r", a, k)
                callback.error()

        log.info("removing buddy from group. %r, %r", contact, g_id)
        ab.ABGroupContactDelete(client = self,
                                contact = contact,
                                group_id = g_id,
                                success = gcd_success,
                                error = gcd_error)


    @callbacks.callsback
    def UpdateContact(self, contact, abid = empty_guid, callback = None):
        abid = abid.lower()
        if getattr(contact, 'contactId', empty_guid) == empty_guid:
            return

        if not self.address_book.HasContact(abid, contact.contactId):
            return

        is_messenger_user = contact.contactInfo.isMessengerUser

        old_contact = self.address_book.SelectContactFromAddressBook(abid, contact.contactId)

        def after_update(resp):
            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.ContactSave, callback = callback)

        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        ab.ABContactUpdate(client = self,
                           old_contact = old_contact,
                           new_contact = contact,
                           PartnerScenario = SOAPServices.PartnerScenario.ContactSave if is_messenger_user else SOAPServices.PartnerScenario.Timer,
                           success = after_update,
                           error = callback.error)

    @callbacks.callsback
    def AddContactGroup(self, name, callback = None):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)

        def after_group_add(resp):
            new_group = self.group_add(name, resp.ABGroupAddResult.Guid)
            callback.success(new_group)

        def group_add_error(e):
            if fault_check(e, 'Group Already Exists'):
                log.info("Got fault from ABGroupAdd stating group already existed. Continuing add process")
                return after_group_add()
            else:
                callback.error()

        ab.ABGroupAdd(client = self,
                      name = name,
                      PartnerScenario = SOAPServices.PartnerScenario.GroupSave,
                      success = after_group_add,
                      error = group_add_error)

    _add_group = AddContactGroup

    @callbacks.callsback
    def RemoveContactGroup(self, group, callback = None):
        g_id = getattr(group, 'id', group)
        ab = self.getService(SOAPServices.AppIDs.AddressBook)

        def after_remove(resp):
            self.group_remove(g_id)
            self.address_book.groups.pop(g_id, None)
            callback.success()

        ab.ABGroupDelete(client = self,
                         group_id = g_id,
                         PartnerScenario = SOAPServices.PartnerScenario.Timer,
                         success = after_remove,
                         error = callback.error)

    _remove_group = RemoveContactGroup

    @callbacks.callsback
    def RenameGroup(self, group, new_name, callback = None):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)

        g_id = getattr(group, 'id', group)

        def after_update(resp):
            self.group_rename(g_id, new_name)
            callback.success()

        ab.ABGroupUpdate(client = self, group_id = g_id, name = new_name,
                         PartnerScenario = SOAPServices.PartnerScenario.GroupSave,
                         success = after_update, error = callback.error)

    _rename_group = RenameGroup

    @callbacks.callsback
    def AddContactToGroup(self, contact, group, callback = None):
        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        g_id = getattr(group, 'id', group)

        def after_add(resp):
            self.contact_list.ContactAdded(contact, MSNAB.MSNList.Forward, groups = [g_id])
            callback.success()

        ab.ABGroupContactAdd(client = self,
                             contact = contact,
                             group_id = g_id,
                             PartnerScenario = SOAPServices.PartnerScenario.GroupSave,
                             success = after_add,
                             error = callback.error)

    @callbacks.callsback
    def RemoveContactFromGroup(self, contact, group, callback = None):
        g_id = getattr(group, 'id', group)
        ab = self.getService(SOAPServices.AppIDs.AddressBook)

        def after_remove(resp):
            self.contact_list.ContactRemoved(contact, MSNAB.MSNList.Forward, groups = [g_id])
            callback.success()

        ab.ABGroupContactDelete(client = self,
                                contact = contact,
                                group_id = g_id,
                                PartnerScenario = SOAPServices.PartnerScenario.GroupSave,
                                success = after_remove,
                                error = callback.error)


    def RequestAddressBookById(self, abid, relationshipState = None, scenario = None):
        if relationshipState == MSNAB.RelationshipStates.Accepted:
            self.requestCircleCount += 1

        if relationshipState not in (None, MSNAB.RelationshipStates.Accepted, MSNAB.RelationshipStates.WaitingResponse):
            return

        self._sync_addressbook(abid = abid, PartnerScenario = SOAPServices.PartnerScenario.Initial)

    def GetCircle(self, name):
        return self.CircleList.get(MSNAB.Circle.MakeHash(name), None)

    @callbacks.callsback
    def InviteCircleMember(self, circleId, bname, message = None, callback = None):
        circle = self.GetCircle(circleId)
        if circle is not None:
            circleId = circle.abid # GetCircle accepts a couple of formats, but from here on out we just want the GUID
        else:
            uuid.UUID(circleId)

        if circle.OnBlockedList:
            log.error("Circle is blocked")
            return callback.error()

        if circle.CircleRole not in (MSNAB.CirclePersonalMembershipRole.Admin, MSNAB.CirclePersonalMembershipRole.AssistantAdmin):
            log.error("You are not an administrator")
            return callback.error()

        def after_manage(resp):
            log.info("invitation complete (invite %r to %r)", bname, circleId)
            callback.success()

        def manage_error(e):
            log.error("error occurred managing WL connection: %r", e)
            callback.error()

        def after_contact_create(resp):
            log.info("Created contact, now managing WL connection")

            annos = []
            if message is not None:
                annos.append((MSNAB.AnnotationNames.MSN_IM_InviteMessage, message))

            ab.ManageWLConnection(client = self,
                                  contactId = str(resp.CreateContactResult.ContactId).lower(),
                                  connection = True,
                                  presence = False,
                                  action = 1,
                                  relationshipRole = MSNAB.CirclePersonalMembershipRole.to_int(MSNAB.CirclePersonalMembershipRole.Member),
                                  relationshipType = MSNAB.RelationshipTypes.CircleGroup,
                                  PartnerScenario = SOAPServices.PartnerScenario.CircleInvite,
                                  Annotations = annos,
                                  abid = circleId,
                                  success = after_manage,
                                  error = manage_error)

        def contact_create_error(e):
            log.error("Error creating contact: %r", e)
            callback.error()

        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        ab.CreateContact(client = self, abid = circleId, email = bname,
                         success = after_contact_create,
                         error = contact_create_error)

    @callbacks.callsback
    def CreateContact(self, email = None, abid = None, callback = None):

        def create_contact_success(resp):
            callback.success()

        def create_contact_error(e = None):
            callback.error()

        sharing = self.getService(SOAPServices.AppIDs.Sharing)
        sharing.CreateContact(client = self, email = email, abid = abid,
                              success = create_contact_success,
                              error = create_contact_error,)

    @callbacks.callsback
    def CreateCircle(self, name, callback = None):

        def after_create_circle(resp = None):
            circleId = resp.CreateCircleResult.Id
            self.address_book.PendingCreateCircleList[resp.CreateCircleResult.Id] = name

            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.JoinedCircleDuringPush,
                                   success = lambda: self.InviteCircleMember(circleId, self.self_buddy.name, callback = callback))

        def create_circle_error(e = None):
            callback.error()

        sharing = self.getService(SOAPServices.AppIDs.Sharing)
        sharing.CreateCircle(client = self,
                             displayName = name,
                             PartnerScenario = SOAPServices.PartnerScenario.CircleSave,
                             success = after_create_circle,
                             error = create_circle_error,
                             )

    @callbacks.callsback
    def LeaveCircle(self, circle_id, callback = None):
        circle = self.GetCircle(circle_id)

        def after_leave_circle(resp):
            self.SendCircleNotifyRML(circle.abid, circle.hostDomain, circle.Lists, True)
            self.address_book.RemoveCircle(circle.CID, circle.abid)
            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.ABChangeNotifyAlert, callback = callback)

        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        ab.BreakConnection(client = self,
                           abid = circle.abid,
                           contactId = self.address_book.SelectSelfContactGuid(circle.abid),
                           PartnerScenario = SOAPServices.PartnerScenario.CircleLeave,
                           success = after_leave_circle,
                           )

    def SendCircleNotifyRML(self, abid, hostDomain, lists, block):
        li = 0
        for l in lists:
            li |= int(MSNAB.MSNList(l))

        circleHash = MSNAB.Circle.MakeHash(abid, hostDomain)
        rmls = self.make_adls({circleHash : int(li)}, not block)
        self.send_adl_sequence(rmls, 'RML')

    def OnJoinCircle(self, circle):
        log.info("Got new circle: %r", circle)
        self.on_contact_add(circle.account, circle.account, int(MSNAB.MSNList('FL')) | int(MSNAB.MSNList('RL')), None)

        if self.sent_initial_adls:
            self.send_initial_adl(MSNAB.Scenario.SendInitialCirclesADL)

    def OnRecvCircle(self, circle):
        log.info("Got existing circle: %r", circle)
        self.recv_contact(circle.account, int(MSNAB.MSNList('FL')) | int(MSNAB.MSNList('RL')), None, None, circle.account)

        if self.sent_initial_adls:
            self.send_initial_adl(MSNAB.Scenario.SendInitialCirclesADL)

    def OnCircleInvite(self, circle, inviter):
        log.debug("Circle Invite: inviter = %r, circle = %r", inviter, circle)

        def cb(join):
            if join:
                self._accept_circle_invite(circle, inviter)
            else:
                self._decline_circle_invite(circle, inviter)

        hooks.notify("digsby.msn.circle_invite", circle, inviter, cb)

    def _accept_circle_invite(self, circle, inviter):
        if circle.CircleRole != MSNAB.CirclePersonalMembershipRole.StatePendingOutbound:
            log.error("Not a pending circle! %r", circle)
            return

        def accept_invite_success(resp):
            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.JoinedCircleDuringPush)

        def accept_invite_error(e):
            log.error("Error accepting circle invite: %r", e)

        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        ab.ManageWLConnection(client = self,
                              contactId = str(circle.hiddenRep.contactId).lower(),
                              connection = True,
                              presence = False,
                              action = 1,
                              relationshipRole = MSNAB.CirclePersonalMembershipRole.to_int(MSNAB.CirclePersonalMembershipRole.NONE),
                              relationshipType = MSNAB.RelationshipTypes.CircleGroup,
                              PartnerScenario = SOAPServices.PartnerScenario.CircleStatus,
                              success = accept_invite_success,
                              error = accept_invite_error)

    def _decline_circle_invite(self, circle, inviter):
        def decline_invite_success(resp):
            self._sync_addressbook(PartnerScenario = SOAPServices.PartnerScenario.JoinedCircleDuringPush)

        def decline_invite_error(e):
            log.error("Error declining circle invite: %r", e)

        ab = self.getService(SOAPServices.AppIDs.AddressBook)
        ab.ManageWLConnection(client = self,
                              contactId = str(circle.hiddenRep.contactId).lower(),
                              connection = True,
                              presence = False,
                              action = 2,
                              relationshipRole = MSNAB.CirclePersonalMembershipRole.to_int(MSNAB.CirclePersonalMembershipRole.NONE),
                              relationshipType = MSNAB.RelationshipTypes.CircleGroup,
                              PartnerScenario = SOAPServices.PartnerScenario.CircleStatus,
                              success = decline_invite_success,
                              error = decline_invite_error)

    @Events.event
    def on_circle_member_joined(self, circle, contact):
        log.info("on_circle_member_joined(%r, %r)", circle, contact)
        return circle.account, contact.account

    @Events.event
    def recv_contact(self, name, lists_int, group_ids, soap = None, id = None):
        pass

    @callbacks.callsback
    def make_temp_circle(self, callback = None):
        message_headers = (
            (('Routing', '1.0'),
                 ('To', '%d:%s@%s' % (MSNAB.IMAddressInfoType.TemporaryGroup, self.contact_list.abid, MSNAB.Circle.hostDomain)),
                 ('From', '%d:%s;epid={%s}'  % (MSNAB.IMAddressInfoType.WindowsLive, self.self_buddy.name, str(self.get_machine_guid()))),
              ),
              (('Reliability', '1.0'),
                 ('Stream', '0'),
                 ('Segment', '0'),
              ),
              (('Publication', '1.0'),
                 ('Uri', '/circle'),
                 ('Content-Type', 'application/multiparty+xml'),
              ),
        )

        def success(msg):
            circle_id = email.message_from_string(msg.payload).get('From').split(':', 1)[-1]
            self.JoinCircleConversation(circle_id)
            callback.success(circle_id)

        payload = str(MSNC.MultiPartMime(headers = message_headers, body = ''))
        self.send_put(payload, success = success, error = callback.error)

    def leave_temp_circle(self, circle_id):
        message_headers = (
            (('Routing', '1.0'),
                 ('To', '%d:%s' % (MSNAB.IMAddressInfoType.TemporaryGroup, circle_id)),
                 ('From', '%d:%s;epid={%s}'  % (MSNAB.IMAddressInfoType.WindowsLive, self.self_buddy.name, str(self.get_machine_guid()))),
              ),
              (('Reliability', '1.0'),
                 ('Stream', '0'),
                 ('Segment', '1'),
              ),
              (('Publication', '1.0'),
                 ('Uri', '/circle/roster(IM)/user(%d:%s)' % (MSNAB.IMAddressInfoType.WindowsLive, self.self_buddy.name)),
                 ('Content-Type', 'application/circles+xml'),
              ),
        )

        payload = str(MSNC.MultiPartMime(message_headers, body = ''))
        self.send_del(payload)

    def JoinCircleConversation(self, circleId):
        return self.invite_to_circle(circleId, self.self_buddy.name)

    def invite_to_circle(self, circle_id, bname, message = None):
        log.info("Invite %r to %r", bname, circle_id)
        circle = self.GetCircle(circle_id)
        contact = self.contact_list.GetContact(bname)

        if circle is None:
            circle_type = MSNAB.IMAddressInfoType.TemporaryGroup
            circle_name, hostDomain = circle_id.lower().split('@')
        else:
            if circle.ADLCount != 0:
                circle.pending_join = True
                if bname != self.self_buddy.name:
                    log.error("Circle invite for %r to %r has been lost", bname, circle_id)
                return

            circle_type = circle.type
            circle_name = circle.abid.lower()
            hostDomain = circle.hostDomain

        def do_ns_invite():
            log.info("Perform invite %r to %r", bname, circle_id)
            message_headers = (
                (('Routing', '1.0'),
                     ('From', '%d:%s;epid={%s}'  % (MSNAB.IMAddressInfoType.WindowsLive, self.self_buddy.name, str(self.get_machine_guid()))),
                     ('To', '%d:%s@%s' % (circle_type, str(circle_name).lower(), hostDomain)),
                  ),
                  (('Reliability', '1.0'),
                     ('Segment', '0' if self.self_buddy.name == bname else '1'),
                     ('Stream', '0'),
                  ),
                  (('Publication', '1.0'),
                     ('Content-Type', "application/circles+xml"),
                     ('Uri', '/circle'),
                  ),
            )

            payload_doc = B.E('circle',
                              B.E('roster',
                                  B.E('id', 'IM'),
                                  B.E('user',
                                      B.E('id', '%d:%s' % (contact.type, contact.account)))))

            payload_data = etree.tostring(payload_doc, encoding = 'utf8')
            self.send_put(str(MSNC.MultiPartMime(message_headers, payload_data)))

        if circle_type == MSNAB.IMAddressInfoType.TemporaryGroup:
            return do_ns_invite()

        elif bname == self.self_buddy.name:
            return do_ns_invite()
        else:
            self.InviteCircleMember(circle_id, bname, message = message)

    def appear_offline_to(self, buddy):
        name = buddy.name
        c = self.contact_list.GetContact(buddy.name, type = self.determine_client_type(buddy.name, buddy.service))
        c.AddToList(MSNAB.MSNList.Hidden)
        adls = self.make_adls({c.Hash : int(MSNAB.MSNList.Hidden)})
        self.send_adl_sequence(adls)

    def appear_online_to(self, buddy):
        name = buddy.name
        c = self.contact_list.GetContact(buddy.name, type = self.determine_client_type(buddy.name, buddy.service))
        c.RemoveFromList(MSNAB.MSNList.Hidden)
        rmls = self.make_adls({c.Hash : int(MSNAB.MSNList.Hidden)})
        self.send_adl_sequence(rmls, cmd = 'RML')

    def get_auth_message_for(self, buddy):
        c = self.contact_list.GetContact(buddy.name, type = self.determine_client_type(buddy.name, buddy.service))
        if c is None:
            return ""

        if not self.address_book.HasMembership(MSNAB.ServiceFilters.Messenger, c.account, c.type, MSNAB.MSNList.Pending.role):
            return ''

        member = self.address_book.SelectBaseMember(MSNAB.ServiceFilters.Messenger, c.account, c.type, MSNAB.MSNList.Pending.role)

        message = member.GetAnnotation(MSNAB.AnnotationNames.MSN_IM_InviteMessage, '')
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]

        return message

    def _set_buddy_icon(self, status, clientid, icon_data, callback = None):
#        super(MSNP21Notification, self)._set_buddy_icon(status, clientid, icon_data, callback)

        finish = lambda *a: super(MSNP21Notification, self)._set_buddy_icon(status, clientid, icon_data, callback)

        storage = self.getSsoService(SOAPServices.SsoDomains.Storage)
        storage.UpdateDocument(client = self, resource_id = self.getProfileAttr('ExpressionProfile.Photo.ResourceID'),
                               docstream = dict(xsitype = 'PhotoStream',
                                                type = 'UserTileStatic',
                                                mimetype = 'image/png',
                                                data = icon_data),
                               scenario = SOAPServices.PartnerScenario.SyncChangesToServer,
                               success = finish,
                               error = finish)

    def getProfileAttr(self, attr):
        return operator.attrgetter(attr)(self.profile)

def split_contact_hash(a):
    return util.flatten(x.split(';via=') for x in a.split(':', 1))

def cmp_contact_domain(a, b):
    a_split = split_contact_hash(a)
    b_split = split_contact_hash(b)

    if len(a_split) == 0:
        return 1
    elif len(b_split) == 0:
        return -1

    a_name = a_split[1]
    b_name = b_split[1]

    return cmp(list(reversed(a_name.split('@', 1))), list(reversed(b_name.split('@', 1))))


def fault_check(fault, text):
    if hasattr(fault, 'typecode'):
        # ZSI object
        if fault.typecode.pname == 'Fault':
            Text = fault.Reason.Text
            if not isinstance(Text, list):
                Text = [Text]

            if any(text in T for T in Text):
                return True
    return False

