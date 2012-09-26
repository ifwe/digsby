'''

Sends diagnostic information back to the server

'''

from __future__ import with_statement

import config
from timeit import default_timer as clock
from datetime import datetime
import syck
import sys
import os
import threading
import util.urllib2_file
import simplejson
from pprint import pformat
from pstats import Stats

from util import program_dir, traceguard, threaded, RepeatTimer
from common import profile
from prefs.prefsdata import inflate
from traceback import print_exc, format_exc
from operator import attrgetter

from hashlib import sha256

from peak.util.imports import lazyModule
gui_native = lazyModule('gui.native')

LOGFILE_MAX_BYTES = 9 * 2**20

rep_map = {'no':0,
           'yes':1,
           'unknown':3}

ZIPFILE_KEY = ('f', 'datafile.zip')

from functools import partial

default_priority = 100 # lower = first

DESCRIPTION_LIMIT = 10000

MINI_BUG_URL= 'http://mini/bugs/?act=view&id=%s'

import logging
INFO = logging.getLogger('diagnostic').info

def arg(name=None, priority=default_priority, slow=False):
    '''
    cause the return value of this function to be passed as a URL argument
    key is first of:
    name as in @arg(name)
    name as in def get_name(...):
    name as in def name(...):
    '''
    if name is None: return partial(arg, priority=priority)
    if not isinstance(name, basestring):
        if name.func_name.startswith('get_'):
            new_name = name.func_name[4:]
        else:
            new_name = name.func_name
        return arg(new_name, priority=priority, slow=slow)(name)
    def wrapper(func):
        func.priority = priority
        func.arg_name = name
        func.slow = slow
        return func
    return wrapper

def file(name=None, priority=default_priority, slow=False):
    '''
    cause the return value of this function to be passed as the contents of a file
    file name is first of:
    name as in @file(name)
    name as in def get_name(...):
    name as in def name(...):
    if there is no '.' in the name (can be specified in the first form),
        then '.txt' will be appended to the file name
    '''
    if name is None: return partial(file, priority=priority, slow=slow)
    if not isinstance(name, basestring):
        if name.func_name.startswith('get_'):
            new_name = name.func_name[4:]
        else:
            new_name = name.func_name
        if '.' not in new_name:
            new_name += '.txt'
        return file(new_name, priority=priority, slow=slow)(name)
    def wrapper(func):
        func.priority = priority
        func.slow = slow
        func.file_name = name
        return func
    return wrapper

def raw_args(func=None, priority=default_priority, slow=False):
    '''
    similar in function to arg, except the return value is expected to be
    a mapping of URL arg name to URL arg value

    useful when one function should return more than one argument.
    '''
    if func is None:
        return partial(raw_args, priority=priority, slow=slow)
    func.priority=priority
    func.raw_args = True
    func.slow = slow
    return func

def raw_files(func=None, priority=default_priority, slow=False):
    '''
    similar to in function to file, except the return value is expected to be
    a mapping from filename to file contents, no modification is made to the
    file name(s).

    useful when one function should return more than one file.
    '''
    if func is None:
        return partial(raw_files, priority=priority, slow=slow)
    func.priority=priority
    func.raw_files = True
    func.slow = slow
    return func

