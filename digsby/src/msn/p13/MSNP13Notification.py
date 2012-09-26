from logging import getLogger
log = getLogger('msn.p13.ns')
import sys
import datetime
import urlparse
import functools
import uuid

import util
import util.callbacks as callbacks
import util.xml_tag as xml_tag
import util.cacheable as cacheable
import lxml.etree as ET
import lxml.builder as B
from util.Events import event
from util.primitives.error_handling import try_this
from util.primitives.funcs import get, isint
from util.primitives.mapping import Storage


from hub import Hub; hub = Hub.getInstance()
import ZSI

import msn
from msn.p12 import Notification as Super
from msn import Message
#from msn.SOAP import MSNABSharingService as MSNAB
MSNAB = Null

from mail.passport import escape, unescape

from msn.p10.MSNP10Notification import GroupId, ContactId

from ZSI import FaultException

defcb = dict(trid=True, callback=sentinel)

def get_fault(exc):
    return try_this(lambda: exc.fault.detail[0], None)

def zsiparse(soap, locatorname, name, raw):
    loc = getattr(soap, '%sLocator' % locatorname)()
    port = getattr(loc, 'get%sPort' % name)()
    binding = port.binding

    binding.reply_headers = Storage(type='text/xml')
    binding.data = raw
    return binding.Receive(getattr(soap,'%sResponseMessage' % name).typecode)

def soapcall(soap, locatorname, Locator='%sLocator', getPort='get%sPort',
              Message='%sMessage', Result='%sResult', Success='%sSuccess', Error='%sError',
              _name=None, cache=False):
    def wrapper(f):
        def wrapper2(*a, **k):
            log.error("%s.%s(%s, %s) was called", locatorname, f.func_name,
                      ', '.join('%r'%x for x in a),
                      ', '.join('%s=%r'%x for x in k.items()))
            raise NotImplementedError
        return wrapper2
    return wrapper
#    locator = getattr(soap, Locator % locatorname)()
#
#    def wrapper(f):
#        @functools.wraps(f)
#        def wrapper2(self, *a, **k):
#
#            name = f.__name__ if _name is None else _name
#            log.debug('%s.%s(%s %s)', locatorname, name, ', '.join(map(str,a+('',))),
#                      ', '.join('%s=%s' %i for i in k.items()))
#            port = getattr(locator, getPort % name)(tracefile = sys.stdout)
#
#            url = port.binding.url
#            domain = urlparse.urlparse(url)[1]
#
#            auth_header = soap.AddressBook.ABAuthHeader_Dec().pyclass()
#            auth_header.ManagedGroupRequest = False
#            auth_header.TicketToken = self.tokens[domain].Token
#
#            app_header  = soap.AddressBook.ABApplicationHeader_Dec().pyclass()
#            app_header.ApplicationId = str(self.app_id)
#            app_header.IsMigration = False
#            app_header.PartnerScenario = self.partner_scenario
#
#            request = getattr(soap, Message % name)()
#
#            e = None
#            try:
#                do_request = f(self, request, *a, **k)
#            except Exception, e:
#                do_request = False
#
#            if not do_request:
#                _v = 'BadRequest', request, a, k, e
#                if e:
#                    import traceback
#                    traceback.print_stack()
#                    traceback.print_exc()
#
#                log.debug('%s.%s failed: %r', locatorname, name, e)
#                return
#
#            try:
#                response = getattr(port, name)(request, soapheaders=(app_header, auth_header))
#            except FaultException, e:
#                log.debug('Error calling %s.%s: %r', locatorname, name, e)
#
#                if 'response' not in locals():
#                    response = None
#                try:
#                    err_handler = getattr(self, Error % name)
#                    # self may not have this attribute - in which case there is no error handler. so raise it again
#                except AttributeError, __:
#                    raise e
#                return err_handler(request, response, e, *a, **k)
#
#            result = getattr(response, Result % name, None)
#
#            should_cache = getattr(self, Success % name, lambda *a, **k:None)(request, result, *a, **k)
#            if cache and should_cache:
#                self._cache_soap(name, response)
#
#            return result
#        return wrapper2
#    return wrapper

class MSNP13Notification(Super):
    versions = ['MSNP13']
    client_chl_id = challenge_id = "PROD01065C%ZFN6F"
    client_chl_code = "O4BG@C7BWLYQX?5G"
    app_id = uuid.UUID('CFE80F9D-180F-4399-82AB-413F33A1FA11')

    # This is the old UUID, and it seems to be invalid now. ('09607671-1C32-421F-A6A6-CBFAA51AB5F4')

    events = Super.events | set(
        ('contact_role_info',
         'contact_cid_recv',
         'contact_profile_update',
         'soap_info',
         'contact_btype',
         'buddy_authed',
         'needs_status_message',
         )
    )

    def __init__(self, *a, **k):
        Super.__init__(self, *a, **k)
        self.members = {}
        self.partner_scenario = 'Initial'

        self.CONNECTED = False
        self.abId = uuid.UUID(int=0)


    @property
    def cache_path(self):

        import os, os.path
        val = os.path.join('msn', self.self_buddy.name, 'soapcache.dat')
        return val

    _soapcache = cacheable.cproperty({})

    @callbacks.callsback
    def _add_buddy_to_list(self, bname, callback=None):

        try:
            self.ABContactAdd(bname)
        except FaultException, e:
            print e.fault.detail
            if get_fault(e) == 'InvalidPassportUser':
                log.error('%s is not a valid passport user', bname)
                self.ABContactAdd(bname, type='federated')

                return True

        self.AddMember(bname, 'Allow')

        return True

    @callbacks.callsback
    def _add_buddy_to_group(self, bname, bid, gid, callback=None):
        if bname != self.self_buddy.name:
            self.ABGroupContactAdd(bname, bid, gid)
        return True

    @callbacks.callsback
    def _remove_buddy_from_group(self, name, bid, g_id, callback=None):
        self.ABGroupContactDelete(name, bid, g_id)
        return True

    @callbacks.callsback
    def _remove_buddy(self, lid, buddy, group, callback=None):

        role = dict(F='Forward',P='Pending', A='Allow',R='Reverse',B='Block')[lid[0]]

        if group and role in ('Forward',):
            log.info('Removing %r (%r) from %r (%r)', buddy, buddy.id, group, getattr(group, 'id',group))
            self.ABGroupContactDelete(buddy.name, buddy.id, get(group, 'id',group))
            #return True

