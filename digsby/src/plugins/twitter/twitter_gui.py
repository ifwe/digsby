from gui.uberwidgets.spacerpanel import SpacerPanel
from gui.uberwidgets.formattedinput2.formatprefsmixin import StyleFromPref
from gui.toolbox.scrolling import WheelScrollCtrlZoomMixin, \
                                            WheelShiftScrollFastMixin,\
    ScrollWinMixin, FrozenLoopScrollMixin
if __name__ == '__main__':
    import __builtin__
    __builtin__._ = lambda s: s

import config
import hooks
import wx.webview
import unicodedata
from traceback import print_exc
import twitter_util
from common import pref, setpref

from functools import wraps
from collections import namedtuple
from time import time
from util import threaded, traceguard, odict
from util.primitives.funcs import Delegate
from util.callbacks import CallbackStream
from util.net import isurl

from gui.uberwidgets.formattedinput2.FormattedExpandoTextCtrl import FormattedExpandoTextCtrl
from gui.uberwidgets.formattedinput2.splittereventsmixin import SplitterEventMixin
from gui.uberwidgets.UberBar import UberBar
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.umenu import UMenu
from gui.uberwidgets.simplemenu import SimpleMenuItem
from gui.toolbox import OKCancelFrame, GetDoubleClickTime, std_textctrl_menu, \
    pick_image_file, paint_outline, insert_text
from gui.anylists import AnyList, AnyRow
from gui.social_status_dialog import color_for_message, _msg_color_thresholds
from gui import skin, clipboard
import gui.windowfx as fx

from logging import getLogger; log = getLogger('twitter_gui')

import mimetypes

if config.platform == 'win':
    import gui.native.win.winhelpers
    gui.native.win.winhelpers.__file__ # gettattr actually causes it to load (for side effects...)

TWITTER_MAX_CHARCOUNT = 140
SEARCH_HELP_URL = 'http://search.twitter.com/operators'

KEEP_ON_TOP_LABEL = _('&Keep on Top')

WEBKIT_TRENDS_MINSIZE = (350, 50)
GROUP_LIST_MINSIZE = (WEBKIT_TRENDS_MINSIZE[0], 180)
flags = wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND

ID_FAVORITES = wx.NewId()
ID_HISTORY = wx.NewId()

ID_NEWGROUP = wx.NewId()
ID_NEWSEARCH = wx.NewId()
ID_EDITANDREARRANGE = wx.NewId()
ID_DELETE_FEED = wx.NewId()
ID_EDIT_FEED = wx.NewId()
ID_TOGGLE_ADDSTOCOUNT = wx.NewId()

ID_SHORTEN_LINKS = wx.NewId()
ID_IMAGE = wx.NewId()
ID_SHRINK = wx.NewId()
ID_GLOBAL_STATUS = wx.NewId()

ID_HIDE_INPUT_BAR = wx.NewId()

ID_MARKFEEDASREAD = wx.NewId()

ID_KEEPONTOP = wx.NewId()
ID_INCREASE_TEXT_SIZE = wx.NewId()
ID_DECREASE_TEXT_SIZE = wx.NewId()
ID_RESET_TEXT_SIZE = wx.NewId()
ID_UPDATE = wx.NewId()
ID_WEBVIEW_COPY = wx.NewId()

TwitterUser = namedtuple('TwitterUser', 'id screen_name selected profile_image_url')

def message_color(m):
    return wx.Color(*color_for_message(m, _msg_color_thresholds))

permanent_feed_types = set(('timeline', 'mentions', 'directs'))
def is_perm_feed(feed):
    return feed['type'] in permanent_feed_types

class TwitterDialog(OKCancelFrame):
    default_style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT
    def __init__(self, *a, **k):
        if 'style' not in k:
            k['style'] = TwitterDialog.default_style

        OKCancelFrame.__init__(self, *a, **k)

        self.on_info = Delegate()
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.SetFrameIcon(skin.get('serviceicons.twitter'))

    def set_component(self, panel):
        self.SetBackgroundColour(panel.BackgroundColour)
        OKCancelFrame.set_component(self, panel, border=5, line=True)
        self.Fit()
        self.SetMinSize(self.Size)

    def on_button(self, e):
        self.Hide()
        if e.Id == wx.ID_OK:
            self.on_info(self.info())

        self.Destroy()

class TwitterSearchDialog(TwitterDialog):
    def __init__(self, parent, options):

        if options.get('title', None):
            ok_caption = _('&Save')
            saving = True
        else:
            ok_caption = _('&Search')
            saving = False

        TwitterDialog.__init__(self, parent,
                           title = _('Twitter Search'),
                           ok_caption = ok_caption,
                           cancel_caption = _('&Cancel'),
                           style = TwitterDialog.default_style & ~wx.RESIZE_BORDER)

        self.search_panel = TwitterSearchPanel(self, options, saving)
        self.set_component(self.search_panel)

    def info(self):
        return self.search_panel.info()

class TwitterDialogPanel(wx.Panel):
    def __init__(self, *a, **k):
        wx.Panel.__init__(self, *a, **k)

    def escape_closes(self, e):
        if e.KeyCode == wx.WXK_ESCAPE:
            self.SimulateCommandEvent(wx.ID_CANCEL)
        else:
            e.Skip()

    def SimulateCommandEvent(self, id):
        event = wx.CommandEvent(wx.EVT_COMMAND_BUTTON_CLICKED, id)
        return self.ProcessEvent(event)


class TwitterSearchPanel(TwitterDialogPanel):
    'The main panel for the Twitter search dialog.'

    def __init__(self, parent, options, saving):
        TwitterDialogPanel.__init__(self, parent)
        self.feed_name = options.get('name', None)

        self.setup_help_button()

        self.construct(options)
        self.layout(options)
        self.saving = saving

    def info(self):
        info = dict()

        for attr in ('query', 'title', 'merge', 'popups'):
            ctrl = getattr(self, attr, None)
            if ctrl is not None:
                info[attr] = ctrl.Value

        if self.feed_name is not None:
            info['name'] = self.feed_name

        info.update(type = 'search',
                    save = self.saving)

        return info

    def construct(self, options):
        trends = options.get('trends', None)

        # Search For
        search_for_string = options.get('query', '')
        self.search_for_header = header(self, _('Search For:'))
        self.query = wx.TextCtrl(self, value=search_for_string)
        self.query.Bind(wx.EVT_KEY_DOWN, self.escape_closes)
        focus_on_show(self.query)

        # Title
        title = options.get('title', None)
        if title is not None:
            self.title_header = header(self, _('Title:'))
            self.title = wx.TextCtrl(self, value=make_title(title, search_for_string))
            self.title.Bind(wx.EVT_KEY_DOWN, self.escape_closes)

        # Trending Topics
        if trends is not None:
            self.trending_topics_header = header(self, _('Trending Topics:'))
            webview = self.trending_topics_html = WebKitDisplay(self)
            webview.SetMinSize(WEBKIT_TRENDS_MINSIZE)

            webview.SetPageSource(trending_topics_html(trends))
            webview.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.__beforeload)

        # Search Options
        search_opts = options.get('search_opts', None)
        if search_opts is not None:
            self.search_opts_header = header(self, _('Search &Options'))
            self.merge  = wx.CheckBox(self, -1, _('Merge search results into Timeline view'))
            self.merge.Value = bool(search_opts.get('merge', False))
            self.popups = wx.CheckBox(self, -1, _('Popup notifications for new search results'))
            self.popups.Value = bool(search_opts.get('popups', True))

    def layout(self, options):
        items = []

        # Title
        if options.get('title', None) is not None:
            items.extend([self.title_header, self.title])

        # Search For
        items.extend([(1, 3),
                      (self.search_for_header, 0),
                      (1, 3),
                      self.query])

        # Trending Topics
        if options.get('trends', None) is not None:
            items.extend([self.trending_topics_header,
                          (self.trending_topics_html, 0, wx.EXPAND, 0)])
        else:
            items.extend((WEBKIT_TRENDS_MINSIZE[0], 0))

        # Search Options
        if options.get('search_opts', None) is not None:
            items.extend([self.search_opts_header, self.merge, self.popups])

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany((item, 0, wx.BOTTOM | wx.EXPAND, 5) if not isinstance(item, tuple) else item
                       for item in items)

        self.Sizer = outer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        outer_sizer.Add(sizer, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 4)

    def __beforeload(self, e):
        e.Cancel()

        trend = e.URL.decode('utf8url')
        self.query.Value = trend

        if self._is_double_click(trend):
            self.SimulateCommandEvent(wx.ID_OK)
        else:
            self.query.SetInsertionPointEnd()
            self.query.SetFocus()

    def _is_double_click(self, trend):
        # keep track of the last time a trend was clicked to simulate double clicks
        is_double_click = False

        now = time()
        if hasattr(self, 'last_link_click'):
            last_trend, last_time = self.last_link_click
            if last_trend == trend and now - last_time <= GetDoubleClickTime():
                is_double_click = True

        self.last_link_click = (trend, now)

        return is_double_click

    # painting/clicking the help button

    def setup_help_button(self):
        self.help_bitmap = wx.Bitmap(skin.resourcedir() / 'skins/default/help.png')
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.in_help = False

    def OnMotion(self, e):
        e.Skip()
        if self.HelpRectangle.Contains(e.Position):
            if not self.in_help:
                self.in_help = True
                self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        else:
            if self.in_help:
                self.in_help = False
                self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

    def OnLeftDown(self, e):
        if self.HelpRectangle.Contains(e.Position):
            wx.LaunchDefaultBrowser(SEARCH_HELP_URL)
        else:
            e.Skip()

    def OnPaint(self, e):
        dc = wx.PaintDC(self)
        r = self.HelpRectangle
        dc.DrawBitmap(self.help_bitmap, r.x, r.y, True)

    @property
    def HelpRectangle(self):
        b = self.help_bitmap
        r = wx.RectPS(self.query.Rect.TopRight, (b.Width, b.Height))
        r.Position = r.Position - wx.Point(*r.Size) - wx.Point(0, 3)
        return r

