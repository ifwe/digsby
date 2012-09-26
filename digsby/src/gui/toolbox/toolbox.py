'''
GUI utilities.
'''
from __future__ import with_statement
from __future__ import division
import config
import functools
import wx, struct
from wx import GetTopLevelWindows, Point, Size
from logging import getLogger; log = getLogger('gui.util')
from traceback import print_exc
from PIL import Image, ImageDraw, ImageFont
from ConfigParser import ConfigParser
import sys
from collections import defaultdict
from time import clock as time_clock
from gui.toolbox.monitor import Monitor
import cgui, new
import simplejson as json
import os.path

# adds methods to Bitmap, Image, etc...
import imagefx #@UnusedImport

wxMSW = 'wxMSW' in wx.PlatformInfo

# colors in skin YAML can start with this string
color_prefix = '0x'

def __repr__(self):
    '''wxBitmap repr showing its .path, if it has one.'''

    try:
        path = getattr(self, 'path', '')
        return '<wxBitmap %d%s>' % (id(self), (' '+os.path.normpath(path)) if path else '')
    except Exception:
        return '<wxBitmap %d>' % id(self)

wx.Bitmap.__repr__ = __repr__
del __repr__

# convenience method for removing all of a wxMenu's items
wx.Menu.RemoveAllItems = lambda self: [self.RemoveItem(item) for item in self.GetMenuItems()]

wx.Window.Tip = property(lambda self: self.GetToolTip().GetTip(),
                         lambda self, tip: self.SetToolTip(wx.ToolTip(tip)))

def check_destroyed(ctrl):
    if wx.IsDestroyed(ctrl):
        code = sys._getframe(1).f_code
        print >> sys.stderr, 'WARNING: destroyed object being used (%s in %s:%d)' % \
             (code.co_name, code.co_filename, code.co_firstlineno)
        return True
    return False

################################################################################
if wxMSW:
    import ctypes
    from ctypes import byref, WinError
    from ctypes.wintypes import UINT, POINT, RECT
    user32 = ctypes.windll.user32

    class WINDOWPLACEMENT(ctypes.Structure):
        _fields_ = [('length', UINT),
                    ('flags', UINT),
                    ('showCmd', UINT),
                    ('ptMinPosition', POINT),
                    ('ptMaxPosition', POINT),
                    ('rcNormalPosition', RECT)]


    def GetWindowPlacement(win):
        hwnd = win.GetHandle()
        p = WINDOWPLACEMENT()
        p.length = ctypes.sizeof(WINDOWPLACEMENT)
        if not user32.GetWindowPlacement(hwnd, byref(p)):
            raise WinError()

        return windowplacement_todict(p)

    def SetWindowPlacement(win, d):
        d2 = GetWindowPlacement(win)
        d2['rcNormalPosition'] = d['rcNormalPosition']
        d2['showCmd'] |= 0x0020 # SWP_FRAMECHANGED
        d = d2

        p = windowplacement_fromdict(d)
        if not user32.SetWindowPlacement(win.Handle, byref(p)):
            raise WinError()

    def windowplacement_todict(p):
        return dict(flags = p.flags,
                    showCmd = p.showCmd,
                    ptMinPosition = (p.ptMinPosition.x, p.ptMinPosition.y),
                    ptMaxPosition = (p.ptMaxPosition.y, p.ptMaxPosition.y),
                    rcNormalPosition = (p.rcNormalPosition.left, p.rcNormalPosition.top, p.rcNormalPosition.right, p.rcNormalPosition.bottom))

    def windowplacement_fromdict(d):
        p = WINDOWPLACEMENT()
        p.length = ctypes.sizeof(WINDOWPLACEMENT)

        p.showCmd = int(d['showCmd'])

        p.ptMinPosition = POINT()
        p.ptMinPosition.x = int(d['ptMinPosition'][0])
        p.ptMinPosition.y = int(d['ptMinPosition'][1])

        p.ptMaxPosition = POINT()
        p.ptMaxPosition.x = int(d['ptMaxPosition'][0])
        p.ptMaxPosition.y = int(d['ptMaxPosition'][1])

        p.rcNormalPosition = RECT()
        p.rcNormalPosition.left, p.rcNormalPosition.top, p.rcNormalPosition.right, p.rcNormalPosition.bottom = d['rcNormalPosition']

        return p

################################################################################


def DeleteRange(textctrl, b, e):
    if b != e:
        with textctrl.Frozen():
            textctrl.Remove(b, e)
            textctrl.InsertionPoint = b

def DeleteWord(textctrl):
    '''
    Deletes the last word (or part of word) at the cursor.

    Commonly bound to Ctrl+Backspace.

    TODO: ignores punctuation--like

        this.is.a.dotted.word[CTRL+BACKSPACE]

    will delete the whole line. is that what we want?
    '''

    i = textctrl.InsertionPoint
    s = textctrl.Value

    if not s or i < 1: return

    e = i
    while s[i-1] == ' ' and i != 0:
        i -= 1

    b = s.rfind(' ', 0, i) + 1 if i != 0 else 0

    if b == -1:
        b = 0

    DeleteRange(textctrl, b, e)

def DeleteRestOfLine(textctrl):
    '''
    Deletes from the cursor until the end of the line.

    Emulates Control+K from many Linux and Mac editors.
    '''

    i = textctrl.InsertionPoint

    # find the next newline
    j = textctrl.Value[i:].find('\n')
    j = textctrl.LastPosition if j == -1 else j + i

    # if the cursor is on the last character of the line before a newline,
    # just delete the newline
    if i == j and j + 1 <= textctrl.LastPosition:
        j += 1

    DeleteRange(textctrl, i, j)



if 'wxMac' in wx.PlatformInfo:
    AutoDC = wx.PaintDC
else:
    AutoDC = wx.AutoBufferedPaintDC


# def to_icon(bitmap):
#     return wx.IconFromBitmap(bitmap.WXB)
def to_icon(bitmap, size = None):
    if isinstance(bitmap, wx.Image):
        bitmap = wx.BitmapFromImage(bitmap)

    bitmap = bitmap.WXB

    return wx.IconFromBitmap(bitmap.Resized(size) if size is not None else bitmap)

wx.Rect.Pos        = new.instancemethod(cgui.RectPosPoint, None, wx.Rect)


from cgui import Subtract as cgui_Subtract

