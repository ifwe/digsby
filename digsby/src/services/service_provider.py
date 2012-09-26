'''
This file contains several helper methods for working with service provider and component metainfo, as well as basic
service provider functionality and subclasses appropriate for real service provider types.
'''
import cPickle

import logging
log = logging.getLogger("service_provider")

import wx
import hooks
import util
import util.net as net
import common.protocolmeta as protocolmeta
from peak.util.addons import AddOn
import common
from util.primitives.structures import oset
from util.primitives.funcs import Delegate
import threading
from contextlib import contextmanager

import plugin_manager.plugin_hub as plugin_hub

class AccountException(Exception):
    def __init__(self, message = u'', fatal = True, debug_message = ''):
        Exception.__init__(self, debug_message)
        self.message = message
        self.fatal = fatal

class DuplicateAccountException(Exception):
    pass

def get_meta_service_providers():
    plugins = wx.GetApp().plugins
    return [plugin for plugin in plugins if getattr(getattr(plugin, 'info', None), 'type', None) == 'service_provider']

def get_meta_service_provider(provider_id):
    for msp in get_meta_service_providers():
        if getattr(getattr(msp, 'info', None), 'provider_id', None) == provider_id:
            return msp

    return None

def get_meta_components_for_provider(service_provider):
    plugins = wx.GetApp().plugins
    return [plugin for plugin in plugins if getattr(getattr(plugin, 'info', None), 'type', None) == 'service_component'
                                        and getattr(getattr(plugin, 'info', None), 'service_provider', None) == service_provider]

def get_meta_component_for_provider(service_provider, component_type):
    for msc in get_meta_components_for_provider(service_provider):
        if getattr(getattr(msc, 'info', None), 'component_type', None) == component_type:
            return msc

def get_service_provider_factory(provider_id):
    ProviderFactory = None
    for impl in (provider_id, None):
        pf = hooks.first("digsby.service_provider", impl = provider_id, provider_id = provider_id)
        if pf is not None:
            ProviderFactory  = pf
            break

    return ProviderFactory

def get_provider_for_account(acct, profile=None):
    if profile is None:
        profile = common.profile()
    msp = get_meta_provider_for_account(acct)
    if msp is None:
        return None
    sp = get_service_provider_factory(msp.provider_id)
    if sp is None:
        return None

    return sp.from_account(acct, profile)

def get_meta_provider_for_account(acct):
    meta = protocolmeta.protocols.get(acct.protocol)
    msp = get_meta_service_provider(getattr(meta, 'service_provider', None))
    return msp

#class IIMComponent(protocols.Interface):
#    pass
#
#class IIMComponentFactory(protocols.Interface):
#    pass

class ServiceProvider(object):

    def __init__(self, provider_id, **kwds):
        self.provider_id = provider_id
        self.accounts = {}

        if kwds:
            #log.info("Create Service provider: %r", kwds)
            self.update_info(kwds)

    def get_component_factory(self, type):
        return list(hooks.Hook("digsby.component.%s" % type, impl = self.provider_id))[0]

    def construct_component(self, type):
        msp = get_meta_service_provider(self.provider_id)
        msc = get_meta_component_for_provider(self.provider_id, type)
        cf = self.get_component_factory(type)

        component = hooks.first("digsby.component.%s.construct" % type,
                                cf, self, msp, msc,
                                impls = (self.provider_id, 'default'))

        return component

    def get_metainfo(self, component_type = None):
        msp = get_meta_service_provider(self.provider_id)
        if component_type is None:
            return msp
        return msp, get_meta_component_for_provider(self.provider_id, component_type)

    def get_component_types(self):
        return [x.info.component_type for x in self.get_meta_components()]

    def get_meta_components(self):
        return get_meta_components_for_provider(self.provider_id)

    def get_component(self, type, create = True):
        if type not in self.get_component_types():
            return None

        if type not in self.accounts and create:
            component = self.construct_component(type)
            if component is not None:
                self.add_account(type, component)
                plugin_hub.act('digsby.%s.addaccount.async' % type, component.protocol, component.name)

        return self.accounts.get(type, None)

    @classmethod
    def from_account(cls, acct, profile):
        container = ServiceProviderContainer(profile)
        meta = protocolmeta.protocols.get(acct.protocol)
        component_type = meta.component_type
        provider_id = meta.service_provider

        username = getattr(acct, 'username', getattr(acct, 'name', None))
        info = acct.get_options()
        info['username'] = acct.username
        sp = container.existing_sps.get(normalized_id(provider_id, info), None)
        if sp is None:
            sp = container.existing_sps[normalized_id(provider_id, info)] = cls(provider_id = provider_id)

        sp.add_account(component_type, acct)
        comp = sp.get_component(component_type, create = False)

        return sp

    def add_account(self, type, acct):

        acct_options = acct.get_options()

        options = copy.deepcopy(getattr(self.get_metainfo(), 'info', {}).get('defaults', {}))
        options.update(copy.deepcopy(getattr(self.get_metainfo(type)[1], 'info', {}).get('defaults', {})))
        options.update(acct.get_options())
        options['name'] = acct.name

        if acct.password:
            options['password'] = acct.password

        options['id'] = acct.id

        if type in self.accounts:
            if self.accounts[type] is not acct:
                self.accounts[type].update_info(**options)
        else:
            self.accounts[type] = acct

        self.update_info(options)
        getattr(self, 'add_account_%s' % type, lambda a: None)(acct)

    def add_account_im(self, acct):
        pass
    def add_account_email(self, acct):
        pass
    def add_account_social(self, acct):
        pass

    def remove_account(self, type):
        self.accounts.pop(type, None)

    def update_info(self, info):
        info.pop('id', None)
        for k, v in info.items():
            setattr(self, k, v)

    def update_components(self, info):
        for type in self.get_component_types():
            comp = self.get_component(type, create = False)
            if comp is not None:
                info.pop('username', None)
                comp.update_info(**info)

    def get_options(self, type):
        import hub

        opts = dict(user = hub.get_instance())
        opts.update(vars(self))
        opts.pop('accounts')

        acct = self.accounts.get(type, None)
        if acct is not None:
            opts.update(acct.get_options())

            opts.update(name = acct.name,
                        password = acct.password)

        opts.pop('enabled', None)
        opts.pop('protocol', None)
        opts.pop('id', None)
        return opts

    def rebuilt(self):
        pass

    def __repr__(self):
        return "<%s %12r: %r>" % (type(self).__name__, getattr(self, 'provider_id', None), getattr(self, 'name', None))