from gui.browser.webkit import WebKitDisplay

if config.platform == 'win':
    FONT_CSS = 'font-family: Tahoma, MS Sans Serif; font-size: 11px;'
else:
    FONT_CSS = '' # TODO: platform GUI fonts

def trending_topics_html(trends):
    'Returns the HTML that gets put into the webview for showing trending topics.'

    # try to match the default GUI dialog color
    dialog_html_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE).GetAsString(wx.C2S_HTML_SYNTAX)

    links = []
    for trend in trends:
        links.append('<a href="{query}">{name}</a>'.format(
            query = trend['query'].encode('utf8url'),
            name = trend['name'].encode('utf8')))

    topics_html = ', '.join(links)

    css = '''\
body {
    margin: 0;
    background-color: %s;
    %s
    -webkit-text-size-adjust: none;
    -webkit-user-select: none;
}''' % (dialog_html_color, FONT_CSS)

    html = '<!doctype html><html><head><style>{css}</style></head><body><div id="container">{body}</container></body></html>'

    return html.format(css=css, body=topics_html)

def make_title(title, search_for):
    if isinstance(title, basestring) and title:
        return title
    else:
        return search_for.split()[0]

class TwitterGroupDialog(TwitterDialog):
    def __init__(self, parent, options=None):
        TwitterDialog.__init__(self, parent,
                               title = _('Twitter Group'),
                               ok_caption = _('&Save'))

        self.group_panel = TwitterGroupPanel(self, options)
        self.set_component(self.group_panel)

    def info(self):
        return self.group_panel.info()

class TwitterGroupPanel(TwitterDialogPanel):
    def __init__(self, parent, options = None):
        TwitterDialogPanel.__init__(self, parent)

        if options is None:
            options = {}

        self.users = options.get('users')
        self.feed_name = options.get('name', None)
        self.construct(options)
        self.layout(options)

        # disable the OK button if there is no group name
        self.groupName.Bind(wx.EVT_TEXT, self.on_text)
        self.on_text()
        self.Bind(wx.EVT_PAINT, self.__onpaint)

    def __onpaint(self, e):
        e.Skip()
        dc = wx.PaintDC(self)

        paint_outline(dc, self.group_members_list)

    def on_text(self, e=None):
        if e is not None: e.Skip()
        self.Top.OKButton.Enable(bool(self.groupName.Value))

    def info(self):
        info = dict(ids = [row.data.id for row in self.group_members_list
                       if row.IsChecked()])

        for attr in ('groupName', 'filter', 'popups'):
            ctrl = getattr(self, attr, None)
            if ctrl is not None:
                info[attr] = ctrl.Value

        if self.feed_name is not None:
            info['name'] = self.feed_name

        info['type'] = 'group'

        return info

    def construct(self, options):
        self.group_name_header = header(self, _('&Group Name'))
        self.groupName = wx.TextCtrl(self, -1, options.get('groupName', ''))
        focus_on_show(self.groupName)
        self.groupName.Bind(wx.EVT_KEY_DOWN, self.escape_closes)

        self.group_members_header = header(self, _('Group &Members'))
        self.group_members_list = TwitterUserList(self, self.users,
                                                  row_control     = TwitterUserRow,
                                                  edit_buttons    = None,
                                                  draggable_items = False,
                                                  velocity        = None)

        self.group_members_list.SetMinSize(GROUP_LIST_MINSIZE)

        if options.get('search', False):
            self.group_members_search = wx.SearchCtrl(self, -1)
            self.group_members_search.ShowSearchButton(True)

        self.group_options_header = header(self, _('Group &Options'))
        self.filter = wx.CheckBox(self, -1, _("&Filter this group's tweets out of the Timeline view"))
        self.filter.Value = options.get('filter', False)
        self.popups = wx.CheckBox(self, -1, _("Show &popup notifications for this group's tweets"))
        self.popups.Value = options.get('popups', False)

    def layout(self, options):
        members_header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        members_header_sizer.Add(self.group_members_header, 0, wx.ALIGN_BOTTOM)
        if options.get('search', False):
            members_header_sizer.AddStretchSpacer(1)
            members_header_sizer.Add(self.group_members_search, 0, wx.EXPAND)

        padding = 5
        ctrls = [
            self.group_name_header,
            self.groupName,
            members_header_sizer,
            (self.group_members_list, 1, flags, padding),
            (1, 3),
            self.group_options_header,
            self.filter,
            self.popups,
        ]

        sizer = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany((c, 0, flags, padding) if not isinstance(c, tuple) else c
                      for c in ctrls)
        sizer.Add((1,6))

class TwitterUserList(AnyList):
    SelectionEnabled = False
    ClickTogglesCheckbox = True

    def __init__(self, *a, **k):
        AnyList.__init__(self, *a, **k)

        self.image_map = {}

        from gui.browser.webkit.imageloader import WebKitImageLoader
        self.image_loader = WebKitImageLoader()
        self.image_loader.on_load += self.on_load

        self.Top.Bind(wx.EVT_CLOSE, self.__OnClosing)

    def __OnClosing(self, e):
        e.Skip()
        self.disconnect()

    def disconnect(self):
        self.image_loader.on_load -= self.on_load

    def on_load(self, img, src):
        if wx.IsDestroyed(self):
            self.disconnect()
            return

        data = self.image_map[src]
        data['bitmap'] = img

        # repaint all rows with this url
        for ctrl in data['ctrls']:
            ctrl.Refresh()

    def get_image(self, row):
        url = row.profile_image_url
        if not url: return None

        try:
            imgdata = self.image_map[url]
        except KeyError:
            imgdata = self.image_map[url] = dict(
                    bitmap=self.image_loader.get(url),
                    ctrls=set([row]))

        imgdata['ctrls'].add(row)
        return imgdata['bitmap']

class TwitterUserRow(AnyRow):
    checkbox_border = 3
    min_row_height = 26
    image_offset = (6, 0)

    def __init__(self, *a, **k):
        AnyRow.__init__(self, *a, **k)

    def PopulateControls(self, user):
        self.checkbox.Value = getattr(user, 'selected', False)
        self.text = user.screen_name
        self.profile_image_url = twitter_util.twitter_mini_img_url(user.profile_image_url) if user.profile_image_url else None

    @property
    def image(self):
        return None

    def PaintMore(self, dc):
        r = self.ClientRect

        ICON_SIZE = 24
        padding = 1
        x = r.Right - ICON_SIZE - padding
        y = r.Top + padding

        icon = self.Parent.get_image(self)
        if icon is None:

            try:
                icon = self.Parent._noicon
            except AttributeError:
                icon = self.Parent._noicon = get_twitter_noicon().Resized(ICON_SIZE)

        if icon:
            dc.DrawBitmap(icon, x, y, True)

    def on_right_up(self, *a, **k): pass

def get_twitter_noicon():
    from twitter import RES_PATH
    return wx.Bitmap(RES_PATH / 'img' / 'twitter_no_icon.png')

def header(parent, txt):
    ctrl = wx.StaticText(parent, -1, txt)
    ctrl.SetBold()
    return ctrl

def count_twitter_characters(unistr):
    '''
    returns what twitter considers the "character count" of the specified
    unicode string.

    see http://dev.twitter.com/pages/counting_characters for details--but the
    short version is that twitter counts the number of code points in an NFC
    normalized version of the string.
    '''

    assert isinstance(unistr, unicode)
    return len(unicodedata.normalize('NFC', unistr))

def textctrl_limit_func(val):
    '''
    used by VisualCharacterLimit to highlight text red if it's over the character limit.
    returns the count limit of characters
    '''
    l = TWITTER_MAX_CHARCOUNT

    try:
        # if the text starts with "d username " then the text can be longer.
        match = twitter_util.direct_msg.match(val)
        if match:
            grp = match.groups()[0] # the username
            l += len(grp)
            l += 3 # for "d<space>[username]<space>" -- the d and two spaces
    except Exception:
        import traceback
        traceback.print_exc_once()

    return l


from gui.uberwidgets.formattedinput2.toolbar import SkinnedToolBar