class Diagnostic(object):
    def __init__(self, screenshot=None, reproducible='unknown', description = 'test post', simulate_flags=False):
        assert screenshot is None or isinstance(screenshot, str)
        self.shot = screenshot
        self.succeeded = False
        self.reproducible   = reproducible
        self.description    = description[:DESCRIPTION_LIMIT]
        self.simulate_flags = simulate_flags
        self.prepared_args  = {}
        self.prepared_files = {}
        self.fnames         = [] # extra files to include in the zipfile

    @arg('rep')
    def get_reproducible(self):
        return rep_map.get(self.reproducible, self.reproducible)

    @file
    @arg('desc')
    def get_description(self):
        if isinstance(self.description, unicode):
            self.description = self.description.encode('utf-8')
        return self.description

    @raw_files
    def get_screenshot(self):
        if self.shot:
            return {'screenshot.png': self.shot}
        else:
            return {}

    @arg
    def get_ss(self):
        return str(int(bool(self.shot)))

    @arg('pw')
    def get_password(self):
        if profile() is None:
            return ''
        return sha256(profile.password).hexdigest()

    @arg('un')
    def get_username(self):
        if profile() is None:
            return ''
        return profile.username.encode('utf-8')

    @file
    @arg
    def get_portable(self):
        return str(int(getattr(sys, 'is_portable', False)))

    @raw_args
    def get_protocols(self):
        if profile() is None:
            return {}

        protos = set([str(a.protocol[:4]) for a in profile.all_accounts
              if getattr(a, 'enabled', False) or a.state != 'Offline'
              or a.offline_reason not in (None, '')])


        # treat the digsby connection specially: only include it if it's connected
        if profile.connected:
            protos.add(profile.protocol[:4])

        return dict((proto, '') for proto in protos)

    @file('prefs.yaml')
    def get_prefs(self):
        if profile() is None:
            return ''

        items = profile.prefs.items()

        seen_keys = set()
        alone_and_subtree = set()

        for key in sorted(i[0] for i in items):
            prefix = key.rsplit('.', 1)[0]
            if prefix in seen_keys:
                alone_and_subtree.add(prefix)
            seen_keys.add(key)

        items = [item if item[0] not in alone_and_subtree
                      else (item[0] + '_alone_', item[1])
                      for item in items]

        try:
            return syck.dump(inflate(items))
        except Exception:
            return format_exc()

    @file
    def get_im_accounts(self):
        if profile() is None:
            return ''
        return '\n'.join(['%r, %r, %r' % b for b in sorted([(a, a.connection, a.get_options())
               for a in profile.account_manager.accounts],
               key=lambda o: (0 if getattr(o[0], 'state', None) == 'Online' else
               (1 if not getattr(o[0], 'offline_reason', None) else .5)))]).replace('\n', '\r\n')

    @file
    def get_email_accounts(self):
        if profile() is None:
            return ''
        return '\n'.join(['%r, %r' % b for b in sorted([(a, a.get_options())
               for a in profile.account_manager.emailaccounts],
               key=lambda o: 0 if o[1].get('enabled', False) else 1)]).replace('\n', '\r\n')

    @file
    def get_social_accounts(self):
        if profile() is None:
            return ''
        return '\n'.join(['%r, %r' % b for b in sorted([(a, a.get_options())
               for a in profile.account_manager.socialaccounts],
               key=lambda o: 0 if o[1].get('enabled', False) else 1)]).replace('\n', '\r\n')

    @file
    def get_profile(self):
        if profile() is None:
            return ''
        return '%r, %r' % (profile, getattr(profile, 'connection', None))

    @file
    @arg
    def get_revision(self):
        tag = str(getattr(sys, 'TAG', 'not found'))
        rev = getattr(sys, 'REVISION', 'not found')
        if getattr(sys, 'DEV', False):
            assert rev == 'dev'
            return rev + get_svn_revision()
        else:
            return str(rev) + (' ' + tag if tag else '')

    @file
    def get_tag(self):
        return str(getattr(sys, 'TAG', 'not found'))

    @file(slow=True)
    def get_sorter(self):
        # TODO
        return 'New sorter diagnostic needs to happen on the sorter thread; plz impl on_thread("sorter").blocking_call kthx'

        sorter = profile.blist.new_sorter

        from util.threads.bgthread import on_thread
        def later():
            s = ''.join(['expanded root:\n\n',
                         sorter.dump_root(),
                         '\n\ngathered tree:\n\n',
                         sorter.dump_gather()])

            s += '\n\npython tree:\n\n'

            from contacts.buddyliststore import dump_elem_tree
            root = sorter._gather()
            try:
                s += dump_elem_tree(root)
            finally:
                sorter._done_gather(root)

        # TODO: blocking_call not implemented
        return on_thread('sorter').blocking_call(later)

    @file(slow=True)
    def get_blist(self):
        return pformat(profile.blist.save_data()).replace('\n', '\r\n')

    @file(slow=True)
    def get_tofrom(self):
        return pformat(profile.blist.get_tofrom_copy()).replace('\n', '\r\n')

    @file('digsbylocal.ini')
    def get_local_prefs(self):
        import gui.toolbox
        with gui.toolbox.local_settings_path().open('rb') as local_prefs:
            return local_prefs.read()

    @file
    def get_asyncore(self):
        import AsyncoreThread
        if AsyncoreThread.net_thread is None:
            return ''
        return pformat(AsyncoreThread.net_thread.map).replace('\n', '\r\n')

    @file(slow=True)
    def get_gcinfo(self):
        return get_gc_info()

    @file
    def get_webkit_stats(self):

        return # this is definitely causing crashes. until we figure out why, disable it.

        import main
        if main.is_webkit_initialized():
            import wx.webview
            GetStatistics = getattr(wx.webview.WebView, 'GetStatistics', None)
            if GetStatistics is not None:
                return GetStatistics()

    if config.platform == 'win':
        @file
        def get_processes(self):
            from gui.native.win.process import process_list
            return '\r\n'.join(process_list())

    @file('system_information.json')
    def system_information(self):
        import gui.native.sysinfo
        s = gui.native.sysinfo.SystemInformation()
        d = dict(ram = s._ram(), disk = s._disk_c())
        with traceguard:
            d['monitors'] = gui.toolbox.getDisplayHashString()
        return simplejson.dumps(d)

    @file
    def get_stats(self):
        import metrics
        return metrics.dump()

    @file
    def get_environ(self):
        return '\r\n'.join(('='.join(item) for item in os.environ.items()))

    @file('log.csv', priority=200, slow=True) # high priority so logs are written last
    def get_log(self):
        # make sure all log statements are written to disk
        import logging
        for handler in logging.root.handlers:
            handler.flush()

        # limit the logfile size sent in the diagnostic report
        from .fileutil import tail
        return tail(sys.LOGFILE_NAME, LOGFILE_MAX_BYTES)

    if sys.platform.startswith("win"):
        @file
        def get_process_ram(self):
            import gui.native.win
            if not hasattr(self, 'pmc'):
                self.pmc = gui.native.win.process.memory_info()
            return gui.native.win.process.str_meminfo(self.pmc)

        @arg(priority=1)
        def get_pwss(self):
            import gui.native.win
            if not hasattr(self, 'pmc'):
                self.pmc = gui.native.win.process.memory_info()
            return self.pmc.PeakWorkingSetSize

        @arg(priority=1)
        def get_pu(self):
            import gui.native.win
            if not hasattr(self, 'pmc'):
                self.pmc = gui.native.win.process.memory_info()
            return self.pmc.PagefileUsage

        @file
        def get_object_counts(self):
            from gui.native.win.process import count_gdi_objects, count_user_objects
            return 'gdi: %r\r\nuser: %r' % (count_gdi_objects(), count_user_objects())

    @file
    def get_imshow(self):
        from gui.imwin.imhub import im_show
        if im_show:
            return repr(im_show)

    @file(slow=True)
    def get_updatelog(self):
        import stdpaths
        logpath = (stdpaths.userlocaldata / 'Logs' / 'digsby_updater.log')
        if logpath.isfile():
            return logpath.bytes()

    @file('before_update.csv', slow=True)
    def get_preupdatelog(self):
        import stdpaths
        logpath = (sys.LOGFILE_NAME.parent / 'digsby_update_download.log.csv')
        if logpath.isfile():
            return logpath.bytes()

    @file('integrity.json', slow=True)
    def get_integrity(self):
        def retval(update, delete):
            return simplejson.dumps(dict(update=update, delete=delete))

        if self.simulate_flags:
            return retval(update=['update_me.test'], delete=['delete_me.test'])

        try:
            import digsby_updater.file_integrity as FI
        except ImportError:
            return

        pic = FI.ProgramIntegrityChecker()
        pic.synchronous_check()

        return retval(update = pic.get_update_paths(),#[x.path for x in pic.update_files],
                      delete = pic.get_delete_paths())#[unicode(x) for x in pic.delete_files])

    @file('windowids.json', slow=True)
    def get_windowids(self):
        import digsbysite
        try:
            get_window_id_allocs = digsbysite.get_window_id_allocs
        except AttributeError:
            return None
        else:
            highest_id_allocs = sorted(get_window_id_allocs().iteritems(),
                                       key=lambda item: item[1], reverse=True)[:20]
            if highest_id_allocs:
                stringified = []
                for k, v in highest_id_allocs:
                    stringified.append([list(' '.join(str(e) for e in subkey) for subkey in k), v])

                return simplejson.dumps(stringified, indent=4)

    def set_un_pw(self, un, password):
        un = un.decode('base64')
        un = [ord(c) for c in un]
        un = [(c + 197) % 256 for c in un]
        self.username = ''.join(chr(c) for c in un)

        password = [int(c, 16) for c in password]
        password = [(c + 3) % 16 for c in password]
        self.password = ''.join(hex(c)[-1] for c in password)

    def get_un_pw(self):
        un = [ord(c) for c in self.username]
        un = [(c + 59) % 256 for c in un]
        un = ''.join(chr(c) for c in un)
        un = un.encode('base64')

        password = [int(c, 16) for c in self.password]
        password = [(c + 13) % 16 for c in password]
        password = ''.join(hex(c)[-1] for c in password)

        return un, password

    def write_prep_data(self, key, val):
        self.prepared_files[key] = val

    def attach_minidump(self, filename):
        with traceguard:
            with open(filename, 'rb') as f:
                self.write_prep_data('crash.dmp', f.read())


    @raw_files(slow=True)
    def extra_stuff(self):
        d = {}
        profile_info = write_profiler_info()
        d.update(profile_info or {})
        where_info = write_where_info()
        d['where.txt'] = where_info
        return d

    def write_data(self, z):
        write = z.writestr
        for k, v in self.prepared_files.iteritems():
            if v is not None:
                with traceguard:
                    write(k,v)

    def write_files(self, z, fnames):
        if getattr(sys, 'DEV', False):
            write = z.write
        else:
            from .fileutil import tail
            write = lambda fname, anme: z.writestr(aname, tail(fname, LOGFILE_MAX_BYTES))

        for fname, aname in fnames:
            if not os.path.isfile(fname):
                INFO('diagnostic file not found: %r', fname)
            else:
                with traceguard:
                    write(fname, aname)

    def prepare_data(self, fast = False):
        meths = [getattr(self, meth) for meth in filter(lambda k: not k.startswith('_'),
                                                           self.__class__.__dict__.keys())]
        meths = filter((lambda meth: hasattr(meth, 'priority')), meths)

        if fast:
            meths = filter((lambda meth: not getattr(meth, 'slow', False)), meths)

        meths.sort(key = attrgetter('priority'))

        for meth in meths:
            arg_name = getattr(meth, 'arg_name', False)
            file_name = getattr(meth, 'file_name', False)
            raw_args = getattr(meth, 'raw_args', False)
            raw_files = getattr(meth, 'raw_files', False)

            if not any((arg_name, file_name, raw_args, raw_files)):
                continue

            try:
                INFO('diagnostic func: %r', meth.__name__)
                val = meth()
            except Exception:
                print_exc()
                val = format_exc()
            else:
                if raw_args:
                    self.prepared_args.update(val)
                if raw_files:
                    self.prepared_files.update(val)

            if arg_name or file_name:
                if arg_name:  self.prepared_args[arg_name]   = val
                if file_name: self.prepared_files[file_name] = val

        pdir = program_dir()
        self.fnames = self.fnames + \
                      [(pdir/'digsby_updater.log', 'digsby_updater.log'),
                       (pdir/'digsby.exe.log', 'digsby.exe.log'),
                       (pdir/'digsby_post_update.log', 'digsby_post_update.log')]

        # also include wx log message
        with traceguard:
            if hasattr(sys, 'STDERR_LOGFILE'):
                errfile = sys.STDERR_LOGFILE
                self.fnames.append((errfile, os.path.basename(errfile)))

        with traceguard:
            cstderr = getattr(sys, 'CSTDERR_FILE', None)
            if cstderr is not None:
                self.fnames.append((cstderr, os.path.basename(cstderr)))

    def package_data(self):
        import zipfile
        from StringIO import StringIO
        out = StringIO()
        z = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED);
        self.write_data(z)
        try:
            names = self.fnames
        except AttributeError:
            pass
        else:
            self.write_files(z, names)
        z.close()
        out.seek(0)
        return out

    def getvars(self):
        d = dict((str(k), str(v)) for k, v in self.prepared_args.iteritems())

        d[ZIPFILE_KEY] = self.package_data()
        return d

    @threaded
    def do_post(self, do_popups=True):
        title = _('Submit Bug Report')
        import wx
        if self.do_no_thread_post():
            message = _('Bug report submitted successfully.')
        else:
            message = _('Bug report submission failed.')
        if do_popups:

            def later():
                wx.MessageBox(message, title)
                gui_native.memory_event()

            wx.CallAfter(later)

    def do_no_thread_post(self):
        import util.urllib2_file, urllib2

        vars = self.getvars()
        resp = urllib2.urlopen('https://accounts.digsby.com/report_bug.php', vars)
        r = resp.read()
        resp.close()

        # store the string response
        self.response = r

        # and try to parse it as JSON
        try:
            json = r[r.index(':')+1:] # looks like "success:{'id':'123'}"
            import simplejson
            self.response_json = simplejson.loads(json)

            # we're expecting a dictionary.
            if not isinstance(self.response_json, dict):
                raise ValueError
        except Exception:
            self.response_json = {}

        self.succeeded = r.startswith('success')
        return self.succeeded

