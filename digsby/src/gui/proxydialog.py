import wx
from wx import WHITE, HORIZONTAL, VERTICAL, ALIGN_RIGHT, ALIGN_CENTER_VERTICAL, EXPAND, ALIGN_LEFT, ALL
from cgui import SimplePanel
from gui.uberwidgets.PrefPanel import PrefPanel

from gui.validators import NumericLimit

import util.proxy_settings

ID_NONPROX = wx.NewId()
ID_SYSPROX = wx.NewId()
ID_SETPROX = wx.NewId()

ID_HTTP = wx.NewId()
ID_HTTPS = wx.NewId()
ID_SOCKS4 = wx.NewId()
ID_SOCKS5 = wx.NewId()

from config import platformName

class ProxyPanel(SimplePanel):

    def __init__(self, parent):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        if platformName != 'mac':
            self.BackgroundColour = WHITE

        sz = self.Sizer = wx.BoxSizer(VERTICAL)

        top = wx.BoxSizer(HORIZONTAL)


        radpanel = wx.Panel(self)
        rs = radpanel.Sizer = wx.BoxSizer(VERTICAL)


        RADIO = wx.RadioButton

        overrads = self.overrads = dict(NONPROX = RADIO(radpanel, ID_NONPROX, _("&No proxy"), style = wx.RB_GROUP, name = 'override'),
                                        SYSPROX = RADIO(radpanel, ID_SYSPROX, _("Use &default system settings"), name = 'override'),
                                        SETPROX = RADIO(radpanel, ID_SETPROX, _("&Specify proxy settings"), name = 'override'))


        rs.Add(overrads["NONPROX"], 0, ALL, 2)
        rs.Add(overrads["SYSPROX"], 0, ALL, 2)
        rs.Add(overrads["SETPROX"], 0, ALL, 2)

#-------------------------------------------------------------------------------
        proxyp = wx.Panel(self)
        ps = proxyp.Sizer = wx.FlexGridSizer(2, 2)

        TEXT = lambda s: wx.StaticText(proxyp, -1, s)
        INPUT = lambda d, v = wx.DefaultValidator: wx.TextCtrl(proxyp, -1, d, validator = v)

        hosti = self.hosti = INPUT('')
        porti = self.porti = INPUT('', NumericLimit(65535))

        ps.Add(TEXT(_("&Host:")),
              0,
              ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)
        ps.Add(hosti,
              0,
              ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)

        ps.Add(TEXT(_("P&ort:")),
              0,
              ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)
        ps.Add(porti,
              0,
              ALIGN_LEFT | ALIGN_CENTER_VERTICAL | ALL, 2)
        ps.AddGrowableCol(1, 1)
#-------------------------------------------------------------------------------
        protop = wx.Panel(self)
        prs = protop.Sizer = wx.BoxSizer(VERTICAL)

        protorads = self.protorads = dict(HTTP = RADIO(protop, ID_HTTP, "&HTTP", style = wx.RB_GROUP, name = 'proxytype'),
                                          #HTTPS  = RADIO(protop, ID_HTTPS, "HTTPS", name = 'proxytype'),
                                          SOCKS4 = RADIO(protop, ID_SOCKS4, "SOCKS &4", name = 'proxytype'),
                                          SOCKS5 = RADIO(protop, ID_SOCKS5, "SOCKS &5", name = 'proxytype')
                                          )

        prs.Add(protorads["HTTP"], 0, ALL, 2)
        #prs.Add(protorads["HTTPS"], 0, ALL, 2)
        prs.Add(protorads["SOCKS4"], 0, ALL, 2)
        prs.Add(protorads["SOCKS5"], 0, ALL, 2)


#-------------------------------------------------------------------------------
        authp = wx.Panel(self)
        aus = authp.Sizer = wx.FlexGridSizer(2, 2)

        TEXT = lambda s: wx.StaticText(authp, -1, s)
        INPUT = lambda d, style = 0: wx.TextCtrl(authp, -1, d, style = style)

        aus.Add(TEXT(_("&Username:")),
              0,
              ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)

        useri = self.usernamei = INPUT('')
        aus.Add(useri,
              0,
              ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)

        aus.Add(TEXT(_("&Password:")),
              0,
              ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)

        passi = self.passwordi = INPUT('', wx.TE_PASSWORD)
        aus.Add(passi,
              0,
              ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)
        aus.AddGrowableCol(1, 1)
