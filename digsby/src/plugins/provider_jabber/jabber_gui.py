import hooks

import wx
import gui.controls as controls
import gui.toolbox as toolbox

import digsby_service_editor.default_ui as default_ui

'''
      - elements:
          - Use TLS if Possible
          - Require TLS
          - Force SSL
          - No Encryption
        type: enum
        store: encryption
      - store: ignore_ssl_warnings
        label: Ignore SSL Warnings
        type: bool
      - type: bool
        store: allow_plaintext
        label: Allow Plaintext Login

'''
def construct_advanced_subpanel_im(panel, SP, MSP, MSC):
    MSC.info.pop('more_details', None)

    hooks.first("digsby.services.edit.advanced.construct_sub.im", impl="digsby_service_editor",
                panel = panel, SP = SP, MSP = MSP, MSC = MSC)


    encryption = dict(radio = controls.RadioPanel(panel,
                                                 [_('Use TLS if Possible'),
                                                  _('Require TLS'),
                                                  _('Force SSL'),
                                                  _('No Encryption')]))

    encryption['radio'].SetValue(getattr(SP, 'encryption', MSC.info.defaults.encryption))

    sz = panel.controls['advanced_sz']

    hsz = wx.BoxSizer(wx.HORIZONTAL)

    l_sz = wx.BoxSizer(wx.VERTICAL)
    default_ui.ezadd(l_sz, encryption['radio'], flag = wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL)
    hsz.Add(l_sz, flag = wx.EXPAND | wx.LEFT, border = 10)

    r_sz = wx.BoxSizer(wx.VERTICAL)

    ignore_ssl_warnings = dict(check = wx.CheckBox(panel, -1, _("Ignore SSL Warnings")))
    ignore_ssl_warnings['check'].Value = getattr(SP, 'ignore_ssl_warnings', MSC.info.defaults.ignore_ssl_warnings)
    default_ui.ezadd(r_sz, ignore_ssl_warnings['check'], flag = wx.EXPAND | wx.ALL)

    allow_plaintext = dict(check = wx.CheckBox(panel, -1, _("Allow Plaintext Login")))
    allow_plaintext['check'].Value = getattr(SP, 'allow_plaintext', MSC.info.defaults.allow_plaintext)
    default_ui.ezadd(r_sz, allow_plaintext['check'], flag = wx.EXPAND | wx.ALL)

    hsz.Add(r_sz, flag = wx.EXPAND | wx.RIGHT, border = 0)

    default_ui.ezadd(sz, hsz, (sz.row, 0), (4, 4), flag = wx.EXPAND | wx.ALL)
    sz.row += 4

    panel.controls.update(
       encryption = encryption,
       ignore_ssl_warnings = ignore_ssl_warnings,
       allow_plaintext = allow_plaintext,
    )

    return True

def extract_advanced_subpanel_im(panel, info, SP, MSP, MSC):
    hooks.first("digsby.services.edit.advanced.extract_sub.im", impl="digsby_service_editor",
                panel = panel, info = info, SP = SP, MSP = MSP, MSC = MSC)

    info['encryption'] = panel.controls['encryption']['radio'].GetValue()
    info['ignore_ssl_warnings'] = panel.controls['ignore_ssl_warnings']['check'].Value
    info['allow_plaintext'] = panel.controls['allow_plaintext']['check'].Value

    return True

def delete_account_dialog(parent = None, SP = None):
    import jabber
    from gui.protocols.jabbergui import JabberDeleteConfirmBox

    message = _('Are you sure you want to delete account "{name}"?').format(name=SP.name)
    caption = _('Delete Account')

    msgbox = JabberDeleteConfirmBox(SP.get_component('im'), message, parent, title=caption)

    return msgbox

