import sys, os
import bootstrap

if os.name == 'nt':
    # fix comtypes issues on windows 7
    # see http://sourceforge.net/tracker/index.php?func=detail&aid=2855280&group_id=115265&atid=692940
    import ctypes
    ctypes.OleDLL._func_restype_ = ctypes.c_void_p

USE_PEAK = False
if USE_PEAK:
    import peak
    peak.install()

try:
    import srcrev; srcrev.REVISION
except Exception:
    sys.REVISION = 'dev'
else:
    sys.REVISION = srcrev.REVISION

sys.TAG = ''

try:
    import devmode
except Exception:
    sys.DEV      = False
else:
    sys.DEV      = devmode.awesome

sys.BRAND = None

# Adds "Digsby/lib" to the system PATH for this process.
# This allows DLL lookups to find modules there.
sepjoin  = os.pathsep.join
pathjoin = os.path.join
lib_dir = pathjoin(os.path.dirname(sys.executable), 'lib')

os.environ['PATH'] = sepjoin([os.environ['PATH'], lib_dir])

if USE_PEAK:
    @peak.whenImported('events')
    def __monkeypatch_wx__CallAfter(mod):
        print 'lololmonkeypatch'
        import wx
        wx.CallAfter = mod.CallAfterCombining

bootstrap.install_sentinel()

sys.modules['psyco'] = None

restricted_names = frozenset(['password', 'secret', 'pass', 'passwd'])

OMITTED = '<OMITTED>'
VALUE_LENGTH_LIMIT = 360

def formatexception(excinfo=None, lastframes=8):
    """Pretty print exception, including local variable information.
     See Python Cookbook, recipe 14.4.
     @param excinfo: tuple of information returned from sys.exc_info when
              the exception occurred.  If you don't supply this then
              information about the current exception being handled
              is used
     @param lastframes: local variables are shown for these number of
                 frames
     @return: A pretty printed string
    """
    import StringIO
    import traceback
    if excinfo is None:
        excinfo=sys.exc_info()

    s=StringIO.StringIO()
    tb=excinfo[2]
    stack=[]

    if tb is not None:
        while True:
            if not tb.tb_next:
                break
            tb=tb.tb_next
        f=tb.tb_frame
        while f:
            stack.append(f)
            f=f.f_back

    stack.reverse()
    if len(stack)>lastframes:
        stack=stack[-lastframes:]
    print >>s, "\nVariables by last %d frames, innermost last" % (lastframes,)

    restricted_values = []

    for frame in stack:
        print >>s, ""
        print >>s, '  File "%s", line %d, in %s' % (frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)

        for key,value in frame.f_locals.items():
            # filter out modules
            if type(value)==type(sys):
                continue
            if key == '__builtins__':
                continue

            for badthing in restricted_names:
                if badthing in key and value:
                    restricted_values.append(value)
                    value = OMITTED

            print >>s,"%15s = " % (key,),
            try:
                if isinstance(value, type({})) and value:
                    valstring = []
                    for _kk, _vv in sorted(value.items()):
                        if _kk == '__builtins__': continue
                        if any((x in _kk) for x in restricted_names) and _vv:
                            valstring.append('%s=%r' % (_kk, OMITTED))
                            restricted_values.append(_vv)
                        else:
                            valstring.append('%s=%r' % (_kk, _vv))

                    valstring = ' '.join(valstring)[:VALUE_LENGTH_LIMIT]
                    print >>s, valstring,
                else:
                    print >>s,repr(value)[:VALUE_LENGTH_LIMIT]
            except:
                print >>s,"(Exception occurred printing value)"
    traceback.print_exception(*excinfo, **{'file': s})

    retval = s.getvalue()
    if isinstance(retval, unicode):
        retval_str = retval.encode('utf-8', 'replace')
    else:
        retval_str = retval
    for value in restricted_values:
        if not value or value == OMITTED:
            continue

        try:
            value_type = type(value)
            if issubclass(value_type, basestring):
                if issubclass(value_type, unicode):
                    value_str = value.encode('utf-8', 'replace')
                elif issubclass(value_type, str):
                    value_str = value

                retval_str = retval_str.replace(value_str, OMITTED)

            retval_str = retval_str.replace(repr(value)[:VALUE_LENGTH_LIMIT], OMITTED)
        except UnicodeError:
            continue
    return retval

import traceback

traceback._old_print_exc = traceback.print_exc
traceback._old_format_exc = traceback.format_exc

COLORIZE_EXCEPTIONS = False
SHOW_TRACEBACK_DIALOG = sys.DEV

def get_exc_dialog():
    diag = getattr(sys, 'exc_dialog', None)
    if diag is not None:
        import wx
        if wx.IsDestroyed(diag):
            diag = None
    if diag is None:
        import gui.tracebackdialog
        diag = sys.exc_dialog = gui.tracebackdialog.ErrorDialog()

    return diag

