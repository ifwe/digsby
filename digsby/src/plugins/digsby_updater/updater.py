import logging
log = logging.getLogger("d_updater")
#log.setLevel(logging.INFO)

import sys
import traceback
import io
import time

import wx
import gui
import hashlib
import path
import syck
import config
import stdpaths
import hooks
import peak.util.addons as addons
import lxml.objectify as objectify

import util
import util.net as net
import util.callbacks as callbacks
import common
import common.asynchttp as asynchttp
import file_integrity, downloader

if config.platform == 'win':
    import winhelpers as helpers
elif config.platform == 'mac':
    import machelpers as helpers

def rm_emptydirs(dir):
    for d in dir.dirs():
        rm_emptydirs(d)

    if not dir.files() or dir.dirs():
        try:
            dir.rmdir()
        except Exception:
            pass

class UpdateChecker(object):
    '''
    Determines if there is an update.

    Usage:
    uc = UpdateChecker('alpha')
    uc.update(success = lambda needs_update, remote_manifest_path, manifest_data: log.info("update check complete"),
              error = lambda exc: log.info("oh no, update check failed")
    '''
    def __init__(self, release_type = None):
        self.remote_manifest_path = None
        self.release_type = release_type or self.get_release_type()
        self.callback = None

    @callbacks.callsback
    def update(self, callback = None):
        self.callback = callback
        self.get_manifest_path()

    def manifest_path_error(self, e):
        log.info("Error getting manifest path: %r", e)
        self._error(e)

    def manifest_request_error(self, e):
        log.error("Error retrieving manifest file: %r", e)
        self._error(e)

    def manifest_check_error(self, e):
        log.error("Error checking manifest integrity: %r", e)
        self._error(e)

    def update_check_complete(self, needs_update, manifest_data):
        log.info("Update check complete. Need update? %r", needs_update)
        self._success(needs_update, self.remote_manifest_path, manifest_data)

    def _error(self, e):
        cb, self.callback = self.callback, None
        if cb is not None:
            cb.error(e)

    def _success(self, *a):
        cb, self.callback = self.callback, None
        if cb is not None:
            cb.success(*a)

    def check_manifest_integrity(self, req, resp):
        headers = resp.headers

        rmtime = headers.get('x-amz-meta-mtime', None)

        if rmtime is None:
            rmtime = headers.get('last-modified', None)
            if rmtime is not None:
                rmtime = net.http_date_to_timestamp(rmtime)

        if rmtime is not None:
            try:
                rmtime = int(rmtime)
            except (TypeError, ValueError):
                rmtime = None

        prog_dir = util.program_dir()
        self.local_manifest_path = path.path(prog_dir) / path.path(self.remote_manifest_path).splitpath()[-1]

        needs_update = True

        if self.local_manifest_path.isfile():
            lmtime = int(self.local_manifest_path.mtime)
        else:
            lmtime = 0

        if sys.opts.force_update or lmtime != rmtime:
            log.info("MTime mismatch or sys.opts.force_update is True. Downloading manifest. (local=%r, remote=%r)", lmtime, rmtime)
            downloader.httpopen(self.remote_manifest_path, success = self.got_manifest_response, error = self.manifest_request_error)
        else:
            log.info("Local MTime matches remote. Not downloading manifest. (local=%r, remote=%r)", lmtime, rmtime)
            self.update_check_complete(False, None)

    def got_manifest_response(self, req, resp):
        if self.local_manifest_path.isfile():
            local_manifest_digest = self.local_manifest_path.read_md5()
        else:
            local_manifest_digest = None

        log.info("Got manifest response. Comparing hashes.")

        manifest_data = resp.read()
        remote_manifest_digest = hashlib.md5(manifest_data).digest()

        needs_update = local_manifest_digest != remote_manifest_digest

        if sys.opts.force_update:
            needs_update = True

        if not needs_update:
            manifest_data = None

        self.update_check_complete(needs_update, manifest_data)

    def get_release_type(self):
        '''
        Returns a cached tag name (from sys.TAG) if present, otherwise loads it from tag.yaml in the program directory.
        '''
        return get_client_tag()

    def get_manifest_path(self):
        '''
        Figure out where the manfiest is supposed to be. Since this may make an HTTP request, control flow
        continues asynchronously into got_updateyaml(file_obj).
        '''
        program_dir = util.program_dir()

        local_info_file = program_dir / 'update.yaml'
        if local_info_file.isfile():
            try:
                local_info = open(local_info_file, 'rb')
            except Exception:
                pass
            else:
                self.got_updateyaml(fobj = local_info)
                return

        log.info("Manifest path not found in %r. checking web for update.yaml", local_info_file)
        asynchttp.httpopen("http://s3.amazonaws.com/update.digsby.com/update.yaml?%s" % int(time.time()), success = self.got_updateyaml, error = self.manifest_path_error)

    def got_updateyaml(self, req = None, fobj = None):
        '''
        an open fileobject that contains yaml with manifest locations in it.
        '''
        try:
            data = fobj.read()
        except Exception as e:
            return self.manifest_path_error(e)

        try:
            ui = syck.load(data)
        except Exception as e:
            return self.manifest_path_error(e)

        all = ui.get('all', {})
        mine = ui.get(config.platform, None) or {}

        merged = all.copy()
        merged.update(mine)

        manifest_path = merged.get(self.release_type, merged.get('release', None))
        if manifest_path is None:
            self.update_check_error(Exception("No manifest URL for %r in %r" % (self.release_type, all)))
        else:
            log.info("Got manifest path: %r", manifest_path)
            self.remote_manifest_path = manifest_path
            downloader.httpopen(self.remote_manifest_path, method = 'HEAD', success = self.check_manifest_integrity, error = self.manifest_check_error)

