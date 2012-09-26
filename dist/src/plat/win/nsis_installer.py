'''
Created on Apr 9, 2012

@author: "Michael Dougherty <mdougherty@tagged.com>"
'''
import path
import helpers

import installer
class NSISInstallerBuilder(installer.InstallerBuilder):
    def __init__(self, pkg, prep, source, options):
        self.package = pkg
        self.content_dir = prep
        self.installer_script = path.path(source) # self.repo.installer_root / 'DigsbyInstall.nsi'
        self.options = options
        '''
        options = dict(
            foldername = 'install',
            honest = True,
            use_no_adware_image = True,
            instver = 7,
            offers = dict(),
        ),
        '''

        self.nsis_exe = pkg.repo.installer_root / 'NSIS' / 'makensis.exe'
        self.content_dir = pkg.repo.dist_prep_root
        self.output_dir = pkg.repo.dist_output_root / 'install'

    def prep(self):

        print '*** prepping for NSIS installer creation ***'
        tag = self.options.get('tag', None)
        if tag is not None:
            tagfile = path.path(self.content_dir) / 'tag.yaml'
            open(tagfile, 'wb').write('tag: %s' % tag)

        nsis_defaults = dict(DISTDIR = self.content_dir,
                             SVNREV = self.package.get_source_rev(),
                             DIGSBY_INSTALLER_DIR = self.package.repo.installer_root)

        nsis_options = {}
        nsis_options.update(nsis_defaults)
        nsis_options.update(self.options)
        self.all_options = nsis_options

        with (path.path(self.package.repo.installer_root) / 'PyInfo.nsh').open('w') as f:
            outfile_str = '"%s"' % (self.output_dir / installer_name_for_settings(nsis_options, nsis_options['SVNREV']))
            f.write('OutFile %s\n' % outfile_str)

            for k, v in nsis_options.items():
                if v is None:
                    s = '!define %s\n' % (k,)
                else:
                    s = '!define %s "%s"\n' % (k,v)

                f.write(s)

        if not self.output_dir.isdir():
            self.output_dir.mkdir()

    def do(self):
        with helpers.cd(self.installer_script.parent):
            print '*** running makensis with options %r ***' % (self.options,)
            helpers.run(self.nsis_exe, '/V4', self.installer_script)

    def post(self):
        tagfile = path.path(self.content_dir) / 'tag.yaml'
        if tagfile.isfile():
            tagfile.remove()

        installer_path = self.output_dir / installer_name_for_settings(self.all_options, self.all_options['SVNREV'])

        # Sign installer
        self.package.sign_binary(installer_path)

        installer_path.copyfile(installer_path.parent / 'digsby_setup.exe')

def installer_name_for_settings(nsis_opts, svnrev):
    instver = nsis_opts.get('INSTVER', 0)
    if instver:
        return 'digsby_setup_r%d_%d.exe' % (svnrev, instver)
    else:
        return 'digsby_setup_r%d.exe' % (svnrev)

installer.InstallerBuilder._builders['nsis'] = NSISInstallerBuilder
