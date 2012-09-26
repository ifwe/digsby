import  wx
from tests.mock.mockbuddy import MockBuddy
from common import caps
from util.observe import ObservableList

from gui.imwin.roomlist import RoomListPanel

def main():
    from tests.testapp import testapp
    a = testapp(skinname='Windows 7')
    f = wx.Frame(None, -1, 'roomlist')


    AIM=('aim',    [caps.BLOCKABLE, caps.EMAIL, caps.FILES, caps.IM, caps.PICTURES, caps.SMS])
    MSN=('msn',    [caps.BLOCKABLE, caps.EMAIL, caps.FILES, caps.IM])
    JBR=('jabber', [caps.EMAIL, caps.FILES, caps.IM])
    YHO=('yahoo',  [caps.BLOCKABLE, caps.EMAIL, caps.FILES, caps.IM, caps.SMS])

    global contacts
    contacts = ObservableList([MockBuddy('Aaron', 'away', *JBR),
                               MockBuddy('Chris', 'available', *JBR),
                               MockBuddy('Jeff',  'offline', *AIM),
                               MockBuddy('Kevin', 'away', *YHO),
                               MockBuddy('Mike',  'available', *MSN),

                               MockBuddy('Steve', 'offline', *AIM),])

    buddies = dict((c.name, c) for c in contacts)

    contacts.extend([
                               MockBuddy('Agatha',  'offline', *AIM),
                               MockBuddy('Abel', 'away', *YHO),
                               MockBuddy('Adam',  'available', *MSN),
                               MockBuddy('Amanda',  'offline', *AIM),
                               MockBuddy('Beatrice',  'offline', *AIM),
                               MockBuddy('Betty', 'away', *YHO),
                               MockBuddy('Brian',  'available', *MSN),
                               MockBuddy('Biff', 'away', *YHO),
                               MockBuddy('Bart',  'available', *MSN),
    ])


    rl = RoomListPanel(f, buddies)
    rl.RoomList = contacts

    f.SetSize((200,400))
    f.Show()

    a.MainLoop()


if __name__ == '__main__':
    main()
