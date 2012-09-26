'''
Chooses, sizes, and moves a buddy icon.
'''
from __future__ import with_statement
from __future__ import division
if __name__ == '__main__':
    __builtins__._ = lambda s: s
from traceback import print_exc
from util import debug_property
import config

#TODO:
# -resizing big images vs small images
# an alternate way to get all the WX compatible extensions:
# [a.GetExtension() for a in wx.Image.GetHandlers()]

IMAGE_WILDCARD = ('Image files (*.bmp;*.gif;*.jpeg;*.jpg;*.png)|*.bmp;*.gif;*.jpeg;*.jpg;*.png|'
                  'All files (*.*)|*.*')

from wx import BufferedPaintDC, ImageFromString, Size, Point, \
    GetMousePosition, Bitmap, ImageFromBitmap, BitmapFromImage

from gui.windowfx import ApplySmokeAndMirrors
import wx
from PIL import Image
from cStringIO import StringIO
from util.primitives.error_handling import traceguard
from util.primitives.funcs import do
from path import path
from logging import getLogger; log = getLogger('iconeditor'); info = log.info

MAX_BICON_SIZE = (128, 128)

SCREEN_BUTTON_LABEL_SCREEN = _('Scree&n')
SCREEN_BUTTON_LABEL_CAPTURE = _('Capt&ure')

class IconEditor(wx.Dialog):
    '''
    An icon editor dialog.

    >>> i = IconEditor(frame)
    >>> if i.ShowModal() == wx.ID_OK: print 'Got a bitmap!', i.Bitmap
    '''

    def_size = (295, 415)

    def __init__(self, parent, icon = None):
        wx.Dialog.__init__(self, parent, -1, _('Set Buddy Icon'), size = self.def_size)

        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)

        self.ReturnCode = wx.ID_CANCEL

        self.iconedit = IconEditPanel(self, icon)
        s.Add(self.iconedit, 1, wx.EXPAND)
        self.Fit()

    @property
    def Bytes(self):
        return self.iconedit.Bytes

    @property
    def ImageChanged(self):
        return self.iconedit.dragger._image_changed

    def Prompt(self, okCallback):
        self.okCallback = okCallback
        self.Show(True)

        def onclose(e):
            self.Show(False)
            if self.ReturnCode in (wx.ID_SAVE, wx.ID_OK):
                self.okCallback()
            e.Skip(True)
            wx.CallAfter(self.Destroy)



        self.Bind(wx.EVT_CLOSE, onclose)



