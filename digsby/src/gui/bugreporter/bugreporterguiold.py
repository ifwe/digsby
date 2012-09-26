from __future__ import with_statement
from wx import TextCtrl, StaticText, ALIGN_CENTER, RadioButton, BoxSizer, HORIZONTAL, VERTICAL, StaticLine, \
    EXPAND, Button, ALL, BOTTOM, LEFT, RIGHT, Point
import wx
from util import Storage as S, callsback, traceguard
from traceback import print_exc
from gui.toolbox.imagefx import pil_to_wxb_nocache
from cgui import getScreenBitmap, GetTrayRect
from gui import skin
from gui.toolbox import Monitor
from PIL import Image, ImageDraw
from PIL.Image import BICUBIC, ANTIALIAS
from cStringIO import StringIO
from logging import getLogger; log = getLogger('bugreporter')

SCREENSHOT_TIMER_SECS = 4
num_screenshots = 0

TAKE_SCREENSHOT_LABEL = _('Take Screenshot')

class BugReportPanel(wx.Panel):
    def __init__(self, parent, callback = None):
        wx.Panel.__init__(self, parent)
        self.screenshot = None
        self.construct()
        self.layout()
        self.callback = callback

        if callback is not None:
            self.Bind(wx.EVT_BUTTON, self.OnButton)

        self.Top.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, e):
        self.Top.Destroy()

    def OnButton(self, e):
        e.Skip()
        b = e.EventObject
        submit = b is self.submit and self.callback is not None

        if submit and not self.input.Value:
            e.Skip(False)
            bug_desc_header = _("Please enter a description of the bug.")
            bug_desc_info = _("Include as much information as possible about "
                              "what went wrong and how to reproduce the issue.")
            
            wx.MessageBox(u'%s\n\n%s' % (bug_desc_header, bug_desc_info),
                          _('Send Bug Report'))
            return

        def after():
            try:
                if submit:
                    self.callback(self.info())
            finally:
                self.Top.Destroy()

        wx.CallAfter(after)

    def construct(self):
        def Text(*a, **k):
            txt = StaticText(self, -1, *a, **k)
            txt.Wrap(520)
            return txt

        def BoldText(*a, **k):
            t = Text(*a, **k); t.SetBold()
            return t

        self.header    = BoldText(_('Use this tool to submit a diagnostic log right after you experience a bug'),
                                  style = ALIGN_CENTER)

        self.subheader = Text(_("This diagnostic log file does not contain personal data such as the content of sent/received IMs, the content of emails, and the content of social network newsfeeds except where it directly pertains to an error."),
                              style = ALIGN_CENTER)

        self.line = StaticLine(self)

        self.input_desc = BoldText(_('Please describe the bug in as much detail as possible.  Include information such as what you were doing when the bug occurred and exactly what goes wrong.'))

        self.input = TextCtrl(self, -1, size = (400, 200), style = wx.TE_MULTILINE)

        self.reproduce_text = Text(_('Can you consistently reproduce this bug?'))

        self.radios = S(yes     = RadioButton(self, -1, _('&Yes'), style = wx.RB_GROUP),
                        no      = RadioButton(self, -1, _('&No')),
                        unknown = RadioButton(self, -1, _("&Don't Know")))
        self.radios.unknown.SetValue(True)

        self.screenshot_text = BoldText(_('If this is a visual bug, please attach a screenshot to this report.'))
        self.screenshot_link = wx.HyperlinkCtrl(self, -1, TAKE_SCREENSHOT_LABEL, '#')
        self.screenshot_link.Bind(wx.EVT_HYPERLINK, self.OnScreenshot)

        self.screenshot_timer = ScreenshotTimer(SCREENSHOT_TIMER_SECS,
                                                lambda t: self.OnScreenshotLinkTimer(_('Taking Screenshot in {secs}').format(secs=t)),
                                                self.OnScreenshotTimer)

        self.submit = Button(self, wx.ID_OK, _('&Submit'))
        self.submit.SetDefault()
        self.cancel = Button(self, wx.ID_CANCEL, _('&Cancel'))

    def OnScreenshotLinkTimer(self, l):
        if wx.IsDestroyed(self):
            self.screenshot_timer.Stop()
            return

        self.SetScreenshotLabel(l)

    def SetScreenshotLabel(self, l):
        self.screenshot_link.SetLabel(l)
        self.Layout()
        self.screenshot_link.Refresh()

    def OnScreenshot(self, e):
        if self.screenshot_timer.IsRunning() or self.screenshot is not None:
            self.screenshot = None
            self.screenshot_timer.Stop()
            self.screenshot_link.Label = TAKE_SCREENSHOT_LABEL
            return
        else:
            self.screenshot_timer.Start()

    def OnScreenshotTimer(self):
        oldpos = self.Parent.Position

        try:
            top = self.Top
            top.Move((-top.Size.width - 50, -top.Size.height - 50))

            wx.BeginBusyCursor()
            wx.WakeUpIdle()
            wx.MilliSleep(500)

            global num_screenshots
            num_screenshots +=1 
            log.info('taking screenshot %d', num_screenshots)

            screen_full, screen = app_windows_image()
            diag = ScreenshotDialog(self, screen_full, screen, pos = oldpos + Point(40, 40))
        except:
            print_exc()
            screen = None
        finally:
            wx.EndBusyCursor()
            self.Top.Move(oldpos)

        if screen is None:
            return

        try:
            self.screenshot_link.Label = TAKE_SCREENSHOT_LABEL
            if diag.ShowModal() == wx.ID_OK:
                self.screenshot = diag.SelectedScreenshot
                self.screenshot_link.Label = _("Remove Screenshot")
            else:
                self.screenshot_link.Label = TAKE_SCREENSHOT_LABEL
        finally:
            diag.Destroy()

        self.Layout()
        self.Refresh()

    @property
    def reproduce(self):
        for name, radio in self.radios.iteritems():
            if radio.Value: return name

    def info(self):
        shot = self.screenshot
        if shot is not None:
            f = StringIO()
            shot.save(f, 'PNG')
            shot = f.getvalue()

        return S(description  = self.input.Value,
                 reproducible = self.reproduce,
                 screenshot   = shot )

    def layout(self):
        reproduce_sizer = HSizer()
        reproduce_sizer.AddMany([(self.reproduce_text, 0),
                                 (self.radios.yes,     1, LEFT, 20),
                                 (self.radios.no,      1, LEFT, 20),
                                 (self.radios.unknown, 1, LEFT, 20)])

        visual_sizer = HSizer()
        visual_sizer.AddMany([(self.screenshot_text, 0, RIGHT, 15),
                              (self.screenshot_link, 0)])

        button_sizer = HSizer()
        button_sizer.AddStretchSpacer(1)
        button_sizer.AddMany([(self.submit, 0, EXPAND | RIGHT, 10),
                              (self.cancel, 0)])

        self.Sizer = v = VSizer()
        v.AddMany([
            (self.header,     0, EXPAND | BOTTOM, 6),
            (self.subheader,  0, EXPAND | BOTTOM, 6),
            (self.line,       0, EXPAND | BOTTOM, 6),
            (self.input_desc, 0, EXPAND | BOTTOM, 6),
            (self.input,      1, EXPAND | BOTTOM, 6),
            (reproduce_sizer, 0, EXPAND | BOTTOM, 6),
            (visual_sizer,    0, EXPAND | BOTTOM, 10),
            (button_sizer,    0, EXPAND)])