class UsernameServiceProvider(ServiceProvider):
    '''
    A service provider with a username. Most service providers will have this.
    '''
    name = None
    def update_info(self, kwds):
        if self.name is not None:
            kwds.pop("name", None)
            kwds.pop('username', None)
        else:
            self.name = kwds.get('username', kwds.get('name', None)) or self.name

        if not self.name:
            raise AccountException(debug_message = "No username provided")

        if 'server' in kwds:
            try:
                host, port = kwds['server']
                port = int(port)
                kwds['server'] = host, port
                if not host:
                    raise ValueError(host)
            except (ValueError, TypeError):
                #raise AccountException(debug_message = "server tuple is invalid: %r" % kwds['server'])
                pass

        super(UsernameServiceProvider, self).update_info(kwds)

    def add_account(self, type, acct):
        super(UsernameServiceProvider, self).add_account(type = type, acct = acct)

        if self.name is None:
            self.name = acct.name

        opts = acct.get_options()
        opts['username'] = acct.name
        acct_id = normalized_id(self.provider_id, opts)
        my_id = normalized_id(self.provider_id, self.get_options(type))
        if acct_id != my_id:
            raise ValueError("Can't add a different username")

    def get_options(self, type):
        opts = super(UsernameServiceProvider, self).get_options(type = type)
        opts.update(name = self.name)
        return opts

    @property
    def display_name(self):
        meta = self.get_metainfo().info.provider_info
        display_domain = meta.get('display_domain', meta.get('default_domain', None))
        if display_domain is None:
            return self.name
        else:
            try:
                return str(net.EmailAddress(self.name, display_domain))
            except ValueError:
                return self.name

class PasswordServiceProvider(ServiceProvider):
    '''
    A service provider with a password. Many, but not all, service providers will require this behavior.
    '''
    password = None
    def update_info(self, kwds):
        super(PasswordServiceProvider, self).update_info(kwds)

        if 'password' in kwds:
            self.password = kwds.get('password', None)

        if self.password == '':
            raise AccountException(debug_message = "No password provided")

    def add_account(self, type, acct):
        super(PasswordServiceProvider, self).add_account(type = type, acct = acct)

        if self.password is None:
            self.password = acct.password

    def get_options(self, type):
        opts = super(PasswordServiceProvider, self).get_options(type = type)
        opts.update(password = self.password)
        return opts

    def _decryptedpw(self):
        return common.profile.plain_pw(self.password)

class UsernamePasswordServiceProvider(UsernameServiceProvider, PasswordServiceProvider):
    '''
    Convenience class to combine UsernameServiceProvider and PasswordServiceProvider.
    '''
    pass

