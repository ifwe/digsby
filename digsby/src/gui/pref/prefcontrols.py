'''
Utility functions for building GUI controls bound to the preference dictionary.
'''

from __future__ import with_statement

from wx import Choice, EXPAND, LEFT, EVT_CHOICE, BOTTOM, ALIGN_CENTER_VERTICAL, ALL, \
    EVT_LEFT_DOWN, EVT_LEFT_UP, HORIZONTAL,VERTICAL, Rect, RectS
from wx import StaticBox, StaticBoxSizer, StaticText, TOP, Window

import wx, re

from util.primitives.error_handling import traceguard
from util.primitives.funcs import autoassign, isiterable, do
from util.primitives.misc import clamp
import logging; log = logging.getLogger("prefs")
from itertools import izip
from gui.toolbox import wx_prop
from gui.textutil import CopyFont
from gui.anylists import AnyList
from gui.validators import LengthLimit

from common import profile
from config import platformName
#log.setLevel(logging.DEBUG)
info = log.info; warning = log.warning
__metaclass__ = type

# matcher for formatting strings like %2(name.subname)d
_fmtmatcher = re.compile(r'%(\d*)\(([A-Za-z_]?[A-Za-z_0-9\.]+[A-Za-z_0-9])\)([sdf])')

typechar_to_type = dict(f=float, d=int)

from contextlib import contextmanager

class NullEvtHandler(wx.EvtHandler):
    def AddPendingEvent(self, evt):
        print 'SSSHHH secret', evt


@contextmanager
def secret(ctrl):
    ctrl.PushEventHandler(NullEvtHandler())
    try:
        yield
    finally:
        ctrl.PopEventHandler()

wx.Control.secret = secret

# These functions are the only interface to the outside preferences

def pref_mapping(key):
    if not isinstance(key, str):
        raise TypeError('prefname must be a string')

    if key.startswith('local.'):
        key = key[len('local.'):]
        mapping = profile.localprefs
    else:
        mapping = profile.prefs

    return key, mapping


def mark_pref(prefname, value):
    'Change a preference!'

    if not isinstance(prefname, str):
        raise TypeError('prefname must be a string')

    prefname, mapping = pref_mapping(prefname)

    # Set and log the change
    mapping[prefname] = value
    log.info('%s ---> %s', prefname, mapping[prefname])

def get_pref(prefname, default=sentinel):
    'Get a preference!'

    prefname, mapping = pref_mapping(prefname)

    try:
        v = mapping[prefname]
    except KeyError, e:
        if default is sentinel:
            try:
                return profile.defaultprefs[prefname]
            except KeyError:
                raise e
        else: v = default

    return v

def get_prefs():
    return profile.prefs

def get_localprefs():
    return profile.localprefs

def wx_evt_type(component):

    if isinstance(component, wx.Sizer):
        component = component.Children[0].Window

    if type(component) is not type:
        component = type(component)

    types = {
             wx.CheckBox    : wx.EVT_CHECKBOX,
             }
    return types[component]

#
# GUI elements
#

class PrefsPanel(wx.Panel):
    'Simple backing wxPanel for pref controls.'

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, size=(0,0), pos=(-50,50))

        if 'wxMac' not in wx.PlatformInfo:
            self.BackgroundColour = wx.WHITE

class PrefGroup(object):

    SPACING = 4

    def __init__(self, title, *elems):
        if isinstance(title, tuple):
            title, prefix = title
        else:
            prefix = ''
        autoassign(self, locals())

    if 'wxMSW' in wx.PlatformInfo:
        # this implementation uses a wx.StaticBox
        def build(self, parent):
            box    = StaticBox(parent, -1, self.title)
            bsizer = StaticBoxSizer(box, VERTICAL)
            self.add_to_sizer(parent, bsizer)
            return bsizer
    else:
        # this implementation does not
        def build(self, parent):
            sz = VSizer()
            text = StaticText(parent, -1, self.title)
            text.SetBold()
            sz.Add(text)

            self.add_to_sizer(parent, sz)
            return sz

    def __call__(self, parent):
        return self.build(parent)

    def add_to_sizer(self, parent, sz):
        for elem in self.elems:
            if callable(elem):
                if hasattr(elem, 'func_code') and elem.func_code.co_argcount == 2:
                    elem = elem(parent, self.prefix)
                else:
                    elem = elem(parent)
            sz.Add(elem, 0 if len(self.elems) > 1 else 1, EXPAND | ALL, self.SPACING)


