from __future__ import with_statement

from common import profile
from config import platformName

from gui.uberwidgets.formattedinput2.formatprefsmixin import PrefInput
import wx
import os
import sys
import stdpaths
from gui.pref.prefcontrols import *
import platform

if platformName == 'mac' and int(platform.mac_ver()[0][3]) >= 5:
    from gui.native.mac.maciconeditor import IconEditor
else:
    from gui.pref.iconeditor import IconEditor

def save_profile(new_profile):
    profile.set_profile_blob(new_profile)

def get_promote():
    return profile.prefs['profile.promote']


def get_shortcut(pth):
    import comtypes.client as client
    shell = client.CreateObject('WScript.Shell')
    scut = client.dynamic.Dispatch(shell.CreateShortcut(pth))

    return scut

def on_startup_change(new):

    if platformName == "mac":
        import loginitems
        appdir = os.path.abspath(os.path.join(sys.argv[0], "..", "..", ".."))

        if new and not loginitems.hasitem(appdir):
            loginitems.additem(appdir)
        elif not new and loginitems.hasitem(appdir):
            loginitems.removeitem("Digsby")

        return

    from path import path

    shortcuts = startup_shortcuts()
    if new and not shortcuts:
        import sys, locale
        exe = sys.executable.decode('locale')

        pth = stdpaths.userstartup /'digsby.lnk'
        scut = get_shortcut(pth)

        scut.TargetPath = exe.encode('filesys')
        scut.WorkingDirectory = unicode(path(exe).parent).encode('filesys')
        scut.Save()

    elif shortcuts and not new:
        # delete shortcuts
        for scut in shortcuts:
            try:
                scut.remove()
            except Exception, e:
                log.info('Error removing shortcut %r: %r', scut, e)
                continue

def startup_shortcuts():
    if "wxMSW" in wx.PlatformInfo:
        shortcuts = digsby_shortcuts(stdpaths.userstartup)
        shortcuts.extend(digsby_shortcuts(stdpaths.startup))

        return shortcuts
    else:
        return False

def digsby_shortcuts(dir):

    from path import path
    import sys, locale

    res = []

    # FIXME: This shortcuts approach is, I think, unique to Windows. I think both
    # Mac and Linux deal with registering apps in system prefs or the equivalent config files.
    if not "wxMSW" in wx.PlatformInfo:
        return res

    dir = path(dir)
    exe = path(sys.executable.decode('locale')).basename().encode('filesys')

    if not dir.isdir():
        print 'warning, no startup dir', dir
        return []

    for lnk in dir.walk('*.lnk'):
        scut = get_shortcut(lnk)
        if exe == path(scut.TargetPath).basename():
            res.append(lnk)

    return res


from gui.uberwidgets.PrefPanel import PrefPanel,PrefCollection
def panel(panel, sizer, addgroup, exithooks):

    startup = wx.CheckBox(panel, label=_('&Launch Digsby when this computer starts'))
    try:
        startupval = bool(startup_shortcuts())
    except Exception:
        startupval = False
        startup.Disable()

    startup.Value = startupval
    startup.Bind(wx.EVT_CHECKBOX, lambda e: on_startup_change(startup.Value))

    # FIXME: Implement this for OS X (and GTK/Linux of course!)

    grp1 = PrefPanel( panel,
                      PrefCollection(
                          startup,
                          #Check('startup.launch_on_login', _('&Launch Digsby when this computer starts')),
                          #Check('startup.default_im_check', _('Check to see if &Digsby is the default IM client on this computer')),
                          Check('digsby.updater.auto_download', _("&Automatically download software updates")),
                          Check('login.reconnect.attempt', _('&If connection to IM service is lost, automatically attempt to reconnect')),
                          Check('social.feed_ads', _('Show trending news articles in social network feeds (powered by OneRiot)')),
                          layout = VSizer(),
                          itemoptions = (0,wx.BOTTOM|wx.TOP,3)
                      ),
                      _('General Options')
                    )


    p, input, chk = build_profile_panel(panel)

    panel.get_profile = lambda: input.GetFormattedValue()
    panel.get_promote = lambda: chk.Value

    exithooks += lambda: save_profile(panel.get_profile())
    #exithooks += lambda: input.SaveStyle(input.formatpref)

    profile_grp = PrefPanel(panel, p, _('Profile (AIM Only)'))

    ico = build_buddy_icon_panel(panel, 'bicon')

    buddy_icon_grp = PrefPanel(panel, ico,_('Buddy Icon'))

    # Profile and Buddy Icon sizer
    innersz = wx.BoxSizer(wx.HORIZONTAL)
    innersz.Add(profile_grp, 1, wx.EXPAND)
    innersz.Add(buddy_icon_grp, 0, wx.LEFT, 6)

    lang_choices = [
        ('en', 'English'),
    ]

