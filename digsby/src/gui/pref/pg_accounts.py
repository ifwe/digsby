import logging
from traceback import print_exc
from util.introspect import memoize
log = logging.getLogger('pg_accounts2')
import wx
from gui.uberwidgets.PrefPanel import PrefPanel
from gui.pref.prefcontrols import HSizer, VSizer, mark_pref, SText
from wx import EXPAND
import protocols
from gui.textutil import default_font
from gui.accountslist import AccountRow
from gui.accountslist import AccountList
from util.primitives.funcs import find
from operator import attrgetter

import hooks
from contacts.sort_model import ChoiceModel
from pg_contact_list import yield_choices, release_syncs
from common import pref, profile
from peak.util.addons import AddOn
import common
from peak.events import trellis
import util.observe as observe
from util.lego.lattice.blocks import IValueListener
from util.lego.lattice.frame import ObservableAttrBindable

class IServiceProviderGUIMetaData(protocols.Interface):
    provider_id = unicode()
    icon = property() #wx.Bitmap (skin.get....)
    name = unicode()
    popularity = int() #needed for comparison
    service_components = list() #IServiceComponentGUIData

class IServiceProviderInstanceGUIMetaData(protocols.Interface):
    account_name = unicode()
    #service_components = list()

class IServiceComponentGUIMetaData(protocols.Interface):
    icon = property() #wx.Bitmap (skin.get....)
    service_name = unicode() #'Yahoo Messenger'
    type = str() #twitter is a 'social', aim is an 'im'
    component_id = str() # 'msn'

from plugin_manager.plugin_registry import ServiceProviderPlugin, \
    ServiceComponentPlugin

import services.service_provider as sp

class ServiceProviderPluginGUIMetaData(protocols.Adapter):
    protocols.advise(asAdapterForTypes = [ServiceProviderPlugin],
                     instancesProvide = [IServiceProviderGUIMetaData])
    @property
    def provider_id(self):
        return self.subject.provider_id
    @property
    def icon(self):
        from gui import skin
        return skin.get('serviceprovidericons.%s' % self.subject.provider_id)
    @property
    def provider_name(self):
        return self.subject.name
    @property
    def popularity(self):
        return getattr(getattr(getattr(self.subject, 'info', None), 'provider_info', None), 'popularity', 0)
    @property
    def service_components(self):
        return sp.get_meta_components_for_provider(self.subject.provider_id)

class ServiceComponentPluginGUIMetaData(protocols.Adapter):
    protocols.advise(asAdapterForTypes = [ServiceComponentPlugin],
                     instancesProvide = [IServiceComponentGUIMetaData])
    @property
    def icon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.subject.shortname)
    @property
    def service_name(self):
        return self.subject.info.get('service_name') or self.subject.info.get('name')
    @property
    def component_id(self):
        return self.subject.shortname
    @property
    def type(self):
        return self.subject.component_type

class StringServiceComponentGUIData(object):
    protocols.advise(asAdapterForTypes=[basestring],
                     instancesProvide=[IServiceComponentGUIMetaData])
    def __init__(self, subject):
        self.subject = subject
    @property
    def service_name(self):
        from common import protocolmeta
        p = protocolmeta.protocols.get(self.subject)
        if p:
            name = p.get('service_name') or p.get('name')
        else:
            name = self.subject.capitalize()
        return name
        return p.name if p else self.subject.capitalize()
    @property
    def icon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.subject, skin.get('serviceprovidericons.%s' % self.subject, None))
    @property
    def type(self):
        from common import protocolmeta
        p = protocolmeta.protocols.get(self.subject)
        return p.get('component_type', p.get('type')) if p else 'unknown'
    @property
    def component_id(self):
        return self.subject

def get_meta_for_provider(provider_instance):
    return IServiceProviderGUIMetaData(sp.get_meta_service_provider(provider_instance.provider_id))

protocols.declareAdapterForType(IServiceProviderGUIMetaData, get_meta_for_provider, sp.ServiceProvider)

class IPaintable(protocols.Interface):
    def on_paint(e):
        pass

