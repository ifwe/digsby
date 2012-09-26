'''
Prepares FormattedExpandoTextCtrl and FormattedTextCtrl dependant on platform

On Windows includes spellcheck mixin while on Mac it does not because spellcheck is provided by the OS

'''

from gui.uberwidgets.formattedinput2.fromattedinputevents import TextFormatChangedEvent
import wx

wxMSW = 'wxMSW' in wx.PlatformInfo
wxMac = 'wxMac' in wx.PlatformInfo

formattedstyle = (wx.TE_RICH2 | wx.TE_MULTILINE | wx.TE_CHARWRAP | wx.NO_BORDER | wx.WANTS_CHARS | wx.TE_NOHIDESEL)

from gui.textutil import default_font
from gui.uberwidgets.umenu import UMenu
from util.primitives.fmtstr import fmtstr, FormattingException

from cgui import InputBox

from cgui import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED

FONT_FLAGS = (wx.TEXT_ATTR_FONT_FACE | wx.TEXT_ATTR_FONT_SIZE | wx.TEXT_ATTR_FONT_WEIGHT | wx.TEXT_ATTR_FONT_ITALIC | wx.TEXT_ATTR_FONT_UNDERLINE)

class FormattingInterface(object):

    '''
    Interface to add text formatting related methods to a TextField object
    '''

    SetFormat = None

    def default_attrs(self):
        return wx.TextAttr(wx.BLACK, wx.WHITE, default_font())

    def __init__(self, multiFormat = True, format = None):
        self.MultiFormat(multiFormat)
        self.BindEvents()

        self.SetFormat(format if format is not None else self.default_attrs())

    def GetFormat(self):
        # FIXME: We need to get the style flags working right under OS X Cocoa
        # Right now it seems you need to have at least
        attrs = self.GetStyle(self.GetInsertionPoint())[1]
        if attrs.IsDefault(): # this will return wx.NullFont, not a very useful thing to use
            return self.default_attrs()

        return attrs

    def SetFormat_Single(self, textattr):
        '''
        Set format for the entire text content
        '''
        self.SetStyle(0, self.GetLastPosition(), textattr)
        self.SetDefaultStyle(textattr)

    def SetFormat_Multi(self, textattr):
        '''
        Set format for just the current selection
        '''
        start, end = self.GetSelection()
        self.SetStyle(start, end, textattr)


    def MultiFormat(self, multi):
        '''
        Turn MultiFormat support for a field on and off
        '''
        self.isMultiFormat = multi
        if multi:
            self.SetFormat = self.SetFormat_Multi
        else:
            self.SetFormat = self.SetFormat_Single

    def ApplyStyle(self, **format):
        '''
        Set the font style using human readable key words and simple values

        @param textcolor: wx.Color
        @param bgcolor: wx.Color
        @param facename: String
        @param pointsize: int
        @param bold: Bool
        @param italic: Bool
        @param underline: Bool
        '''

        textattr = self.GetFormat()
        font = textattr.GetFont()

        flags = 0

        if 'textcolor' in format:
            flags |= wx.TEXT_ATTR_TEXT_COLOUR
            textattr.SetTextColour(format['textcolor'])
        if 'bgcolor' in format:
            flags |= wx.TEXT_ATTR_BACKGROUND_COLOUR
            textattr.SetBackgroundColour(format['bgcolor'])

        if 'facename' in format:
            flags |= wx.TEXT_ATTR_FONT_FACE
            font.SetFaceName(format['facename'])
        if 'pointsize' in format:
            flags |= wx.TEXT_ATTR_FONT_SIZE
            font.SetPointSize(format['pointsize'])

        if 'bold' in format:
            flags |= wx.TEXT_ATTR_FONT_WEIGHT
            font.SetWeight(wx.FONTWEIGHT_BOLD if format['bold'] else wx.NORMAL,)
        if 'italic' in format:
            flags |= wx.TEXT_ATTR_FONT_ITALIC
            font.SetStyle(wx.FONTSTYLE_ITALIC if format['italic'] else wx.FONTSTYLE_NORMAL)
        if 'underline' in format:
            flags |= wx.TEXT_ATTR_FONT_UNDERLINE
            font.SetUnderlined(format['underline'])

        if flags & FONT_FLAGS:
            textattr.SetFont(font)

        textattr.SetFlags(flags)

        self.SetFormat(textattr)
        self.SetFocus()

        self.AddPendingEvent(TextFormatChangedEvent(self.Id, EventObject = self))

    def GenMenu(self):
        m = UMenu(self)

        # spelling suggestions and options
        if isinstance(self, SpellCheckTextCtrlMixin):
            if self.AddSuggestionsToMenu(m):
                m.AddSep()

        m.AddItem(_('Cut'),   id = wx.ID_CUT,   callback = self.Cut)
        m.AddItem(_('Copy'),  id = wx.ID_COPY,  callback = self.Copy)
        m.AddItem(_('Paste'), id = wx.ID_PASTE, callback = self.Paste)
        m.AddSep()
        m.AddItem(_('Select All'), id = wx.ID_SELECTALL, callback = lambda: self.SetSelection(0, self.GetLastPosition()))
        m.AddSep()

        from gui.toolbox import add_rtl_checkbox
        add_rtl_checkbox(self, m)

        return m


    def BindEvents(self):
        def OnContextMenu(event):
            pt = self.ScreenToClient(wx.GetMousePosition())
            ht = self.HitTest(pt)
            self.SetInsertionPoint(self.XYToPosition(ht[1], ht[2]))
            menu = self.GenMenu()
            menu.PopupMenu()


        Bind = self.Bind
        if not wxMac:
            Bind(wx.EVT_CONTEXT_MENU, OnContextMenu)