class TwitterInputToolBar(SkinnedToolBar):
    def __init__(self, *a, **k):
        self.count = ''
        SkinnedToolBar.__init__(self, *a, **k)
        self.construct()
        #self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.Top.Bind(wx.EVT_MENU, self.on_hide, id=ID_HIDE_INPUT_BAR)

        self.count = str(TWITTER_MAX_CHARCOUNT)

    def on_hide(self, e):
        e.Skip()
        self.Show(False)
        self.Parent.Layout()

    def on_context_menu(self, e):
        try: menu = self._context_menu
        except AttributeError:
            menu = self._context_menu = UMenu(self)
            menu.AddItem(_('&Hide Toolbar'), id=ID_HIDE_INPUT_BAR)
        menu.PopupMenu()

    def construct(self):
        buttons = []

        action_buttons = [(_('Shorten &Links'),   ID_SHORTEN_LINKS,   'link'),
                          (_('Image'),  ID_IMAGE,  'image'),
                          (_('Shrink'), ID_SHRINK, 'shrink'),
                          (_('Global Status'), ID_GLOBAL_STATUS, 'global')]

        for label, id, icon in action_buttons:
            button = UberButton(self, id, label,
                icon=skin.get('twitter.toolbaricons.' + icon))
            setattr(self, icon + '_button', button)
            buttons.append(button)

        self.AddMany(buttons)

    def construct_progress_bar(self):
        bar = self.progress_bar = wx.Gauge(self, style = wx.GA_SMOOTH)
        self.Add(bar, expand=True)
        self.content.Layout()
        return bar

    def destroy_progress_bar(self):
        self.Detach(self.progress_bar)
        self.progress_bar.Destroy()
        self.Refresh()

    def LinkTextControl(self, text_ctrl):
        # update the character count and text color when text changes
        self._text_ctrl = text_ctrl
        text_ctrl.Bind(wx.EVT_TEXT, self._on_input_text)

    def CountRect(self, dc = None):
        dc = dc if dc is not None else wx.MemoryDC()
        w, h = dc.GetTextExtent(self.count)
        crect = self.ClientRect
        xpad = 3
        return wx.Rect(crect.Right - w - xpad, crect.VCenterH(h), w + xpad, h)

    def DoUpdateSkin(self, skinobj):
        super(TwitterInputToolBar, self).DoUpdateSkin(skinobj)

        # grab the color to draw the character counter with--we use
        # the bottom bar button normal color
        toolbar_skin = skin.get(self.skinTTB.localitems['toolbarskin'] or '', {})
        button_skin_name = toolbar_skin.get('buttonskin', '')
        button_skin = skin.get(button_skin_name, {})
        font_colors = button_skin.get('fontcolors', {})
        self.text_color = font_colors.get('normal', wx.BLACK)

    def OnPaintMore(self, dc):
        # paint the character count
        if self.count:
            r = self.CountRect(dc)
            dc.Font = self.Font
            dc.TextForeground = self.text_color
            dc.DrawText(self.count, r.x, r.y)

def toolbaricon(name):
    return skin.get('twitter.toolbaricons.' + name)

def feed_label(feed):
    if feed.get('noCount', False):
        count = 0
    else:
        count = max(0, int(feed.get('count', 0)))

    count_string = (' (%s)' % count) if count else ''
    return feed['label'] + count_string

class TwitterActionsBar(UberBar):
    def __init__(self, parent, twitter_panel):
        self.twitter_panel = twitter_panel
        UberBar.__init__(self, parent, skinkey = skin.get('ActionsBar.ToolBarSkin', None), overflowmode=True)
        self.construct()

    def UpdateSkin(self):
        self.SetSkinKey(skin.get('ActionsBar.ToolBarSkin', None))
        UberBar.UpdateSkin(self)

    def update_unread_counts(self, counts):
        for feed in counts:
            label = feed_label(feed)
            feed = self.twitter_panel.protocol.feeds_by_name.get(feed['name'], None)
            if feed is not None:
                id = self.twitter_panel.ids[feed['name']]
                self.UpdateItemLabel(id, label)

        self.OnUBSize()
        wx.CallAfter(self.Parent.Layout)

    def construct(self):
        def menu_item(name):
            id, label = dict(favorites = (ID_FAVORITES, _('Favorites')),
                             history   = (ID_HISTORY,   _('History')))[name]
            return ([toolbaricon(name), label], id)

        overflow_items = [
            menu_item('favorites'),
            menu_item('history'),
            ('', -1), # separator
            ([toolbaricon('group'),     _('New Group...')], ID_NEWGROUP),
            ([toolbaricon('search'),    _('New Search...')], ID_NEWSEARCH),
            (_('Edit and Rearrange...'), ID_EDITANDREARRANGE),
        ]

        for content, id in overflow_items:
            self.AddMenuItem(SimpleMenuItem(content, id=id))

class HoverFrame(wx.Frame):
    def __init__(self, parent, label):
        wx.Frame.__init__(self, parent, style = wx.FRAME_SHAPED | wx.NO_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR)
        self.label = label
        #self.icon = icon
        self.border = wx.Point(1, 1)

        parent.Top.Bind(wx.EVT_MOVE, self.OnParentMove)
        self.Bind(wx.EVT_SHOW, self.OnShow)

        dc = wx.ClientDC(self)
        dc.Font=self.Font

        w, h = dc.GetTextExtent(label)
        self.SetSize((w + self.border.x*2, h + self.border.y*2))

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnShow(self, e):
        e.Skip()
        if e.GetShow():
            self.offset = self.Position - self.Parent.ScreenRect.Position

    def OnParentMove(self, e):
        e.Skip()
        if self.IsShown():
            self.SetPosition(self.Parent.ScreenRect.Position + self.offset)

    def OnPaint(self, e):
        r = self.ClientRect
        dc = wx.PaintDC(self)

        # draw a border
        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.Pen(wx.Color(200, 200, 200))
        dc.DrawRectangleRect(r)

        dc.Font = self.Font
        dc.TextForeground = wx.Color(128, 128, 128)
        dc.DrawText(self.label, self.border.x, self.border.y)
        # draw the icon
        #dc.DrawBitmap(self.icon, self.border.x, self.border.y, True)

class URLShortenerPopup(object):
    def __init__(self, textctrl):
        self.textctrl = textctrl

        textctrl.Bind(wx.EVT_TEXT, self.__OnText)
        textctrl.Bind(wx.EVT_KEY_DOWN, self.__OnKeyDown)

        self.last_value = None
        textctrl.Bind(wx.EVT_MOTION, self.__OnMotion)
        textctrl.Bind(wx.EVT_LEAVE_WINDOW, self.__OnLeave)

        WM_PASTE = 0x302
        textctrl.BindWin32(WM_PASTE, self.__OnPaste)

        self.hover_icon = None

    def __OnLeave(self, e):
        win = wx.FindWindowAtPointer()
        if win is None or win.Parent is not self.textctrl:
            self.ShowShortenerPopup(False)

    def __OnMotion(self, e):
        e.Skip()
        txt = self.textctrl
        val = txt.Value
        if val != self.last_value:
            self.last_value = val

            from util.net import LinkAccumulator
            self.links = LinkAccumulator(val)

        p = txt.XYToPosition(*txt.HitTest(e.Position)[1:])
        if p != -1:
            for n, (i, j) in enumerate(self.links.spans):
                if p >= i and p < j:
                    pos = txt.ClientToScreen(txt.IndexToCoords(i))
                    self.ShowShortenerPopup(True, pos)

    def __OnPaste(self, hWnd, msg, wParam, lParam):
        txt = clipboard.get_text()
        if txt and isurl(txt):
            self.delay_hide = True
            wx.CallAfter(self.ShowShortenerPopup, True)
            wx.CallAfter(lambda: setattr(self, 'delay_hide', False))

    def ShowShortenerPopup(self, show, pos=None):
        if show and self.hover_icon is None:
            self.hover_icon = HoverIcon(self.textctrl, skin.get('twitter.toolbaricons.shrink'))
            if pos is None:
                pos = self.textctrl.ScreenRect.BottomLeft + self.textctrl.IndexToCoords(self.textctrl.InsertionPoint)
            self.hover_icon.SetPosition(pos)
            fx.fadein(self.hover_icon, speed='fast')
        elif not show and self.ShortenerPopupIsShown():
            icon, self.hover_icon = self.hover_icon, None
            fx.fadeout(icon, speed='fast')

    def ShortenerPopupIsShown(self):
        return self.hover_icon is not None and self.hover_icon.IsShown()

    def __OnText(self, e):
        e.Skip()
        if self.ShortenerPopupIsShown() and not getattr(self, 'delay_hide', False):
            self.ShowShortenerPopup(False)

    def __OnKeyDown(self, e):
        e.Skip()

        if self.hover_icon is None or not self.hover_icon.IsShown():
            return

        if e.KeyCode not in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            return

        e.Skip(False)


from peak.util.addons import AddOn

def twitter_autocomplete(textctrl):
    TwitterAutoCompleter(textctrl).bind()

class TwitterAutoCompleter(AddOn):
    def __init__(self, subject):
        self.textctrl = subject
        super(TwitterAutoCompleter, self).__init__(subject)

    def bind(self):
        if getattr(self, 'bound', False):
            import warnings
            warnings.warn('attempted to re-bind events on %r' % self.textctrl)
            return
        self.bound = True
        self.textctrl.Bind(wx.EVT_TEXT, self.__OnText)
        self._autocomplete_timer = wx.PyTimer(self.on_autocomplete_users)
        self._autocomplete_enabled = True
        self.accts = None

    initial_show_delay_ms = 500

    def on_autocomplete_users(self):
        def callback(users):
            users = sorted(users.values(), key=lambda user: user['screen_name'].lower())
            controller = TwitterAutoCompleteController(users)
            results = [TwitterSearchResult(u) for u in users]

            from gui.autocomplete import autocomplete
            autocomplete(self.textctrl, results, controller)

        import twitter
        twitter.get_users(callback, self.accts)

    def delayed_show(self):
        self._autocomplete_timer.StartOneShot(self.initial_show_delay_ms)

    def immediate_show(self):
        self._autocomplete_timer.Stop()
        self.on_autocomplete_users()

    def __OnText(self, e):
        e.Skip()
        if not self._autocomplete_enabled:
            return

        ip = self.textctrl.InsertionPoint
        val = self.textctrl.Value
        if (ip > 0 and val[ip - 1] == '@' and \
            (ip == 1 or val[ip - 2] in (' ', '.', ','))) \
            or (ip == 2 and val[:2] == 'd '):
                self.delayed_show()
        elif ip > 1 and val[ip-2] == '@' and at_someone.match(val[ip-2:ip]):
            self.immediate_show()
        elif ip == 3 and val[:2] == 'd ' and direct.match(val[:ip]):
            self.immediate_show()

