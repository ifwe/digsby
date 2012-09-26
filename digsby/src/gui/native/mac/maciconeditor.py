import os

import wx
import objc
from AppKit import *
from Foundation import *
from Quartz import *

from .machelpers import *

NSApplicationLoad()

class IconEditor(object):
    def __init__(self, parent, icon=''):
        self.image_changed = False
        with nspool():
            self.picTaker = IKPictureTaker.alloc().init()
            try:
                if not icon == '':
                    data = NSData.dataWithBytes_length_(icon, len(icon))
                    image = NSImage.alloc().initWithData_(data)
                
                    if image:
                        self.picTaker.setInputImage_(image)
            except:
                raise
    
    @classmethod
    def RaiseExisting(cls):
        return False
        
    def Prompt(self, callback):
        result = self.picTaker.runModal()
        if result == NSOKButton:
            self.image_changed = True
            self.output = self.picTaker.outputImage()
            
            callback()
            
    @property
    def Bytes(self):
        rep = None
        # we need a NSBitmapImageRep to convert to png. This code assumes
        # outputImage always returns an NSImage that contains an NSBitmapImageRep
        # representation.
        for arep in self.output.representations():
            if isinstance(arep, NSBitmapImageRep):
                rep = arep
        assert rep
        return str(rep.representationUsingType_properties_(NSPNGFileType, None).bytes())

    @property
    def ImageChanged(self):
        return self.image_changed