def Rect_Subtract(r, left = 0, right = 0, up = 0, down = 0):
    r.x, r.y, r.width, r.height = cgui_Subtract(r, left, right, up, down)
    return r

def Rect_SubtractCopy(r, left = 0, right = 0, up = 0, down = 0):
    return cgui_Subtract(r, left, right, up, down)

wx.Rect.Subtract = new.instancemethod(Rect_Subtract, None, wx.Rect)
wx.Rect.SubtractCopy = new.instancemethod(Rect_SubtractCopy, None, wx.Rect)
del Rect_Subtract


wx.Rect.AddMargins = new.instancemethod(cgui.RectAddMargins, None, wx.Rect)

# methods for getting/setting "always on top" state for top level windows
#

def GetOnTop(toplevelwin):
    'Returns True if this window is always on top, False otherwise.'
    s = toplevelwin.WindowStyleFlag

    return bool(s & wx.STAY_ON_TOP)

def SetOnTop(toplevelwin, ontop):
    '''Sets this window's "always on top" state.'''

    if ontop:
        flag = toplevelwin.WindowStyleFlag |  wx.STAY_ON_TOP
    else:
        flag = toplevelwin.WindowStyleFlag & ~wx.STAY_ON_TOP

    toplevelwin.WindowStyleFlag = flag

def ToggleOnTop(toplevelwin):
    toplevelwin.OnTop = not toplevelwin.OnTop

wx.TopLevelWindow.OnTop = property(GetOnTop, SetOnTop)
wx.TopLevelWindow.ToggleOnTop = ToggleOnTop


class FocusTimer(wx.Timer):
    def __init__(self, draw = False):
        wx.Timer.__init__(self)
        self.draw = draw

    def Notify(self):
        c = self.last_focused = wx.Window.FindFocus()
        r = c.ScreenRect if c is not None else wx.Rect()
        print 'wx.Window.FindFocus() ->', c, 'at', r

        if self.draw:
            dc = wx.ScreenDC()
            p = wx.RED_PEN
            p.SetWidth(4)
            dc.SetPen(p)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangleRect(r)


def trackfocus(update_ms = 2000, draw = False):
    t = FocusTimer(draw = draw)
    t.Start(update_ms)
    return t

#
# patch hcenter and vcenter methods into wxRect for centering images/rectangles
#

def VCenter(rect, img):
    return rect.y + rect.height / 2 - img.Height / 2

def HCenter(rect, img):
    return rect.x + rect.width / 2 - img.Width / 2

def VCenterH(rect, h):
    return rect.y + rect.height / 2 - h / 2

def HCenterW(rect, w):
    return rect.x + rect.width / 2 - w / 2

def CenterPoint(rect, pt):
    w, h = pt
    return rect.x + rect.HCenterW(w), rect.y + rect.VCenterH(h)

wx.Rect.VCenter = VCenter
wx.Rect.HCenter = HCenter
wx.Rect.VCenterH = VCenterH
wx.Rect.HCenterW = HCenterW
wx.Rect.CenterPoint = CenterPoint

Image.Image.Width  = property(lambda image: image.size[0])
Image.Image.Height = property(lambda image: image.size[1])

class progress_dialog(object):
    'Threadsafe progress dialog.'

    def __init__(self, message, title):
        self.stopped = False

        # callback to the GUI thread for dialog creation
        wx.CallAfter(self.create_dialog, message, title)

    def create_dialog(self, message, title):
        # dialog will not have a close button or system menu
        self.dialog = d = wx.Dialog(None, -1, title, style = wx.CAPTION)

        d.Sizer = s = wx.BoxSizer(wx.VERTICAL)
        self.gauge = wx.Gauge(d, -1, style = wx.GA_HORIZONTAL)

        s.Add(wx.StaticText(d, -1, message), 0, wx.EXPAND | wx.ALL, 10)
        s.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 10)

        self.timer = wx.PyTimer(self.on_timer)
        self.timer.StartRepeating(300)

        self.gauge.Pulse()
        s.Layout()
        d.Fit()
        d.CenterOnScreen()
        d.Show()

    def on_timer(self):
        if self.stopped:
            self.dialog.Destroy()
            self.timer.Stop()
            del self.dialog
            del self.timer
        else:
            self.gauge.Pulse()

    def stop(self):
        self.stopped = True

def yes_no_prompt(title, text, default = True):
    flags = wx.NO_DEFAULT * (not default)
    result = wx.MessageBox(text, title, style = wx.YES_NO | flags)
    if result == wx.YES:
        return True
    elif result == wx.NO:
        return False
    else:
        return None

def ShowImage(b, title = ''):
    '''
    Displays the given wxImage, wxBitmap, PIL image, or skin region on screen
    in a frame.
    '''
    title = title + ' '  + repr(b)

    b = getattr(b, 'WXB', b)

    f = wx.Frame(None, title = title, style = wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)
    if isinstance(b, wx.Bitmap):
        f.SetClientRect((0, 0, b.Width, b.Height))
        def paint_bitmap(e):
            dc = wx.AutoBufferedPaintDC(f)
            dc.Brush, dc.Pen = wx.CYAN_BRUSH, wx.TRANSPARENT_PEN
            dc.DrawRectangleRect(f.ClientRect)
            dc.DrawBitmap(b, 0, 0, True)
        f.Bind(wx.EVT_PAINT, paint_bitmap)
        f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    elif isinstance(b, wx.Colour):
        f.SetBackgroundColour(b)
        f.SetClientRect((0, 0,  200, 200))
    else:
        f.SetClientRect((0, 0, 200, 200))
        def paint_skinregion(e):
            dc = wx.AutoBufferedPaintDC(f)
            dc.Brush, dc.Pen = wx.WHITE_BRUSH, wx.TRANSPARENT_PEN
            dc.DrawRectangleRect(f.ClientRect)
            b.Draw(dc, f.ClientRect)
        f.Bind(wx.EVT_PAINT, paint_skinregion)
        f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

    f.CenterOnScreen()
    f.Show()

# allow ".Show()" on any image or color object to display it on screen
Image.Image.Show = wx.Image.Show = wx.Bitmap.Show = wx.Icon.Show = wx.Colour.Show = ShowImage

def wx_prop(attrname, field='Value', set_cleanup=lambda x:x, get_cleanup=lambda x:x):
    def set(self, val):
        setattr(getattr(self, attrname), field, set_cleanup(val))
    def get(self):
        return get_cleanup(getattr(getattr(self, attrname), field))
    return property(get, set)