class TwitterInputBoxBase(FormattedExpandoTextCtrl, SplitterEventMixin):
    def __init__(self, *a, **k):
        self.tc = self
        FormattedExpandoTextCtrl.__init__(self, *a, **k)
        SplitterEventMixin.__init__(self)

class TwitterInputBox(TwitterInputBoxBase):
    def CanPaste(self): return True

    def __init__(self, *a, **k):
        super(TwitterInputBox, self).__init__(*a, **k)

        textattr = StyleFromPref('messaging.default_style')
        textattr.TextColour = wx.BLACK
        textattr.BackgroundColour = wx.WHITE
        self.SetFormat_Single(textattr)

        from gui.toolbox import add_shortened_url_tooltips
        add_shortened_url_tooltips(self)

        for regex in twitter_util.spellcheck_regex_ignores:
            self.AddRegexIgnore(regex)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

    @property
    def BestSizeControl(self):
        return self.Parent

    def OnContextMenu(self, e):
        with UMenu.Reuse(self, event=e) as menu:
            self.AddSuggestionsToMenu(menu)

            from gui.toolbox import add_rtl_checkbox, maybe_add_shorten_link
            maybe_add_shorten_link(self, menu)

            std_textctrl_menu(self, menu)
            add_rtl_checkbox(self, menu)

    def OnExpandEvent(self, event):
        event.Skip()
        height = self.MinSize.height
        min_size = wx.Size(-1, height)
        self.MinSize = min_size

class TwitterPanel(object):
    def __init__(self, parent, protocol):
        self.ids = {'favorites': ID_FAVORITES, 'history': ID_HISTORY}
        self.protocol = protocol

        self.connect_events()

        self.custom_feed_buttons = odict()
        self.construct(parent, protocol)
        self.bind_events()

        self.Control.Top.OnTop = self.AlwaysOnTop

    def _events(self):
        return [('on_unread_counts', self.on_unread_counts),
                ('on_feeds',         self.on_feeds),
                ('on_view',          self.on_view),
                ('on_edit_feed',     self.OnEditFeed)]

    def connect_events(self):
        for event_name, method in self._events():
            event_delegate = getattr(self.protocol.events, event_name)
            event_delegate += method

    def disconnect_events(self):
        for event_name, method in self._events():
            event_delegate = getattr(self.protocol.events, event_name)
            event_delegate -= method

    @property
    def Control(self): return self.splitter

    @property
    def WebView(self): return self.webview

    def bind_events(self):
        bind = self.actions_bar.Bind
        bind(wx.EVT_MENU, self.on_new_group,    id=ID_NEWGROUP)
        bind(wx.EVT_MENU, self.on_new_search,   id=ID_NEWSEARCH)
        bind(wx.EVT_TOGGLEBUTTON, self.on_button) # for view buttons
        bind(wx.EVT_BUTTON, self.on_button)   # for overflow menu items
        bind(wx.EVT_MENU, self.on_button)   # for overflow menu items
        bind(wx.EVT_MENU, self.on_rearrange_feeds,  id=ID_EDITANDREARRANGE)

        # TODO: umenu events go to the top level frame :(
        bind = self.Control.Top.Bind
        bind(wx.EVT_MENU, self.on_delete_feed,  id=ID_DELETE_FEED)
        bind(wx.EVT_MENU, self.on_edit_feed,    id=ID_EDIT_FEED)
        bind(wx.EVT_MENU, self.on_rearrange_feeds,  id=ID_EDITANDREARRANGE)
        bind(wx.EVT_MENU, self.on_mark_feed_as_read,  id=ID_MARKFEEDASREAD)
        bind(wx.EVT_MENU, self.on_toggle_addstocount,  id=ID_TOGGLE_ADDSTOCOUNT)
        bind(wx.EVT_MENU, self.toggle_always_on_top, id=ID_KEEPONTOP)
        bind(wx.EVT_MENU, lambda e: self.webview.Copy(), id=ID_WEBVIEW_COPY)
        bind(wx.EVT_MENU, lambda e: self.webview.IncreaseTextSize(), id=ID_INCREASE_TEXT_SIZE)
        bind(wx.EVT_MENU, lambda e: self.webview.DecreaseTextSize(), id=ID_DECREASE_TEXT_SIZE)
        bind(wx.EVT_MENU, lambda e: self.webview.ResetTextSize(), id=ID_RESET_TEXT_SIZE)
        bind(wx.EVT_MENU, lambda e: self.protocol.update(), id=ID_UPDATE)

        bind = self.Control.Top.Bind
        bind(wx.EVT_MENU, self.on_shorten_links, id=ID_SHORTEN_LINKS)
        bind(wx.EVT_MENU, self.on_shrink,     id=ID_SHRINK)
        bind(wx.EVT_MENU, self.on_global_status, id=ID_GLOBAL_STATUS)
        bind(wx.EVT_MENU, self.on_image,      id=ID_IMAGE)

        from gui.toolbox import bind_special_paste

        hover = HoverFrame(self.input_area, _('Shortening...'))

        def onshorten(cancel):
            hover.SetPosition(self.CursorScreenPosition)
            hover.ShowNoActivate(True)

            def _on_cancel():
                hover.Hide()
                cancel()
                self.cancel_mode(False)

            return self.cancel_mode(_on_cancel)

        def onshorten_done(url):
            hover.Hide()
            self.cancel_mode(False)

        bind_special_paste(self.input_area,
                           shorten_urls=lambda: pref('twitter.paste.shorten_urls', default=True),
                           onbitmap   = self.upload_image,
                           onfilename = self.upload_image,
                           onshorten = onshorten,
                           onshorten_done = onshorten_done)

        ## this function doesn't get called. wtf? i dont understand dnd
