'''
Created on Apr 9, 2012

@author: "Michael Dougherty <mdougherty@tagged.com>"
'''
import os
import yaml
import sys
import uuid
import time
import email
import optparse
import distutils
import config
import path
import deploy
import helpers
import shutil

DEBUG = hasattr(sys, 'gettotalrefcount')
SVN = os.environ.get('SVN_EXE', 'svn')

class DigsbyClean(deploy.Clean):
    strategy = 'digsby'
    def do(self):
        helpers.clean(self.paths)

class SVNCheckout(deploy.Checkout):
    strategy = 'svn'
    revision = None
    def do(self):
        # TODO: make sure repo is clean
        helpers.run(SVN, 'status', self.source)
        helpers.run(SVN, 'update', self.source)

        svnoutput = helpers.run(SVN, 'info', self.source, verbose = False)
        svninfo = dict(line.split(': ', 1) for line in filter(bool, svnoutput.splitlines()))
        self.revision = int(svninfo['Last Changed Rev'])

        if self.options.get('dest'):
            helpers.run(SVN, 'export', '-r', self.revision, self.source, self.dest)


class GitCheckout(deploy.Checkout):
    strategy = 'git'
    revision = None

    def do(self):
        with helpers.cd(self.source):
            branch = getattr(self, 'branch', 'master')
            remote = getattr(self, 'remote', 'origin')

            git_status = helpers.run('git', 'status', '--porcelain', verbose = False).strip()
            helpers.run('git', 'checkout', branch)
            if git_status:
                helpers.run('git', 'reset', '--hard', branch)
            helpers.run('git', 'fetch', remote, branch)
            helpers.run('git', 'merge', '--ff-only', '%s/%s' % (remote, branch))
            helpers.run('git', 'submodule', 'init')
            helpers.run('git', 'submodule', 'update')

            self.revision = helpers.run('git', 'rev-parse', '--short', 'HEAD', verbose = False).strip()

            if self.options.get('dest'):
                raise Exception("Haven't figured out the proper set of `git archive` commands yet")

                helpers.run('git', 'archive', '-o', self.options.get('dest') / ('%s.zip' % self.revision), branch)
                with helpers.cd(self.options.get('dest')):
                    # TODO: this doesn't work.
                    helpers.run('unzip', 'archive.zip')


class MSVC(deploy.Compile):
    strategy = 'msvc'

class PyUnitTest(deploy.Test):
    strategy = 'pyunittest'
    def pre(self):
        super(PyUnitTest, self).pre()
        self._old_pypath = os.environ['PYTHONPATH']
        os.environ['PYTHONPATH'] = self.options.get('pythonpath', '')

    def do(self):
        ## not valid in 2.6
        #helpers.run(sys.executable, '-m', 'unittest', 'discover', '-s', self.dest / 'digsby' / 'src' / 'tests')
        helpers.run(sys.executable, self.dest / 'digsby' / 'src' / 'tests' / 'unittests' / 'runtests.py')

    def post(self):
        os.environ['PYTHONPATH'] = self._old_pypath
        super(PyUnitTest, self).post()

class SanityTest(deploy.Test):
    strategy = 'sanitycheck'
    def do(self):
        self.sanitycheck_win()

    def sanitycheck_win(self):
        self.needed_dlls = []

        assert os.path.isdir(self.path / 'installer')
        assert os.path.isdir(self.launcher_exe.parent)
        assert os.path.isfile(self.launcher_exe)

        self.msvc_devenv = path.path(os.environ.get('VS90COMNTOOLS', r'C:\Program Files (x86)\Microsoft Visual Studio 9.0\Common7\Tools')).abspath()
        assert self.msvc_devenv.isdir()

        if not DEBUG:
            self.redist_dirname = 'Microsoft.VC90.CRT'
            self.msvc_crt = self.msvc_devenv / '..' / '..' / 'VC' / 'redist' / 'x86' / self.redist_dirname
            self.debug_postfix = ''
        else:
            self.redist_dirname = 'Microsoft.VC90.DebugCRT'
            self.msvc_crt = self.msvc_devenv / '..' / '..' / 'VC' / 'Debug_NonRedist' / 'x86' / self.redist_dirname
            self.debug_postfix = 'd'

        self.needed_dlls.extend(['msvcp90%s.dll' % self.debug_postfix,
                                 'msvcr90%s.dll' % self.debug_postfix])

        for f in self.needed_dlls:
            f = self.msvc_crt / f
            assert f.isfile()

