#TODO: This should be replaced with a newer system similar to how social networks are handle with Tenjin templates
'''
These functions are used to build the HTML used in the infobox for IM buddies
'''

from gui.buddylist.renderers import get_buddy_icon_url
import wx
from time import time
from xml.sax.saxutils import escape
from gui.textutil import default_font
from util import linkify
from common import pref

LINK_CSS = ''
'''\
a:link
    {
    text-decoration:none;
    }
a:hover
    {
    text-decoration:underline;
    }
'''

import logging
log = logging.getLogger('htmlgeneration')

from gui.skin import get as skin_get
import gui.skin as skin

def separatorshort():
    return get_hr('shortseparatorimage')

def separatorlong():
    return get_hr('longseparatorimage')

def separatorsocial():
    return get_hr('shortseparatorimage', padding = False)

def get_hr(key = None, padding = True):

    if key is not None:
        separator = skin_get('infobox.%s' % key, None)
    else:
        separator = None

    if separator is not None:
        html = '<div style="width: 100%%; padding: %ipx 0;"><img src = "%s" width = 100%% height = %spx /></div>' % ((4 if padding else 0), separator.path.url(), separator.Size.height)
    else:
        html = '<hr />'

    return html



JABBER_SERVICES = [u'jabber', u'gtalk', u'digsby']

from common.protocolmeta import protocols

def ColorHTML(color):
    if color[0:2].lower() == '0x':
        return ''.join('#', color[2:8])
    return color

def GenBitmapHTML(key, width, height):

    imagedata = {'source': key,
                 'width': width,
                 'height': height}

    return u'<img src="%(source)s" width=%(width)i height=%(height)i >' % imagedata

def GenBuddyIconHTML(contact):

    iconinfo = {'iconurl': get_buddy_icon_url(contact),
                'iconsize': pref('infobox.iconsize', 64)}

    return (u'<img id="#contactIcon" src="%(iconurl)s" style="width: %(iconsize)ipx;" '
             'onError="imgError(this)" />') % iconinfo

def GenStatusIconHTML(contact):

    sicon = skin_get("statusicons." + contact.status_orb)
    margins = skin_get('infobox.margins')

    iconinfo = {'iconurl': sicon.path.url(),
                'iwidth': sicon.Width,
                'iheight': sicon.Height,
                'iposx': margins.right + (16-sicon.Width)//2,
                'iposy': margins.top}

    return u'<img src= "%(iconurl)s" style="width: %(iwidth)ipx; height: %(iheight)ipx; position: absolute; top: %(iposy)ipx; right: %(iposx)ipx;" >' % iconinfo

def FontTagify(string, fonttype, nowrap = False):
    font  = skin_get('infobox.fonts.%s' % fonttype, default_font)
    color = skin_get('infobox.fontcolors.%s' % fonttype, wx.BLACK).GetAsString(wx.C2S_HTML_SYNTAX)

    if isinstance(string, str):
        try:
            string = string.decode('fuzzy') # Last ditch attempt
        except UnicodeDecodeError, e:
            log.info('Couldn\'t put %r into a font tag- decode failed with error %r', string, e)
            return ''

    tag = u''.join(['<span style="font-family: %(facename)s; font-size: %(size)ipt; color: %(color)s; %(nowrap)s">' %
                        {'facename': font.FaceName,
                         'size': font.PointSize,
                         'color': color,
                         'nowrap': 'white-space: nowrap;' if nowrap else ''},
                    '<b>' if font.Weight == wx.BOLD else '',
                    '<i>' if font.Style  == wx.ITALIC else '',
                    '<u>' if font.Underlined else '',
                    string,
                    '</u>' if font.Underlined else '',
                    '</i>' if font.Style  == wx.ITALIC else '',
                    '</b>' if font.Weight == wx.BOLD else '',
                    '</span>'])
    return tag


def TitleHTML(title):
    return FontTagify((title+'&nbsp;&nbsp;').replace('\n','<br>'),'title')

def BodyHTML(text):
    return FontTagify(escape(text).replace('\n','<br>'),'minor')

def DetailHTML(text):
    return FontTagify(text.replace('\n','<br>'),'minor')

def List2HTML(listostuff):
    string=''
    for stuff in listostuff:
        string=''.join([string,(BodyHTML(stuff)    if isinstance(stuff, basestring) else
                                LinkHTML(*stuff)   if isinstance(stuff, tuple) else
                                List2HTML(stuff)   if isinstance(stuff, list) else
                                ImageHTML(**stuff) if isinstance(stuff, dict) else '')])

    return string

def NoProfile():
    return FontTagify(_('No Profile'), 'minor')

def ListProfile2HTML(listostuff):
    profile=[]
    for stuff in listostuff:
        profile.append(stuff if isinstance(stuff,basestring) else
                       PrettyProfile2HTML(stuff) if isinstance(stuff,dict) else
                       NoProfile() if stuff is None else
                       '')

    return ''.join(profile)

