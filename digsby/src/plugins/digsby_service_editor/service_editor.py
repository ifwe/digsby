import services.service_provider as SP
import wx
import wx.lib.sized_controls as sc
import gui.skin as skin
import gui.toolbox as toolbox
import gui.chevron as chevron

import hooks
import config
import util
import util.callbacks as callbacks
import common

import logging
log = logging.getLogger('digsby_service_editor')

class ServiceEditor(sc.SizedDialog):
    @classmethod
    def create(cls, parent = None, sp_info = None):
        return cls(parent = parent, sp_info = sp_info)

    @classmethod
    def edit(cls, parent = None, sp = None):
        return cls(parent = parent, sp = sp)

    def __init__(self, parent = None, sp = None, sp_info = None):
        self.new = sp is None

        if sp_info is None:
            if sp is None:
                raise Exception()

            sp_info = SP.get_meta_service_provider(sp.provider_id)

        self.sp = sp
        self.sp_info = sp_info

        self.component_names = list(x.component_type for x in SP.get_meta_components_for_provider(self.sp_info.provider_id)) + ['provider']
        self.component_names.sort(key = lambda x: ("provider", "im", "email", "social").index(x))

        title = self.hook("digsby.services.edit.title", self.sp, self.sp_info)

        wx.Dialog.__init__(self, parent, title = title)

        self.SetFrameIcon(skin.get("serviceprovidericons.%s" % self.sp_info.provider_id))

        self.construct()
        self.layout()
        self.bind_events()
        self.DoValidate()

        self.Fit()

    def hook(self, hookname, *hookargs, **hookkwargs):
        return hooks.first(hookname, impls = (self.sp_info.provider_id, 'digsby_service_editor'), *hookargs, **hookkwargs)

    def construct(self):
        for panel_type in ("basic", "advanced"):
            parent = self
            if panel_type == "advanced":
                self.chevron = chevron.ChevronPanel(self, _("Advanced"))
                parent = self.chevron.contents
            panel = self.hook("digsby.services.edit.%s.construct_panel" % panel_type,
                              parent = parent,
                              SP = self.sp,
                              MSP = self.sp_info)

            if panel is False:
                panel = None
            setattr(self, "%s_panel" % panel_type, panel)
            if panel is None:
                continue

            panel.Label = "%s_panel" % panel_type

            for partname in self.component_names:
                self.hook("digsby.services.edit.%s.construct_sub.%s" % (panel_type, partname),
                          panel = panel,
                          SP = self.sp,
                          MSP = self.sp_info,
                          MSC = SP.get_meta_component_for_provider(self.sp_info.provider_id, partname))

        assert hasattr(self, 'basic_panel')
        assert hasattr(self, 'advanced_panel')

        if not self.advanced_panel:
            self.chevron.Destroy()
            self.chevron = None

        self.save_btn = wx.Button(self, wx.ID_SAVE, _("&Save"))
        self.save_btn.SetDefault()

        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))

    def layout(self):
        if self.basic_panel is not None:
            self.Sizer = wx.BoxSizer(wx.VERTICAL)
            self.Sizer.Add(self.basic_panel)

        if self.advanced_panel:
            self.Sizer.Add(self.chevron, 1, wx.EXPAND | wx.LEFT, 3)
            self.chevron.contents.Sizer.Add(self.advanced_panel, 1, wx.EXPAND)

        self.Sizer.Add(toolbox.build_button_sizer(self.save_btn, self.cancel_btn, border = self.save_btn.GetDefaultBorder()), 0, wx.EXPAND | wx.ALL, self.GetDefaultBorder())

        self.hook('digsby.services.edit.layout.polish', self.basic_panel, getattr(self, 'advanced_panel', None))

    def bind_events(self):

        self.Bind(wx.EVT_TEXT, self.DoValidate)
        self.Bind(wx.EVT_CHOICE, self.DoValidate)
        self.Bind(wx.EVT_CHECKBOX, self.DoValidate)
        self.Bind(wx.EVT_RADIOBUTTON, self.DoValidate)
        # TODO: bind all event types that might get fired.
        self.save_btn.Bind(wx.EVT_BUTTON, self.OnSave)

    def OnSave(self, evt):
        success = lambda: self.EndModal(wx.ID_SAVE)
        error = lambda: self.EndModal(wx.ID_CANCEL)

        self.hook("digsby.services.edit.save", success = success, error = error, info = self.extract(), SP = self.sp, MSP = self.sp_info)

    def on_success_register(self):
        self.EndModal(wx.ID_SAVE)

    def on_fail_register(self, error):
        textcode, text, kind, codenum = error
        wx.MessageBox("Error %(codenum)d: %(text)s" % locals(), textcode)
        self.EndModal(wx.ID_CANCEL)

    def extract(self):
        info = {'provider_id' : self.sp_info.provider_id}
        for panel_type in ('basic', 'advanced'):
            panel = getattr(self, '%s_panel' % panel_type, None)
            if panel is None:
                continue

            self.hook('digsby.services.edit.%s.extract_panel' % panel_type,
                      panel = panel,
                      info = info,
                      SP = self.sp,
                      MSP = self.sp_info)

            for component in self.component_names:

                self.hook('digsby.services.edit.%s.extract_sub.%s' % (panel_type, component),
                          panel = panel,
                          info = info,
                          SP = self.sp,
                          MSP = self.sp_info,
                          MSC = SP.get_meta_component_for_provider(self.sp_info.provider_id, component))

        return info

    def DoValidate(self, e = None):
        if e is not None:
            e.Skip()

        self.validate()

    def SetWarning(self, message = None):
        warnings = self.basic_panel.controls.get('warnings_lbl', None)

        if warnings is None:
            return

        if not message:
            message = ''

        if warnings.Label == message:
            return
        warnings.Label = message

        # FIXME: this throws the sizing on Mac all out of whack. Perhaps some native API gets
        # messed up when called on a hidden control?
        if not config.platformName == "mac":
            if not message:
                warnings.Show(False)
            else:
                warnings.Show(True)

        self.Layout()
        self.Fit()
        self.Refresh()

    def validate(self):
        info = self.extract()
        info = self.hook('digsby.services.normalize', info, self.sp_info, self.new)
        try:
            self.hook('digsby.services.validate', info, self.sp_info, self.new, raise_hook_exceptions = True)
        except SP.AccountException, e:
            fatal = e.fatal
            self.save_btn.Enabled = not fatal
            self.SetWarning(getattr(e, 'message', u''))
            return False
        else:
            self.save_btn.Enabled = True
            self.SetWarning(None)
            return True

    def RetrieveData(self):
        info = self.extract()
        info.pop("_real_password_", None)
        return info