class CheckReleaseNotes(deploy.Prepare):
    strategy = 'release_notes'
    def do(self):
        from buildutil.promptlib import prompt
        if not prompt("Type 'blag' if you updated the blog post in res/release_notes.html", str).lower() == 'blag':
            raise Exception('Update the blog post link in res/release_notes.html')

class SignBinary(deploy.Prepare):
    strategy = 'sign_binary'

    def do(self):
        from buildutil.signing import Authenticode
        Authenticode(self.path)

class SignBinaryInstaller(deploy.Prepare):
    strategy = 'sign_binary_installer'

class DigsbyUpdaterPrep(deploy.Prepare):
    strategy = 'digsby'

    def do(self):
        "Do any finalizations before the installer is made"
        # You'll want to remove unneeded files, set permissions etc
        badfiles = [self.source / 'devmode.pyo',
                    self.source / 'package.pyo',
                    ]

        for badfile in badfiles:
            badfile = badfile.expand()
            if badfile.isfile():
                badfile.remove()

        if not self.dest.isdir():
            self.dest.makedirs()
        if (self.source / 'lib').isdir():
            (self.source / 'lib').rename(self.dest / 'lib')

        if not (self.dest / 'lib').isdir():
            (self.dest / 'lib').makedirs()

        for fname in self.source.listdir():
            if fname.name != 'lib':
                try:
                    fname.rename(self.dest / 'lib' / fname.name)
                except:
                    print fname
                    raise

        self.target.launcher_exe.copy2(self.dest / 'digsby.exe')
        self.target.copyresources(self.dest)

        print '*** generating manifest ***'
        import __builtin__
        __builtins__._ = __builtin__._ = __builtins__.N_ = __builtin__.N_ = lambda s:s

        from plugins.digsby_updater.file_integrity import generate_manifest
        man = generate_manifest(self.dest)

        with open(self.dest / 'manifest', 'wb') as f:
            f.write(man)

        print '*** manifest is in %s ***' % (self.dest /'manifest')

class DigsbyUpdaterVerify(deploy.Verify):
    strategy = 'digsby'

    def do(self):
        helpers.check_no_sources(self.path)

class NSISInstaller(deploy.Package):
    strategy = 'nsis'
    tag = None
    def installer_name_for_settings(self, nsis_opts):
        build_id = nsis_opts.get('build_identifier')
        instver = nsis_opts.get('INSTVER', 0)
        if instver:
            return 'digsby_setup_r%s_%s.exe' % (build_id, instver)
        else:
            return 'digsby_setup_r%s.exe' % (build_id)

    def pre(self):
        super(NSISInstaller, self).pre()
        from buildutil.promptlib import prompt

        self.tag = prompt('(optional) Please enter a tag for the installer:', str, None)

        if self.tag:
            tag_path = self.source / 'tag.yaml'
            tag_path.open('wb').write('tag: %s' % self.tag)

        nsis_defaults = dict(DISTDIR = str(self.source),
                             SVNREV  = str(self.build_identifier))

        nsis_options = {}
        nsis_options.update(nsis_defaults)
        nsis_options.update(self.options)
        self.outfile = self.dest / self.installer_name_for_settings(nsis_options)
        if not self.outfile.parent.isdir():
            self.outfile.parent.makedirs()

        with (self.script.parent / 'PyInfo.nsh').open('w') as f:
            outfile_str = '"%s"' % self.outfile
            f.write('OutFile %s\n' % outfile_str)

            for k, v in nsis_options.items():
                if v is None:
                    s = '!define %s\n' % (k,)
                else:
                    s = '!define %s "%s"\n' % (k,v)

                f.write(s)

    def do(self):
        with helpers.cd(self.script.parent):
            helpers.run(self.path_nsis, '/V4', self.script)

    def post(self):
        (self.script.parent / 'PyInfo.nsh').remove()
        super(NSISInstaller, self).post()

class MoveFiles(deploy.Prepare):
    strategy = 'move_files'
    def do(self):
        if not self.dest_dir.isdir():
            self.dest_dir.makedirs()
        self.source.rename(self.dest_dir / self.build_identifier)

class YamlDeploy(deploy.Deploy):
    strategy = 'yaml'

