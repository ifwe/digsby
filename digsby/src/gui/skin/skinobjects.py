'''

Skin objects for drawing into rectangular regions

'''
from __future__ import with_statement
from __future__ import division
import wx
from util.primitives.funcs import autoassign
create_gc = wx.GraphicsContext.Create
from gui.toolbox import TransparentBitmap
from operator import itemgetter

from cgui import Bitmap_Draw
from config import platformName

import new
wx.Bitmap.Draw = new.instancemethod(Bitmap_Draw, None, wx.Bitmap)

# This seems to have problems with SWIG, so let's just enable it on Win for now.
USE_CGUI_SKIN_OBJECTS = False

if platformName == "win":
    USE_CGUI_SKIN_OBJECTS = True

class MarginSizer(wx.GridBagSizer):
    'A sizer that adds margin space.'

    def __init__(self, margins, content):
        wx.GridBagSizer.__init__(self)
        self.SetEmptyCellSize(wx.Size(0, 0))
        self.Add(content, (1,1), flag = wx.EXPAND)

        self.AddGrowableCol(1,1)
        self.AddGrowableRow(1,1)

        self.SetMargins(margins)

    def SetMargins(self, margins):
        if len(self.GetChildren()) > 2:
            self.Detach(1) # remove the two padding
            self.Detach(1)

        self.Add(wx.Size(margins.left,  margins.top),     (0, 0))
        self.Add(wx.Size(margins.right, margins.bottom),  (2, 2))

class Margins(list):
    def __init__(self, a = None):
        if a is None:
            list.__init__(self, [0, 0, 0, 0])
        else:
            if isinstance(a, basestring):
                list.__init__(self, (int(c) for c in a.split()))
            elif isinstance(a, int):
                list.__init__(self, [a] * 4)
            else:
                if len(a) == 2:
                    a = [a[0], a[1], a[0], a[1]] # x y -> x y x y
                list.__init__(self, (int(c) for c in a))

        assert len(self) == 4

    def Sizer(self, content):
        return MarginSizer(self, content)

    left   = property(itemgetter(0))
    top    = property(itemgetter(1))
    right  = property(itemgetter(2))
    bottom = property(itemgetter(3))

    x = property(lambda self: self[0] + self[2])
    y = property(lambda self: self[1] + self[3])

    TopLeft     = property(lambda self: wx.Point(self[0], self[1]))
    BottomRight = property(lambda self: wx.Point(self[2], self[3]))

    def __neg__(self):
        return Margins([-a for a in self])



class SkinBase(object):
    def Show(self):
        from gui.toolbox import ShowImage
        ShowImage(self)

