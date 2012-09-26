import wx

def main():
    from tests.testapp import testapp
    from tests.mock.mockbuddy import MockBuddy
    a = testapp()

    from gui.imwin.messagearea import MessageArea
    from gui.imwin.styles import get_theme
    from common.logger import history_from_files
    from gui import skin

    f = wx.Frame(None, title = 'Conversation Preview')
    msgarea = MessageArea(f)

    buddy = MockBuddy('digsby01')

    theme = get_theme('MiniBubble2', None)
    msgarea.init_content(theme, buddy.alias, buddy, show_history = False)

    msgs = history_from_files([skin.resourcedir() / 'Example Conversation.html'])
    msgarea.replay_messages(msgs, buddy)

    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()