def TextEntryDialog(message, caption = '', default_value = '', password = False, limit=1024):
    style = wx.OK | wx.CANCEL | wx.CENTRE
    if password:
        style |= wx.TE_PASSWORD

    TED = wx.TextEntryDialog(None, message, caption, default_value, style = style)
    return TED

def GetTextFromUser_FixInput(val, limit):
    if limit is not None:
        if len(val) > limit:
            print >>sys.stderr, "Data is %d bytes long, cutting to %d bytes" % (len(val), limit)
            val = val[:limit]

    return val

def GetTextFromUser(message, caption = '', default_value = '', password = False, limit=1024):
    try:
        TED = TextEntryDialog(message, caption, default_value, password, limit)
        id = TED.ShowModal()
        val = TED.Value
    finally:
        TED.Destroy()

    val = GetTextFromUser_FixInput(val, limit)
    return val if id == wx.ID_OK else None

def make_okcancel(name, cls):
    class okcancel_class(cls):
        'Wraps any component in a OK/Cancel dialog.'

        dialog_style = wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX

        def __init__(self, parent, id=-1,
                    title=None,
                    ok_caption = '',
                    cancel_caption = '',
                     style = dialog_style):

            if title is None:
                title = _("Confirm")

            cls.__init__(self, parent, id, title=title, style=style)

            self.OKButton = ok     = wx.Button(self, wx.ID_OK, ok_caption)
            cancel = wx.Button(self, wx.ID_CANCEL, cancel_caption)

            if config.platform == 'win':
                button_order = [ok, cancel]
            else:
                button_order = [cancel, ok]

            self._button_sizer = hbox = wx.BoxSizer(wx.HORIZONTAL)

            if hasattr(self, 'ExtraButtons'):
                ctrl = self.ExtraButtons()
                if ctrl is not None:
                    hbox.Add(ctrl, 0, wx.EXPAND | wx.ALL, 5)

            hbox.AddStretchSpacer(1)

            for button in button_order:
                hbox.Add(button, 0, wx.ALL, 5)

            vbox = wx.BoxSizer(wx.VERTICAL)
            vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 7)
            self.vbox = vbox

            self.SetSizer(vbox)

            self.Layout()
            ok.SetDefault()

        def set_component(self, c, border=7, line=False):
            self.vbox.Insert(0, c, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border)
            if line:
                self.vbox.Insert(1, wx.StaticLine(self), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, border)

            self.Layout()

        @property
        def ButtonSizer(self):
            return self._button_sizer

    okcancel_class.__name__ = name
    return okcancel_class

OKCancelDialog = make_okcancel('OKCancelDialog', wx.Dialog)
OKCancelFrame = make_okcancel('OKCancelFrame', wx.Frame)

class Link(wx.HyperlinkCtrl):
    def __init__(self, parent, label, url):
        wx.HyperlinkCtrl.__init__(self, parent, -1, label, url)
        self.HoverColour = self.VisitedColour = self.NormalColour


class NonModalDialogMixin(object):
    def ShowWithCallback(self, cb=None):
        self.cb = cb
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Show()
        self.Raise()

    def on_button(self, e):
        ok = e.Id == wx.ID_OK
        self.Hide()
        cb, self.cb = self.cb, None
        if cb is not None:
            import util
            with util.traceguard:
                cb(ok)

        self.Destroy()

