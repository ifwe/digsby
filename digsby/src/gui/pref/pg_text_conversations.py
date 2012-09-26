import wx
from wx import EXPAND, BOTTOM, LEFT
from common import profile
from gui.uberwidgets.formattedinput2.formatprefsmixin import PrefInput
from gui.uberwidgets.formattedinput2.fromattedinputevents import EVT_TEXT_FORMAT_CHANGED
import operator
from gui.pref.prefcontrols import Check, Choice, CheckChoice, get_pref, HSizer, Label, Browse,\
    LocationButton
from gui.uberwidgets.PrefPanel import PrefCollection, PrefPanel
from config import platformName
from common import pref, delpref

timestamp_options = (('%#I:%M',       '5:43'),
                     ('%#I:%M %p',    '5:43 PM'),
                     ('%#I:%M:%S',    '5:43:20'),
                     ('%#I:%M:%S %p', '5:43:20 PM'),
                     ('%H:%M',        '17:43'),
                     ('%H:%M:%S',     '17:43:20'))

new_im_choices = [
    ('stealfocus', _('automatically take focus')),
    ('minimize',   _('start minimized in taskbar')),
    ('hide',       _('start hidden (tray icon blinks)')),
]

ad_position_options = (
    ('bottom', _('bottom')),
    ('top',    _('top')),
    ('left',   _('left')),
    ('right',   _('right')),
)

def checkbox_enabled_when_pref(cb, prefname):
    cb.Enabled = get_pref(prefname)
    profile.prefs.link(prefname, lambda val: wx.CallAfter(cb.Enable, val), obj = cb)

def panel(panel, sizer, newgroup, exithooks):
    warncheck = Check('messaging.tabs.warn_on_close', 'Warn me when I attempt to close multiple conversations')(panel)
    checkbox_enabled_when_pref(warncheck, 'messaging.tabs.enabled')

    window_options = [
        Check('conversation_window.always_on_top',     _('&Keep on top of other applications'))
    ]

    window_options.extend([
                      Check('messaging.tabs.enabled', _("Group multiple conversations into one tabbed window")),
                      warncheck])

    if platformName != 'mac':
        window_options.append((Choice('conversation_window.new_action',
                                     new_im_choices,
                                     caption = _('New conversation windows: ')), 0, wx.EXPAND | wx.BOTTOM, 3))
    window_options.append(
                      Choice('messaging.tabs.icon', (('buddy',   _("buddy icon")),
                                                     ('service', _("service icon")),
                                                     ('status',  _("status icon"))),
                                                    _("Identify conversations with the contact's: ")))

    winops = PrefPanel(panel,
                       PrefCollection(*window_options),
                       _('Window Options'))


    conops   = PrefPanel(panel, get_conversation_entries(panel, exithooks),  _('Conversation Options'))

    disable_flash = Check('imwin.ads_disable_flash', _("Don't show flash ads"))(panel)
    checkbox_enabled_when_pref(disable_flash, 'imwin.ads')

    ad_options = PrefPanel(panel,
        PrefCollection(Label(_('Help keep Digsby free by showing an\nadvertisement in the IM window.')),
                       Check('imwin.ads', _('Support Digsby development with an ad')),
                       disable_flash,
                       Choice('imwin.ads_position', ad_position_options, _('Location of ad in IM window: ')),
                       layout=wx.BoxSizer(wx.VERTICAL),
                       itemoptions = (0, wx.EXPAND | wx.BOTTOM, 8),
                       ),
        _('Ad Options'))

    hsizer = HSizer()
    hsizer.AddMany([
        (conops, 1, wx.EXPAND | wx.ALL, 3),
        (ad_options, 0, wx.EXPAND | wx.ALL, 3)
    ])


    textform = PrefPanel(panel, build_format_preview(panel, exithooks), _('Text Formatting'))

    panel._conops = conops

    sizer.AddMany([(winops,   0, EXPAND | BOTTOM, 6),
                   (hsizer,   0, EXPAND | BOTTOM, 6),
                   (textform, 1, EXPAND | BOTTOM, 6)])

    return panel

def AspellMenuEntries(spellchecker):
    dicts = spellchecker.dict_info
    langs = ((key, dicts[key]['name_native']) if 'name_native' in dicts[key] else (key, dicts[key]['name_english']) for key in dicts)
    return sorted(langs, key = lambda x: x[1].upper())