def help_menu_items(*a):
    '''
    Returns zero or one items representing menu options to be placed in the help menu.
    The text is to include the app tag if we're not in 'release'.
    '''
    if not common.pref("digsby.updater.help_menu", type = bool, default = True):
        return []

    if sys.TAG and sys.TAG != "release":
        txt = _("Check for %s updates") % sys.TAG
    else:
        txt = _("Check for Updates")

    return [(txt, update_check)]

def update_check(*a):
    p = common.profile()
    if p is not None:
        UpdateManager(p).update()

def update_check_later(*a):
    '''
    The app performs an initial update check 5 minutes after launching.
    (After that, it's every 6 hours - see UpdateManager.setup)
    '''
    util.Timer(common.pref('digsby.updater.initial_delay',
                           type = int, default = 5*60),
               update_check).start()

def on_update_complete(*a):
    '''
    Save the current application log to a 'digsby_update_download.log.csv' file in case there's an error while updating.
    Otherwise these problems are very hard to debug ;)
    '''
    # make sure all log statements are written to disk
    for handler in logging.root.handlers:
        handler.flush()

    # limit the logfile size sent in the diagnostic report
    src_file = path.path(sys.LOGFILE_NAME)
    dst_file = src_file.parent / 'digsby_update_download.log.csv'
    try:
        data = src_file.bytes()
    except Exception, e:
        f = io.BytesIO()
        traceback.print_exc(file = f)
        data = f.getvalue()
        del f

    with dst_file.open('wb') as f:
        f.write(data)

def update_cancel(*a):
    p = common.profile()
    if p is not None:
        UpdateManager(p).cancel()

def start_fastmode(*a):
    p = common.profile()
    if p is not None:
        UpdateManager(p).set_fastmode(True)

def stop_fastmode(*a):
    p = common.profile()
    if p is not None:
        UpdateManager(p).set_fastmode(False)

def load_tag_and_install_update(*a):
    get_client_tag()
    return install_update()

