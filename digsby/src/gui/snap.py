'''
Window snapping.

>> f = wx.Frame(None, -1, 'My Frame')
>> f.Snap = True

TODO:
- Mac/Linux implementations
'''

import wx

if 'wxMSW' in wx.PlatformInfo:
    from cgui import WindowSnapper as Snapper
else:

    #
    # Other platforms: not implemented.
    #

    class Snapper(object):
        def __init__(self, frame, *a, **k): pass
        def SetDocked(self, val): pass
        def SetEnabled(self, val): pass
        def IsEnabled(self): return False

def SetSnap(win, snapping, filter_func = None):
    if not isinstance(snapping, bool):
        raise TypeError('SetSnap first argument must be a bool, got type %r' % type(snapping))

    @wx.CallAfter
    def later():
        try:
            snapper = win._snapper
        except AttributeError:
            snapper = win._snapper = Snapper(win, 12, snapping)

            # have the Docker object inform us when we're docked, so that the
            # two objects don't interfere with another.
            docker = getattr(win, 'docker', None)
            if docker is not None:
                docker.OnDock += win._snapper.SetDocked

        else:
            win._snapper.SetEnabled(snapping)

def GetSnap(win):
    try:
        snapper = win._snapper
    except AttributeError:
        return False
    else:
        return snapper.IsEnabled()

#
# Add a "Snap" property to TopLevelWindow.
#

import new
wx.TopLevelWindow.GetSnap = new.instancemethod(GetSnap, None, wx.TopLevelWindow)
wx.TopLevelWindow.SetSnap = new.instancemethod(SetSnap, None, wx.TopLevelWindow)
wx.TopLevelWindow.Snap = property(GetSnap, SetSnap)

