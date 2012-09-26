from peak.util.addons import AddOn
import interfaces as gui_interfaces
from util.net import linkify
import protocols

class IBCacheAddon(AddOn, dict):
    pass

class CachingIBP(protocols.Adapter):
    protocols.advise(instancesProvide=[gui_interfaces.ICachingInfoboxHTMLProvider])

    def __init__(self, subject):
        try:
            gui_interfaces.ICacheableInfoboxHTMLProvider(subject)
        except protocols.AdaptationFailure:
            raise
        return super(CachingIBP, self).__init__(subject)

    def get_html(self, *a, **k):
        c = IBCacheAddon(self.subject)
        ibp = gui_interfaces.ICacheableInfoboxHTMLProvider(self.subject)
        if ibp._dirty or 'cachedata' not in c:
            c['cachedata'] = ibp.get_html(*a, **k)
        return c['cachedata']

class AccountCachingIBP(protocols.Adapter):
    protocols.advise(instancesProvide=[gui_interfaces.ICachingInfoboxHTMLProvider])

    def get_html(self, htmlfonts, make_format, *a, **k):
        acct = self.subject
        cachekey = '__cache__'
        format_key = acct
        if getattr(acct, 'header_tabs', False):
            currtab = acct._current_tab
            cachekey = currtab
            format_key = (acct, cachekey)
            dirty = acct._dirty[currtab]
        elif getattr(acct, '_dirty', False):
            dirty = True
        else:
            dirty = False
        _cache = IBCacheAddon(acct)
        if dirty or cachekey not in _cache:
            _cache[cachekey] = linkify(make_format(htmlfonts, format_key))
            if getattr(acct, 'header_tabs', False):
                acct._dirty[currtab] = False
            else:
                acct._dirty = False
            _cache[cachekey] = ''.join(y.strip() for y in _cache[cachekey].split('\n'))
        return _cache[cachekey]
