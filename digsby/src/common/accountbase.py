import cPickle
from util.observe import Observable
from common import HashedAccount
from common.actions import ActionMeta, action
from common import profile
from util import dictdiff

import services.service_provider as service_provider

class AccountBase(Observable, HashedAccount):
    max_error_tolerance = 3
    __metaclass__ = ActionMeta

    _ids = []

    @classmethod
    def next_id(cls):
        i = len(cls._ids)-1
        for i, j in enumerate(sorted(set(cls._ids))):
            if i != j: break
        else:
            i += 1

        cls._ids.insert(i,i)
        return i

    def __init__(self, name, password, **options):
        Observable.__init__(self)
        self.name = name
        self.password = password
        self.id = options.pop('id') if 'id' in options else self.next_id()
        self.alias = options.pop('alias', None)
        self.error_count = 0

    def get_provider(self):
        return service_provider.get_provider_for_account(self)

    @property
    def popupids(self):
        return set((self,))

    @action()
    def rename_gui(self):
        from gui.toolbox import GetTextFromUser

        localalias = self.alias
        if localalias is None:
            localalias = ''

        s = GetTextFromUser(_('Enter an alias for %s:' % self.name),
                                           caption = _('Rename %s' % self.name),
                                           default_value = localalias,
                                           limit = 32)
        if s is not None:
            if s == '' or s.strip():
                # dialog returns None if "Cancel" button is pressed -- that means do nothing

                # rename expects None to mean "no alias" and anything else to mean an alias--so
                # do the bool check to turn '' into None here.
                self.rename(s if s else None)
                return s

    alias = None

    def rename(self, newalias):
        oldalias = self.alias
        self.alias = newalias
        self.notify('alias', oldalias, newalias)
        profile.update_account(self)

    @property
    def username(self):
        return self.name

    def protocol_class(self):
        "Returns the class of this Account's protocol."

        from common.protocolmeta import proto_init
        return proto_init(self.protocol)

    @staticmethod
    def _repr(self):
        return "<%s %r (%s) %s, %r>" % (self.__class__.__name__,
                                   self.name,
                                   getattr(self, 'protocol', None),
                                   getattr(self, 'state', None),
                                   getattr(self, 'offline_reason', None))

    def __repr__(self):
        return self._repr(self)

    def default(self, key):
        defaults = self.protocol_info()['defaults']
        return defaults[key]

    def get_options(self):
        opts = self._get_options()
        d = self.protocol_info()['defaults']
        return dictdiff(d, opts)

    def _decryptedpw(self):
        return profile.plain_pw(self.password)

    def _crypt_set_pw(self, value):
        self.password = profile.crypt_pw(value)

class FromNetMixin(object):
    def __init__(self, *a, **k):
        pass

    @classmethod
    def from_net(cls, info, **extra):
#        log.info('from_net')
#        log.info(pformat(info))

        from common.protocolmeta import proto_init
        Class = proto_init(info.protocol)
        cls._ids.insert(info.id, info.id)
        if not all(isinstance(c, str) for c in extra):
            from pprint import pprint
            pprint(extra)
        extra.update(**cPickle.loads(info.data))
        return Class(name = info.username, password = info.password,
                          id=info.id, **extra)

class SimpleAccountSerializer(object):
    '''account options are set on self. provides get_options and update_info'''

    def __init__(self, **options):
        for key in self.protocol_info()['defaults'].iterkeys():
            try: val = options[key]
            except KeyError: val = self.default(key)
            setattr(self, key, val)

    def update_info(self, **info):
        '''new account info arrives from network/account dialog'''

        for item in self.protocol_info()['new_details']:
            info.pop(item['store'], None)

        super(SimpleAccountSerializer, self).update_info(**info)

    def get_options(self):
        '''return the set of values to be serialized to the server'''

        opts = super(SimpleAccountSerializer, self).get_options()

        for k in self.protocol_info()['defaults'].iterkeys():
            v = getattr(self, k)
            if v != self.default(k):
                opts[k] = v

        return opts