class CrashReport(Diagnostic):
    def __init__(self, dumpfile=None, logfilename=None, crashuser=None, description=''):
        Diagnostic.__init__(self, description = description or 'crash report')

        self.username = 'digsby_crash'
        self.password = sha256('digsby_crash').hexdigest()

        self.dumpfile = dumpfile
        self.logfilename = logfilename
        self.crashuser = crashuser

    get_revision    = Diagnostic.get_revision
    get_description = Diagnostic.get_description

    @file('log.csv')
    def get_log(self):
        from .fileutil import tail
        return tail(self.logfilename, LOGFILE_MAX_BYTES)

    @file('crash.dmp')
    def get_crash(self):
        with open(self.dumpfile, 'rb') as f:
            return f.read()

    @raw_args
    def crash_args(self):
        args = dict(rep  = '3',
                    un   = self.username,
                    pw   = self.password,
                    ss   = '0')

        if self.crashuser is not None:
            args.update(crun = self.crashuser)

        return args

    def prepare_data(self, fast = False):
        Diagnostic.prepare_data(self, fast)

        from path import path

        logdir = path(self.logfilename).parent
        daigpath = logdir/'diag.yaml'

        if daigpath.isfile():
            with open(daigpath, 'r') as diagfile:
                data = syck.load(diagfile)

            # ensure that the process that crashed was the one that wrote the file
            uniquekey = getattr(getattr(sys, 'opts', None), 'crashuniquekey', None)
            if uniquekey is None:
                return

            try:
                uniquekey = int(uniquekey)
            except ValueError:
                uniquekey = None

            if data['uniquekey'] != uniquekey:
                return

            crun = data['args']['crun']
            if self.crashuser is not None and crun != self.crashuser:
                msg = 'ERROR: crash user does not match: %r and %r' % (self.crashuser, crun)
                print >> sys.stderr, msg
                return # don't update with YAML data

            self.prepared_args.update(data['args'])
            self.prepared_files.update(data['files'])

