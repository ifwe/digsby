#__LICENSE_GOES_HERE__
import babel_mod.babelgen_ext
from util.primitives.mapping import odict
import babel.messages.pofile as pofile
import argparse
write_po = pofile.write_po
from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import read_po
from genargspec import get_argspec
from path import path
import sys
import os.path

thisdir = path(__file__).abspath().dirname()
DIGSBYROOT = thisdir.parent.normpath()
sys.path.insert(0, thisdir)
sys.path.insert(0, DIGSBYROOT / 'build')

import buildutil

import mkappfill
import mki18n
import langtools
from path import path

# directories with code containing strings to be translated.
SOURCE_DIRS = [DIGSBYROOT / p for p in [
    'src',
    'ext/src',
]]

YAML_SOURCE_DIRS = [DIGSBYROOT / p for p in [
    'src',
    'ext/src',
    'res',
]]

DOMAIN = 'digsby'

def download_i18n_tools():
    pass

def check_for_i18n_tools():
    def _check():
        stdout = buildutil.run(['xgettext'],
                expect_return_code=1,
                capture_stdout=True,
                include_stderr=True)
        if not 'no input file given' in stdout:
            raise Exception('unexpected output')

    try:
        _check()
    except Exception:
        dir = os.path.abspath(langtools.download_i18n_tools())
        assert os.path.isdir(dir), dir
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + dir
        _check()

MO_DIR = None # default ./locale
PO_DIR = DIGSBYROOT / 'devplugins' / 'l33t_language'
POT_DIR = DIGSBYROOT / 'i18n' / 'templates'
TEMP_DIR = DIGSBYROOT / 'i18n' / 'temp'
if not POT_DIR.isdir():
    POT_DIR.makedirs()
if not TEMP_DIR.isdir():
    TEMP_DIR.makedirs()

def POT_path(name):
    return os.path.join(POT_DIR, name, name + '.pot')

def PO_path(name, lang):
    return os.path.join(POT_DIR, name, name + '-' + lang + '.po')

def TEMP_path(name):
    return os.path.join(TEMP_DIR, name)

FIL_PATH = TEMP_path('app.fil')
FIL_SIP_PATH = TEMP_path('appsip.fil')
FIL_YAML_PATH = TEMP_path('appyaml.fil')
FIL_TENJIN_PATH = TEMP_path('apptenjin.fil')

def rename_new_pofiles(POT_DIR):
    with buildutil.cd(POT_DIR):
        for p in path('.').files('*.po.new'):
            pofile = path(p.namebase)
            if pofile.isfile():
                oldfile = pofile+'.old'
                if oldfile.isfile():
                    oldfile.remove()
                print 'renaming', pofile, 'to', pofile+'.old'
                pofile.rename(pofile + '.old')
            print 'renaming', p, 'to', pofile
            p.rename(pofile)

def yield_translatable_yaml_strings(filename):
    # TODO: this is a hack. how can we construct a syck loader that retains line number information?
    import re
    pattern = re.compile(r'''\!N?\_ +?("|')((?:.+?)[^\\])(?:\1)''')
    for lineno, line in enumerate(open(filename, 'rb').readlines()):
        m = pattern.search(line)
        if m is not None:
            if line.lstrip().startswith('#'): # skip comments
                continue

            text = m.group(2).strip()
#            if (text.startswith('"') and text.endswith('"')) or \
#               (text.startswith("'") and text.endswith("'")):
#                text = text[1:-1]

            yield text, lineno

def xgettext_yaml(filelist, outputfilename):
    output = open(outputfilename, 'wb')
    print output, outputfilename
    cat = Catalog()
    for f in open(filelist, 'rb').readlines():
        f = f.strip()
        assert os.path.isfile(f), f
        for s, lineno in yield_translatable_yaml_strings(f):
            cat[s] = Message(s, locations=[(f, lineno)])
    write_po(output, cat, width=None, sort_by_file=True)

header_comment = '''\
# Translations for the Digsby client.
# Copyright (C) 2011 dotSyntax, LLC
# This file is distributed under the BSD License.
#
# TOS for Digsby is located at http://www.digsby.com/tos.php
#
'''

HEADER = [
#    '--package-name', 'digsby',
#    '--msgid-bugs-address', 'https://translations.launchpad.net/digsby',
#    '--copyright-holder', 'dotSyntax, LLC',
    ]

def KEYWORDS():
    return ['--keyword=' + spec for spec in \
            (get_argspec()
             + [
                '_',
                'N_',
                ]
             )
           ]

def xgettext(input_file, output_file, *args):
    buildutil.run(['xgettext',
                   ]
                   + HEADER
                   + KEYWORDS() + [
                   '--from-code', 'UTF-8',
                   '--no-wrap', '--add-comments=Translators:'] +
                   list(args) +
                   ['--files-from', input_file,
                   '--output', output_file])

def pot_read_clean(f):
    from analyze import remove_template_problems
    cat = read_po(remove_template_problems(f))
    write_pot(f, cat)
    return cat

