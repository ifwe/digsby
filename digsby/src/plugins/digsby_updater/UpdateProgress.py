'''
A progress monitor for the app's updater. Works via the file transfer window.

Displays number of files completed out of number of files to be processed (checked or downloaded) instead of byte
count. Due to differing file sizes, the 'time remaining' feature may not be entirely correct, especially when
downloading.

Also supported is 'fast mode', which (under normal circumstances, i.e. app run-time) removes any timing-based limiters
on the integrity check and download mechanisms.
'''
import sys
import logging

import peak.util.addons as addons

import gui

import hooks
import util
import common
import common.filetransfer as FT

log = logging.getLogger("d_updater.progress")

class UpdateStates(FT.FileTransferStates):
    CHECKING_FILES = "Checking files"
    FAILED = "Update failed"

    TransferringStates = FT.FileTransferStates.TransferringStates | set((
                          CHECKING_FILES,
                         ))

    ErrorStates = FT.FileTransferStates.ErrorStates | set((
                   FAILED,
                  ))

    FailStates  = ErrorStates | set((
                   FT.FileTransferStates.CANCELLED_BY_YOU,
                  ))

class UpdateProgress(addons.AddOn, FT.FileTransfer):
    ATROPHY_TIME = sys.maxint

    direction = 'incoming'
    states = UpdateStates

    autoshow = False
    autoremove = True
    autoremove_states = set((UpdateStates.CANCELLED_BY_YOU,
                             UpdateStates.FINISHED))

    use_serviceicon = False

    @property
    def icon(self):
        return gui.skin.get('serviceicons.digsby')

    def setup(self):
        FT.FileTransfer.__init__(self)
        self.name = _("Digsby Update")
        self.buddy = util.Storage(name = "Digsby Servers",
                                  alias = "Digsby Servers",
                                  icon = None)

        self.xfer_display_strings[self.states.CHECKING_FILES] = \
        self.xfer_display_strings[self.states.TRANSFERRING] = \
            lambda x, d=None: _('%s: %s of %s -- %s remain') % (x.state, x.completed, x.size, util.nicetimecount(x.ETA))

        log.info("UpdateProgress setup")

    def on_file_check_start(self, updater):
        try:
            self.buddy.icon = self.icon
        except gui.skin.SkinException:
            pass

        log.debug("File check starting")
        self.updater = updater
        self.completed = 0
        self.size = len(updater.unchecked_files)
        self.state = self.states.CHECKING_FILES

    def on_file_checked(self, file):
        self._setcompleted(self.completed + 1)

    def on_file_check_complete(self, updater):
        log.debug("File check complete")
        self.updater = updater
        self.state = self.states.WAITING_FOR_YOU

    def on_file_download_complete(self, file):
        log.debug("File download completed: %r", file.path)
        self._setcompleted(self.completed + 1)

    def on_update_download_start(self, files_to_download):
        log.debug("Update download start: %r", files_to_download)
        self.size = len(self.updater.update_files)
        self.updater = None
        self.state = self.states.TRANSFERRING
        self.bytecounts = []
        self._bytes_per_sec = 0
        self.completed = 0
        self._starttime = None
        self._done = False

    def on_update_download_complete(self, downloaded_files):
        log.debug("All files downloaded")
        self.state = self.states.FINISHED

    def on_update_failed(self):
        log.debug("Update failed")
        self.autoremove = False
        self.state = self.states.FAILED

        util.Timer(10, lambda: (setattr(self, 'autoremove', True), setattr(self, 'state', self.states.FINISHED))).start()

    def cancel(self):
        hooks.notify("digsby.updater.cancel")

    def allow_cancel(self):
        return self.state not in (self.states.FailStates | self.states.CompleteStates)

    def allow_remove(self):
        return self.state in (self.states.FailStates | self.states.CompleteStates)

    def allow_open(self):
        return False

    def allow_open_folder(self):
        return False

    def allow_save(self):
        return False
    def allow_save_as(self):
        return False
    def allow_reject(self):
        return False

    def on_cancel(self):
        self.state = self.states.CANCELLED_BY_YOU

    def get_bottom_links(self):
        return []

    def get_right_links(self):
        return [
                ('remove', _('Remove'),  lambda *a: None, self.allow_remove),
                ('slower', _('Slower'),  self.slower, self.allow_slower),
                ('faster', _('Faster!'), self.faster, self.allow_faster),
                ('cancel', _('Cancel'),  self.cancel, self.allow_cancel),
                ]

    def faster(self):
        hooks.notify("digsby.updater.fast_mode.enable")

    def slower(self):
        hooks.notify("digsby.updater.fast_mode.disable")

    def allow_slower(self):
        return (self.allow_cancel() and
                self.updater is not None and
                self.updater.fast_mode)

    def allow_faster(self):
        return (self.allow_cancel() and
                self.updater is not None and
                not self.updater.fast_mode)

def up():
    if not common.pref("digsby.updater.use_transfer_window", type = bool, default = False):
        return

    p = common.profile()
    up = UpdateProgress(p)

    return up

def _insert_up(up):
    if up.updater is not None or up.state in up.states.TransferringStates:
        p = common.profile()
        if up not in p.xfers:
            log.info("putting UpdateProgress in profile.xfers")
            p.xfers.insert(0, up)

def _set_update_hook_handler(name):
    def handler(*a, **k):
        u = up()
        if u is None:
            return
        getattr(u, name)(*a, **k)
        if u.state not in (UpdateStates.CANCELLED_BY_YOU, UpdateStates.FAILED):
            _insert_up(u)

    setattr(sys.modules[__name__], name, handler)

for name in ('on_file_check_start',
             'on_file_checked',
             'on_file_check_complete',
             'on_file_download_complete',
             'on_update_download_start',
             'on_update_download_complete',
             'on_cancel_update',
             'on_update_failed',
            ):

    _set_update_hook_handler(name)