class EnabledGroup(PrefGroup):
    SPACING = 3
    def __init__(self, title, required, *elems):
        PrefGroup.__init__(self, title, *elems)
        try:
            self.req_cmp, self.req_cb = required
        except TypeError:
            self.req_cmp = required
            self.req_cb = lambda v, *a: v

    def build(self, parent):
        sz = VSizer()
        if self.title:
            text = StaticText(parent, -1, self.title)
            text.SetBold()
            sz.Add(text)

        if callable(self.req_cmp):
            if self.req_cmp.func_code.co_argcount == 2:
                self.req_cmp = self.req_cmp(parent, self.prefix)
            else:
                self.req_cmp = self.req_cmp(parent)

        sz.Add(self.req_cmp, 0, EXPAND | TOP, 7)
        spc_sz = HSizer()
        sz.Add(spc_sz,0, EXPAND)
        spc_sz.AddSpacer(int(self.req_cmp.Size.height*1.5))
        cmp_sz = VSizer()
        spc_sz.Add(cmp_sz,1)

        self.add_to_sizer(parent, cmp_sz)
        return sz

    def add_to_sizer(self, parent, sz):

        components = [] # collection of wxObjects
        for elem in self.elems:
            if callable(elem):
                if elem.func_code.co_argcount == 2:
                    elem = elem(parent, self.prefix)
                else:
                    elem = elem(parent)

            sz.Add(elem, 0 if len(self.elems) > 1 else 1, EXPAND | TOP, border = self.SPACING)
            components.append(elem)

        if components:
            def callback(e):
                for c in components:
                    c.Enabled = self.req_cb(self.req_cmp.GetValue(), c)
                if e: e.Skip()

            self.req_cmp.Bind(wx_evt_type(self.req_cmp), callback)
            callback(None)

        return sz

class OffsetGroup(PrefGroup):
    SPACING = 3
    def __init__(self, title, header, *elems):
        PrefGroup.__init__(self, title, *elems)
        self.header = header

    def build(self, parent):
        sz = VSizer()
        if self.title:
            text = StaticText(parent, -1, self.title)
            text.SetBold()
            sz.Add(text)

        sz.Add(self.header, 0, EXPAND | TOP, 7)
        spc_sz = HSizer()
        sz.Add(spc_sz,0, EXPAND)
        spc_sz.AddSpacer(int(self.header.Size.height*1.5))
        cmp_sz = VSizer()
        spc_sz.Add(cmp_sz,1)

        self.add_to_sizer(parent, cmp_sz)
        return sz

    def add_to_sizer(self, parent, sz):
        components = [] # collection of wxObjects
        for elem in self.elems:
            sz.Add(elem, 0 if len(self.elems) > 1 else 1, EXPAND | TOP, border = self.SPACING)
            components.append(elem)

        return sz

def MakeEnabledSizer(baseclass):
    class EnabledSizer(baseclass):
        def __init__(self, *a, **k):
            try:
                baseclass.__init__(self, *a, **k)
            except:
                import sys; print >> sys.stderr, baseclass
                raise
            self._enabled = True

        def SetEnabled(self, val=True):
            res = self._enabled != val
            for child in self.Children:
                if child.Window:
                    child.Window.Enabled = val

            self._enabled = val
            return res

        def SetSelection(self, i):
            do(c.Window.SetSelection(i) for c in self.Children if hasattr(getattr(c, 'Window', None), 'SetSelection'))

        def GetEnabled(self):
            return self._enabled

        Enable = SetEnabled

        Enabled = property(GetEnabled, SetEnabled)

    return EnabledSizer

def HSizer(cls = wx.BoxSizer, *a, **k):
    'Returns a horizontal box sizer.'
    return MakeEnabledSizer(cls)(HORIZONTAL, *a, **k)

def VSizer(cls = wx.BoxSizer, *a, **k):
    'Returns a vertical box sizer.'
    return MakeEnabledSizer(cls)(VERTICAL, *a, **k)