class IconDragger(wx.Panel):
    '''
    The panel showing the image and a square represnting the selection for
    the buddy icon.
    '''

    normal  = 48    # The size of a "normal" icon. (Won't be resized.)
    maxpick = 128   # The biggest size you can pick for an icon.

    def __init__(self, parent, slider):
        wx.Panel.__init__(self, parent, style = wx.SUNKEN_BORDER)
        Bind = self.Bind
        Bind(wx.EVT_PAINT,              self.on_paint)
        Bind(wx.EVT_ERASE_BACKGROUND,   lambda e: None)
        Bind(wx.EVT_LEFT_DOWN,          self.on_mouse_down)
        Bind(wx.EVT_RIGHT_DOWN,         self.on_right_down)
        Bind(wx.EVT_LEFT_UP,            self.on_mouse_up)
        Bind(wx.EVT_MOTION,             self.on_motion)
        Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_mouse_capture_lost)
        Bind(wx.EVT_KEY_DOWN,           self.on_key)

        self.bitmap = wx.TransparentBitmap(32, 32)
        self.adjustment = (0,0)
        self.dragging = False
        self.picksize = wx.Size(self.normal, self.normal)

        # The size slider
        self.slider = slider
        slider.Bind(wx.EVT_SLIDER,         lambda e: self.on_slider(e, high_quality = False))
        slider.Bind(wx.EVT_SCROLL_CHANGED, lambda e: wx.CallAfter(lambda e=e: self.on_slider(e, high_quality = True)))

        self._image_changed = False
        self._image_bytes = None

        sz = (260, 260)
        self.SetMinSize(sz)
        self.SetMaxSize(sz)
        self.SetSize(sz)

        from gui.toolbox.dnd import SimpleDropTarget
        self.SetDropTarget(SimpleDropTarget(self))
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

    def OnDropFiles(self, filelist):
        for filepath in (path(f) for f in filelist):
            if filepath.isfile():
                with traceguard:
                    img = Image.open(filepath)
                    img.load()
                    return self.set_image(img.WX)

        log.warning('no images in %r', filelist)

    def OnDropBitmap(self, bitmap):
        self.set_image(bitmap)

    def on_slider(self, e = None, high_quality = True):
        n = self.resize_func(self.slider.Value, high_quality = high_quality)
        self.picksize = Size(n, n)
        self.Refresh()

        if e is not None:
            self._image_changed = True
            self._image_bytes = None

    def _resized_high(self, width, height):
        return self.image.PIL.Resized((width, height))

    def _resized_low(self, width, height):
        return self.image.Scale(width, height)

    def resize_image(self, dim, high_quality = True):
        "Resizes the image so that it's largest dimension is dim."

        # Preserve aspect ratio
        w, h = self.image.Width, self.image.Height
        s = self._resized_high if high_quality else self._resized_low

        new_image = s(w/h*dim, dim) if w < h else s(dim, h/w*dim)

        self.bitmap = new_image.WXB

    def on_paint(self, e = None):
        dc = BufferedPaintDC(self)

        # Draw empty background
        b = wx.WHITE_BRUSH#Brush(Color(40, 40, 40)) @UndefinedVariable
        #b.SetStipple(self.stipple)
        dc.Brush = b

        dc.Pen   = wx.TRANSPARENT_PEN #@UndefinedVariable
        dc.DrawRectangle(0,0,*self.Size)

        # Draw the bitmap
        self.paint_bitmap(dc)

        # Draw the picker square
        dc.Brush = wx.TRANSPARENT_BRUSH #@UndefinedVariable
        dc.Pen   = wx.RED_PEN #@UndefinedVariable

        x,y = self.middle
        x -= self.picksize[0] / 2
        y -= self.picksize[1] / 2
        dc.SetLogicalFunction(wx.INVERT)
        dc.DrawRectangle(x,y,self.picksize[0],self.picksize[1])

    def paint_bitmap(self, dc, pickerPos = None):
        '''
        If dc is None, returns a PIL image
        '''

        bw, bh = self.bitmap.Width, self.bitmap.Height

        # get the 0,0 point of the image if centered
        imagecenter  = Point(self.Rect.Width / 2, self.Rect.Height / 2) - Point(bw/2, bh/2)

        # adjust away from center
        xy = imagecenter + (self.adjustment[0] * bw, self.adjustment[1] * bh)

        # adjust the offset by how far into the picture the selection is
#        if pickerPos:
#            xy[0] += pickerPos[0]; xy[1] += pickerPos[1]


        if dc is not None:
#            dc.SetBrush(wx.TRANSPARENT_BRUSH) #@UndefinedVariable
#            dc.SetPen(wx.RED_PEN) #@UndefinedVariable
            dc.DrawBitmap(self.bitmap, *xy)
