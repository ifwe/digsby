'''
Formatted text input.
'''

from __future__ import with_statement

import config
from traceback import print_exc
from gui.prototypes.fontdropdown import FontDropDown

import wx, cgi, cgui
from wx import FONTSTYLE_NORMAL, FONTFAMILY_DEFAULT, FONTWEIGHT_NORMAL, Font, BufferedPaintDC, RectS

from common import profile, setpref, pref, prefprop
from util import Storage, try_this

from gui import skin
from simplemenu import SimpleMenu,SimpleMenuItem
from gui.textutil import CopyFont
from gui.skin.skinparse import makeFont
from UberBar import UberBar
from UberButton import UberButton
from UberEmotiBox import UberEmotiBox

from gui.textutil import default_font
from gui.validators import LengthLimit
from gui import clipboard

import logging
log = logging.getLogger('formattedinput')

OUTLINE_COLOR = wx.Colour(213, 213, 213)
DEFAULT_SIZES = ['8', '10', '12', '14', '18', '24', '36']

def FontFromFacename(facename):
    return Font(10, FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, FONTWEIGHT_NORMAL, False, facename)

def FamilyNameFromFont(font):
    return font.GetFamilyString()[2:].lower()

wxMSW = 'wxMSW' in wx.PlatformInfo

if wxMSW:
    from cgui import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED

    from gui.spellchecktextctrlmixin import SpellCheckTextCtrlMixin

    class FormattedExpandoTextCtrl(ExpandoTextCtrl, SpellCheckTextCtrlMixin):
        def __init__(self, parent, style = 0, value = '', validator = wx.DefaultValidator):
            ExpandoTextCtrl.__init__(self, parent, wx.ID_ANY, value, wx.DefaultPosition, wx.DefaultSize, style, validator, value)

            SpellCheckTextCtrlMixin.__init__(self)

    class FormattedTextCtrl(cgui.InputBox, SpellCheckTextCtrlMixin):
        def __init__(self, parent, id = wx.ID_ANY, value = '',
                     pos = wx.DefaultPosition,
                     size = wx.DefaultSize,
                     style = 0,
                     validator = wx.DefaultValidator,
                     name = "FormatterTextCtrl"):
            cgui.InputBox.__init__(self, parent, id, value, pos, size, style, validator, name)

            SpellCheckTextCtrlMixin.__init__(self)


else:
    from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED
    oldfontset = ExpandoTextCtrl.SetFont
    ExpandoTextCtrl.SetFont = lambda s, *a, **k: wx.CallAfter(lambda: oldfontset(s, *a, **k))

    class FormattedExpandoTextCtrl(ExpandoTextCtrl):
        def __init__(self, *a, **k):
            ExpandoTextCtrl.__init__(self, *a, **k)

        def HitTestSuggestions(self, *a, **k):
            return -1, []

        def GetWordAtPosition(self, *a, **k):
            return None

    class FormattedTextCtrl(wx.TextCtrl):
        def __init__(self, *a, **k):
            wx.TextCtrl.__init__(self, *a, **k)



def default_umenu(tc):
    from gui.uberwidgets.umenu import UMenu
    m = UMenu(tc)

    # spelling suggestions and options
    if isinstance(tc, SpellCheckTextCtrlMixin):
        tc.AddSuggestionsToMenu(m)

    m.AddItem(_('Copy'),  id = wx.ID_COPY,  callback = tc.Copy)
    m.AddItem(_('Paste'), id = wx.ID_PASTE, callback = tc.Paste)
    m.AddSep()

    from gui.toolbox import add_rtl_checkbox
    add_rtl_checkbox(tc, m)

    return m

TextAttrs = ('Alignment BackgroundColour Font LeftIndent LeftSubIndent '
            'RightIndent Tabs TextColour').split()

FontAttrs = 'pointSize family style weight underline faceName encoding'.split()

def font_to_tuple(font):
    args = []
    for a in FontAttrs:
        if a == 'underline':
            a = 'Underlined'
        else:
            a = str(a[0].upper() + a[1:]) # str.title lowers everything but the first

        if a == 'Encoding':
            # FontEncoding is an enum, we must int it
            args.append(int(getattr(font, a)))
        else:
            args.append(getattr(font, a))
    return tuple(args)