def PlusMinus():
    def buildplusminus(panel):
        h = HSizer()
        h.AddStretchSpacer(1)
        plus  = wx.Button(panel, wx.ID_NEW,    '+', size=(30,15))
        minus = wx.Button(panel, wx.ID_DELETE, '-', size=(30,15))
        h.GetButtons = lambda p=plus, m=minus: (p, m)
        h.Add(plus,  0, wx.ALL | wx.ALIGN_RIGHT)
        h.Add(minus, 0, wx.ALL | wx.ALIGN_RIGHT)
        return h
    return buildplusminus


class Text(wx.TextCtrl):
    'Text field. Updates its preference upon losing focus.'
    def __init__(self, parent, prefname, name='', size=wx.DefaultSize, validator=None, _type=None, style = 0):
        wx.TextCtrl.__init__(self, parent, size=size, validator=(validator or LengthLimit(2048)), style = style)
        if not isinstance(prefname, basestring):
            prefix, prefname = prefname
        else:
            prefix = ''

        self.validator = validator

        self.type = _type
        self.prefix = prefix
        self.prefname = prefname
        self._style = style

        if self.validator is not None:
            self.Bind(wx.EVT_CHAR, self.validator.OnChar)
            self.Bind(wx.EVT_TEXT, self.validator.OnText)

        if self.pname.startswith('local.'):
            self.prefname = self.pname[len('local.'):]
            self.prefix = ''
            self.mapping = profile.localprefs
        else:
            self.mapping = profile.prefs

        self.mapping.link(self.pname, self.pref_changed)

        self.secret = 0
        self.Bind(wx.EVT_KILL_FOCUS, self.changed)

    def changed(self, e):
        self.mark_pref(self.Value)

    def pref_changed(self, val):
        self.SetValue(unicode(val))

    @property
    def pname(self):
        'Glues a prefix on a name, if it exists.'
        if self.prefname.startswith('local.'):
            return self.prefname
        return self.prefix + '.' + self.prefname if self.prefix else self.prefname
    def mark_pref(self, val):
        '''
        Set the value in the preferences dictionary.
        '''
        if self.pname not in self.mapping:
            raise KeyError("Trying to set a preference that doesn't exist: %s" % self.pname)

        if self.type is not None:
            try:
                val = self.type(val)
            except Exception:
                log.error('"pref[%r] = %r" : value does not match %r, not setting it', self.pname, val, self.type)
                return

        if self.secret:
            self.mapping.secret_set(self.pname, val)
        else:
            self.mapping[self.pname] = val
        log.debug('%s ---> %s', self.pname, val)

    def get_pref(self):
        return self.mapping[self.pname]

    @contextmanager
    def secret(self):
        self.PushEventHandler(NullEvtHandler())
        self.secret += 1
        try:
            yield self
        finally:
            self.secret -= 1
            self.PopEventHandler()

def Button(label,callback=None):
    def makeButton(parent,prefix = ''):
        button = wx.Button(parent,-1,label, style=wx.BU_EXACTFIT)

        if callback:
            button.Bind(wx.EVT_BUTTON,lambda e: callback(button))

        return button

    return makeButton

def Label(text):
    def makeStext(parent,prefix=''):
        return SText(parent,text)

    return makeStext


WindowClass = getattr(wx, '_Window', wx.Window)

def SText(parent, text):
    if not isinstance(parent, WindowClass):
        raise TypeError('first arg to SText must be a wx.Window')
    return StaticText(parent, -1, text)

def Check(prefname, caption, callback = None, default = False, help = None):
    '''
    A checkbox for a single preference.

    Optionally, a %2(some.pref)d type string in the caption will be turned
    into an additional textbox-linked-preference.
    '''
    if callback is None:
        callback = lambda *a, **k: None

    if caption.find('%') != -1:
        def my_check(parent, prefix = ''):
            p = wx.Panel(parent)
            s = caption
            textctrl = None
            checkPref = pname(prefix, prefname) if prefname is not None else None

            checkbox = boundcheckbox(p, s[:s.find('%')], checkPref,
                                     callback=(lambda v: (textctrl.Enable(v), callback(v))),
                                     default = default)
            elems = [ checkbox ]
            match = _fmtmatcher.search(s)

            if match:
                n, name, type = match.groups()
                textctrl = Text(p, pname(prefix, name), name,
                                size = (int(n) * 8 +10,-1),
                                validator = validators[type](),
                                _type=typechar_to_type.get(type, lambda x:x))
                textctrl.SetMaxLength(long(n))
                textctrl.Enable(checkbox.GetValue())
                elems += [textctrl]
                elems += [wx.StaticText(p, -1, s[match.span()[1]:])]

            hz = p.Sizer = HSizer()
            hz.check = checkbox
            hz.AddMany([(elem, 0, ALIGN_CENTER_VERTICAL) for elem in elems])

            return p
    else:
        def my_check(parent, prefix='', default = default):
            return boundcheckbox(parent, caption, pname(prefix, prefname), callback, default = default, help = help)

    return my_check