#        def emit_paste_event(_):
#            log.info("dropped some junk: %r", _)
#
#        self.input_area.SetDropTarget(gui.toolbox.dnd.SimpleDropTarget
#                                      (files  = emit_paste_event,
#                                       bitmap = emit_paste_event,
#                                       text   = emit_paste_event,
#                                       ))

    def activate_feed_button(self, feed_id):
        button = self.actions_bar.FindWindowById(feed_id)
        if hasattr(button, 'Active'):
            button.Active(True)

        # untoggle other feed buttons
        for feed_name, id in self.ids.iteritems():
            if id != feed_id:
                button = self.actions_bar.FindWindowById(id)
                if hasattr(button, 'Active'):
                    button.Active(False)

    def on_button(self, e):
        feed = self.feed_for_id(e.Id)
        if feed is not None:
            self.switch_to_feed(feed)
        else:
            e.Skip()

    def switch_to_feed(self, feed):
        self.activate_feed_button(self.ids[feed['name']])

        # CallAfter(1) so that the button redraws before the webview switch
        wx.CallLater(1, lambda: self.webview.switch_to_view(feed['name']))

    def on_image(self, e=None):
        '''uploads an image to pic.im, inserting the shortened url into the input
        area when finished'''

        # select a file
        filename = pick_image_file(self.Control.Top)
        if filename is None: return

        self.upload_image(filename, auto = False)

    def cancel_mode(self, callback):
        if not callback:
            self.cancel_button.Hide()
            changed = self.input_button.Show()
            self.cancel_callback = None
        else:
            changed = self.cancel_button.Show()
            self.input_button.Hide()
            self.cancel_callback = callback

        if changed:
            self.bottom_pane.Sizer.Layout()

    def on_cancel(self, *a, **k):
        if getattr(self, 'cancel_callback', None) is not None:
            self.cancel_callback()

    @property
    def CursorScreenPosition(self):
        i = self.input_area
        return i.ClientToScreen(i.IndexToCoords(i.InsertionPoint))

    def upload_image(self, filename, bitmap=None, auto = True):
        if auto and not pref('twitter.paste.upload_images', True):
            return

        if auto:
            message = _(u"Are you sure you want to upload the image in your clipboard?")
            title = _(u"Image Upload")
            if bitmap is None:
                bitmap = wx.Bitmap(filename)
            from gui.imagedialog import show_image_dialog
            if not show_image_dialog(self.Control, message, bitmap, title=title):
                return

        mtype, _encoding = mimetypes.guess_type(filename)
        if mtype is None or not mtype.startswith('image'):
            # Not an image file
            return

        hover = HoverFrame(self.input_area, 'Uploading...')

        def disable():
            self.input_area.Disable()
            hover.SetPosition(self.CursorScreenPosition)
            hover.ShowNoActivate(True)

        def enable():
            self.input_area.Enable()
            if not wx.IsDestroyed(hover):
                hover.Destroy()

        # TODO: timeout needed here.
        # setup callbacks
        def progress(value):
            pass
            #wx.CallAfter(bar.SetValue, value)

        def cancel():
            cancel._called = True
            self.cancel_mode(False)
            enable()

        def done():
            if not getattr(done, '_called', False):
                #self.input_toolbar.destroy_progress_bar()
                done._called = True
                self.cancel_mode(False)
                enable()

        def success(resp):
            @wx.CallAfter
            def after():
                done()
                if not getattr(cancel, '_called', False):
                    insert_text(self.input_area, resp['url'])
                    self.input_area.SetFocus()

        def error(e):
            wx.CallAfter(done)

        disable()
        self.cancel_mode(cancel)

        # start transfer
        try:
            from imagehost.imgur import ImgurApi
            #bar.SetRange(os.path.getsize(filename))
            stream = CallbackStream(open(filename, 'rb'), progress, lambda: None)
            ImgurApi().upload(stream, success = success, error = error)
        except Exception as e:
            print_exc()
            error(e)

    def on_shrink(self, e=None):
        inp = self.input_area
        val = inp.Value
        if not val: return

        def success(shrunk_text):
            @wx.CallAfter
            def after():
                # don't change the value if the user has changed the text field
                # in the meantime
                if not wx.IsDestroyed(inp) and val == inp.Value:
                    inp.Value = shrunk_text
                    inp.SetInsertionPointEnd()
                    inp.SetFocus()

        def error(e):
            log.error('error shrinking tweet: %r', e)

        # todo: timeout
        threaded(twitter_util.shrink_tweet)(val, success=success, error=error)

    def on_global_status(self, e=None):
        wx.GetApp().SetStatusPrompt(initial_text=self.input_area.Value)
        self.input_area.Clear()

    def on_shorten_links(self, e=None):
        '''shortens all links in the input area'''

        from gui.textutil import shorten_all_links
        shorten_all_links(self.input_area, ondone=self.input_area.SetFocus)

    def on_new_group(self, e):
        self.new_or_edit_group()

    def new_or_edit_group(self, feed=None):
        if feed is None:
            new = True
            feed = dict(ids=[], filter=True, popups=False)
        else:
            new = False

        ids = set(str(i) for i in feed.get('ids'))

        @self.get_users
        def success(users):
            users = sorted((TwitterUser(id=u['id'],
                                        screen_name=u['screen_name'],
                                        profile_image_url=u['profile_image_url'],
                                        selected=str(u['id']) in ids)
                            for u in users.itervalues()),
                            key=lambda u: u.screen_name.lower())

            opts = feed.copy()
            opts['users'] = users

            cb = getattr(self.protocol, 'add_feed' if new else 'edit_feed')
            self._show_dialog_with_opts(TwitterGroupDialog, opts, cb)

    def on_new_search(self, e):
        self.new_or_edit_search()

    def new_or_edit_search(self, feed=None):
        if feed is not None:
            new = False
            from pprint import pprint; pprint(feed)
        else:
            new = True
            feed = dict(merge=False, popups=True)

        opts = dict(query = feed.get('query', ''))

        if new:
            if self.protocol.trends:
                opts.update(trends=self.protocol.trends)
        else:
            from .twitter import title_from_query
            title = feed.get('title', None)
            if title is None:
                title = title_from_query(feed.get('query', ''))
            search_opts = dict(merge=feed.get('merge', False), popups=feed.get('popups'))
            opts.update(name = feed.get('name', ''),
                        search_opts = search_opts,
                        title = title)

        cb = getattr(self.protocol, 'add_feed' if new else 'edit_feed')
        self._show_dialog_with_opts(TwitterSearchDialog, opts, cb)

    def OnEditFeed(self, feed):
        print 'OnEditFeed'
        from pprint import pprint; pprint(feed)

        dict(group=self.new_or_edit_group,
             search=self.new_or_edit_search)[feed['type']](feed)

    def OnRemoveFeed(self, feed):
        self.protocol.delete_feed(feed['name'])

    def get_users(self, callback):
        if hasattr(self, '_cached_users'):
            callback(self._cached_users)
            return

        def cb(users):
            self._cached_users = users
            callback(users)

        self.protocol.get_users(cb)

    def on_delete_feed(self, e):
        feed = self.feed_for_id(self._feed_menu_target.Id)
        if feed is not None:
            self.protocol.delete_feed(feed['name'])

    def on_edit_feed(self, e):
        feed = self.feed_for_id(self._feed_menu_target.Id)
        if feed is not None:
            self.OnEditFeed(feed)

    @property
    def ExistingFeedEditor(self):
        return find_tlw(TwitterFeedsEditDialog, lambda w: w.protocol is self.protocol)

    def on_rearrange_feeds(self, e):
        dialog = self.ExistingFeedEditor
        if dialog is not None:
            return dialog.Raise()

        protocol = self.protocol
        dialog = TwitterFeedsEditDialog(self.Control,
                                        protocol,
                                        protocol.feeds,
                                        protocol.set_feeds)

        dialog.on_edit_feed += self.OnEditFeed
        dialog.on_remove_feed += self.OnRemoveFeed

        dialog.CenterOnParent()
        dialog.Show()

    def on_mark_feed_as_read(self, e):
        feed = self.feed_for_id(self._feed_menu_target.Id)
        if feed is not None:
            self.protocol.mark_feed_as_read(feed['name'])

    def on_toggle_addstocount(self, e):
        feed = self.feed_for_id(self._feed_menu_target.Id)
        if feed is not None:
            self.protocol.toggle_addstocount(feed['name'])

    def _show_dialog_with_opts(self, dialog_cls, opts, info_cb=None):
        if not wx.IsMainThread():
            return wx.CallAfter(self._show_dialog_with_opts, dialog_cls, opts)

        if not dialog_cls.RaiseExisting():
            diag = dialog_cls(self.Control.Top, opts)
            if info_cb is not None:
                diag.on_info = info_cb
            diag.CenterOnParent()
            diag.Show()

    def on_unread_counts(self, opts):
        counts = opts.get('feeds')
        self.counts = counts

        count_timer = getattr(self, '_count_timer', None)
        if count_timer is None:
            def update():
                self.actions_bar.update_unread_counts(self.counts)
            self._count_timer = count_timer = wx.PyTimer(update)
        if not count_timer.IsRunning():
            count_timer.StartOneShot(10)

    def feed_for_id(self, id):
        for feed_name, feed_id in self.ids.iteritems():
            if feed_id == id:
                try:
                    return self.protocol.feeds_by_name[feed_name]
                except KeyError:
                    from pprint import pprint; pprint(self.protocol.feeds_by_name)
                    raise

    def id_for_feed(self, feed):
        if not isinstance(feed, basestring):
            feed = feed['name']

        try:
            id = self.ids[feed]
        except KeyError:
            id = self.ids[feed] = wx.NewId()

        return id

    def construct_feed_button(self, feed):
        id = self.id_for_feed(feed)

        icon = skin.get('twitter.toolbaricons.' + feed['type'])
        button = UberButton(self.actions_bar, id, feed_label(feed),
                            icon=icon, type='toggle')
        button.Bind(wx.EVT_CONTEXT_MENU, self.on_feed_button_menu)
        return button

    def on_feed_button_menu(self, e):
        self._feed_menu_target = e.EventObject

        try:
            menu = self._feed_button_menu
        except AttributeError, e:
            menu = UMenu(self.Control)

        menu.RemoveAllItems()

        feed = self.feed_for_id(self._feed_menu_target.Id)
        if feed['name'] not in permanent_feed_types:
            menu.AddItem(_('&Edit'),   id=ID_EDIT_FEED)
            menu.AddItem(_('&Delete'), id=ID_DELETE_FEED)
            menu.AddSep()
            menu.AddItem(_('&Rearrange'), id=ID_EDITANDREARRANGE)
        else:
            menu.AddItem(_('Edit and &Rearrange'), id=ID_EDITANDREARRANGE)

        menu.AddSep()
        menu.AddItem(_('&Mark As Read'), id=ID_MARKFEEDASREAD)

        if feed.get('type', None) in ('group', 'search'):
            item = menu.AddCheckItem(_('&Adds to Unread Count'), id=ID_TOGGLE_ADDSTOCOUNT)
            item.Check(not feed.get('noCount', False))

        menu.PopupMenu()

    def select_view(self, n):
        '''select the nth view'''

        try:
            button = self.custom_feed_buttons.values()[n]
        except IndexError:
            pass
        else:
            self.switch_to_feed(self.feed_for_id(button.Id))

    def page_view(self, delta):
        '''
        switches feeds forward or backward based on the visual order of buttons
        '''
        keys = self.custom_feed_buttons.keys()
        if not keys: return

        # find index of active feed button
        index = -1
        for i, k in enumerate(keys):
            if self.custom_feed_buttons[k].IsActive():
                index = i
                break

        # go to next or previous button
        if delta < 0 and index == -1:
            newkey = keys[len(keys)-1]
        else:
            index += delta
            newkey = keys[index % len(keys)]

        self.switch_to_feed(self.feed_for_id(self.custom_feed_buttons[newkey].Id))

    def on_view(self, view=None):
        if view is None:
            view = getattr(self, '_view', None)
            if view is None:
                return

        self._view = view

        log.warning('on_view %r', view)
        feed = self.protocol.feeds_by_name.get(view, None)
        if feed is not None:
            self.active_view = view
            self.activate_feed_button(self.id_for_feed(feed))
            title = u'%s - %s' % (self.protocol.username, feed['label'])
            self.Control.Top.Title = title
        else:
            self.activate_feed_button(0)

        self.actions_bar.OnUBSize()

    def on_feeds(self, feeds):
        log.info('on_feeds: %r', feeds)
        self.counts = feeds
        # TODO: remove old ids

        # Send new feeds to the edit/rearrange dialog, if it exists.
        editor = self.ExistingFeedEditor
        if editor is not None:
            editor.SetList(feeds)
            editor.Fit()

        bar = self.actions_bar
        with self.Control.Frozen():
            active_name = None
            for name, button in self.custom_feed_buttons.items():
                if button.IsActive():
                    active_name = name
                bar.Remove(button, calcSize=False)
                button.Destroy()

            self.custom_feed_buttons.clear()

            for feed in feeds:
                name = feed['name']
                if feed['type'] in ('search', 'user') and not feed.get('save', False):
                    continue # don't show buttons for unsaved search feeds
                button = self.construct_feed_button(feed)
                self.custom_feed_buttons[name] = button
                if active_name is not None and name == active_name:
                    button.Active(True)
                bar.Add(button, calcSize=False)

        bar.OnUBSize()
        wx.CallAfter(bar.Parent.Layout)
        self.on_view()

    def on_webview_menu(self, e):
        w = self.webview
        try:
            menu = self._menu
        except AttributeError:
            menu = self._menu = UMenu(self.webview)

        menu.RemoveAllItems()
        if self.webview.CanCopy():
            item = menu.AddItem(_('Copy'), id=ID_WEBVIEW_COPY)
            menu.AddSep()

        menu.AddItem(_('&Update Now'), id=ID_UPDATE)

        menu.AddSep()
        item = menu.AddCheckItem(KEEP_ON_TOP_LABEL, id=ID_KEEPONTOP)
        item.Check(self.AlwaysOnTop)

        # text size submenu
        textsizemenu = UMenu(self.webview)
        textsizemenu.AddItem(_('&Increase Text Size\tCtrl+='), id=ID_INCREASE_TEXT_SIZE)
        textsizemenu.AddItem(_('&Decrease Text Size\tCtrl+-'), id=ID_DECREASE_TEXT_SIZE)
        textsizemenu.AddSep()
        textsizemenu.AddItem(_('&Reset Text Size\tCtrl+0'), id=ID_RESET_TEXT_SIZE)
        menu.AddSubMenu(textsizemenu, _('Text Size'))

        menu.PopupMenu()

    @property
    def AlwaysOnTopKey(self):
        return self.protocol.account_pref_key('always_on_top')

    @property
    def AlwaysOnTop(self):
        return pref(self.AlwaysOnTopKey, default=False)

    def toggle_always_on_top(self, e=None):
        newval = not self.AlwaysOnTop
        setpref(self.AlwaysOnTopKey, newval)
        self.Control.Top.OnTop = newval

    def construct(self, parent, protocol):
        from gui.uberwidgets.skinsplitter import SkinSplitter

        self.splitter = spl = SkinSplitter(parent, wx.SP_NOBORDER | wx.SP_LIVE_UPDATE)
        spl.SetMinimumPaneSize(10)
        spl.SetSashGravity(1)

        self.top_pane = wx.Panel(spl)
        self.top_pane.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.bottom_pane = wx.Panel(spl)
        self.bottom_pane.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.actions_bar = TwitterActionsBar(self.top_pane, self)

        self.webview = TwitterWebView(self.top_pane, protocol)
        self.webview.Bind(wx.EVT_CONTEXT_MENU, self.on_webview_menu)
        #self.input_toolbar = TwitterInputToolBar(self.bottom_pane, indirect_skinkey = 'FormattingBar')

        self.input_area = TwitterInputBox(self.bottom_pane,
                multiFormat = False)
                #fbar = self.input_toolbar)

        import hooks
        hooks.notify('digsby.status_textctrl.created', self.input_area)

        from gui.textutil import VisualCharacterLimit
        VisualCharacterLimit(self.input_area, textctrl_limit_func, count_twitter_characters)

        self.setup_focus()

        self.input_area.Bind(wx.EVT_KEY_DOWN, self.__onkey)
        self.webview.BindWheel(self.input_area)
        self.webview.BindWheel(self.webview)
        self.webview.BindScrollWin(self.input_area)
        self.webview.BindScrollWin(self.webview)
        self.input_area.BindSplitter(spl, protocol.account_pref_key('input_ctrl_height'))
        self.input_area.Bind(wx.EVT_TEXT, self._on_input_text)

        #self.input_toolbar.LinkTextControl(self.input_area)

        self.top_pane.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.top_pane.Sizer.AddMany([
            (self.actions_bar, 0, wx.EXPAND),
            (self.webview, 1, wx.EXPAND),
        ])

        self.construct_input_button()

        self.bottom_pane.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.spacer_panel = SpacerPanel(self.bottom_pane, skinkey = 'inputspacer')

        self.bottom_pane.Sizer.AddMany([
            #(self.input_toolbar, 0, wx.EXPAND),
            (self.input_area, 1, wx.EXPAND),
            (self.spacer_panel, 0, wx.EXPAND),
            (self.input_button, 0, wx.EXPAND),
            (self.cancel_button, 0, wx.EXPAND),
        ])

        spl.SplitHorizontally(self.top_pane, self.bottom_pane)
        spl.SetSashPosition(2400)

    def construct_input_button(self):
        def onshow(menu):
            ontop_item.Check(self.AlwaysOnTop)

        m = UMenu(self.bottom_pane, onshow = onshow)

        def g(skinkey):
            return skin.get('twitter.toolbaricons.' + skinkey)

        m.AddItem(_('Shorten URLs\tCtrl+L'), id=ID_SHORTEN_LINKS, bitmap=g('link'))
        m.AddItem(_('Share Picture\tCtrl+P'), id=ID_IMAGE, bitmap=g('image'))
        m.AddItem(_('TweetShrink\tCtrl+S'), id=ID_SHRINK, bitmap=g('shrink'))
        m.AddSep()
        m.AddItem(_('Set Global Status\tCtrl+G'), id=ID_GLOBAL_STATUS, bitmap=g('global'))
        m.AddSep()
        m.AddPrefCheck('twitter.paste.shorten_urls',  _('Auto Shorten Pasted URLs'))
        m.AddPrefCheck('twitter.paste.upload_images', _('Auto Upload Pasted Images'))
        m.AddPrefCheck('twitter.autoscroll.when_at_bottom', _('Auto Scroll When At Bottom'))
        m.AddSep()
        ontop_item = m.AddCheckItem(KEEP_ON_TOP_LABEL, id=ID_KEEPONTOP)

        self.input_button = UberButton(self.bottom_pane,
                                       skin='InputButton',
                                       label=str(TWITTER_MAX_CHARCOUNT),
                                       menu=m,
                                       type='menu')

        self.cancel_button = UberButton(self.bottom_pane,
                                        skin='InputButton',
                                        label=_('Cancel'),
                                        onclick = self.on_cancel)
        self.cancel_button.Hide()

    def setup_focus(self):
        # HACK: uberbuttons steal focus from us, get it back every 500 ms
        def on_focus_timer():
            if wx.IsDestroyed(self.Control):
                self.focus_timer.Stop()
                return

            w = wx.Window.FindFocus()
            if w is not None and w.Top is self.Control.Top and w is not self.input_area:
                s = wx.GetMouseState()
                if not (s.LeftDown() or s.MiddleDown() or s.RightDown()):
                    self.input_area.SetFocus()

        self.focus_timer = wx.PyTimer(on_focus_timer)
        self.focus_timer.StartRepeating(500)

        # clicking the webview focuses the input box
        self.webview.Bind(wx.EVT_SET_FOCUS, lambda e: (e.Skip(), self.input_area.SetFocus()))

    def __onkey(self, e):
        e.Skip(False)

        key, mod = e.KeyCode, e.Modifiers
        webview = self.webview

        # catch ctrl+tab and shift+ctrl+tab
        if key == wx.WXK_TAB and mod == wx.MOD_CMD:
            self.page_view(1)
        elif key == wx.WXK_TAB and mod == wx.MOD_CMD | wx.MOD_SHIFT:
            self.page_view(-1)

        # ctrl+1-9 select buttons
        elif mod == wx.MOD_CMD and key >= ord('1') and e.KeyCode <= ord('9'):
            self.select_view(key - ord('1'))

        # up and down scroll the webview when there's only one line
        elif key in (wx.WXK_UP, wx.WXK_DOWN) and self.input_area.GetNumberOfLines() == 1:
            webview.ScrollLines(-1 if wx.WXK_UP == key else 1)

        # page up/down always go to the webview
        elif key == wx.WXK_PAGEUP:
            webview.ScrollLines(-3)
        elif key == wx.WXK_PAGEDOWN:
            webview.ScrollLines(3)

        # Catch enter on the input box and send a tweet
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not mod & wx.MOD_SHIFT:
            self.send_tweet()

        # escape and ctrl+w closes window
        elif (key == wx.WXK_ESCAPE and mod == 0) or \
             (key == ord('W') and mod == wx.MOD_CMD):
            self.Control.Top.Close()

        elif mod == wx.MOD_CMD and key == ord('L'):
            self.on_shorten_links()

        elif mod == wx.MOD_CMD and key == ord('P'):
            self.on_image()

        elif mod == wx.MOD_CMD and key == ord('S'):
            self.on_shrink()

        elif mod == wx.MOD_CMD and key == ord('G'):
            self.on_global_status()

        elif mod == wx.MOD_CMD and key == ord('C'):
            if webview.CanCopy():
                webview.Copy()
            elif self.input_area.CanCopy():
                self.input_area.Copy()
            else:
                e.Skip(True)

        # text size
        elif mod == wx.MOD_CMD and key ==  ord('0'):
            webview.ResetTextSize()
        elif mod == wx.MOD_CMD and key == ord('+'):
            webview.IncreaseTextSize()
        elif mod == wx.MOD_CMD and key == ord('-'):
            webview.DecreaseTextSize()

        else:
            e.Skip(True)

    def send_tweet(self):
        if not self._should_send_tweet():
            return

        inp = self.input_area
        text, reply_id = inp.Value, getattr(inp, 'reply_id', None)
        self.protocol.on_status_with_error_popup(text, reply_id)
        inp.reply_id = None
        inp.Clear()

    def _should_send_tweet(self):
        if not self.input_area.Value.strip():
            return False

        if (pref('twitter.spell_guard', False) and
            pref('messaging.spellcheck.enabled', True) and
            self.input_area.HasSpellingErrors()):

            from gui.toolbox import SimpleMessageDialog

            msg1 = _('Your tweet has spelling errors.')
            msg2 = _("Are you sure you'd like to send it?")
            msg = u'%s\n\n%s' % (msg1, msg2)

            dialog = SimpleMessageDialog(self.top_pane.Top,
                title   = _("Tweet spelling errors"),
                message = msg,
                icon    = wx.ArtProvider.GetBitmap(wx.ART_QUESTION),
                ok_caption = _('Send Anyways'))

            dialog.CenterOnParent()
            res = dialog.ShowModal()

            return res == wx.ID_OK

        return True

    def _on_input_text(self, e):
        e.Skip()
        val = self.input_area.Value

        # try to subtract a "d screen_name" from the count
        count = len(val)
        try:
            match = twitter_util.direct_msg.match(val)
            if match:
                count = len(match.groups()[1])
        except Exception:
            import traceback
            traceback.print_exc_once()

        self.set_charcount(TWITTER_MAX_CHARCOUNT - count)

    def set_charcount(self, count):
        self.count = str(count)
        self.input_button.SetLabel(str(count))