def write_pot(f, cat, version=False):
    cat.header_comment = header_comment
    cat.fuzzy = False
    cat.project = 'digsby'
    cat.version = '$Rev$'
    cat.msgid_bugs_address = 'https://translations.launchpad.net/digsby'
    cat.copyright_holder = 'dotSyntax, LLC'

    for m in cat:
        m.locations = sorted(m.locations)
    cat._messages = odict(sorted(cat._messages.iteritems(), key = lambda x: x[1].locations))
    if version:
        cat.add('__version__', auto_comments=['$Rev$'], context='__metadata__')
    return write_po(open(f, 'w'), cat, width=None)

class All(argparse.Action):
    def __call__(self, parser, ns, value, option_string):
        all = value or not any((ns.po, ns.mo, ns.appfil))
        print 'running All:', all
        ns.all = all
        if all:
            Appfil(None, None)(None, self, True, None)
            Po(None, None)(None, self, True, None)
            Mo(None, None)(None, self, True, None)

class Appfil(argparse.Action):
    def __call__(self, parser, ns, value, option_string):
        if not value:
            return
        print 'running Appfil', id(self)
        # TODO: instead of N walks over the filesystem tree, do one walk, with multiple visitors
        mkappfill.generate_fil_file(FIL_PATH, SOURCE_DIRS)
#        mkappfill.generate_fil_file(FIL_SIP_PATH, SOURCE_DIRS, extensions=['.sip'])
        mkappfill.generate_fil_file(FIL_YAML_PATH, YAML_SOURCE_DIRS, extensions=['.yaml'])
        mkappfill.generate_fil_file(FIL_TENJIN_PATH, SOURCE_DIRS, extensions=['.tenjin', '.py.xml'])

class Po(argparse.Action):
    def __call__(self, parser, ns, value, option_string):
        if not value:
            return
        print 'running Po', id(self)
        with buildutil.cd(DIGSBYROOT):
            default_pot = TEMP_path('digsby_default.pot')
            sip_pot = TEMP_path('digsby_sip.pot')
            yaml_pot = TEMP_path('digsby_yaml.pot')
            tenjin_pot = TEMP_path('digsby_tenjin.pot')
            input_pots = [default_pot, sip_pot, yaml_pot, tenjin_pot]
            final_pot = POT_path('digsby')
            for pot in input_pots:
                if os.path.isfile(pot):
                    os.remove(pot)

            xgettext(FIL_PATH, default_pot)
#            xgettext(FIL_SIP_PATH, sip_pot, '-C')
            xgettext_yaml(FIL_YAML_PATH, yaml_pot)
            xgettext(FIL_TENJIN_PATH, tenjin_pot, '-L', 'python')

            input_pots = filter(lambda pot: os.path.isfile(pot), input_pots)

            cat = pot_read_clean(input_pots[0])
            for potfile in input_pots[1:]:
                cat_u = pot_read_clean(potfile)
                for msg in cat_u:
                    cat[msg.id] = msg
            write_pot(final_pot, cat, version=True)

            pofiles = [os.path.join(PO_DIR, f) for f in os.listdir(PO_DIR) if f.endswith('.po')]
            for pofile in pofiles:
                buildutil.run(['msgmerge', '-F', '--no-wrap',
                    pofile, final_pot, '-o', pofile])
#            for potfile in input_pots:
#                os.remove(potfile)

class Mo(argparse.Action):
    def __call__(self, parser, ns, value, option_string):
        if not value:
            return
        print 'running Mo', id(self)
        mki18n.makeMO(DIGSBYROOT, MO_DIR, DOMAIN, True, poDir=PO_DIR)

def arguments():
    import argparse
    parser = argparse.ArgumentParser(description='i18n template builder')
    group = parser.add_argument_group()
    group.add_argument('--all', action=All, nargs='?', const=True, default=False)
    group.add_argument('-a', '--appfil', action=Appfil, nargs='?', const=True)
    group.add_argument('-p', '--po',     action=Po, nargs='?', const=True)
    group.add_argument('-m', '--mo',     action=Mo, nargs='?', const=True)
    return parser.parse_args()

def coalesce():
    default_pot = PO_path('digsby_default', 'tr')
    sip_pot = PO_path('digsby_sip', 'tr')
    yaml_pot = PO_path('digsby_yaml', 'tr')
    tenjin_pot = PO_path('digsby_tenjin', 'tr')
    input_pots = [default_pot, sip_pot, yaml_pot, tenjin_pot]
    final_pot = POT_path('digsby')
    final_po = PO_path('digsby', 'tr')
    input_pots = filter(lambda pot: os.path.isfile(pot), input_pots)
    from analyze import remove_template_problems
    cat = read_po(remove_template_problems(final_pot))
    for potfile in input_pots:
        cat_u = read_po(open(potfile))
        for msg in cat_u:
            new = msg.string
            if msg.id in cat:
                cat[msg.id].string = new
    write_po(open(final_po, 'w'), cat, width=77, sort_by_file=False)

def main():
    origdir = os.getcwd()
    os.chdir(DIGSBYROOT)
    try:
        check_for_i18n_tools()
        arguments()
#        coalesce()
    finally:
        os.chdir(origdir)

if __name__ == '__main__':
    main()

