'''

BuddyList renderers for drawing contact rows

'''
import util.primitives.strings as strings
from common import profile
from common.Buddy import get_status_orb

DEFAULT_NOICON_OPACITY = .40


import wx
from wx import ALIGN_LEFT, ALIGN_CENTER_VERTICAL, Font, Rect, ALIGN_BOTTOM, FONTFAMILY_DEFAULT, \
  FONTSTYLE_ITALIC, FONTSTYLE_NORMAL, FONTWEIGHT_BOLD, FONTWEIGHT_NORMAL, SystemSettings_GetColour, Point, \
  ALIGN_RIGHT, ALIGN_CENTER
lmiddle = ALIGN_LEFT | ALIGN_CENTER_VERTICAL
LBOTTOM = ALIGN_LEFT | ALIGN_BOTTOM
RBOTTOM = ALIGN_RIGHT | ALIGN_BOTTOM
from gui.textutil import default_font
from util.introspect import memoize
from util.lrucache import lru_cache
from util.primitives.error_handling import try_this
from util.primitives.funcs import isiterable, do
from util.primitives.mapping import Storage as S
from time import time
from logging import getLogger; log = getLogger('renderers'); info = log.info
from common import pref, prefprop
import hooks


from gui import skin
from gui.skin.skinobjects import SkinColor, Margins
syscol = lambda s: SkinColor(SystemSettings_GetColour(s))

from PIL import Image

from traceback import print_exc
import sys

replace_newlines = lru_cache(100)(strings.replace_newlines)

def contact_online(contact):
    'Whether to display a buddy as online or not in the buddylist.'

    return contact.online or contact.status == 'mobile'

def get_contact_status(contact):
    if not contact_online(contact):
        return ''

    msg = hooks.reduce('digsby.status.tagging.strip_tag', contact.stripped_msg, contact.status, impl='text')
    if msg is not None:
        return replace_newlines(msg)

    return ''

_cached_noicon = None

from gui.toolbox.imagefx import pil_setalpha

def _load_noicon():
    try:
        return skin.get('BuddiesPanel.BuddyIcons.NoIcon').PIL
    except:
        # A fallback.
        return Image.open(skin.resourcedir() / 'AppDefaults' / 'contact.png')

try:
    _registered_noicon_hook
except NameError:
    _registered_noicon_hook = False

def _on_skin_change(skin, variant):
    global _cached_noicon
    _cached_noicon = None

def get_no_icon(with_transparency = False):
    'Return the icon used for buddies with no icons.'

    global _cached_noicon
    global _registered_noicon_hook

    if not _registered_noicon_hook:
        _registered_noicon_hook = True
        import hooks
        hooks.register('skin.set.pre', _on_skin_change)

    try:
        return _cached_noicon[int(with_transparency)]
    except TypeError:
        pass

    img = _load_noicon()
    imgnoalpha = img.copy()

    try:
        # Transparency is specifed in a skin value like "66%"...
        alpha = skin.get('BuddiesPanel.BuddyIcons.NoIconAlpha', '75%').strip().rstrip('%')
        alpha_opacity = float(alpha) / 100.0
    except:
        alpha_opacity = DEFAULT_NOICON_OPACITY

    pil_setalpha(img, alpha_opacity) # Lighten the alpha channel somewhat


    _cached_noicon = (imgnoalpha, img)

    return _cached_noicon[int(with_transparency)]

def print_bicon_exc(buddykey):
    print_exc()

if not getattr(sys, 'DEV', False) or True:
    # on release builds, never print a traceback for a buddy's icon more than
    # once.
    print_bicon_exc = memoize(print_bicon_exc)

def _geticon(buddy):
    'Returns a valid buddy icon, or None.'

    try:
        icon = buddy.icon
    except Exception:
        print_bicon_exc(buddy.info_key)
        return None

    # don't return empty GIFs lacking any color
    try:
        if icon is not None:
            try:
                extrema = icon._extrema
            except AttributeError:
                extrema = icon._extrema = icon.getextrema()

            # extrema may be (0, 0) or ((0, 0), (0, 0), ...) for each channel
            if extrema != (0, 0) and not all(e == (0, 0) for e in extrema):
                return icon
    except Exception, e:
        try:
            print_bicon_exc(buddy.info_key)
        except Exception:
            pass # if we fail printing the exception, so what.

    return None