def Active(func):
    @wraps(func)
    def wrapper(*a, **k):
        active = wx.GetActiveWindow()
        if isinstance(active, TwitterFrame):
            return func(active, *a, **k)

    return staticmethod(wrapper)

def _saveinput():
    return pref('twitter.save_input', default=False)

class TwitterFrame(wx.Frame):
    default_size = (400, 700)

    @staticmethod
    def ForProtocol(protocol):
        return find_tlw(TwitterFrame, lambda w: w.panel.protocol is protocol)

    def __init__(self, parent, protocol):
        wx.Frame.__init__(self, parent, wx.ID_ANY, protocol.username, name='Twitter ' + protocol.username)
        self.SetFrameIcon(skin.get('serviceicons.twitter'))
        self.SetMinSize((260, 250))
        self.panel = TwitterPanel(self, protocol)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.panel.Control, 1, wx.EXPAND)
        self.Layout()

        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

        with traceguard:
            from gui.toolbox import persist_window_pos, snap_pref
            persist_window_pos(self, defaultPos  = wx.Point(50, 50), defaultSize = self.default_size)
            snap_pref(self)

        hooks.notify('digsby.statistics.twitter.feed_window.shown')
        self.load_input()
        self.Show()

        # CallAfter here so that the splitter gets the right minsize for the text control
        wx.CallAfter(self.panel.input_area.RequestResize)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, e):
        e.Skip()
        self.Hide()
        self._closing = True
        self.save_input()
        self.panel.disconnect_events()

    def save_input(self):
        if not _saveinput(): return
        self.unfinished_tweet.save(dict(text=self.InputBox.Value,
                                        cursorpos=self.InputBox.InsertionPoint))

    def load_input(self):
        if not _saveinput(): return
        with traceguard:
            info = self.unfinished_tweet.safe_load()
            if info is None: return

            self.InputBox.Value = info['text']
            self.InputBox.InsertionPoint = info['cursorpos']

    @property
    def unfinished_tweet(self):
        try:
            return self._unfinished_tweet
        except AttributeError:
            from util.cacheable import DiskCache
            self._unfinished_tweet = DiskCache('Unfinished Tweet')
            return self._unfinished_tweet

    def OnActivate(self, e):
        e.Skip()
        if getattr(self, '_closing', False) or wx.IsDestroyed(self):
            return

        # wxWebKit's document.onblur/onfocus is broken, so simulate it here
        script = "onFrameActivate(%s);" % ('true' if e.GetActive() else 'false')
        self.RunScript(script);

        if e.GetActive():
            hooks.notify('digsby.statistics.twitter.feed_window.activated')

    def RunScript(self, script):
        return self.panel.webview.RunScript(script)

    @property
    def WebView(self): return self.panel.WebView

    @property
    def InputBox(self):
        return self.panel.input_area

    def SetValueAndReplyId(self, value, reply_id=None, cursor_pos=None):
        inp = self.InputBox
        oldval = inp.Value

        with inp.Frozen():
            inp.Replace(0, inp.LastPosition, value) # preserves undo, unlike SetValue
            inp.reply_id = reply_id

            if cursor_pos:
                inp.SetInsertionPoint(cursor_pos)
            else:
                inp.SetInsertionPointEnd()

            inp.SetFocus()

    @Active
    def Reply(self, id, screen_name, text):
        from .twitter import new_reply_text
        val, cursor = new_reply_text(screen_name, text)
        self.SetValueAndReplyId(val, id, cursor)

    @Active
    def Retweet(self, id, screen_name, text):
        self.SetValueAndReplyId('RT @' + screen_name + ': ' + text.decode('xml'), None)

    @Active
    def Direct(self, screen_name):
        self.SetValueAndReplyId('d ' + screen_name + ' ')

