import wx

from cgui import isGlassEnabled, glassExtendInto, DragMixin

def isVistaOrHigher():
    import ctypes
    return 'wxMSW' in wx.PlatformInfo and hasattr(ctypes.windll, 'dwmapi')

def ModifiedFont(font, weight = -1, pointSize = -1, faceName = '', underline = -1):
    font = wx.Font(font)
    if weight != -1:
        font.SetWeight(weight)
    if pointSize != -1:
        font.SetPointSize(pointSize)
    if len(faceName):
        font.SetFaceName(faceName)
    if underline != -1:
        font.SetUnderlined(bool(underline))
    return font

def ModifyFont(ctrl, weight = -1, pointSize = -1, faceName = '', underline = -1):
    ctrl.SetFont(ModifiedFont(ctrl.GetFont(), weight, pointSize, faceName, underline))

def setVistaFont(ctrl):
    if not isVistaOrHigher():
        return
    font = wx.Font(ctrl.GetFont().GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, u"Segoe UI")
    ctrl.SetFont(font)

def GetPolyRegion(points, w, h, border = 1):
    i = wx.EmptyImage(w + border, h + border)
    b = wx.BitmapFromImage(i)

    m = wx.MemoryDC(b)
    m.Clear()
    m.SetBrush(wx.BLACK_BRUSH)
    m.SetPen(wx.BLACK_PEN)
    m.DrawRectangle(0, 0, w + border, h + border)
    m.SetBrush(wx.WHITE_BRUSH)
    m.SetPen(wx.Pen(wx.WHITE))
    m.DrawPolygon(points)
    m.SelectObject(wx.NullBitmap)

    b.SetMask(wx.Mask(b, wx.BLACK))
    return wx.RegionFromBitmap(b)

class BubbleWindow(wx.Frame):
    _internalSize = None
    _poly = []
    _labelText = ''

    def __init__(self, parent, size):
        wx.Frame.__init__(self, parent, wx.ID_ANY, u'', wx.DefaultPosition, wx.DefaultSize,
                          wx.FRAME_SHAPED | wx.BORDER_NONE | wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP)
        setVistaFont(self)
        self._internalSize = size
        self.InitPoly()
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def ShowPointTo(self, point):
        x = point.x
        y = point.y
        xborder = 0
        yborder = 0
        startx = 0
        starty = 10
        px = 10
        py = 0
        endx = 2 * xborder + self._internalSize.x + startx
        endy = 2 * yborder + self._internalSize.y + starty
        diff = endy

        self.Freeze()
        self.SetPosition(wx.Point(x - px, y - py - diff))
        self.SetSize(wx.Size(endx + 1, endy + 1))
        self.SetShape(GetPolyRegion(self._poly, endx, endy))
        self.ShowNoActivate(True)
        self.Thaw()

    def DrawContent(self, dc):
        #return wx.Frame.DrawContent(self, dc)
        pass

    def SetText(self, text):
        if text == self._labelText:
            return

        self._labelText = text
        dc = wx.MemoryDC()
        dc.SetFont(self.GetFont())
        self._internalSize = dc.GetTextExtent(text) + wx.Size(18, 20)

        self.InitPoly()

        if self.Shown:
            self.Refresh()

    def InitPoly(self):
        point = wx.Point(10, 0)
        xborder = 0
        yborder = 0
        startx = 0
        starty = 10
        px = point.x
        py = point.y
        endx = (2 * xborder + self._internalSize.x + startx)
        endy = (2 * yborder + self._internalSize.y + starty)

        pt = lambda x, y: wx.Point(x, (-1 * y) + endy)

        self._poly[:] = [
            pt(px, py),
            pt(px + 1, py),
            pt(px + 11, starty),
            pt(endx, starty),
            pt(endx, endy),
            pt(startx, endy),
            pt(startx, starty),
            pt(px, starty),
            pt(px, py),
        ]

    def GetNumPolyPoints(self):
        return len(self._poly)

    def GetPolyPoints(self):
        return self._poly

    def OnPaint(self, evt):
        dc = wx.AutoBufferedPaintDC(self)
        o = wx.Color(254, 214, 76)
        y = wx.Color(255, 251, 184)

        dc.SetPen(wx.Pen(o))
        dc.SetBrush(wx.Brush(y))

        dc.DrawPolygon(self.GetPolyPoints())
        self.DrawContent(dc)

        dc.SetFont(self.GetFont())
        textSize = wx.Size(dc.GetTextExtent(self._labelText))
        dc.DrawText(self._labelText, 10, (self.GetSize().y - textSize.y) / 2 - 5)

