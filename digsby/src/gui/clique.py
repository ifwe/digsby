from util import FunctionList

class Clique(set):
    def __setattr__(self, attr, val):
        for o in self: setattr(o, attr, val)

    def __getattr__(self, attr):
        try:
            return set.__getattr__(self, attr)
        except AttributeError:
            try:
                return self.__dict__[attr]
            except KeyError:

                default = lambda *a, **k: None

                res = FunctionList(getattr(x, attr, default) for x in self)

                return res

    def __repr__(self):
        return '<%s: %r>' % (type(self).__name__, set.__repr__(self))