class TwitterWebView(FrozenLoopScrollMixin, ScrollWinMixin, WheelShiftScrollFastMixin, WheelScrollCtrlZoomMixin, wx.webview.WebView):
    '''WebView subclass implementing a CreateWindow function that creates a
    TwitterFrame.'''

    def __init__(self, parent, protocol):
        style = wx.WANTS_CHARS # send arrow keys, enter, etc to the webview
        super(TwitterWebView, self).__init__(parent, wx.ID_ANY, wx.DefaultPosition,
                                    wx.DefaultSize, style)

        self.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.on_before_load)
        self.Bind(wx.webview.EVT_WEBVIEW_NEW_WINDOW, self._on_new_window)
        self.protocol = protocol
        self.SetMouseWheelZooms(True)

    def switch_to_view(self, view):
        log.info('switch_to_view %r on %r', view, self)
        from simplejson import dumps as jsenc
        self.RunScript('''guard(function() {
                            window.opener.account.changeView(%s);
                          });''' % jsenc(view))

    def on_before_load(self, e):
        url = e.URL
        for protocol in ('mailto:', 'http://', 'https://', 'ftp://'):
            if url.lower().startswith(protocol):
                wx.LaunchDefaultBrowser(url)
                e.Cancel()
                return

        e.Skip()

    def _on_new_window(self, e):
        frame = TwitterFrame(self.Parent, self.protocol)
        e.SetWebView(frame.WebView)

    def CreateWindow(self, *a):
        frame = TwitterFrame(self.Parent, self.protocol)
        return frame.WebView

    def _setup_logging(self, log):
        # shorten filenames in twitter webkit log messages by making
        # them relative to this file's directory.
        from path import path
        twitter_root_dir = path(__file__).parent

        from gui.browser.webkit import setup_webview_logging
        setup_webview_logging(self, log, logbasedir=twitter_root_dir)

from gui.visuallisteditor import VisualListEditor, VisualListEditorListWithLinks

class TwitterFeedsEditList(VisualListEditorListWithLinks):
    def __init__(self, *a, **k):
        self.on_edit_feed = Delegate()
        self.on_remove_feed = Delegate()
        self.links = [(_('Edit'), self.on_edit_feed),
                      (_('Remove'), self.on_remove_feed)]

        VisualListEditorListWithLinks.__init__(self, *a, **k)

    def LinksForRow(self, n):
        feed = self.thelist[n]
        return self.links if not is_perm_feed(feed) else []

    def ItemText(self, item):
        return item['label']

    def OnDrawItem(self, dc, rect, n):
        dc.Font = self.Font
        feed = self.thelist[n]
        icon = skin.get('twitter.toolbaricons.' + feed['type'], None)

        x, y = rect.TopLeft + (3, 3)
        if icon: dc.DrawBitmap(icon, x, y, True)

        textrect = wx.Rect(x + 16 + 3, rect.y, rect.Width - x - 38, rect.Height)
        dc.TextForeground = wx.BLACK
        dc.DrawLabel(feed['label'], textrect, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)

        if self.Hovered == n:
            self.PaintLinks(dc, rect, n)

    def CalcMinWidth(self):
        dc = wx.ClientDC(self)
        dc.Font = self.Font
        txtwidth = lambda s: dc.GetTextExtent(s)[0]

        padding_x = 3
        min_width = 0
        for n, item in enumerate(self.thelist):
            w = 30 + padding_x + txtwidth(self.ItemText(item))
            for link_label, _linkfunc in self.LinksForRow(n):
                w += padding_x + txtwidth(link_label)

            min_width = max(w, min_width)

        return max(220, min_width)

class TwitterFeedsEditDialog(VisualListEditor):
    def __init__(self, parent, protocol, feeds, set_feeds):
        self.protocol = protocol
        VisualListEditor.__init__(self, parent, feeds,
            listcallback = set_feeds,
            listclass = TwitterFeedsEditList,
            title = _('Twitter Groups and Searches'))
        self.on_edit_feed = self.vle.on_edit_feed
        self.on_remove_feed = self.vle.on_remove_feed

