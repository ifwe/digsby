from peak.util.addons import AddOn
import protocols

class IAliasProvider(protocols.Interface):
    def get_alias(name, service, protocol=None):
        pass

    def set_alias(name, service, protocol, alias):
        pass

class StubAliasProvider(AddOn):
    protocols.advise(instancesProvide=(IAliasProvider,), asAdapterForTypes=(object,))

    def get_alias(self, name, service, protocol=None):
        return None #"Foo"

    def set_alias(self, name, service, protocol, alias):
        pass