class wxPaintingMixin(object):
    def __init__(self, *a, **k):
        try:
            IPaintable(self)
        except protocols.AdaptationFailure:
            raise
        super(wxPaintingMixin, self).__init__(*a, **k)
        self.Bind(wx.EVT_PAINT, self.on_paint)

class IDrawable(protocols.Interface):
    def draw(dc):
        pass

class IDrawingContext(protocols.Interface):
    def DrawText(text, x, y): pass
    def DrawBitmap(bmp, x, y): pass
    def DrawRoundedRectangleRect(rect, radius): pass

def wxPaintEventDrawingContextAdapter(event):
    if event.EventType == wx.EVT_PAINT:
        return wx.AutoBufferedPaintDC(event.GetEventObject())

protocols.declareImplementation(wx.DC, instancesProvide=[IDrawingContext])
protocols.declareAdapterForType(IDrawingContext, wxPaintEventDrawingContextAdapter, wx.Event)

class IRectagleFactory(protocols.Interface):
    def get_rect(x,y,w,h):
        pass

class wxRectangleFactory(protocols.Adapter):
    protocols.advise(instancesProvide=[IRectagleFactory],
                     asAdapterForTypes=[wx.DC])
    @staticmethod
    def get_rect(x,y,w,h):
        return wx.Rect(x,y,w,h)

class ServiceProviderGUIMetaIconUser(object):
    icon_cache = {}
    def get_icon(self, meta, size):
        meta = IServiceProviderGUIMetaData(meta)
        try:
            ret = self.icon_cache[(meta.provider_id, size)]
        except KeyError:
            ret = self.icon_cache[(meta.provider_id, size)] = meta.icon.PIL.Resized(size).WXB
        return ret

class ServiceComponentGUIMetaIconUser(object):
    icon_cache = {}
    def get_icon(self, meta, size):
        meta = IServiceComponentGUIMetaData(meta)
        try:
            ret = self.icon_cache[(meta.component_id, size)]
        except KeyError:
            ret = self.icon_cache[(meta.component_id, size)] = meta.icon.PIL.Resized(size).WXB
        return ret