def _expand_event(self):
    if wx.IsDestroyed(self):
        return

    self.AddPendingEvent(wx.CommandEvent(EVT_ETC_LAYOUT_NEEDED, self.Id))

if wxMSW:
    from gui.spellchecktextctrlmixin import SpellCheckTextCtrlMixin

    class FormattedExpandoTextCtrl(ExpandoTextCtrl, SpellCheckTextCtrlMixin, FormattingInterface):
        def __init__(self, parent, style = 0, value = '', multiFormat = True, format = None, validator = wx.DefaultValidator):
            ExpandoTextCtrl.__init__(self, parent, wx.ID_ANY, value, wx.DefaultPosition, wx.DefaultSize, style | formattedstyle, validator, value)
            FormattingInterface.__init__(self, multiFormat, format)
            SpellCheckTextCtrlMixin.__init__(self)

        def ForceExpandEvent(self):
            _expand_event(self)

    class FormattedTextCtrl(InputBox, SpellCheckTextCtrlMixin, FormattingInterface):
        def __init__(self, parent, style = 0, value = '', multiFormat = True, format = None, validator = wx.DefaultValidator):
            InputBox.__init__(self, parent, wx.ID_ANY, value, wx.DefaultPosition, wx.DefaultSize, style | formattedstyle, validator, value)
            FormattingInterface.__init__(self, multiFormat, format)
            SpellCheckTextCtrlMixin.__init__(self)

else:
    class FormattedExpandoTextCtrl(ExpandoTextCtrl, FormattingInterface):
        def __init__(self, parent, style = 0, value = '', multiFormat = True, format = None, validator = wx.DefaultValidator):
            ExpandoTextCtrl.__init__(self, parent, wx.ID_ANY, value, wx.DefaultPosition, wx.DefaultSize, style | formattedstyle, validator, value)
            FormattingInterface.__init__(self, multiFormat, format)

        def HitTestSuggestions(self, *a, **k):
            return -1, []

        def GetWordAtPosition(self, *a, **k):
            return None

        def GetReqHeight(self):
            return self.GetBestSize().y

        def ForceExpandEvent(self):
            _expand_event(self)

    class FormattedTextCtrl(InputBox, FormattingInterface):
        def __init__(self, parent, style = 0, value = '', multiFormat = True, format = None, validator = wx.DefaultValidator):
            InputBox.__init__(self, parent, wx.ID_ANY, value, wx.DefaultPosition, wx.DefaultSize, style | formattedstyle, validator, value)
            FormattingInterface.__init__(self, multiFormat, format)

        def GetReqHeight(self):
            return self.GetBestSize().y

def add_rtf_methods(cls):
    def GetFormattedValue(self):
        if wxMSW:
            rtf, plaintext = cls.GetRTF(self), cls.GetValue(self)
            return fmtstr(rtf=rtf, plaintext=plaintext)
        else:
            return fmtstr(plaintext=cls.GetValue(self))

    cls.GetFormattedValue = GetFormattedValue

    def SetFormattedValue(self, fmtstr):
        try:
            rtf = fmtstr.format_as('rtf')
        except FormattingException:
            cls.SetValue(self, fmtstr.format_as('plaintext'))
        else:
            cls.SetRTF(self, rtf)

    cls.SetFormattedValue = SetFormattedValue

add_rtf_methods(FormattedExpandoTextCtrl)
add_rtf_methods(FormattedTextCtrl)