default_blacklist = ['makedist', 'bot',
                     'build.updatedeps', 'linecount', 'video',
                     'gui.webcam',
                     'common.MultiImage', 'common.shaped',
                     'gui.gfxlist.gfxlist', 'gui.si4demo',
                     'gui._splitimage4', 'gui.splitimage4',
                     'util.ie', 'util.shared.testshared',
                     'gui._ctextutil', 'gui.ctextutil',
                     'gui.browser.iewindow', 'psyco',
                     'thumbs.db', 'Thumbs.db',
                     'gui.bugreporter', 'pylint', 'logilab',
                     'tagtrunk', 'pyflakes',
                     'python_twitter', 'spelling.dicts',
                     'package', 'makedist', 'setup', 'tagtrunk',
                     'jsTestDriver.conf',

                     #'build.mac.build-deps',
                     lambda x: 'pg_dev' in x,
                     lambda x: '.svn' in x,
                     lambda x: '.git' in x,
                     lambda x: x.startswith('gui.native.'),
                     lambda x: 'devmode' in x,
                     lambda x: 'PPCRL' in x,
                     lambda x: 'uberdemos' in x,
                     lambda x: x.endswith('_setup'),
                     lambda x: 'tests' in x.lower(),
                     lambda x: 'otherskins' in x.lower(),
                     lambda x: x.endswith('.pdb'),
                     lambda x: 'rupture' in x,
                     lambda x: x.startswith('build'),
                     lambda x: 'SOAPpy' in x,
                     lambda x: 'fake' in x,
                     lambda x: 'fb20' in x,
                     lambda x: 'ms20' in x,
                     lambda x: 'devplugins' in x,
                     lambda x: 'BuddyList' in x,
                     lambda x: x.startswith('i18n'),
                     lambda x: x.startswith('src.jangle'),
                     lambda x: x.startswith('src.RTFToX'),
                     lambda x: x.startswith('lib.'),
                     lambda x: x.startswith('src.'),
                     lambda x: x.startswith('platlib.'),
                     ]

windows_res_blacklist = [
                         lambda x: '.svn' in x,
                         lambda x: '.git' in x,
                         lambda x: os.path.isdir(x) and x.startswith('mac'),
                         lambda x: os.path.isdir(x) and x == 'defaultmac',
                         lambda x: 'res\\skins\\native' in x,
                         ]

