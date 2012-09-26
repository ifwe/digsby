from PIL.Image import BICUBIC, ANTIALIAS
import wx
from gui.toolbox.imagefx import wxb_to_pil_nocache, pil_to_wxb_nocache

class ImageDialog(wx.Dialog):
    SuccessID = wx.ID_OK

    def __init__(self, parent,
            screenshot, pos, title,
            message,
            oklabel = _('OK'),
            cancellabel = _('Cancel')):

        wx.Dialog.__init__(self, parent, -1, title)

        self.screenshot = resize_image_for_dialog(screenshot)

        p = self.panel = wx.Panel(self)
        s = self.panel.Sizer = VSizer()

        s.Add((self.screenshot.Width, self.screenshot.Height + 20))
        p.Bind(wx.EVT_PAINT, self.paint)
        s.Add(wx.StaticText(p, -1, message), 0, wx.EXPAND | wx.BOTTOM, 8)

        send = wx.Button(p, self.SuccessID, oklabel)
        send.SetDefault()

        cancel = wx.Button(p, wx.ID_CANCEL, cancellabel)

        h = HSizer()
        h.AddStretchSpacer(1)
        h.AddMany([(send, 0, wx.EXPAND | wx.RIGHT, 10), (cancel, 0)])
        s.Add(h, 0, wx.EXPAND)

        s = self.Sizer = VSizer()
        s.Add(self.panel, 1, wx.EXPAND | wx.ALL, 8)

        self.Fit()
        self.SetPosition(pos)

    def paint(self, e):
        dc = wx.PaintDC(e.EventObject)
        r = self.panel.ClientRect
        dc.DrawBitmap(self.screenshot, r.HCenter(self.screenshot), 10, True)

def resize_image_for_dialog(screenshot, maxsize=650):
    if isinstance(screenshot, wx.Bitmap):
        screenshot = wxb_to_pil_nocache(screenshot)

    w, h = screenshot.size
    img = screenshot

    if w > maxsize or h > maxsize:
        if w > h:
            new_height = int(h/float(w) * maxsize)
            img = img.resize((maxsize, new_height), BICUBIC if maxsize > w else ANTIALIAS)
        else:
            new_width = int(w/float(h) * maxsize)
            img = img.resize((new_width, maxsize), BICUBIC if maxsize > h else ANTIALIAS)

    return pil_to_wxb_nocache(img)

HSizer = lambda: wx.BoxSizer(wx.HORIZONTAL)
VSizer = lambda: wx.BoxSizer(wx.VERTICAL)

def show_image_dialog(parent, message, bitmap, title = None):
    from gui.imagedialog import ImageDialog

    diag = ImageDialog(parent, bitmap, wx.DefaultPosition,
        message = message,
        title = title or _('Send Image'),
        oklabel = _('&Send Image'),
        cancellabel = _('&Don\'t Send'))

    diag.CenterOnParent()
    try:
        return diag.ShowModal() == ImageDialog.SuccessID
    finally:
        if not wx.IsDestroyed(diag):
            diag.Destroy()

