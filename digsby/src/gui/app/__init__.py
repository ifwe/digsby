"""
The purpose of this module is to store code that affects DigsbyApp. Eventually,
it'd be nice to move some of main.py into here as well.
"""

import sip
import sys
import traceback
import types
import wx

def checkMainThread(func):
    def new(*args, **kwargs):
        if not wx.IsMainThread():
            import util.introspect
            # print the stack before we assert to be more helpful :)
            print >> sys.stderr, util.introspect.print_stack_trace()
            assert wx.IsMainThread()
        return func(*args, **kwargs)
    return new

excludes = ["Event", "Timer", "CallLater", "sip", "ExitMainLoop"]

def addThreadChecksToClassRecursive(obj):
    for symbol in dir(obj):
        objname = getattr(obj, '__name__', None)
        if objname is None:
            continue

        if hasattr(obj, "__module__"):
            objname = obj.__module__ + "." + objname

        if symbol.startswith("_") or objname.startswith("_"):
            continue

        exclude = False
        for exc in excludes:
            if symbol.find(exc) != -1 or objname.find(exc) != -1:
                exclude = True

        if exclude:
            continue

        try:
            sym = getattr(obj, symbol)
        except:
            continue
    
        if type(sym) == types.MethodType:
            #print objname, symbol
            assert objname.find("PyEvent") == -1 and symbol.find("PyTimer") == -1
            # im_self existing means classmethod, we hit problems if we do this on classmethods
            
            if not sym.im_self:
                exec "%s.%s = checkMainThread(%s.%s)" % (objname, symbol, objname, symbol)
        elif type(sym) == types.ClassType or type(sym) == types.TypeType or type(sym) == sip.wrappertype:
            addThreadChecksToClassRecursive(sym)