class ServiceMetaProviderPanel(wxPaintingMixin, wx.Panel, ServiceProviderGUIMetaIconUser):
    protocols.advise(instancesProvide=[IPaintable, IDrawable])
    def __init__(self, service_providers, height, spacing, *a, **k):
        self.service_providers = [s[0] for s in
                                  sorted(((sp,IServiceProviderGUIMetaData(sp))
                                          for sp in service_providers),
                                         key = (lambda o: o[1].popularity),
                                         reverse = True)]
        self.height = height
        self.spacing = spacing
        super(ServiceMetaProviderPanel, self).__init__(*a, **k)
        #wx object operations must wait until after the wx constructor
        self.MinSize = (len(service_providers) - 1)*(height + spacing) + height, (height + spacing)
        self.w = None
        self.Bind(wx.EVT_MOTION, self.on_mouseover, self)
        self.Bind(wx.EVT_LEFT_UP, self.on_mouseclick, self)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mousein, self)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouseout, self)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_capture_lost, self)
        self.sx = self.sy = None

    def draw(self, obj):
        dc = IDrawingContext(obj)
        dc.Clear()
        size = self.height
        offset = self.height+self.spacing
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0,0,self.Size.width, self.Size.height)
        for i, s in enumerate(self.service_providers):
            dc.DrawBitmap(self.get_icon(s, size), i*offset, 0)
    on_paint = draw

    def service_provider_from_evt(self, e):
        if e.GetEventObject() is not self:
            return
        if not self.HasCapture():
            return
        lx = e.X
        r = self.ClientRect
        if not wx.Rect(r.y,r.x,r.width + 1, r.height + 1).Contains(e.Position):
            return
        offset = self.height+self.spacing
        pos = lx / float(offset)
        posi = int(pos)
        posr = pos - posi
        if posr * offset <= (offset - self.spacing):
            if posi < len(self.service_providers):
                return self.service_providers[posi]

    def on_mouseover(self, e):
        e.Skip()
        if e.GetEventObject() is not self:
            return
        if not self.HasCapture():
            return
        lx = e.X
        r = self.ClientRect
        if not wx.Rect(r.y,r.x,r.width + 1, r.height + 1).Contains(e.Position):
            return self.on_mouseout(e)
        offset = self.height+self.spacing
        pos = lx / float(offset)
        posi = int(pos)
        posr = pos - posi
        if posr * offset <= (offset - self.spacing):
            sx = posi * offset + self.height/2
            sy = self.height
            if posi >= len(self.service_providers):
                return self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            if self.w is None:
                self.w = ServiceProviderBubble(self.service_providers[0], 0, parent=self)
            if self.w.Shown and sx == self.sx and sy == self.sy:
                return
            self.sx = sx
            self.sy = sy
            with self.w.Frozen():
                self.w.service_provider = IServiceProviderGUIMetaData(self.service_providers[posi])
                self.w.show_point_to(self.ClientToScreen((sx,sy)))
        else:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def on_mouseclick(self, e):
        e.Skip()
        sp = self.service_provider_from_evt(e)
        if sp is None:
            return

        diag = hooks.first('digsby.services.create', parent = self.Top, sp_info = sp, impl="digsby_service_editor")
        diag.CenterOnParent()
        return_code = diag.ShowModal()

        if return_code != wx.ID_SAVE:
            log.info("Account creation cancelled. Return code = %r", return_code)
            return

        info = diag.extract()
        sp = hooks.first('digsby.service_provider',
                         impl = diag.sp_info.provider_id,
                         **info)

        log.info("Created %r", sp)
        components = []
        types_ = sp.get_component_types()
        if 'im' in types_:
            sp.autologin = True
        for type_ in types_:
            comp = sp.get_component(type_)
            components.append((comp, type_[:2]))
            log.info("\thas component %r: %r", type_, comp)
        import services.service_provider as sp
        with sp.ServiceProviderContainer(profile()).rebuilding() as container:
            profile.account_manager.add_multi(components)
            for comp, type_ in components:
                try:
                    if hasattr(comp, 'enable'):
                        comp.enable()
                    else:
                        comp.enabled = True
                except Exception:
                    print_exc()
                try:
                    on_create = getattr(comp, 'onCreate', None) #CamelCase for GUI code
                    if on_create is not None:
                        on_create()
                except Exception:
                    print_exc()
                if type_ == 'em':
                    hooks.notify('digsby.email.new_account', parent = self.Top, protocol = comp.protocol, **info)
            container.rebuild()

    def on_mousein(self, e):
        if e.GetEventObject() is not self:
            return
        self.CaptureMouse()

    def on_mouseout(self, e):
        if self.w is not None:
            self.w.Hide()
        while self.HasCapture():
            self.ReleaseMouse()
        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def on_capture_lost(self, e):
        pass

class BubbleWindow(wx.Frame):
    def __init__(self, internal_size, parent = None, *a, **k):
        style = wx.FRAME_SHAPED | wx.BORDER_NONE | wx.FRAME_NO_TASKBAR | \
                ((parent and wx.FRAME_FLOAT_ON_PARENT) or wx.STAY_ON_TOP)
        ret = super(BubbleWindow, self).__init__(parent, style=style, *a, **k)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.internal_size = internal_size
        self.point = (10,0)
        return ret

    def draw_content(self, dc):
        pass

    @property
    def poly(self):
        xborder = 0
        yborder = 0
        startx, starty = (0,10)
        px,py = self.point
        endx, endy = (2*xborder + self.internal_size[0] + startx), (2*yborder + self.internal_size[1] + starty)
        return ((px,py),(px+1,py), (px+11,starty), (endx,starty),(endx,endy),(startx,endy),(startx,starty),(px,starty),(px,py))

    def show_point_to(self, point):
        x,y = point
        xborder = 0
        yborder = 0
        startx, starty = (0,10)
        px,py = self.point
        endx, endy = (2*xborder + self.internal_size[0] + startx), (2*yborder + self.internal_size[1] + starty)
        with self.Frozen():
            self.Position = (x - px, y - py)
            self.Size = (endx+1, endy+1)
            self.SetShape(get_polyregion(self.poly, endx, endy))
            self.ShowNoActivate(True)

    def on_paint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