#    langpanel = VSizer()
    langchoice = Choice('locale', lang_choices)(panel)
#    langchoice.SetMinSize((200,-1))
#    langpanel.Add(langchoice)

    lang_grp = PrefPanel(panel, langchoice,_('Language'))

    sizer.AddMany([(grp1,     0, wx.EXPAND | wx.ALL, 3),
                   (innersz,  0, wx.EXPAND | wx.ALL, 3),
                   (lang_grp, 0, wx.EXPAND | wx.ALL, 3),
                   ])#(40, 40)
    sizer.AddStretchSpacer()

    wx.CallAfter(input.SetFormattedValue, profile.profile)

    panel.Layout()

    return panel


class BitmapPanel(wx.Panel):
    def __init__(self, *a, **k):
        wx.Panel.__init__(self, *a, **k)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self._icon = None

    icon = property(lambda self: self._icon,                        # get
                    lambda self, i: (setattr(self, '_icon', i),     # set
                                     self.Refresh()))

    def OnPaint(self, e):
        e.Skip()
        icon, dc = self.icon, wx.PaintDC(self)
        if icon is not None:
            # draw a centered buddy icon
            w, h = self.Size
            assert isinstance(icon, wx.Bitmap), str(type(icon))

            icopos = (w / 2 - icon.Width  / 2, h / 2 - icon.Height / 2 )

            dc.DrawBitmap(icon, *icopos)

            dc.Brush = wx.TRANSPARENT_BRUSH
            dc.Pen = wx.Pen(wx.Color(213,213,213))
            dc.DrawRectangleRect(wx.RectPS(icopos,(icon.Width,icon.Height)))

def build_buddy_icon_panel(parent, prefix):
    p = wx.Panel(parent)

    icon_panel = BitmapPanel(p, size = (128, 128))

    picon = profile.get_icon_bitmap()

    if picon is not None:
        icon_panel.icon = picon.ResizedSmaller(128)
    else:
        icon_panel.icon = None

    button = wx.Button(p, -1, _('Change'))
    if platformName == 'mac':
        button.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)
        icon_button_flags = 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM, 4
    else:
        icon_button_flags = 0, wx.EXPAND | wx.TOP, 5

    def changeicon(e):
        if IconEditor.RaiseExisting():
            return

        ie = IconEditor(p, profile.get_icon_bytes() or '')

        def onOK():
            if ie.ImageChanged:
                log.info('iconeditor.ImageChanged = True')
                import hub; h = hub.get_instance()
                bytes = ie.Bytes
                h.set_buddy_icon_file(bytes)
                icon_panel.icon = profile.get_icon_bitmap()

        ie.Prompt(onOK)

    button.Bind(wx.EVT_BUTTON, changeicon)

    sz = p.Sizer = wx.BoxSizer(wx.VERTICAL)
    sz.Add(icon_panel)
    sz.Add(button, *icon_button_flags)
    return p


def build_profile_panel(parent):
    p = wx.Panel(parent)

    input = PrefInput(p, autosize = False, multiFormat = True, showFormattingBar = (platformName != 'mac'), skin = 'AppDefaults.FormattingBar', formatpref = 'profile.formatting')

    chk = Check('profile.promote', _('&Promote Digsby in my AIM profile'))(p)
    chk.Value = get_promote()

    if platformName == 'mac':
        # just show one font button on mac
        checkbox = chk
        chk = wx.BoxSizer(wx.HORIZONTAL)
        chk.Add(checkbox)
        chk.AddStretchSpacer(1)
        chk.Add(input.CreateFontButton(p))
        chk.AddSpacer(4)
        chk_sizer_flags = 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5
    else:
        chk_sizer_flags = 0, wx.TOP, 3

    s =  p.Sizer = VSizer()
    s.Add(input, 1, wx.EXPAND|wx.ALL, 1)
    s.Add(chk, *chk_sizer_flags)


    def OnPaintWithOutline(event):
        dc = wx.AutoBufferedPaintDC(p)

        rect = wx.RectS(p.Size)
        irect = wx.Rect(input.Rect)
        irect.Inflate(1, 1)

        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)

        dc.Pen = wx.Pen(wx.Color(213, 213, 213))
        dc.DrawRectangleRect(irect)

    p.Bind(wx.EVT_PAINT, OnPaintWithOutline)


    return p, input, chk


def build_name_panel(parent):
    s = wx.BoxSizer(wx.VERTICAL)
    txt = Text(parent, 'profile.name')
    s.Add(txt)
    return s