def CheckChoice(checkprefname, choiceprefname, text, choices, allow_custom = False, max_width=None):
    'Checkbox with dropdown after.'

    def build(parent, prefix = ''):
        choice = Choice(choiceprefname, choices, allow_custom = allow_custom, max_width=max_width)(parent, prefix)
        choice.Enable(bool(get_pref(pname(prefix,checkprefname))))

        check = Check(checkprefname, text,
                      lambda v: choice.Enable(v))(parent, prefix)

        sz = HSizer()
        sz.Add(check,  0, EXPAND | ALIGN_CENTER_VERTICAL)
        sz.Add(choice, 0, EXPAND | ALIGN_CENTER_VERTICAL)

        sz.Bind = check.Bind
        sz.GetValue = check.GetValue
        sz.SetValue = check.SetValue

        return sz
    return build


class _AutoCombo(wx.ComboBox):
    def __init__(self, *a, **k):
        k['style'] = k.get('style', 0) | wx.CB_DROPDOWN #| wx.CB_READONLY

        if k.get('validator', None) is None:
            k['validator'] = LengthLimit(1024)

        wx.ComboBox.__init__(self, *a, **k)

        self._items = self.Items
        self._modifying = False
        self.last_selection = self.Value

    def bind_evts(self):
        self.Bind(wx.EVT_TEXT, self.keypressed)

    def keypressed(self, e):
        e.Skip()
        if self._modifying: return

        bad_selection = False
        self._modifying = True
        oldval = self.Value
        newitems = filter(lambda x: x.lower().startswith(e.String.lower()), self.Items)
        if not newitems:
            newitems = self.Items
            bad_selection = True
            newval = self.last_selection
            newval = e.String
        else:
            newval = newitems[0]
        self.Value = newval
        if bad_selection:
            wx.Bell()
            self.Value = self.last_selection
            self.SetMark(0, len(newval))
            self.SetInsertionPoint(len(newval))
        else:
            self.SetMark(len(oldval), len(newval))
            self.last_selection = newval
        self._modifying = False

    def on_close(self):
        pass

def ComboOrChoice(mytype):
    class mytype(mytype):
        def DeleteString(self, s):
            idx = self.FindString(s)
            if idx != wx.NOT_FOUND:
                self.Delete(idx)
        def __contains__(self, s):
            return self.FindString(s) != wx.NOT_FOUND

    def Choice(prefname, choices, caption='', callback=None, allow_custom = False, do_mark_pref = True, max_width=None):
        '''
        Choice dropdown.

        choices is a list of tuples, like:
            [('prefkey', '&Nice Pref Name'), ...]

            do_mark_pref   if True, automatically sets the preference when changed
        '''


        try:
            prefnames, displaynames = izip(*choices)
            prefnames, displaynames = list(prefnames), list(displaynames)
        except ValueError:
            prefnames, displaynames = choices, list(choices)
        prefnames = list(prefnames)

        def build_choice(parent, prefix='', prefnames=prefnames, displaynames=displaynames):
            def on_choice(e):
                pref, value = pname(prefix, prefname), prefnames[e.GetInt()]
                if do_mark_pref: mark_pref(pref, value)
                if callback:
                    with traceguard:
                        callback(pref, value)

            _p = pname(prefix, prefname) if prefname is not None else None

            if not prefnames:
                prefnames = [get_pref(_p)]
                displaynames = list(prefnames)

            try:
                c = mytype(parent, choices = displaynames if displaynames != [None] else [''])
            except Exception:
                import sys
                print >> sys.stderr, repr(displaynames)
                raise

            if max_width is not None:
                sz = (max_width, c.Size.height)
                c.SetSize(sz)
                c.SetMinSize(sz)
                #hit().Size = hit().BestSize = hit().MaxSize = hit().MinSize = (120, 23)

            try:
                if _p is None: raise ValueError()
                c.Selection = prefnames.index(get_pref(_p))
            except KeyError:
                c.Selection = 0
            except ValueError, unused_e:
                if allow_custom:
                    disp = _('Custom ({prefval})').format(prefval=get_pref(_p))
                    c.Append(disp)
                    prefnames    += [get_pref(_p)]
                    displaynames += [disp]
                    c.Selection = c.GetCount() - 1
                else:
                    c.Selection = 0

