'''
Links actions and keyboard shortcuts (or possibly other input methods).
'''
from __future__ import with_statement

from traceback import print_exc
from collections import defaultdict

from util.introspect import import_function, memoize
from util.primitives.funcs import Delegate
from util.merge import merge_keys
from prefs import flatten

import wx
from wx import WXK_F1, WXK_F24, wxEVT_KEY_DOWN

from logging import getLogger; log = getLogger('input'); DEBUG = log.debug

class InputManager(object):
    '''
    Binds keyboard shortcuts to actions.

    Watches the wxApp object for key events, and then uses the window returned
    by wxKeyEvent::GetEventObject to determine contexts for the keyboard
    action.
    '''

    def __init__(self):
        self.reset()

    def reset(self):
        self.handlers = defaultdict(Delegate) # {actionname: callbacks}
        self.actions  = defaultdict(dict)     # {wx event type: {context: actionset}}
        self.contexts = []                    # [sorted list of contexts to try]
        self.context_lookups = []             # [list of (contextstr, context)]
        self.actionnames = {}                 # {actionname: actionset}
        self.context_cache = {}               # {actionname: context}
        self.bound = False                    # if bound to an EvtHandler, the EvtHandler

    def AddGlobalContext(self, name, contextstr):
        'Add a context that works across the entire application.'

        self.context_lookups.append((contextstr.lower(), GlobalContext()))
        self.context_cache.clear()
        self.resolve_actions()

    def AddClassContext(self, name, contextstr, cls):
        'Add a context that works inside controls of a certain class.'

        self.context_lookups.append((contextstr.lower(), ClassContext(name, cls)))
        self.context_cache.clear()
        self.resolve_actions()

    def AddKeyboardShortcut(self, actionname, accels):
        '''
        Adds a new keyboard shortcut.

        actionname    a dotted.hierachical.string describing the action
        accels        a string describing the keys in the shortcut, like
                      "shift+alt+k." for more info see the keycodes function
                      below.

                      this string maybe also me several keyboard shortcuts
                      separated by a comma
        '''

        keys = KeyActionSet((keycodes(accel), actionname) for accel in accels.split(','))
        self.actionnames[actionname.lower()] = keys
        self.resolve_actions()

    def LoadKeys(self, filepath):
        'Loads a set of keyboard shortcuts from a YAML file.'

        addkey = self.AddKeyboardShortcut
        import syck

        with open(filepath) as f:
            for actionname, accels in flatten(merge_keys(syck.load(f))):
                addkey(actionname, accels)

    def resolve_actions(self):
        'Links inputs (like keyboard commands) to their actions.'

        if not self.bound: return

        contexts = set()
        find_context = self.find_context

        for actionname, actionset in self.actionnames.iteritems():
            context = find_context(actionname)
            if context is not None:
                try:
                    keyactions = self.actions[wxEVT_KEY_DOWN][context]
                except KeyError:
                    keyactions = self.actions[wxEVT_KEY_DOWN][context] = KeyActionSet()

                keyactions.update(actionset)
                contexts.add(context)

        self.contexts = sorted(contexts, reverse = True)

    def AddActionCallback(self, actionname, callback):
        'Associates a callable with an action.'

        actionname = actionname.lower()

        if isinstance(callback, basestring):
            callback = LazyStringImport(callback)

        if not actionname in self.handlers:
            self.handlers[actionname] = Delegate([callback])
        else:
            self.handlers[actionname] += callback

        self.resolve_actions()

    def BindWxEvents(self, evt_handler):
        if not self.bound is evt_handler:
            evt_handler.Bind(wx.EVT_KEY_DOWN, self.handle_event)
            self.bound = evt_handler

        self.resolve_actions()

    def find_context(self, actionname):
        if actionname in self.context_cache:
            return self.context_cache[actionname]

        actionname = actionname.lower()
        startswith = actionname.startswith

        found = [(cstr, c) for cstr, c in self.context_lookups if startswith(cstr)]

        # Find the longest match.
        found.sort(key = lambda s: len(s[0]), reverse = True)

        context = found[0][1] if found else None
        return self.context_cache.setdefault(actionname, context)

    def handle_event(self, e):
        contexts = self.contexts

        # walk control tree up to the top level window
        for win in child_and_parents(e.EventObject):
            # see if any of the contexts return True for the window
            for context in contexts:
                if context(win):
                    #DEBUG('context %r responded', context)
                    if self.invoke_actions(context, e, win) is False:
                        return
        e.Skip()

    def invoke_actions(self, context, e, win):
        try:
            actionset = self.actions[e.EventType][context]
        except KeyError:
            #DEBUG('no actionset found')
            return

        try:
            actionname = actionset(e, win)
            if actionname is False:
                return
            elif actionname is not None:
                return self.event(actionname, win)
        except Exception:
            print_exc()



    def event(self, actionname, *a, **k):
        try:
            DEBUG('firing action %r', actionname)
            action_delegate = self.handlers[actionname]
            DEBUG(' callbacks: %r', action_delegate)
        except KeyError:
            pass
        else:
            try:
                if action_delegate:
                    action_delegate(*a, **k)
                    return False
            except Exception:
                print_exc()