#        else:


        if buddy.contactsoap is not None:
            self.ABContactDelete(buddy)
        else:
            log.info('Not calling ABContactDelete because no contact soap was received for %r', buddy)

        if role in buddy.mships:
            self.DeleteMember(buddy, role)
        else:
            log.info('Not calling DeleteMember because %s not in %r\'s member roles', role, buddy)

        callback.success()

    @callbacks.callsback
    def _add_buddy(self, lid, buddy, bid, gid, callback=None):

        lid = dict(AL='Allow',
                   FL='Forward',
                   BL='Block',
                   RL='Reverse',
                   PL='Pending').get(lid, lid)

        try:
            self.AddMember(getattr(buddy, 'name', buddy), lid)
        except FaultException, e:
            if get_fault(e) == 'InvalidPassportUser':
                try:
                    self.AddMember(getattr(buddy, 'name', buddy), lid, member_type='Email')
                except FaultException, e2:
                    print 'fault:',vars(e2.fault)
                    raise e2


        return True


    @callbacks.callsback
    def _block_buddy(self, buddy, callback=None):
        if 'Allow' in buddy.mships:
            self.DeleteMember(buddy, 'Allow')

        if 'Block' not in buddy.mships:
            self._add_buddy('Block', buddy, buddy.id, None, callback=callback)
#            try:
#                self.AddMember(buddy.name, 'Block')
#            except FaultException, e:
#                print 'fault', e.fault.detail
#                if e.fault.detail[0] == 'InvalidPassportUser':
#                    err_str = '%s is not a valid passport user, trying to add as federated', buddy.name
#                    log.error(errstr)
#                    hub.on_error(e)
#
#                    try:
#                        self.AddMember(buddy.name, 'Block', member_type='Email')
#                    except FaultException, e:
#                        if e.fault.detail[0] =='MemberAlreadyExists':
#                            log.info('%r already on %s list', buddy, 'Block')

#        callback.success()

    @callbacks.callsback
    def _unblock_buddy(self, buddy, callback=None):
        if 'Block' in buddy.mships:
            self.DeleteMember(buddy, 'Block')

        if 'Allow' not in buddy.mships:
            try:
                self.AddMember(buddy.name, 'Allow')
            except FaultException, e:
                print e.fault.detail
                if get_fault(e) == 'InvalidPassportUser':
                    log.error('%s is not a valid passport user', buddy.name)

                    try:
                        self.AddMember(buddy.name, 'Allow', member_type='Email')
                    except FaultException, e:
                        if get_fault(e) =='MemberAlreadyExists':
                            log.info('%r already on %s list', buddy, 'Allow')


        return True

    @callbacks.callsback
    def _authorize_buddy(self, buddy, authorize, callback=None):

        if authorize:
            self._unblock_buddy(buddy, callback=callback)
            bname = buddy.name
            try:
                self.ABContactAdd(bname)
            except FaultException, e:
                print e.fault.detail
                if get_fault(e) == 'InvalidPassportUser':
                    log.error('%s is not a valid passport user', bname)
                    self.ABContactAdd(bname, type='federated')

        else:
            self._block_buddy(buddy, callback=callback)

        try:
            if 'Pending' in buddy.mships:
                self.DeleteMember(buddy, 'Pending')
        except:
            import traceback;traceback.print_exc()
            raise
        else:
            self.event('buddy_authed', buddy, authorize)

    def _add_group(self, groupname, callback):
        val = self.ABGroupAdd(groupname)
        callback.success()

    def _remove_group(self, groupid, callback=None):
        self.ABGroupDelete(groupid)
        if callback:
            callback.success()
        return True

    def _rename_group(self, group, newname, callback):
        self.ABGroupUpdate(group, newname)
        if callback:
            callback.success()
        return True

    def _get_profile(self, buddy, callback):
        request = xml_tag.tag('GetXmlFeed')

        ri = request.refreshInformation

        ri.cid = buddy.CID
        ri.storageAuthCache = ''
        ri.market = '%s-%s' % (hub.language.lower(), hub.country.upper())
        ri.brand = ''
        ri.maxElementCount = 15
        ri.maxCharacterCount = 200
        ri.maxImageCount = 6
        ri.applicationId = 'Messenger Client 8.0'
        ri.updateAccessedTime = False

        yesterday = datetime.datetime.today() - datetime.timedelta(1)
        ri.spaceLastViewed = yesterday.isoformat()
        ri.profileLastViewed = yesterday.isoformat()
        ri.contactProfileLastViewed = yesterday.isoformat()

        ri.isActiveContact = False

        fs = ri.foreignStore
        fs.itemType = 'Profile'
        fs.foreignId = 'MyProfile'
        fs.lastChanged = yesterday.isoformat()
        fs.lastViewed = yesterday.isoformat()

        auth = xml_tag.tag('AuthTokenHeader')
        #auth.Token = self.ticket.encode('xml')
        token = str(self.tokens['spaces.live.com'].received.RequestedSecurityToken.BinarySecurityToken)
        assert token, token.received._to_xml()

        auth.Token = escape(token)
        auth.AuthPolicy = self.tokens['spaces.live.com'].policyref

        env = xml_tag.tag("envelope") #soap_envelope("http://www.msn.com/webservices/spaces/v1/")

        env.Header(auth)
        env.Body(request)
        #del env._children[0]
        print env._to_xml(pretty=False)
        response = xml_tag.post_xml("http://cid-%X.cc.services.spaces.live.com/contactcard/contactcardservice.asmx" % int(self.self_buddy.CID),
                                 env,
                                 success=lambda t: self.incoming_profile(t, buddy),
                                 error  =lambda e: self.incoming_profile(e, buddy, True)
                                 #Cookie=token
                                 )

    def incoming_profile(self, t, buddy, error=False):
        if error:
            print 'Bad profile response for buddy profile', buddy, repr(t)
            raise t
        #print t._to_xml()
        buddy.update_contact_card(t.Body.GetXmlFeedResponse.GetXmlFeedResult.contactCard)

    def recv_not(self, msg):
        data = xml_tag.tag(xml_tag.tag(msg.payload).MSG.BODY._cdata)

        if not data.OwnerCID:
            return

        cid = int(data.OwnerCID)
        #last_mod = str(data.LastModifiedDate)
        has_new = bool(data.HasNewItem)

        if has_new:
            self.event('contact_profile_update', cid)

    def recv_gcf(self, msg):
        '''
        hooray for XML verbosity telling us nothing is blocked
        '''
        log.debug('got gcf')

    def adl(self, msg):
        log.debug('got adl: %r', (msg.args,msg.payload))

        if not msg.trid: # from the server

            self._sync_memberships(False)