#        gc = wx.GraphicsContext.Create(dc)
        o = wx.Color(254,214,76) # skin!
        y = wx.Color(255,251,184)
        dc.SetPen(wx.Pen(o))
        dc.SetBrush(wx.Brush(y))
        dc.DrawPolygon(self.poly)
        self.draw_content(dc)

class ServiceProviderBubble(BubbleWindow, ServiceComponentGUIMetaIconUser):
    def __init__(self, service_provider, font_adjust = 0, *a, **k):
        self.service_provider = IServiceProviderGUIMetaData(service_provider)
        super(ServiceProviderBubble, self).__init__((0,0), *a, **k)
        self.Font = default_font()
        self.font_adjust = font_adjust
        self._service_provider = None
        self.recalcsize()

    def recalcsize(self):
        if self.service_provider is self._service_provider:
            return
        ftitle = self.Font
        ftitle.PointSize = int((ftitle.PointSize + self.font_adjust) * 4/3.)
        fbase = self.Font
        fbase.PointSize += self.font_adjust
        h = 0
        h += ftitle.LineHeight + 2
        h += ftitle.Descent * 2
        lh = round(fbase.LineHeight / 4. + .25) * 4 + 2
        #^ .25 = .5 - 1/4. (ceil, except when exactly divisible by 4)
        h += lh*len(self.service_provider.service_components) - 2
        dc = wx.ClientDC(self)
        dc.Font = ftitle
        w = dc.GetTextExtent(self.service_provider.provider_name)[0]
        self.offset = dc.GetTextExtent(" ")[0]
        dc.Font = fbase
        w2 = max([dc.GetTextExtent(" " + IServiceComponentGUIMetaData(s).service_name)[0]
                  for s in self.service_provider.service_components] + [0])
        w2 += lh
        w2 += self.offset
        w = max(w, w2)
        w += ftitle.Descent * 4
        h += 2
        self.internal_size = (int(w), int(h))
        self._service_provider = self.service_provider

    def draw_content(self, dc):
        ftitle = self.Font
        ftitle.PointSize = int((ftitle.PointSize + self.font_adjust) * 4/3.)
        fbase = self.Font
        fbase.PointSize += self.font_adjust
        dc.Font = ftitle
        x,y = ftitle.Descent * 2, 10 + ftitle.Descent * 1
        dc.DrawText(self.service_provider.provider_name, x, y)
        y += ftitle.LineHeight + 2
        lh = int(round(fbase.LineHeight / 4. + .25)) * 4 + 2
        dc.Font = fbase
        x += self.offset
        for s in sorted((IServiceComponentGUIMetaData(sc)
                         for sc in self.service_provider.service_components),
                        key = attrgetter('type'),
                        cmp = component_sort):
            dc.DrawBitmap(self.get_icon(s, lh -2), x, y)
            dc.DrawText(" " + s.service_name, x+lh, y)
            y += lh

    def show_point_to(self, point):
        self.recalcsize()
        return super(ServiceProviderBubble, self).show_point_to(point)

@memoize
def get_polyregion(points, w, h, border=1):
    i = wx.EmptyImage(w + border, h + border)
    b = i.WXB
    m = wx.MemoryDC(b)
    m.Clear()
    m.SetBrush(wx.Brush(wx.Color(0,0,0)))
    m.SetPen(wx.Pen(wx.Color(0,0,0)))
    #ceil(border/2)?
    m.DrawRectangle(0,0,w + border, h + border)
    m.SetBrush(wx.Brush(wx.Color(255,255,255)))
    m.SetPen(wx.Pen(wx.Color(255,255,255)))
    m.DrawPolygon(points)
    m.SelectObject(wx.NullBitmap)
    del m
    b.SetMaskColour(wx.Color(0,0,0))
    return wx.RegionFromBitmap(b)

class IServiceProviderInstance(protocols.Interface):
    icon = property()

def grayify(i, grayshade):
    return int(round((i + grayshade) / 2.))