def was_updated():
    '''
    Show the release notes (if any) after an update.
    (the updater starts the app with --updated after it completes)
    '''
    if not sys.opts.updated:
        return

    p = common.profile()
  # TODO: create some sort of dummy buddy object, this is silly
    buddy = util.Storage(name = "digsby.org",
             service = "digsby",
             protocol = p.connection,
                         increase_log_size = lambda *a, **k: None,
                         icon = None)
    # make message object,
    release_notes = _get_release_notes()
    if not release_notes.strip():
        return

    msg = common.message.Message(buddy = buddy,
                                 message = release_notes,
                                 content_type = "text/html",
                                 conversation = util.Storage(protocol = p.connection,
                                                             buddy = buddy,
                                                             ischat = False))
    p.on_message(msg)

def _get_release_notes():
    try:
        with open(util.program_dir() / 'res' / "release_notes.html", 'rb') as f:
            data = f.read()

        return data
    except Exception, e:
        log.error("Release notes not found. %r", e)
        return ''

def install_update(*a):
    '''
    Install an update. To do this we need:
     - the downloaded manifest data
     - a list of all the files that need to be written (updateme.txt)
     - a list of all the files that need to be deleted (deleteme.txt)
     - updates must be enabled (--no-update, sys.DEV, or --update-failed can all disable updates)

    If all of this is true, call the appropriate restart_and_update method for our platform.
    Otherwise, delete the aforementioned files so that we don't accidentally start an update again later. This is
    especially important in the case of --update-failed; the app would go into a loop.
    '''
    temp_dir = file_integrity.GetUserTempDir()
    manifest = (temp_dir / 'manifest')
    updateme = (temp_dir / 'updateme.txt')
    deleteme = (temp_dir / 'deleteme.txt')

    if UpdateManager(Null()).should_check_for_updates() and not sys.opts.update_failed:
        if updateme.isfile() and deleteme.isfile() and manifest.isfile():
            print >>sys.stderr, 'Installing update'
            log.info("Installing update")
            helpers.restart_and_update(temp_dir)
            return False # To veto the GUI
    else:
        _delete_updater_files()

        print >>sys.stderr, 'Not installing update'
        log.info("Not installing update")

def _delete_updater_files():
    '''
    Clear out the files that indicate an update is available. After this is done, we can attempt updates again (so
    sys.opts.update_failed is set to False).
    '''
    temp_dir = file_integrity.GetUserTempDir()
    manifest = (temp_dir / 'manifest')
    updateme = (temp_dir / 'updateme.txt')
    deleteme = (temp_dir / 'deleteme.txt')
    if updateme.isfile():
        updateme.remove()
    if deleteme.isfile():
        deleteme.remove()
    if manifest.isfile():
        manifest.remove()

    sys.opts.update_failed = False

def update_status():
    p = common.profile()
    if p is None:
        return False

    um = UpdateManager(p)
    return um.status

def get_client_tag():
    if getattr(sys, 'DEV', False):
        tag = ''
    else:
        tag = 'release'

    tag_fname = 'tag.yaml'
    for fpath in ((stdpaths.userlocaldata / tag_fname), (util.program_dir() / tag_fname)):
        try:
            # If the location or name of this file changes, also update the installer (DigsbyInstaller/DigsbyInstall.nsi)
            # since it deletes it.
            with open(fpath, 'rb') as f:
                yaml = syck.load(f)
                tag = yaml['tag']

        except Exception, e:
            log.debug('Didn\'t get a release tag from %r: %r', fpath, e)
        else:
            log.info("Got release tag %r from %r", tag, fpath)
            break
    else:
        log.info('Using default release tag: %r', tag)

    sys.TAG = tag
    return tag