#            ml = tag(msg.payload)
#
#            contacts = []
#            for d in ml:
#                if d._name != 'd': continue
#
#                for c in d:
#                    if c._name != 'c': continue
#
#                    bname = '%s@%s' % (c['n'], d['n'])
#
#                    self.event('on_contact_add', bname, None, int(c['l']), None)
#                    self.event('on_contact_alias', bname, msn.util.url_decode(c['f']))
#                    #self.apply_list_flags(int(c['l']), buddy)

    def recv_rml(self, msg):

        log.info('RML: %s', msg)
        if msg.args:
            msg, = msg.args
            if msg != 'OK':
                raise msn.GeneralException('Unknown RML error')
        else:
            print 'UNKNOWN RML MSG:',msg

    def recv_uun(self, msg):
        name, __ = msg.args
        raise NotImplementedError

    def recv_ubn(self, msg):
        name, __ = msg.args
        raise NotImplementedError

    def recv_cvq(self, msg):
        cur_ver, max_ver, min_ver, dl_link, homepage = msg.args
        raise NotImplementedError

#    def xfr(self, *a, **k):
#        #log.warning('Got MSNP13 XFR, which may not be fully implemented!')
#        return Super.xfr(self, *a, **k)

    def recv_rng(self, msg):
        log.info('Got a RNG from %s', msg.args[3])
        msg.args = msg.args[:5]
        return Super.recv_rng(self, msg)

    def recv_adc(self, *a, **k):
        raise msn.WrongVersionException

#    def send_adc(self, *a, **k):
#        raise msn.WrongVersionException

    def recv_rem(self, *a, **k):
        raise msn.WrongVersionException

#    def send_rem(self, *a, **k):
#        raise msn.WrongVersionException

    def recv_syn(self, *a, **k):
        #raise msn.WrongVersionException
        pass

    def recv_uux(self, msg):
        # confirmation that our message was set right
        pass

    def recv_gtc(self, *a, **k):
        raise msn.WrongVersionException

    def usr_ok(self, msg):

        username, verified = msg.args[:2]
        log.debug('got usr_ok')
        assert username == self.self_buddy.name
        #self.self_buddy.remote_alias = username
        self.self_buddy.verified = bool(verified)

        self._get_connected()

    def send_adl(self, ml):
        log.debug('sending adl')
        self.socket.send(Message('ADL', payload=ml._to_xml(pretty=False).strip()), **defcb)

    def recv_adl(self, msg):
        '''
        ADL 0 86\r\n
        <ml><d n="hotmail.com"><c n="digsby06" t="1" l="8" f="digsby%20oh%20sicks" /></d></ml>

        ADL 19 60\r\n
        <ml><d n="yahoo.com"><c n="digsby04" l="2" t="32" /></d></ml>
        '''
        'ADL 0 81\r\n<ml><d n="yahoo.com"><c n="digsby06" t="32" l="8" f="asdlkj%20asdlkj" /></d></ml>\r\n'

        t = xml_tag.tag(str(msg.payload))

        for d in t._children:
            domain = d['n']

            for c in d._children:
                username = c['n']
                type = int(c['t'])
                l_id = int(c['l'])
                mfn  = c['f'].decode('url').decode('fuzzy utf8')

                name = '%s@%s' % (username,domain)

                if not msg.trid:
                    self._sync_memberships(False)