class DigsbyDeployTarget(object):
    disallowed_extensions = ['.py', '.pyc', '.cpp', '.c', '.h', '.erl', '.hrl', '.php', '.cs', '.pl', '.gitignore']
    verbose = False
    has_updated_syspath = False
    version = None
    def __init__(self, location):
        self.location = location
        self.update_sys_path()

    def get_options(self, phase, strategy, options):
        phase_updater = getattr(self, 'get_options_' + phase, None)
        if phase_updater is not None:
            options = phase_updater(options)
        strategy_updater = getattr(self, 'get_options_%s_%s' % (phase, strategy), None)
        if strategy_updater is not None:
            options = strategy_updater(options)
        return options

    def get_options_freeze_py2exe(self, options):
        options['pythonpath'] = self.get_pythonpath()
        import plat.win.manifest as manifest
        manifest_resource = (24, 1, manifest.manifest)
        for windows_options in options['distutils_options']['windows']:
            if manifest_resource not in windows_options['other_resources']:
                windows_options['other_resources'].append(manifest_resource)

        options['distutils_vals']['GUID'] = str(uuid.uuid3(uuid.NAMESPACE_DNS, options['distutils_vals']['URL']))
        options['distutils_vals']['VERSION'] = self.build_identifier()
        options['distutils_vals']['BUILDDATETIME'] = email.Utils.formatdate(time.time(), True)

        options['distutils_options']['options']['py2exe']['includes'] = self.getallmodulenames()

        options['distutils_options'] = eval(helpers.dosubs(options['distutils_vals'],
                                                           repr(options['distutils_options'])),
                                            {},
                                            dict(path = path.path))
        options['product_version'] = self.build_identifier()
        return options

    def get_options_upload(self, options):
        options['build_identifier'] = self.build_identifier()
        return options

    def get_options_package_nsis(self, options):
        #options['tag'] = ??
        options['build_identifier'] = self.build_identifier()
        return options

    def get_options_prepare_sign_binary_installer(self, options):
        options['path'] = self.install_package
        return options

    def get_options_prepare_move_files(self, options):
        options['build_identifier'] = self.build_identifier()
        return options

    def get_options_deploy_updater(self, options):
        options['build_identifier'] = self.build_identifier()
        return options

    def get_options_deploy_installer(self, options):
        options['build_identifier'] = self.build_identifier()
        options['release_tags'] = self.tags
        options['install_package'] = self.install_package
        return options

    def post_deploy_updater(self, updater_deployer):
        self.tags = updater_deployer.release_tags

    def post_package_nsis(self, nsis_builder):
        self.install_package = nsis_builder.outfile

    def post_test_sanitycheck(self, sanitychecker):
        # checker has needed DLL paths
        self.msvc_crt = sanitychecker.msvc_crt
        self.needed_dlls = sanitychecker.needed_dlls
        self.redist_dirname = sanitychecker.redist_dirname

    def post_checkout_svn(self, svn_checkout):
        self.version = svn_checkout.revision

    def post_checkout_git(self, git_checkout):
        self.version = git_checkout.revision

    def build_identifier(self):
        # return your version string
        return str(self.version)

    def update_sys_path(self):
        if self.has_updated_syspath:
            return

        self.has_updated_syspath = True
        for pth in ('.', 'src', 'lib', 'res', 'ext', 'build',
                    path.path('ext') / config.platformName,
                    path.path('platlib') / config.platformName):
            sys.path.append((self.location / 'digsby' / pth).abspath())

        sys.path.append(self.get_platlib_dir())

    def get_platlib_dir(self, debug=DEBUG):
        if debug is None:
            debug = hasattr(sys, 'gettotalrefcount')

        return (self.location / 'platlib' / ('platlib_%s32_26%s' % (config.platformName, '_d' if debug else ''))).abspath()

    def get_pythonpath(self):
        return os.pathsep.join(sys.path)

    def getallmodulenames_fromdir(self, root, prefix='', blacklist = default_blacklist):
        pyfiles = []

        # directories that will be on PYTHONPATH when running the program
        pathdirs = ['src', '', 'ext',]

        for curdir, dirs, files in os.walk(root):
            # TODO: this should eventually be unnecessary
            if '.git' in root:
                continue
            if '.svn' in root:
                continue
            if '.git' in dirs:
                dirs.remove('.git')
            if '.svn' in dirs:
                dirs.remove('.svn')

            for file in files:
                if file.endswith('.py') or file.endswith('.pyc') or file.endswith('.pyd'):
                    pyfiles.append(path.path(curdir[len(root)+1:]) / file.rsplit('.')[0])

        if prefix and not prefix.endswith('.'):
            prefix = prefix + '.'

        modules = []
        for f in pyfiles:
            f = f.replace('\\','.')
            if f.endswith('.__init__'):
                f = f[:-len('.__init__')]

            parts = f.split('.')
            for pathdir in pathdirs:
                if parts[0] == pathdir:
                    parts = parts[1:]
                    break

            f = '.'.join(parts)

            if not f: continue

            if self.blacklisted(f, blacklist):
                print 'skipping %r because it\'s blacklisted' % f
                continue

            if (prefix+f) not in modules:
                modules.append(prefix+f)

        return modules

    def getallmodulenames(self):
        import dns
        import email
        import ZSI
        import PIL
        import lxml
        import pkg_resources
        import peak
        f = self.getallmodulenames_fromdir

        modules = (
                f(self.location / 'digsby') +
                f(os.path.dirname(dns.__file__), 'dns') +
                f(os.path.dirname(email.__file__), 'email') +
                f(os.path.dirname(ZSI.__file__), 'ZSI') +
                f(os.path.dirname(PIL.__file__), 'PIL') +
                f(os.path.dirname(lxml.__file__), 'lxml') +
                f(os.path.dirname(peak.__file__), 'peak')
        ) + self.os_specific_modules()

        return modules

    def os_specific_modules(self):
        return getattr(self, 'os_specific_modules_%s' % config.platform, lambda: [])()

    def os_specific_modules_win(self):
        import gui.native.win as guiwin
        f = self.getallmodulenames_fromdir

        return (
            f(os.path.dirname(guiwin.__file__), 'gui.native.win', []) +
            f(os.path.abspath('./ext/win'), '') +
            f(os.path.abspath('./platlib/win'), '')
            )

    def blacklisted(self, file, blacklist):
        for test in blacklist:
            if not callable(test):
                filename = test
                comparator = lambda a, b = filename: a == b
            else:
                comparator = test
            if comparator(file):
                return True

        return False

    def copyresources(self, prep):
        "Copy other files to the destination directory"

        print '*** copying resources ***'

        ext = self.location / 'digsby' / 'ext'
        lib = prep / 'lib'

        def strays():
            yield (ext / 'msw' / 'Digsby Updater.exe', lib)
            yield (ext / 'msw' / 'Digsby PreUpdater.exe', lib)
            # yield (self.repo.source_root / 'lib' /'digsby_updater.exe', lib)
            yield (self.location / 'digsby' / 'lib' / 'digsby.dummy', lib)

            bad_exts = frozenset(self.disallowed_extensions)
            plugins_dir = self.location / 'digsby' / 'src' / 'plugins'

            for plugin_info in plugins_dir.walk():
                if plugin_info.isfile() and \
                   not self.blacklisted(plugin_info, default_blacklist) and \
                   not plugin_info.ext.lower() in bad_exts:
                    target = lib / 'plugins' / plugins_dir.relpathto(plugin_info).parent
                    yield plugin_info, target

        for fname, dest in strays():
            fdst = (dest / fname.name)

            if not fdst.parent.isdir():
                fdst.parent.makedirs()

            fname.copy2(fdst)
            if self.verbose:
                print fdst

        def copy_stray_dir(start, destdir, ignore=[]):
            pth = self.location / 'digsby' / start
            destdir = path.path(destdir)
            dst = destdir.abspath() / start
            #print pth, '->', dst
            _myblacklist = windows_res_blacklist+ignore
            for file in pth.walk():
                if self.blacklisted(file, _myblacklist):
                    print 'skipping', file, 'because it\'s blacklisted'
                    continue

                rel = pth.relpathto(file)
                fdst = dst / rel
                if file.isdir() and not fdst.isdir():
                    os.makedirs(fdst)
                else:
                    if not fdst.parent.isdir():
                        os.makedirs(fdst.parent)
                    shutil.copy2(file, fdst)

        # comtypes IE support needs a aux. type library file
        import wx.lib.iewin # <-- its in this file's directory

        ole_tlb  = path.path(wx.lib.iewin.__file__).parent / 'myole4ax.tlb'
        ole_dest = lib / 'wx' / 'lib'
        if self.verbose:
            print 'copying %r to %r' % (ole_tlb, ole_dest)
        if not ole_dest.isdir():
            ole_dest.makedirs()
        ole_tlb.copy2(ole_dest)

        self.copy_certifi_resources(prep)
        self.copy_msvc_binaries(prep)

        copy_stray_dir('lib/aspell', prep)
        copy_stray_dir('res', prep)

    def copy_certifi_resources(self, prep):
        # certifi has a .pem file, which is a list of CA certificates for browser-style authentication.
        import certifi
        certifi_dest = prep / 'lib' / 'certifi'
        if not certifi_dest.isdir():
            certifi_dest.makedirs()
        path.path(certifi.where()).copy2(certifi_dest)

    def copy_msvc_binaries(self, prep):
        'Copies MSVC redistributable files.'

        # Copy the two needed MSVC DLLs into Digsby/lib
        for f in self.needed_dlls:
            redist_src  = self.msvc_crt / f
            redist_dest = prep / 'lib' / f
            redist_src.copy2(redist_dest)

        # Write a private assembly manifest into ./lib pointing at the DLLs
        # in the same directory.
        import plat.win.manifest as manifest

        with (prep / 'lib' / (self.redist_dirname + '.manifest')).open('w') as f:
            f.write(manifest.msvc9_private_assembly %
                    ' '.join('<file name="%s" />' % dll for dll in self.needed_dlls))

    @property
    def launcher_exe(self):
        return self.location / 'digsby' / 'ext' / 'msw' / 'DigsbyLauncher.exe'

