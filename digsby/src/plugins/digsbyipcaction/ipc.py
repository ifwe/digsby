'''
simple IPC

todo: multiple servers
'''
import config

if config.platform == 'win':
    import win32events as win
    import ctypes
    import wx

    hidden_frame = None
    receiver = None

    WINDOW_CLASS = 'wxWindowClassNR'
    RECEIVER_GUID = '60210be0-de97-11de-8a39-0800200c9a66'
    MESSAGE_GUID  = '7e01e6f0-de99-11de-8a39-0800200c9a66'
    WM_COPYDATA = 0x4a

    class COPYDATASTRUCT(ctypes.Structure):
        _fields_ = [
            ('dwData', ctypes.wintypes.DWORD), # will fail on 64 bit
            ('cbData', ctypes.wintypes.DWORD),
            ('lpData', ctypes.c_void_p),
        ]

    def listen(receiver_cb):
        global hidden_frame, receiver
        if hidden_frame is not None:
            hidden_frame.Destroy()

        receiver = receiver_cb

        hidden_frame = wx.Frame(None, title=RECEIVER_GUID)
        win.bindwin32(hidden_frame, WM_COPYDATA, on_copydata)

    def on_copydata(hWnd, msg, wParam, lParam):
        if receiver is not None and lParam:
            cds = COPYDATASTRUCT.from_address(lParam)
            if cds.dwData == hash(MESSAGE_GUID):
                message = ctypes.string_at(cds.lpData, cds.cbData-1) # minus one for NULL byte at end
                receiver(message)

    def send_message(message):
        assert isinstance(message, str)

        hwnd = ctypes.windll.user32.FindWindowA(WINDOW_CLASS, RECEIVER_GUID)
        if not hwnd:
            return False

        sender_hwnd = 0
        buf = ctypes.create_string_buffer(message)

        copydata = COPYDATASTRUCT()
        copydata.dwData = hash(MESSAGE_GUID)
        copydata.cbData = buf._length_
        copydata.lpData = ctypes.cast(buf, ctypes.c_void_p)

        return ctypes.windll.user32.SendMessageA(hwnd, WM_COPYDATA, sender_hwnd, ctypes.byref(copydata))

else:
    def listen(receiver_cb):
        pass

    def send_message(message):
        pass

