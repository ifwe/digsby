from __future__ import with_statement, division
from util import soupify, httpjoin, autoassign, httpok
from util.cacheable import urlcacheopen
from path import path
import subprocess
import os

import tarfile, shlex


import logging
log = logging.getLogger('spellchecker')

class AspellDictionary(object):
    def __init__(self, id, name_english, name_native):
        autoassign(self, locals())

    def __repr__(self):
        return '<%s id=%s name=%s(%r)>' % (type(self).__name__, self.id, self.name_english,self.name_native)

    @property
    def name_description(self):
        return self.name_english

class RemoteAspellDictionary(AspellDictionary):
    ROOT = 'http://ftp.gnu.org/gnu/aspell/dict/'
    def __init__(self, id, n_e, n_n, dict_dir, dict_path):
        AspellDictionary.__init__(self, id, n_e, n_n)

        self.directory = dict_dir
        self.package_path = dict_path
        self.digest_location = dict_path + '.sig'

        self.sig = None
        self.needs_update = True

    def fetch_sig(self, root=None):
        '''
        Fetches the .sig file for the remote dictionary file. Returns True if successful, else False.
        If successful, sets _needs_update to be True if the file has changed (that is, if it was fetched
        from the server and not the local cache).
        '''
        if self.sig is None:
            response, content = urlcacheopen(self.get_digest_location(root))
            if not response.ok:
                return False

            self.sig = content
            self.needs_update = not response.fromcache

        return True

    def clear_sig(self, root=None):
        '''
        Clear the signature out of the cache. useful if you tried to update a dictionary
        but the download failed.
        '''

    def get_package_path(self, root=None):
        return httpjoin(root or self.ROOT, self.package_path)

    def get_digest_location(self, root=None):
        return self.get_package_path(root) + '.sig'

    def get_directory(self, root=None):
        return httpjoin(root or self.ROOT, self.directory)

    def __repr__(self):
        return AspellDictionary.__repr__(self)[:-1] + (' url=%s>' % self.package_path)

class LocalAspellDictionary(AspellDictionary):
    def __init__(self, id, n_e, n_n, signame):
        AspellDictionary(self, id, n_e, n_n)
        self.signame = signame

def AspellIndexToYaml(root=None, outfile=None):
    import syck

    index = _GetAspellIndex(root)
    mydict = {}
    def RAD_to_dict(rad):
        res = {}
        if rad.name_native is not None:
            res.update(name_native=rad.name_native.encode('utf-8'))
        res.update(name_english=rad.name_english.encode('utf-8'), location=rad.package_path.encode('utf-8'))
        return res

    for d in index:
        mydict[d.id.encode('utf-8')] = RAD_to_dict(d)

    return syck.dump(mydict, outfile)

def _GetAspellIndex(root=None):
    RAD = RemoteAspellDictionary
    response, content = urlcacheopen(httpjoin(root or RAD.ROOT,'0index.html'), decode=False)

    if not response.ok:
        print 'Unhandled HTTP response code: %r' % response
        return ()

    soup = soupify(content)
    results = {}
    for row in soup.find('a', attrs=dict(name='0.50')).findAllNext('tr'):
        contents = row.findAll('td')
        if len(contents) == 4:
            id, name_english, name_native, dictionary_path = contents
            id = id.find(href=True)

            if id is None:
                continue

            id = id['href']
            if id not in results:
                dictionary_path = dictionary_path.find(href=True)
                if dictionary_path is None:
                    continue
                dictionary_path = dictionary_path['href']

                name_english = name_english.renderContents(None).decode('xml')
                name_native = name_native.renderContents(None).decode('xml').strip() or None
                results[id] = RAD(id, name_english, name_native, id, dictionary_path)

    return results.values()