@callsback
def show_dialog(callback = None):
    if not BugReportDialog.RaiseExisting():
        diag = BugReportDialog(None, callback = callback)
        diag.CenterOnScreen()
        diag.Show()

class BugReportDialog(wx.Dialog):
    def __init__(self, parent, callback = None):
        wx.Dialog.__init__(self, parent, -1, _('Submit Bug Report - Digsby'))
        self.SetFrameIcon(skin.get('appdefaults.taskbaricon'))

        self.panel    = BugReportPanel(self, callback)
        self.info     = self.panel.info

        s = self.Sizer = VSizer()
        s.Add(self.panel, 1, EXPAND | ALL, 8)
        self.SetMaxSize((500, -1))
        self.Fit()

def resize_screenshot(img):
    w, h = img.size
    squaresize = 650

    if w > h:
        new_height = int(h/float(w) * squaresize)
        img = img.resize((squaresize, new_height), BICUBIC if squaresize > w else ANTIALIAS)
    else:
        new_width = int(w/float(h) * squaresize)
        img = img.resize((new_width, squaresize), BICUBIC if squaresize > h else ANTIALIAS)

    return img

class ScreenshotDialog(wx.Dialog):
    def __init__(self, parent, screenshot_full, screenshot, pos):
        wx.Dialog.__init__(self, parent, -1, _('Submit Bug Report - Screenshot - Digsby'))
        self.SetFrameIcon(skin.get('appdefaults.taskbaricon'))

        # store both screenshots -- the one with blanked out areas, and the
        # full one
        self.big_screenshot_digsby = screenshot
        self.screenshot_digsby = pil_to_wxb_nocache(resize_screenshot(screenshot))

        self.big_screenshot_full = screenshot_full
        self.screenshot_full = pil_to_wxb_nocache(resize_screenshot(screenshot_full))

        self.screenshot = self.screenshot_digsby
        self.hide_non_digsby = True

        p = self.panel = wx.Panel(self)
        s = self.panel.Sizer = VSizer()

        s.Add((self.screenshot_full.Width, self.screenshot_full.Height + 20))
        p.Bind(wx.EVT_PAINT, self.paint)

        hz = wx.BoxSizer(wx.HORIZONTAL)
        checkbox = wx.CheckBox(p, -1, _('Blank out non Digsby windows'))
        checkbox.SetValue(True)
        checkbox.Bind(wx.EVT_CHECKBOX, self.OnCheckFullScreenShot)
        hz.Add(checkbox, 0, EXPAND)
        hz.AddStretchSpacer(1)
        hz.Add(StaticText(p, -1, _('Is it OK to send this screenshot to digsby.com?')), 0, EXPAND)
        s.Add(hz, 0, wx.BOTTOM | EXPAND, 7)

        send = Button(p, wx.ID_OK, _('OK'))
        send.SetDefault()

        cancel = Button(p, wx.ID_CANCEL, _('Cancel'))

        h = HSizer()
        h.AddStretchSpacer(1)
        h.AddMany([(send, 0, EXPAND | RIGHT, 10),
                   (cancel, 0)])
        s.Add(h, 0, EXPAND)

        s = self.Sizer = VSizer()
        s.Add(self.panel, 1, EXPAND | ALL, 8)

        self.Fit()
        self.SetPosition(pos)

    @property
    def SelectedScreenshot(self):
        if self.hide_non_digsby:
            return self.big_screenshot_digsby
        else:
            return self.big_screenshot_full

    def OnCheckFullScreenShot(self, e):
        self.hide_non_digsby = e.IsChecked()
        self.Refresh()

    def paint(self, e):
        dc = wx.PaintDC(e.EventObject)
        screenshot = self.screenshot_digsby if self.hide_non_digsby else self.screenshot_full
        dc.DrawBitmap(screenshot, 10, 10, True)