if getattr(wx, 'WXPY', False):
    #
    # This is a hack for the WXPY bindings until it deals with enums in a more
    # sane way.
    #
    def tuple_to_font(t):
        t = list(t)
        if len(t) >= 7:
            t[6] = wx.FontEncoding(t[6])

        return Font(*t)

else:
    def tuple_to_font(t):
        return Font(*t)

wx.Colour.__hash__   = lambda c: hash((c[i] for i in xrange(4)))

#spellcheck: wx.TE_RICH2|wx.TE_MULTILINE| wx.TE_CHARWRAP | wx.NO_BORDER | wx.WANTS_CHARS | wx.TE_NOHIDESEL
txtFlags = (wx.TE_MULTILINE | wx.TE_CHARWRAP | wx.NO_BORDER | wx.WANTS_CHARS | wx.TE_NOHIDESEL)

def default_msg_font():
    return try_this(lambda: makeFont('Arial 10'), default_font())

def load_pref_style(prefname):

    try:
        stylepref = pref(prefname)

        if isinstance(stylepref, basestring):
            style = Storage(Font = makeFont(stylepref))
        else:
            style = Storage(stylepref)
    except Exception:
        print_exc()
        style = {}

    if type(style.Font) is tuple:
        try:
            font = tuple_to_font(style.Font)
        except Exception:
            print_exc()
            font = default_msg_font()
    else:
        font = style.Font
    fgc  = try_this(lambda: wx.Colour(*style.TextColour), None) or wx.BLACK
    bgc  = try_this(lambda: wx.Colour(*style.BackgroundColour), None) or wx.WHITE

    return font, fgc, bgc

def font_attrs_from_storage(s):
    font = Font(s['size'],
                FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_ITALIC if s['italic'] else wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD  if s['bold'] else wx.FONTWEIGHT_NORMAL,
                s['underline'],
                s['face'])

    fgc  = s['foregroundcolor']
    bgc  = s['backgroundcolor']

    return font, fgc, bgc

def textattr_from_storage(s):
    font, fgc, bgc = font_attrs_from_storage(s)
    fgc  = try_this(lambda: wx.Colour(fgc), None) or wx.BLACK
    bgc  = try_this(lambda: wx.Colour(bgc), None) or wx.WHITE
    return wx.TextAttr(fgc, bgc, font)

def make_format_storage(font, fgc, bgc):
    return Storage(backgroundcolor = bgc,
                   foregroundcolor = fgc,
                   face            = font.FaceName,
                   size            = font.PointSize,
                   underline       = font.Underlined,
                   bold            = font.Weight == wx.BOLD,
                   italic          = font.Style == wx.ITALIC,
                   family          = FamilyNameFromFont(font),
                   )

def get_default_format(prefname = 'messaging.default_style'):
    '''
    Returns a format storage for the current pref.
    '''

    return make_format_storage(*load_pref_style(prefname))

