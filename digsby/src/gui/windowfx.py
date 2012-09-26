'''windowfx.py - simple wxWindow effects

Usage:
>>> import windowfx

Fade a window in:
>>> myFrame = wx.Frame(None, -1, "My Frame!")
>>> windowfx.fadein(myFrame)

Fade a window in slowly:
>> windowfx.fadein(myFrame, 'slow')

Possible speeds are slow, normal, quick, fast, and xfast. You can also specify
a number.

Set a window to be half transparent:
>>> windowfx.setalpha(myFrame, 128)

Fade a window out:
>>> windowfx.fadeout(myFrame)    # NOTE: This will call myFrame.Destroy()
                                 # see fadeout's docstring for alternatives

Draw a native button:
  dc = wx.PaintDC(f)
  windowfx.drawnative(dc.GetHDC(), (10,10,100,40), windowfx.controls.buttonpush)

'''
from __future__ import division
from __future__ import with_statement
import wx
from traceback import print_exc
import ctypes
from util.vec import vector
from util.primitives.misc import clamp

from wx import RectPS

from gui.textutil import default_font
from gui.native.effects import *

USE_HIRES_TIMER = False

# adjustable fade speeds
fade_speeds = dict(
   xslow = 3,
   slow = 7,
   normal = 13,
   quick  = 25,
   fast   = 37,
   xfast  = 50
)

'''
  Native window control values

  for example:
    dc = wx.PaintDC(f)
    drawnative(dc.GetHDC(), (10,10,100,40), controls.buttonpush)

  also specify an optional state
    drawnative(dc.GetHDC(), (10,10,100,40), controls.buttonpush, states.pushed)
'''

from wx import ImageFromBitmap, BitmapFromImage, RegionFromBitmap

def ApplyVirtualSmokeAndMirrors(dc,shape):
    if shape:
        if isinstance(shape, wx.Region):
            region=shape
        else:
            if not shape.GetMask():
                image  = ImageFromBitmap(shape)
                image.ConvertAlphaToMask()
                bitmap = BitmapFromImage(image)
            else:
                bitmap = shape
            region = RegionFromBitmap(bitmap)

            # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/gdi/regions_2h0u.asp
            region.Offset(-1,-1)

        dc.SetClippingRegionAsRegion(region)

def rectdiff(r1, r2):
    'Returns the intersection of two rectangles.'

    tmp = wx.Rect()
    if r1.Intersects(r2):
        tmp = wx.Rect(max(r1.x, r2.x), max(r1.y, r2.y))

        myBR, BR = r1.GetBottomRight(), r2.GetBottomRight()
        tmp.SetWidth(  min(myBR.x, BR.x) - tmp.x )
        tmp.SetHeight( min(myBR.y, BR.y) - tmp.y )
    return tmp

def fadein(window, speed = 'normal', to = 255):
    'Fades in a window.'

    setalpha(window, 0)
    try:
        window.ShowNoActivate(True)
    except:
        window.Show(True)
    return Fader(window, step = _speed_val(speed), end = to)

def fadeout(window, speed = 'normal', on_done = None, from_ = None):
    '''
    Fades out a window.

    By default, the window's Destroy function will be invoked when it's
    transparency hits zero, but you can provide any callable in on_done.
    '''
    return Fader( window, from_ or getalpha(window), 0, -_speed_val(speed),
                  on_done = on_done or (lambda: window.Destroy()) )

# W2K hack
if 'wxMSW' in wx.PlatformInfo:
    import ctypes
    try:
        ctypes.windll.user32.SetLayeredWindowAttributes
    except AttributeError:
        #
        # windows 2000 without one of the newer service packs completely lacks
        # SetLayeredWindowAttributes -- just disable fading there.
        #
        def fadein(window, speed = 'normal', to = 255):
            try:
                window.Show(True, False)
            except:
                window.Show(True)
        def fadeout(window, speed = 'normal', on_done = None, from_ = None):
            on_done = on_done or (lambda: window.Destroy())
            window.Hide()
            try:
                on_done()
            except Exception:
                print_exc()

# the implementations for setalpha (window transparency) vary by platfrom:
if not 'setalpha' in locals():
    raise AssertionError('Sorry, platform is not supported. Your platform info: %s' % \
                         ', '.join(wx.PlatformInfo))

setalpha.__doc__  = "Sets a window's transparency. 0 is completely transparent, 255 opaque."
setalpha.__name__ = 'setalpha'

#
#
#

def _speed_val(speed):
    if isinstance(speed, basestring):
        if not speed in fade_speeds:
            raise KeyError('speed must be one of [%s] or an integer from 0 to 255' % \
                           ', '.join(fade_speeds.keys()))
        speed = fade_speeds[speed]

    return speed