#                    self.event('recv_contact', name, l_id, None, None)
#                    self.event('contact_alias', name, mfn)

        if not self.CONNECTED:
            log.info('got ADL, changing to connected')
            self.CONNECTED = True
            #self.event('on_connect')


    def send_rml(self, buddy, l_id):

        if buddy._btype == 'mob':
            return

        n = buddy.name

        u, d = n.split('@')
        ml = xml_tag.tag('ml')
        ml.d['n']=d
        ml.d.c['n']=u
        ml.d.c['l']=dict(forward=1, allow=2, block=4, reverse=8, pending=16)[l_id.lower()]
        ml.d.c['t']=dict(im=1, msn=1, mob=4, fed=32)[buddy._btype]

        self.socket.send(Message('RML', payload=ml._to_xml(pretty=False).strip()), **defcb)

    def send_cvq(self, *a, **k):
        raise NotImplementedError

    def send_uux(self, msg='', callback=sentinel):
        data = xml_tag.tag('Data')
        data.PSM = msg
        data.CurrentMedia = ''
        data.MachineGuid = uuid.uuid1()

        self.socket.send(Message('UUX', payload=data._to_xml(pretty=False).encode('utf-8')), trid=True, callback=callback)

    def send_gtc(self, *a, **k):
        raise msn.WrongVersionException

    def process_groups(self, groups):
        #util.tag_view(groups)
        for g in groups:
            gid = GroupId(str(g.GroupId))
            gname = str(g.GroupInfo.Name)

            self.event('group_receive', gname, gid)

    def process_contacts(self, contacts):

        for c in contacts:
            name, alias, guid, cid, groups, bprops = self.process_contact(c)
            if not name: continue

            self.event('recv_contact', name, ['FL'], groups, c, guid)
            self.event('contact_id_recv', name, guid)

            if alias:
                self.event('contact_alias', name, alias)

            if cid:
                self.event('contact_cid_recv', name, cid)

            for prop, val in bprops:
                self.event('recv_prop', name, prop, val)

    def process_contact(self, c):
        guid = ContactId(str(c.ContactId))
        i = c.ContactInfo
        if str(i.ContactType) == 'Me':
            for annotation in i.Annotations.Annotation:
                _name = str(annotation.Name)
                try:
                    _val  = int(annotation.Value)
                except ValueError:
                    _val  = str(annotation.Value)

                if _name == 'MSN.IM.MBEA':
                    self.event('recv_prop', self.self_buddy.name, 'mbe', bool(_val))
                elif _name == 'MSN.IM.GTC':
                    self.event('on_rl_notify', bool(_val))
                elif _name == 'MSN.IM.BLP':
                    self.allow_unknown_contacts = bool(_val)
                    self.event('on_blist_privacy', bool(_val))
                elif _name == 'MSN.IM.RoamLiveProperties':
                    pass

        name = i.PassportName

        if name is None and i.Emails is not None:
            es = i.Emails.ContactEmail
            if es:
                for e in es:
                    if e.ContactEmailType == 'Messenger2':
                        name = 'fed:'+e.Email

        alias = i.DisplayName
        if alias:
            alias = alias.decode('url').decode('fuzzy utf8')

        cid = i.CID

        groups = [GroupId(gid) for gid in i.GroupIds.Guid] if i.GroupIds else []

        bprops = []
        bprops.append(('mob', i.IsNotMobileVisible))
        bprops.append(('mbe', i.IsMobileIMEnabled))
        bprops.append(('hsb', i.HasSpace))

        return name, alias, guid, cid, groups, bprops

    @soapcall(MSNAB, 'ABService', cache=False)
    def ABFindAll(self, request, deltas=False, lastChange='0001-01-01T00:00:00.0000000-08:00'):
        request.set_element_abId(request.new_abId(self.abId))
        request.AbView = 'Full'
        #request.DeltasOnly = True
        #request.LastChange = datetime.datetime(2007, 11, 12, 19, 9, 54, 63).timetuple()
        request.DeltasOnly = deltas
        request.LastChange = lastChange

        return True

    def ABFindAllError(self, request, result, exc, deltas=False, lastChange='0001-01-01T00:00:00.0000000-08:00'):
        if get_fault(exc) == 'ABDoesNotExist':