def grayify3(tuple_, grayshade):
    return tuple(grayify(i, grayshade) for i in tuple_)

class CheckModel(trellis.Component):
    value = trellis.attr(False)
    enabled = trellis.attr(True)

class ListenerSync(trellis.Component):
    listener = trellis.attr()
    model = trellis.attr()

class ModelListenerSync(ListenerSync):
    @trellis.maintain
    def value(self):
        self.model.value = self.listener.value

class ListenerModelSync(ListenerSync):
    @trellis.maintain
    def keep_value(self):
        self.listener.value = self.model.value

class ViewListenerModelSync(ListenerModelSync):
    view = trellis.attr()

class CheckModelSync(ViewListenerModelSync):
    @trellis.perform
    def update(self):
        try:
#            print 'syncing', self.model.enabled, self.model.value
            with self.view.Frozen():
                self.view.Enabled = self.model.enabled
                self.view.Value = self.model.value
        except Exception:
            if not wx.IsDestroyed(self.view):
                raise

class CheckSync(object):
    def __init__(self, model, view):
        #order matters, make the view sync to the model before we allow
        #the other direction
        listener = IValueListener(view)
        self.model_to_view = CheckModelSync(model = model, view = view, listener = listener)
        self.view_to_model = ModelListenerSync(model = model, listener = listener)

class AccountModelSync(ViewListenerModelSync):
    #syncs the model.value to the account
    @trellis.perform
    def update(self):
        has_enabled = hasattr(self.view, 'enabled')
        if has_enabled and self.view.enabled != self.model.value:
            val = self.model.value
            #assume accounts with enable()/disable() know what to do
            #as far as saving that data.
            if val and hasattr(self.view, 'enable'):
                self.view.enable()
            elif (not val) and hasattr(self.view, 'disable'):
                self.view.disable()
            else:
                self.view.setnotify('enabled', val)
                #email/social get saved to the server;
                #update_info without any data works to just save them.
                wx.CallAfter(self.view.update_info)

class AccountEnabledSync(object):
    def __init__(self, model, view):
        #order matters, model syncs to the account first
        listener = IValueListener(ObservableAttrBindable(view, 'enabled'))
        self.acct_to_model = ModelListenerSync(model = model, listener = listener)
        self.model_to_acct = AccountModelSync (model = model, view = view, listener = listener)

class EnabledAccountSync(object):
    def __init__(self, model, view):
        #order matters, acct syncs to the model first
        listener = IValueListener(ObservableAttrBindable(view, 'enabled'))
        self.model_to_acct = AccountModelSync (model = model, view = view, listener = listener)
        self.acct_to_model = ModelListenerSync(model = model, listener = listener)

class AccountEnabledCheckSync(object):
    def __init__(self, account, check):
        #double MVC
        model = CheckModel()
        self.acct_model = AccountEnabledSync(model = model, view = account)
        self.view_model = CheckSync(         model = model, view = check)

class NoAccountEnabledCheckSync(trellis.Component):
    created_account = trellis.attr(False)
    def __init__(self, provider, component, check):
        super(NoAccountEnabledCheckSync, self).__init__()
        self.model = CheckModel()
        self.provider = provider
        self.component = component
        self.view_model = CheckSync(model = self.model, view = check)

    @trellis.maintain
    def update(self):
        if not self.model.value:
            return

        if self.created_account:
            return
        self.created_account = True

        # create account object, put it in the account manager
        acct = self.provider.get_component(self.component.type)
        profile.account_manager.add(acct, self.component.type[:2], ignore_on_rebuild=True)

        self.acct_to_model = EnabledAccountSync(model = self.model, view = acct)

class ServiceProviderRow(AccountRow, ServiceProviderGUIMetaIconUser):
    row_height = 50
    def __init__(self, parent, data, *a, **k):
        self.data = data
        self._base_color_tuple = (128,128,128)
        self._name_color_tuple = (0,0,0)
        ret = super(ServiceProviderRow, self).__init__(parent=parent, data=data, *a, **k)
