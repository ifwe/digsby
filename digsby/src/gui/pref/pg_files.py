import wx
import stdpaths
from gui.pref.prefcontrols import *

def default_save_dir():
    import os.path
    return os.path.join(stdpaths.documents, 'Digsby Downloads')


def panel(panel, sizer, newgroup, exithooks):
    newgroup((_('File Transfers'), 'filetransfer'),

        Browse('local.save_to',         _('Save &files to:'), 'dir'),
#        CheckBrowse('virus_scan',       _('&Virus Scan:'), 'file'),
        Check('create_subfolders',      _('Create s&ubfolders for each IM account')),
        Check('auto_accept_from_blist', _('&Auto-accept all file transfers from contacts on my contact list')),
#        Check('use_port',               _('Use &Port: %6(port)d'))

    )

#    newgroup((_('AIM File Sharing'), 'oscar.peer'),
#
#        CheckBrowse('share_files', _('Share &Folder:'), 'dir'),
#        Check('auto_accept.sharing', _('Auto-accept all file sharing &requests from contacts on my contact list')),
#        Check('use_port', _('Use Por&t: %6(port)d'))
#
#    )
#
#    newgroup((_('AIM Direct Connect'), ''),
#
#             Check('oscar.peer.auto_accept.direct_connect',
#                   _('Auto-accept all Direct Connect invitations from contacts on my contact list')),
#
#    )

    return panel
