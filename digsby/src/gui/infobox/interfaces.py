import protocols

class IInfoboxHTMLProvider(protocols.Interface):

    def get_html(htmlfonts):
        pass

class ICacheableInfoboxHTMLProvider(IInfoboxHTMLProvider):
    _dirty = property()

class ICachingInfoboxHTMLProvider(IInfoboxHTMLProvider):

    def get_html(htmlfonts, make_format):
        pass
