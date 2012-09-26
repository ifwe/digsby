# This file was created automatically by SWIG 1.3.29.
# Don't modify this file, modify the SWIG interface instead.

import _splitimage4
import new
new_instancemethod = new.instancemethod
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'PySwigObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static) or hasattr(self,name):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError,name

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

import types
try:
    _object = types.ObjectType
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0
del types


def _swig_setattr_nondynamic_method(set):
    def set_attr(self,name,value):
        if (name == "thisown"): return self.this.own(value)
        if hasattr(self,name) or (name == "this"):
            set(self,name,value)
        else:
            raise AttributeError("You cannot add attributes to %s" % self)
    return set_attr


import wx._core
import wx._windows
import wx._misc
wx = wx._core 
__docfilter__ = wx.__DocFilter(globals()) 

def getObjectRef(*args, **kwargs):
  """getObjectRef(Object obj) -> long"""
  return _splitimage4.getObjectRef(*args, **kwargs)
class Extend(object):
    """Proxy of C++ Extend class"""
    thisown = property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        """__init__(self, bool up=False, bool down=False, bool left=False, bool right=False) -> Extend"""
        this = _splitimage4.new_Extend(*args, **kwargs)
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _splitimage4.delete_Extend
    __del__ = lambda self : None;
    up = property(_splitimage4.Extend_up_get, _splitimage4.Extend_up_set)
    down = property(_splitimage4.Extend_down_get, _splitimage4.Extend_down_set)
    left = property(_splitimage4.Extend_left_get, _splitimage4.Extend_left_set)
    right = property(_splitimage4.Extend_right_get, _splitimage4.Extend_right_set)
_splitimage4.Extend_swigregister(Extend)

class Region(object):
    """Proxy of C++ Region class"""
    thisown = property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args): 
        """
        __init__(self, Extend extends, int hstyle, int vstyle, int align, 
            Point offset) -> Region
        __init__(self) -> Region
        """
        this = _splitimage4.new_Region(*args)
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _splitimage4.delete_Region
    __del__ = lambda self : None;
    extends = property(_splitimage4.Region_extends_get, _splitimage4.Region_extends_set)
    hstyle = property(_splitimage4.Region_hstyle_get, _splitimage4.Region_hstyle_set)
    vstyle = property(_splitimage4.Region_vstyle_get, _splitimage4.Region_vstyle_set)
    align = property(_splitimage4.Region_align_get, _splitimage4.Region_align_set)
    offset = property(_splitimage4.Region_offset_get, _splitimage4.Region_offset_set)
_splitimage4.Region_swigregister(Region)

class ImageData(object):
    """Proxy of C++ ImageData class"""
    thisown = property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args): 
        """
        __init__(self, String source) -> ImageData
        __init__(self) -> ImageData
        """
        this = _splitimage4.new_ImageData(*args)
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _splitimage4.delete_ImageData
    __del__ = lambda self : None;
    source = property(_splitimage4.ImageData_source_get, _splitimage4.ImageData_source_set)
    x1 = property(_splitimage4.ImageData_x1_get, _splitimage4.ImageData_x1_set)
    y1 = property(_splitimage4.ImageData_y1_get, _splitimage4.ImageData_y1_set)
    x2 = property(_splitimage4.ImageData_x2_get, _splitimage4.ImageData_x2_set)
    y2 = property(_splitimage4.ImageData_y2_get, _splitimage4.ImageData_y2_set)
    left = property(_splitimage4.ImageData_left_get, _splitimage4.ImageData_left_set)
    right = property(_splitimage4.ImageData_right_get, _splitimage4.ImageData_right_set)
    top = property(_splitimage4.ImageData_top_get, _splitimage4.ImageData_top_set)
    bottom = property(_splitimage4.ImageData_bottom_get, _splitimage4.ImageData_bottom_set)
    center = property(_splitimage4.ImageData_center_get, _splitimage4.ImageData_center_set)
_splitimage4.ImageData_swigregister(ImageData)