def build_format_preview(parent, exithooks):
    p = wx.Panel(parent)
    s = p.Sizer = wx.BoxSizer(wx.VERTICAL)

    input = PrefInput(p,
                      value = _('Your messages will look like this.'),
                      autosize = False,
                      multiFormat = False,
                      showFormattingBar = (platformName != 'mac'),
                      skin = 'AppDefaults.FormattingBar',
                      formatpref = 'messaging.default_style')


    def OnFormatChanged(event):
        input.SaveStyle('messaging.default_style')

    input.Bind(EVT_TEXT_FORMAT_CHANGED, OnFormatChanged)

    input.SetMinSize((300, 77)) # why doesn't IMInput size correctly?

    s.Add(input, 1, wx.EXPAND|wx.ALL, 1)

    # include a "font" button on mac.
    if platformName == 'mac':
        h = wx.BoxSizer(wx.HORIZONTAL)
        h.AddStretchSpacer(1)
        h.Add(input.CreateFontButton(p), 0, EXPAND | wx.ALL, 5)
        s.Add(h, 0, wx.EXPAND)



    def OnPaintWithOutline(event):
        dc = wx.AutoBufferedPaintDC(p)

        rect = wx.RectS(p.Size)
        irect = wx.Rect(input.Rect)
        irect.Inflate(1, 1)

        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)

        dc.Pen = wx.Pen(wx.Color(213, 213, 213))
        dc.DrawRectangleRect(irect)

    p.Bind(wx.EVT_PAINT, OnPaintWithOutline)

    return p


def get_conversation_entries(panel, exithooks):
    p = wx.Panel(panel)
    from common.spelling import spellchecker

    history = Check('conversation_window.show_history',
                    _('Show last %2(conversation_window.num_lines)d lines in IM window'))(p)

    conversation_entries = [
        Check('conversation_window.timestamp', _('&Display timestamp:'))(p),
        Choice('conversation_window.timestamp_format', timestamp_options, allow_custom=True)(p),
    ]

    if 'wxMac' not in wx.PlatformInfo:
        # don't include Aspell options in wxMac, since spell checking will
        # be provided by the system text controls
        conversation_entries.extend([
            Check('messaging.spellcheck.enabled', _('Spell check:'))(p),
            Choice('messaging.spellcheck.engineoptions.lang', AspellMenuEntries(spellchecker))(p)
        ])

    conversation_entries.extend(emoticon_choice(p))

    s = wx.FlexGridSizer(len(conversation_entries), 2, 3, 6)
    s.AddGrowableCol(1, 1)

    for i, entry in enumerate(conversation_entries):
        assert not isinstance(entry, tuple)
        s.Add(entry, i%2, wx.EXPAND)

    v = wx.BoxSizer(wx.VERTICAL)
    v.Add(s, 1, wx.EXPAND)


    v.AddMany([
        (1, 7),
        (Check('log.ims',  _('Log IM conversations to hard drive'), callback = history.Enable)(p), 0, wx.EXPAND),
        (1, 4),
        (history, 0, LEFT, 18),
        (1, 4),
        (LocationButton('local.chatlogdir', _('Location:'))(p), 0, wx.EXPAND | LEFT, 18),
    ])

    history.Enable(pref('log.ims', type=bool, default=True))

    if 'wxMac' not in wx.PlatformInfo:
        exithooks += spellchecker.DownloadDict

    p.Sizer = v

    return p

def emoticon_choice(panel):
    '''
    Builds a dropdown for selecting emoticon packs.

    If your current pack cannot be found, it is reset to default.
    '''

    from gui.imwin import emoticons
    emoticonchoices = [(pack.path.name, pack.name) for pack in emoticons.findsets() if pack.name]

    current_pack = pref('appearance.conversations.emoticons.pack', None)

    if (current_pack) not in map(operator.itemgetter(0), emoticonchoices):
        delpref('appearance.conversations.emoticons.pack')

    return [
        Check('appearance.conversations.emoticons.enabled', _('Show &emoticons:'))(panel),
        Choice('appearance.conversations.emoticons.pack', emoticonchoices)(panel)
    ]