class SkinRegion(SkinBase):
    def __init__(self, border = None, rounded = False, highlight = False, shadow = False):
        '''
        Any rectangular area.

        border    a wxPen object used to draw the edges
        rounded   if True, the rectangle is drawn with rounded corners
        highlight if True, the upper left corner is highlighted
        shadow    if True, the bottom right corner is shadowed
        '''
        if not isinstance(border, (type(None), wx.Pen)):
            raise TypeError('border must be a Pen or None')

        autoassign(self, locals())
        self.pen = wx.TRANSPARENT_PEN if border is None else border

    def GetBitmap(self, size, n = 0):
        tb = TransparentBitmap(size)
        dc = wx.MemoryDC()
        dc.SelectObject(tb)
        self.draw(dc, wx.RectS(size), n)
        dc.SelectObject(wx.NullBitmap)
        return tb

    def Stroke(self, dc, gc, rect, n = 0):
        pen  = self.pen
        penw = pen.Width // 2
        rect = wx.Rect(*rect)
        rect.Deflate(penw, penw)

        pen.SetCap(wx.CAP_PROJECTING)
        gc.SetPen(pen)
        dc.SetPen(pen)
        dc.Brush = wx.TRANSPARENT_BRUSH
        gc.Brush = wx.TRANSPARENT_BRUSH

        if self.rounded:
            if self.border:
                gc.DrawRoundedRectangle(*(tuple(rect) + (self.rounded * .97, )))

            rect.Inflate(penw, penw)
            self.stroke_highlights_rounded(gc, rect)

        else:
            if self.border:
                # because dc.DrawRectangle() results in a rounded rectangle. do
                # it manually :(
                offset   = int(pen.Width % 2 == 0)
                dl, x, y = dc.DrawLine, wx.Point(offset, 0), wx.Point(0, offset)

                for a, b in [(rect.TopLeft,             rect.BottomLeft + y),
                             (rect.BottomLeft + y,      rect.BottomRight + y + x),
                             (rect.BottomRight + y + x, rect.TopRight + x),
                             (rect.TopRight + x,        rect.TopLeft)]:
                    dl(*(tuple(a) + tuple(b)))

            rect.Inflate(penw, penw)
            self.stroke_highlights(gc, rect)

    def stroke_highlights_rounded(self, gc, rect):
        pass

    def stroke_highlights(self, gc, rect):
        hw = max(2, self.pen.Width)
        seq = []

        if self.highlight:
            c1,  c2  = wx.Color(255, 255, 255, 100), wx.Color(255, 255, 255, 150)

            seq.extend([(
                (rect.x, rect.y),
                [(rect.x, rect.Bottom),      (rect.x + hw, rect.Bottom - hw),
                 (rect.x + hw, rect.y + hw), (rect.x, rect.y)],
                gc.CreateLinearGradientBrush(rect.x, rect.y, rect.x + hw, rect.y, c1, c2)
            ), ((rect.x, rect.y),
                [(rect.Right + 1, rect.y),   (rect.Right - hw, rect.y + hw),
                 (rect.x + hw, rect.y + hw), (rect.x, rect.y)],
                gc.CreateLinearGradientBrush(rect.x, rect.y, rect.x, rect.y + hw, c1, c2)
            )])


        if self.shadow:
            sc1, sc2 = wx.Color(0, 0, 0, 50),        wx.Color(0, 0, 0, 100)

            seq.extend([(
                (rect.Right + 1, rect.Bottom + 1),
                [(rect.x, rect.Bottom + 1),           (rect.x + hw, rect.Bottom - hw + 1),
                 (rect.Right - hw + 1, rect.Bottom - hw + 1), (rect.Right + 1, rect.Bottom + 1)],
                gc.CreateLinearGradientBrush(rect.x, rect.Bottom - hw + 1, rect.x, rect.Bottom + 1, sc1, sc2)),

                ((rect.Right + 1, rect.Bottom + 1),
                [(rect.Right + 1, rect.y),            (rect.Right - hw + 1, rect.y + hw),
                 (rect.Right - hw + 1, rect.Bottom - hw + 1), (rect.Right + 1, rect.Bottom + 1)],
                gc.CreateLinearGradientBrush(rect.Right - hw + 1, rect.Bottom, rect.Right + 1, rect.Bottom, sc1, sc2))])


        if seq:
            for origin, pts, brush in seq:
                p = gc.CreatePath()
                p.MoveToPoint(*origin)
                for pt in pts:
                    p.AddLineToPoint(*pt)

                gc.SetBrush(brush)
                gc.FillPath(p)



    def draw(self, *a, **k):
        self.Draw(*a, **k)


class SkinStack(list, SkinBase):
    'Stacking skin regions.'

    def __init__(self, seq):
        list.__init__(self, seq)

        if not all(callable(getattr(elem, 'Draw', None)) for elem in seq):
            raise TypeError('SkinStack must be constructed with .Draw-able elements (you gave %r)' % seq)

    def Draw(self, dc, rect, n = 0):
        for brush in reversed(self):
            brush.Draw(dc, rect, n)

    def GetBitmap(self, size, n = 0):
        tb = TransparentBitmap(size)
        dc = wx.MemoryDC()
        dc.SelectObject(tb)

        for region in reversed(self):
            region.draw(dc, wx.RectS(size), n)

        dc.SelectObject(wx.NullBitmap)
        return tb

    @property
    def ytile(self): return all(c.ytile for c in self)

class SkinList(list, SkinBase):
    'Alternating skin regions in a list of items.'

    def __init__(self, seq):
        list.__init__(self, seq)

        if not all(callable(getattr(elem, 'Draw', None)) for elem in seq):
            raise TypeError('SkinStack must be constructed with .Draw-able elements (you gave %r)' % seq)

    def Draw(self, dc, rect, n = 0):
        self[n % len(self)].Draw(dc, rect, n)

    @property
    def ytile(self): return all(c.ytile for c in self)