class Slice(object):
    """Proxy of C++ Slice class"""
    thisown = property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        """__init__(self) -> Slice"""
        this = _splitimage4.new_Slice(*args, **kwargs)
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _splitimage4.delete_Slice
    __del__ = lambda self : None;
    image = property(_splitimage4.Slice_image_get, _splitimage4.Slice_image_set)
    hstyle = property(_splitimage4.Slice_hstyle_get, _splitimage4.Slice_hstyle_set)
    vstyle = property(_splitimage4.Slice_vstyle_get, _splitimage4.Slice_vstyle_set)
    pos = property(_splitimage4.Slice_pos_get, _splitimage4.Slice_pos_set)
    offset = property(_splitimage4.Slice_offset_get, _splitimage4.Slice_offset_set)
    align = property(_splitimage4.Slice_align_get, _splitimage4.Slice_align_set)
_splitimage4.Slice_swigregister(Slice)

class ImageCluster(object):
    """Proxy of C++ ImageCluster class"""
    thisown = property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    def __init__(self, *args, **kwargs): 
        """__init__(self) -> ImageCluster"""
        this = _splitimage4.new_ImageCluster(*args, **kwargs)
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _splitimage4.delete_ImageCluster
    __del__ = lambda self : None;
    center = property(_splitimage4.ImageCluster_center_get, _splitimage4.ImageCluster_center_set)
    left = property(_splitimage4.ImageCluster_left_get, _splitimage4.ImageCluster_left_set)
    right = property(_splitimage4.ImageCluster_right_get, _splitimage4.ImageCluster_right_set)
    top = property(_splitimage4.ImageCluster_top_get, _splitimage4.ImageCluster_top_set)
    bottom = property(_splitimage4.ImageCluster_bottom_get, _splitimage4.ImageCluster_bottom_set)
    c1 = property(_splitimage4.ImageCluster_c1_get, _splitimage4.ImageCluster_c1_set)
    c2 = property(_splitimage4.ImageCluster_c2_get, _splitimage4.ImageCluster_c2_set)
    c3 = property(_splitimage4.ImageCluster_c3_get, _splitimage4.ImageCluster_c3_set)
    c4 = property(_splitimage4.ImageCluster_c4_get, _splitimage4.ImageCluster_c4_set)
_splitimage4.ImageCluster_swigregister(ImageCluster)

class SplitImage4(object):
    """Proxy of C++ SplitImage4 class"""
    thisown = property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    splitimage = property(_splitimage4.SplitImage4_splitimage_get, _splitimage4.SplitImage4_splitimage_set)
    Size = property(_splitimage4.SplitImage4_Size_get, _splitimage4.SplitImage4_Size_set)
    MinSize = property(_splitimage4.SplitImage4_MinSize_get, _splitimage4.SplitImage4_MinSize_set)
    ratio = property(_splitimage4.SplitImage4_ratio_get, _splitimage4.SplitImage4_ratio_set)
    def __init__(self, *args, **kwargs): 
        """__init__(self, ImageData idata) -> SplitImage4"""
        this = _splitimage4.new_SplitImage4(*args, **kwargs)
        try: self.this.append(this)
        except: self.this = this
    __swig_destroy__ = _splitimage4.delete_SplitImage4
    __del__ = lambda self : None;
    def SetImage(*args, **kwargs):
        """SetImage(self, ImageData idata)"""
        return _splitimage4.SplitImage4_SetImage(*args, **kwargs)

    def Draw(*args, **kwargs):
        """Draw(self, DC dc, Rect rect, int n=0)"""
        return _splitimage4.SplitImage4_Draw(*args, **kwargs)

    def GetBitmap(*args, **kwargs):
        """GetBitmap(self, Size size) -> Bitmap"""
        return _splitimage4.SplitImage4_GetBitmap(*args, **kwargs)

    def PreRender(*args, **kwargs):
        """
        PreRender(self, DC dc, Slice slice, int posx, int posy, int width, 
            int height)
        """
        return _splitimage4.SplitImage4_PreRender(*args, **kwargs)

    def Render(*args, **kwargs):
        """Render(self, DC dc, int w, int h, int x=0, int y=0, bool center=True)"""
        return _splitimage4.SplitImage4_Render(*args, **kwargs)

_splitimage4.SplitImage4_swigregister(SplitImage4)