def PrettyProfile2HTML(profile):
    if not profile: return NoProfile()
    string=''

    for key in profile.keys():
        value = profile[key]
        if value:
            if isinstance(value,int): string=''.join([string,exbr(value)])
            else: string=''.join([string, TitleHTML(key),
                                  (BodyHTML(value)    if isinstance(value,basestring) else
                                   LinkHTML(*value)   if isinstance(value,tuple) else
                                   List2HTML(value)   if isinstance(value,list) else
                                   ImageHTML(**value) if isinstance(value,dict) else ''),
                                   '<br>'])

    return string

def exbr(height):
    return '<table cellpadding=%i cellspacing=0 border=0><tr><td></td></tr></table>' % height

def ProfileHTML(profile):

    if isinstance(profile, dict):
        profile = PrettyProfile2HTML(profile)
    elif isinstance(profile, list):
        profile = ListProfile2HTML(profile)
    else:
        profile = u''.join([u'<TABLE width="100%" cellpadding="0" cellspacing="0" '
                    'border=0><tr><td>', NoProfile(), '</td></tr></table>'])

    return u''.join([u'</TD></TR></TABLE>',
                     u'<TABLE WIDTH=100% cellpadding=0 border=0><TR><TD>',
                     separatorlong(),
                     profile])

def ImageHTML(**attrs):
    if not attrs:
        return ''

    if 'src' in attrs:
        key = 'url'
        cls = 'BitmapFromWeb'
        data = attrs['src']
    elif 'data' in attrs:
        from base64 import b64encode
        log.error('Getting a bitmap from data is deprecated; data was: \n%s', b64encode(attrs['data']))
#        key = 'data'
#        cls = 'BitmapFromData'
#        data = b64encode(attrs['data'])
    else:
        assert False

    w = attrs.get('width', -1)
    h = attrs.get('height', -1)
    href = attrs['href']

    return ('<img width="%(w)d" height="%(h)d" src="%(href)s">') % locals()

def LinkHTML(url,text, nowrap = False):
    return u''.join([u'<a href=',
                     url,
                     u'>',
                     FontTagify((text.replace('\n','<br>') if isinstance(text,basestring) else ImageHTML(text) if isinstance(text,dict) else ''),
                                'link',
                                nowrap = nowrap),

                      u'</a>'])

def GenTimedString(timeinsecs):
    secs = int(time()) - timeinsecs

    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)

    if not (days > 0 or hours > 0 or mins > 0):
        return u'<1m'

    timeStr = u''
    if days > 0: timeStr += str(int(days)) + u'd&nbsp;'
    if hours > 0: timeStr += str(int(hours)) + u'h&nbsp;'
    if mins > 0 and days == 0: timeStr += str(int(mins)) + u'm'

    return timeStr

def JabberStatusMagic(contact):
    string=u''.join([TitleHTML(_('Subscription:')),BodyHTML(contact.protocol.roster.get_item_by_jid(contact.id).subscription.capitalize())])
    for r in contact.resources.values():
        string=u''.join([string,separatorshort(),TitleHTML(_('Resource:')),BodyHTML(u''.join([r.jid.resource or '',u' (',str(r.priority),u')']))])
        string=u''.join([string,u'<br>',TitleHTML(_(u'Status:')),BodyHTML(r.sightly_status)])
        import hooks
        if r.status_message and hooks.reduce('digsby.status.tagging.strip_tag', r.status_message, impl='text'):
            string=u''.join([string,u'<br>',BodyHTML(hooks.reduce('digsby.status.tagging.strip_tag', r.status_message, impl='text'))])
    return string

def GetLocationFromIP(contact):
    import urllib2
    import lxml
    from util.primitives.mapping import odict
    from common import pref
    info = odict()

    if pref('digsby.guest.geoiplookup', default = False, type = bool):
        if getattr(contact, 'ip', False):
            url  = 'http://www.iplocationtools.com/ip_query.php?output=xml&ip=%s' % contact.ip
            try:
                resp = urllib2.urlopen(url).read()
            except Exception:
                import traceback
                traceback.print_exc()
                return info

            try:
                doc = lxml.etree.fromstring(resp)
            except Exception:
                import traceback
                traceback.print_exc()
                return info

            divs = [
                    ('City', 'City'),
                    ('RegionName', 'State'),
                    ('CountryCode', 'Country'),
                   ]
            for tag, key in divs:
                val = doc.find(tag)
                if tag:
                    info[key] = val.text

    return info

