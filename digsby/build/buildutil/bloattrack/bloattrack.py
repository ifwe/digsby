import os.path
import sys
import json
import subprocess
import re
from cache import file_contents, cache

thisdir = os.path.abspath(os.path.dirname(__file__))
SIZER_EXE = os.path.join(thisdir, 'sizer', 'Sizer.exe')

def run(*args):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        print >> sys.stderr, stderr
        raise Exception('Error running %r' % (args,))
    return stdout

if os.name == 'nt':
    import ctypes
    UnDecorateSymbolName = ctypes.windll.dbghelp.UnDecorateSymbolName
    N = 1000
    _outstr = ctypes.create_string_buffer(N)
    def unmangle(symbol):
        if not UnDecorateSymbolName(symbol, ctypes.byref(_outstr), N, 0):
            raise ctypes.WinError()
        return _outstr.value

def get_win32_symbols(filepath):
    assert os.path.isfile(SIZER_EXE)
    return cache(lambda: run(SIZER_EXE, filepath),
            dirname='symanalysis',
            hashelems=('get_win32_symbols',
                file_contents(SIZER_EXE),
                file_contents(filepath)))['val']

# pattern for matching dumpbin /EXPORTS output
dumpbin_export_pattern = re.compile('''\s*
                       (?P<ordinal>\d+) \s+
                       (?P<hint>\S+) \s+
                       (?P<rva>\S+) \s+
                       (?P<symbol>\?\S+)
                       ''', re.VERBOSE)

# sizer.exe output matcher
sizer_export_pattern = re.compile('''
    (?P<size>\d+) \s+
    (?P<symbol>\S+) \s+
    (?P<file>\S+)
''', re.VERBOSE)

def parse_sizer(sizer_output):
    datatype = None
    for line in sizer_output.split('\n'):
        line = line.strip()
        if not line:
            continue

        if line == 'CODE:':
            datatype = 't'
        elif line == 'DATA:':
            datatype = 'd'
        else:
            m = sizer_export_pattern.match(line)
            if m is not None:
                assert datatype is not None
                yield m.group('symbol'), datatype, int(m.group('size')), m.group('file')
            else:
                print >> sys.stderr, 'warning: ignoring line %r' % line

def json_tree(binary):
    import bloat
    dirs = bloat.treeify_syms(parse_sizer(get_win32_symbols(binary)))

    json_txt = 'var kTree = ' + json.dumps(bloat.jsonify_tree(dirs, '/'), indent=2)
    return json_txt

def json_for_svn_url(url, rev):
    from svntools import svn_download
    info = svn_download(url, rev)
    local_file = info['path']
    assert os.path.isfile(local_file), 'file was not created: %r' % local_file
    lowerurl = url.lower()
    if lowerurl.endswith('.dll') or lowerurl.endswith('.exe'):
        svn_download(url[:-4] + '.pdb')

    return dict(json=json_tree(local_file), rev=info['rev'])

def main():
    binary = sys.argv[1]
    json_txt = json_tree(binary)
    open(os.path.join(thisdir, 'demo.json'), 'wb').write(json_txt)

if __name__ == '__main__':
    main()

