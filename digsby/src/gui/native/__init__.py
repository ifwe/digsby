import wx, sys
from logging import getLogger; log = getLogger('Not Implemented')

def notImplemented():

    # prep the error message
    caller_info = sys._getframe(1).f_code
    notImplMessage = "Unimplemented function. Function %s at line %d of file %s" \
                % (caller_info.co_name, caller_info.co_firstlineno, caller_info.co_filename)

    if getattr(sys, "notImplementedIsError", False):
        raise NotImplementedError(notImplMessage)
    else:
        log.error(notImplMessage)

def getPlatformDir():
    if "wxMSW" in wx.PlatformInfo:
        return "win"
    elif "wxMac" in wx.PlatformInfo:
        return "mac"
    elif "wxGTK" in wx.PlatformInfo:
        return "gtk"
    else:
        notImplemented()

def extendStdPaths():
    exec("import %s.%spaths" % (getPlatformDir(), getPlatformDir()))

if 'wxMSW' in wx.PlatformInfo:
    def lower_memory_footprint(): #lazy call for lazyModule('process')
        import win.process
        win.process.page_out_ram()
    from .memfootprint import memory_event
else:
    def lower_memory_footprint():
        pass

    def memory_event():
        pass

# uhm this looks bad. do not want
# we need a way to make stuff in the 'win' module be imported here if platform is windows, etc.
exec("from %s import *" % getPlatformDir())