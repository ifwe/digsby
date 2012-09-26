def install_sentinel():
    'add "sentinel" to builtins'

    import __builtin__

    class Sentinel:
        def __init__(self, *a,**k):
            pass
        def __repr__(self):
            return '<Sentinel %s>' % id(self)
        def __nonzero__(self):
            return False

    __builtin__.Sentinel = Sentinel
    __builtin__.sentinel = Sentinel()

def install_N_():
    """
    add "N_" to builtins
    N_ is used to mark string for translation but not translate them in place
    """

    import __builtin__

    __builtin__.N_ = lambda s: s