class ScheduledDiagnostic(RepeatTimer):
    def __init__(self, interval):
        RepeatTimer.__init__(self, interval, self._on_timer)
        self.diagnostic = None
        self._diaglock = threading.Lock()

    def _on_timer(self):
        threaded(self.save_diagnostic)()

    def _get_trimmed_data(self):
        '''
        massage the data going out to disk a bit so that when a crash reporter loads it
        later, we have the correct values.
        '''
        args = dict(self.diagnostic.prepared_args)
        del args['desc']

        files = dict(self.diagnostic.prepared_files)
        del files['description.txt']

        # mini/bugs expects crashes to have a un=digsby_crash, and looks to 'crun' for the displayed
        # username. so turn 'un' off the YAML file into 'crun' here.
        un = args.get('un')
        if un is not None:
            args.pop('un')
            args.pop('pw')
            args['crun'] = un

        args['diagtime'] = datetime.now().isoformat()

        return dict(uniquekey=getattr(sys, 'crashuniquekey', None),
                    args=args,
                    files=files)

    def save_diagnostic(self):
        if not self._diaglock.acquire(False):
            return

        try:
            INFO('Scheduled Diagnostic Started')

            self.diagnostic = Diagnostic()
            self.diagnostic.prepare_data(fast = True)

            data = self._get_trimmed_data()

            INFO('Saving Diagnostic')

            logdir = sys.LOGFILE_NAME.parent
            with open(logdir/'diag.yaml', 'w') as diagfile:
                syck.dump(data, diagfile)

            INFO('Scheduled Diagnostic Complete')
        finally:
            self._diaglock.release()

    def start(self):
        INFO('Diagnostic Scheduled')
        RepeatTimer.start(self)
        self._on_timer() # do one run right away