def find_tlw(cls, func):
    for tlw in wx.GetTopLevelWindows():
        if isinstance(tlw, cls) and func(tlw):
            return tlw

def focus_on_show(ctrl):
    '''Calls SetFocus on ctrl when its top level parent receives EVT_SHOW.'''

    def onshow(e):
        e.Skip()
        ctrl.SetFocus()

    ctrl.Top.Bind(wx.EVT_SHOW, onshow)

from gui.buddylist.accounttray import SocialAccountTrayIcon

USE_WEBPAGE_LINKS = True

def menu_actions(acct, m):

    m.AddItem(_('Refresh Now'), callback = acct.update_now)
    m.AddItem(_('Mark All As Read'), callback = acct.mark_all_as_read)
    m.AddSep()

    if USE_WEBPAGE_LINKS:
        for label, url in acct.header_funcs:
            m.AddItem(label, callback=lambda url=url: wx.LaunchDefaultBrowser(url))
    else:
        # disabled until counts are correct.
        proto = acct.twitter_protocol

        if proto:
            for feed in proto.feeds:
                label = feed['label']
                try:
                    if feed['count']:
                        label += ' (%d)' % max(0, feed['count'])
                except Exception:
                    pass
                def cb(name=feed['name']):
                    proto.on_change_view(name)
                m.AddItem(label, callback=cb)

    m.AddSep()
    m.AddItem(_('&Rename'), callback = acct.rename_gui)
    m.AddSep()
    m.AddItem(_('Set Status'), callback = acct.update_status_window_needed)

class TwitterTrayIcon(SocialAccountTrayIcon):
    def __init__(self, *a, **k):
        SocialAccountTrayIcon.__init__(self, *a, **k)

        # refresh every five minutes so that the icon doesn't become inactive
        if config.platform == 'win':
            self.tray_refresh_timer = wx.PyTimer(self.Refresh)
            self.tray_refresh_timer.StartRepeating(60 * 1000 * 5)

    def update_menu(self, event=None):
        self._menu.RemoveAllItems()
        menu_actions(self.acct, self._menu)

    @property
    def Tooltip(self):
        # twitter doesn't have a count
        return _('Twitter (%s)') % self.acct.name

    def should_show_count(self):
        return pref('trayicons.email.show_count', True) and self.acct.should_show_unread_counts()

def sorted_screen_names(users):
    return sorted((unicode(user['screen_name']) for user in users.itervalues()), key=unicode.lower)


import re
at_someone = re.compile(r'(?<!\w)@((\w+)(/\w+)?)?', re.UNICODE)
direct     = re.compile(r'^d\s+(?:(\S+))?', re.DOTALL)
user_regexes = (at_someone, direct)

def get_match(val, cursor):
    orig_val = val
    for regex in user_regexes:
        val = orig_val
        match = regex.search(val)
        k = 0
        while match:
            i, j = match.span()
            if i <= (cursor-k) <= j:
                return match

            val = val[j:]
            k += j
            match = regex.search(val)

class TwitterSearchResult(object):
    def __init__(self, user, screen_name_index=-1, name_index=-1, prefix=None):
        self.user = user

        preflen = 0 if prefix is None else len(prefix)
        self.screen_name_span = (screen_name_index, preflen)
        self.name_span = (name_index, preflen)

    def __eq__(self, o):
        return self.user['id'] == o.user['id']

    def __neq__(self, o):
        return not self.__eq__(self, o)


class TwitterAutoCompleteController(object):
    def __init__(self, users):
        self.users = users

    def finish(self, val, cursor, selected_item):
        match = get_match(val, cursor)
        if match is not None:
            sofar = match.group(1)
            idx = len(sofar) if sofar is not None else 0
            before_cursor = ''.join([val[:cursor-idx], selected_item, ' '])
            value = before_cursor + val[cursor:]
            return value, len(before_cursor)

    def search_users(self, prefix):
        if prefix is None:
            return [TwitterSearchResult(user) for user in self.users]

        prefix = prefix.lower()
        found = []

        for user in self.users:
            screen_name_index = user['screen_name'].lower().find(prefix)
            name_index = user['name'].lower().find(prefix)

            if screen_name_index != -1 or name_index != -1:
                result = TwitterSearchResult(user, screen_name_index, name_index, prefix)
                found.append(result)

        return found

    def complete(self, val, cursor):
        items = []

        match = get_match(val, cursor)
        if match is not None:
            prefix = match.group(1)
            if prefix is not None:
                prefix = prefix.lower()
            items = self.search_users(prefix)

        return items or None

from gui.autocomplete import AutoCompleteDropDown
from collections import defaultdict

class TwitterAutoCompleteDropDown(AutoCompleteDropDown):
    profile_image_size = 24
    def __init__(self, parent):
        AutoCompleteDropDown.__init__(self, parent)

        self.UpdateSkin()

        from gui.browser.webkit.imageloader import WebKitImageLoader
        self.image_loader = WebKitImageLoader()
        self.image_loader.on_load += self.on_image_load

        self.images = {}
        self.image_rows = defaultdict(set)

    def on_image_load(self, img, src):
        self.images[src] = img
        for row in self.image_rows[src]:
            self.RefreshLine(row)

    def should_ignore_key(self, e):
        # "@" shouldn't trigger the reshowing of the popup.
        if e.KeyCode == 50 and e.ShiftDown():
            return True

        if e.KeyCode in (wx.WXK_LEFT, wx.WXK_RIGHT):
            return True


    def get_profile_image(self, url, n):
        self.image_rows[url].add(n)

        try:
            image = self.images[url]
        except KeyError:
            image = self.images[url] = self.image_loader.get(url)

        return image

    def UpdateSkin(self):
        syscol = wx.SystemSettings.GetColour
        self.colors = dict(
            screen_name = syscol(wx.SYS_COLOUR_MENUTEXT),
            screen_name_selected = syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT),
            name = wx.Color(160, 160, 160),
            name_selected = syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT),
            background = syscol(wx.SYS_COLOUR_WINDOW),#wx.WHITE,
            background_selected = syscol(wx.SYS_COLOUR_HIGHLIGHT),
        )

    def get_icon_for_item(self, n):
        item = self.items[n].user

        try:
            url = item['small_profile_image_url']
        except KeyError:
            url = item['small_profile_image_url'] = twitter_util.twitter_mini_img_url(item['profile_image_url'])

        image = self.get_profile_image(url, n)
        if image is None:
            image = self.get_no_icon()
        else:
            image = image.Resized(self.profile_image_size)

        return image

    def color(self, name, selected=False):
        if selected: name += '_selected'
        return self.colors[name]

    def OnPaint(self, dc, rect, n):
        item = self.items[n]
        user = item.user
        selected = self.IsSelected(n)

        # draw background
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(self.color('background', selected)))
        dc.DrawRectangleRect(rect)

        dc.Font = self.frame.Font

        padding = 5

        # the profile image
        image = self.get_icon_for_item(n)
        image.Draw(dc, rect.SubtractCopy(left=padding), wx.ALIGN_CENTER_VERTICAL)
        rect = rect.SubtractCopy(left = image.Width + padding * 2)

        # the screen name
        screen_name = user['screen_name']
        screen_name_w = dc.GetTextExtent(screen_name)[0]

        text_alignment = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL

        def draw_with_highlight(text, rect, span, colorname, offset=0):
            dc.SetTextForeground(self.color(colorname, selected))
            dc.DrawLabel(text, rect, text_alignment)

            if False: # disable highlight
                # draw a search highlight if it exists
                i, j = span
                j += i
                if i != -1:
                    i += offset
                    j += offset
                    w, h = dc.GetTextExtent(text[:i])
                    r = rect.SubtractCopy(left=w)
                    w, h = dc.GetTextExtent(text[i:j])
                    dc.SetTextForeground(wx.BLACK)
                    dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0)))
                    dc.SetPen(wx.TRANSPARENT_PEN)
                    highlight_rect = r.x, r.y + (r.height/2-h/2), w-2, h
                    dc.DrawRectangleRect(highlight_rect)
                    dc.DrawLabel(text[i:j], r, text_alignment)

        draw_with_highlight(screen_name, rect, item.screen_name_span, 'screen_name')

        # the real name
        if screen_name_w <= rect.width:
            draw_with_highlight(u' (%s)' % user['name'], rect.SubtractCopy(left=screen_name_w), item.name_span, 'name', 2)

    def get_no_icon(self):
        try:
            return self._noicon
        except AttributeError:
            self._noicon = get_twitter_noicon().Resized(self.profile_image_size)
            return self._noicon

from gui.toolbox import UpgradeDialog

class TwitterAchievmentsDialog(UpgradeDialog):
    def __init__(self, parent, title, message):
        icon = skin.get('serviceicons.twitter', None)
        super(TwitterAchievmentsDialog, self).__init__(parent,
            title=title,
            message = message,
            icon=icon,
            ok_caption=_('&Invite Followers'),
            cancel_caption=_('&No Thanks'),
            )

def show_acheivements_dialog(cb):
    def diag_cb(ok):
        if ok:
            cb()
            hooks.notify('digsby.statistics.twitter.invite.yes')
        else:
            hooks.notify('digsby.statistics.twitter.invite.no')

    TwitterAchievmentsDialog.show_dialog(
        parent=None,
        title='Invite Twitter Followers',
        message = 'Please support Digsby by helping us spread the word. Would\n'
                    'you like to send a direct message to your Twitter followers\n'
                    'inviting them to Digsby?',
        success=diag_cb)

    hooks.notify('digsby.statistics.twitter.invite.shown')



