from peak.util.imports import lazyModule
from pyxmpp.utils import from_utf8
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import get_node_ns_uri
from digsby.widgets import DIGSBY_WIDGETS_NS
from hashlib import sha256
from util import callsback
from digsby.web import digsby_webget
from logging import getLogger; log = getLogger('digsby.widget')
skin = lazyModule('gui.skin')

from util.xml_tag import tag
from urllib2 import urlopen
from urllib import urlencode


from common import profile
from util.net import UrlQuery
import wx



def iswidget(buddy):
    'Returns True if the given buddy is from a webpage widget.'

    return hasattr(buddy, 'jid') and buddy.jid.domain == 'guest.digsby.org'

def get_local_swf():
    return skin.resourcedir() / 'widget' / 'digsby_widget.swf'


class Widget(StanzaPayloadObject):

    action_url = 'https://accounts.digsby.com/login.php?'

    modify_url = 'http://widget.digsby.com/?'


    xml_element_name = 'widget'
    xml_element_namespace = DIGSBY_WIDGETS_NS

    def __init__(self, xmlnode_or_acct_or_id):
        self.__from_xml(xmlnode_or_acct_or_id)

    def __repr__(self):
        return '<Digsby.Widget id:%(id)s title:%(title)s on:%(on)s width:%(width)d height:%(height)d'\
                ' type:%(type)s typeuid:%(typeuid)s>' % self.__dict__

    def __from_xml(self,node):
        if node.type != "element":
            raise ValueError,"XML node is not an %s element (not en element)" % self.xml_element_name

        ns = get_node_ns_uri(node)

        if ns and ns != DIGSBY_WIDGETS_NS or node.name != self.xml_element_name:
            raise ValueError,"XML node is not an %s element" % self.xml_element_name

        for prop in ('id', 'title', 'on', 'width', 'height', 'type', 'typeuid'):
            val = node.prop(prop)
            if val is not None:
                setattr(self, prop, from_utf8(val))
            else:
                setattr(self, prop, val)

        for prop in ['width', 'height']:
            if getattr(self, prop):
                setattr(self, prop, int(getattr(self, prop)))

        self.on = bool(int(self.on))

    def set_enabled(self, enabled):
        if not enabled:
            # when disabling a widget, all of that widget's buddies should go
            # offline
            conn = profile.connection
            if conn is not None:
                conn.remove_widget_buddies(self)

        self._action('toggleon' if enabled else 'toggleoff')

    def edit(self):
        def success(res):
            print
            print res
            print

            file, key = res.split(':')
            wx.LaunchDefaultBrowser(UrlQuery(self.modify_url, id=file, tkn=key))

        self._action('modify', success = success)
        #autologin(profile.username, profile.password, 'http://widget.digsby.com/?id=' + self.id)

    def delete(self):
        self._action('del')

    @callsback
    def _action(self, action, callback = None):
        url = self.action_url
        params =   dict(obj='widget',
                        user = profile.username,
                        key  = sha256(profile.password).hexdigest(),
                        act  = action,
                        doto = self.id)

        def error(result = ''):
            log.warning('server indicated an error %r', result)
            callback.error()

        def success(result):
            if result.lower() == 'err': error(result)
            else: callback.success(result)

        digsby_webget(url, success = success, error = error, **params)


    @property
    def embed_tag(self):
        '''
        Returns the text of the embed tag which will embed this widget in a
        webpage.
        '''

        if self.type == 'fb':
            return ''

        return ('<embed src="http://w.digsby.com/dw.swf?c=%s" wmode="transparent" '
                'type="application/x-shockwave-flash" width="%s" height="%s"></embed>'
                % (self.id, self.width, self.height))


    @property
    def flash_url(self):
        return 'http://w.digsby.com/dw.swf?c=%s&STATE=creator' % self.id

    def embed_creator(self, w, h):
        '<embed> for showing a disabled widget preview'

        widget = ('<embed src="%s" wmode="transparent"'
                  'type="application/x-shockwave-flash" width="%s" height="%s"></embed>'
                  % (self.flash_url, self.width, self.height))

        return ('<html><head><style type="text/css">body { border: 0px; padding: 0px; margin: 0px;} *{overflow:hidden;}</style></head>'
                '<body border=0 padding=0 margin=0><div id="widget">%s</div></body></html>' % self.get_config(w,h))



    def get_config(self,w,h):
        'returns an embed tag with the parsed values of a given widget config file'

        url = 'http://config.digsby.com/%s' % (self.id)
        data = urlopen(url).read()
        xml = tag(data)

        sc = xml.style.text.status['color']
        bc = xml.style.background['color']
        tc = xml.style.title['color']
        fc = xml.style.field['color']
        xc = xml.style.text['color']
        tt = xml.o['title']
        nt = xml.o['nick']

        d = dict(title=tt, nick=nt, statustext=sc, bgcolor=bc, titletext=tc, field=fc, text=xc)
        flashvars = urlencode(d)

        #local_widget = skin.resourcedir() / 'widget' / 'digsby_widget.swf'
        widget_url = 'http://w.digsby.com/dw.swf'

        return ('<embed src="%s%s" type="application/x-shockwave-flash" wmode="transparent" width="%s" height="%s"'
                '></embed>' % (widget_url, '?STATE=creator&' + flashvars, w, h))