class LoginWindow(wx.Frame):
    SAVEPASSWORD = 0
    AUTOLOGIN = 1
    FORGOTPASSWORD = 2
    NOACCOUNT = 3
    CONNSETTINGS = 4
    CLOSE = 5
    USERNAME = 6
    PASSWORD = 7
    HELPBUTTON = 8
    LANGUAGE = 9
    CREATEPROFILE = 10

    _logoBitmap = None
    _helpBitmap = None
    _settingsBitmap = None
    _languageBitmap = None

    revisionString = None
    glassMarginTop = None
    _showRevision = None
    _useGlass = None
    _helpHover = None

    panel = None
    usernameLabel = None
    usernameChoice = None
    passwordLabel = None
    passwordTextbox = None
    saveButton = None
    saveCheck = None
    autoLoginCheck = None
    statusLabel = None
    languageChoice = None

    forgotPasswordLink = None
    noAccountLink = None

    dragMixin = None
    _bubble = None
    settingsButton = None

    def __init__(self, window, pos, bitmaps, revision, showLanguages, profiles):
        self._useGlass = isGlassEnabled()
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX)
        if not self.useGlass():
            style |= wx.FRAME_SHAPED

        wx.Frame.__init__(self, window, wx.ID_ANY, u'', pos, wx.DefaultSize, style, _(u'Welcome to Digsby'))
        self._logoBitmap = bitmaps.logo
        self._helpBitmap = bitmaps.help
        self._settingsBitmap = bitmaps.settings
        self._languageBitmap = bitmaps.language

        self._helpHover = False
        self.revisionString = revision
        self._showRevision = False

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.createComponents(showLanguages, profiles)

        self.setupGlass()
        if not self.useGlass():
            self.SetShape(wx.Region(0, 0, self.GetClientSize().x, self.GetClientSize().y))

        self.dragMixin = DragMixin(self.panel)
        self.panel.PushEventHandler(self.dragMixin)

    def GetBubble(self):
        if self._bubble is None:
            self._bubble = BubbleWindow(self, wx.Size(100, 40))
        return self._bubble

    def UpdateUIStrings(self):
        self.SetTitle(_('Welcome to Digsby'))
        self.usernameLabel.SetLabel(_('Profile &Name'))
        self.passwordLabel.SetLabel(_('Profile &Password'))
        self.saveCheck.SetLabel(_('&Save Password'))
        self.createProfileButton.SetLabel(_('&Create Profile'))
        self.autoLoginCheck.SetLabel(_('&Auto login'))
        self.saveButton.SetLabel(_('&Load Profile'))
        self.forgotPasswordLink.SetLabel(_('Forgot?'))

        self.GetSizer().Fit(self)

    def SetStatus(self, status, windowTitle = u''):
        self.statusLabel.SetLabel(status)
        title = windowTitle or status
        if title:
            self.SetTitle(title)
        self.panel.Layout()

    def EnableControls(self, enable, label, buttonEnable = -1):
        self.Freeze()
        self.usernameChoice.Enable(enable)
        self.passwordTextbox.Enable(enable)
        self.saveCheck.Enable(enable)

        if (buttonEnable != -1):
            self.saveButton.Enable(bool(buttonEnable))

        self.saveButton.SetLabel(label)

        self.Thaw()
        self.Refresh()
        self.Update()

    def setShowRevision(self, show, repaint = True):
        self._showRevision = show
        if repaint:
            self.Refresh()

    def setHyperlinkColor(self, link):
        c = link.GetNormalColour()
        link.SetVisitedColour(c)
        link.SetHoverColour(c)

    def makeTooltipButton(self, ctrl):
        ctrl.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        ctrl.Connect(ctrl.Id, ctrl.Id, wx.EVT_MOTION, self.OnButtonHover)
        ctrl.Connect(ctrl.Id, ctrl.Id, wx.EVT_LEAVE_WINDOW, self.OnButtonLeave)
        ctrl.Connect(ctrl.Id, ctrl.Id, wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseLost)

    def OnMouseLost(self, evt):
        ctrl = evt.GetEventObject()

        if not ctrl.GetClientRect().Contains(ctrl.ScreenToClient(wx.GetMousePosition())):
            while ctrl.HasCapture():
                ctrl.ReleaseMouse()

            self.HideBubble()

    def showRevision(self):
        return self._showRevision
    showRevision = property(showRevision, setShowRevision)

    def SetUsername(self, username):
        if username:
            self.usernameChoice.SetStringSelection(unicode(username))

    def GetUsername(self):
        return self.usernameChoice.GetStringSelection()

    def SetPassword(self, password):
        self.passwordTextbox.ChangeValue(unicode(password))

    def GetPassword(self):
        return self.passwordTextbox.GetValue()

    def SetSaveInfo(self, shouldSave):
        self.saveCheck.SetValue(shouldSave)

    def GetSaveInfo(self):
        return self.saveCheck.GetValue()

    def SetAutoLogin(self, auto):
        self.autoLoginCheck.SetValue(auto)

    def GetAutoLogin(self):
        return self.autoLoginCheck.GetValue()

    def OnPaint(self, evt):
        dc = wx.AutoBufferedPaintDC(self.panel)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangleRect(self.panel.GetClientRect())

        rect = self.GetClientRect()
        if (self.useGlass()):
            dc.SetBrush(wx.BLACK_BRUSH)
            dc.DrawRectangle(rect.x, rect.y, rect.width, self.glassMarginTop)
            rect.SetHeight(rect.GetHeight() - self.glassMarginTop)
            rect.Offset(wx.Size(0, self.glassMarginTop))

        else:
            dc.SetPen(wx.BLACK_PEN)

        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangleRect(rect)

        dc.DrawBitmap(self._logoBitmap,
                      self.GetClientSize().x / 2 - self._logoBitmap.GetWidth() /2,
                      0 if self.useGlass() else 30,
                      True)

        if self.showRevision:
            self.DrawRevision(dc, rect)

    def OnDoubleClick(self, evt):
        evt.Skip()
        self.showRevision = not self.showRevision
        self.Refresh()

    def OnCloseLink(self, evt):
        self.Close()

    def OnClickSettings(self, evt):
        self.HideBubble()
        linkEvent = wx.HyperlinkEvent(self.panel, self.CONNSETTINGS, '#')
        self.GetEventHandler().ProcessEvent(linkEvent)

    def OnClickHelp(self, evt):
        self.HideBubble()
        event = wx.CommandEvent(wx.EVT_COMMAND_BUTTON_CLICKED, self.HELPBUTTON)
        self.GetEventHandler().ProcessEvent(event)

    def HideBubble(self):
        window = wx.Window.GetCapture()
        if window:
            while(window.HasCapture()):
                window.ReleaseMouse()

        self.GetBubble().Hide()

    def OnButtonHover(self, evt):
        evt.Skip()
        ctrl = evt.GetEventObject()
        if not ctrl:
            return

        if not ctrl.GetClientRect().Contains(evt.GetPosition()):
            while ctrl.HasCapture():
                ctrl.ReleaseMouse()
            self.GetBubble().Show(False)
        elif self.IsActive():
            pt = wx.Point(ctrl.ClientToScreen(wx.Point(ctrl.GetSize().x / 2, 0)))
            ctrl.CaptureMouse()
            self.GetBubble().SetText("Connection Settings" if ctrl is self.settingsButton else "Help")
            self.GetBubble().ShowPointTo(pt)

    def OnButtonLeave(self, evt):
        evt.Skip()
        ctrl = evt.GetEventObject()
        if not ctrl:
            return

        while ctrl.HasCapture():
            ctrl.ReleaseMouse()

        self.GetBubble().Show(False)

    def DrawRevision(self, dc, rect):
        revisionColor = wx.Color(200, 200, 200)
        font = self.GetFont()
        font.SetPointSize(7)
        textExtent = wx.Size(dc.GetTextExtent(self.revisionString))
        dc.SetFont(font)
        dc.SetTextForeground(revisionColor)
        dc.DrawText(self.revisionString, rect.x + 5, rect.GetBottom() - textExtent.y - 18)

    def createComponents(self, showLanguages, profiles):
        panel = self.panel = wx.Panel(self)
        panel.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        panel.Connect(panel.Id, self.panel.Id, wx.EVT_PAINT, self.OnPaint)
        panel.Connect(panel.Id, self.panel.Id, wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

        closeLink = None
        if not self.useGlass():
            closeLink = wx.HyperlinkCtrl(panel, wx.ID_CLOSE, u'X', u'#')
            ModifyFont(closeLink, wx.FONTWEIGHT_BOLD, 14, u'Arial Black', 0)
            closeLink.SetNormalColour(wx.Colour(0xBB, 0xBB, 0xBB))
            closeLink.SetHoverColour(wx.Colour(0x4f, 0x4f, 0x4f))

        self.usernameLabel = wx.StaticText(panel, -1, u'')
        self.usernameChoice = wx.Choice(panel, self.USERNAME,
            wx.DefaultPosition, wx.DefaultSize,
            [p.name for p in profiles])

        self.passwordLabel = wx.StaticText(panel, -1, u'')
        self.passwordTextbox = wx.TextCtrl(panel, self.PASSWORD, u'', wx.DefaultPosition, wx.DefaultSize, wx.TE_PASSWORD)

        self.saveCheck = wx.CheckBox(panel, self.SAVEPASSWORD, u'')
        self.autoLoginCheck = wx.CheckBox(panel, self.AUTOLOGIN, u'')

        self.saveButton = wx.Button(panel, wx.ID_OK, u'')
        self.createProfileButton = wx.Button(panel, self.CREATEPROFILE, u'')
        self.forgotPasswordLink = wx.HyperlinkCtrl(panel, self.FORGOTPASSWORD, u'', u'#')

        self.settingsButton = wx.StaticBitmap(panel, -1, self._settingsBitmap)
        self.settingsButton.Connect(-1, -1, wx.EVT_LEFT_DOWN, self.OnClickSettings)

        helpButton = wx.StaticBitmap(panel, -1, self._helpBitmap)
        helpButton.Connect(-1, -1, wx.EVT_LEFT_DOWN, self.OnClickHelp)
        self.makeTooltipButton(helpButton)

        if (showLanguages):
            self.languageChoice = wx.Choice(panel, self.LANGUAGE)

        self.statusLabel = wx.StaticText(panel, -1, u'', wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTER)
        ModifyFont(self.statusLabel, wx.FONTWEIGHT_BOLD)
        bgColor = wx.WHITE
        for ctrl in (self.usernameLabel, self.passwordLabel, self.saveCheck, self.autoLoginCheck, self.saveButton,
                     self.createProfileButton, self.forgotPasswordLink, self.statusLabel):
            ctrl.SetBackgroundColour(bgColor)

        if closeLink is not None:
            closeLink.SetBackgroundColour(bgColor)

        self.setHyperlinkColor(self.forgotPasswordLink)

        for ctrl in (self.usernameLabel, self.passwordLabel, self.saveCheck, self.autoLoginCheck, self.saveButton,
                     self.createProfileButton, self.forgotPasswordLink):
            setVistaFont(ctrl)

        # Layout

        outerSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainSizer = mainSizer = wx.BoxSizer(wx.VERTICAL)
        subSizer = wx.BoxSizer(wx.HORIZONTAL)

        subSizer.Add(self.saveCheck)
        subSizer.AddSpacer(self.saveButton.GetSize().x / 2)
        subSizer.Add(self.autoLoginCheck)

        if (closeLink):
            linkSizer = wx.BoxSizer(wx.HORIZONTAL)
            linkSizer.Add(closeLink, 0, wx.ALIGN_RIGHT)
            linkSizer.AddSpacer(8)
            mainSizer.Add(linkSizer, 0, wx.ALIGN_RIGHT)

        mainSizer.AddSpacer(self._logoBitmap.GetHeight() + 10)

        if not self.useGlass():
            mainSizer.AddSpacer(10)

        hSizer = wx.BoxSizer(wx.HORIZONTAL)

        hSizer.AddSpacer(7)
        hSizer.AddStretchSpacer(1)
        hSizer.Add(self.statusLabel, 0, wx.EXPAND)
        hSizer.AddStretchSpacer(1)

        usernameHSizer = wx.BoxSizer(wx.HORIZONTAL)
        usernameHSizer.Add(self.usernameLabel)
        usernameHSizer.AddStretchSpacer(1)

        passwordHSizer = wx.BoxSizer(wx.HORIZONTAL)
        passwordHSizer.Add(self.passwordLabel)
        passwordHSizer.AddStretchSpacer()
        passwordHSizer.Add(self.forgotPasswordLink)

        self.controlSizer = controlSizer = wx.BoxSizer(wx.VERTICAL)
        controlSizer.Add(usernameHSizer, 0, wx.EXPAND)
        controlSizer.Add(self.usernameChoice, 0, wx.EXPAND | wx.ALL, 4)
        controlSizer.Add(passwordHSizer, 0, wx.EXPAND)
        controlSizer.Add(self.passwordTextbox, 0, wx.EXPAND | wx.ALL, 4)
        controlSizer.Add(subSizer, 0, wx.ALIGN_CENTER)
        controlSizer.AddSpacer(10)
        controlSizer.Add(hSizer, 0, wx.ALIGN_CENTER)
        controlSizer.AddSpacer(10)
        controlSizer.Add(self.saveButton, 0, wx.ALIGN_CENTER)

        mainSizer.Add(controlSizer, 0, wx.EXPAND)

        self.createProfileSizer = createProfileSizer = wx.BoxSizer(wx.VERTICAL)
        createProfileSizer.SetMinSize(wx.Size(207, 177))
        createProfileSizer.Add(self.createProfileButton, 0, wx.ALIGN_CENTER | wx.TOP, 70)

        mainSizer.Add(createProfileSizer, 0, wx.EXPAND)

        self.set_profiles(profiles)

        mainSizer.AddSpacer(20)

        buttonsH = wx.BoxSizer(wx.HORIZONTAL)
        buttonsH.Add(self.settingsButton, 0, wx.ALIGN_BOTTOM)
        buttonsH.Add(helpButton, 0, wx.ALIGN_BOTTOM | wx.LEFT, 4)
        buttonsH.AddStretchSpacer(1)

        if self._languageBitmap:
            buttonsH.Add(self._languageBitmap, 0, wx.ALIGN_BOTTOM | wx.RIGHT, 4)
        if self.languageChoice:
            buttonsH.Add(self.languageChoice, 0, wx.ALIGN_BOTTOM | wx.RIGHT, 4);

        mainSizer.Add(buttonsH, 0, wx.EXPAND)
        outerSizer.Add(mainSizer, 1, wx.EXPAND | wx.ALL, 4)

        panel.SetSizer(outerSizer)
        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(panel, 1, wx.EXPAND)
        self.SetSizer(s)
        self.UpdateUIStrings()
        self.UpdateUIStrings()

        self.Layout()
        return outerSizer;

    def set_profiles(self, profiles, select_username=None, password=None):
        have_profiles = bool(profiles)
        self.mainSizer.Show(self.controlSizer, have_profiles)
        self.mainSizer.Show(self.createProfileSizer, not have_profiles)
        self.usernameChoice.SetItems([p.name for p in profiles] + 
                ['-'*30, _('Add Profile'), _('Remove Profile')])
        if select_username:
            self.usernameChoice.SetStringSelection(select_username)
        else:
            self.usernameChoice.SetSelection(0)
        if password:
            self.passwordTextbox.SetValue(password)

    def useGlass(self):
        return self._useGlass

    def setupGlass(self):
        if self.useGlass():
            self.glassMarginTop = 10 + self._logoBitmap.GetHeight()
            glassExtendInto(self, 0, 0, self.glassMarginTop, 0)

    def GetLanguageChoice(self):
        return self.languageChoice

    def SetLanguageChoice(self, choice):
        self.languageChoice = choice
    LanguageChoice = property(GetLanguageChoice, SetLanguageChoice)
