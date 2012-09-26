#__LICENSE_GOES_HERE__
'''
build util
'''

from __future__ import with_statement

from contextlib import contextmanager

import commands
import fnmatch
import hashlib
import os.path
import shlex
import shutil
import subprocess
import sys
import distutils.sysconfig

pathjoin = os.path.join

from constants import *

if sys.platform == 'win32':
    platformName = 'win'
    build_dir = os.path.split(os.path.abspath(__file__))[0]
    assert os.path.isdir(build_dir)

    class buildpaths:
        platform_deps = pathjoin(build_dir, 'msw', 'dependencies')
elif sys.platform == 'darwin':
    platformName = 'mac'
elif 'linux' in sys.platform:
    platformName = 'gtk'
else:
    raise AssertionError('Help! Unknown platform!')

if platformName == "win":
    # TODO: 64 bit?
    platname = 'win32'
else:
    platname = platformName

python_version = '26'

try:
    import digsbypaths
except ImportError:
    path_to_digsby_paths = os.path.normpath(pathjoin(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    sys.path.append(path_to_digsby_paths)
    import digsbypaths

DEPS_DIR = distutils.sysconfig.get_python_lib()  # digsbypaths.get_platlib_dir(DEBUG)

if not os.path.isdir(DEPS_DIR):
    os.makedirs(DEPS_DIR)


stars = '*'*80
if '--quiet' in sys.argv:
    def inform(*a, **k): pass
else:
    def inform(*a, **k):
        if 'banner' in k:
            print '\n%s\n  %s\n\n%s\n' % (stars, k['banner'], stars)
        else:
            for arg in a:
                print arg,
            print

def fatal(msg, return_code = 1):
    print >> sys.stderr, msg
    sys.exit(return_code)

class tardep(object):
    def __init__(self, url, tar, ext, size, dirname = None, md5 = None, indir=None):
        self.url = url + tar + ext
        self.filename = self.tar = tar + ext
        self.dirname = dirname if dirname is not None else tar
        self.size = size
        self.md5 = md5
        self.indir = indir
        if indir: self.dirname = indir

    def get(self):
        if not os.path.isdir(self.dirname):
            wget_cached(self.tar, self.size, self.url)

            if self.md5 is not None and md5_file(self.tar, hex=True) != self.md5:
                raise AssertionError('md5 did not match: %r' % self.tar)
            if self.tar.endswith('.zip'):
                unzip(self.tar, indir=self.indir)
            else:
                untar(self.tar, indir=self.indir)

            if self.indir is None:
                assert os.path.isdir(self.dirname), self.dirname
            else:
                assert os.path.isdir(self.indir), self.indir
        else:
            inform('exists: %s' % self.dirname)

        return self.dirname

@contextmanager
def timed(name=''):
    'Shows the time something takes.'

    from time import time

    before = time()
    try:
        yield
    finally:
        msg = 'took %s secs' % (time() - before)
        if name:
            msg = name + ' ' + msg
        inform(msg)

@contextmanager
def cd(*path):
    '''
    chdirs to path, always restoring the cwd

    >>> with cd('mydir'):
    >>>     do_stuff()
    '''
    original_cwd = os.getcwd()
    try:
        new_cwd = pathjoin(*path)
        #inform('cd %s' % os.path.abspath(new_cwd))
        os.chdir(new_cwd)
        yield
    finally:
        #inform('cd %s' % os.path.abspath(original_cwd))
        os.chdir(original_cwd)

def which(cmd, default=None):
    if platformName == "win":
        for adir in os.environ["PATH"].split(os.pathsep):
            cmd_path = os.path.join(adir, cmd)
            for ext in [''] + os.environ['PATHEXT'].split(os.pathsep):
                if os.path.exists(cmd_path + ext):
                    return cmd_path + ext
    else:
        return commands.getoutput('which ' + cmd)

    return default

def run(cmd, checkret = True, expect_return_code = 0, capture_stdout = False, env = None, shell=False,
        executable=None, include_stderr=False, print_stdout = None):
    '''
    Runs cmd.

    If the process returns 0, returns the contents of stdout.
    Otherwise, raises an exception showing the error code and stderr.
    '''
    inform(cmd)
    if print_stdout is None:
        print_stdout = capture_stdout

    try:
        if isinstance(cmd, basestring):
            args = shlex.split(cmd.replace('\\', '\\\\'))
        else:
            args = cmd

        if capture_stdout:
            process = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE, env = env, shell=shell)
        else:
            process = subprocess.Popen(args, env = env, shell=shell)
    except OSError:
        print >>sys.stderr, 'Error using Popen: args were %r' % args
        raise

    # grab any stdout, stderr -- this means we block until the process is finished!
    stdout, stderr = process.communicate()

    # also grab the return code
    retcode = process.returncode

    # fail if the return code was an error
    if checkret and retcode != expect_return_code:
        print stderr
        print "Error running %s" % cmd
        sys.exit(retcode)

    txt = stdout.strip() if stdout is not None else None
    if txt is not None and include_stderr:
        stdout += stderr

    if print_stdout and stdout:
        print stdout,

    return stdout.strip() if stdout is not None else None

def downloaded(path, size):
    'Checks to see if file at path exists and has a certain size.'

    return os.path.exists(path) and os.path.getsize(path) == size

if os.name == 'nt':
    def wget(url):
        'wget for windows, implemented with urllib'

        i = url.rfind('/')
        file = url[i+1:]
        def reporthook(*a): print file, a

        print url, "->", file
        import urllib
        urllib.urlretrieve(url, file, reporthook)
else:
    def wget(url):
        'Downloads the file at url.'

        run(['curl', '-O', url])

def unzip(path, verbose = False, indir=None):
    "Unzip using Python's zipfile module."

    import zipfile
    makedirs, dirname = os.makedirs, os.path.dirname

    f = zipfile.ZipFile(path, 'r')
    unzip_dir = os.path.splitext(os.path.basename(path))[0]
    try:
        makedirs(unzip_dir)
    except Exception:
        pass

    for info in f.infolist():
        on_disk_filename = filename = info.filename

        if indir is not None:
            on_disk_filename = os.path.join(indir, filename)

        try: makedirs(dirname(on_disk_filename))
        except Exception: pass

        if not filename.endswith('/'):
            open(on_disk_filename, 'wb').write(f.read(filename))

import tarfile
makedirs, dirname = os.makedirs, os.path.dirname

def untar(path, verbose = False, indir=None):
    'A wimpy untar for tar impoverished systems.'

    if sys.platform.startswith("win"):
        print 'untar %s' % path
        fileobj = open(path, 'rb')
        try:
            # try gzipped first
            tf = tarfile.open(path, "r:gz", fileobj=fileobj)
        except:
            fileobj = open(path, 'rb')
            tf = tarfile.open(path, 'r', fileobj=fileobj)

        for oInfo in tf:
            if verbose: print oInfo.name

            if oInfo.isfile():
                strFile = oInfo.name
                if indir is not None:
                    strFile = os.path.join(indir, strFile)

                try:
                    makedirs(dirname(strFile))
                except:
                    pass

                open(strFile, "wb").write(tf.extractfile(oInfo).read())
    else:
        flags = "xf"
        if path.endswith(".tar.gz") or path.endswith(".tgz"):
            flags += "z"
        elif path.endswith(".tar.bz2"):
            flags += "j"

        if verbose:
            flags += "v"
        run(['tar', flags, path])

def wget_cached(filename, size, url):
    'wget a url, unless filename with size already exists'

    if not downloaded(filename, size):
        wget(url)
    else:
        inform('Already downloaded:', filename)

    assert os.path.isfile(filename), filename

def mkdirs(p):
    'Recursively make directory path p unless it already exists.'
    if not os.path.exists(p):
        inform('making directory %r' % p)
        os.makedirs(p)

def locate(pattern, root = None):
    if root is None:
        root = os.getcwd()

    for path, dirs, files in os.walk(root):
        for filename in (os.path.abspath(pathjoin(path, filename)) for filename in files if fnmatch.fnmatch(filename, pattern)):
            yield filename

def filerepl(filename, old, new):
    '''
    Replaces all instances of the string "out" with the string "new" in the
    specified file.
    '''
    with open(filename, 'rb') as fin:
        inbytes = fin.read()
    outbytes = inbytes.replace(old, new)
    if outbytes != inbytes:
        with open(filename, 'wb') as fout:
            fout.write(outbytes)
        return True

#
# on windows, we build a custom optimized Python. using the "dpy" function
# to run python scripts ensures that this custom Python is the one used to
# launch.
#
# on platforms where we're using stock python, it just calls "python"
#
if False and os.name == 'nt':
    def dpy(cmd, platlib = False, addenv=None):
        PYTHON_EXE = os.environ.get('PYTHON_EXE')
        PYTHON_VER = os.environ.get('PYTHON_VER')
        if PYTHON_EXE is None:
            try:
                from build_python import PYTHON_EXE, PYTHON_VER
            except ImportError:
                sys.path.append(os.path.abspath(pathjoin(__file__, '../../msw')))
                from build_python import PYTHON_EXE, PYTHON_VER

        env = python_env(platlib, addenv=addenv)
        return run(['python'] + cmd, env=env)
        if PYTHON_VER == '25':
            # some hacks to get Python 2.5's distutils to build with MSVC2008.
            env.update(DISTUTILS_USE_SDK='1',
                       MSSdk='1')

        run([PYTHON_EXE] + cmd, env=env)

    import distutils.msvccompiler

    def list_repl(l, old, new):
        if old in l:
            l.remove(old)
            l.append(new)

    def initialize(self, old_init=distutils.msvccompiler.MSVCCompiler.initialize):
        # also on windows, hack distutils to use /EHsc instead of /GX (which is
        # deprecated)
        res = old_init()
        list_repl(self.compile_options, '/GX', '/EHsc')
        list_repl(self.compile_options_debug, '/GX', '/EHsc')
        return res

    distutils.msvccompiler.MSVCCompiler.initialize = initialize


else:
    def dpy(cmd, platlib = False):
        run(['python'] + cmd, env=python_env(platlib))

def python_env(platlib = False, addenv=None):
    '''
    Returns an environment mapping for running DPython.

      platlib: Add DEPS_DIR to PYTHONPATH if True
    '''

    env = dict(os.environ)

    if platlib:
        env['PYTHONPATH'] = os.path.pathsep.join([env.get('PYTHONPATH', ''), DEPS_DIR])

    if addenv is not None:
        env.update(addenv)

    return env

def copytree_filter(src, dst, symlinks=False, filefilter=None, only_different = False):
    '''
    Copies a tree of files, testing an optional predicate function (filefilter)
    against each file. If the predicate returns True, the file is copied.
    '''
    from shutil import Error, copy2, copystat

    if filefilter is None:
        filefilter = lambda filename: True

    if only_different:
        copy_func = copy_different
    else:
        def copy_func(src, dest):
            print 'copy', src, '->', dst
            return copy2(src, dest)

    names = os.listdir(src)
    if not os.path.isdir(dst):
        os.makedirs(dst)
    errors = []
    for name in names:
        srcname = pathjoin(src, name)
        dstname = pathjoin(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree_filter(srcname, dstname, symlinks, filefilter)
            else:
                if filefilter(srcname):
                    copy_func(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error, err:
            errors.extend(err.args[0])

    if platformName == 'win':
        try:
            copystat(src, dst)
        except WindowsError:
            pass # can't copy file access times on Windows
        except OSError, why:
            errors.extend((src, dst, str(why)))
    else:
        try:
            copystat(src, dst)
        except OSError, why:
            errors.extend((src, dst, str(why)))

    if errors:
        raise Error, errors

def _hash_file(hashobj, fileobj, chunksize = 1024):
    read, update = fileobj.read, hashobj.update
    chunk = read(chunksize)
    while chunk:
        update(chunk)
        chunk = read(chunksize)

def md5_file(f, hex = False):
    with open(f, 'rb') as fobj:
        md5obj = hashlib.md5()
        _hash_file(md5obj, fobj)

    return md5obj.hexdigest() if hex else md5obj.digest()

def files_different(src, dest):
    from os.path import isfile, split as pathsplit, getsize, isdir

    srcparent, destparent = pathsplit(src)[0], pathsplit(dest)[0]

    # TODO: mtime?
    if not isdir(srcparent) or not isdir(destparent):
        return True
    if not isfile(src) or not isfile(dest):
        return True
    if getsize(src) != getsize(dest):
        return True

    if md5_file(src) != md5_file(dest):
        return True

    return False

def copy_with_prompt(src, dest):
    '''
    Tries to copy src to dest.

    If an IOError is raised, prompt for a retry. (This helps greatly when copying
    binaries on Windows that might be running.)
    '''
    try_again = True
    while try_again:
        try:
            shutil.copy2(src, dest)
        except IOError, e:
            print e
            inp = raw_input('Retry? [Y|n] ')

            if inp and not inp.lower().startswith('y'):
                raise SystemExit(1)
            else:
                try_again = True
        else:
            try_again = False

def copy_different(src, dest, prompt_on_deny = True, destname=None):
    '''
    Copy src to dest, but only if it is different (the files are hashed).

    If prompt_on_deny is True, a prompt will occur on an IOError (like copy_with_prompt).
    '''
    if not os.path.isfile(src):
        raise AssertionError(src + " not found, cwd is " + os.getcwd())

    srcname = os.path.split(src)[1]
    if os.path.isdir(dest):
        dest = pathjoin(dest, srcname if destname is None else destname)

    if files_different(src, dest):
        inform('* %s -> %s' % (srcname, dest))

        copy_with_prompt(src, dest)
    else:
        inform('X %s -> %s (skipped)' % (srcname, dest))
