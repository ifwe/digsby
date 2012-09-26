from __future__ import with_statement
import wx
from gui.addcontactdialog import AddContactDialog
from gui import skin
from util import traceguard

LEFTLESS  = wx.ALL & ~wx.LEFT

try:
    _
except NameError:
    def _(s):
        return s

authdialog_style = (  wx.DEFAULT_FRAME_STYLE
                    #& ~(wx.RESIZE_BORDER)
                    | wx.STAY_ON_TOP)

class AuthorizationDialog(wx.Frame):
    def __init__(self, protocol, buddy, message, username_added, callback = None):
        wx.Frame.__init__(self, None, -1, _('Authorize Contact'), style = authdialog_style)
        with traceguard:
            self.SetFrameIcon(skin.get('appdefaults.taskbaricon'))
        p = wx.Panel(self)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(p,1,wx.EXPAND)

        self.protocol = protocol
        self.buddy    = buddy
        self.bname    = getattr(buddy, 'name', buddy)
        self.username_added = username_added
        self.callback = callback

        bitmap      = wx.ArtProvider.GetBitmap(wx.ART_QUESTION)
        bitmap.SetMaskColour(wx.BLACK)

        sbitmap     = wx.StaticBitmap(p, -1, bitmap)

        text        = wx.StaticText(p, -1, message)

        addbutton   = wx.Button(p, wx.YES, _('Authorize and Add'))
        authbutton  = wx.Button(p, wx.OK,  _('Authorize'))
        denybutton  = wx.Button(p, wx.NO,  _('Deny'))

        selfSizer   = p.Sizer = wx.BoxSizer(wx.VERTICAL  )
        topSizer                 = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer              = wx.BoxSizer(wx.HORIZONTAL)

        topSizer.Add(sbitmap, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.RIGHT, 8)
        topSizer.Add(text,    0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)

        buttonSizer.AddStretchSpacer()
        add_flags = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|LEFTLESS
        buttonSizer.AddMany([ (addbutton,  0, add_flags, 8),
                              (authbutton, 0, add_flags, 8),
                              (denybutton, 0, add_flags, 8), ])
        selfSizer.Add(topSizer,     1, wx.ALIGN_CENTER_HORIZONTAL)
        selfSizer.Add(buttonSizer,  0, wx.EXPAND)

        self.Fit()

        self.Size += (40, 30)

        self.Bind(wx.EVT_BUTTON, self.OnButton)
        self.Bind(wx.EVT_CLOSE,  self.OnClose)

    def OnButton(self, event):
        if event.Id == wx.YES:
            AddContactDialog.MakeOrShow(service = getattr(self.buddy, 'service', self.protocol.service), name = unicode(self.bname))
            self.callback(self.buddy, True, self.username_added)
        elif event.Id == wx.OK:
            self.callback(self.buddy, True, self.username_added)
        elif event.Id == wx.NO:
            self.callback(self.buddy, False, self.username_added)

        self.Close()

    def OnClose(self, event):
        self.Hide()
        self.Destroy()




if __name__ == '__main__':
    from tests.testapp import testapp
    app = testapp()

    ad = AuthorizationDialog(None, None, 'Allow SomeBuddy to add you as a buddy as YourNick on Protocol?', 'protoname')
    ad.Show()
    app.MainLoop()
