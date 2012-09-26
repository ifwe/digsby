from util.primitives import dictdiff
import cPickle
from traceback import print_exc
from base64 import b64encode

def uname_str(name):
    if isinstance(name, unicode):
        return name.encode('utf8')
    else:
        assert isinstance(name, str)
        return str(name)

def password_str(password):
    assert (isinstance(password, str) and password or password is None)
    password = str(password)
    return b64encode(password)

class HashedAccount(object):
    def min_hash(self):
        return ''.join(str(c) for c in [self.id, self.protocol, uname_str(self.username)])

    def total_hash(self):
        if not hasattr(self, 'xml_element_name'):
            data = self.get_options()
        else:
            try:
                if self.data is not None:
                    data = cPickle.loads(self.data)
                    try:
                        d = self.protocol_info()['defaults']
                    except KeyError:
                        d = {}
                    data = dictdiff(d, data)
                    import common.protocolmeta as pm
                    if self.protocol in pm.improtocols.keys():
                        for k in data.keys():
                            if k not in d:
                                data.pop(k)
                    else:
                        try:
                            opts = self.protocol_info()['whitelist_opts']
                        except KeyError:
                            opts = ()
                        for k in data.keys():
                            if k not in opts:
                                data.pop(k)
                else:
                    data = None
                #HACK: unfortunately, there's not actually a better place for this right now.
                if self.protocol in ('face', 'facebook'):
                    if 'filters' in data:
                        if 'alerts' in data['filters']:
                            alrts = [True]*7
                            alrts[:len(data['filters']['alerts'])] = data['filters']['alerts']
                            data['filters']['alerts'] = alrts
            except Exception:
                print 'data was: %r' % self.data
                print_exc()
                data = None
        result = (''.join(str(c) for c in [self.id, self.protocol, uname_str(self.username), password_str(self.password)]), data)

        return result

    def protocol_info(self, proto = sentinel):
        from common.protocolmeta import protocols
        return protocols[proto if proto is not sentinel else self.protocol]

    @property
    def _total_hash(self):
        return getattr(self, '_total_hash_', None)

    def store_hash(self, hash=sentinel):
        self._total_hash_ = hash if hash is not sentinel else self.total_hash()

class HashedAccounts(object):

    def calc_hash(self):
        if not hasattr(self, 'xml_element_name'):
            return sorted(a._total_hash for a in self)
        else:
            return dict((a.id, a.total_hash()) for a in self)
