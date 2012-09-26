from .observe import ObservableDict as SavingDictBase
class ProxySavingDict(SavingDictBase):
    def __init__(self, save_func, *a, **k):
        self.save_func = save_func
        SavingDictBase.__init__(self, *a, **k)

    def save(self):
        self.save_func(self)

    def __setitem__(self, key, val):
        SavingDictBase.__setitem__(self, key, val)
        self.save()

    def __delitem__(self, key):
        SavingDictBase.__delitem__(self, key)
        self.save()

    def clear(self):
        SavingDictBase.clear(self)
        self.save()

__proxy_settings = None

def get_proxy_dict():
    global __proxy_settings

    if __proxy_settings is not None:
        return __proxy_settings

    import gui.toolbox.toolbox as tb
    ls = tb.local_settings()

    section = 'Proxy Settings'

    if not ls.has_section(section):
        ls.add_section(section)

    def save(d):
        ls._sections[section] = d.copy()
        ls.save()

    __proxy_settings = ProxySavingDict(save, ls.iteritems(section))


    return __proxy_settings
