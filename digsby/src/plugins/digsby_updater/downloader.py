'''
Initialize a Downloader with an UpdateManager instance:
>>> my_updater
<digsby_updater.updater.UpdateManager instance>
>>> d = Downloader(my_updater)

The download process can be kicked off by calling the `start` method:
>>> d.start(success = lambda list_of_downloaded_files: None,
			error   = lambda list_of_error_files, list_of_success_files: None)

Instances of this class also trigger certain hooks:
 - digsby.updater.update_download_start(list_of_file_descriptions_to_download)
	When the first file is about to be processed.
 - digsby.updater.file_download_start(file_description)
    When any file is about to be processed.
 - digsby.updater.file_download_complete(file_description)
	When a file is moved to the 'done' state.
 - digsby.updater.file_download_error(file_description)
	When a file is moved to the 'error' state.
 - digsby.updater.update_download_complete(list_of_done_file_descriptions)
	When all files are in the 'done' state.
 - digsby.updater.update_download_error(list_of_failed_file_descriptions, list_of_done_file_descriptions)
	When all files are in the 'done' or 'failed' state.
			
Manages a queue of files (file description objects) that need to be downloaded. The source 
should be a web URL and the destination should be a directory - usually a temporary one. 

For each file, the destination directory is scanned for an existing and equivalent copy 
(equivalence is determined the file description we have). If found, the file is considered 
'done'. If an equivalent copy is not found, downloading begins.

Downloading is performed with asynchttp, which by default may attempt the a single request up
to 3 times. If the first request fails, the backup host is used.

If there is an error downloading, the file is considered 'failed'.

If downloading succeeds, the file content is checked against the description we have for it.
If the description matches, the file is considered 'done'. If it does not, the backup host will
be attempted. If the file was retrieved from the backup host, the file is considered  'failed'.

At this point the next file is attempted. Only one file is downloaded at a time (the process is 
not parallelized).

Once all files are in either 'done' or 'failed' state, callbacks are called (success if all files
are done, error otherwise).
'''
import path
import hooks
import time
import common
import util
import util.net as net
import util.callbacks as callbacks
import util.httptools as httptools
import common.asynchttp as asynchttp

import logging
log = logging.getLogger('d_updater.download')

def append_ts(url):
    '''
    Append a query string to the end of a URL that contains the timestamp. The
    purpose for this is to force proxies to not return cached data. Amazon S3 (and perhaps
    other web servers?) don't do anything with the query string so the original file is the one
    requested.
    >>> append_ts('http://www.google.com/thing.txt')
    'http://www.google.com/thing.txt?12345678'
    '''
    if isinstance(url, basestring) and '?' not in url and not url.startswith('file:'):
        url = url + '?' + str(int(time.time()))

    return url

def httpopen(url, *a, **k):
    url = append_ts(url)
    return asynchttp.httpopen(url, *a, **k)

class Downloader(object):
    remote_root_base = path.path('http://update.digsby.com/')
    backup_root_base = path.path('http://updatebackup.digsby.com/')

    def __init__(self, updater):
        self.updater = updater
        self.unchecked_files = list(updater.update_files)
        self.errored_files = []
        self.downloaded_files = []
        self.num_files = len(self.unchecked_files)
        relpath = self.remote_root_base.relpathto(path.path(updater.manifest_path).parent)
        self.local_root = path.path(updater.temp_dir)
        self.remote_root = net.httpjoin(self.remote_root_base, relpath) + "/"
        self.backup_root = net.httpjoin(self.backup_root_base, relpath) + "/"
        self.callback = None
        self.cancelling = self.updater.cancelling

    @callbacks.callsback
    def start(self, callback = None):
        self.callback = callback
        hooks.notify("digsby.updater.update_download_start", self.unchecked_files)
        self.next_file()

    def cancel(self):
        self.cancelling = True

    def next_file(self):
        if self.cancelling:
            return

        if self.unchecked_files:
            file = self.unchecked_files.pop()
            hooks.notify("digsby.updater.file_download_start", file)
            if not file.match_local(self.local_path_for_file(file)):
                self._download_file(file)
            else:
                log.debug("%r was already downloaded", file.path)
                self.downloaded_files.append(file)
                hooks.notify("digsby.updater.file_download_complete", file)
                self.queue_next_file()
        else:
            if len(self.errored_files) + len(self.downloaded_files) == self.num_files:
                self.finished()

    def queue_next_file(self):
        interval = common.pref('digsby.updater.file_download_interval', type = int, default = 0.1)
        if interval == 0:
            interval = 0.1

        t = util.Timer(interval, self.next_file)
        t._verbose = False
        t.start()

    def _download_file(self, file):
        httpopen(self.remote_path_for_file(file),
                 success = lambda req, resp: self.got_file(file, resp),
                 error = lambda req, e: self.try_backup(file, e))

    def got_file(self, file, resp, backup_exception = None):
        dest_path = self.local_path_for_file(file)
        if not dest_path.parent.isdir():
            dest_path.parent.makedirs()
        with open(dest_path, 'wb') as f:
            data = resp.read(32768)
            while data:
                f.write(data)
                data = resp.read(32768)

        resp.close()

        if file.match_local(dest_path):
            log.debug("successful download: %r", file.path)
            self.downloaded_files.append(file)
            hooks.notify("digsby.updater.file_download_complete", file)
        else:
            try:
                dest_path.remove()
            except Exception, e:
                log.debug("Error deleting bad file: %r", e)

            if backup_exception is None:
                self.try_backup(file, Exception("Bad data from primary server"))
                return # Don't queue next file yet.
            else:
                log.error("Error downloading %r. Bad data from backup server; primary server error was: %r", 
						  file.path, backup_exception)
                self.errored_files.append(file)
                hooks.notify("digsby.updater.file_download_error", file)

        self.queue_next_file()

    def try_backup(self, file, e):
        log.error("Error downloading %r from primary server. Error was %r", file.path, e)
        httpopen(self.remote_path_for_file(file, backup = True),
                 success = lambda req, resp: self.got_file(file, resp, e),
                 error = lambda req, e2: self.file_error(file, e, e2))

    def file_error(self, file, e1, e2):
        log.error("Errors occurred fetching %r from primary and backup servers. Errors were (%r, %r)", 
				  file.path, e1, e2)
        self.errored_files.append(file)
        self.queue_next_file()

    def local_path_for_file(self, file):
        return self.local_root / file.path

    def remote_path_for_file(self, file, backup = False):
        if backup:
            root = self.backup_root
        else:
            root = self.remote_root
        return net.httpjoin(root, file.path.replace("\\", "/").encode('url'))

    def finished(self):
        cb, self.callback = self.callback, None
        if self.errored_files:
            hooks.notify("digsby.updater.update_download_error", self.errored_files, self.downloaded_files)
            if cb is not None:
                cb.error(self.errored_files, self.downloaded_files)
        else:
            hooks.notify("digsby.updater.update_download_complete", self.downloaded_files)
            if cb is not None:
                cb.success(self.downloaded_files)
