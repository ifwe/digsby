'''
"Skins" tab for the main preferences window.

- application skin
- conversation preview
- conversation settings
- text formatting
'''
from __future__ import with_statement

import wx
import config
from wx import VERTICAL, EXPAND, HORIZONTAL, CallLater, ALIGN_CENTER_VERTICAL, BOTTOM, \
    BoxSizer

from gui.pref.prefcontrols import *
from gui.uberwidgets.PrefPanel import PrefPanel

from common import pref
import common.logger
from util import try_this

from string import Template

from logging import getLogger; log = getLogger('prefs.appearance')

from tests.mock.mockbuddy import MockBuddy
from gui.imwin.messagearea import MessageArea
from gui.imwin.styles import get_theme_safe
from common import profile
from gui import skin

CONVO_THEME_PREF = 'appearance.conversations.theme'
EXAMPLE_CONVO_FILENAME = 'Example Conversation.html'

def panel(panel, sizer, addgroup, exithooks):
    # disable skins on mac
    if config.platform != 'mac':
        addgroup(_('Application Skin'), lambda p,*a: skin_sizer(p))

    addgroup(_('Conversation Theme'), lambda p,*a: conversation_sizer(p, panel))

    convo_preview = PrefPanel(panel, lambda parent, _prefix: conversation_preview(parent, exithooks, panel),
                              _('Conversation Preview'))
    sizer.Add(convo_preview, 1, EXPAND)

    return panel

def build_example_message_area(parent, theme):
    buddy = MockBuddy('Friend')

    msgarea = MessageArea(parent)
    msgarea.SetMinSize((-1, 150))
    msgarea.init_content(theme, buddy.alias, buddy, show_history = False)

    # load an example conversation from the resource directory.
    bytes = (skin.resourcedir() / EXAMPLE_CONVO_FILENAME).bytes()
    bytes = Template(bytes).safe_substitute({'Me': profile.username})
    msgs  = parent._examplehistory = list(common.logger.parse_html(bytes))

    log.info('  %d messages', len(msgs))
    msgarea.replay_messages(msgs, buddy, context = False)

    return msgarea

def conversation_preview(parent, exithooks, pref_panel):
    convo_panel = wx.Panel(parent)
    convo_panel.Sizer = sz = BoxSizer(VERTICAL)

    def setcontent(*a):
        convo_panel.Freeze()
        sz.Clear(True)
        
        theme = pref(CONVO_THEME_PREF)
        themeName = pref('appearance.conversations.theme')
        theme     = get_theme_safe(themeName, pref('appearance.conversations.variant'))
        log.info('showing message style %r', themeName)

        pref_panel.msgarea = msgarea = build_example_message_area(convo_panel, theme)
        sz.Add(msgarea, 1, EXPAND)
        sz.Layout()

        parent._thawtimer = CallLater(150, lambda: convo_panel.Thaw())
        return msgarea

    timer = wx.PyTimer(setcontent)

    def doset(*a):
        if timer.IsRunning(): return
        else: timer.Start(300, True)

    link = profile.prefs.link
    p = 'appearance.conversations.'

    # Changes to the following prefs cause the conversation preview window to update.
    links = [link(name, doset, False, obj = convo_panel) for name in [
                 # conversation appearance prefs
                 p + 'theme',
                 p + 'variant',
                 p + 'show_message_fonts',
                 p + 'show_message_colors',
                 p + 'show_header',

                 # timestamp format prefs
                 'conversation_window.timestamp',
                 'conversation_window.timestamp_format']]

    # Unlink these prefs when the prefs dialog closes.
    exithooks += lambda: [link.unlink() for link in links]
    wx.CallLater(200, setcontent)
    return convo_panel

def skin_sizer(p):
    from gui import skin
    skin_caption, variant_caption = _('Skin:'), _('Variant:')

    skins        = skin.list_skins()
    skin_choices = [(s, s.alias) for s in skins]

    sz = wx.FlexGridSizer(rows = 2, cols = 2, vgap = 5, hgap = 5)
    variant_sizer  = BoxSizer(VERTICAL)
    skin_choice    = Choice('appearance.skin', skin_choices, caption = '',
                            callback = lambda *a: wx.CallAfter(setskin, *a),
                            do_mark_pref = False)(p)

    def setskin(prefname = None, val = None):
        with p.Frozen():
            variant_sizer.Clear(True)

            if val is None:
                i = try_this(lambda: [s.name for s in skins].index(pref('appearance.skin')), 0)
                j = try_this(lambda: [v.path.namebase for v in skins[i].variants].index(pref('appearance.variant'))+1, 0)
                val = skins[i]

            variants = list(val.variants)

            if prefname is not None:
                mark_pref('appearance.skin',    val.name)
                mark_pref('appearance.variant', ('%s' % variants[0].path) if variants else None)
                wx.CallAfter(skin.reload)

            vchoices = [(None, val.novariant_alias)]
            if variants:
                vchoices += [(v.path.namebase, v.alias) for v in variants]

            choice = Choice('appearance.variant', vchoices, '',
                            callback = lambda *a: wx.CallAfter(skin.reload))(p)

            if prefname is None:
                skin_choice.SetSelection(i)
                choice.SetSelection(j)

            variant_sizer.Add(choice, 1, wx.EXPAND)
            choice.Enable(bool(variants))

            sz.Layout()

    setskin()
    sz.AddMany([
        (wx.StaticText(p,-1, skin_caption), 0, ALIGN_CENTER_VERTICAL),
        (skin_choice,   1, EXPAND),
        (wx.StaticText(p,-1, variant_caption), 0, ALIGN_CENTER_VERTICAL),
        (variant_sizer, 1, EXPAND),
    ])
    sz.AddGrowableCol(1,1)
    return sz

