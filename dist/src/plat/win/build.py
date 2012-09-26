import distutils
from path import path
from helpers import clean, dosubs
from . import manifest


def builder(pkg, vals):
    'Do all the steps necessary to make a Windows installer.'
    import py2exe
    defaults = {
        'options': {'py2exe': {'optimize': 2,
                               'compressed': 1,
                               'dist_dir': pkg.repo.dist_prep_root}},
        'windows': [],
        'console': [],
        'script_args': ('py2exe', ),
        'verbose': False,
    }

    opts = pkg.getpy2exeoptions(defaults)

    # add in manifests if not already specified
    w = []
    for i in opts['windows']:
        # insert manifest at begining - user version will override if supplied
        i['other_resources'] = [(manifest.RT_MANIFEST, 1, manifest.WINXP_MANIFEST)] + i.get('other_resources', [])

        # set other values if not provided
        for k, v in (('icon_resources', [(1, pkg.repo.source_root / 'res' / 'digsby.ico')]),
                     ('product_version', '%%VERSION%%'),
                     ('version', '%%DQVERSION%%'),
                     ('comments', '%%COMMENTS%%'),
                     ('company_name', "%%URL%%"),
                     ('copyright', "%%COPYRIGHT%%"),
                     ('name', "%%NAME%%"),
                     ('description', "%%DESCRIPTION%%")):
            if k not in i:
                i[k] = v
        w.append(i)

    opts['windows'] = w

    # fixup vals for any that are missing
    if 'RELEASE' not in vals:
        vals['RELEASE'] = 0
    if 'OUTFILE' not in vals:
        if vals['RELEASE']:
            rstr = '-r' + repr(vals['RELEASE']) + "-"
        else:
            rstr = ""
        vals['OUTFILE'] = "%s%s-%s-%ssetup.exe" % (vals['OUTFILEPREFIX'], vals['NAME'].lower(), vals['VERSION'], rstr)

    opts = eval(dosubs(vals, repr(opts)))
    pkg.pre_setup(opts)
    # run py2exe
    distutils.core.setup(**opts)

    pkg.post_setup()
    # copy resources

    distdir = opts['options']['py2exe']['dist_dir']
    pkg.copyresources(distdir)
    pkg.finalize(distdir)
    pkg.verify_output(distdir)
    #check_no_sources(distdir)

    # make the innosetup package
    vals['GUID'] = vals['GUID'].replace("{", "{{") # needed for innosetup
    # must not supply .exe on end to innosetup
    while vals['OUTFILE'].endswith(".exe"):
        vals['OUTFILE']=vals['OUTFILE'][:-4]

    if 'INSTALLER' in vals:
        for installer_options in vals['INSTALLER']:
            inst = installer.make(pkg, pkg.repo.installer_root, installer_options)
            inst.prep()
            inst.do()
            inst.post()

    else:
        print '*** no installer key present, skipping installer build ***'
    # TODO: move files from 'prep' to folder with revision id
    if pkg.upload_files:
        dir_to_upload = pkg.repo.dist_output_root
        if hasattr(pkg, 'prep_upload'):
            dir_to_upload = pkg.prep_upload()

        for uploader_options in vals['UPLOADER']:
            upl = uploader.make(pkg, dir_to_upload, uploader_options)
            upl.prep()
            upl.do()
            upl.post()

        if hasattr(pkg, 'post_upload'):
            pkg.post_upload()

    else:
        print '*** upload disabled ***'

    print '*** windowsbuild finished ***'