class EmailPasswordServiceProvider(UsernamePasswordServiceProvider):
    ''' Same as a UsernamePasswordServiceProvider but has an email address property '''

    def update_info(self, kwds):
        super(EmailPasswordServiceProvider, self).update_info(kwds)
        try:
            self._get_email_address()
        except ValueError:
            raise AccountException("Invalid email address", debug_message = "No oauth account label or username provided")

    def _get_email_address(self):

        default_domain = self.get_metainfo().info.provider_info.get('default_domain', None)
        if default_domain is not None:
            return str(net.EmailAddress(''.join(self.name.split()).lower(), default_domain))
        else:
            return self.name

    def _set_email_address(self, v):
        pass

    email_address = property(_get_email_address, _set_email_address)

    @property
    def display_name(self):
        if self.name.lower() != self.email_address.lower():
            meta = self.get_metainfo().info.provider_info
            return ''.join(self.name.split()).lower() + '@' + meta.get('display_domain', meta.get('default_domain'))

        else:
            return self.name

    def get_options(self, type):
        opts = super(EmailPasswordServiceProvider, self).get_options(type = type)
        opts.update(email_address = self.email_address)
        return opts

class OAuthServiceProvider(ServiceProvider):
    '''
    Does not have a password and only sort-of has a username. The username is treated as a 'label', since we have
    no reasonable way of checking the username entered into the OAuth field when login happens.
    '''
    label = None
    oauth_token = None
    def update_info(self, kwds):
        super(OAuthServiceProvider, self).update_info(kwds)

        self.label = kwds.get('label', kwds.get('name', kwds.get('username', getattr(self, 'name', None))))
        if not self.label:
            raise AccountException(debug_message = "No oauth account label or username provided")

        self.oauth_token = kwds.get('oauth_token', None)

    def get_options(self, type):
        opts = super(OAuthServiceProvider, self).get_options(type = type)
        opts.update(label = opts.get('name', None), name = self.label)

        return opts

    def add_account(self, type, acct):
        super(OAuthServiceProvider, self).add_account(type = type, acct = acct)

        if self.label is None:
            self.name = self.label = getattr(acct, 'name', None)

        if self.oauth_token is None:
            self.oauth_token = getattr(acct, 'oauth_token', None)

    @property
    def display_name(self):
        meta = self.get_metainfo().info.provider_info
        display_domain = meta.get('display_domain', meta.get('default_domain', None))
        if display_domain is None:
            return self.name
        else:
            try:
                return str(net.EmailAddress(self.name, display_domain))
            except ValueError:
                return self.name

class MixedAuthServiceProvided(UsernamePasswordServiceProvider, OAuthServiceProvider):
    '''
    In some rare cases, we might actually have a username/password combination and an OAuth token. (myspace comes to
    mind).
    '''
    pass

import copy
def default_component_constructor(cf, SP, MSP, MSC):
    '''
    Create a service component by flattening 3 options dictionaries together:
      meta info for the service provider
      meta info for the service component
      info for the service component instance we're creating
    '''
    options = copy.deepcopy(getattr(MSP, 'info', {}).get('defaults', {}))
    options.update(copy.deepcopy(getattr(MSC, 'info', {}).get('defaults', {})))
    options.update(SP.get_options(MSC.info.component_type))

    return cf(**options)

def default_component_constructor_im(cf, SP, MSP, MSC):
    '''
    Like default_component_constructor but also includes a 'protocol' key, which is required for IM accounts.
    This also forces the class imaccount.Account for the result (instead of the provided cf argument)
    '''
    import imaccount
    options = copy.deepcopy(getattr(MSP, 'info', {}).get('defaults', {}))
    options.update(copy.deepcopy(getattr(MSC, 'info', {}).get('defaults', {})))
    options.update(SP.get_options(MSC.info.component_type))
    if 'protocol' not in options:
        options.update(protocol = MSC.info.shortname)

    util.dictrecurse(dict)(options)

    # TODO: cf is ignored - should we have a way for it to be overridden? perhaps let it default to imaccount if not
    # provided.
    return imaccount.Account(**options)

hooks.register("digsby.component.im.construct", default_component_constructor_im, impl = 'default')
hooks.register("digsby.component.email.construct", default_component_constructor, impl = 'default')
hooks.register("digsby.component.social.construct", default_component_constructor, impl = 'default')