class SkinGradient(SkinRegion):

    __slots__ = ['direction', 'ytile', 'colors', '_oldrect']

    def __init__(self, direction, colors, **opts):
        SkinRegion.__init__(self, **opts)
        self.direction = direction

        self.ytile = direction == 'horizontal' and not self.border

        self.colors    = colors
        self._oldrect  = None

        if self.rounded is not False or len(colors) > 2:
            self.Fill = lambda gc, x, y, w, h: wx.GraphicsContext.DrawRoundedRectangle(gc, x, y, w, h, self.rounded)
        else:
            self.Fill = wx.GraphicsContext.DrawRectangle

    def __repr__(self):
        return '<%s %s %r>' % (self.__class__.__name__, self.direction, self.colors)

    def _rects(self, therect):
        # cache most recently used rectangles
        if therect == self._oldrect:
            return self._oldrects

        x, y = float(therect.x), float(therect.y)
        w    = float(therect.width)
        h    = float(therect.height)
        vert = self.direction == 'vertical'

        p1 = float(therect.Top if vert else therect.Left)

        lc = len(self.colors) - 1
        dx = (h if vert else w) / float(lc)

        rects = []

        for i in xrange(0, lc):
            c1, c2 = self.colors[i:i+2]

            delta = 1 if i not in (lc, 0) else 0

            if vert:
                r = (x, p1, w, dx + delta)
                gradrect = (x, p1 - delta, x, p1 + dx + delta*2, c1, c2)
            else:
                r = (p1, y, dx + delta, h)
                gradrect = (p1 - delta, y, p1 + dx + delta*2, y, c1, c2)

            rects.append( (gradrect, r) )
            p1 = p1 + dx

        # todo: why is caching breaking VLists?
        #self._oldrect  = therect
        #self._oldrects = rects
        return rects

    def Draw(self, dc, therect, n = 0):
        gc = create_gc(dc)
        gc.SetPen(wx.TRANSPARENT_PEN)
        createb = gc.CreateLinearGradientBrush

        gc.Clip(*therect)

        for gradrect, fillrect in self._rects(therect):
            gc.SetBrush(createb(*gradrect))
            self.Fill(gc, *fillrect)

        self.Stroke(dc, gc, therect)



class SkinColor(wx.Color, SkinRegion):
    'A solid color.'

    simple = False

    def __init__(self, color, **opts):
        # self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        if not any(val for key, val in opts.iteritems()):
            c = tuple(color)
            if len(c) < 4 or c[3] == 255:
                self.simple = True

        SkinRegion.__init__(self, **opts)
        wx.Color.__init__(self)

        self.Set(*color)
        self.ytile = not self.border

    def Fill(self, dc, rect):
        if self.rounded and not self.simple:
            dc.DrawRoundedRectangle(*(tuple(rect) + (self.rounded, )))
        else:
            dc.DrawRectangle(*rect)

    def __repr__(self):
        return '<%s (%s, %s, %s, %s)>' % ((self.__class__.__name__,) + tuple(self))

    def Draw(self, dc, rect, n = 0):
        brush = wx.Brush(self)

        if self.simple:
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(brush)
            dc.DrawRectangle(*rect)
        else:
            gc = create_gc(dc)
            gc.SetBrush(brush)
            gc.SetPen(wx.TRANSPARENT_PEN)

            gc.Clip(*rect)

            # GraphicsContext off by half a pixel?
            self.Fill(gc, rect)
            self.Stroke(dc, gc, rect, n)


if USE_CGUI_SKIN_OBJECTS:
    from cgui import SkinColor as CGUISkinColor
    from cgui import SkinGradient as CGUISkinGradient
    import gui.toolbox

    # Patch .Show method onto skin object classes.
    for clz in (CGUISkinColor, CGUISkinGradient):
        clz.Show = new.instancemethod(gui.toolbox.ShowImage, None, clz)

    from cgui import SkinRegion # for isinstance checks

    def SkinColor(color, **opts):
        color = CGUISkinColor(color)
        set_skin_options(color, opts)
        return color

    def SkinGradient(direction, colors, **opts):
        direction = wx.HORIZONTAL if direction == 'horizontal' else wx.VERTICAL
        gradient = CGUISkinGradient(direction, colors)
        set_skin_options(gradient, opts)
        return gradient

    def set_skin_options(obj, opts):
        obj.SetOutline(opts.get('border') or wx.TRANSPARENT_PEN,
                       opts.get('rounded', 0),
                       opts.get('highlight', False),
                       opts.get('shadow', False))

