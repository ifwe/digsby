from util import traceguard
from gui.toolbox import GetTextFromUser
from common import profile, pref
import wx

def change_password(protocol, cb):
    val = GetTextFromUser(_('Enter a new password for {username}:'.format(username=protocol.username)),
                          _('Change Password'),
                          default_value = protocol.password,
                          password = True)
    if val: cb(val)

def remove_contact(contact, do_remove):

    action_allowed = getattr(do_remove, 'action_allowed', lambda c: True)
    if not action_allowed(contact):
        return

    yes_default = pref('prompts.defaults.contacts.del_contact', type=bool, default=True)
    more_flags = wx.NO_DEFAULT * (not yes_default)

    if wx.YES == wx.MessageBox(_('Are you sure you want to delete contact {name}?').format(name=contact.name),
                               _('Delete Contact'), style = wx.YES_NO | more_flags):
        do_remove()

def remove_group(group, do_remove):

    try:
        s = u'group "%s"' % group.name
    except:
        s = u'this group'

    yes_default = pref('prompts.defaults.contacts.del_group', type=bool, default=True)
    more_flags = wx.NO_DEFAULT * (not yes_default)
    
    line1 = _('WARNING!')
    line2 = _('All your contacts in this group will be deleted locally AND on the server.')
    line3 = _('Are you sure you want to remove {groupname}?').format(groupname=s)
    
    msg = u'\n\n'.join((line1, line2, line3))

    if wx.YES == wx.MessageBox(msg, _('Delete Group'),
                               style = wx.YES_NO | wx.ICON_ERROR | more_flags):
        do_remove()

def add_group():
    group = GetTextFromUser(_('Please enter a group name:'),_('Add Group'))
    if group is None or not group.strip():
        return

    protos = [acct.connection for acct in profile.account_manager.connected_accounts]
    for proto in protos:
        with traceguard:
            proto.add_group(group)

def block_buddy(buddy, do_block):
    yes_default = pref('prompts.defaults.contacts.block', type=bool, default=True)
    more_flags = wx.NO_DEFAULT * (not yes_default)

    if wx.YES == wx.MessageBox(_('Are you sure you want to block %s?') % buddy.name,
                               _('Block Buddy'),
                               style = wx.YES_NO | more_flags):
        do_block()