#            dc.DrawRectangleRect(cropRect)
        else:


            pickWidth  = int(self.picksize[0])
            pickHeight = int(self.picksize[1])
            pickRect = wx.RectPS(pickerPos or ((self.Rect.width // 2 - self.picksize[0] // 2), (self.Rect.height // 2 - self.picksize[1] // 2)) , (pickWidth, pickHeight))
            pickRect.Position -= xy
            imageRect = wx.RectPS((0, 0), (bw, bh))
            cropRect = imageRect.Intersect(pickRect)

            crop_box = (cropRect.left, cropRect.top, cropRect.right, cropRect.bottom)

            croppedImage = self.bitmap.PIL.crop(crop_box)
#            croppedImage.Show("croppedImage")


            offsetX = max(-(pickRect.x - cropRect.x), 0)
            offsetY = max(-(pickRect.y - cropRect.y), 0)
            if(offsetX or offsetY):
                paddedImage = Image.new('RGBA', (pickRect.width, pickRect.height), (0,0,0,0))
                paddedImage.paste(croppedImage, (offsetX, offsetY))
                return paddedImage

            return croppedImage

    @property
    def middle(self):
        w, h = self.Size
        return Point(w/2, h/2)

    @debug_property
    def Bytes(self):
        # Size of the icon picker
        s = self.picksize

        # Size of the icon dragger area
        r = self.Rect

        # position of the iconpicker in relation to the dragger area
        pickerPos = (r.Width // 2 - s[0] // 2), (r.Height // 2 - s[1] // 2)

        # crop the image
        img = self.paint_bitmap(None, pickerPos)

        # Save as PNG
        imgFile = StringIO()
        img.save(imgFile, 'PNG', optimize = True)

        return imgFile.getvalue()

    def on_mouse_capture_lost(self,event):
        self.CancelDrag()

    def on_mouse_down(self, e):
        e.Skip()
        if e.LeftDown():
            self.startdrag = self.dragging = GetMousePosition()
            self.CaptureMouse()

    def on_right_down(self,event):
        if self.dragging:
            self.CancelDrag()
        else:
            event.Skip()


    def on_key(self,event):
        isesc = event.KeyCode == wx.WXK_ESCAPE
        if self.dragging and isesc:
            self.CancelDrag()
        elif not isesc:
            event.Skip()

    def CancelDrag(self):
        startdrag = self.startdrag
        curdrag = self.dragging
        self.on_mouse_up()
        self.dragging = curdrag
        self.on_motion(forcednewpos = startdrag)
        self.dragging = False

    def on_motion(self, e=None, forcednewpos=None):
        if self.dragging is not False:
            newpos = forcednewpos or GetMousePosition()
            delta = newpos - Point(*self.dragging)
            diff = (float(delta.x) / self.bitmap.Width,
                    float(delta.y) / self.bitmap.Height)
            self.adjustment = (self.adjustment[0] + diff[0],
                           self.adjustment[1] + diff[1])

            self.dragging = newpos
            self.Refresh()
            self._image_changed = True
            self._image_bytes = None

    def on_mouse_up(self, e=None):
        if not e or e.LeftUp():
            self.startdrag = None
            self.dragging = False
            while self.HasCapture():
                self.ReleaseMouse()

    def set_image(self, image, first = False):
        self.Parent.set_screen_button_mode()

        if isinstance(image, str):
            log.info('set_image received bytes')
            self._image_bytes = image
            image = ImageFromString(image)

        if not first:
            self._image_changed = True

        self._set_imageorbitmap(image)

        self.dim = max(self.image.Width, self.image.Height)
        if self.dim > max(MAX_BICON_SIZE):
            self._image_changed = True

        self.adjustment = (0,0)

        # first: is it the normal size? if so, disable the slider
        if self.image.Width == self.normal and self.image.Height == self.normal:
            self.slider.Enable(False)
            self.picksize = Size(self.normal, self.normal)
        else:
            self.slider.Enable(True)

            if    self.dim < self.normal:   f = self.f1 # case 1: small
            elif  self.dim < self.maxpick:  f = self.f2 # case 2: smaller than max
            else:                           f = self.f3 # case 3: bigger than max
            self.resize_func = f

            self.on_slider()

        self.Refresh()

    # The following functions are used to determine the image's size when from
    # the slider value. The slider behavior is different for images of
    # different sizes.

    def f1(self, val, high_quality = True):
        'The image is smaller than normal.'

        return self.normal - int((self.normal - self.dim) * (val / 100.0))

    def f2(self, val, high_quality = True):
        'The image is bigger than the normal, but smaller than the max pick size.'

        return self.dim - (val/100.0)*(self.dim - self.normal)

    def f3(self, val, high_quality = True):
        'The image is really big.'

        mid = 50 # This could probably be chosen based on how "really big"
        pickval = val - mid
        if pickval < 0: pickval = 0

        if val < mid:
            dim = (self.dim - self.maxpick) * (val/mid) + self.maxpick
            self.resize_image(dim, high_quality = high_quality)
        else:
            self.resize_image(max(self.image.Width, self.image.Height), high_quality = high_quality)

        # Picker size
        return self.maxpick - pickval / mid * (self.maxpick - self.normal)

    def _set_imageorbitmap(self, image):
        if isinstance(image, Bitmap):
            self.image = ImageFromBitmap(image)
            if not self.image.HasAlpha():
                self.image.InitAlpha()

            self.bitmap = image

        elif isinstance(image, wx.Image):
            self.image = image
            if not image.HasAlpha():
                image.InitAlpha()
            self.bitmap = BitmapFromImage(self.image)
        else:
            raise TypeError

class IconEditPanel(wx.Panel):
    '''
    The panel holding buttons for file, webcam, clipboard, etc.
    '''

    def __init__(self, parent, bitmap = None, dialog_buttons = True):
        wx.Panel.__init__(self, parent)
        wx.InitAllImageHandlers()
        self.construct_and_layout(dialog_buttons)

        # bind on_XXX to button XXX
        for b in self.buttonnames:
            self.buttonfor(b).Bind(wx.EVT_BUTTON, getattr(self, 'on_' + b))

        if bitmap:
            if not hasattr(bitmap, 'IsOk') or bitmap.IsOk():
                with traceguard:
                    self.set_image(bitmap, first = True)

    @property
    def Bytes(self):
        if self.dragger._image_bytes and not self.dragger._image_changed:
            log.info('returning original image bytes')
            return self.dragger._image_bytes
        else:
            log.info('returning new bytes from resized image')
            return self.dragger.Bytes


    #
    # Button callbacks
    #

    def on_file(self, e):
        filediag = wx.FileDialog(wx.GetTopLevelParent(self),
                                 _('Choose an icon'), wildcard = IMAGE_WILDCARD)
        if filediag.ShowModal() == wx.ID_OK:
            imgpath = path(filediag.GetPath())
            if imgpath.isfile():

                try:
                    # make sure its a valid image.
                    Image.open(imgpath).load()
                except:
                    msg = _('Not a valid image:')
                    
                    wx.MessageBox(u'{msg}\n\n"{imgpath}"'.format(msg=msg, imgpath=imgpath),
                                  _('Invalid Image'), style = wx.ICON_ERROR,
                                  parent = self)
                else:
                    self.set_image(imgpath.bytes())

    def on_webcam(self, e):
        pass

    capture_related = ['save']

    def set_image(self, img, *a, **k):
        return self.dragger.set_image(img, *a, **k)

    def on_screen(self, e):
        if self._screen_button_mode == 'capture':
            return self.on_capture()

        self._set_screen_button_mode('capture')
        self.buttonfor('screen').SetBold()
        self.slider.Enable(False)
        for b in self.capture_related: self.buttonfor(b).Enable(False)
        cuthole(self.dragger)

    def on_capture(self):
        self.slider.Enable(True)
        dragger = self.dragger
        self.Freeze()

        try:
            if config.platform == 'win':
                try:
                    from cgui import getScreenBitmap
                except ImportError:
                    print_exc()
                    return

                bitmap = getScreenBitmap(wx.RectPS(dragger.ScreenRect.Position, dragger.ClientSize))
            else:
                screendc = wx.ScreenDC()
                bitmap = screendc.GetAsBitmap()

            if bitmap is not None:
                self.set_image(wx.ImageFromBitmap(bitmap))

            s = self.slider
            s.Value = (s.Max - s.Min) / 2
        finally:
            wx.CallAfter(self.ThawLater)

    def ThawLater(self):
        try:
            self.dragger.on_slider()
        finally:
            self.Thaw()
            
    def _set_screen_button_mode(self, mode):
        assert mode in ('capture', 'screen')
        self._screen_button_mode = mode
        
        if mode == 'capture':
            label = SCREEN_BUTTON_LABEL_CAPTURE
        else:
            label = SCREEN_BUTTON_LABEL_SCREEN
            
        self.buttonfor('screen').Label = label

    def set_screen_button_mode(self):
        b = self.buttonfor('screen')
        if self._screen_button_mode == 'capture':
            self._set_screen_button_mode('screen')
            f = b.Font; f.SetWeight(wx.FONTWEIGHT_NORMAL); b.Font = f
            do(self.buttonfor(b).Enable(True) for b in self.capture_related)
            ApplySmokeAndMirrors(wx.GetTopLevelParent(self))


    def on_clipboard(self, e):
        cb = wx.TheClipboard
        if cb.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
            data = wx.BitmapDataObject()
            cb.GetData(data)
            self.set_image(data.Bitmap)
        else:
            wx.MessageBox('No image data found in clipboard.',
                          'Icon From Clipboard')

    def on_save(self, e):
        self.EndWithReturnCode(wx.ID_OK)

    def EndWithReturnCode(self, code):
        win = wx.GetTopLevelParent(self)

        while self.dragger.HasCapture():
            self.dragger.ReleaseMouse()

        win.ReturnCode = code
        win.Close()

    def on_clear(self, e):
        self.set_image(wx.TransparentBitmap(100, 100))

    def on_cancel(self, e):
        self.EndWithReturnCode(wx.ID_CANCEL)

    def button_names(self, dialog_buttons):
        names = [('file',      _('&File')),
                 ('clipboard', _('Cli&pboard')),
                 ('screen',    SCREEN_BUTTON_LABEL_SCREEN)]

        if dialog_buttons:
            names += [
                 ('save',      _('&Save')),
                 ('clear',     _('C&lear')),
                 ('cancel',    _('&Cancel'))
            ]

        return names

    def construct_and_layout(self, dialog_buttons):
        # File, Webcam, Clipboard buttons
        top = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Source'), wx.HORIZONTAL)
        middle = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Preview'), wx.VERTICAL)

        names = self.button_names(dialog_buttons)
        self.buttonnames = [name for name, guiname in names]
        self.buttons = [wx.Button(self, -1, guiname) for name, guiname in names]
        self._set_screen_button_mode('screen')

        top.AddMany([(b, 1, wx.EXPAND | wx.ALL, 3) for b in self.buttons[:3]])

        self.slider = wx.Slider(self)
        self.slider.Disable()
        self.dragger = IconDragger(self, self.slider)

        # The interactive window image preview
        middle.Add(self.dragger, 1, wx.EXPAND | wx.ALL)
        middle.Add(self.slider,  0, wx.EXPAND | wx.ALL)


        self.Sizer = sz = wx.BoxSizer(wx.VERTICAL)
        sz.AddMany([ (top,    0, wx.EXPAND | wx.ALL, 3),
                     (middle, 1, wx.EXPAND | wx.ALL, 3) ])

        if dialog_buttons:
            # Save, Clear, and Cancel buttons
            bottom = wx.BoxSizer(wx.HORIZONTAL)
            bottom.AddMany([(b, 1, wx.EXPAND | wx.ALL, 3) for b in self.buttons[3:]])
            sz.AddMany([(bottom, 0, wx.EXPAND | wx.ALL, 3)])

    def buttonfor(self, s):
        return self.buttons[self.buttonnames.index(s)]

def cuthole(ctrl):
    top = wx.GetTopLevelParent(ctrl)
    x = ctrl.ScreenRect.X - top.ScreenRect.X
    y = ctrl.ScreenRect.Y - top.ScreenRect.Y
    w, h = ctrl.ClientSize

    winsz = top.Size
    region = wx.Region(0, 0, winsz[0], y)
    region.UnionRect((0, 0, x, winsz[1]))
    region.UnionRect((x+w, y, winsz[0] - w - x, h))
    region.UnionRect((0, y + h, winsz[0], winsz[1] - h - y))

    ApplySmokeAndMirrors(top, region)

if __name__ == '__main__':    # Tests the editor
    _ = lambda s: s
    from gui.toolbox import setuplogging; setuplogging()
    app = wx.PySimpleApp()
    IconEditor(None).ShowModal()