#            self.abId = uuid.UUID(str(exc.fault.detail[1]).split('=')[-1].strip())
#
#            # now that we have the right abId, we should be able to complete this successfully.
#            return self.ABFindAll(deltas=deltas, lastChange=lastChange)
            self.ABAdd()
            self.ABFindAll()
        else:
            raise exc

    def ABFindAllSuccess(self, request, result, deltas=False, lastChange='0001-01-01T00:00:00.0000000-08:00'):

        should_cache = True

        if deltas and (result.Groups or result.Contacts):
            # We used our cache timestamp but there were changes! we need to request the whole thing again =(
            log.info('ABFindAllResult is out of date, getting new version')
            should_cache = False # this result should not be cached.
            self.ABFindAll() # but this one will be
        elif deltas:
            # we used our cache timestamp and there were no changes (yay). Use the cached copy.
            log.info('ABFindAllResult was empty, using cached version')
            cached_data = self._soapcache.get('ABFindAll')
            old_response = zsiparse(MSNAB, 'ABService', 'ABFindAll', cached_data)
            result = old_response.ABFindAllResult
            # don't cache the (empty) response we just got.
            should_cache = False
        else:
            # we didnt ask for the cached version. result is the right result

            log.info('Got new ABFindAllResult')
            pass

        self.process_blist(result)
        return should_cache

    @soapcall(MSNAB, 'ABService')
    def ABAdd(self, request, default=True):
        info = request.AbInfo = request.new_abInfo()
        info.Name = ''
        info.OwnerPuid = 0
        info.OwnerEmail = self.self_buddy.name
        info.FDefault = default

        return True

    def ABAddSuccess(self, request, result):
        self.abid = uuid.UUID(result)

    @soapcall(MSNAB, 'ABService')
    def ABContactAdd(self, request, buddy_or_name, type='LivePending'):
        '''
        <ABContactAdd xmlns="http://www.msn.com/webservices/AddressBook">
            <abId>00000000-0000-0000-0000-000000000000</abId>
            <contacts>
                <Contact xmlns="http://www.msn.com/webservices/AddressBook">
                    <contactInfo>
                        <contactType>LivePending</contactType>
                        <passportName>XXX@YYY.com</passportName>
                        <isMessengerUser>true</isMessengerUser>
                        <MessengerMemberInfo>
                            <DisplayName>petit</DisplayName>
                        </MessengerMemberInfo>
                    </contactInfo>
                </Contact>
            </contacts>
            <options>
                <EnableAllowListManagement>true</EnableAllowListManagement>
            </options>
        </ABContactAdd>
        '''
        name = getattr(buddy_or_name, 'name', buddy_or_name)

        request.AbId = str(self.abId)
        contacts = request.Contacts = request.new_contacts()
        Contact = contacts.new_Contact(); contacts.Contact.append(Contact)

        info = Contact.ContactInfo = Contact.new_contactInfo()

        getattr(self, '_setup_info_%s' % type.lower())(info, name)

        options = request.Options = request.new_options()
        options.EnableAllowListManagement = True

        return True

    def _setup_info_livepending(self, info, name):
        info.ContactType = 'LivePending'
        info.PassportName = name

    def _setup_info_federated(self, info, name):
        '''
        <emails>
            <ContactEmail>
                <contactEmailType>Messenger2</contactEmailType>
                <email>digsby04@yahoo.com</email>
                <isMessengerEnabled>true</isMessengerEnabled>
                <Capability>32</Capability>
                <propertiesChanged>Email IsMessengerEnabled Capability</propertiesChanged>
            </ContactEmail>
        </emails>
        '''

        changed = []

        info.Emails = info.new_emails()
        email = info.Emails.new_ContactEmail(); info.Emails.ContactEmail.append(email)
        email.ContactEmailType = 'Messenger2'

        def set(attr, val):
            changed.append(attr)
            setattr(email, attr, val)

        set("IsMessengerEnabled", True)
        set("Email", name)
        set('Capability', 0x20)

        email.PropertiesChanged = ' '.join(changed)

    def ABContactAddSuccess(self, request, result, name, type='LivePending'):
        if type == 'federated':
            tagged_name = 'fed:'+name
        else:
            tagged_name = name

        self.event('on_contact_add', tagged_name, ContactId(result.Guid), ['FL'], [])

    def ABContactAddError(self, request, response, exc, name, type='LivePending'):
        if get_fault(exc) == 'ContactAlreadyExists':
            self.ABContactAddSuccess(request, response, name, type)
        else:
            raise exc

    @soapcall(MSNAB, 'ABService')
    def ABContactDelete(self, request, buddy):
        request.AbId = str(self.abId)
        request.Contacts = request.new_contacts()
        c = request.Contacts.new_Contact(); request.Contacts.Contact.append(c)

        c.ContactId = str(buddy.id)

        return True

    def ABContactDeleteSuccess(self, request, response, buddy):
        self.event('contact_remove', buddy.id, 'FL', None)
        self.send_rml(buddy, 'Forward')

    def ABContactDeleteError(self, request, response, exc, buddy):
        if get_fault(exc) == 'ContactDoesNotExist':
            self.ABContactDeleteSuccess(request, response, buddy)
        else:
            raise exc

    @soapcall(MSNAB, 'ABService')
    def ABGroupContactAdd(self, request, bname, bid, groupid):
        '''
        <abId>00000000-0000-0000-0000-000000000000</abId>
        <groupFilter>
            <groupIds>
                <guid>62b9fd12-df18-4b39-837b-035eef22df29</guid>
            </groupIds>
        </groupFilter>
        <contacts>
            <Contact>
                <contactId>239abf4f-64a8-4c7b-bc5d-78875e00798d</contactId>
            </Contact>
        </contacts>
        '''
        request.AbId = str(self.abId)
        gfilter = request.GroupFilter = request.new_groupFilter()
        gids = gfilter.GroupIds = gfilter.new_groupIds()
        gids.Guid.append(gids.new_guid(str(groupid)))

        contacts = request.Contacts = request.new_contacts()
        contact = contacts.new_Contact(); contacts.Contact.append(contact)
        contact.ContactId = str(bid)

        return True

    def ABGroupContactAddSuccess(self, request, result, bname, bid, groupid):

        if not isinstance(groupid, GroupId):
            groupid = GroupId(groupid)

        self.event('on_contact_add', bname, bid, ['FL'], [groupid])

    @soapcall(MSNAB, 'ABService')
    def ABGroupAdd(self, request, gname):

        request.AbId = str(self.abId)
        options = request.GroupAddOptions = request.new_groupAddOptions()
        options.FRenameOnMsgrConflict = False

        info_ = request.GroupInfo = request.new_groupInfo()
        info = info_.GroupInfo = info_.new_GroupInfo()

        info.Name = gname
        info.GroupType = "C8529CE2-6EAD-434d-881F-341E17DB3FF8"
        info.FMessenger = False

        annots = info.Annotations = info.new_annotations()
        annot = annots.new_Annotation(); annots.Annotation.append(annot)
        annot.Name = 'MSN.IM.Display'
        annot.Value = '1'

        return True

    def ABGroupAddError(self, request, result, exc, gname):
        if get_fault(exc) == 'GroupAlreadyExists':
            detail = exc.fault.detail
            gid = None
            try:
                gid = detail[3]['conflictObjectId']
            except (AttributeError, KeyError):
                log.info('Couldn\'t get conflict ID, here\'s the detail: %r', detail)

            if gid is not None:
                return self.ABGroupAddSuccess(request, Storage(Guid=gid), gname)
            else:
                raise exc
        else:
            raise exc


        '''
            <detail>
                <errorcode xmlns="http://www.msn.com/webservices/AddressBook">GroupAlreadyExists</errorcode>
                <errorstring xmlns="http://www.msn.com/webservices/AddressBook">Group Already Exists </errorstring>
                <machineName xmlns="http://www.msn.com/webservices/AddressBook">BAYABCHWBB143</machineName>
                <additionalDetails>
                    <conflictObjectId>D06C117E-F8A8-4167-B693-5241CE0CAAF3</conflictObjectId>
                </additionalDetails>
            </detail>
        '''

    def ABGroupAddSuccess(self, request, result, gname):
        gid = GroupId(result.Guid)
        self.event('group_add', gname, gid)

        return gid

    @soapcall(MSNAB, 'ABService')
    def ABGroupUpdate(self, request, gid, newname):
        '''
        <abId>
            00000000-0000-0000-0000-000000000000
        </abId>
        <groups>
            <Group>
                <groupId>
                    4e851eb6-4714-4cfd-9216-a5886d3b4201
                </groupId>
                <groupInfo>
                    <name>
                        bbbbbbbbbbbbb
                    </name>
                </groupInfo>
                <propertiesChanged>
                    GroupName
                </propertiesChanged>
            </Group>
        </groups>
        '''

        request.AbId = str(self.abId)

        gs = request.Groups = request.new_groups()
        g = gs.new_Group(); gs.Group.append(g)
        g.GroupId = gid
        gi = g.GroupInfo = g.new_groupInfo()
        gi.Name = newname
        g.PropertiesChanged = 'GroupName'

        return True

    def ABGroupUpdateSuccess(self, request, result, gid, newname):
        self.event('group_rename', gid, newname)

    @soapcall(MSNAB, 'ABService')
    def ABGroupDelete(self, request, gid):
        '''
        <abId>00000000-0000-0000-0000-000000000000</abId>
        <groupFilter>
            <groupIds>
                <guid>8fd9b0fc-7abf-4211-9122-bef3b8a326c1</guid>
            </groupIds>
        </groupFilter>
        '''
        request.AbId = str(self.abId)

        gfilter = request.GroupFilter = request.new_groupFilter()
        gids = gfilter.GroupIds = gfilter.new_groupIds()
        gids.Guid.append(gids.new_guid(str(gid)))

        return True

    def ABGroupDeleteSuccess(self, request, result, gid):
        self.event('group_remove', gid)

    def ABGroupDeleteError(self, request, result, exc, gid):
        if get_fault(exc) == 'GroupDoesNotExist':
            self.ABGroupDeleteSuccess(request, result, gid)
        else:
            raise exc

    @soapcall(MSNAB, 'ABService')
    def ABGroupContactDelete(self, request, name, bid, groupid):
        '''
        <abId>00000000-0000-0000-0000-000000000000</abId>
        <contacts>
            <Contact>
                <contactId>239abf4f-64a8-4c7b-bc5d-78875e00798d</contactId>
            </Contact>
        </contacts>
        <groupFilter>
            <groupIds>
                <guid>4e851eb6-4714-4cfd-9216-a5886d3b4201</guid>
            </groupIds>
        </groupFilter>
        '''

        request.AbId = str(self.abId)
        gfilter = request.GroupFilter = request.new_groupFilter()
        gids = gfilter.GroupIds = gfilter.new_groupIds()
        gids.Guid.append(gids.new_guid(str(groupid)))

        contacts = request.Contacts = request.new_contacts()
        contact = contacts.new_Contact(); contacts.Contact.append(contact)
        contact.ContactId = str(bid)

        return True

    def ABGroupContactDeleteSuccess(self, request, result, name, bid, groupid):
        self.event('contact_remove',  bid, 'FL', groupid)

    def ABGroupContactDeleteError(self, request, result, exc, name, bid, groupid):
        if get_fault(exc) == 'ContactDoesNotExist':
            self.ABGroupContactDeleteSuccess(request, result, name, bid, groupid)
        else:
            raise exc

    @soapcall(MSNAB, 'ABService')
    def ABContactUpdate(self, request, contact):
        request.AbId = str(self.abId)
        contacts = request.Contacts = request.new_contacts()

        contacts.Contact.append(contact)

        return True

    def ABContactUpdateSuccess(self, request, result, contact):
        log.info('Got ABContactUpdateSuccess')

    @soapcall(MSNAB, 'SharingService', cache=False)
    def FindMembership(self, request, services=None, view='Full', deltas=False, lastchange='0001-01-01T00:00:00.0000000-08:00'):

        if services is None:
            services = ('Messenger',
                        'Invitation',
                        'SocialNetwork',
                        'Space',
                        'Profile')
        else:
            if not isinstance(services, (tuple, list)):
                services = (services,)

        request.View = view
        request.DeltasOnly = deltas
        request.LastChange = lastchange
        request.ServiceFilter = filter = request.new_serviceFilter()
        request.ServiceFilter.Types = types = filter.new_Types()
        types.ServiceType.extend(services)

        return True

    def FindMembershipError(self, request, result, exc, services=None, view='Full', deltas=False,
                              lastchange='0001-01-01T00:00:00.0000000-08:00'):

        if get_fault(exc) == 'ABDoesNotExist':
            self.abId = uuid.UUID(str(exc.fault.detail[1]).split('=')[-1].strip())

            # now that we have the right abId, we should be able to complete this successfully.
            #return self.FindMembership(services, view, deltas, lastchange)
        elif get_fault(exc) == 'FullSyncRequired':
            self.FindMembership(services, view='Full', deltas=False)
        else:
            raise exc


    def FindMembershipSuccess(self, request, result, services=None, view='Full', deltas=False, lastchange='0001-01-01T00:00:00.0000000-08:00'):

        # cache result
        #self._cache_soap('FindMembership', result)

        # this will be returned
        should_cache = True



        if deltas and result is not None:
            # We used our cache timestamp but there were changes! we need to request the whole thing again =(
            log.info('FindMembershipResult is out of date, getting new version')
            should_cache = False  # this result should not be cached
            self.FindMembership() # this one will be
        elif deltas:
            # we used our cache timestamp and there were no changes (yay). Use the cached copy.
            log.info('FindMembershipResult was empty, using cached version')
            cached_data = self._soapcache.get('FindMembership')
            old_response = zsiparse(MSNAB, 'SharingService', 'FindMembership', cached_data)
            result = old_response.FindMembershipResult
            # don't cache the (empty) response we just got.
            should_cache = False
        else:
            # we didnt ask for the cached version. result is the right result
            log.info('Got new FindMembershipResult')
            pass

        self.process_memberships(result)

        return should_cache

    @soapcall(MSNAB, 'SharingService')
    def AddMember(self, request, name, role, state='Accepted',
                  handle_type='Messenger', member_type='Passport'):

        request.ServiceHandle = handle = request.new_serviceHandle()
        handle.Id = 0
        handle.Type = handle_type
        handle.ForeignId = ''

        memberships = request.Memberships = request.new_memberships()
        membership = memberships.new_Membership()
        memberships.Membership.append(membership)
        membership.MemberRole = role
        members = membership.Members = membership.new_Members()

        member = getattr(MSNAB, '%sMember' % member_type, MSNAB.BaseMember)()
        member.Type = member_type
        member.State = state

        ds = member.DefiningService = member.new_DefiningService()
        ds.Id = 0
        ds.Type = handle_type
        ds.ForeignId = ''
        '''
          <DefiningService>
            <Id>
              0
            </Id>
            <Type>
              Messenger
            </Type>
            <ForeignId />
          </DefiningService>
        '''

        name_name = MSNAB.member_names[type(member)]
        setattr(member, name_name, name)

        if member_type == 'Email':
            annots = member.Annotations = member.new_Annotations()
            annot = annots.new_Annotation(); annots.Annotation.append(annot)

            annot.Name = 'MSN.IM.BuddyType'
            annot.Value = '32:'

        members.Member.append(member)

        return True

    def AddMemberSuccess(self, request, result, name, role, state='Accepted',
                           handle_type='Messenger', member_type='Passport'):
        assert result is None

        # the Membership and Member sequences should nearly always be of length 1

        for mship in request.Memberships.Membership:

            names = []
            mrole = mship.MemberRole

            for member in mship.Members.Member:

                _name = getattr(member, MSNAB.member_names[member.Type], name) or name

                print _name, mrole
                self.event('soap_info', _name,
                           member.Type, member, mrole)

                self.event('on_contact_add', _name, None, [mrole[0]+'L'], None)
                names.append(_name)

            log.error('Going to send ADL (%s) for %r', mrole, names)

    def AddMemberError(self, request, result, exc, name, role, state='Accepted',
                       handle_type = 'Messenger', member_type='Passport'):

        if get_fault(exc) == 'MemberAlreadyExists':
            return self.AddMemberSuccess(request, result, name, role, state, handle_type, member_type)
        else:
            raise exc

    @soapcall(MSNAB, 'SharingService')
    def DeleteMember(self, request, buddy, role, handle_type='Messenger'):

        request.ServiceHandle = handle = request.new_serviceHandle()
        handle.Id = 0
        handle.Type = handle_type
        handle.ForeignId = ''

        memberships = request.Memberships = request.new_memberships()
        membership = memberships.new_Membership()
        memberships.Membership.append(membership)
        members = membership.Members = membership.new_Members()

        membership.MemberRole = role

        if role not in buddy.mships:
            log.error('%s not in buddy\'s roles: %r', role, buddy.mships.keys())
            return False

        old = buddy.mships[role]

        copy = type(old)()

        copy.MembershipId = old.MembershipId
        copy.Type = old.Type
        copy.State = old.State

        name_name = MSNAB.member_names[copy.Type]

        if not copy.MembershipId:
            the_name = getattr(old, name_name, None) or \
                       getattr(buddy.contactsoap.ContactInfo, name_name, None)

            if the_name:
                setattr(copy, name_name, the_name)
            else:
                copy.CID = old.CID or buddy.contactsoap.ContactInfo.CID

        members.Member.append(copy)

        return True

    def DeleteMemberError(self, request, result, exc, buddy, role, handle_type="Messenger"):
        if get_fault(exc) == 'MemberDoesNotExist':
            buddy.mships.pop(role, None)
            self.event('contact_remove', buddy.name, role[0]+'L', None)
            self.send_rml(buddy, role)
        else:
            raise exc

    def DeleteMemberSuccess(self, request, result, buddy, role, handle_type="Messenger"):
        assert result is None, result