def GetInfo(contact, showprofile=False, showhide=True, overflow_hidden=True):#showicon=True):

    css = '''\
table{
    table-layout: fixed;
}
body{
    word-wrap: break-word;
    %s
}
div{
    overflow: hidden;
}
''' % ('overflow: hidden' if overflow_hidden else '') + LINK_CSS + skin.get_css()

    no_icon_path = skin.get('BuddiesPanel.BuddyIcons.NoIcon').path.url()

    constanttop    = u'''\
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <style>
%(css)s
        </style>
        <script type="text/javascript">
            /* used to replace missing or BMP buddy icons with the default digsby one */
            function imgError(img) {
                img.onerror = "";
                img.src = "%(no_icon_path)s";
            }
        </script>
    </head>
    <body><div id="content"><TABLE WIDTH=100%% cellpadding=0 border=0><TR><TD valign=top>
''' % dict(css=css, no_icon_path=no_icon_path)

    constantmiddle = u'</TD><TD width="68" valign="top" align="center">'
    constantbottom = u'</TD></TR></TABLE></div></body></html>'

    s = contact.serviceicon

    if contact.service == 'digsby' and getattr(contact, 'iswidget', False):
        s = 'widget'

    ico = skin_get('serviceicons.' + s) if isinstance(s, basestring) else s
    servico=u''.join([u'<div style="white-space: nowrap; position: relative;"><div style = "position: absolute; left: 0px; top: 0px;">',
                      GenBitmapHTML(ico.path.url(), 16, 16),
                      u'</div>'])

    alias = contact.alias
    name=u''.join([u'<div style="white-space: normal; overflow: hidden; word-wrap: break-word; min-height: 20; margin: 0 0 0 20;">',
                   FontTagify(escape(alias),'header'),
                   u'</div></div>'])

    if s=='widget':
        location = GetLocationFromIP(contact) #odict
        moreinfo = u''

        if location:
            moreinfo = u''.join(['<div style="white-space: nowrap; width: 100%;">',
                                 TitleHTML(_(u'Location:')),
                                 BodyHTML(', '.join(location.values())),
                                 '</div>'])

        ip = u''.join(['<div style="white-space: nowrap; width: 100%;">',
                       TitleHTML(_(u'IP Address:')),
                      '<a href="http://www.geoiptool.com/en/?IP=%s">' % contact.ip,
                      BodyHTML(contact.ip),
                      '</a>',
                      '</div>'])

        time_ = u''.join(['<div style="white-space: nowrap;">',
                          TitleHTML(_(u'Time on Page:')),
                          DetailHTML(GenTimedString(contact.online_time)),
                          '</div>'])


        html = u''.join([constanttop, servico, name, time_, ip, moreinfo, constantbottom])

        return html

    nicename = contact.nice_name

    if nicename != alias:
        username = u''.join(['<div style="white-space: nowrap;">',
                             TitleHTML(protocols[contact.service].username_desc + u':'),
                             BodyHTML(nicename),
                             '</div>'])
    else:
        username = ''

    profile = ProfileHTML(contact.pretty_profile) if showprofile else u''

    times = ''
    if contact.service in ('icq', 'aim') and contact.online_time:
        times = u''.join([TitleHTML(_(u'Online:')),
                          DetailHTML(GenTimedString(contact.online_time))
                          ])

    idle_since = contact.idle
    if contact.service in ('icq', 'aim', 'yahoo') and idle_since and idle_since is not True:

        times += (u''.join([TitleHTML(('&nbsp; ' if times else '') + _(u'Idle:')),
                            DetailHTML(GenTimedString(idle_since)),
                            ]))

    away_since = getattr(contact, 'away_updated', None)
    if getattr(contact, 'away', False) and away_since:
        times += (u''.join([TitleHTML(_(('&nbsp; ' if times else '') + _(u'Away:'))),
                            DetailHTML(GenTimedString(away_since))
                            ]))
    if times:
        times = '<div>%s</div>' % times

    if contact.status_orb == 'unknown' or contact.service not in JABBER_SERVICES:
        status = u''.join(['<div style="white-space: nowrap;">',
                           TitleHTML(_(u'Status:')),
                           BodyHTML((_('{status} + Idle').format(status = contact.sightly_status) if contact.status == u'away' and contact.idle else contact.sightly_status)),
                           '</div>'])
    else:
        status = JabberStatusMagic(contact)

    statusmsg = getattr(contact, '_infobox_status_message', contact.status_message)
    import hooks
    if statusmsg is not None:
        statusmsg = hooks.reduce('digsby.status.tagging.strip_tag', statusmsg, impl='text')
    if not statusmsg or contact.service in JABBER_SERVICES:
        statusmsg = ''
    else:
        if contact.service not in ('aim', 'icq'):
            statusmsg = BodyHTML(statusmsg)

        statusmsg = u''.join((separatorshort(), statusmsg))

    icon = ''.join([constantmiddle,
                    GenStatusIconHTML(contact),
                    GenBuddyIconHTML(contact),
                    LinkHTML(u'profile', (_(u'Hide Profile') if showprofile else _(u'Show Profile')) if showhide else '', nowrap = True)])

    html = u''.join([constanttop, servico, name, username,
                     times, status, statusmsg, icon, profile, constantbottom])

    return linkify(html)
