#__LICENSE_GOES_HERE__
# -*- coding: utf-8 -*-
from generate_monolithic import xgettext
from mkappfill import generate_fil_file
from path import path
import os
import shutil
from babel.messages.pofile import read_po

root = path(__file__).parent.parent
os.chdir(root)
paths = {
         'ext/src':{'cmd':'walkfiles',
                    'ignore':['src\\generated']},
         'src/':'files',
         'src/plugins':{'cmd':'walkdirs',
                        'ignore':['.svn']},
         'src':{'cmd':'walkdirs',
                'ignore':['src\\plugins', '.svn']},
         'res':{'cmd':'walkfiles'}
         }

def walkfiles(pth, ignore, exts):
    root = path(__file__).parent.parent
    pthin = (root / pth).abspath().normpath()
    pthout = path(__file__).parent / 'segments' / pth
    if not pthout.isdir():
        pthout.makedirs()
    fil = (pthout / 'app.fil').abspath().normpath()
    generate_fil_file(fil, [pthin])
    outfile =fil.parent / (fil.parent.name + '.pot')
    xgettext(fil, outfile, '--omit-header')

def files(pth, ignore, exts):
    print 'files', pth

segments = (path(__file__).parent / 'segments')
if False:
    shutil.rmtree(segments, True)

    for pth, val in paths.items():
        pthin = (root / pth).abspath().normpath()
        if isinstance(val, basestring):
            cmd = val
            ignore = []
        else:
            cmd = val['cmd']
            ignore = val.get('ignore', [])

        if cmd == 'walkfiles':
            walkfiles(pth, ignore, None)
        elif cmd == 'walkdirs':
            for dpth in path(pthin).dirs():
                for ign in ignore:
                    if ign in dpth:
                        break
                else:
                    walkfiles(root.relpathto(dpth), ignore, None)
                continue
        elif cmd == 'files':
            files(pth, ignore, ['.py'])

for file in segments.walkfiles('*.pot'):
    print file
    catalog = read_po(file.open())
    for key, message in catalog._messages.items():
        print repr(key), repr(message.string)
    break