#            def pref_changed(val):
#
#                try:
#                    newSelection = prefnames.index(val)
#                except ValueError, unused_e:
#                    return
#
#                if c.Selection != newSelection:
#                    c.Selection = newSelection
#                    evt = wx.CommandEvent(wx.wxEVT_COMMAND_CHOICE_SELECTED, c.Id)
#                    evt.Int = newSelection
#                    c.AddPendingEvent(evt)
#
#
#            if _p:
#                profile.prefs.link(_p, pref_changed, obj = c)
            c.Bind(wx.EVT_CHOICE, on_choice)

            def PrefValue(c=c):
                i = c.GetSelection()
                if i == -1: i = 0
                return prefnames[i]

            c.GetPrefValue = PrefValue

            if caption != '':
                sz = HSizer()
                sz.Add(SText(parent, caption), 0, 3)
                sz.Add(c, 0, wx.EXPAND)
                return sz
            else:
                return c
        return build_choice
    return Choice

Choice = ComboOrChoice(wx.Choice)
Combo = ComboOrChoice(wx.ComboBox)
AutoCombo = ComboOrChoice(_AutoCombo)

def LocationButton(prefname, caption, default_pref_val=sentinel):
    def _build(p, prefix = ''):


        currentpath = get_pref(pname(prefix, prefname), default_pref_val)

        button = wx.Button(p, -1, currentpath, style = wx.BU_LEFT) #wx.DirPickerCtrl(p, -1)

        def OnButton(event):

            currentpath = get_pref(pname(prefix, prefname), default_pref_val)

            newpath = wx.DirSelector(_('Choose a folder'), currentpath)

            if newpath:


                from path import path
                newpath = path(newpath)

                if not newpath.isabs():
                    newpath = newpath.abspath()

                button.SetLabel(newpath)

                mark_pref(pname(prefix, prefname), newpath)


        button.Bind(wx.EVT_BUTTON, OnButton)

        if caption:
            sz = HSizer()
            sz.Add(SText(p, caption), 0, wx.EXPAND | wx.ALL, 3)
            sz.Add(button, 1, wx.EXPAND | wx.ALL)
            ctrl = sz
        else:
            ctrl = button

        return ctrl

    return _build

def Browse(prefname, caption, type, default_pref_val=sentinel):
    def _build(p, prefix):
        def new_val(self, ):

            from path import path
            p = path(picker.GetPath())

            if not p:
                _pref = pname(prefix, prefname + '_' + type)
                _pref, d = pref_mapping(_pref)
                d.pop(_pref, None)
                return

            if not p.isabs():
                p = p.abspath()
                #picker.SetPath(p)

            mark_pref(pname(prefix, prefname + '_' + type), p)

        if type == 'file':
            picker = wx.FilePickerCtrl(p, -1, style = wx.FLP_DEFAULT_STYLE | wx.FLP_USE_TEXTCTRL)
            picker.Bind(wx.EVT_FILEPICKER_CHANGED, new_val)
        else:
            picker = wx.DirPickerCtrl(p, -1, style = wx.DIRP_USE_TEXTCTRL)
            picker.Bind(wx.EVT_DIRPICKER_CHANGED, new_val)

        picker.SetPath(get_pref(pname(prefix, prefname + '_' + type), default_pref_val))

        if caption:
            sz = HSizer()
            sz.Add(SText(p, caption), 0, wx.EXPAND | wx.ALL, 3)
            sz.Add(picker, 1, wx.EXPAND | wx.ALL)
            ctrl = sz
        else:
            ctrl = picker

        return ctrl
    return _build

def CheckBrowse(prefname, caption, type):
    'Checkbox with an additional file browser field and button.'

    def _build(p, prefix):

        picker =  Browse(prefname, '', type)(p,prefix)

        s = HSizer()

        checkbox = boundcheckbox(p, caption, pname(prefix, prefname),
                                 callback=lambda v: picker.Enable(v))

        s.Add(checkbox, 0, wx.EXPAND | wx.ALL)

        picker.Enable(checkbox.IsChecked())
        s.Add(picker, 1, wx.EXPAND | wx.LEFT, 5)
        return s
    return _build

