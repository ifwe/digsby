import wx
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.simplemenu import SimpleMenu,SimpleMenuItem
from gui import skin
from gui.uberwidgets.UberBar import UberBar
from random import randint

def buttons(parent):

    yahoo = skin.load_bitmap('../../protocols/yahoo.png')

    s = 'button'
    b1 = UberButton(parent, -1, 'Skinned', skin = s)
    b2 = UberButton(parent, -1, 'Native',    skin = None)
    b3 = UberButton(parent, -1, 'SkinnedPic', skin = s, icon = yahoo)
    b4 = UberButton(parent, -1, 'NativePic', skin = None, icon = yahoo)

    return [b1, b2, b3, b4]

def combos(parent):
    uct = UberCombo(parent, value='test', skinkey = 'combobox', typeable = True, size=(100, 20))
    uct.AppendItem(SimpleMenuItem('Sample Item 1'))
    uct.AppendItem(SimpleMenuItem('Sample Item 2'))
    uct.AppendItem(SimpleMenuItem(id=-1))
    uct.AppendItem(SimpleMenuItem('Sample Item 3'))

    return [uct]


def progressbars(parent, sizer):
    from gui.uberwidgets.UberProgressBar import UberProgressBar


    sizer.Add(wx.StaticText(parent, -1, 'With label, no size:'))
    b1 = UberProgressBar(parent, wx.NewId(), 100, 'progressbar', showlabel = True)
    sizer.Add(b1, 0, wx.EXPAND)

    sizer.Add(wx.StaticText(parent, -1, 'No label, with size:'))
    b2 = UberProgressBar(parent, wx.NewId(), 100, 'progressbar', showlabel = False, size=(300,20))
    sizer.Add(b2, 0, wx.EXPAND)

    bars = [b1, b2]

    class T(wx.Timer):
        def Notify(self):
            for b in bars:
                newval = (b.GetValue() + randint(3, 15)) % 100
                b.SetValue(newval)

    b.t = T()
    b.t.Start(200)