class FormattedInput(cgui.SimplePanel):
    '''
    An RTF2 based input box with a formatting bar and auto sizing,
    '''
    def __init__(self,
                 parent,
                 pos       = wx.DefaultPosition,
                 size      = wx.DefaultSize,
                 value     = '',
                 entercallback = None,
                 font      = True,
                 pointsize = True,
                 bold      = True,
                 italic    = True,
                 underline = True,
                 textcolor = True,
                 bgcolor   = True,
                 sizes     = DEFAULT_SIZES,
                 emots     = None,

                 singleFormat = False,
                 show_formatting_bar = True,
                 rtl_input = False,
                 prefmode = False,
                 outlined = False,
                 aimprofile = False,
                 autosize = True,
                 default_skin = False,

                 validator = None,

                 format = None,):

        cgui.SimplePanel.__init__(self, parent)

        self.prefmode   = prefmode
        self.aimprofile = aimprofile
        self.autosize   = autosize

        self.UseAppDefaultSkin = (self.prefmode or self.aimprofile) or default_skin

        self.initover = False
        self.entercallback = entercallback

        self.sizes = sizes
        self.emots = emots

        # create the Formatting bar, buttons, and menus
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        csizer = self.csizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(csizer, 1, wx.EXPAND | wx.ALL, 1 if outlined else 0)

        self.UpdateSkin()

        if validator is None:
            validator = LengthLimit(20480)

        if self.autosize:
            tc = self.tc = FormattedExpandoTextCtrl(self, style=txtFlags, value = value, validator=validator)
            tc.Bind(EVT_ETC_LAYOUT_NEEDED, self.expandEvent)
            tc.Bind(wx.EVT_SIZE, self.OnSize)
            if config.platform == 'win':
                tc.Bind(wx.EVT_COMMAND_TEXT_PASTE, self.OnPaste)
            tc.SetMaxHeight(100)

            loadedHeight = pref('conversation_window.input_base_height')
            baseHeight = self.tc.GetCharHeight() + getattr(self.tc, 'GetExtraHeight', lambda: 0)()

            tc.SetMinHeight(loadedHeight or baseHeight)

            if loadedHeight:
                log.info("input_base_height loaded as %s", loadedHeight)
            else:
                log.info("input_base_height not used, set to baseHeight as %s", baseHeight)

            tc.MinSize = wx.Size(tc.MinSize.width, tc.GetMinHeight())
