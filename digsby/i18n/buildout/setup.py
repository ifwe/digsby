#__LICENSE_GOES_HERE__
# -*- coding: utf-8 -*-
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from path import path
import sys
import zipfile
import syck
import babel
from package import cd
from util.net import wget
import traceback

sys.path.append('..')
import argparse
from babel_mod import babelgen_ext
sys.path.append('../../build')
from buildutil.buildfileutils import tardep

bzr = tardep(url='http://launchpad.net/bzr/2.3/2.3.1/+download/',
             tar='bzr-2.3.1',
             ext='.tar.gz',
             size=7026390,
             md5='1a4367ce59a2880f321ecb882e195856')

try:
    import bzrlib
except ImportError:
    sys.path.append('./' + bzr.dirname)
    try:
        import bzrlib
    except ImportError:
        bzr.get()
        import bzrlib
import bzrlib.workingtree

def scan_po(dir):
    for p in path(dir).walk('*.po'):
        domain = p.parent.basename()
        locale = p.namebase
        yield domain, locale, p

def read_pos(dir):
    for domain, locale, pofile in scan_po(dir):
        with pofile.open('r') as f:
            yield domain, locale, pofile, read_po(f)#, domain=domain, locale=locale)

def versioned_pos(dir):
    for domain, locale, pofile, catalog in read_pos(dir):
        version_message = catalog.get('__version__', '__metadata__')
        if version_message:
            for c in version_message.auto_comments:
                if c.startswith('$Rev: '):
                    yield domain, locale, pofile, catalog, c[len('$Rev: '):-len(' $')]
                    break

def enumerate_revisions(src):
    wt = bzrlib.workingtree.WorkingTree.open_containing(src)[0]
    b = wt.branch
    wt.lock_read()
    basis_tree = wt.basis_tree()
    basis_tree.lock_read()
    revisions = {}
    revnos = {}
    try:
        for info in basis_tree.list_files(include_root=True):
            rev_id = info[-1].revision
            if rev_id not in revnos:
                revnos[rev_id] = b.revision_id_to_revno(rev_id)
            revno = revnos[rev_id]
            revisions[path(info[0]).expand()] = (rev_id, revno)
    finally:
        basis_tree.unlock()
        wt.unlock()
    return revisions

def info_yaml(feature, domain, locale):
    d = {}
    d['type'] = 'lang'
    d['language'] = locale.split('_')[0]
#    d['country'] = resolve alias
    d['shortname'] = '-'.join([feature, domain, locale])
#    d['name'] = '-'.join()
    d['name'] = d['shortname']
    d['domain'] = domain
    return d

INFOYAML = 'info.yaml'
ZIP_DIST = ['zip']

def httprelpath(pth):
    return '/'.join(['.'] + pth.splitall()[1:])

'''
how do we encode the catalog for distribution?
we only need to arrive at a valid Translations class,
since that is where all translations are coming from.
we have the routines for turning po-files into mo-files
and mo-files into Translations instances, so we can definitely
go directly from po to Translations
Advantage to using POs:
    no extra step/extra file.
    user can edit.  (good for translators)
Disadvantage:
    Slower.  Significantly? unlikely.
    user can edit.  (bad for users)
Possible Solution:
    Build both, potentially give translators the fast path.
    Will also allow Digsby to run updated translations w/o compile.
    ^probably good for devs.
'''
def run(args):
    src = path(args.src)
    revs = enumerate_revisions(src)
    dist = path(args.dist)

    feature_pth = dist / args.feature

    from StringIO import StringIO
    from collections import defaultdict
    from util.primitives.structures import oset
    versions = oset()
    groups = defaultdict(list)
    for domain, locale, pofile, catalog, template_version in versioned_pos('.'):
        versions.add(template_version)
        groups[template_version].append((domain, locale, pofile, catalog))

    for template_version in versions:
        plugins = {}
        template_root = feature_pth / template_version
        for domain, locale, pofile, catalog in groups[template_version]:
            revid, revno = revs[src.relpathto(pofile).expand()]
            out_zip = template_root / locale / '-'.join([domain, template_version, locale, str(revno)]) + '.zip'
            if not out_zip.parent.isdir():
                out_zip.parent.makedirs()
            mobuf = StringIO()
            write_mo(mobuf, catalog)
            zbuf = StringIO()
            z = zipfile.ZipFile(zbuf, 'w', zipfile.ZIP_DEFLATED)
            z.writestr('-'.join([domain, locale]) + '.mo', mobuf.getvalue())
            infoyaml = info_yaml(args.feature, domain, locale)
            try:
                infoyaml['name'] = u'%s (%s)' % (babel.Locale(locale).get_display_name('en'),
                                                 babel.Locale(locale).get_display_name(locale))
            except Exception:
                pass
            infoyaml['pot_version'] = template_version
            infoyaml['bzr_revno'] = revno
            infoyaml['bzr_revid'] = revid
            infoyaml['catalog_format'] = 'mo'
            infoyaml_bin = syck.dump(infoyaml)
            z.writestr(INFOYAML, infoyaml_bin)
            z.close()
            zout = zbuf.getvalue()
            with out_zip.open('wb') as out:
                out.write(zout)
            infoyaml_pth =(out_zip.parent/INFOYAML)
            with infoyaml_pth.open('wb') as infoyaml_out:
                infoyaml_out.write(infoyaml_bin)
            plugins[infoyaml['shortname']] = dict(
                                                  meta = httprelpath(template_root.relpathto(infoyaml_pth)),
                                                  dist_types = ZIP_DIST,
                                                  zip = dict(
                                                             location = httprelpath(template_root.relpathto(out_zip))
                                                             )
                                                  )
        idxyaml = template_root / 'index.yaml'
        idxbin = syck.dump(dict(plugins=plugins))
        with idxyaml.open('wb') as idx_out:
            idx_out.write(idxbin)
    update_pth = feature_pth / 'update.yaml'
    with open(update_pth, 'wb') as update_out:
        update_out.write(syck.dump({'all':{'release':httprelpath(feature_pth.relpathto(idxyaml))}}))
    try:
        site_d = syck.load(wget('http://s3.amazonaws.com/update.digsby.com/' + dist.name + '/site.yaml'))
    except Exception:
        traceback.print_exc()
        site_d = {}
    try:
        featurs = site_d['features']
    except KeyError:
        featurs = site_d['features'] = {}
    featurs[args.feature]= {
                           'name':args.name,
                           'url': httprelpath(dist.relpathto(update_pth)),
                           }
    with open(dist / 'site.yaml', 'wb') as site_out:
        site_out.write(syck.dump(site_d))
#    with cd(dist.parent):
#        import package
#        package.upload_dir_to_s3(dist.name,
#                                 compress = False,
#                                 mimetypes = True)

class Src(argparse.Action):
    def __call__(self, parser, ns, value, option_string):
        if not path(value).isdir():
            raise argparse.ArgumentError(self, '{path!r} is not a valid path, try "bzr co lp:~/digsby/digsby/translation-export {path!s}"'.format(path=value))
        ns.src = value

def arguments():
    parser = argparse.ArgumentParser(description='i18n catalog compiler')
    parser.add_argument('--dist', action='store', nargs='?', default='dist')
    parser.add_argument('--src', action=Src, nargs='?', default='translation-export')
    parser.add_argument('--feature', action='store', default='digsby-i18n')
    parser.add_argument('--name', action='store', default="Digsby Internationalization")
    return parser.parse_args()

if __name__ == '__main__':
    import sys
    sys.argv.extend(['--dist', 'D:\\digsby-1_0_0'])
    args = arguments()
    run(args)