if __name__ == '__main__':

    import re
    debug_re = re.compile('line (\d+), column (\d+)')

    skinyaml = '''
Common:
- &DigsGreenV gradient vertical 0xC8FFC8 0x55FF55

Button:
  Backgrounds:
    Normal: *DigsGreenV
    Down: gradient vertical 0x007700 0x00CC00
    Active: gradient vertical 0xC8FFEE 0x55FFEE
    Hover: gradient vertical 0x00CC00 0x00FF00
    ActiveHover: gradient vertical 0x00CCEE 0x00FFEE
    Disabled: gradient vertical 0x7D7D7D 0xEDEDED
    Notify: gradient vertical 0xFFFFC8 0xFFFF55
  FontColors:
    Normal: '0xFF0000'
    Down: '0xFF0000'
    Active: '0xFF0000'
    Hover: '0xFF0000'
    ActiveHover: '0xFF0000'
    Disabled: '0xFF0000'
    Notify: '0xFF0000'
  MenuIcon: dropmenuicon.png
  Padding: [ 3 , 3 ]                      #x,y between all items

#### SHOULD BE LIKE REGULAR MENU - ONE USED THROUGHOUT
SimpleMenu:
  SubmenuIcon: submenuicon.png
  SeparatorImage: separator2.png
  Padding: 0                            # left right between items
  Border: 5
  Backgrounds:
    Frame: gradient red white blue #0x000000 0xFFFFFF #pic gradient or color
    Menu: 0xFFFFFF border red dot #selectedtab.png 6 6 -6 -7 #gradient vertical 0x00CC00 0x00FF00
    #Item: 0xCCCCCC rounded shadow bevel #each item instead of menu
    Selection: square_grad.png 6 6 -6 -6
  Font: comic sans ms
  Fontcolors:
    Normal: '0x00FF00'
    Selection: white

#### ?????
#### USE GENERIC (comboboxskin) or separate for each place
#### SINGLE BUTTON SKIN MODE !!!!!
combobox:
  Backgrounds:
    Normal: *DigsGreenV
    Active: red #white
    hover: yellow        #not implemented
  fontcolors:
    normal: black
    active: white
    Hover: white         #not implemented
  font: comic sans ms
  dropdownbutton:
    Icon: dropmenuicon.png
    Skin: Button
  cyclebutton:
    Skin: Button
  menu:
    Skin: SimpleMenu
  padding: 3

Menu:
  Margins: [ 3 , 3 ]
  Border: 2                  #frame
  Iconsize: 16
  Font: comic sans ms
  Backgrounds:
    Frame: black #menubgofuglyness.png 38 38 -38 -38
    menu: black
    item: #white frame1.png 8 8 -8 -8 #White
    #disabled:
    Selection: vertical 0xC8FFC8 0x55FF55
    #Gutter: selectedtab.png 6 6 -6 -7 #gradient vertical 0x00CC00 0x00FF00
  FontColors:
    Normal: white
    Selection: black
    Disabled: gray
  SeparatorImage: separator2.png
  SubmenuIcon: submenuicon.png
  CheckedIcon: checked.png
  #uncheckedicon:

#### OVERRIDE'S DEFAULT OPERATING SYSTEM MENUBAR AT THE TOP OF THE BUDDY LIST
MenuBar:
  padding: 3
  background: *DigsGreenV
  itemskin: Button

#### OVERRIDE'S DEFAULT OPERATING SYSTEM PROGRESS BAR USED FOR FILE TRANSFERS
#### MERGE INFO FILE TRANSFER DIALOG SKIN
Progressbar:
  #Padding: 4
  #Style: Repeat or none
  Backgrounds:
    Normal: progressbg.png 9 1 -9 -1
    Fill: progressfg.png 9 1 -9 -1
  #font not needed
  #fontcolors     not needed
    #normal
    #fill

'''

    from gui.skin import SkinException

    a = wx.PySimpleApp()

    #set_yaml('../../res/skins/default', skinyaml)
    from tests.testapp import testapp
    app = testapp('../..', skinname = 'silverblue')

    f = wx.Frame(None, -1, 'UberWidgets', size = (800, 750))
    f.Bind(wx.EVT_CLOSE, lambda e: a.ExitMainLoop())

    split = wx.SplitterWindow(f, style = wx.SP_LIVE_UPDATE)

    panel = wx.Panel(split)
    f.Sizer = wx.BoxSizer(wx.VERTICAL)
    #f.Sizer.Add(menubar(f), 0, wx.EXPAND)
    f.Sizer.Add(split, 1, wx.EXPAND)

    def box(title):
        box = wx.StaticBox(panel, -1, title)
        sz = wx.StaticBoxSizer(box, wx.VERTICAL)
        return sz

    sz = panel.Sizer = wx.GridSizer(3, 3)

    buttongroup = box('buttons')
    for i, b in enumerate(buttons(panel)): buttongroup.Add(b, 0, wx.EXPAND | wx.ALL, 3)

    combogroup = box('combos')
    for c in combos(panel): combogroup.Add(c, 0, wx.EXPAND | wx.ALL, 3)

    progressgrp = box('progress')
    progressbars(panel, progressgrp)

    sz.AddMany([(buttongroup, 1, wx.EXPAND),
                (combogroup, 1, wx.EXPAND),
                (progressgrp, 1, wx.EXPAND)])


    epanel = wx.Panel(split)
    txt = wx.TextCtrl(epanel, -1, skinyaml, style = wx.TE_MULTILINE | wx.TE_DONTWRAP)
    save = wx.Button(epanel, -1, '&Save'); save.Enable(False)
    undo = wx.Button(epanel, -1, '&Undo'); undo.Enable(False)

    def doundo(e):
        txt.SetValue(skinyaml)
        updatebuttons()

    def dosave(e):
        global skinyaml
        skinyaml = txt.GetValue()

        try: set_yaml('../../res/skins/default', skinyaml)
        except SkinException, e:
            m = debug_re.search(str(e))
            if m: txt.SetInsertionPoint(txt.XYToPosition(*(int(c) for c in reversed(m.groups()))))
            raise

        txt.SetModified(False)
        updatebuttons()



    undo.Bind(wx.EVT_BUTTON, doundo)
    save.Bind(wx.EVT_BUTTON, dosave)

    def updatebuttons(e = None):
        undo.Enable(txt.IsModified())
        save.Enable(txt.IsModified())

    txt.Bind(wx.EVT_TEXT, updatebuttons)
    epanel.Sizer = s = wx.BoxSizer(wx.VERTICAL)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    buttons.AddStretchSpacer(1)
    buttons.Add(undo)
    buttons.Add(save, 0, wx.LEFT, 7)

    s.Add(txt, 1, wx.EXPAND)
    s.Add(buttons, 0, wx.EXPAND | wx.ALL, 5)

    split.SplitHorizontally(panel, epanel)

    f.Show()
    a.MainLoop()