class ServiceProviderContainer(AddOn):
    '''
    Used to contain all ServiceProvider data - this is essentially the user's account list. It is also responsible
    for maintaining order of accounts.
    '''
    def __init__(self, subject):
        self.profile = subject
        self.existing_sps = {}
        self.order = None
        self.on_order_changed = Delegate()
        self.lock = threading.RLock()
        self.rebuild_count = 0
        self.accounts_to_rebuild = None
        self.new = set()

    def has_account(self, info):
        return normalized_id(info['provider_id'], info) in self.existing_sps

    def get_ordered(self, new=()):
        if self.order is None:
            return
        order = self.order
        acct_position = dict((v,k) for (k,v) in enumerate(order))
        from collections import defaultdict
        types = defaultdict(list)
        provider_list = self.existing_sps.values()
        provider_lookup = dict()
        account_lookup = dict()
        for provider in provider_list:
            for type_, acct in provider.accounts.items():
                if acct in new:
                    assert len(new) == 1
                    assert len(provider.accounts) > len(new)
                    continue
                types[type_].append(acct)
                provider_lookup[acct.id] = provider
                account_lookup[acct.id] = acct
        for val in types.values():
            val.sort(key = lambda a: acct_position.get(a.id, 1000))
        loc = dict(enumerate(provider_list))
        from util.primitives.mapping import dictreverse
        loc2 = dictreverse(loc)
        chains = [types['im'], types['email'], types['social']]

        #this adds just a little more information about the relationship between
        #im/email/social accounts.
        total_chain = oset(account_lookup[id_] for id_ in order if id_ in account_lookup)
        for chain in chains:
            total_chain.update(chain)
        chains.append(total_chain)

        chains = [oset([loc2[provider_lookup[acct.id]] for acct in type_]) for type_ in chains]

        #enforce that if there is a previous ordering between two nodes,
        #then the reverse ordering is discarded
#        partial = set()
#        chains2 = []
#        for chain in chains:
#            chain2 = []
#            blacklist = []
#            for i, a in enumerate(chain):
#                if a in blacklist:
#                    continue
#                for b in chain[i:]:
#                    if a == b:
#                        continue
#                    node = (a,b)
#                    revnode = (b,a)
#                    if revnode in partial:
#                        #the conflict doesn't exist until we get to b
#                        #and it's farther down than this one, so discard b.
#                        _none = blacklist.append(b)
#                    else:
#                        _none = partial.add(node)
#                else:
#                    _none = chain2.append(a)
#            _none = chains2.append(chain2)
#            #_none is for pasting into the console, consumed return values aren't shown.
#        import util.primitives.topological_sort as tsort
#        order = tsort.topological_sort_chains(chains2)
        import util.primitives.topo_sort as tsort
        order = tsort.topological_sort_chains(chains)
        provider_accts = [loc[i] for i in order]

        out = []
        for prov in provider_accts:
            [out.append(a.id) for a in
             [prov.accounts.get(t, None) for t in
              ['im', 'email', 'social']]
             if a is not None]
        self.order = out
        return provider_accts

    def get_order(self):
        return self.order[:] if self.order else []

    def set_order(self, order):
        if order == self.order:
            return
        self.order = order[:]
        self.rebuild_order()

    def rebuild_order(self, new=()):
        self.get_ordered(new=new)
        #again, to flush all inconsistency
        self.get_ordered()
        self.on_order_changed(self.order)

    def rebuild(self, accounts=None, new=()):
        with self.lock:
            if accounts is not None:
                self.accounts_to_rebuild = accounts
            if self.rebuild_count != 0:
                return
            else:
                accounts = self.accounts_to_rebuild
                self.accounts_to_rebuild = None
        self.existing_sps.clear()
        for a in accounts:
            try:
                get_provider_for_account(a, self.profile)
            except Exception:
                import traceback; traceback.print_exc()

        if self.order is not None:
            self.rebuild_order(new=new)

    @contextmanager
    def rebuilding(self, new=()):
        with self.lock:
            self.rebuild_count += 1
        self.new.update(new)
        yield self
        with self.lock:
            self.rebuild_count -= 1
            if self.rebuild_count == 0:
                self.new, new = set(), self.new
                self.rebuild(new=new)
                for sp in self.existing_sps.values():
                    sp.rebuilt()

def normalized_id(provider_id, info):
    MSP = get_meta_service_provider(provider_id)

    id = info.get('name', info.get('username'))
    id = ''.join(id.split()).lower()

    default_domain = MSP.info.provider_info.get('default_domain', None)
    if default_domain is not None:
        try:
            email = net.EmailAddress(id, default_domain)
            if email.domain in MSP.info.provider_info.get('equivalent_domains', [default_domain]):
                email = net.EmailAddress(email.name, default_domain)
            id = str(email)
        except ValueError:
            pass

    if provider_id != 'aol': # xxx: gtfo
        server = info.get('imapserver', info.get('popserver', None))
        if server is not None:
            id = server + '_' + id

    return provider_id, id

hooks.register("digsby.profile.addons", ServiceProviderContainer, impl = 'services')