class Context(object):
    '''
    Keyboard shortcuts are each associated with different "context" objects
    that describe when and where they work.
    '''
    __slots__ = ['name']

    priority = 0

    def __init__(self, name):
        self.name  = name

    def __call__(self):
        raise NotImplementedError('Context subclasses must implement __call__')

    def __cmp__(self, other):
        return cmp(self.priority, other.priority)

    def __hash__(self):
        return hash(id(self))

class WindowNameContext(Context):
    '''
    Groups keyboard shortcuts that work when a top level window with a given
    name is active.

    Note that a window's "name" is not the same as it's "title," which is
    visible to the user. See wxTopLevelWindow's constructor.
    '''
    __slots__ = ['window_name']

    priority = 100

    def __init__(self, name, window_name):
        Context.__init__(self, name)
        self.window_name = window_name

    def __call__(self, window):
        return window.Name == self.window_name

    def __repr__(self):
        return '<WindowNameContext %r>' % self.window_name

class ClassContext(Context):
    '''
    Groups keyboard shortcuts that work with a certain class.

    (Uses an isinstance check)
    '''
    __slots__ = ['cls']

    priority = 90

    def __init__(self, name, cls):
        Context.__init__(self, name)
        self.cls = cls

    def __call__(self, window):
        return isinstance(window, self.cls)

    def __repr__(self):
        return '<ClassContext %r>' % self.cls

class GlobalContext(Context):
    '''
    Groups keyboard shortcuts that work any time.
    '''

    priority = 10

    def __init__(self, name = 'Global Shortcuts'):
        Context.__init__(self, name)

    def __call__(self, window, tlw = wx.TopLevelWindow):
        return isinstance(window, tlw)

    def __repr__(self):
        return '<GlobalContext %s>' % self.name

class KeyActionSet(dict):
    def __call__(self, e, win):
        keycode = e.KeyCode

        if WXK_F1 <= keycode <= WXK_F24:
            pass
        elif keycode < 256:
            # we used to check e.UnicodeKey, but that behaves differently
            # on Mac and MSW, and moreover, keycodes for key shortcuts
            # should always correspond to actual keys on the keyboard,
            # meaning we don't need any Unicode conversions, which are used
            # for keycodes greater than 128.
            keycode = ord(chr(keycode).upper())

        key = (e.Modifiers, keycode)
        return self.get(key, None)


def child_and_parents(win):
    'Yields a window and all of its parents.'

    yield win

    win = getattr(win, 'Parent', None)
    while win is not None:
        yield win
        win = win.Parent


def _accelerr(s):
    raise ValueError('illegal accelerator: like "cmd+k" or "k" (you gave "%s")' % s)

# easier to remember replacements for some keys with strangely named wx enums
replacements = {
    'backspace': 'back',
    'capslock' : 'capital',

    # This is evil, but EVT_KEY_DOWN fires different keycodes than EVT_CHAR.
    # We might end up needed to react to both events, depending on which key
    # we're looking for.
    '='        : 43,
}