#
#def Radio(label, style=0, prefname=None, prefvalue=None, callback=None):
#    def makeradio(parent, prefix = ''):
#        radio = wx.RadioButton(parent, -1, label=label, style=style)
#
#        def OnSelect(e):
#            if radio.Value:
#                if prefname is not None:
#                    mark_pref(pname(prefix,prefname),prefvalue)
#
#                if callback is not None:
#                    callback(e)
#
#
#        radio.Bind(wx.EVT_RADIOBUTTON, OnSelect)
#
#        return radio


def RadioBox(prefname, choices):
    def makeradio(parent, prefix = ''):
        return NewRadioBox(parent, prefname, choices, prefix)
    return makeradio

class NewRadioBox(wx.Panel):
    def __init__(self,parent,prefname, choices, prefix = ''):
        wx.Panel.__init__(self, parent)

        self.prefvalues, self.displaynames = zip(*choices)
        self.prefix     = prefix
        self.prefname   = prefname
        self.prefvalues = list(self.prefvalues)
        self.Sizer      = wx.BoxSizer(wx.VERTICAL)
        self.radios     = []

        for name in self.displaynames:
            radio = wx.RadioButton(self,-1,name)
            self.radios.append(radio)
            self.Sizer.Add(radio,0,wx.TOP|wx.BOTTOM,3)

        try:
            sel = self.prefvalues.index(get_pref(prefname))
        except:
            sel = 0

        self.radios[sel].SetValue(True)

        self.Bind(wx.EVT_RADIOBUTTON,self.OnRadio)

    def OnRadio(self,event):
        mark_pref(self.prefname, self.prefvalues[self.radios.index(event.EventObject)])