class UpdateManager(addons.AddOn):
    '''
    Controller for the update process.
    '''
    updating = False

    @property
    def status(self):
        if self.updating:
            if self.downloader:
                return 'downloading'
            if self.updater:
                return 'filechecking'
            return 'checking'
        return 'idle'

    def setup(self):
        log.info("UpdateManager setup")

        self.updating = False
        self.cancelling = False
        self.updater = None
        self.downloader = None
        self.update_checker = UpdateChecker()

        self._timer = util.RepeatTimer(common.pref("digsby.updater.update_interval",
                                                   type = int, default = 6 * 60 * 60),
                                       self.update)
        self._timer.start()

        self.fast_mode = False

    def set_fastmode(self, v):
        self.fast_mode = v
        if self.updater is not None:
            self.updater.fast_mode = v

    def cancel(self):
        if not self.updating:
            return

        self.updating = False
        self.cancelling = True

        if self.updater is not None:
            self.updater.cancel()
            self.updater = None
        if self.downloader is not None:
            self.downloader.cancel()
            self.downloader = None

        hooks.notify("digsby.updater.cancelled")

    def should_check_for_updates(self):

        retval = True
        reason = None
        if not sys.opts.allow_update:
            retval = False
            reason = 'sys.opts.allow_updates == False'

        if sys.DEV and not sys.opts.force_update:
            retval = False
            reason = "sys.DEV and not sys.opts.force_update"

        if self.updating:
            retval = False
            reason = "already checking for updates, or currently updating"

        if not retval:
            log.info('Not checking for updates because: %r', reason)

        return retval

    def update(self):
        if not self.should_check_for_updates():
            if not self.updating:
                # If we're not updating for a reason other than that we're already updating, notify
                # that the update check is complete.
                hooks.notify('digsby.updater.update_check_results', False, None, None)
            return

        self.delete_file_changes()

        self.cancelling = False
        self.updating = True
        hooks.notify("digsby.updater.update_start")
        self.update_checker.release_type = get_client_tag()
        self.update_checker.update(success = self.update_check_success, error = self.update_check_error)

    def update_check_success(self, update_required, manifest_path, manifest_data):
        log.info("Got result for update check. update_required = %r, manifest_path = %r", update_required, manifest_path)

        hooks.notify('digsby.updater.update_check_results', update_required, manifest_path, manifest_data)

        if not update_required:
            self.cancel()
            return

        if self.cancelling:
            return
        log.info("Starting updater.")
        self.updater = file_integrity.ProgramIntegrityChecker(manifest_path = manifest_path,
                                                              manifest_data = manifest_data)

        self.updater.start(success = self.file_check_complete)

    def update_check_error(self, *a):
        self.cancel()
        hooks.notify('digsby.updater.update_check_error', *a)

    def file_check_complete(self, updater):
        assert updater is self.updater

        if not (updater.update_files or updater.delete_files):
            self.cancel()
            return

        self.downloader = downloader.Downloader(updater)

        auto_download = common.pref("digsby.updater.auto_download", type = bool, default = True)
        res = []

        def after_popup():
            if auto_download:
                self.start_downloader()
            elif (not res) or res[0] is None: # No popup was fired.
                def dialog_cb(ok):
                    if ok:
                        self.start_downloader()
                    else:
                        self.stop_timer()

                diag = gui.toolbox.SimpleMessageDialog(
                           None,
                           title= _('Update Available'),
                           message= _("A Digsby update is available to download.\nWould you like to begin downloading it now?"),
                           icon = gui.skin.get('serviceicons.digsby').Resized(32),
                           ok_caption=_('Yes'),
                           cancel_caption=_('No'),
                           wrap=450
                       )
                diag.OnTop = True
                diag.ShowWithCallback(dialog_cb)

        def do_popup():
            res.append(gui.toast.popup(icon = gui.skin.get("serviceicons.digsby"),
                                       header = _("Update Available"),
                                       minor = _("A Digsby update is available to download.\nWould you like to begin downloading it now?"),
                                       sticky = True,
                                       buttons = [(_("Yes"), lambda *a: self.start_downloader()),
                                                  (_("No"), self.stop_timer)],

                                       size = util.nicebytecount(updater.expected_download_size),
                                       onclose = self._download_popup_closed,
#                                       popupid = 'digsby.update',
                                       ))

            wx.CallAfter(after_popup)


        if not auto_download:
            wx.CallAfter(do_popup)
        else:
            wx.CallAfter(after_popup)


    def write_file_changes(self, temp, to_update, to_delete):
        if not temp.isdir():
            temp.makedirs()

        with open(temp/'deleteme.txt', 'wb') as out:
            if to_delete:
                write = lambda s: out.write(unicode(s).encode('filesys', 'replace') + '\n')
                for f in sorted(to_delete, reverse=True):
                    rel_path = self.updater.local_dir.relpathto(f)
                    if rel_path.lower() in ('uninstall.exe', 'digsby.exe',
                                            'lib\\msvcr90.dll', 'lib\\msvcp90.dll',
                                            'lib\\digsby-app.exe','lib\\digsby.exe',
                                            'lib\\digsby updater.exe', 'lib\\digsby preupdater.exe'):
                        continue

                    write(rel_path)

        with open(temp/'updateme.txt', 'wb') as out:
            write = lambda s: out.write(unicode(s).encode('filesys', 'replace') + '\n')

            write('manifest')
            for f  in sorted(to_update, reverse = True):
                if f.path.lower() != helpers.get_exe_name().lower():
                    # this is updated in the 'digsby.clone' process that the updater.exe takes care of.
                    write(f.path)

    def delete_file_changes(self):
        _delete_updater_files()

    def start_downloader(self):
        if self.cancelling:
            return

        self.downloader.start(success = self.download_success, error = self.download_error)

    def stop_timer(self, *a):
        log.info("Stopping update checker timer.")
        self._timer.stop()
        self.cancel()

    def _download_popup_closed(self, *a, **k):
        if k.get("userClose", False):
            self.stop_timer()

    def download_error(self, error_files, success_files):
        log.error("Update incomplete. %d successful files, %d errored files", len(success_files), len(error_files))
        for f in error_files:
            log.error("\t%r", f.path)

        self.cancel()
        hooks.notify('digsby.updater.update_failed')

        auto_download = common.pref("digsby.updater.auto_download", type = bool, default = True)

        if not auto_download:
            popup = gui.toast.popup(
                icon = gui.skin.get('serviceicons.digsby'),
                header = _("Update Failed"),
                minor = _("Digsby was unable to complete the download. This update will be attempted again later."),
                sticky = True,
                buttons = [(_("Manual Update"), lambda: wx.LaunchDefaultBrowser("http://install.digsby.com")),
                           (_("Close"), lambda: popup.cancel())],
#                popupid = 'digsby.update',
            )

    def download_success(self, success_files):
        log.info("Downloaded files. %d files downloaded", len(success_files))

        updater = self.updater
        if updater is None:
            self.cancel()
            return
        self.write_file_changes(updater.temp_dir, updater.update_files, updater.delete_files)

        hooks.notify('digsby.updater.update_complete')
        if not common.pref("digsby.updater.install_prompt", type = bool, default = False):
            log.debug("Update install prompt disabled. Scheduling install")
            self.schedule_install()
        else:
            res = []

            def after_popup():
                if (not res) or res[0] is None:
                    log.debug("Popup was not shown. Scheduling install")
                    self.schedule_install()

            @wx.CallAfter
            def do_popup():
                res.append(gui.toast.popup(
                    icon = gui.skin.get('serviceicons.digsby'),
                    header = _("Update Ready"),
                    minor = _("A new version of Digsby is ready to install. Restart Digsby to apply the update."),
                    sticky = True,
                    buttons = [(_("Restart Now"), self.do_install),
                               (_("Restart Later"), self.schedule_install)],
                    onclose = self._install_popup_closed,
#                    popupid = 'digsby.update',
                ))
                wx.CallAfter(after_popup)

    def do_install(self):
        log.info("Doing install!")
        if self.cancelling:
            log.info("\tNevermind, we're cancelling. Install not happening now.")
            return
        install_update()

    def _install_popup_closed(self, *a, **k):
        if k.get('userClose', False):
            self.schedule_install()

    def schedule_install(self):
        log.info("Schedule install somehow!")
        self.stop_timer()
