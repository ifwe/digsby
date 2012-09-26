
def bindwin32(win, msg, callback):
    if not hasattr(win, '_win32binder'):
        from cgui import PlatformMessageBinder
        win._win32binder = PlatformMessageBinder.ForWindow(win)

    win._win32binder.Bind(msg, callback)

def unbindwin32(win, msg, callback):
    if not hasattr(win, '_win32binder'):
        return

    win._win32binder.Unbind(msg, callback)