#            wx.CallAfter(self.tc.HideScrollbars)
            self.expandEvent()
        else:
            tc = self.tc = FormattedTextCtrl(self, style = txtFlags, value = value, validator=validator)

        self.tc.LayoutDirection = wx.Layout_RightToLeft if rtl_input else wx.Layout_LeftToRight

        tc.Bind(wx.EVT_CONTEXT_MENU, lambda e: default_umenu(tc).PopupMenu(event = e))

        # bind textfield events
        tc.Bind(wx.EVT_KEY_DOWN,  self.OnKey)

        self.shownbuttons = dict(
            font      = font,
            pointsize = pointsize,
            bold      = bold,
            italic    = italic,
            underline = underline,
            textcolor = textcolor,
            bgcolor   = bgcolor)


        if config.platform != 'mac' and show_formatting_bar:
            self.construct_formatting_bar()
        else:
            self.formatbar = None

        csizer.Add(self.tc, 1, wx.EXPAND)
        self.single_format = singleFormat

        self.initover = True

        if format is None:
            wx.CallAfter(self.LoadStyle)
            profile.prefs.add_observer(self.WhenDefaultLayoutChange, 'messaging.default_style')
        else:
            self.SetFormatStorage(format)

        Bind = self.Bind
        if outlined:
            Bind(wx.EVT_PAINT,self.OnPaint)

        Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    def OnPaste(self, event):
        text = clipboard.get_text()
        if text is None:
            return

        # our rich text control adds a newline to the end of copied text--
        # strip one out if it's there
        if text.endswith('\n'):
            text = text[:-1]

        self.tc.WriteText(text)

    def OnSize(self, event):
        # this is an ugly hack, but unavoidable. For some reason, whenever this is called it
        # resets the Mac spell checker state. (i.e. all misspelled words are no longer underlined)
        # this code makes sure that doesn't happen.
        if config.platform == 'mac':
            self.tc.OnTextChanged(event)
            self.tc.MacCheckSpelling(True)

    def BindSplitter(self, splitter):
        splitter.Bind(wx.EVT_LEFT_DOWN, self.OnSplitterStart)
        splitter.Bind(wx.EVT_LEFT_UP, self.OnSplitterSet)
        self.sizeID = wx.EVT_SIZE
        #SWIG HAX: In Robin's bindings, wx.EVT_SIZE is a function, and wx.wxEVT_SIZE is the int id
        if not config.platform == "win":
            self.sizeID = wx.wxEVT_SIZE
        splitter.Connect(splitter.Id, splitter.Id, self.sizeID, self.OnFirstSplitterSize)

        self.splitter = splitter

    def OnFirstSplitterSize(self, event):

        #HAX: make sure the splitter lays out the first time it get's a real size

        event.Skip()

        splitter = self.splitter

        if splitter.Size.height and splitter.Size.width:
            splitter.Disconnect(splitter.Id, splitter.Id, self.sizeID)
            wx.CallAfter(self.expandEvent)

    def OnSplitterStart(self, event):
        event.Skip()
        tc = self.tc

        baseh = min(tc.GetMaxHeight(), tc.GetCharHeight() * tc.GetNumLines() + tc.GetExtraHeight())

        tc.MinSize = wx.Size(tc.MinSize.width, baseh)
        tc.SetMinHeight(baseh)
        self.MinSize = wx.Size(-1, (self.formatbar.Size.height if self.FormattingBarIsShown() else 0) + tc.MinSize.height)

    def OnSplitterSet(self,event):
        event.Skip()
        tc = self.tc

        baseh = min(tc.GetMaxHeight(), self.tc.GetCharHeight() * self.tc.GetNumLines() + self.tc.GetExtraHeight())
        h = tc.Size.height if tc.Size.height != baseh else 0

        log.info("input_base_height set to %s", h)

        setpref('conversation_window.input_base_height', h)
        tc.SetMinHeight(h)

    def OnPaint(self, event):
        'Draws an outline around the control.'
        dc = BufferedPaintDC(self)
        dc.Brush = wx.TRANSPARENT_BRUSH
        dc.Pen = wx.Pen(OUTLINE_COLOR)
        dc.DrawRectangleRect(RectS(self.ClientSize))

    def OnDestroy(self, event):
        event.Skip()
        profile.prefs.remove_observer(self.WhenDefaultLayoutChange, 'messaging.default_style')

    def expandEvent(self, e=None):
        height = (self.formatbar.Size.height if self.FormattingBarIsShown() else 0) + \
            max(self.tc.MinSize.height, self.tc.GetMinHeight())

        self.MinSize = wx.Size(-1, height)

        # If BindSplitter was called, we have .splitter
        if hasattr(self, 'splitter'):
            self.splitter.SetSashPosition(self.splitter.ClientSize.height - height)

    def on_fbar_context_menu(self, e):
        # TODO: why isn't the IM window's formatting bar its own subclass!?

        from gui.uberwidgets.umenu import UMenu
        m = UMenu(self)
        m.AddItem(_('Hide Formatting Bar'), callback = lambda: wx.CallAfter(setpref, 'messaging.show_formatting_bar', False))
        m.PopupMenu()

    def construct_formatting_bar(self):
        fb = self.formatbar = UberBar(self, skinkey = self.toolbarskin, alignment = wx.ALIGN_LEFT)

        if not self.prefmode and not self.aimprofile:
            fb.Bind(wx.EVT_CONTEXT_MENU, self.on_fbar_context_menu)

        self.fontdd = FontDropDown(fb, skinkey = fb.buttonskin)
        self.fontdd.Bind(wx.EVT_COMMAND_CHOICE_SELECTED, self.OnFontSelect)

        self.msize = SimpleMenu(self, self.menuskin, maxheight = 10) # TODO: max and min width?
        self.msize.SetItems(self.SetSizes(self.sizes))
        self.bsize = UberButton(fb, -1, '10', menu = self.msize, type = 'menu')
        self.bsize.SetStaticWidth(self.sizeddwidth)
        self.msize.SetWidth(self.sizeddwidth)
        self.bbold = UberButton(fb, -1, icon = self.bicon, type = 'toggle')
        self.bbold.Bind(wx.EVT_TOGGLEBUTTON, self.ToggleBold)

        self.bitalic = UberButton(fb, -1, icon = self.iicon, type="toggle")
        self.bitalic.Bind(wx.EVT_TOGGLEBUTTON, self.ToggleItalic)

        self.bunderline = UberButton(fb, -1, icon = self.uicon,  type="toggle")
        self.bunderline.Bind(wx.EVT_TOGGLEBUTTON, self.ToggleUnderline)

        self.bcolor = UberButton(fb, -1, icon = self.fcicon )
        self.bcolor.Bind(wx.EVT_BUTTON, self.OnColor)

        self.bbgcolor = UberButton(fb,-1, icon = self.bcicon)
        self.bbgcolor.Bind(wx.EVT_BUTTON, self.OnBGColor)

        self.bemote = UberButton(fb, -1, icon = self.eicon)
        self.bemote.Bind(wx.EVT_BUTTON, self.on_emote_button)

        self.EnableFormattingButtons(getattr(self, 'formatting_enabled', True))

        #Add all the buttons to the formating bar
        fb.AddMany([self.fontdd,
                    self.bsize,
                    self.bbold,
                    self.bitalic,
                    self.bunderline,
                    self.bcolor,
                    self.bbgcolor,
                    self.bemote])

        self.csizer.Insert(0, fb, 0, wx.EXPAND, 0)
        self.ShowButtons(**self.shownbuttons)

        self.UpdateDisplay()

        self.formatbar.Bind(wx.EVT_SIZE, lambda e: (e.Skip(), wx.CallAfter(self.expandEvent)))

    def on_emote_button(self, e):
        self.display_emotibox(self.bemote.ScreenRect)

    def display_emotibox(self, rect):
        ebox = self.get_emotibox()
        # position and display the emotibox
        ebox.Display(rect)

    def get_emotibox(self):
        'Shares the emoticon box between all instances of this class.'

        b = None
        old_name, new_name = getattr(self, '_emotipack_name', None), pref('appearance.conversations.emoticons.pack', type = unicode, default = u'default')
        self._emotipack_name = new_name

        try:
            b = self.__class__.emotibox
            if not wx.IsDestroyed(b):
                if old_name != new_name:
                    b.Destroy()
                elif b.Parent is not self:
                    b.Reparent(self)

        except AttributeError:
            pass

        if b is None or wx.IsDestroyed(b):
            from gui.imwin.emoticons import get_emoticon_bitmaps
            b = self.__class__.emotibox = UberEmotiBox(self, get_emoticon_bitmaps(self._emotipack_name), self.tc, maxwidth = 12)
        else:
            b.SetTextCtrl(self.tc)

        return b

    def UpdateSkin(self):
        s = lambda name, d = None: skin.get('%sFormattingBar.%s' % ('AppDefaults.' if self.UseAppDefaultSkin else '',name),d)

        iconsize = self.iconsize = s('iconsize')

        icons = s('icons').get

        bicon   = self.bicon   =             icons('bold').Resized(iconsize)
        iicon   = self.iicon   =           icons('italic').Resized(iconsize)
        uicon   = self.uicon   =        icons('underline').Resized(iconsize)
        fcicon  = self.fcicon  =  icons('foregroundcolor').Resized(iconsize)
        bcicon  = self.bcicon  =  icons('backgroundcolor').Resized(iconsize)
        eicon   = self.eicon   =            icons('emote').Resized(iconsize)

        fontddwidth = self.fontddwidth = s('FontDropDownWidth')
        sizeddwidth = self.sizeddwidth = s('SizeDropDownWidth')
        menuskin    = self.menuskin    = s('MenuSkin', None)
        toolbarskin = self.toolbarskin = s('toolbarskin', None)

        if self.initover and getattr(self, 'formatbar', None) is not None:
            self.formatbar.SetSkinKey(toolbarskin)
            # new font drop down does not have SetMinWidth
            # self.fontdd.SetMinWidth(fontddwidth)
            self.bsize.SetStaticWidth(sizeddwidth)
            self.msize.SetWidth(sizeddwidth)
            self.bbold.SetIcon(bicon)
            self.bitalic.SetIcon(iicon)
            self.bunderline.SetIcon(uicon)
            self.bcolor.SetIcon(fcicon)
            self.bbgcolor.SetIcon(bcicon)
            self.bemote.SetIcon(eicon)

        wx.CallAfter(self.Layout)

    def __repr__(self):
        try:
            return '<%s under %r>' % (self.__class__.__name__, self.Parent)
        except Exception:
            return object.__repr__(self)

    def SetSingleFormat(self, singleformat = True):
        '''
        Sets this control to only have one style for all of its contents. The
        style used is the first one found.
        '''

        return

    def GetSingleFormat(self):
        return True#self.single_format

    SingleFormat = property(GetSingleFormat, SetSingleFormat, None, doc = SetSingleFormat.__doc__)

    def SaveStyle(self):
        style = self.GetStyleAsDict()
        from pprint import pformat
        print 'saving style:\n%s' % pformat(style)
        setpref('profile.formatting' if self.aimprofile else 'messaging.default_style',style)

    def GetStyleAsDict(self):

        tc = self.tc

        return dict(BackgroundColour = tuple(tc.BackgroundColour),
                     TextColour = tuple(tc.ForegroundColour),
                     Font = font_to_tuple(tc.Font))

    def WhenDefaultLayoutChange(self,src,pref,old,new):