#        if buddy._btype != 'msn':
#            return

        # the Membership and Member sequences should nearly always be of length 1

        try:
            for mship in request.Memberships.Membership:
                for member in mship.Members.Member:
                    name = getattr(member, MSNAB.member_names[member.Type], buddy.name) or buddy.name
                    role = mship.MemberRole
                    buddy.mships.pop(role, None)
                    self.event('contact_remove', name, role[0]+'L', None)
                    self.send_rml(buddy, role)
        except Exception:
            import traceback;traceback.print_exc()


    def process_members(self, role, members):

        # List ids are AL, PL, BL, RL, FL.
        # Roles are Allow, Block, Reverse, Pending. Allow means AL and FL

        #l = getattr(self, '%s_list' % role.lower())
#        util.tag_view(members)
#        print members._to_xml()
        for m in members.Member:
            typ = m.Type

            mshipid = m.MembershipId
            alias = (m.DisplayName or '').decode('url').decode('fuzzy utf8')

            cid = None

            if typ == 'Passport':
                name = m.PassportName
                cid = m.CID
                btype = 0x01
            elif typ == 'Phone':
                name = m.PhoneNumber
                btype = 0x04
            elif typ == 'Email':
                name = m.Email
                btype = 0x20
            else:
                log.error('Unknown member.Type: %s', m.Type)
                btype = 1

            self.event('contact_btype', name, btype)
            self.event('soap_info', name, typ, m, role)
            self.event('contact_alias', name, alias or name)

            if cid:
                self.event('contact_cid_recv', name, cid)

            l_ids = set()
            l_ids.add(role[0] + 'L')

            if role == 'Reverse' and str(m.State) != 'Accepted':
                l_ids.add('PL')

            self.event('contact_role_info', name, l_ids, mshipid)

    def _set_persist_blp(self, bool):

        log.info('Setting persistent BLP to %d', int(bool))

        s = self.self_buddy.contactsoap

        if s.ContactInfo is None:
            s.ContactInfo = s.new_ContactInfo()

        if s.ContactInfo.Annotations is None:
            s.ContactInfo.Annotations = s.ContactInfo.new_annotations()


        annos = s.ContactInfo.Annotations

        for anno in annos.Annotation:
            if anno.Name == 'MSN.IM.BLP':
                break
        else:
            anno = annos.new_Annotation(); annos.Annotation.append(anno)
            anno.Name = 'MSN.IM.BLP'

        anno.Value = str(int(bool))

        s.PropertiesChanged = "Annotation"
        self.ABContactUpdate(s)

    def _load_contact_list(self):
        CACHE = True
        self._sync_addressbook(CACHE)
        ###
        self._sync_memberships(CACHE)

    def _sync_addressbook(self, use_cache):

        # Load cache, get timestamp

        # Load cache, get timestamp

        kwargs = {}
        if use_cache:
            cached = self._soapcache.get('ABFindAll', None)

            log.debug('Cached ABFindAllResult: %r', cached)

            if cached is not None:
                try:
                    oldresp = zsiparse(MSNAB, 'ABService', 'ABFindAll', cached)
                except:
                    import traceback;traceback.print_exc()
                else:
                    lastchange = oldresp.ABFindAllResult.Ab.LastChange
                    kwargs = dict(deltas=True, lastChange=lastchange)


        try:
            self.ABFindAll(**kwargs)
        except ZSI.FaultException:
            import traceback;traceback.print_exc()
            if kwargs:
                self.ABFindAll()
        except Exception, e:
            self.blist_error(e)