def get_buddy_icon_path(buddy):
    icon = _geticon(buddy)

    if icon is None:
        return skin.get('BuddiesPanel.BuddyIcons.NoIcon').path
    else:
        return buddy.icon_path

def get_buddy_icon_url(buddy):
    path = get_buddy_icon_path(buddy)

    # webkit is caching the icon; add the modification time to URL to
    # prevent stale icons from being shown
    return path.url() + '?modified=%d' % int(path.mtime)

def get_buddy_icon(buddy, size=None, round_size=1, grey_offline=True, with_transparency=False, meta_lookup=False):
    '''
    Returns a buddy icon or a special "no icon" image for the given buddy.

    size should be one integer, the size to resize to
    round_corners indicates whether to cut the corners off the icon
    '''
    icon = None

    if meta_lookup:
        metas = profile.blist.metacontacts.forbuddy(buddy)
        if metas:
            metas = set(metas)
            icon = _geticon(metas.pop())
            while icon is None and metas:
                icon = _geticon(metas.pop())

    if icon is None:
        icon = _geticon(buddy)

    isno = icon is None
    icon = get_no_icon(with_transparency) if isno else icon
    icon = icon.Resized(size) if size else icon

    if isno or not round_size:
        i = icon.Greyed.WXB if grey_offline and not contact_online(buddy) else icon.WXB
    else:
        i = icon.Rounded(round_size).WXB
        i = i.Greyed if grey_offline and not contact_online(buddy) else i

    return i

def get_idle_string(contact):
    '''
    Returns a single string, possibly empty for a contact's idle time.
    '''
    idle = getattr(contact, 'idle', None)

    if idle in (True, False, None):
        return ''

    elif isinstance(idle, (int, long)):
        diff = int(time() - idle)

        if diff != 0:
            return _get_idle_string_from_seconds(diff)
        else:
            return ''
    else:
        return ''
        #raise TypeError, str(type(idle))



@lru_cache(100)
def _get_idle_string_from_seconds(secs):
    'Formats seconds into a readable idle time, like (32) or (4:55)'

    mins,  secs  = divmod(secs, 60)
    hours, mins  = divmod(mins, 60)
    days,  hours = divmod(hours, 24)

    timeStr = ''
    if days:
        return '(%dd)' % int(days)
    if hours > 0:
        timeStr += '%d'  % int( hours ) + ":"
        timeStr += '%02d' % int( mins )
    else:
        mins = int(mins)
        if mins < 10:
            timeStr += '%dm' % mins
        else:
            timeStr += '%02dm' % mins

    return '(%s)' % timeStr if timeStr else ''

def get_prefs():
    try:
        from common import profile
        return profile.prefs
    except ImportError:
        from util.observe import ObservableDict
        return ObservableDict()


def safefont(name, size, bold = False):
    weight = FONTWEIGHT_BOLD if bold else FONTWEIGHT_NORMAL

    try:
        return Font(size, FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, weight, False, name)
    except:
        print_exc()

        font = default_font()
        font.SetPointSize(size)
        font.SetWeight(weight)
        return font





#from gui.ctextutil import RectPos
#wx.Rect.Pos = RectPos

class Renderer(object):
    'Common elements between Groups and Contacts.'

    def __init__(self, parent):
        self.parent = parent
        self.prefs = get_prefs()
        self.skin = S(fontcolors = S())

    def UpdateSkin(self):
        # Initialize skin values.
        s, g = self.skin, skin.get

        s.bg         = g('BuddiesPanel.Backgrounds.Buddy',    lambda: syscol(wx.SYS_COLOUR_LISTBOX))
        s.selectedbg = g('BuddiesPanel.Backgrounds.BuddySelected', lambda: syscol(wx.SYS_COLOUR_HIGHLIGHT))
        s.hoverbg    = g('BuddiesPanel.Backgrounds.BuddyHover',    lambda: syscol(wx.SYS_COLOUR_LISTBOX))

    def getpref(self, prefname, default = None):
        return pref('buddylist.layout.%s' % prefname, default)

    def attrlink(self, attr):
        return self.prefs.link('buddylist.layout.%s' % attr,
                               lambda val: (self.calcsizes(),
                                            self.parent.list_changed()), False, obj = self)

    def draw_background( self, obj, dc, rect, n, selected, hover ):
        s = self.skin
        if selected and s.selectedbg: s.selectedbg.Draw(dc, rect, n)
        elif hover and s.hoverbg:     s.hoverbg.Draw(dc, rect, n)
        elif s.bg:                    s.bg.Draw(dc, rect, n)


