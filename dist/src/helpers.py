from path import path
import os
import re
import logging
log = logging.getLogger('helpers')
import subprocess
from contextlib import contextmanager

def run(*args, **kwargs):
    """Execute the command.

    The path is searched"""
    verbose = kwargs.get("verbose", True)
    args = map(str, args)
    if verbose:
        log.debug('run: args = %r', args)

    if not verbose:
        popen_kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    else:
        popen_kwargs = {}

    p = subprocess.Popen(args, **popen_kwargs)

    stdout, stderr = p.communicate()

    if verbose:
        log.debug('run: stdout = %r', stdout)
        log.debug('run: stderr = %r', stderr)
        log.debug('run: status = %r', p.returncode)

    if p.returncode:
        if not verbose:
            logging.debug('run: args = %r', args)
            logging.debug('run: status = %r', p.returncode)
        raise Exception("The command failed")

    return stdout

def clean(dirs):
    """Remove temporary directories created by various packaging tools"""
    for d in dirs:
        if d.isdir():
            d.rmtree()

def dosubs(subs, infile, outfile=None):
    """Performs substitutions on a template file or string

    @param infile:  filename to read or string
    @param outfile: filename to write result to or None if infile is a string
    @type subs: dict
    @param subs: the substitutions to make
    """
    if outfile is None:
        stuff=infile
    else:
        stuff=open(infile, "rt").read()

    for k in subs:
        stuff=re.sub("%%"+k+"%%", "%s" % (subs[k],), stuff)

    if outfile:
        open(outfile, "w").write(stuff)
    else:
        return stuff

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
        logging.info(msg)

@contextmanager
def cd(*pth):
    '''
    chdirs to path, always restoring the cwd

    >>> with cd('mydir'):
    >>>     do_stuff()
    '''
    original_cwd = os.getcwd()
    try:
        new_cwd = path.joinpath(*pth)
        #inform('cd %s' % os.path.abspath(new_cwd))
        os.chdir(new_cwd)
        yield
    finally:
        #inform('cd %s' % os.path.abspath(original_cwd))
        os.chdir(original_cwd)

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    instead of `obj['foo']`. Create one by doing `storage({'a':1})`.

    Setting attributes is like putting key-value pairs in too!

    (Thanks web.py)
    """
    def __getattr__(self, key, ga = dict.__getattribute__, gi = None):
        try:
            return ga(self, key)
        except AttributeError:
            try:
                if gi is not None:
                    return gi(self, key)
                else:
                    return self[key]
            except KeyError:
                msg = repr(key)
                if len(self) <= 20:
                    keys = sorted(self.keys())
                    msg += '\n  (%d existing keys: ' % len(keys) + str(keys) + ')'
                raise AttributeError, msg

    def __setattr__(self, key, value):
        self[key] = value

    def copy(self):
        return type(self)(self)


disallowed_extensions = [e.lower() for e in
    ['.py', '.pyc', '.cpp', '.c', '.h', '.erl', '.hrl', '.php', '.cs', '.pl', '.gitignore']]

def check_no_sources(distdir):
    'Make sure there are no source files in distdir.'


    for root, dirs, files in os.walk(distdir):
        for file in files:
            for ext in disallowed_extensions:
                if file.lower().endswith(ext):
                    raise AssertionError('found a %s file in %s: %s' % (ext, distdir, os.path.join(root, file)))
