import cPickle
import common

class ServiceComponent(object):
    '''
    A ServiceComponent instance is responsible for de/serializing all of the data that needs to be stored in order to
    maintain a user's settings for a given service feature. This also contains some legacy fields due to the way
    they're stored in the server database.

    This class is also responsible for providing access to the plaintext password of the account.
    '''
    _attrfields_ = [('protocol', 'protocol'),
                    ('name', 'username'),
                    ('password', 'password_crypted'),
                    ('id', 'id')]

    _datafields_ = []

    @classmethod
    def deserialize(cls, netacct):
        attrs = {}

        msc = common.protocolmeta.get(netacct.protocol)
        subcls = hooks.first('digsby.services.component.%s.factory' % msc.component_type,
                             impls = (msc.service_provider, 'default'))
        attrs['provider_id'] = msc.service_provider
        attrs['component_type'] = msc.component_type

        assert issubclass(cls, subcls)

        default = lambda k: msc.info.defaults.get(k, sentinel)
        for netkey, mykey in subcls._attrfields_:
            attrs[mykey] = getattr(netacct, netkey)

        options = cPickle.loads(netacct.data)
        for netkey, mykey in subcls._datafields_:
            val = options.get(netkey)
            if val is None:
                val = default(netkey)
                if val is sentinel:
                    raise KeyError("%r is required but is not present.", netkey)
            attrs[mykey] = val

        return subcls(attrs)

    def serialize(self):
        attrs = {}
        for netkey, mykey in self._attrfields_:
            attrs[netkey] = getattr(self, mykey)

        options = {}
        for netkey, mykey in self._datafields_:
            options[netkey] = getattr(self, mykey)

        attrs['data'] = cPickle.dumps(options)

        return attrs

    def __init__(self, **options):

        if options:
            self.init(options)

    def init(self, options):
        for k,v in options.items():
            setattr(self, k, v)

    def _get_password(self):
        return common.profile.plain_pw(self.password_crypted)

    def _set_password(self, val):
        self.password_crypted = common.profile.crypt_pw(val)

    password = property(_get_password, _set_password)