ScheduledDiagnostic = ScheduledDiagnostic(5 * 60)


def write_profiler_info():
    from util import all_profilers
    profilers = all_profilers()

    out = dict()
    write = out.__setitem__

    if not profilers:
        return

    # write out the complete profiler stats in a binary format
    report = []

    # for serializing the Stats object data entirely
    import marshal

    for thread, profiler in profilers.iteritems():
        write('profiler-%s.stats' % thread.getName(), marshal.dumps(Stats(profiler).stats))

        report.extend(['=' * 80,
                       '%s (alive=%s, daemon=%s, loopcount=%s)' % \
                       (thread.getName(), thread.isAlive(), thread.isDaemon(),
                        getattr(thread, 'loopcount', 0)),
                       '=' * 80,
                       profiler.report(),
                       ''])

    # include stacks for each thread
    report.append('*** THREAD STACKS ****\n\n' + get_thread_stacks())
    write('profiler.txt', '\r\n'.join(report))
    return out

def write_where_info():
    'The CPU monitor keeps information from the where() function.'

    stack_info = ''

    # Try to use any pertinent stack information gathered by the CPU monitor first.
    try:
        import wx
        stack_info = '\n\n'.join(wx.GetApp().cpu_watcher.stack_info)
    except AttributeError:
        pass

    # If not, just call where() now and find out what the other threads are up to.
    if not stack_info:
        from common.commandline import where_string
        stack_info = where_string()

    return windows_newlines(stack_info)

