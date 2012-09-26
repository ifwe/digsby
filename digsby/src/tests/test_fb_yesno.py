
def show_dialog():
    from facebook.fbgui import show_achievements_dialog
    from facebook.fbacct import UPGRADE_QUESTION

    def success(e):
        print 'success', e
    show_achievements_dialog(None, 'New Facebook', UPGRADE_QUESTION, success)

def main():
    from tests.testapp import testapp
    app = testapp()

    show_dialog()


    app.MainLoop()


if __name__ == '__main__':
    main()
