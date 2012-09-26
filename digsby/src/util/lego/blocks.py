import protocols

class IBindableValue(protocols.Interface):
    def bind(func):
        pass
    def unbind():
        pass
    value = property()

