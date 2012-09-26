import sys
from bloattrack import run
from cache import cache
import os.path

binary_checkout_dir = '.bloatbins'

def svn(*args):
    return run(*('svn',) + args)

class Changeset(object):
    def __repr__(self):
        return '<Changeset r%s by %s: %r>' % (self.revision, self.author, self.message[:40])
    def __init__(self, revision, author, message, date):
        self.revision = revision
        self.author = author
        self.message = message
        self.date = date

def checkout_revision(filename, revision):
    run('svn', 'checkout', '--revision', revision, filename)

def _parse_svn_output(colon_sep_key_val_txt):
    info = dict()
    for line in colon_sep_key_val_txt.split('\n'):
        line = line.strip()
        if not line: continue

        index = line.find(':')
        if index == -1: continue

        key, value = line[:index], line[index+2:]
        info[key] = value

    return info

def svn_file_info(url, key=None):
    output = svn('info', url)
    infodict = _parse_svn_output(output)
    if key is not None:
        return infodict[key]
    else:
        return infodict

def url_for_file(local_svn_file):
    return svn_file_info(local_svn_file)['URL']

def log_xml_for_file(local_svn_file):
    url = url_for_file(local_svn_file)
    xml = svn('log', url, '--xml')

    doc = lxml.etree.fromstring(xml)
    revisions = []
    for entry in doc.xpath('//logentry'):
        revision = int(entry.attrib.get('revision'))
        author = entry.findall('author')[0].text
        msg = entry.findall('msg')[0].text
        date = entry.findall('date')[0].text
        revisions.append(Changeset(
            revision=revision,
            author=author,
            message=msg,
            date=date))

    return revisions

def svn_download(url, rev=None):
    if rev is None:
        rev = svn_file_info(url, 'Last Changed Rev')

    def getfile():
        temppath = '.svndownload'
        if os.path.isfile(temppath):
            os.remove(temppath)
        assert not os.path.isfile(temppath)
        svn('export', '-r', rev, url, temppath)
        contents = open(temppath, 'rb').read()
        os.remove(temppath)
        return contents

    urlelems = url.split('/')
    filename = urlelems[-1]
    urldir = '/'.join(urlelems[:-1])

    local_path = cache(getfile,
       dirname='svn',
       hashelems=('export', urldir, rev),
       filename=filename)['path']

    return dict(path=local_path, rev=rev)

def main():
    print svn_download(sys.argv[1])

if __name__ == '__main__':
    main()