#-------------------------------------------------------------------------------


        top.Add(PrefPanel(self, proxyp, _("Proxy Server")), 1, EXPAND | ALL, 2)
        top.Add(PrefPanel(self, protop, _("Protocol")), 0, EXPAND | ALL, 2)


        sz.Add(PrefPanel(self, radpanel, _("How to Connect")), 0, EXPAND | ALL, 2)
        sz.Add(top, 1, EXPAND)
        sz.Add(PrefPanel(self, authp, _("Authentication")), 1, EXPAND | ALL, 2)

        pd = self.proxy_dict

        override = pd.get('override', "SYSPROX")

        try:
            override = int(override)
        except:
            pass
        else:
            override = ['SYSPROX', 'SETPROX'][override]

        self.override = override
        self.overrads[self.override].Value = True

        self.addr = pd.get('addr', '')
        self.port = pd.get('port', '')

        self.proxytype = pd.get('proxytype', 'HTTP')
        self.protorads[self.proxytype].Value = True

        self.username = pd.get('username', '')
        self.password = pd.get('password', '')

        self.Enablement()

        Bind = self.Bind
        Bind(wx.EVT_RADIOBUTTON, self.OnRadio)

        if platformName != 'mac':
            Bind(wx.EVT_PAINT, self.OnPaint)

    @property
    def proxy_dict(self):
        return util.proxy_settings.get_proxy_dict()

    def OnOK(self, event = None):
        pd = self.proxy_dict


        keys = ['override',
                'addr',
                'port',
                'proxytype',
                'username',
                'password']

        for key in keys:
            pd[key] = str(getattr(self, key))

        #print pd
        pd.save()

    addr = property(lambda self: self.hosti.Value, lambda self, address: self.hosti.SetValue(address))
    port = property(lambda self: self.porti.Value, lambda self, address: self.porti.SetValue(address))

    username = property(lambda self: self.usernamei.Value, lambda self, address: self.usernamei.SetValue(address))
    password = property(lambda self: self.passwordi.Value, lambda self, address: self.passwordi.SetValue(address))

    def OnRadio(self, event):
        rad = event.GetEventObject()

        if rad.GetName() == "proxytype":
            setattr(self, "proxytype", rad.GetLabelText().replace(' ' , ''))
        elif rad.GetName() == 'override':
            for key in self.overrads:
                if self.overrads[key].Value:
                    setattr(self, "override", key)

            self.Enablement()

    def Enablement(self):

        switch = self.overrads["SETPROX"].Value

        self.hosti.Enable(switch)
        self.porti.Enable(switch)

        for rad in self.protorads:
            self.protorads[rad].Enable(switch)

        hasproxy = not self.overrads["NONPROX"].Value
        self.usernamei.Enable(hasproxy)
        self.passwordi.Enable(hasproxy)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        rect = wx.RectS(self.ClientSize)

        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)


class ProxyDialog(wx.Dialog):
    def __init__(self, parent = None):
        wx.Dialog.__init__(self, parent, title = _("Connection Settings"))

        if not platformName == 'mac':
            self.SetBackgroundColour(wx.WHITE)

        self.Sizer = wx.BoxSizer(VERTICAL)
        self.pp = ProxyPanel(self)
        self.Sizer.Add(self.pp, 1, EXPAND | ALL, 5)

        bsz = wx.BoxSizer(wx.HORIZONTAL)
        okb = wx.Button(self, wx.ID_OK, _("&OK"))
        okb.SetDefault()
        canb = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        bsz.Add(okb, 0, ALL, 4)
        bsz.Add(canb, 0, ALL, 4)

        self.Sizer.Add(bsz, 0, ALIGN_RIGHT)

        okb.Bind(wx.EVT_BUTTON, self.OnOK)
        canb.Bind(wx.EVT_BUTTON, lambda e: self.Close())

        self.Fit()
        self.Size = wx.Size(400, self.Size.height)

        self.Layout()
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        self.Show(False)
        self.pp = None

    def OnOK(self, event):
        res = self.pp.OnOK(event)
        self.SetReturnCode(wx.ID_OK)
        self.Close()
        return res

if __name__ == "__main__":
    from tests.testapp import testapp
    app = testapp()

    f = ProxyDialog()
    f.Show(True)

    app.MainLoop()
