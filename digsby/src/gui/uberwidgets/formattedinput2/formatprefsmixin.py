from gui.textutil import default_font
from gui.skin.skinparse import makeFont
from util import try_this
from gui.uberwidgets.formattedinput2.formattedinput import FormattedInput


import wx
from gui.uberwidgets.formattedinput2.fontutil import StyleToDict, TupleToFont
from common import setpref, pref
from traceback import print_exc



#'profile.formatting' if self.aimprofile else 'messaging.default_style',

def StyleFromPref(prefname):

    try:
        stylepref = pref(prefname)

        if isinstance(stylepref, basestring):
            style = dict(Font = makeFont(stylepref))
        else:
            style = dict(stylepref)
    except Exception:
        print_exc()
        style = {}

    if type(style['Font']) is tuple:
        try:
            font = TupleToFont(style['Font'])
        except Exception:
            print_exc()
            font = try_this(lambda: makeFont('Arial 10'), default_font())
    else:
        font = style['Font']
    fgc  = try_this(lambda: wx.Colour(*style['TextColour']), None) or wx.BLACK #@UndefinedVariable
    bgc  = try_this(lambda: wx.Colour(*style['BackgroundColour']), None) or wx.WHITE #@UndefinedVariable

    return wx.TextAttr(fgc, bgc, font)

class FormatPrefsMixin(object):

    def SaveStyle(self, prefname):
        style = StyleToDict(self.tc.GetStyle(0)[1])
        from pprint import pformat
        print 'saving style:\n%s' % pformat(style)
        setpref(prefname, style)

    def WhenDefaultLayoutChange(self,src,pref,old,new):

    #        if self.GetStyleAsDict() == old:
        self.LoadStyle()

    def LoadStyle(self, prefname):
        self.tc.SetFormat_Single(StyleFromPref(prefname))

class PrefInput(FormattedInput, FormatPrefsMixin):
    def __init__(self,
                 parent,
                 value     = '',
                 autosize = True,
                 formatOptions = None,
                 multiFormat = True,
                 showFormattingBar = True,
                 rtl = False,
                 skin = None,
                 entercallback = None,
                 validator = wx.DefaultValidator,
                 formatpref = None):


        FormattedInput.__init__(self,
                                parent,
                                value = value,
                                autosize = autosize,
                                formatOptions = formatOptions,
                                multiFormat = multiFormat,
                                showFormattingBar = showFormattingBar,
                                rtl = rtl,
                                skin = skin,
                                validator = validator)

        self.formatpref = formatpref
        if formatpref is not None:
            self.LoadStyle(formatpref) #'messaging.default_style'