def edit(parent = None, sp = None):
    return ServiceEditor.edit(parent = parent, sp = sp)

def create(parent = None, sp_info = None):
    return ServiceEditor.create(parent = parent, sp_info = sp_info)

def delete_dialog(parent = None, SP = None):

    message = _('Are you sure you want to delete account "{name}"?').format(name=SP.name)
    caption = _('Delete Account')
    style   = wx.ICON_QUESTION | wx.YES_NO

    msgbox = wx.MessageDialog(parent, message, caption, style)

    return msgbox

def validate(info, MSP, is_new):
    spc = SP.ServiceProviderContainer(common.profile())
    if is_new and spc.has_account(info):
        raise SP.AccountException(_("That account already exists."))

    try:
        sp = hooks.first('digsby.service_provider', impl = MSP.provider_id, raise_hook_exceptions = True, **info)
    except SP.AccountException, e:
        raise e
    except Exception, e:
        import traceback; traceback.print_exc()
        raise SP.AccountException(e.args[0] if e.args else "Unknown error", True)

    return True

def normalize(info, MSP, is_new):

    return info

def colorize_name(name):
    # The sum of the strings returned by this should be less
    # than or equal to the length of the input
    if '@' in name:
        split = name.split('@', 1)
        return (('name', split[0]),
                ('base', '@' + split[1]))
    else:
        return (('name', name),)

@callbacks.callsback
def on_save_account(SP, MSP, info, callback = None):
    if SP is not None:
        for ctype in SP.get_component_types():
            comp = SP.get_component(ctype, create = False)
            if comp is None:
                continue
            conn = getattr(comp, 'connection', None)
            if conn is None:
                continue
            for updatee in getattr(conn, 'needs_update', []):
                try:
                    attr, fname = updatee
                    f = getattr(conn, fname)
                except (TypeError,ValueError) as e:
                    attr = updatee
                    f = lambda v: setattr(conn, attr, v)

                f(info.get(attr))

    if info.get('register', False):
        log.info_s('adding account: %r', info)
        common.profile().register_account(
             on_success = callback.success,
             on_fail = callback.error,
             **info
        )
    else:
        callback.success()


