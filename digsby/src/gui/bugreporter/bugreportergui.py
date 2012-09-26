from __future__ import with_statement
from wx import TextCtrl, StaticText, ALIGN_CENTER, RadioButton, BoxSizer, HORIZONTAL, VERTICAL, StaticLine, \
    EXPAND, Button, ALL, TOP, BOTTOM, LEFT, RIGHT, Point
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

from gui.imagedialog import ImageDialog
import wx.lib.sized_controls as sc

SCREENSHOT_TIMER_SECS = 4
num_screenshots = 0


class BugReportPanel(sc.SizedPanel):
    def __init__(self, parent, callback = None):
        sc.SizedPanel.__init__(self, parent)
        self.screenshot = None
        self.construct()
        # self.layout()
        self.callback = callback

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

        self.subheader.SetSizerProps(expand=True)

        self.line = StaticLine(self)

        self.input_desc = BoldText(_('Please describe the bug in as much detail as possible. Include information such as what you were doing when the bug occurred and exactly what goes wrong.'))

        self.input_desc.SetSizerProps(expand=True)

        self.input = TextCtrl(self, -1, size = (400, 200), style = wx.TE_MULTILINE)
        self.input.SetSizerProps(expand=True, proportion=1)

        radioPanel = self.radioPanel = sc.SizedPanel(self, -1)
        radioPanel.SetSizerType("horizontal")

        self.reproduce_text = wx.StaticText(radioPanel, -1, _('Can you consistently reproduce this bug?'))

        self.radios = S(yes     = RadioButton(radioPanel, -1, _('&Yes'), style = wx.RB_GROUP),
                        no      = RadioButton(radioPanel, -1, _('&No')),
                        unknown = RadioButton(radioPanel, -1, _("&Don't Know")))
        self.radios.unknown.SetValue(True)

        self.screenshot_text = BoldText(_('If this is a visual bug, please attach a screenshot to this report.'))
        self.screenshot_link = wx.HyperlinkCtrl(self, -1, _('Take Screenshot'), '#')
        self.screenshot_link.Bind(wx.EVT_HYPERLINK, self.OnScreenshot)

        self.screenshot_timer = ScreenshotTimer(SCREENSHOT_TIMER_SECS,
                                                lambda t: self.OnScreenshotLinkTimer(_('Taking Screenshot in {secs}').format(secs=t)),
                                                self.OnScreenshotTimer)

        self.Bind(wx.EVT_SIZE, self.OnSize)


    def OnSize(self, event):
        self.subheader.SetLabel(_("This diagnostic log file does not contain personal data such as the content of sent/received IMs,"
                                " the content of emails, and the content of social network newsfeeds except where it directly pertains to an error."))
        self.subheader.Wrap(event.Size.width)
        self.input_desc.SetLabel(_('Please describe the bug in as much detail as possible. Include information such as what you were doing when the bug occurred and exactly what goes wrong.'))
        self.input_desc.Wrap(event.Size.width)

        event.Skip()

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
            self.screenshot_link.Label = _('Take Screenshot')
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
            if diag.ShowModal() == wx.ID_OK:
                self.screenshot = diag.SelectedScreenshot
                self.screenshot_link.Label = _("Remove Screenshot")
            else:
                self.screenshot_link.Label = _('Take Screenshot')
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
    diag = BugReportDialog(None, callback = callback)
    diag.CenterOnScreen()
    diag.Show()

class BugReportDialog(sc.SizedDialog):
    def __init__(self, parent, callback = None):
        sc.SizedDialog.__init__(self, parent, -1, _('Submit Bug Report - Digsby'),
                                size=(590, 600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetFrameIcon(skin.get('appdefaults.taskbaricon'))

        self.panel    = BugReportPanel(self.GetContentsPane(), callback)
        self.panel.SetSizerProps(expand=True, proportion=1)
        self.callback = callback

        self.SetButtonSizer(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL))

        # rename OK Button
        button = self.FindWindowById(wx.ID_OK, self)
        if button:
            button.SetLabel(_("Submit"))

        if callback is not None:
            self.Bind(wx.EVT_BUTTON, self.OnButton)

        self.Fit()
        self.MinSize = self.Size

    def OnButton(self, e):
        e.Skip(False)
        submit = e.Id == wx.ID_OK and self.callback is not None

        if submit and not self.panel.input.Value:
            bug_desc_header = _("Please enter a description of the bug.")
            bug_desc_info = _("Include as much information as possible about "
                              "what went wrong and how to reproduce the issue.")

            wx.MessageBox(u'%s\n\n%s' % (bug_desc_header, bug_desc_info),
                          _('Send Bug Report'))
            return

        try:
            if submit:
                self.callback(self.panel.info())
        finally:
            self.Destroy()

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


class ScreenshotDialog(sc.SizedDialog):
    def __init__(self, parent, screenshot_full, screenshot, pos):
        sc.SizedDialog.__init__(self, parent, -1, _('Submit Bug Report - Screenshot - Digsby'))
        self.SetFrameIcon(skin.get('appdefaults.taskbaricon'))

        # store both screenshots -- the one with blanked out areas, and the
        # full one
        self.big_screenshot_digsby = screenshot
        self.screenshot_digsby = pil_to_wxb_nocache(resize_screenshot(screenshot))

        self.big_screenshot_full = screenshot_full
        self.screenshot_full = pil_to_wxb_nocache(resize_screenshot(screenshot_full))

        self.screenshot = self.screenshot_digsby
        self.hide_non_digsby = True

        p = self.panel = self.GetContentsPane()

        screenshot_panel = sc.SizedPanel(self.panel, -1)
        screenshot_panel.SetMinSize((self.screenshot_full.Width, self.screenshot_full.Height + 20))
        screenshot_panel.Bind(wx.EVT_PAINT, self.paint)

        hpanel = sc.SizedPanel(self.panel, -1)
        hpanel.SetSizerType("horizontal")
        checkbox = wx.CheckBox(hpanel, -1, _('Blank out non Digsby windows'))
        checkbox.SetValue(True)
        checkbox.Bind(wx.EVT_CHECKBOX, self.OnCheckFullScreenShot)
        checkbox.SetSizerProps(expand=True)
        stretchpanel = sc.SizedPanel(hpanel, -1)
        stretchpanel.SetSizerProps(expand=True, proportion=1)

        StaticText(hpanel, -1, _('Is it OK to send this screenshot to digsby.com?'))

        self.SetButtonSizer(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL))

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
            with traceguard:
                self.done()
            self.Stop()


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
        r.Offset((-rect.Position[0], -rect.Position[1])) # some monitors may be in negative coordinate space...
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