def tb_pref_enabled():
    try:
        import common
        return common.pref('debug.traceback_dialog', default=True)
    except:
        return False

def print_exc(limit=None, file=None):
    traceback.format_exc = traceback._old_format_exc()
    try:
        try:
            if file is None:
                file = sys.stderr

            formattedexc = formatexception()

            if SHOW_TRACEBACK_DIALOG and tb_pref_enabled():
                def show_dialog():
                    try:
                        diag = get_exc_dialog()
                        diag.AppendText(formattedexc + "\n\n")
                        if not diag.IsShown(): diag.CenterOnScreen()
                        diag.Show()
                    except Exception:
                        #break infinite loop, just in case
                        print sys.stderr, 'error showing exception dialog: %r' % e

                import wx
                if wx.App.IsMainLoopRunning():
                    wx.CallAfter(show_dialog)

            if COLORIZE_EXCEPTIONS and file is sys.stderr:
                from gui.native.win import console
                with console.color('bold red'):
                    file.write(formattedexc)
            else:
                file.write(formattedexc)
        except:
            # Old exception is lost.
            traceback._old_print_exc()
    finally:
        traceback.format_exc = formatexception

traceback.print_exc = print_exc

def format_exc():
    traceback.format_exc = traceback._old_print_exc()
    try:
        try:
            return formatexception()
        except:
            # Old exception is lost.
            return traceback._old_format_exc()
    finally:
        traceback.format_exc = formatexception

traceback.format_exc = formatexception

print_exc_once_cache = set()
import inspect

def print_exc_once():
    'Like print_exc, but only displays an exception once.'

    import traceback

    try:
        frame = inspect.currentframe()
        filename = frame.f_back.f_code.co_filename
        line_number = frame.f_lineno
        key = (filename, line_number)
    except Exception:
        traceback.print_exc()
    else:
        if key not in print_exc_once_cache:
            traceback.print_exc()
            print_exc_once_cache.add(key)

traceback.print_exc_once = print_exc_once

# in DEV or with --track-windowids, keep track of where we're calling wx.NewId from
TRACK_WINDOW_ID_ALLOCATIONS = sys.DEV or \
    getattr(getattr(sys, 'opts', None), 'track_windowids', False) or \
    getattr(sys, 'TAG', None) == 'alpha'

if TRACK_WINDOW_ID_ALLOCATIONS:
    # replace wx.NewId

    import wx

    count_map = {}
    _original_NewId = wx.NewId
    def debug_NewId():
        global count_map
        try:
            loc = tuple(traceback.extract_stack()[-3:-1]) # 2 outer frames of wx.NewId caller
            new_count = count_map.get(loc, 0) + 1
            count_map[loc] = new_count

            # don't let the map get too big
            if len(count_map) > 100:
                count_map = dict(sorted(count_map.iteritems(), key=lambda item: item[1], reverse=True)[:50])

        except Exception:
            print_exc()
        return _original_NewId()

    wx.NewId = debug_NewId

    def get_window_id_allocs():
        return count_map

def eh(*args):
    try:
        print >>sys.stderr,formatexception(args)
    except:
        print >>sys.stderr,args
if True:
    sys.excepthook=eh



class NullType(object):
    '''
    >> # Null() is a no-op, like lambda *a, **k: None
    >> bool(Null) == False
    True
    >>> Null.Foo.Bar.Meep is Null
    True
    '''
    # thanks Python cookbook
    def __new__(cls, *args, **kwargs):
        if '_inst' not in vars(cls):
            cls._inst = object.__new__(cls, *args, **kwargs)
        return cls._inst

    def __init__(self, *args, **kwargs): pass
    def __call__(self, *args, **kwargs): return self
    def __repr__(self): return '<Null>'
    def __nonzero__(self): return False
    def __getattr__(self, name): return self
    def __setattr__(self, name, value): return self
    def __delattr__(self, name): return self

import __builtin__
__builtin__.Null = NullType()
del NullType

#
# patch ctypes.util.find_library to look in sys.path, as well as
# the usual os.environ['PATH']
#
find_library = None
if os.name == "nt":
    def find_library(name):
        # See MSDN for the REAL search order.
        for directory in (sys.path + os.environ['PATH'].split(os.pathsep)):
            fname = os.path.join(directory, name)
            if os.path.exists(fname):
                return fname
            if fname.lower().endswith(".dll"):
                continue
            fname = fname + ".dll"
            if os.path.exists(fname):
                return fname
        return None

if find_library is not None:
    import ctypes.util
    ctypes.util.find_library = find_library
del find_library

import gettext
gettext.install('Digsby', './locale', unicode=True)