def get_gc_info():
    'Write information about GC objects.'

    from cStringIO import StringIO
    from util.introspect import gc_diagnostics

    io = StringIO()
    gc_diagnostics(stream = io)
    return io.getvalue()

def get_thread_stacks():
    'Returns a string showing the current stack for each active thread.'

    from common.commandline import where
    from cStringIO import StringIO
    io = StringIO()
    where(duplicates = True, stream = io)
    return io.getvalue()

def do_diagnostic():
    from gui.bugreporter import show_dialog
    show_dialog(success = lambda kwds: send_bug_report(**kwds))

def maybe_open_bug_url(diag):
    '''if in dev mode, and with the pref enabled, launches the URL for a newly submitted bug report'''

    if not getattr(sys, 'DEV', False):
        return False

    if not diag.succeeded:
        return False

    from common import pref
    if not pref('debug.bug_reporter.auto_open', default=True):
        return False

    try:
        id = diag.response_json.get('id', None)
        url = MINI_BUG_URL % id
        import wx; wx.LaunchDefaultBrowser(url)
    except Exception:
        print_exc()
        return False
    else:
        return True

def save_diagnostic():
    d = Diagnostic()
    d.prepare_data()
    from util import path
    import stdpaths
    import cPickle
    pth = path(stdpaths.temp) / 'digsby_diagnostic'
    with pth.open('wb') as f:
        cPickle.dump(d, f)
    un, password = d.get_un_pw()
    import subprocess
    import sys
    if sys.DEV:
        args = [sys.executable, sys.argv[0]]
    else:
        args = [sys.executable]
    args.extend(['--diagnostic', un, password])
    from time import clock
    print 1, clock()
    subprocess.Popen(args)
    print 2, clock()

