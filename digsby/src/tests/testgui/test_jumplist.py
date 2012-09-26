import wx

APP_ID = u'TestJumpListApp'

def set_app_id():
    import ctypes

    try:
        SetAppID = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
    except AttributeError:
        return

    SetAppID(APP_ID)

def main():
    set_app_id()
    app = wx.App()
    import cgui
    assert cgui.SetUpJumpList(APP_ID, [(u'test', u'bc', u're', 4)])

if __name__ == '__main__':
    main()