def do_deploy(repo, deploy_file, target = None):
    repo = path.path(repo)
    if target is None:
        target = DigsbyDeployTarget(repo)

    def path_constructor(loader, node):
        if node.id == 'sequence':
            return repo.joinpath(*(loader.construct_sequence(node))).abspath()
        elif node.id == 'scalar':
            return (repo / loader.construct_scalar(node)).abspath()

    import digsby_phases
    yaml.add_constructor('!path', path_constructor)
    phases = yaml.load(open(deploy_file))

    for phase in phases:
        assert(len(phase) == 1)
        phase_name, phase_parts = phase.items()[0]
        for strat in phase_parts:
            ((strategy_name, options),) = strat.items()
            options = target.get_options(phase_name, strategy_name, options)
            with deploy.phase(phase_name, strategy_name, target, **options) as phase:
                phase.do()

    print('*** done ***')


def main(args):
    opts, args = _option_parser.parse_args(args)
    do_deploy(**vars(opts))

_option_parser = optparse.OptionParser(prog = 'makedist')
_option_parser.add_option('-r', '--repo', type = 'string', dest = 'repo')
_option_parser.add_option('-d', '--deploy', type = 'string', dest = 'deploy_file', default = 'deploy.yaml')

if __name__ == '__main__':
    main(sys.argv)