class FXTimer(object):
    '''Invokes a callback over and over until it returns an expression
    that evaluates to False.'''


    def __init__(self, callback, tick=4, on_done = None):
        self.timer = wx.PyTimer(self.on_tick)
        self.callback = callback
        self.on_done = on_done
        self.timer.Start(tick)

    def on_tick(self):
        if not self.callback():
            self.timer.Stop()
            del self.timer
            if self.on_done is not None:
                self.on_done()

    def stop(self):
        if hasattr(self, 'timer'):
            self.timer.Stop()

class GenTimer(object):
    'Calls a generator over and over until a StopIteration is raised.'

    def __init__(self, gen, callback, on_tick=None, on_done=lambda: None):
        self.timer = wx.PyTimer(self.on_tick)

        self.tick_cb = on_tick
        self.gen = gen
        self.callback = callback
        self.on_done = on_done

    def on_tick(self):
        try:
            val = self.gen.next()
            self.callback(val)

            if self.tick_cb:
                self.tick_cb()

        except StopIteration:
            pass
        except Exception:
            print_exc()
        else:
            return

        self.timer.Stop()
        del self.timer
        self.on_done()

    def start(self, interval_ms):
        assert interval_ms > 0 and isinstance(interval_ms, int)
        self.timer.Start(interval_ms)

    def stop(self):
        if hasattr(self, 'timer'):
            self.timer.Stop()

class Fader(FXTimer):
    'Fades a window from one value to another.'

    def __init__(self, window, start=0, end=255, step=10, tick=8, on_done = None):
        if step == 0:
            raise ValueError('step cannot be zero')
        if end < 0 or end > 255:
            raise ValueError('end must be between 0 and 255')

        if hasattr(window, '_fader'):
            window._fader.stop()
            del window._fader
        window._fader = self

        self.range  = (start, end, step)
        self.tick, self.window, self.value = tick, window, start
        self.cback = on_done
        FXTimer.__init__(self, self.fade_tick, tick, on_done = self.on_done)

    def fade_tick(self):
        start, end, step = self.range
        self.value += step
        try:
            setalpha(self.window, clamp(self.value, 0, 255))
        except wx.PyDeadObjectError:
            return self.stop()

        if step < 0:
            return self.value > end
        elif step > 0:
            return self.value < end
        else:
            raise AssertionError('FXTimer has a zero step!')

    def on_done(self):
        if hasattr(self.window, '_fader'):
            del self.window._fader
        if self.cback: self.cback()

def interpolate_gen(total_ticks, p1, p2, func = None):
    '''
    Will yield [total_ticks] points between p1 and p2, based on the given
    interpolation function.
    '''


    if func is None or func not in globals():
        posfunc = better_logistic
    else:
        posfunc = globals()[func] if not callable(func) else func
    diff = vector(p2) - vector(p1)
    normal, total_distance = diff.normal, diff.length

    for n in xrange(total_ticks):
        d = total_distance * posfunc(n / total_ticks)
        yield p1 + normal * d

    yield p2 # make sure we end on the destination


from math import e as math_e, log as math_log

def logistic(x, mu = 9):
    'Smoothing function (s curve).'

    return 1 - 1 /( 1 + math_e ** ((x - 1/2) * mu))

def better_logistic(x):
    return (.5-(1.0/(1+math_e**(x*6.5))))*2


def ln_func(x):
    return max(0, float(math_log(x+.1) + 2)/2.1)

def linear(x):
    return x

class InterpTimer(GenTimer):
    def __init__(self, func, p1, p2, time=200, interval=10, on_tick=None, on_done = lambda: None, method = None):
        total_ticks = int(time / interval)
        gen = interpolate_gen(total_ticks, p1, p2, func = method)
        GenTimer.__init__(self, gen, func, on_tick=on_tick, on_done=on_done)
        self.start(interval)

def move_smoothly(win, position, oldpos = None, time = 200, interval = 10):
    '''Moves a window to a new position smoothly.

    Optionally specify an old position.'''

    if hasattr(win, '_timer'):
        win._timer.stop()

    if oldpos is None:
        oldpos = vector(win.Rect[:2])

    if vector(oldpos) == vector(position):
        return

    def cb(p):
        try:
            win.SetRect(RectPS(p, win.Size))
        except wx.PyDeadObjectError:
            win._timer.stop()
            del win._timer

    win._timer  = InterpTimer(cb, oldpos, position, time = time, interval = interval)
    win._newpos = position
    return win._timer