class ScreenshotTimer(wx.Timer):
    def __init__(self, secs, on_tick, on_done):
        wx.Timer.__init__(self)
        self.secs = secs
        self.tick = on_tick
        self.done = on_done

    def Start(self):
        self.count = self.secs
        wx.Timer.Start(self, 1000, False)
        self.tick(self.count)

    def Notify(self):
        self.count -= 1
        self.tick(self.count)
        if self.count == 0:
            self.Stop()
            with traceguard:
                self.done()



HSizer = lambda: BoxSizer(HORIZONTAL)
VSizer = lambda: BoxSizer(VERTICAL)

import gui.wxextensions

def app_windows_image():
    '''
    Returns a bitmap showing all the top level windows in this application.

    Other areas of the screen are blanked out.
    '''

    # get the union of all screen rectangles (this will be a big rectangle
    # covering the area of all monitors)
    rect     = reduce(wx.Rect.Union, (m.Geometry for m in Monitor.All()))
    if "wxMSW" in wx.PlatformInfo:
        screen   = getScreenBitmap(rect).PIL
    else:
        screen = wx.ScreenDC().GetAsBitmap().PIL

    mask     = Image.new('RGBA', rect.Size, (255, 255, 255, 255))
    drawrect = lambda r: ImageDraw.Draw(mask).rectangle([r.x, r.y, r.Right, r.Bottom ], fill = (0, 0, 0, 0))

    # draw rectangles into a mask for each top level window (and the system tray)
    for r in [GetTrayRect()] + [w.Rect for w in wx.GetTopLevelWindows() if w.IsShown()]:
        r.Offset(-rect.Position) # some monitors may be in negative coordinate space...
        drawrect(r)

    # paste the mask into the screenshot--whiteing out areas not in our windows
    screen_full = screen.copy()
    screen.paste(mask, (0, 0), mask)

    return screen_full, screen

if __name__ == '__main__':
    import gettext; gettext.install('Digsby')

    from tests.testapp import testapp
    a = testapp('../../..')

    f = wx.Frame(None, pos = (50, 50))
    f.Show()
    f = wx.Frame(None, pos = (10050, 80))
    f.Show()
    f = wx.Frame(None, pos = (400, 300))
    f.Show()


    print show_dialog()