class SimpleMessageDialog(OKCancelDialog, NonModalDialogMixin):
    def __init__(self, parent, title, message,
                 icon, ok_caption='', cancel_caption='',
                 style=None,
                 link=None,
                 wrap=None):

        if style is None:
            style = self.dialog_style

        if link is not None:
            def ExtraButtons():
                self._panel = wx.Panel(self)
                return Link(self, link[0], link[1])
            self.ExtraButtons = ExtraButtons

        OKCancelDialog.__init__(self, parent, title=title,
                ok_caption=ok_caption, cancel_caption=cancel_caption,
                style=style)

        self.icon = icon
        if icon is not None:
            self.SetFrameIcon(self.icon)

        p = self._panel
        p.Bind(wx.EVT_PAINT, self.OnPanelPaint)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        p.SetBackgroundColour(wx.WHITE)

        static_text = wx.StaticText(p, -1, message)

        sizer.AddSpacer((60, 20))
        sizer.Add(static_text, 1, wx.EXPAND)

        main_sizer.Add(sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add((5,5))
        p.SetSizer(main_sizer)

        self.set_component(p, border=0)

        if wrap is not None:
            static_text.Wrap(wrap)

        self.Fit()


    def OnPanelPaint(self, e):
        dc = wx.PaintDC(self._panel)

        icon = self.icon
        if icon is not None:
            dc.DrawBitmap(icon, 20, 14, True)

    def ExtraButtons(self):
        self._panel = wx.Panel(self)

class UpgradeDialog(SimpleMessageDialog):
    dialog_style = SimpleMessageDialog.dialog_style & ~wx.CLOSE_BOX
    def __init__(self, *a, **k):
        super(UpgradeDialog, self).__init__(*a, **k)
        self.SetEscapeId(wx.ID_NONE)

    @classmethod
    def show_dialog(cls, parent, title, message, success=None):
        wx.CallAfter(cls.do_show_dialog, parent, title, message, success)

    @classmethod
    def do_show_dialog(cls, parent, title, message, success=None):
        dialog = cls(parent, title=title, message=message)
        dialog.ShowWithCallback(success)

try:
    from cgui import FindTopLevelWindow
except ImportError:
    print >> sys.stderr, "WARNING: using slow FindTopLevelWindow"
    def FindTopLevelWindow(window):
        return window if window.TopLevel else FindTopLevelWindow(window.Parent)

# wx.Window.GetNormalRect : return the non maximized dimensions of a window
try:
    from cgui import GetNormalRect
except ImportError:
    def GetNormalRect(win):
        return win.Rect


wx.WindowClass.NormalRect = property(GetNormalRect)
wx.WindowClass.GetNormalRect = new.instancemethod(GetNormalRect, None, wx.WindowClass)

wx.WindowClass.Top = property(FindTopLevelWindow)

def edit_list(parent=None, obj_list=None, title="Editing List"):

    if not isinstance(obj_list, list):
        obj_list = []

    diag = OKCancelDialog(wx.GetTopLevelParent(parent), title=title)
    t = type(obj_list[0]) if len(obj_list) else None
    textctrl = wx.TextCtrl(diag, value = ','.join([str(i) for i in obj_list]))
    diag.set_component(textctrl)
    textctrl.MinSize = (300, -1)
    diag.Fit()
    textctrl.SetFocus()
    textctrl.SetInsertionPointEnd()

    result = diag.ShowModal() == wx.ID_OK

    if t is None:
        t = int if all([s.isdigit() for s in textctrl.Value.split(',')]) else str

    return result, [t(s.strip()) for s in textctrl.Value.split(',')] if len(textctrl.Value) else []

try:
    import wx.gizmos as gizmos
except ImportError:
    def edit_string_list(parent=None, obj_list=['one', 'two', 'three'], title="Editing List"):
        log.critical('no wx.gizmos')
        return edit_list(parent, obj_list, title)
else:
    def edit_string_list(parent=None, obj_list=['one', 'two', 'three'], title="Editing List"):
        diag = OKCancelDialog(wx.GetTopLevelParent(parent), title=title)
        t = type(obj_list[0])
        elb = gizmos.EditableListBox(diag, -1, title)
        elb.SetStrings([unicode(elem) for elem in obj_list])
        diag.set_component(elb)
        return diag.ShowModal() == wx.ID_OK, [t(s) for s in elb.GetStrings()]

from wx import Color, ColourDatabase, NamedColor
from binascii import unhexlify
from types import NoneType

def get_wxColor(c):
    if isinstance(c, (NoneType, Color)):
        return c

    elif isinstance(c, basestring):
        if c[0:2].lower() == color_prefix.lower():
            # a hex string like "0xabcdef"
            return Color(*(struct.unpack("BBB", unhexlify(c[2:8])) + (255,)))

        elif ColourDatabase().Find(c).Ok():
            # a color name
            return NamedColor(c)

        else:
            try: c = int(c)
            except ValueError: pass

    if isinstance(c, int):
        # an integer
        return Color((c >> 16) & 0xff, (c >> 8) & 0xff, c & 0xff, (c >> 24) or 255)

    raise ValueError('error: %r is not a valid color' % c)

colorfor = get_wxColor

LOCAL_SETTINGS_FILE = 'digsbylocal.ini'

class MyConfigParser(ConfigParser):
    def save(self):
        import util
        with util.traceguard:
            parent = local_settings_path().parent
            if not parent.isdir():
                parent.makedirs()

        lsp = local_settings_path()
        try:
            with open(lsp, 'w') as f:
                self.write(f)
        except Exception, e:
            log.error('Error saving file %r. Error was: %r', lsp, e)

    def iteritems(self, section):
        return ((k, self.value_transform(v)) for k, v in ConfigParser.items(self, section))

    def items(self, section):
        return list(self.iteritems())

    def _interpolate(self, section, option, rawval, vars):
        try:
            value = ConfigParser._interpolate(self, section, option, rawval, vars)
        except TypeError:
            value = rawval
        return value

    def value_transform(self, v):
        import util
        return {'none': None,
                'true': True,
                'false': False}.get(util.try_this(lambda: v.lower(), None), v)

def local_settings_path():
    import stdpaths
    return stdpaths.userlocaldata / LOCAL_SETTINGS_FILE

_global_ini_parser = None

def local_settings():
    global _global_ini_parser

    if _global_ini_parser is None:
        _global_ini_parser = MyConfigParser()
        lsp = local_settings_path()
        try:
            _global_ini_parser.read(lsp)
        except Exception, e:
            log.error('There was an error loading file %r. The error was %r.', lsp, e)

    return _global_ini_parser

def getDisplayHashString():
    '''
    Returns a unique string for the current monitor/resolution configuration.

    Used below in save/loadWindowPos.

    The rationale is that using things like Remote Desktop can result in the
    window remembering a location that won't work on a differently sized
    display.  This way you only position the window once on each display
    configuration and be done with it.
    '''

    return '{%s}' % ', '.join('<(%s, %s): %sx%s>' % tuple(m.Geometry) for m in Monitor.All())

def saveWindowPos(win, uniqueId=""):
    '''
    Saves a window's position to the config file.
    '''

    cfg = local_settings()
    section = windowId(win.Name, uniqueId)
    if not cfg.has_section(section):
        cfg.add_section(section)

    if wxMSW:
        placement = GetWindowPlacement(win)

        # on win7, if a window is Aero Snapped, GetWindowPlacement will return
        # it's "unsnapped" size. we want to save the size of the window as it
        # is now, though--so grab the size from win.Rect and use that.
        if cgui.isWin7OrHigher() and not win.IsMaximized() and not win.IsIconized():
            placement_set_size(placement, win.Rect.Size)

        cfg.set(section, 'placement', json.dumps(placement))
    else:
        rect = GetNormalRect(win)
        sz, p = rect.GetSize(), rect.GetPosition()

        for k, v in [("x", p.x),
                     ("y", p.y),
                     ("w", sz.width),
                     ("h", sz.height),
                     ('maximized', win.IsMaximized())]:
            cfg.set(section, k, str(v))

    cfg.save()

defSizes = {
    'Buddy List': (280, 600),
    'IM Window':  (420, 330),
}

def windowId(windowName, uniqueId):
    from common import profile

    username = getattr(profile, 'username', None)
    if not username:
        username = getattr(wx.FindWindowByName('Digsby Login Window'), 'username', '_')
    return ' '.join([windowName, uniqueId, username, getDisplayHashString()])

def placement_set_size(placement, size):
    np = placement['rcNormalPosition']
    right  = np[0] + size.width
    bottom = np[1] + size.height
    placement['rcNormalPosition'] = [np[0], np[1], right, bottom]

def preLoadWindowPos(windowName, uniqueId="", position_only = False, defaultPos = None, defaultSize = None):
    # save based on classname, and any unique identifier that is specified
    section = windowId(windowName, uniqueId)

    if defaultPos is not None:
        doCenter = defaultPos == 'center'
        hasDefPos = not doCenter
    else:
        hasDefPos = False
        doCenter = False


    size = defaultSize if defaultSize is not None else wx.DefaultSize#(450, 400)
    pos  = defaultPos  if hasDefPos else wx.DefaultPosition
    style = 0

    try:
        cfg = local_settings()
        hassection = cfg.has_section(section)
    except Exception:
        print_exc()
        hassection = False

    placement = None
    if wxMSW:
        if hassection:
            import util
            with util.traceguard:
                placement = json.loads(cfg.get(section, 'placement'))

                if position_only:
                    placement_set_size(placement, size)

    if hassection and not position_only:
        try:
            size = Size(cfg.getint(section, "w"), cfg.getint(section, "h"))
        except Exception:
            pass
            #TODO: this isn't expected to work anymore with IM windows, needs to
            #be removed once everything else is moved to use SetPalcement
            #print_exc()

    if doCenter:
        mon = Monitor.GetFromRect(wx.RectPS(wx.Point(0, 0), size)) #@UndefinedVariable
        pos = wx.Point(*mon.ClientArea.CenterPoint(size))

    if hassection:
        try:
            pos = Point(cfg.getint(section, "x"), cfg.getint(section, "y"))
        except Exception:
            pass
            #TODO: this isn't expected to work anymore with IM windows, needs to
            #be removed once everything else is moved to use SetPalcement
            #print_exc()

    import util
    max = util.try_this(lambda: cfg.getboolean(section, "maximized"), False) if hassection else False

    if max:
        style |= wx.MAXIMIZE

    return dict(style = style, size = size, pos = pos), placement

def loadWindowPos(win, uniqueId="", position_only = False, defaultPos = None, defaultSize = None):
    '''
    Loads a window's position from the default config file.
    '''

    wininfo, placement = preLoadWindowPos(win.Name, uniqueId, position_only, defaultPos, defaultSize or win.Size)

    if placement is not None:
        SetWindowPlacement(win, placement)
    else:
        if not position_only:
            win.SetRect(wx.RectPS(wininfo['pos'], wininfo['size']))
        else:
            win.Position = wininfo['pos']
#        if wininfo['style'] & wx.MAXIMIZE:
#            win.Maximize()

    win.EnsureInScreen()

def persist_window_pos(frame, close_method=None, unique_id="", position_only = False, defaultPos = None, defaultSize = None, nostack = False):
    '''
    To make a frame remember where it was, call this function on it in its
    constructor.
    '''
    def _persist_close(e):
        saveWindowPos(frame, unique_id)
        close_method(e) if close_method is not None else e.Skip(True)

    frame.Bind(wx.EVT_CLOSE, _persist_close)
    loadWindowPos(frame, unique_id, position_only, defaultPos = defaultPos, defaultSize = defaultSize)
    if nostack:
        frame.EnsureNotStacked()

def TransparentBitmap(size):
    w, h = max(size[0], 1), max(size[1], 1)
    return wx.TransparentBitmap(w, h)

def toscreen(bmap, x, y):
    wx.ScreenDC().DrawBitmap(bmap, x, y)

def bbind(window, **evts):
    '''
    Shortcut for binding wxEvents.

    Instead of:

    self.Bind(wx.EVT_PAINT, self.on_paint)
    self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_paint_background)
    self.Bind(wx.EVT_SET_FOCUS, self.on_focus)

    Use this:

    self.BBind(PAINT = self.on_paint,
               ERASE_BACKGROUND = self.on_paint_background,
               SET_FOCUS, self.on_focus)
    '''

    bind = window.Bind
    for k, v in evts.iteritems():
        bind(getattr(wx, 'EVT_' + k), v)

wx.WindowClass.BBind = bbind

def EnsureInScreen(win, mon=None, client_area=True):
    mon = Monitor.GetFromWindow(win)
    if mon:
        rect = mon.ClientArea if client_area else mon.Geometry
        win.SetRect(rect.Clamp(win.Rect))
    else:
        win.CentreOnScreen()

wx.WindowClass.EnsureInScreen = EnsureInScreen

def FitInScreen(win, mon=None):
    '''
    Like wx.Window.Fit(), except also ensures the window is within the client
    rectangle of its current Display.
    '''
    win.Fit()
    EnsureInScreen(win, mon)

wx.WindowClass.FitInScreen = FitInScreen

def build_button_sizer(save, cancel = None, border=5):
    'Builds a standard platform specific button sizer.'
    # Only because wxStdDialogButtonSizer.Realize crashed the Mac
    sz = wx.BoxSizer(wx.HORIZONTAL)
    sz.AddStretchSpacer(1)

    addbutton = lambda b: sz.Add(b, 0, (wx.ALL & ~wx.TOP) | wx.ALIGN_RIGHT, border)

    mac = 'wxMac' in wx.PlatformInfo
    import util.primitives.funcs as funcs
    if save and cancel:
        funcs.do(addbutton(b) for b in ([cancel, save] if mac else [save, cancel]))
    else:
        addbutton(save)
    return sz

_tinyoffsets = ((-1, 0), (1, 0), (1, -1), (1, 1), (-1, -1), (-1, 1))

def draw_tiny_text(image, text, outline = 'black', fill = 'white'):
    image = getattr(image, 'PIL', image).copy()

    # Load the pixel font.
    font = load_tiny_font()
    if font is None:
        return image

    drawtext = ImageDraw.Draw(image).text
    size     = font.getsize(text)

    x, y = image.size[0] - size[0], image.size[1] - size[1]

    if outline:
        # shift the color one pixel in several directions to create an outline
        for a, b in _tinyoffsets:
            drawtext((x+a, y+b), text, fill = outline, font = font)

    drawtext((x, y), text, fill = fill, font = font)

    return image

_tinyfont = None

def load_tiny_font():
    global _tinyfont
    if _tinyfont == -1:
        # There was an error loading the pixel font before.
        return None
    elif _tinyfont is None:
        try:
            import locale
            from gui import skin
            _tinyfont = ImageFont.truetype((skin.resourcedir() / 'slkscr.ttf').encode(locale.getpreferredencoding()), 9)
        except Exception:
            print_exc()
            _tinyfont = -1
            return None

    return _tinyfont

#@lru_cache(10)
def add_image_text(wxbitmap, text):
    return draw_tiny_text(wxbitmap, unicode(text)).WXB

def rect_with_negatives(rect, boundary):
    '''
    Allows rectangles specified in negative coordinates within some boundary.

    Parameters:
    rect: a sequence of four numbers specifying a rectangle
    boundary: a sequence of two numbers, a width and height representing a BoundaryError

    Returns a sequence of four numbers, a new rectangle which takes any negative
    numbers from the original rectangle and adds them to the boundary rectangle.
    '''

    if not len(rect) == 4 or not len(boundary) == 2: raise TypeError('parameters are (x,y,w,h) and (w,h)')
    ret = list(rect)
    for i in xrange(len(ret)):
        if ret[i] < 0:
            ret[i] += boundary[i%2]

    return ret

class Frozen(object):
    '''
    "with" statement context manager for freezing wx.Window GUI elements
    '''

    def __init__(self, win):
        self.win = win

    def __enter__(self):
        self.win.Freeze()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.win.Thaw()
        del self.win

wx.WindowClass.Frozen = lambda win: Frozen(win)
wx.WindowClass.FrozenQuick = lambda win: Frozen(win)

from wx import IconFromBitmap
GetMetric = wx.SystemSettings.GetMetric

_win7bigicon = None

def SetFrameIcon(frame, bitmap):
    "Given any Bitmap/Image/PILImage, sets this frame's icon."

    small_w, small_h = GetMetric(wx.SYS_SMALLICON_X), GetMetric(wx.SYS_SMALLICON_Y)
    big_w, big_h     = GetMetric(wx.SYS_ICON_X), GetMetric(wx.SYS_ICON_Y)

    if small_w == -1:
        small_w = 16
    if small_h == -1:
        small_h = 16

    if big_w == -1:
        big_w = 32
    if big_h == -1:
        big_h = 32

    if isinstance(bitmap, wx.IconBundle):
        bundle = bitmap
    elif isinstance(bitmap, list):
        bundle = wx.IconBundle()
        for b in bitmap:
            if isinstance(b, wx.Icon):
                bundle.AddIcon(b)
            else:
                bundle.AddIcon(IconFromBitmap(b.PIL.ResizedSmaller(big_w).ResizeCanvas(big_w, big_h).WXB))
    else:
        small_bitmap = bitmap.PIL.ResizedSmaller(small_w).ResizeCanvas(small_w, small_h).WXB

        if cgui.isWin7OrHigher():
            # On Windows 7, always use the Digsby icon for the 32x32 version.
            # this is so that our application icon in the taskbar always shows as the Digsby logo.
            global _win7bigicon
            if _win7bigicon is None:
                from gui import skin
                _win7bigicon = skin.get('AppDefaults.TaskBarIcon').PIL.ResizedSmaller(big_w).ResizeCanvas(big_w, big_h).WXB
            large_bitmap = _win7bigicon
        else:
            large_bitmap = bitmap.PIL.ResizedSmaller(big_w).ResizeCanvas(big_w, big_h).WXB

        bundle = wx.IconBundle()
        bundle.AddIcon(IconFromBitmap(large_bitmap))
        bundle.AddIcon(IconFromBitmap(small_bitmap))

    frame.SetIcons(bundle)

wx.TopLevelWindow.SetFrameIcon = SetFrameIcon


def snap_pref(win):
    'Makes a window obey the windows.sticky preference. (The window snaps to edges.)'

    from common import profile

    #needs to import snap to patch SetSnap into TopLevelWindow
    import gui.snap

    if profile.prefs:
        linked = profile.prefs.link('windows.sticky', win.SetSnap)

        def on_destroy(e):
            e.Skip()
            if e.EventObject is win:
                linked.unlink()

        win.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    else:
        raise Exception('profile.prefs is empty -- cannot observe')

def setuplogging(logfilename = 'digsby-testapp.log', level=None):
    import logging

    if level is None:
        level = logging.DEBUG

    # Setup log so it's visible
    logging.basicConfig(level=level,
                        filename=logfilename,
                        filemode='w')

    import logextensions
    console = logextensions.ColorStreamHandler()

    from main import ConsoleFormatter
    console.setFormatter(ConsoleFormatter())

    logging.getLogger().addHandler(console)

def OverflowShow(self, switch=True, genWidth = True):
    self.shouldshow=switch
    wx.Window.Show(self, switch)
    if genWidth: self.Parent.GenWidthRestriction(True)


def EnsureNotStacked(f, clz = None, offset = (20, 20)):
    '''
    Positions a top level window so that it is not directly stacked on
    top of another for which isinstance(window, clz)
    '''

    if clz is None:
        clz = f.__class__

    found = True
    top   = GetTopLevelWindows()
    pos   = f.Position

    while found:
        found = False

        for frame in top:
            if frame is not f and isinstance(frame, clz) and frame.IsShown() and frame.Position == pos:
                pos   = pos + offset
                found = True

    f.Position = pos

wx.TopLevelWindow.EnsureNotStacked = EnsureNotStacked



def AddInOrder(sizer, *order, **windows):
    if sizer and windows:
        for key in list(order):
            if key in windows:
                try:
                    sizer.Add(*windows[key])
                except Exception:
                    print >> sys.stderr, 'sizer', sizer
                    print >> sys.stderr, 'order', order
                    print >> sys.stderr, 'windows', windows
                    print >> sys.stderr, 'key', key
                    raise

def GetStartupDir():
    import stdpaths
    return stdpaths.userstartup

def ToScreen(rect, ctrl):
    r = wx.Rect(*rect)
    r.x, r.y = ctrl.ClientToScreen(r.TopLeft)
    return r

wx.Rect.ToScreen = ToScreen

from wx import TOP, BOTTOM, LEFT, RIGHT

def alignment_to_string(a):
    if a & TOP: s = 'upper'
    elif a & BOTTOM: s = 'lower'
    else: s = 'middle'

    if a & LEFT: s += 'left'
    elif a & RIGHT: s += 'right'
    else: s += 'center'

    return s

def prnt(*a):
    """
        Strings the arguments and pieces them together, separated with spaces
        The string is printed inbetween lines of 80 '='
    """
    print
    print '=' * 80
    print ' '.join(str(i) for i in a)
    print '=' * 80

if wxMSW:
    # use custom rich edit alignment flags -- wxLayoutDirection doesn't work
    # with rich text controls
    PFA_LEFT = 1
    PFA_RIGHT = 2
    PFA_CENTER = 3
    PFA_JUSTIFY = 4


    def set_rich_layoutdirection(ctrl, align):
        align = {wx.Layout_RightToLeft: PFA_RIGHT,
                 wx.Layout_LeftToRight: PFA_LEFT}[align]

        if cgui.SetRichEditParagraphAlignment(ctrl, align):
            ctrl.Refresh()

    def add_rtl_checkbox(ctrl, menu):
        '''
        Adds a checkbox when the menu is over the main input area for toggling
        a right to left reading order.

        ctrl is the control currently under the mouse
        menu is the menu we're updating
        '''
        # If we're over the main input area, add a checkbox for toggling RTL state.
        item = menu.AddCheckItem(_('Right To Left'), callback = lambda: toggle_layout_direction(ctrl))

        # The item is checked if RTL mode is on.
        item.Check(cgui.GetRichEditParagraphAlignment(ctrl) == PFA_RIGHT)

    def toggle_layout_direction(tc):
        'Toggles the layout direction of a control between right-to-left and left-to-right.'

#        alignment = PFA_RIGHT if cgui.GetRichEditParagraphAlignment(tc) == PFA_LEFT else PFA_LEFT
#
#        if not cgui.SetRichEditParagraphAlignment(tc, alignment):
#            log.warning('SetRichEditParagraphAlignment returned False')
#        else:
#            tc.Refresh()

        tc.SetRTL(not tc.GetRTL())

else:
    def add_rtl_checkbox(ctrl, menu):
        '''
        Adds a checkbox when the menu is over the main input area for toggling
        a right to left reading order.

        ctrl is the control currently under the mouse
        menu is the menu we're updating
        '''
        # If we're over the main input area, add a checkbox for toggling RTL state.
        item = menu.AddCheckItem(_('Right To Left'), callback = lambda: toggle_layout_direction(ctrl))

        # The item is checked if RTL mode is on.
        item.Check(ctrl.GetRTL()) #LayoutDirection == wx.Layout_RightToLeft)

    def toggle_layout_direction(tc):
        'Toggles the layout direction of a control between right-to-left and left-to-right.'

        if tc:
            tc.LayoutDirection = wx.Layout_RightToLeft if tc.LayoutDirection == wx.Layout_LeftToRight else wx.Layout_LeftToRight
            tc.Refresh()

def textctrl_hittest(txt, pos=None):
    if pos is None:
        pos = wx.GetMousePosition()

    hit, col, row = txt.HitTest(txt.ScreenToClient(pos))
    return txt.XYToPosition(col, row)

class Unshortener(object):
    def __init__(self, cb=None):
        self.urls = {}
        self.cb = cb

    def get_long_url(self, url):
        try:
            return self.urls[url]
        except KeyError:
            self.urls[url] = None

            def cb(longurl):
                self.urls[url] = longurl
                if self.cb:
                    self.cb()

            import util.net
            util.net.unshorten_url(url, cb)

def add_shortened_url_tooltips(txt):
    '''
    binds a mouse motion handler that detects when the mouse hovers over shortened urls,
    and shows the long version
    '''
    def update_url_tooltip(e=None):
        if e is not None:
            e.Skip()

        val = txt.Value
        import util.net
        i = textctrl_hittest(txt)
        tooltip = None
        for link, span in util.net.LinkAccumulator(val):
            if i < span[0] or i >= span[1]:
                continue
            if util.net.is_short_url(link):
                try:
                    shortener = txt._url_unshortener
                except AttributeError:
                    shortener = txt._url_unshortener = Unshortener(lambda: wx.CallAfter(update_url_tooltip))

                tooltip = shortener.get_long_url(link)
                break

        update_tooltip(txt, tooltip)

    txt.Bind(wx.EVT_MOTION, update_url_tooltip)

def maybe_add_shorten_link(txt, menu):
    import util.net

    val = txt.Value
    i = textctrl_hittest(txt) # TODO: what if the menu was spawned via the keyboard?

    for link, span in util.net.LinkAccumulator(val):
        if i < span[0] or i >= span[1]:
            continue

        def repl(s):
            i, j = span
            txt.Value = ''.join((val[:i], s, val[j:]))

        if util.net.is_short_url(link):
            longurl = util.net.long_url_from_cache(link)
            if longurl is not None:
                menu.AddItem(_('Use Long URL'), callback=lambda: repl(longurl))
                menu.AddSep()
            continue

        @util.threaded
        def bgthread():
            url = util.net.get_short_url(link)
            if url and val == txt.Value:
                wx.CallAfter(lambda: repl(url))

        menu.AddItem(_('Shorten URL'), callback = bgthread)
        menu.AddSep()
        break

def show_sizers(win, stream = None):
    if isinstance(win, wx.WindowClass):
        sizer = win.Sizer
        if sizer is None:
            raise ValueError('%r has no sizer' % win)
    elif isinstance(win, wx.Sizer):
        sizer = win
    else:
        raise TypeError('must pass a window or sizer, you gave %r' % win)

    if stream is None:
        stream = sys.stdout

    _print_sizer(sizer, stream)

def _shownstr(o):
    return '(hidden)' if not o.IsShown() else ''

def _print_sizer(sizer, stream, indent = '', sizer_shown_str = ''):
    assert isinstance(sizer, wx.Sizer)
    stream.write(''.join([indent, repr(sizer), ' ', sizer_shown_str, '\n']))
    indent = '  ' + indent
    for child in sizer.Children:
        assert isinstance(child, wx.SizerItem)
        if child.Sizer is not None:
            _print_sizer(child.Sizer, stream, '  ' + indent, sizer_shown_str = _shownstr(child))
        else:
            stream.write(''.join([indent,
                                  repr(child.Window if child.Window is not None else child.Spacer),
                                  ' ',
                                  _shownstr(child),
                                  '\n']))

_delays = defaultdict(lambda: (0, None))

def calllimit(secs=.5):
    '''
    Assures a function will only be called only once every "secs" seconds.

    If a new call comes in while a "delay" is occurring, the function is
    guaranteed to be called after the delay is over.
    '''
    def inner(func):  # argument to the decorator: a function
        @functools.wraps(func)
        def wrapper(*args, **kwargs): # arguments to the original function

            now = time_clock()
            key = (func, getattr(func, 'im_self', None))
            lastcalled, caller = _delays[key]
            diff = now - lastcalled

            if diff > secs:
                # CALL NOW
                if isinstance(caller, wx.CallLater): caller.Stop()
                _delays[key] = (now, None)
                return func(*args, **kwargs)
            else:
                # CALL LATER
                if caller == 'pending':
                    # the wx.CallAfter hasn't completed yet.
                    pass
                elif not caller:
                    callin_ms = (lastcalled + secs - now) * 1000
                    def later():
                        def muchlater():
                            _delays[key] = (time_clock(), None)
                            func(*args, **kwargs)

                        _delays[key] = (lastcalled,
                                         wx.CallLater(max(1, callin_ms), muchlater))
                    _delays[key] = (lastcalled, 'pending')
                    wx.CallAfter(later)

            return func
        return wrapper
    return inner

# TODO: move me to gui.native
GetDoubleClickTime = lambda: 600
if wxMSW:
    try:
        from ctypes import windll
        GetDoubleClickTime = windll.user32.GetDoubleClickTime
    except Exception:
        print_exc()

def std_textctrl_menu(txt, menu):
    menu.AddItem(_("Undo"), callback = txt.Undo, id=wx.ID_UNDO)
    menu.Enable(wx.ID_UNDO, txt.CanUndo())

    menu.AddItem(_("Redo"), callback = txt.Redo, id=wx.ID_REDO)
    menu.Enable(wx.ID_REDO, txt.CanRedo())

    menu.AppendSeparator()

    menu.AddItem(_("Cut"), callback = txt.Cut, id=wx.ID_CUT)
    menu.Enable(wx.ID_CUT, txt.CanCut())

    menu.AddItem(_("Copy"), callback = txt.Copy, id=wx.ID_COPY)
    menu.Enable(wx.ID_COPY, txt.CanCopy())

    menu.AddItem(_("Paste"), callback = txt.Paste, id=wx.ID_PASTE)
    menu.Enable(wx.ID_PASTE, txt.CanPaste())

    menu.AppendSeparator()
    menu.AddItem(_("Select All"), callback = lambda: txt.SetSelection(0 , txt.GetLastPosition()), id=wx.ID_SELECTALL)

IMAGE_WILDCARD = ('Image files (*.gif;*.jpeg;*.jpg;*.png)|*.gif;*.jpeg;*.jpg;*.png|'
                  'All files (*.*)|*.*')

def pick_image_file(parent):
    diag = wx.FileDialog(parent, _('Select an image file'),
                         wildcard = IMAGE_WILDCARD)
    filename = None

    try:
        status = diag.ShowModal()
        if status == wx.ID_OK:
            filename = diag.Path
    finally:
        diag.Destroy()

    return filename

def paint_outline(dc, control, color=None, border=1):
    if color is None:
        color = wx.Color(213, 213, 213)

    dc.Brush = wx.TRANSPARENT_BRUSH
    dc.Pen = wx.Pen(color)
    r = control.Rect
    r.Inflate(border, border)
    dc.DrawRectangleRect(r)

def maybe_callable(val):
    return val if not callable(val) else val()

def insert_text(textctrl, text):
    ip = textctrl.InsertionPoint
    if ip != 0 and textctrl.Value[ip-1] and textctrl.Value[ip-1] != ' ':
        textctrl.WriteText(' ')

    textctrl.WriteText(text + ' ')

def insert_shortened_url(textctrl, url, ondone=None, timeoutms=5000):
    import util.net

    textctrl.Freeze()
    textctrl.Enable(False)

    class C(object): pass
    c = C()

    c._finished = False
    def finish(shorturl=None):
        if c._finished: return
        c._finished = True
        insert_text(textctrl, shorturl or url)
        textctrl.Thaw()
        textctrl.Enable()
        textctrl.SetFocus()
        if ondone is not None:
            ondone(shorturl)

    def get():
        short_url = None
        with util.traceguard:
            short_url = util.net.get_short_url(url)
            if short_url is not None and len(short_url) >= len(url):
                short_url = url
        wx.CallAfter(lambda: finish(short_url))

    util.threaded(get)()
    if timeoutms is not None:
        wx.CallLater(timeoutms, finish)

    def cancel(): finish(None)
    return cancel

def bind_special_paste(textctrl, shorten_urls=True, onbitmap=None, onfilename=None,
    onshorten=None, onshorten_done=None):
    import gui.clipboard as clipboard

    def on_text_paste(e):
        if e.EventObject is not textctrl: return e.Skip()

        if onfilename is not None:
            files = clipboard.get_files() or []
            for file in files:
                if file.isfile():
                    if onfilename(file) is False:
                        e.Skip()
                    return

        if maybe_callable(shorten_urls):
            text = clipboard.get_text()
            if text is not None:
                import util.net
                if util.isurl(text) and not util.net.is_short_url(text):
                    cancellable = insert_shortened_url(textctrl, text, ondone=onshorten_done)
                    if onshorten is not None:
                        onshorten(cancellable)
                else:
                    e.Skip()
                return

        if onbitmap is not None:
            bitmap = clipboard.get_bitmap()
            if bitmap is not None:
                import stdpaths, time
                filename = stdpaths.temp / 'digsby.clipboard.%s.png' % time.time()
                bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG)
                if onbitmap(filename, bitmap) is False:
                    e.Skip()
                return

        e.Skip()

    textctrl.Bind(wx.EVT_TEXT_PASTE, on_text_paste)