def conversation_sizer(p, panel):
    from gui.imwin.styles import get_themes

    themes = get_themes()

    theme_choices    = [(s.theme_name, s.theme_name) for s in themes]
#    icon_choices     = [('none','None')]
#    variant_choices  = [('red_green','Red - Green')]
#    emoticon_choices = [(s.lower(), '%s Emoticons' % s) for s in
#                        'Digsby Yahoo AIM Adium'.split()]

    sz = BoxSizer(wx.HORIZONTAL)
    combosizer = wx.FlexGridSizer(2,2, vgap = 5, hgap = 5)
    vsizer = BoxSizer(VERTICAL)

    checksizer = BoxSizer(wx.VERTICAL)

    PFX = 'appearance.conversations.'

    header_check = Check(PFX + 'show_header', _('Show header'),
                         callback = lambda val: panel.msgarea.show_header(val))(p)


    checksizer.Add(header_check,         0, BOTTOM,5)
    checksizer.Add(Check(PFX + 'show_message_fonts',    _('Show message fonts'))(p),  0, BOTTOM,5)

    colors_checkbox = Check(PFX + 'show_message_colors',   _('Show message colors'))(p)
    checksizer.Add(colors_checkbox, 0, BOTTOM,5)
    def combo(*a, **k):
        choice = Choice(*a, **k)(p)
        combosizer.Add(choice, 1, EXPAND)
        return choice

    combosizer.Add(wx.StaticText(p,-1, _('Theme:')),0,ALIGN_CENTER_VERTICAL)
    combo(PFX + 'theme',     theme_choices,   '', callback = lambda pref, value: wx.CallAfter(revar, value))
    combosizer.Add(wx.StaticText(p,-1, _('Variant:')),0,ALIGN_CENTER_VERTICAL)
    combosizer.AddGrowableCol(1,1)

    def revar(name = None, first = False):
        from common import pref
        if name is None:
            name = pref(PFX + 'theme')

        themes = get_themes()
        found = None
        for theme in themes:
            if theme.theme_name == name:
                found = theme

        if found is None:
            found = themes[0] if themes else None

        if found is not None:
            vars = found.variants
            if vars: vchoices = [((v, v) if v is not None else (None, found.novariant_name)) for v in vars]
            else:    vchoices = [(None, found.novariant_name)]
        else:
            vchoices = []
            vars = []

        p.Freeze()
        vsizer.Clear(True)

        if not first:
            mark_pref(PFX + 'variant', found.variant or '')
        choice = Choice(PFX + 'variant',  vchoices, '')(p)

        vsizer.Add(choice, 1, EXPAND)
        if not vars:
            #choice.SetSelection(vars.index(found.variant))
            choice.Enable(False)

        if found is not None:
            allow_colors = found.allow_text_colors if found is not None else True
            allow_header = bool(found.header)
        else:
            allow_colors = True
            allow_header = True

        # "Show Message Colors" checkbox is disabled and unchecked if the theme does not
        # support colors.
        colors_checkbox.Enable(allow_colors)
        colors_checkbox.SetValue(allow_colors and pref(PFX + 'show_message_colors'))

        header_check.Enable(allow_header)
        header_check.SetValue(allow_header and pref(PFX + 'show_header'))

        sz.Layout()
        p.Thaw()

    revar(first = True)

    sz.Add(combosizer,1,wx.EXPAND)
    sz.Add(checksizer,0,wx.LEFT,10)
    combosizer.Add(vsizer,1,wx.EXPAND)
    return sz

def text_formatting_sizer(p):
    sz = wx.FlexGridSizer(2,4, 3, 3)
    sz.FlexibleDirection = HORIZONTAL
    return sz

    sz.Add(SText(p, _('Fonts:')))
    sz.Add(Choice(['Theme Fonts'])(p))
    sz.Add(Choice(['12'])(p))
    sz.AddStretchSpacer(0)

    sz.AddMany([(SText(p,_('Colors:'))),
                (Choice(['Theme Colors'])(p)),
                (Choice(['A'])(p)),
                (Choice(['A'])(p)),
                ])



    return sz