class GroupCellRenderer(Renderer):
    def __init__( self, parent ):
        Renderer.__init__(self, parent)

        layout_attrs = '''
        name_font_face
        name_font_size
        padding
        '''.strip().split()

        do(self.attrlink(attr) for attr in layout_attrs)

        self.UpdateSkin()

    def UpdateSkin(self):
        Renderer.UpdateSkin(self)
        s = self.skin

        s.margins          = skin.get('BuddiesPanel.GroupMargins')
        s.padding          = skin.get('BuddiesPanel.GroupPadding', lambda: Point(4,4))

        # Expanded/Collapsed icons next to group names
        g = lambda k, default = sentinel: skin.get('BuddiesPanel.GroupIcons.' + k, default)
        s.expanded         = g('Expanded',         lambda: None)
        s.expandedhover    = g('ExpandedHover',    lambda: s.expanded)
        s.expandedselected = g('ExpandedSelected', lambda: s.expanded)

        s.collapsed         = g('Collapsed',         lambda: None)
        s.collapsedhover    = g('CollapsedHover',    s.collapsed)
        s.collapsedselected = g('CollapsedSelected', s.collapsed)

        # Group backgrounds (default to Buddy backgrounds if not specified)
        g = lambda k, default: skin.get('BuddiesPanel.Backgrounds.' + k, default)
        s.bg         = g('Group',         lambda: g('Buddy'))
        s.hoverbg    = g('GroupHover',    lambda: g('BuddyHover'))
        s.selectedbg = g('GroupSelected', lambda: g('BuddySelected'))

        # Group font colors (default to Buddy font colors if not specified)
        f = s.fontcolors
        g = lambda k, default: skin.get('BuddiesPanel.FontColors.' + k, default)
        f.group         = g('Group',         lambda: g('Buddy',         lambda: syscol(wx.SYS_COLOUR_WINDOWTEXT)))
        f.grouphover    = g('GroupHover',    lambda: g('BuddyHover',    lambda: syscol(wx.SYS_COLOUR_WINDOWTEXT)))
        f.groupselected = g('GroupSelected', lambda: g('BuddySelected', lambda: syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT)))

        self.calcsizes()

    def item_height( self, obj ):
        return int(self.group_height)

    def calcsizes(self):
        p = self.getpref
        margins = self.skin.margins
        padding = self.skin.padding

        # Main Font: contact's name
        self.mainfont        = safefont(p('name_font_face', None), try_this(lambda: int(p('name_font_size')), 10))
        self.mainfont_height = self.mainfont.LineHeight

        # group_height is reported via OnMeasureItem to VListBox
        self.group_height = int(self.mainfont_height) + margins.top + margins.bottom + (padding.y * 2)

        self.depth_indent = p('indent', 5)

    font_face    = prefprop('buddylist.layout.name_font_face', None)
    font_size    = prefprop('buddylist.layout.name_font_size', None)
    group_indent = prefprop('buddylist.layout.indent', 0)

    def Draw( self, dc, rect, selected, obj, depth, expanded, index, hover ):
        s = self.skin

        # apply margins
        rect = rect.AddMargins(wx.Rect(*s.margins)).AddMargins(wx.Rect(0, s.padding.y, 0, s.padding.y))

        # Group font is drawn with the same as the buddies.
        fontface = self.font_face
        font = safefont(fontface, try_this(lambda: int(self.font_size), 10), bold = True)
        dc.SetFont( font )

        # indent for depth
        rect = rect.Subtract(left = self.group_indent * depth)

        # Expander triangles.
        if isiterable( obj ):
            triangle = self.get_expander(selected, expanded, hover)

            if triangle is not None:
                dc.DrawBitmap(triangle, rect.x, rect.VCenter(triangle), True)
                rect = rect.Subtract(left = triangle.Width + s.padding.x)

        # decide on a foreground text color
        if selected: fg = s.fontcolors.groupselected
        elif hover:  fg = s.fontcolors.grouphover
        else:        fg = s.fontcolors.group
        dc.SetTextForeground( fg )

        # the actual text label
        dc.DrawTruncatedText(obj.display_string, rect, alignment = lmiddle)

    def get_expander(self, selected, expanded, hover):
        iconname = 'expanded' if expanded else 'collapsed'
        if selected: iconname += 'selected'
        elif hover:  iconname += 'hover'
        return getattr(self.skin, iconname, None)