def DownloadAllDictionaries(infodict, towhere, root=None):

    if root is None:
        root = RemoteAspellDictionary.ROOT

    for id in infodict:
        name = infodict[id]['name_english']
        bz2path = infodict[id]['location']

        localpath = path(towhere) / bz2path
        bz2path = httpjoin(root,bz2path)

        localpath = localpath.expand()

        print ('Downloading %s (%s) from %s to %s... ' % (name, id, bz2path, localpath)),
        response, content = urlcacheopen(bz2path)
        print response.reason
        if response.ok:
            if not localpath.parent.isdir():
                localpath.parent.makedirs()

            with open(localpath, 'wb') as f:
                f.write(content)

def ExtractInfoFiles(localroot):

    localroot = path(localroot)
    for bz2path in localroot.walkfiles('*.tar.bz2'):
        tar = None
        infofile = None
        try:
            tar = tarfile.open(bz2path, 'r:bz2')

            for member in tar.getmembers():
                mempth = path(member.name)
                if mempth.name == 'info':
                    break
            else:
                print 'Couldn\'t get "info" from %s' % bz2path
                continue
            infofile = tar.extractfile(member)
            with open(bz2path.parent/'info', 'wb') as f:
                f.write(infofile.read())
        finally:
            if tar is not None:
                tar.close()
            if infofile is not None:
                infofile.close()

class AspellInfoShlexer(shlex.shlex):
    def __init__(self, *a, **k):
        if 'posix' not in k:
            k['posix'] = True
        shlex.shlex.__init__(self, *a, **k)
        self.whitespace_split = True

    def get_token(self):
        curlineno = self.lineno
        token = shlex.shlex.get_token(self)
        if self.lineno != curlineno:
            self.pushback.append('\n')
        return token

def GetAliases(root, id):
    aliases = []
    root = path(root)
    with open(root/id/'info') as info:
        for line in info:
            line = line.rstrip() # chomp newline
            if line.startswith('alias'):
                _alias, rest = line.split(None, 1)

                rest = rest.split()
                alias_id, alias_names = rest[0], rest[1:]
                if alias_id != id:
                    aliases.append((alias_id, alias_names))

    return aliases

def GetAllAliases(root):
    root = path(root)
    aliases = {}
    for lang in root.walkdirs():
        lang = lang.name
        aliases = GetAliases(root, lang)
        if aliases:
            print lang, aliases

    return aliases

def _getshlexer(fpath):
    f = open(fpath, 'rb')
    return AspellInfoShlexer(f)

def MakeDigsbyDict(lang='en', local_dir=None):
    """
        Create a custom wordlist of common IM slang
    """
    digsby_words = set(('asap', 'asl', 'bbs', 'bff', 'brb', 'btw', 'cya',
                        'digsby', 'fud', 'fwiw', 'gl', 'ic', 'ily', 'im',
                        'imho', 'irl', 'jk', 'lmao', 'lol', 'np', 'oic',
                        'omg', 'plz', 'rofl', 'roflmao', 'thx', 'ttyl',
                        'ttys', 'u', 'wtf'))

    #local_dir

    dict_file = local_dir / ('digsby-%s.rws' % lang)
    cmd = ' '.join(['.\\lib\\aspell\\bin\\aspell.exe',
           '--local-data-dir=%s' % subprocess.list2cmdline([local_dir]), #@UndefinedVariable
           '--lang=%s' % lang,
           'create',
           'master',
           '"%s"' % dict_file])


    if os.name == 'nt':
        import _subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = _subprocess.SW_HIDE
    else:
        startupinfo = None

    from subprocess import Popen, PIPE
    proc = Popen(cmd.encode('filesys'), stdout=PIPE, stderr=PIPE, stdin=PIPE, startupinfo=startupinfo)
    log.info('Creating Digsby dict in "%s"', lang)
    log.info('Executing Command: %s', cmd)

    result = proc.communicate('\n'.join(digsby_words))

    log.info('Subprocess returned: %s', result)

    return dict_file

def _main(*a,**k):
    MakeDigsbyDict(*a,**k)


if __name__ == '__main__':
    import sys
    _main(sys.argv[1:])