#        self.SetToolTipString(IServiceProviderGUIMetaData(data).provider_name +\
#                              ': ' + IServiceProviderInstanceGUIMetaData(data).account_name)
        self.Font = default_font()
        return ret

    @property
    def image(self):
        try:
            ret = self.get_icon(self.data, 40)
        except AttributeError:
            ret = super(ServiceProviderRow, self).image
        return ret

    def draw_text(self, dc, x, sz):
        pass

    def _paint(self, e):
        dc = super(ServiceProviderRow, self)._paint(e)
        f = self.Font
        f.PointSize += 3
        dc.Font = f
        name = IServiceProviderInstanceGUIMetaData(self.data).account_name
        x,y = self._place_text.Position
        y += f.Descent

        for (color, string) in (hooks.first('digsby.services.colorize_name', impls = (self.data.provider_id, 'digsby_service_editor'), name = name) or ()):
            color_obj = getattr(self, '_active_%s_color' % color, None)
            dc.SetTextForeground(wx.Color(*color_obj))
            dc.DrawText(string, x, y)
            x += dc.GetTextExtent(string)[0]

    def ConstructMore(self):
        self.checks = []
        self.hiddens = []
        import gui.lattice
        for s in sorted((IServiceComponentGUIMetaData(sc)
                         for sc in IServiceProviderGUIMetaData(self.data).service_components),
                        key = attrgetter('type'),
                        cmp = component_sort):
            c = wx.CheckBox(self, -1, s.service_name)
            for a in self.data.accounts.values():
                if a.protocol == s.component_id:
                    c.controller = AccountEnabledCheckSync(account = a,
                                                           check = c)
                    break
            else:
                c.controller = NoAccountEnabledCheckSync(provider = self.data, component = s, check = c)
            if s.type == 'im':
                text = wx.StaticText(self, label = _('(auto login)'))
                f = c.Font
                text.Font = f
                text.ForegroundColour = wx.Color(*self._base_color_tuple)
                text.Hide()
                self.hiddens.append(text)
                c = (c, text)
            self.checks.append(c)

        # Extra component--the edit hyperlink
        edit = self.edit = wx.HyperlinkCtrl(self, -1, _('Edit'), '#')
        edit.Hide()
        edit.Bind(wx.EVT_HYPERLINK, lambda e: self.on_edit())

        remove = self.remove = wx.HyperlinkCtrl(self, -1, _('Remove'), '#')
        remove.Hide()
        remove.Bind(wx.EVT_HYPERLINK, lambda e: self.on_delete())

        self.hiddens.append(edit)
        self.hiddens.append(remove)

        edit.HoverColour = edit.VisitedColour = edit.ForegroundColour
        remove.HoverColour = remove.VisitedColour = remove.ForegroundColour
        self._reset_text_name()

    def on_edit(self):
        super(ServiceProviderRow, self).on_edit()
        self.on_data_changed(self)

    def on_delete(self):
        super(ServiceProviderRow, self).on_delete()
        #super.on_data_changed to skip the GUI refresh
        super(ServiceProviderRow, self).on_data_changed(self)

    def _reset_text_name(self):
        dc = wx.ClientDC(self)
        f = self.Font
        f.PointSize += 3
        dc.Font = f
        txt = IServiceProviderInstanceGUIMetaData(self.data).account_name
        w,h = dc.GetTextExtent(txt)
        self.text_name = w, h

    def CalcColors(self, *a, **k):
        if self.IsHovered():
            self._active_base_color = self._base_color_tuple
            self._active_name_color = self._name_color_tuple
        else:
            self._active_base_color = grayify3(self._base_color_tuple, 128)
            self._active_name_color = grayify3(self._name_color_tuple, 128)
        return super(ServiceProviderRow, self).CalcColors(*a, **k)

    def LayoutMore(self, sizer):
        #checkboxes
        check_sizer = VSizer()
        check_sizer.AddStretchSpacer(3)
        for check in self.checks:
            if isinstance(check, tuple):
                check, text = check
                h = HSizer()
                h.Add(check)
                h.Add(text)
                check_sizer.Add(h)
            else:
                check_sizer.Add(check)
            check_sizer.AddStretchSpacer()
        check_sizer.AddStretchSpacer(2)
        #add checkboxes
        sizer.Add(check_sizer, 1, wx.LEFT | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, self.padding.x*2)
        #right side
        right_sizer = VSizer()
        self._place_text = right_sizer.Add(self.text_name, 3, wx.ALIGN_RIGHT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, self.padding.y)
        #right bottom
        link_sizer = HSizer()
        link_sizer.Add(self.edit, 0, wx.LEFT, self.padding.x)
        link_sizer.Add(self.remove, 0, wx.LEFT, self.padding.x)
        right_sizer.AddStretchSpacer()
        #add right bottom to right
        right_sizer.Add(link_sizer, 3, wx.ALIGN_RIGHT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, self.padding.y)
        #add right side
        sizer.Add(right_sizer, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, 0)

    def on_data_changed(self, src=None, *a):
        super(ServiceProviderRow, self).on_data_changed(src, *a)
        self._reset_text_name()
        self.layout()
        self.Layout()
        self.Refresh()