@memoize
def keycodes(s, accel = True):
    '''
    Turns an accelerator shortcut string into a wx.ACCEL and wx.WXK constants.

    cmd+k           --> (wx.ACCEL_CMD, ord('k'))
    ctrl+alt+return --> (wx.ACCEL_CTRL | wx.ACCEL_ALT, wx.WXK_RETURN)

    If accel is True, wxACCEL_XXX values will be returned; otherwise wxMOD_XXX
    '''
    if isinstance(s, basestring):
        s = s.strip()
        seq = s.split('+')
        for i, _elem in enumerate(seq[:]):
            if _elem == '':
                seq[i] = '+'

        if len(seq) == 1:
            modifiers, key = ['normal'], s
        else:
            modifiers, key = seq[:-1], seq[-1]
    else:
        if not isinstance(s, int):
            _accelerr(s)

        modifiers, key = ['normal'], s

    modifier = 0

    PREFIX = 'ACCEL_' if accel else 'MOD_'

    for mod in modifiers:
        modifier |= getattr(wx, PREFIX + mod.upper())

    if isinstance(key, basestring):
        if len(key) == 1 and key not in replacements:
            key = ord(key.upper())
        else:
            key = replacements.get(key.lower(), key)
            if isinstance(key, basestring):
                try:
                    key = getattr(wx, 'WXK_' + replacements.get(key.lower(), key).upper())
                except AttributeError:
                    _accelerr(s)

    assert isinstance(modifier, int)
    assert isinstance(key, int)
    return modifier, key


class LazyStringImport(str):
    def __call__(self, *a, **k):
        try:
            return self.cb()
        except TypeError, e:
            # TODO: type annotation? interface? something?
            if str(e).endswith('takes exactly 1 argument (0 given)'):
                return self.cb(*a, **k)
            else:
                raise

    @property
    def cb(self):
        try:
            return self._cb
        except AttributeError:
            self._cb = import_function(self)
            return self._cb

# global instance of InputManager
input_manager = InputManager()


if __debug__:
    if 'wxMac' in wx.PlatformInfo:
        AutoDC = wx.PaintDC
    else:
        AutoDC = wx.AutoBufferedPaintDC

    class KeyDebugger(wx.Frame):

        key_event_attrs = 'Modifiers', 'KeyCode', 'UnicodeKey'

        def __init__(self):
            wx.Frame.__init__(self, None, title = _('Key Debugger'))

            self.Bind(wx.EVT_KEY_DOWN, self.on_key)
            self.Bind(wx.EVT_KEY_UP, self.on_key)
            self.Bind(wx.EVT_PAINT, self.on_paint)
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

            self.text = wx.TextCtrl(self, -1)
            self.text.Bind(wx.EVT_TEXT, self.on_text)
            self.label = wx.StaticText(self, -1)
            self.label.SetBackgroundColour(wx.WHITE)

            h = wx.BoxSizer(wx.HORIZONTAL)
            h.Add(self.text, 1, wx.EXPAND)
            h.Add(self.label, 1, wx.EXPAND)

            s = self.Sizer = wx.BoxSizer(wx.VERTICAL)
            s.AddStretchSpacer(1)
            s.Add(h, 0, wx.EXPAND)

        def on_text(self, e):
            try:
                s = str(keycodes(self.text.Value))
            except Exception:
                from traceback import print_exc
                print_exc()
                s = ''

            self.label.SetLabel(s)

            e.Skip()

        def on_paint(self, e):
            dc = AutoDC(self)
            dc.SetFont(self.Font)
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.DrawRectangleRect(self.ClientRect)

            x = 0
            y = 0
            for a in self.key_event_attrs:
                txt = '%s: %s' % (a, getattr(self, a, ''))
                dc.DrawText(txt, x, y)
                y += 15

            if hasattr(self, 'KeyName'):
                dc.DrawText(self.KeyName, x, y)

        def on_key(self, e):
            for a in self.key_event_attrs:
                setattr(self, a, getattr(e, a))

            from gui.toolbox.keynames import keynames
            self.KeyName = keynames.get(e.KeyCode, '')

            self.Refresh()