class StickySlider(wx.Slider):
    def __init__(self, parent, start=0, stop=None, step=1, value=0):
        if isiterable(start):
            values = start
        else:
            if stop is None:
                start, stop = 0, start

            if start > stop and step > 0:
                step *= -1

            values = range(start, stop, step)

        max_ = max(values)
        min_ = min(values)
        reverse = step < 0

        self.start = start
        self.step = step

        style = wx.SL_HORIZONTAL #| wx.SL_AUTOTICKS | wx.SL_LABELS
        style |= wx.SL_INVERSE * reverse

        wx.Slider.__init__(self, value=value, minValue=min_, maxValue=max_, parent=parent, style = style)
        self.SetTickFreq(step, start)

    def bind_evts(self):
        self.Bind(wx.EVT_SCROLL_CHANGED, self.stick)
        self.Bind(wx.EVT_SCROLL_THUMBTRACK, self.stick)
        self.Bind(wx.EVT_KEY_DOWN, self.keypress)

    def stick(self, e):
        e.Skip()

        if not self.Enabled: return

        v = self.Value
        v -= self.start
        div, mod = divmod(v, self.step)
        move_up = bool((mod * 2) // self.step)

        new_val = (div + move_up) * self.step
        self.Value = new_val + self.start


    def keypress(self, e):
        if not self.Enabled: return
        if e.KeyCode in (wx.WXK_UP, wx.WXK_RIGHT):
            self.Value += self.step
            self.Value = min(self.Value, self.Max)

        elif e.KeyCode in (wx.WXK_DOWN, wx.WXK_LEFT):
            self.Value -= self.step
            self.Value = max(self.Value, self.Min)

def Slider(prefname, caption='', start=0, stop=None, step=1, value=0, callback=None,
           fireonslide = False, unit=_('{val}px'), default=sentinel):

    def build_slider(parent, prefix=''):

        c = StickySlider(parent, start, stop, step, value)

        def ctrl_string(c):
            return unit.format(val=unicode(c.Value))

        lbl = SText(parent, ctrl_string(c))

        def on_select(e):
            mark_pref(pname(prefix, prefname), c.Value)
            lbl.Label = ctrl_string(c)
            if callback: callback(prefname, c.Value)

        def on_slide(e):
            lbl.Label = ctrl_string(c)

        try:
            _p = pname(prefix, prefname)
            c.Value = int(get_pref(_p, default=default))
        except ValueError:
            c.Value = value

        c.Bind(wx.EVT_SCROLL_CHANGED, on_select)
        c.Bind(wx.EVT_SCROLL_THUMBTRACK, on_slide if not fireonslide else on_select)
        c.bind_evts()
        if caption != '':
            sz1 = VSizer()
            sz1.Add(SText(parent, caption), 0, wx.EXPAND | wx.ALL, 3)

            sz2 = HSizer()
            sz2.Add(c, 1, wx.EXPAND | wx.ALL, 3)
            sz2.Add(lbl, 0, wx.EXPAND | wx.ALL, 3)
            sz1.Add(sz2, 1, wx.EXPAND | wx.ALL, 3)
            return sz1, c
        else:
            return c, c
    return build_slider

#
#
#

def boundcheckbox(parent, cap, prefname, callback = None, default = False, help=None):
    checkbox = wx.CheckBox(parent, -1, _(cap))

    def check(val):
        if prefname is not None:

#            if get_pref(prefname) != val:
            mark_pref(prefname, val)

        if callback: callback(val)

    checkbox.SetValueEvent = check

    if prefname is not None:
        checkbox.SetValue(bool(get_pref(prefname, default)))
#        profile.prefs.link(prefname,lambda val: checkbox.SetValue(val))

    checkbox.Bind(wx.EVT_CHECKBOX, lambda e: check(e.IsChecked()))

    if help is not None:
        from gui.toolbox import HelpLink

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddMany([ (checkbox, 0, wx.EXPAND),
                        (HelpLink(parent, help), 0, wx.EXPAND) ])
        sizer.AddStretchSpacer(1)

        return sizer

    return checkbox

from gui.validators import common_validators as validators

font_sizes = map(str, range(6,13)+range(14,29)+[36,48,72])


def FontFaceAndSize(prefname='', caption='', callback=None):
    import gui

    fontlist = gui.textutil.GetFonts()
    sizelist = font_sizes

    def build(parent, prefix=''):
        fontchoice = wx.Choice(parent, choices=fontlist)
        sizechoice = wx.Choice(parent, choices=sizelist)

        font_pref = pname(prefix, prefname+'_face')
        size_pref = pname(prefix, prefname+'_size')

        def onfont(e):
            pref, value = font_pref, fontchoice.GetStringSelection()
            mark_pref(pref, value)
            if callback: callback(pref, value)

        def onsize(e):
            pref, value = size_pref, sizechoice.StringSelection
            mark_pref(pref, value)
            if callback: callback(pref, value)

        try:
            fontchoice.SetStringSelection(get_pref(font_pref))
        except ValueError, unused_e:
            fontchoice.Selection = 0

        try:
            sizechoice.SetStringSelection(unicode(get_pref(size_pref)))
        except ValueError, unused_e:
            sizechoice.Selection = 0

        fontchoice.Bind(EVT_CHOICE, onfont)
        sizechoice.Bind(EVT_CHOICE, onsize)


        sz_ = HSizer()
        sz_.Add(fontchoice, 1, EXPAND)
        sz_.Add(sizechoice, 0, EXPAND | LEFT, 3)

        if caption != '':
            sz = VSizer()
            sz.Add(SText(parent, caption), 0, EXPAND | BOTTOM, 3)
            sz.Add(sz_, 1, EXPAND | LEFT, 18)
            return sz
        else:
            return sz_
    return build

###################################################################################################
from gui.anylists import AnyRow
class PrivacyListRow(AnyRow):
    row_height = 20
    def __init__(self, parent, data):
        AnyRow.__init__(self, parent, data, False)
        self.mouse_flag = False
        self.Bind(EVT_LEFT_DOWN, self.onleftdown)
        self.Bind(EVT_LEFT_UP, self.leftup)

    @property
    def popup(self):
        return None

    @property
    def image(self):
        return None

#    def LayoutMore(self, sizer):
#        sizer.Add(self.rem_button, 0, ALL | ALIGN_CENTER_VERTICAL, 10)

    def ConstructMore(self):
        from gui import skin
#        self.rem_button = wx.StaticBitmap(self, -1, skin.get('AppDefaults.removeicon'))
        self.rem_ico = skin.get('AppDefaults.removeicon')



    def onleftdown(self, e):
        rem_ico_size = self.rem_ico.Size

        rect = Rect(self.Size.width - rem_ico_size.width - 4, self.Size.height//2 - rem_ico_size.height//2,*rem_ico_size)

        if rect.Contains(e.Position):
            self.mouse_flag = True
        else:
            e.Skip()

    def leftup(self, e):

        rem_ico_size = self.rem_ico.Size

        rect = Rect(self.Size.width - rem_ico_size.width - 4, self.Size.height//2 - rem_ico_size.height//2,*rem_ico_size)

        if rect.Contains(e.Position):
            if self.mouse_flag:
                remove_row = getattr(self.Parent, 'remove_row', None)
                if remove_row is not None:
                    remove_row(self.data)
                else:
                    p = self.Parent.Parent.Parent
                    wx.CallAfter(p.remove_item, self.data)
        else:
            e.Skip()
        self.mouse_flag = False

    def PaintMore(self, dc):
        rect= RectS(self.Size)

        rem_ico = self.rem_ico

        dc.DrawBitmap(rem_ico,rect.Width - rem_ico.Width - 4, rect.Height//2 - rem_ico.Height//2,True)


class AutoCompleteListEditor(wx.Frame):
    def __init__(self, *a, **k):
        wx.Frame.__init__(self, *a, **k)
        self._panel = p = wx.Panel(self, -1)
        self._text = _AutoCombo(p, -1, style=wx.TE_PROCESS_ENTER)

        listvals = self.get_values()

        self.list = AnyList(p, data = listvals, row_control = PrivacyListRow, style = 8,
                            draggable_items = False)
        self.list.BackgroundColour = wx.WHITE

        self.populate_combo()

        self.add_btn = wx.Button(p, -1, _('Add'), style = wx.BU_EXACTFIT)
        self.add_btn.MinSize = wx.Size(-1, 0)
        if platformName != 'mac':
            self.add_btn.Font = CopyFont(self.add_btn.Font, weight = wx.BOLD)
        else:
            self.add_btn.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)

        tb_sz = HSizer()
        tb_sz.Add(self._text, 1, ALIGN_CENTER_VERTICAL)
        tb_sz.Add(self.add_btn, 0, EXPAND | ALL | ALIGN_CENTER_VERTICAL)

        p.Sizer = sz = VSizer()
        sz.Add(tb_sz,     0, EXPAND | ALL, border=3)
        sz.Add(self.list, 1, EXPAND | ALL, border=3)

        self.add_btn.Bind(wx.EVT_BUTTON, self._add_clicked)
        self._text.Bind(wx.EVT_TEXT, self.set_btn_enable)
        self._text.Bind(wx.EVT_TEXT_ENTER, self._add_clicked)

        self.set_btn_enable()
        self.Layout()

    text = wx_prop('_text')

    def set_btn_enable(self, e=None):
        self.add_btn.Enable(self.validate(self.text))

    def populate_combo(self):
        self._text.Clear()
        self._text.AppendItems(self.get_autovalues())

    def _add_clicked(self, e):
        if not self.validate(self.text):
            log.error('%s does not validate. Not adding item.', self.text)
            return

        if self.text:
            self.add_item(self.text)
        self.text = ''

    def _rem_clicked(self, e):
        sel = self.list.Selection
        if sel == wx.NOT_FOUND: return
        obj = self.list.data[sel]
        #_str = self.list.GetString(sel)
        self.remove_item(obj)
        first = clamp(sel, 0, len(self.list.data)-1)
        print first, len(self.list.data)-1
        if first >= 0:
            self.list.Selections = [first]

    def _get_list(self):
        return self.list.data

    def _set_list(self, val):
        self.list.data[:] = val
        self.list.on_data_changed()

    mylist = property(_get_list, _set_list)

    def get_values(self):
        raise NotImplementedError

    def add_item(self, _str):
        self.list.data.append(_str)
        self.populate_combo()
        self.set_btn_enable()
        self.list.on_data_changed()

    def remove_item(self, obj):
        assert obj in self.list.data
        self.list.RemoveItem(obj)
        self.populate_combo()

    def get_matches(self, _str):
        raise NotImplementedError

    def get_autovalues(self):
        raise NotImplementedError

    def __contains__(self, x):
        return x in self.list

    def on_close(self):
        self._text.on_close()
        self.list.on_close()

def pname(prefix, name):
    'Glues a prefix on a name, if it exists.'
    if name and name.startswith('local.'):
        return name
    return prefix + '.' + name if prefix else name
