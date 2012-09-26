import contextlib
import common
from common.protocolmeta import protocols
from contacts.metacontacts import MetaContact
from copy import deepcopy
from util import Storage, traceguard
from util.primitives.funcs import make_first
from threading import RLock
S = Storage
from common import profile

from logging import getLogger;
log = getLogger('dispatch')
#tofromlog = getLogger('tofrom')

from common.protocolmeta import REVERSE_SERVICE_MAP, SERVICE_MAP

class ContactDispatcher(object):
    _locknames = ('im', 'email', 'sms')

    def __init__(self, profile=None):
        self.locks = dict((t, RLock()) for t in self._locknames)
        self.tofrom = default_tofrom()
        self.profile = common.profile if profile is None else profile

    def set_tofrom(self, tofrom):
        with self.lock_all_data():
            self.tofrom = tofrom

    @contextlib.contextmanager
    def lock_all_data(self):
        locks = [self.locks[name] for name in self._locknames]
        with contextlib.nested(*locks):
            yield

    def get_tofrom_copy(self):
        with self.lock_all_data():
            return deepcopy(self.tofrom)

    def imaccts_for_buddy(self, buddy, contacts, force_has_on_list=False):
        # Find the best matching From account.
        contact, fromacct = self.get_from(buddy, only_on_list=force_has_on_list)

        if contact is None or fromacct is None:
            log.critical('get_from returned (%r, %r) for %r', contact, fromacct, buddy)
            contact, fromacct = self.get_from(contacts, only_on_list=force_has_on_list)

        if contact is None:
            contact = buddy

        srv = contact.service

        # Pick account services to show.
        services = [k for (k,v) in SERVICE_MAP.items() if srv in v]

        protos = [a.connection for a in self.profile.connected_accounts
                 if a.protocol in services]

        if fromacct is None:
            bproto = buddy.protocol
            for a in protos:
                if a.username == bproto.name and a.name == bproto.protocol:
                    fromacct = a
                    log.info('Found exact match for %r: %r', buddy, a)
                    break
            if fromacct is None:
                if force_has_on_list:
                    for proto in protos:
                        if proto.has_buddy_on_list(buddy):
                            fromacct = proto
                            break
                elif protos:
                    fromacct = protos[0]

        return fromacct, contact, protos

    #
    # to/from history list
    #

    def add_tofrom(self, history_type, to, from_):
        'Add a new entry in the to/from history list.'

        if history_type not in ('im', 'email', 'sms'):
            raise ValueError

        tofrom = self.tofrom[history_type]

        entries = dict(# IM: buddy name, buddy service, from username, from service name
                       im = lambda: (to.name, to.service, from_.username, from_.name),

                       # EMAIL: email address, from email username, from protcol
                       email = lambda: (to, from_.name, from_.protocol),

                       # SMS: tosmsnumber, from username, from protocol
                       sms = lambda: (to, from_.username, from_.name))

        entry = entries[history_type]()

        log.info('making %r first in to/from list', (entry,))

        with self.locks[history_type]:
            make_first(tofrom, entry)

    def get_from(self, tobuddy, connected=True, only_on_list=False):
        'Return the preferred account to message a buddy from, based on message history.'

        #if tobuddy is a metacontact use first online
        if isinstance(tobuddy, MetaContact):
            metacontact = tobuddy
            tobuddy = metacontact.first_online

            if tobuddy is None:
                tobuddy = metacontact[0]

        #if tobuddy is a list, use the first buddy
        elif isinstance(tobuddy, list):
            tobuddy = tobuddy[0]

        #All connected accounts
        connected = getattr(self.profile.account_manager, 'connected_accounts' if connected else 'accounts')

        #All services that are compatible with the current tobuddy
        compatible = REVERSE_SERVICE_MAP[tobuddy.service]

        #All accounts that are online and compatible with the current buddy
        conncomp = [account for account in connected if account.protocol in compatible]

        #if no online and compatible accounts are found return None
        if not conncomp:
            return tobuddy, None

        #Finding and return combination of tobuddy and one of the applicable accounts in history
        with self.locks['im']:
            for (bname, bservice, fromname, fromservice) in self.tofrom['im']:
                if tobuddy.name == bname and tobuddy.service == bservice:
                    for account in conncomp:
                        if account.connection.protocol == fromservice and account.connection.username == fromname:
                            return tobuddy, account.connection

        if only_on_list:
            return None, None

        # if the buddy is online, choose an account that sees the buddy as online
        with traceguard:
            for account in conncomp:
                conn = account.connection
                if conn.get_protocol_buddy(tobuddy).online:
                    return tobuddy, conn

        # First, find an account with the buddy on its list
        with traceguard:
            for account in conncomp:
                if account.connection.has_buddy_on_list(tobuddy):
                    return tobuddy, account.connection

        #Find first online and compatible account that has the same service as buddy
        for account in conncomp:
            if account.protocol == tobuddy.service:
                return tobuddy, account.connection

        #Return first compatible account as a last resort
        return tobuddy, conncomp[0].connection

    def get_tofrom_email(self, buddy):
        '''
        Given an email address, returns the last email account to have "Composed"
        an email to that address.
        '''
        emailaccts = self.profile.emailaccounts
        emails = self.get_contact_info(buddy, 'email') or []

        def findacct(username, proto):
            for acct in emailaccts:
                if acct.name == username and acct.protocol == proto:
                    return acct

        with self.locks['email']:
            for (to, fromuser, fromproto) in self.tofrom['email']:
                for email in emails:
                    if to == email:
                        acct = findacct(fromuser, fromproto)
                        if acct is not None:
                            return email, acct

        return None, None

    def get_tofrom_sms(self, buddy):

        # return all capable accounts
        with self.locks['sms']:
            for (to, from_username, protoname) in self.tofrom['sms']:
                for acct in self.profile.connected_accounts:
                    # find enabled email accounts
                    if acct.name == protoname and acct.username == from_username:
                        # found an (SMS, account) pair
                        return to, acct

        return None, None


tofrom_entry_length = dict(
    im = 4,
    email = 3,
    sms = 3,
)

def validate_tofrom(tofrom):
    '''
    Validate the data in a "tofrom" dict.

    {'im': [('buddy', 'service', 'buddy', 'service'), ...],
     'email':
     'sms'}
    '''
    if not isinstance(tofrom, dict):
        raise TypeError('tofrom should be a dict, instead is a %r: %r' % (tofrom.__class__, tofrom))

    for key in ('im', 'email', 'sms'):
        for history_entry in tofrom[key]:
            if not isinstance(history_entry, list):
                raise TypeError

            if len(history_entry) != tofrom_entry_length[key]:
                raise TypeError('invalid length')
            elif not all(isinstance(s, basestring) for s in history_entry):
                raise TypeError('each history entry should be a sequence of strings')

    return tofrom

def default_tofrom():
    '''
    The default to/from dataset.

    The to/from table stores buddies that you last messaged, and from which
    account.
    '''

    log.info('TOFROM: default_tofrom')
    return {'im':[], 'email':[], 'sms':[]}

def im_service_compatible(to_service, from_service):
    '''
    Returns True if a buddy on to_service can be IMed from a connection to from_service.
    '''

    return to_service in protocols[from_service].compatible

def get_account_name(a):
    # TODO: profile.name is different than any other account.name in that it doesn't include name@digsby.org
    if a is profile():
        return a.name + '@digsby.org'
    else:
        return a.name