class ContactCellRenderer(Renderer):
    def __init__(self, parent):
        Renderer.__init__(self, parent)

        self._lastcalc = None

        # changing any of these prefs triggers a RefreshAll
        self.layout_attrs = '''
        name_font_face
        name_font_size
        show_extra
        extra_info
        extra_font_face
        extra_font_size
        extra_padding
        show_buddy_icon
        buddy_icon_pos
        badge_max_size
        badge_min_size
        show_status_icon
        status_icon_pos
        status_icon_size
        show_service_icon
        service_icon_pos
        badge_ratio
        buddy_icon_size
        service_icon_size
        side_icon_size
        padding
        indent
        grey_offline
        blocked
        '''.strip().split()

        do(self.attrlink(attr) for attr in self.layout_attrs)


        self.UpdateSkin()

    icons = ['service_icon', 'status_icon', 'buddy_icon']

    def UpdateSkin(self):
        Renderer.UpdateSkin(self)

        self.drawseqs = {}
        self._lastcalc = []

        s, g = self.skin, skin.get

        self.statusicons = g('statusicons')

        s.margins          = g('BuddiesPanel.BuddyMargins')
        s.icon_frame      = g('BuddiesPanel.BuddyIcons.Frame', None)
        s.icon_frame_size = Margins(g('BuddiesPanel.BuddyIcons.FrameSize', (0, 0, 0, 0)))

        s.round_corners = try_this(lambda: int(g('BuddiesPanel.BuddyIcons.Rounded', 1)), 1)

        f, g = s.fontcolors, lambda k, default: skin.get('BuddiesPanel.FontColors.' + k, default)
        f.buddy            = g('Buddy',         lambda: syscol(wx.SYS_COLOUR_WINDOWTEXT))
        f.buddyoffline     = g('BuddyOffline',  lambda: syscol(wx.SYS_COLOUR_GRAYTEXT))
        f.buddyselected    = g('BuddySelected', lambda: syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        f.buddyhover       = g('BuddyHover',    lambda: f.buddy)

        f.status           = g('Status',         lambda: f.buddy)
        f.statushover      = g('StatusHover',    lambda: f.buddyhover)
        f.statusselected   = g('StatusSelected', lambda: f.buddyselected)

        f.idletime         = g('IdleTime',         lambda: syscol(wx.SYS_COLOUR_GRAYTEXT))
        f.idletimehover    = g('IdleTimeHover',    lambda: syscol(wx.SYS_COLOUR_GRAYTEXT))
        f.idletimeselected = g('IdleTimeSelected', lambda: syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT))

        # icons to be drawn
        self.calcsizes()

    def calcsizes(self):
        p, s = self.getpref, self.skin
        padding = p('padding', 4)

        do(setattr(self, k.replace('.', '_'), p(k)) for k in self.layout_attrs)

        # Main Font: contact's name
        sz = int(p('name_font_size', 10))
        self.mainfont = safefont(p('name_font_face', None), sz)
        self.mainfont.Style = FONTSTYLE_NORMAL
        self.mainfont_height = mainfont_height = self.mainfont.LineHeight

        # Extra font: idle time, status message
        self.extrafont = safefont(p('extra_font_face', None), int(p('extra_font_size', 10)))
        self.extrafont_height = extrafont_height = self.extrafont.LineHeight

        # depth indent
        self.depth_indent = p('indent', 5)

        # decide on a maximum height
        icon_size = p('buddy_icon_size', 0)
        if s.icon_frame_size:
            # add overlay size if necessary
            icon_size += s.icon_frame_size.top + s.icon_frame_size.bottom


        show_icon = p('show_buddy_icon', False)

        # item_height method will use this
        extraheight = extrafont_height if (p('show_extra', True) \
                                           and p('extra_info', 'status') in ('status','both'))\
                                            else 0
        margins = self.skin.margins
        self.cell_height = padding * 2 + \
            max(icon_size  if show_icon else 0, mainfont_height + extraheight) + \
            margins.top + margins.bottom

        if self.cell_height < mainfont_height * 1.2:
            self.cell_height = mainfont_height * 1.2

        self.drawseqs.clear()
        self._serviceiconcache = {}
        self._lastcalc = None
        return self.cell_height

    def calcdraw(self, w, h, Rect = Rect):
        if self._lastcalc == (w, h):
            return self._lastseq

        s = self.skin
        rect = Rect(0, 0, w, h).AddMargins(wx.Rect(*s.margins))
        icons = sorted(((icon, getattr(self, icon + '_pos')) for icon in self.icons),
                       key = lambda o: {'f': -1, 'b': 1}.get(o[1][0], 0))

        seq        = []
        last       = Rect()
        badge_size = min(self.badge_max_size, max(self.badge_min_size, int(self.buddy_icon_size * self.badge_ratio)))
        frame_size = s.icon_frame_size
        padding    = self.padding
        hpadding   = 4

        for icon, pos in icons:
            if getattr(self, 'show_' + icon):
                pos     = pos.lower()
                size    = getattr(self, icon + '_size')
                left    = pos.endswith('left')
                iconpos = Point(-size * int(not left), 0)

                if icon == 'buddy_icon':
                    # special case for buddy icon, which can optionally have a frame around it.
                    iconw = size + frame_size.left + frame_size.right
                    frameRect = Rect(0, 0, iconw, size + frame_size.top + frame_size.bottom)
                    frameRect.x, frameRect.y = rect.Pos(wx.Point(-frameRect.width * int(not left), 0))[0], rect.VCenterH(frameRect.height)

                    last = Rect(frameRect.x + frame_size.left, frameRect.y + frame_size.top, size, size)
                    seq += [(getattr(self, 'get_buddy_icon'), last, 0)]

                    seq += [(getattr(self, 'get_frame_icon'), frameRect, 0)]
                    rect = rect.Subtract(**{'left' if left else 'right':  iconw + hpadding})
                    bitmap = getattr(self, 'get_' + icon)
                else:
                    if not pos.startswith('b'):
                        # non badge
                        r = Rect(rect.Pos(iconpos)[0], rect.VCenterH(size), size, size)
                        rect = rect.Subtract(**{'left' if left else 'right': size + hpadding})
                        last = r
                        alignment = ALIGN_CENTER
                        bitmap = getattr(self, 'get_' + icon)
                    else:
                        # badge
                        bp        = badge_size
                        alignment = LBOTTOM if left else RBOTTOM
                        badgepos  = last.Pos(wx.Point(0 if left else -bp, -bp))
                        r         = Rect(badgepos[0], badgepos[1], badge_size,  badge_size)

                        bitmap = lambda obj, icon=icon: getattr(self, 'get_' + icon)(obj).ResizedSmaller(badge_size)

                    seq.append((bitmap, r, alignment))


        self.inforect  = rect
        self._lastcalc = (w, h)
        self._lastseq  = seq
        return seq

    def Draw(self, dc, rect, selected, obj, depth, expanded, index, hover, Rect = Rect):
        DrawBitmap             = dc.DrawBitmap
        DrawTruncatedText      = dc.DrawTruncatedText
        idle_string            = get_idle_string(obj)
        extrafont              = self.extrafont
        extra_info             = self.extra_info if self.show_extra else None
        msg                    = get_contact_status(obj)
        padding, extra_padding = self.padding, self.extra_padding
        contact_name           = obj.alias
        mainfont_height        = self.mainfont_height


        # draw all icons
        for method, r, align in self.calcdraw(rect.width, rect.height):
            try:
                b = method(obj)
            except:
                print_exc()
            else:
                if b: b.Draw(dc, Rect(rect.x + r.x, rect.y + r.y, r.width, r.height), align)

        rect = rect.AddMargins(wx.Rect(*self.skin.margins))
        rect.x, rect.width = self.inforect.x, self.inforect.width

        # draw the status message (if necessary)
        if msg and extra_info in ('status', 'both'):
            th       = self.mainfont.LineHeight + extra_padding + self.extrafont_height
            rect     = Rect(rect.x, rect.VCenterH(th), rect.width, rect.height)
            namerect = Rect(rect.x, rect.y + 1, rect.Width, self.mainfont.LineHeight)
            inforect = Rect(rect.x, rect.y + self.mainfont.LineHeight + extra_padding, rect.Width, self.extrafont_height)

            DrawTruncatedText(self.get_contact_info(obj, dc, selected, expanded, hover), inforect, alignment = lmiddle)
        else:
            namerect = rect

        # draw idle time
        hpadding = 4
        if idle_string and extra_info in ('idle', 'both'):
            # do some measurements to see if
            #  a) idle time needs to be left aligned against the buddy name, or
            #  b) right aligned and cutting off the buddy name (i.e., buddy na...IDLE)
            namew, nameh, namedescent, __ = dc.GetFullTextExtent(contact_name, self.mainfont)
            w, h, desc, __ = dc.GetFullTextExtent(idle_string, extrafont)

            iy = 3
            diff = namew + w + hpadding - namerect.width

            if diff > 0:
                x, y = namerect.Pos((-w, 0))[0], namerect.Y
                r = Rect(x, y, w, namerect.Height)
                namerect = namerect.Subtract(right = w + hpadding)
            else:
                r = Rect(namerect.X + namew + hpadding, namerect.Y, w, namerect.Height)

            self.set_idle_time_dc(obj, dc, selected, expanded, hover)
            dc.DrawLabel(idle_string, r, ALIGN_LEFT | ALIGN_CENTER_VERTICAL)

        # draw buddy name
        self.set_contact_name_dc(obj, dc, selected, expanded, hover)
        DrawTruncatedText(contact_name, namerect, alignment = lmiddle)

    def get_buddy_icon(self, contact, *a):
        return get_buddy_icon(contact, self.buddy_icon_size, self.skin.round_corners, self.grey_offline, with_transparency = True)

    def get_frame_icon(self, contact, *a):
        return self.skin.icon_frame

    def get_service_icon(self, contact, *a):
        try:
            icon = contact.serviceicon
        except AttributeError:
            icon = skin.get('serviceicons.' + contact.service)

        if max(icon.Width, icon.Height) > self.service_icon_size:
            icon = icon.Resized(self.service_icon_size)

        if self.grey_offline and not contact_online(contact):
            icon = icon.Greyed

        return icon


    def get_status_icon(self, contact, *a):
        "Returns an icon for a contact's status."
        if contact.blocked:
            orb = 'blocked'
        else:
            try:
                orb = contact.status_orb
            except AttributeError:
                orb = get_status_orb(contact)
        icon = skin.get('statusicons.'+orb)
        if max(icon.Width, icon.Height) > self.status_icon_size:
            return icon.Resized(self.status_icon_size)
        else:
            return icon


    def set_contact_name_dc(self, contact, dc, selected, expanded, hover):
        'Returns a name for the given contact.'

        # select foreground colors
        fontcolors = self.skin.fontcolors
        online = contact_online(contact)

        if selected:     fg = fontcolors.buddyselected
        elif hover:      fg = fontcolors.buddyhover
        elif not online: fg = fontcolors.buddyoffline
        else:            fg = fontcolors.buddy

        dc.TextForeground = fg

        # select font
        mainfont = self.mainfont
        mainfont.SetStyle(FONTSTYLE_NORMAL if online else FONTSTYLE_ITALIC)

        # bold the buddyname when just after they come online
        mainfont.SetWeight(FONTWEIGHT_BOLD if getattr(contact, 'entering', False) else FONTWEIGHT_NORMAL)

        dc.SetFont( mainfont )

    def set_idle_time_dc(self, contact, dc, selected, expanded, hover):
        # select foreground colors
        fontcolors = self.skin.fontcolors

        if selected: fg = fontcolors.idletimeselected
        elif hover:  fg = fontcolors.idletimehover
        else:        fg = fontcolors.idletime

        dc.TextForeground = fg

        # select font
        dc.Font = self.extrafont

    def get_contact_info(self, contact, dc, selected, expanded, hover):
        'Line #2 of the contact row (the status message)'

        # select foreground colors
        fontcolors = self.skin.fontcolors

        if selected: fg = fontcolors.statusselected
        elif hover:  fg = fontcolors.statushover
        else:        fg = fontcolors.status

        dc.TextForeground = fg

        dc.SetFont( self.extrafont )
        return get_contact_status(contact)

    def item_height( self, obj ):
        return int(self.cell_height)