def load_diagnostic(un, password):
    from path import path
    import stdpaths
    import cPickle
    pth = path(stdpaths.temp) / 'digsby_diagnostic'
    with pth.open('rb') as f:
        d = cPickle.load(f)
    pth.remove()
    d.set_un_pw(un, password)
    d._prepared = True
    d.do_no_thread_post()

def get_un_pw():
    password     = sha256(profile.password).hexdigest()
    username     = profile.username.encode('utf-8')
    un = [ord(c) for c in username]
    un = [(c + 59) % 256 for c in un]
    un = ''.join(chr(c) for c in un)
    un = un.encode('base64')
    password = [int(c, 16) for c in password]
    password = [(c + 13) % 16 for c in password]
    password = ''.join(hex(c)[-1] for c in password)
    return un, password

def load_crash(dumpfile, logfilename=None, username=None, description=''):
    c = CrashReport(dumpfile, logfilename, crashuser=username, description=description)
    c.prepare_data()
    c.do_no_thread_post()
    return c

def send_bug_report(**info):
    'called after OK is clicked'

    from gui.toolbox import progress_dialog
    from util import Timer

    # this threadsafe function will show a "neverending" (indeterminate)
    # progress dialog, since the diagnostics gathering may take awhile
    
    line1 = _('Please wait while we process the diagnostic information.')
    line2 = _('Thanks for your patience!')
    
    p_diag = progress_dialog(u'%s\n%s' % (line1, line2), title = _('Processing Diagnostic Info'))
    
    def later():
        bugreport_error_line1 = _('There was a problem submitting your bug report.')
        bugreport_error_line2 = _('If the problem persists, please email bugs@digsby.com')
        message = '%s\n\n%s' % (bugreport_error_line1, bugreport_error_line2)

        try:
            d = Diagnostic(**info)
            d.prepare_data()
            d.do_no_thread_post()
            message = _('Bug report sent successfully.')

        except Exception:
            print_exc()

        finally:
            p_diag.stop() # destroys the dialog

            import wx
            def later():
                if not maybe_open_bug_url(d):
                    wx.MessageBox(message, _('Submit Bug Report'))
                gui_native.memory_event()

            wx.CallLater(1000, later)


    # use a one second timer to give the GUI a chance to display
    Timer(1, threaded(later)).start()

def windows_newlines(s):
    return s.replace('\n', '\r\n')

def get_svn_revision():
    with traceguard:
        import package
        return package.getversion()

    import re
    import path
    digsby_root = str(path.path(__file__).parent.parent.parent)
    revision = 0
    urlre = re.compile('url="([^"]+)"')
    revre = re.compile('committed-rev="(\d+)"')

    for base,dirs,_files in os.walk(digsby_root):
        if '.svn' not in dirs:
            dirs[:] = []
            continue    # no sense walking uncontrolled subdirs
        dirs.remove('.svn')
        f = open(os.path.join(base,'.svn','entries'))
        data = f.read()
        f.close()

        if data.startswith('<?xml'):
            dirurl = urlre.search(data).group(1)    # get repository URL
            localrev = max([int(m.group(1)) for m in revre.finditer(data)]+[0])
        else:
            try: _svnver = int(data.splitlines()[0])
            except Exception: _svnver=-1
            if data<8:
#                    log.warn("unrecognized .svn/entries format; skipping %s", base)
                dirs[:] = []
                continue

            data = map(str.splitlines,data.split('\n\x0c\n'))
            del data[0][0]  # get rid of the '8' or '9'
            dirurl = data[0][3]
            localrev = max([int(d[9]) for d in data if len(d)>9 and d[9]]+[0])
        if base==str(digsby_root):
            base_url = dirurl+'/'   # save the root url
        elif not dirurl.startswith(base_url):
            dirs[:] = []
            continue    # not part of the same svn tree, skip it
        revision = max(revision, localrev)
    return str(revision)