#        try:
#            address_book = self.ABFindAll()
#        except Exception, e:
#            log.info('Error getting address book')
#            print 'Error getting address book', repr(e)
#            import traceback;traceback.print_exc()
#        else:
#            log.info('Got address book result')
#            self.process_blist(address_book)
#            log.info('Processed address book')

    def _sync_memberships(self, use_cache):

        # Load cache, get timestamp

        kwargs = {}
        if use_cache:
            cached = self._soapcache.get('FindMembership', None)
            log.debug('Cached ABFindAllResult: %r', cached)
            if cached is not None:
                try:
                    oldresp = zsiparse(MSNAB, 'SharingService', 'FindMembership', cached)
                except:
                    import traceback;traceback.print_exc()
                else:
                    if oldresp.FindMembershipResult.Services is not None:
                        lastchange = max(x.LastChange for x in oldresp.FindMembershipResult.Services.Service)
                        kwargs = dict(deltas=True, lastchange=lastchange)

        try:
            self.FindMembership(**kwargs)
        except Exception, e:
            self.blist_error(e)
#
#        try:
#            memberships = self.FindMembership()
#        except Exception, e:
#            log.info('Error getting memberships')
#        else:
#            log.info('Got memberships result')
#            self.process_memberships(memberships)
#            log.info('Processed memberships')


    def blist_error(self, e):
        #self.hub.on_error(e)
        log.error('Error getting buddy list: %r, %r, %r', type(e), str(e), repr(e))
        import traceback;traceback.print_exc()

        if not self.CONNECTED:
            self.event('on_conn_error', self, e)

    def process_blist(self, t):