#low to high priority order, (-1 = not found = lowest)
sorted_component_types = ['social', 'email', 'im']
def component_sort(a, b):
    return find(sorted_component_types, b) - find(sorted_component_types, a)

class ServiceProviderGUIMetaDataAdapter(protocols.Adapter):
    protocols.advise(asAdapterForTypes = [sp.ServiceProvider],
                     instancesProvide  = [IServiceProviderInstanceGUIMetaData])
    @property
    def account_name(self):
        name = None
        try:
            name = getattr(self.subject, 'display_name', None)
        except Exception:
            print_exc()
            if name is None:
                name = self.subject.name
        return name
#    @property
#    def service_components(self):
#        return [ServiceComponentGUIMetaData(s.component_type, s.shortname) for s in
#                sp.get_meta_components_for_provider(self.subject.provider_id)]

class ProviderList(AccountList):
    def __init__(self, *a, **k):
        super(ProviderList, self).__init__(*a, **k)
        self.Bind(wx.EVT_LIST_ITEM_FOCUSED,self.OnHoveredChanged)

    def OnHoveredChanged(self,e):
        row = self.GetRow(e.Int)
        if row:
            with row.Frozen():
                hiddens = getattr(row, 'hiddens', [])
                if row.IsHovered():
                    for obj in hiddens:
                        obj.Show()
                    row.Layout()
                    row.Refresh()
                else:
                    for obj in hiddens:
                        obj.Hide()
                    row.Layout()
                    row.Refresh()

    def on_edit(self, rowdata):
        diag = hooks.first('digsby.services.edit', parent = self.Top, sp = rowdata, impl="digsby_service_editor")
        return_code = diag.ShowModal()
        if return_code != wx.ID_SAVE:
            return

        info = diag.RetrieveData()

        log.info("Modifying %r", rowdata)
        rowdata.update_info(info)
        rowdata.update_components(info)

    def OnDelete(self, data):

        # Display a confirmation dialog.
        msgbox = hooks.first("digsby.services.delete.build_dialog", impls = (data.provider_id, 'default'), parent = self.Top, SP = data)

        try:
            if msgbox.ShowModal() == wx.ID_YES:
                for type_ in data.get_component_types():
                    comp = data.get_component(type_, create = False)
                    if comp is None:
                        continue
                    profile.account_manager.remove(comp)
        finally:
            msgbox.Destroy()

    def get_wheel_lines(self, rotation, e):
        val = rotation / float(e.GetWheelDelta()) * e.LinesPerAction
        return val / 2.5 # 2.5-line panels

    def rotation_for_lines(self, lines, e):
        return float(e.GetWheelDelta()) / e.LinesPerAction * lines * 2.5