def HelpLink(parent, url):
    sz = wx.BoxSizer(wx.HORIZONTAL)
    txt_left = wx.StaticText(parent, label = u' [')
    link = wx.HyperlinkCtrl(parent, -1, label = u' ? ', url = url)
    txt_right = wx.StaticText(parent, label = u']')

    sz.Add(txt_left, flag = wx.ALIGN_CENTER_VERTICAL)
    sz.Add(link, flag = wx.ALIGN_CENTER_VERTICAL)
    sz.Add(txt_right, flag = wx.ALIGN_CENTER_VERTICAL)

    return sz

def update_tooltip(ctrl, tip):
    '''only updates a control's tooltip if it's different.'''

    if tip is None:
        if ctrl.ToolTip is not None:
            ctrl.SetToolTip(None)
    else:
        if ctrl.ToolTip is None:
            ctrl.SetToolTipString(tip)
        elif ctrl.ToolTip.Tip != tip:
            ctrl.ToolTip.SetTip(tip)

class tempdc(object):
    def __init__(self, width, height, transparent=True):
        self.width = width
        self.height = height
        self.transparent = transparent

    def __enter__(self):
        self.bitmap = wx.TransparentBitmap(self.width, self.height)
        self.dc = wx.MemoryDC(self.bitmap)
        return self.dc, self.bitmap

    def __exit__(self, exc, val, tb):
        self.dc.SelectObject(wx.NullBitmap)

