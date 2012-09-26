import contextlib
import ctypes

from ctypes import byref
from ctypes.wintypes import SHORT, WORD

# See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp
# for information on Windows APIs.
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE= -11
STD_ERROR_HANDLE = -12

FOREGROUND_BLUE = 0x01 # text color contains blue.
FOREGROUND_GREEN= 0x02 # text color contains green.
FOREGROUND_RED  = 0x04 # text color contains red.
FOREGROUND_INTENSITY = 0x08 # text color is intensified.
BACKGROUND_BLUE = 0x10 # background color contains blue.
BACKGROUND_GREEN= 0x20 # background color contains green.
BACKGROUND_RED  = 0x40 # background color contains red.
BACKGROUND_INTENSITY = 0x80 # background color is intensified.


kernel32 = ctypes.windll.kernel32

SetConsoleTextAttribute = kernel32.SetConsoleTextAttribute
GetConsoleScreenBufferInfo = kernel32.GetConsoleScreenBufferInfo
std_out_handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

class COORD(ctypes.Structure):
    _fields_ = [('X', SHORT),
                ('Y', SHORT)]

class SMALL_RECT(ctypes.Structure):
    _fields_ = [('Left', SHORT),
                ('Top', SHORT),
                ('Right', SHORT),
                ('Bottom', SHORT)]

class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [('dwSize', COORD),
                ('dwCursorPosition', COORD),
                ('wAttributes', WORD),
                ('srWindow', SMALL_RECT),
                ('dwMaximumWindowSize', COORD)]

screen_info = CONSOLE_SCREEN_BUFFER_INFO()

def set_color(color, handle=std_out_handle):
    """(color) -> BOOL
    
    Example: set_color(FOREGROUND_GREEN | FOREGROUND_INTENSITY)
    """
    return SetConsoleTextAttribute(handle, color)

colormap = dict(grey = 0x08,
                white = 0x07,
                red   = FOREGROUND_RED,
                green = FOREGROUND_GREEN,
                blue  = FOREGROUND_BLUE,
                yellow = FOREGROUND_RED | FOREGROUND_GREEN,
                bold  = FOREGROUND_INTENSITY)

@contextlib.contextmanager
def color(color):
    color_int = 0
    for c in color.split():
        color_int |= colormap.get(c)

    GetConsoleScreenBufferInfo(std_out_handle, byref(screen_info))
    set_color(color_int)
    try:
        yield
    finally:
        set_color(screen_info.wAttributes)

def main():
    with color('bold red'):
        print 'red'
    with color('grey'): print 'grey'
    with color('white'): print 'white'
    print 'normal'

if __name__ == '__main__':
    main()