def resize_smoothly(win, newsize, oldsize = None, on_tick=None, set_min = False, method=None, time=150):
    'Resizes a window smoothly. Optionally specify an old size.'

    if hasattr(win, '_resizetimer'):
        win._resizetimer.stop()

    win.SetAutoLayout(False)

    if oldsize is None:
        oldsize = vector(win.Size)
    else:
        assert len(oldsize) == 2
        oldsize = vector(oldsize)

    if set_min:
        def mysize(*a):
            #win.SetMinSize(*a)
            win.SetLA
            win.SetSize(*a)
            win.Refresh()
    else:
        def mysize(*a):
            p = win.Rect
            win.SetRect(wx.Rect(p[0], p[1], *a[0]))

    try:
        win._resizetimer = InterpTimer(mysize, oldsize, newsize, time=time,
                                       on_tick=on_tick, on_done = lambda: (win.SetAutoLayout(True), win.Layout(), win.Refresh()),
                                       method = method)
        return win._resizetimer
    except wx.PyDeadObjectError:
        pass

wx.Window.FitSmoothly = lambda win, on_tick = None: resize_smoothly(win, win.GetBestSize(), on_tick = win.Refresh(), time=80)

def getfloat(n, default):
    try: return float(n)
    except ValueError: return default

class SlideTimer(wx.Timer):
    'Animated window move, gradually getting slower as it approaches.'

    stop_threshold = 2
    dampen = .4
    tick_ms = 10

    observing = False

    def __init__(self, window):
        if not self.observing:
            from common import profile
            profile.prefs.link('infobox.animation.slide_speed',
                               lambda s: setattr(self, 'dampen', getfloat(s, .4)))
            self.observing = True

        wx.Timer.__init__(self)
        self.window = window

    def Start(self):
        if tuple(self.target) != tuple(self.window.ScreenRect[:2]):
            wx.Timer.Start(self, self.tick_ms)

    def Notify(self):
        '''
        Invoked by the wxTimer.

        Decides how much to move, and if it is time to stop.
        '''
        if not self: return
        if not self.window: return
        winrect = self.window.ScreenRect
        w, pos, target = self.window, vector(winrect[:2]), vector(self.target)
        move = lambda newpos: w.SetRect((newpos[0], newpos[1], winrect.width, winrect.height))

        if pos.to(target) < self.stop_threshold:
            move(self.target)
            self.Stop()
        else:
            move( pos + (target - pos) * self.dampen )


def slide_to(win, pos):
    'Moves win smoothly to "pos" (a 2-tuple).'

    try:
        t = win._spring_timer
    except AttributeError:
        t = win._spring_timer = SlideTimer(win)

    t.target = pos
    t.Start()
    return t

wx.Window.SlideTo = slide_to

def testSliding():
    app = wx.PySimpleApp()
    f = wx.Frame(None, -1, 'Slide Test')
    f.Sizer = wx.BoxSizer(wx.HORIZONTAL)
    panel = wx.Panel(f)
    f.Sizer.Add(panel, 1, wx.EXPAND)


    panel.BackgroundColour = wx.WHITE

    h  = wx.BoxSizer(wx.HORIZONTAL)
    sz = wx.BoxSizer(wx.VERTICAL)

    class TestListBox(wx.VListBox):
        def __init__(self, parent):
            print 'yo'
            wx.VListBox.__init__(self, parent, -1, style = wx.SUNKEN_BORDER)
            self.SetMinSize((300,0))

        def OnDrawItem(self, dc, rect, n):
            dc.Pen = wx.BLACK_PEN
            dc.Brush = wx.WHITE_BRUSH
            dc.Font = default_font()
            dc.DrawText(str(n), rect.x, rect.y)

        def OnMeasureItem(self, n):
            return 13

    lst = TestListBox(f)
    lst.SetItemCount(300)


    b  = wx.Button(panel, -1, 'Slide', style=wx.NO_BORDER)
    b2 = wx.Button(panel, -1, 'Resize')
    b3 = wx.Button(panel, -1, 'Both!')

    def both(e):
        move_smoothly(f,   (600,500))
        resize_smoothly(f, (300,300))

    b.Bind (wx.EVT_BUTTON, lambda e: move_smoothly(f, (400,400)))
    b2.Bind(wx.EVT_BUTTON, lambda e: resize_smoothly(f, (600,160)))
    b3.Bind(wx.EVT_BUTTON, both)
    sz.Add(b,  flag = wx.ALL, border = 3)
    sz.Add(b2, flag = wx.ALL, border = 3)
    sz.Add(b3, flag = wx.ALL, border = 3)

    panel.Sizer = h
    h.Add(sz, 1, wx.EXPAND)
    h.Add(lst, 0, wx.EXPAND)
    f.Sizer.Layout()

    f.Show(True)
    app.MainLoop()

vista = False

# Is this Windows Vista?
if 'wxMSW' in wx.PlatformInfo and hasattr(ctypes.windll, 'dwmapi'):
    glassEnabled = True
    vista = True
    from gui.vista import *
else:
    glassEnabled = False
    vista = False