def panel(panel, sizer, addgroup, exithooks):

    service_providers = ServiceMetaProviderPanel(sp.get_meta_service_providers(),
                                             40, 3, panel)

    two = PrefPanel(panel, service_providers, _('Add Accounts'))

    import services

    container = services.service_provider.ServiceProviderContainer(profile())
    provider_accts = observe.ObservableList(container.get_ordered() or [])

    def on_change(*a, **k):
        if not provider_accts.isflagged('being_set'):
            order = []
            for provider in provider_accts:
                for type_ in ('im', 'email', 'social'): #keep order! - no frozenset!
                    if type_ in provider.accounts:
                        order.append(provider.accounts[type_].id)
            container.set_order(order)

    def order_set(*a, **k):
        @wx.CallAfter
        def do_set():
            new = container.get_ordered()
            if new[:] != provider_accts[:]:
                with provider_accts.flagged('being_set'):
                    provider_accts[:] = new

    container.on_order_changed += order_set

    def unregister(*a, **k):
        if order_set in container.on_order_changed:
            container.on_order_changed -= order_set

    exithooks += unregister

    #hook this into on_data_changed

    accts = ProviderList(panel, provider_accts,
                            row_control = lambda *a, **k: ServiceProviderRow(use_checkbox = False, *a, **k),
                            edit_buttons = None)
    provider_accts.add_observer(on_change, obj = accts)

    three     = PrefPanel(panel, accts, _('My Accounts'))
    sizer.Add(two, 0, EXPAND)
    sizer.Add(three, 1, EXPAND | wx.TOP, 3)
    four = PrefPanel(panel,
        choices_sizer(panel, exithooks), _('Account Options'))
    sizer.Add(four, 0, EXPAND | wx.TOP, 3)
    return panel

def set_loc_values(model, prefname):
    val = pref(prefname)
    try:
        model.selection = [v[0] for v in model.values].index(val)
    except ValueError:
        pass

class PrefChoiceWatcher(trellis.Component):
    def __init__(self, model, prefname):
        trellis.Component.__init__(self)
        self.model = model
        self.prefname = prefname

    @trellis.perform
    def output_pref(self):
        mark_pref(self.prefname, self.model.values[self.model.selection][0])

class AccountLocationModels(AddOn):
    did_setup = False
    def __init__(self, subject):
        self.profile = subject
        super(AccountLocationModels, self).__init__(subject)

    def setup(self):
        if self.did_setup:
            return
        self.did_setup = True
        account_options = [('panel',   _('buddy list')),
                           ('systray', _('icon tray')),
                           ('both',    _('buddy list and icon tray'))]
        email_pref  = 'buddylist.show_email_as'
        social_pref = 'buddylist.show_social_as'
        self.email  = email  = ChoiceModel(values = account_options[:])
        self.social = social = ChoiceModel(values = account_options[:])
        set_loc_values(email, email_pref)
        set_loc_values(social, social_pref)
        self.profile.prefs.add_observer(self.on_email_changed, email_pref)
        self.profile.prefs.add_observer(self.on_social_changed, social_pref)
        self.email_watcher  = PrefChoiceWatcher(self.email,  email_pref)
        self.social_watcher = PrefChoiceWatcher(self.social, social_pref)

    @property
    def location_models(self):
        return [self.email, self.social]

    def on_email_changed(self, src, attr, old, new):
        import wx
        wx.CallAfter(set_loc_values, self.email, 'buddylist.show_email_as')
    def on_social_changed(self, src, attr, old, new):
        import wx
        wx.CallAfter(set_loc_values, self.social, 'buddylist.show_social_as')

def choices_sizer(panel, exithooks):
    p = wx.Panel(panel)
    sz = p.Sizer = VSizer()

    model_addon = AccountLocationModels(common.profile())
    model_addon.setup()

    location_models = model_addon.location_models

    import gui.lattice #@UnusedImport: side effect registering interfaces
    choices = list(yield_choices(location_models, p))
    exithooks.append(lambda:release_syncs(choices))

    labels = [_('Show email accounts in:'),
              _('Show social networks in:'),]

    to_add = [[(SText(p, label), 0, wx.ALIGN_CENTER_VERTICAL),
                   (choice, 1, 0)]
                  for label,choice in zip(labels, choices)]

    s = wx.FlexGridSizer(len(location_models), 2, 7,7)
    s.AddMany(sum(to_add,[]))
    s.AddGrowableCol(1,1)
    sz.Add(s, 0, EXPAND)

    return p