class MetaContactCellRenderer(ContactCellRenderer):
    def __init__(self, parent):
        ContactCellRenderer.__init__(self, parent)

class SearchCellBase(Renderer):
    icon_height = 16

    def __init__(self, parent):
        Renderer.__init__(self, parent)
        self.UpdateSkin()

        for attr in ('padding', 'name_font_face', 'name_font_size'):
            self.attrlink(attr)

    def calcsizes(self):
        s = self.skin
        p = self.getpref
        self.padding = p('padding')
        self.mainfont        = safefont(p('name_font_face', None), try_this(lambda: int(p('name_font_size')), 10))
        self.mainfont_height = self.mainfont.LineHeight
        self.cell_height = (max(self.icon_height, self.mainfont_height) +
                            s.margins.top + s.margins.bottom +
                            self.padding * 2)

    def item_height(self, obj):
        return self.cell_height

class SearchCellRenderer(SearchCellBase):
    '''
    Draws buddylist entries for searching the web
    '''

    icon_horizontal_padding = 8

    def UpdateSkin(self):
        Renderer.UpdateSkin(self)
        s = self.skin
        self.skin.margins = skin.get('BuddiesPanel.BuddyMargins')

        f, g = s.fontcolors, lambda k, default: skin.get('BuddiesPanel.FontColors.' + k, default)
        f.buddy            = g('Buddy',         lambda: syscol(wx.SYS_COLOUR_WINDOWTEXT))
        f.buddyoffline     = g('BuddyOffline',  lambda: syscol(wx.SYS_COLOUR_GRAYTEXT))
        f.buddyselected    = g('BuddySelected', lambda: syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        f.buddyhover       = g('BuddyHover',    lambda: f.buddy)
        f.details          = g('IdleTime',      lambda: syscol(wx.SYS_COLOUR_GRAYTEXT))

        self.calcsizes()

    def Draw(self, dc, rect, selected, obj, depth, expanded, index, hover):
        s = self.skin
        icon = skin.get('appdefaults.search.icons.' + obj.searchengine.name, None)

        rect = rect.AddMargins(wx.Rect(*s.margins))

        if icon is not None:
            dc.DrawBitmap(icon, rect.x, rect.VCenter(icon), True)
            rect = rect.Subtract(left = icon.Width + self.icon_horizontal_padding)

        dc.SetFont(self.mainfont)

        if selected: fg = s.fontcolors.buddyselected
        elif hover:  fg = s.fontcolors.buddyhover
        else:        fg = s.fontcolors.buddy
        dc.TextForeground = fg

        # draw search engine name
        text = obj.searchengine.gui_name + ': '
        w, h, desc, __ = dc.GetFullTextExtent(text)
        dc.DrawLabel(text, rect, ALIGN_LEFT | ALIGN_CENTER_VERTICAL)
        rect = rect.Subtract(left = w)

        # draw search string
        dc.TextForeground = s.fontcolors.details
        text = obj.searchstring
        dc.DrawTruncatedText(text, rect, ALIGN_LEFT | ALIGN_CENTER_VERTICAL)

class SearchCellOptionsRenderer(SearchCellBase):
    def UpdateSkin(self):
        Renderer.UpdateSkin(self)
        s = self.skin
        self.skin.margins = skin.get('BuddiesPanel.BuddyMargins')

        f, g = s.fontcolors, lambda k, default: skin.get('BuddiesPanel.FontColors.' + k, default)
        f.details = g('IdleTime',      lambda: syscol(wx.SYS_COLOUR_GRAYTEXT))

        self.calcsizes()

    def Draw(self, dc, rect, selected, obj, depth, expanded, index, hover):
        s = self.skin
        rect = rect.AddMargins(wx.Rect(*s.margins))
        dc.SetFont(self.mainfont)

        # WARNING: assuming icon height = width
        rect = rect.Subtract(left = self.icon_height + 8)

        # draw options string
        dc.TextForeground = s.fontcolors.details
        dc.DrawTruncatedText(_('Options...'), rect, ALIGN_LEFT | ALIGN_CENTER_VERTICAL)

