import util, wx
from tests.mock.mockbuddy import MockBuddy
from tests.mock.mockmetacontact import MockMetaContact
from gui.buddylist import BuddyList
from common import caps
import random

away,idle,available='away','idle','available'

class MockBuddyList(BuddyList):
    def __init__(self, parent):
        from contacts.Group import DGroup

        AIM=('aim',[caps.BLOCKABLE, caps.EMAIL, caps.FILES, caps.IM, caps.PICTURES, caps.SMS])
        MSN=('msn',[caps.BLOCKABLE, caps.EMAIL, caps.FILES, caps.IM])
        JBR=('jabber',[caps.EMAIL, caps.FILES, caps.IM])
        YHO=('yahoo',[caps.BLOCKABLE, caps.EMAIL, caps.FILES, caps.IM, caps.SMS])

        self.dude=MockMetaContact(
                       'MetaDude',
                        MockBuddy('Dude1',0,*AIM),
                        MockBuddy('Dude2',0,*YHO),
                        MockBuddy('Dude3',0,*MSN),
                        MockBuddy('Dude4',0,*JBR),
                   )

        grp = DGroup('coworkers', [], [], [
                   MockBuddy('Aaron',0,*JBR),
                   MockBuddy('Chris',0,*JBR),
                   MockBuddy('Jeff',0,*AIM),
                   MockBuddy('Kevin',0,*YHO),
                   MockBuddy('Mike',0,*MSN),
                   MockBuddy('Steve',0,*AIM),
                   self.dude
              ]
           )


        from gui.treelist import expanded_id
        BuddyList.__init__(self, parent, expanded = [expanded_id(grp)])
        self.set_root([grp])

statuses = 'away available idle'.split()
def OnButton(event):
    print 'All Away'
    f.MBL.dude[0].status=random.choice(statuses)
    f.MBL.dude[1].status=random.choice(statuses)
    f.MBL.dude[2].status=random.choice(statuses)
    f.MBL.dude[3].status=random.choice(statuses)



if __name__ == '__main__':
    import gettext, sys
    from gui.skin import skininit
    gettext.install('Digsby', './locale', unicode=True)

    app = wx.PySimpleApp()
    skininit('../../../res')
    f = wx.Frame(None, -1, 'BuddyList test')
    f.Sizer=wx.BoxSizer(wx.VERTICAL)
    f.MBL=MockBuddyList(f)
    f.Sizer.Add(f.MBL,1,wx.EXPAND)
    rrb=wx.Button(f,-1,'Randomize')
    rrb.Bind(wx.EVT_BUTTON,OnButton)
    f.Sizer.Add(rrb,0,wx.EXPAND)
    f.Size=(200,400)
    f.Show()
    f.Bind(wx.EVT_CLOSE, lambda e: app.Exit())
    app.MainLoop()