#        if self.GetStyleAsDict() == old:
        self.LoadStyle()

    def LoadStyle(self):
        self.SetFormat(*load_pref_style('profile.formatting' if self.aimprofile else 'messaging.default_style'))


    def SetFormatStorage(self, format_storage):
        return self.SetFormat(*font_attrs_from_storage(format_storage))

    def SetFormat(self, font, fgc, bgc):
        tc = self.tc
        tc.Font = font
        tc.SetFont(font)
        tc.ForegroundColour = wx.BLACK
        tc.ForegroundColour = wx.Color(*fgc)
        tc.BackgroundColour = wx.Color(*bgc)
        self.UpdateDisplay()

    def ShowFormattingBar(self, val):
        'Shows or hides the formatting bar.'

        if val and self.formatbar is None:
            self.construct_formatting_bar()

        if self.formatbar is not None:
            self.csizer.Show(self.formatbar, val, True)
            self.Layout()

        if self.autosize:
            self.expandEvent()

    def FormattingBarIsShown(self):
        if getattr(self, 'formatbar', None) is not None:
            return self.formatbar.IsShown()

        return False

    def EnableFormattingButtons(self, enable):
        self.formatting_enabled = enable

        if hasattr(self, 'fontdd'): # the formatting bar might not have been constructed yet
            self.fontdd.Enable(enable)
            self.bsize.Enable(enable)
            self.bbold.Enable(enable)
            self.bitalic.Enable(enable)
            self.bunderline.Enable(enable)
            self.bcolor.Enable(enable)
            self.bbgcolor.Enable(enable)

    def ShowButtons(self,
                 font = True,
                 pointsize = True,
                 bold = True,
                 italic = True,
                 underline = True,
                 textcolor = True,
                 bgcolor = True):

        'Show or hide each button on the format bar.'

        self.fontdd.Show(font)
        self.bsize.Show(pointsize)
        self.bbold.Show(bold)
        self.bitalic.Show(italic)
        self.bunderline.Show(underline)
        self.bcolor.Show(textcolor)
        self.bbgcolor.Show(bgcolor)
        #self.bemote.Show(not self.prefmode)

    def GetStyleAsStorage(self):
        tc = self.tc
        font = tc.Font

        return Storage(
            backgroundcolor = tuple(tc.BackgroundColour),
            foregroundcolor = tuple(tc.ForegroundColour),
            family = FamilyNameFromFont(font),
            face = font.FaceName,
            size = font.PointSize,
            underline = font.Underlined,
            bold = font.Weight == wx.BOLD,
            italic = font.Style == wx.ITALIC)


    @property
    def Format(self):
        return self.GetStyleAsStorage()


    def GetHTML(self):
        'Does the necessary steps to convert the textfield value into HTML.'

        s = ''
        value = self.tc.Value

        s =  cgi.escape(value)

        s = s.replace('\n','<br>').replace('\t','&nbsp;&nbsp;')
        return s

    HTML = property(GetHTML)

    def GetValue(self):
        'Returns the string in the textfield.'

        return self.tc.GetValue()

    def SetValue(self, value):
        'Sets the string in the textfield.'

        return self.tc.SetValue(value)

    Value = property(GetValue, SetValue)

    @property
    def FontData(self):
        d = wx.FontData()
        tc = self.tc
        d.SetInitialFont(tc.GetFont())
        d.SetColour(tc.GetForegroundColour())
        return d

    def ShowModalFontDialog(self, e = None):
        '''
        Uses the native Mac font dialog to allow the user to select a font
        and a color.
        '''
        diag = wx.FontDialog(self, self.FontData)
        if wx.ID_OK == diag.ShowModal():
            font_data = diag.GetFontData()
            font = font_data.GetChosenFont()
            color = font_data.GetColour()

            tc = self.tc
            if color.IsOk():
                tc.ForegroundColour = color
            if font.IsOk():
                tc.Font = font

            if self.prefmode or self.aimprofile:
                wx.CallAfter(self.SaveStyle)

            tc.Refresh()
            tc.SetFocus()

    def CreateFontButton(self, parent, label = _('Set Font...')):
        '''
        Create a small button that will spawn a font dialog for setting
        the properties of this text control.
        '''
        font_button = wx.Button(parent, -1, label)
        font_button.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        font_button.Bind(wx.EVT_BUTTON, self.ShowModalFontDialog)
        return font_button

    def OnColor(self, event = None):
        "Calls the color chooser for setting font color."

        newcolor = wx.GetColourFromUser(self, self.tc.ForegroundColour, _('Choose a foreground color'))
        self.update_color(newcolor)

    def update_color(self, newcolor):

        if newcolor.IsOk():
            self.tc.ForegroundColour = newcolor

        if self.prefmode or self.aimprofile:
            wx.CallAfter(self.SaveStyle)

        #Insure the focus goes back to the TextField
        self.tc.Refresh()
        self.tc.SetFocus()


    def OnBGColor(self,event):
        'Calls the color chooser for setting font background color.'

        newcolor = wx.GetColourFromUser(self, self.tc.BackgroundColour, _('Choose a background color'))
        self.update_bgcolor(newcolor)

    def update_bgcolor(self, newcolor):

        if newcolor.IsOk():
            self.tc.BackgroundColour = newcolor


        if self.prefmode or self.aimprofile:
            wx.CallAfter(self.SaveStyle)

        self.tc.Refresh()
        self.tc.SetFocus()


    def ApplyStyleGUIless(self, flag=None):
        tc = self.tc

        font     = tc.GetFont()
        fontsize = font.GetPointSize()

        weight = font.Weight == wx.FONTWEIGHT_BOLD
        style = font.Style == wx.FONTSTYLE_ITALIC
        underline = font.Underlined

        if flag == 'bold': weight = not weight
        if flag == 'italic': style = not style
        if flag == 'underline':  underline = not underline

        font= CopyFont(font,
                       pointSize = fontsize,
                       style     = wx.ITALIC if style else wx.NORMAL,
                       weight    = wx.FONTWEIGHT_BOLD if weight else wx.NORMAL,
                       underline = underline)

        # setting the font twices fixes a bug.
        tc.Font = font
        tc.SetFont(font)

        fgc = tc.ForegroundColour
        tc.ForegroundColour = wx.BLACK
        tc.ForegroundColour = fgc

        if self.prefmode or self.aimprofile:
            wx.CallAfter(self.SaveStyle)

        self.tc.SetFocus()

    shiftToSend = prefprop("messaging.shift_to_send", False)

    def OnKey(self, event):
        """
            This detects key presses, runs entercallback if enter or return is pressed
            Any other key continues as normal, then refreshes the font and size info
        """
        keycode = event.KeyCode


        shiftToSend = self.shiftToSend
        hasModifiers = event.HasModifiers()
        shiftIsDown = event.Modifiers == wx.MOD_SHIFT
        ctrlIsDown = event.Modifiers == wx.MOD_CONTROL

        if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            # if there is a enter callback and no modifiers are down or if
            # shift should send and shift is down, call the callback
            if self.entercallback and \
                    (not (shiftToSend or hasModifiers or shiftIsDown) or \
                     (shiftToSend and shiftIsDown)):
                return self.entercallback(self)
            else:
                event.Skip()

        if not ctrlIsDown:
            return event.Skip()

        if wxMSW:
            # make Ctrl+R and Ctrl+L modify the RTL setting of the rich edit
            # control, not just the alignment.
            from gui.toolbox import set_rich_layoutdirection
            if keycode == ord('R'):
                set_rich_layoutdirection(self.tc, wx.Layout_RightToLeft)
                return
            elif keycode == ord('L'):
                set_rich_layoutdirection(self.tc, wx.Layout_LeftToRight)
                return

        if keycode == ord('B'):
            if hasattr(self, 'bbold'):
                self.bbold.Active()
                self.ApplyStyle()
            else:
                self.ApplyStyleGUIless('bold')
            return

        elif keycode == ord('I'):
            if hasattr(self, 'bitalic'):
                self.bitalic.Active()
                self.ApplyStyle()
            else:
                self.ApplyStyleGUIless('italic')
            return

        elif keycode == ord('U'):
            if hasattr(self, 'bunderline'):
                self.bunderline.Active()
                self.ApplyStyle()
            else:
                self.ApplyStyleGUIless('underline')
            return

        event.Skip()

    def Clear(self):
        """
            Clears the text from the text field
        """
        tc = self.tc

        if 'wxMSW' in wx.PlatformInfo:
            # Clear() removes any alignment flags that are set in the text control, so
            # reset them
            alignment = cgui.GetRichEditParagraphAlignment(tc)
            tc.Clear()
            if cgui.GetRichEditParagraphAlignment(tc) != alignment:
                cgui.SetRichEditParagraphAlignment(tc, alignment)
        else:
            tc.Clear()

    def UpdateDisplay(self):
        """
            Update the values of Font and Size buttons and the states of
            the bold, italic, and underline buttons based on selection or
            cursor posirion
        """
        with self.tc.Frozen():

            tc = self.tc

            font     = tc.GetFont()
            fontface = font.GetFaceName()
            fontsize = font.GetPointSize()


            bold = font.Weight == wx.FONTWEIGHT_BOLD
            italic = font.Style == wx.FONTSTYLE_ITALIC
            underline = font.Underlined

            # Set Bold, Italic, and Underline buttons
            if self.formatbar is not None:
                self.bbold.Active(bold)
                self.bitalic.Active(italic)
                self.bunderline.Active(underline)

                i = self.fontdd.FindString(fontface, False)
                self.fontdd.SetSelection(i)

                self.bsize.SetLabel(str(fontsize))
                self.bsize.Refresh()

    def ToggleBold(self, event):
        """
            Toggles the bold value of the selection
            or calls Applystyle in no selection
        """
        self.ApplyStyle()

    def ToggleItalic(self, event):
        """
            Toggles the italics state of the selection
            or calls Applystyle in no selection
        """
        self.ApplyStyle()

    def ToggleUnderline(self,event):
        'Toggles underline state of selection or calls Applystyle in no selection.'

        self.ApplyStyle()

    def ApplyStyle(self):
        'Sets the style at the cursor.'

        tc = self.tc

        style     = self.bitalic.active
        weight    = self.bbold.active
        underline = self.bunderline.active

        font= CopyFont(self.fontdd.GetClientData(self.fontdd.GetSelection()),
                       pointSize = int(self.bsize.label),
                       style     = wx.ITALIC if style else wx.NORMAL,
                       weight    = wx.FONTWEIGHT_BOLD if weight else wx.NORMAL,
                       underline = underline)

        tc.Font = font
        tc.SetFont(font)

        fgc = tc.ForegroundColour
        tc.ForegroundColour = wx.BLACK
        tc.ForegroundColour=fgc

        if self.prefmode or self.aimprofile:
            wx.CallAfter(self.SaveStyle)

        self.tc.SetFocus()

    def OnFontSelect(self, event):
        """
            Updates the button to the new font and applies it to the selection
            or calls ApplyStlye
        """
        self.ApplyStyle()

    def OnSizeMenu(self,item):
        """
            Updates the Size button to the new size and apllies it to the selection
            or calls ApplyStyle
        """
        self.bsize.SetLabel(item.content[0])

        self.ApplyStyle()

    def SetSizes(self, sizes = DEFAULT_SIZES):
        """
            Sets the list of selectable sizes
            If not set sizes default to ['8', '10', '12', '14', '18', '24', '36']
        """
        return [SimpleMenuItem([size], method = self.OnSizeMenu) for size in sizes]