#        print repr(t._to_xml())
#        util.tag_view(t)

        log.info('Got ABFindAllResult')

        try:
            groups = t.Groups.Group or []
        except AttributeError:
            groups = []

        try:
            contacts = t.Contacts.Contact or []
        except AttributeError:
            contacts = []

        log.info('Got %d buddies and %d groups', int(len(contacts)), int(len(groups)))
        self.event('contact_list_details', int(len(contacts)), int(len(groups)))
        log.info('Adding groups')
        self.process_groups(groups)
        log.info('Adding contacts')
        self.process_contacts(contacts)

    def process_memberships(self, result):

        if result.Services is not None:
            services = dict((str(svc.Info.Handle.Type).strip(),svc) for svc in
                            result.Services.Service)

            try:
                for mship in services['Messenger'].Memberships.Membership:
                    role = mship.MemberRole
                    members = mship.Members
                    self.process_members(role, members)

            except (AttributeError,KeyError), e:
                log.warning('Error when trying to add memberships: %r', e)

        if not self.CONNECTED:
            self.socket.send(Message('BLP', 'AL' if self.allow_unknown_contacts else 'BL'), **defcb)

        if not self.CONNECTED:
            self.event('needs_status_message', self.send_uux)

    def send_fqy(self, n, flags):
        'FQY 10 51\r\n<ml l="1"><d n="yahoo.com"><c n="synae" /></d></ml>'
        'FQY 17 53\r\n<ml l="2"><d n="yahoo.com"><c n="digbsy04" /></d></ml>'
        u, d = n.split('@')
        ml = xml_tag.tag('ml')
        ml.d['n']=d
        ml.d.c['n']=u

        if not isint(flags):
            d = dict(f=1, a=2, b=4, r=8, p=16)
            if isinstance(flags, basestring):
                flags = [flags]

            flags = sum(d[f[0].lower()] for f in flags)

        if flags == 1:
            flags = 2

        ml['l']=flags

        xml = ml._to_xml(pretty=False)
        self.socket.send(Message('FQY', payload=xml), trid=True, callback=sentinel)

    def send_blp(self, value):
        assert value in ('AL', 'BL')
        bool = 'AL' == value
        self._set_persist_blp(bool)

        Super.send_blp(self, value)

    def _cache_soap(self, name, res):
        from ZSI import SoapWriter
        sw = SoapWriter()
        xml = str(sw.serialize(res))
        self._soapcache[name] = xml

        # hack to get the cache to save
        self._soapcache = self._soapcache

