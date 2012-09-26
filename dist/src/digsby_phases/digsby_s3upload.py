import sys
import deploy
import helpers

class S3Uploader(object):
    def upload_file_to_s3(self, f, compress = True, mimetypes = False):
        return self.upload_to_s3(f, compress, False, mimetypes = mimetypes)

    def upload_dir_to_s3(self, directory, compress = True, mimetypes = False):
        return self.upload_to_s3(directory, compress, True, mimetypes = mimetypes)

    def upload_to_s3(self, what, compress, recursive, mimetypes = False):
        args = []
        if getattr(self, 'dry_run', False):
            args.append('--dry-run')
        if recursive:
            args.append('--recursive')
        if compress:
            args.append('--compress-all')
            args.extend('-c %s' % ext for ext in ('png', 'jpg', 'zip'))

        if mimetypes:
            args.append('--mimetypes')

        helpers.run(sys.executable, self.script, what,
            "--key", self.access,
            '--secret', self.secret,
            '--bucket', self.bucket,
            '--public-read',
            '--time',
            '--verbose',
            *args
            )

class S3(deploy.Upload, S3Uploader):
    strategy = 's3'
    def do(self):
        with helpers.cd(self.path):
            self.upload_dir_to_s3(self.build_identifier)

        print '*** done uploading ***'

class InstallerDeploy(deploy.Deploy, S3Uploader):
    strategy = 'installer'
    cancel = False

    def pre(self):
        super(InstallerDeploy, self).pre()
        from buildutil.promptlib import prompt

        plain_installer = self.install_package

        if not (self.path / 'install').isdir():
            (self.path / 'install').makedirs()

        for name in self.release_tags:
            if name == 'release':
                plain_installer.copyfile(self.path / 'install' / 'digsby_setup.exe' % name)
            else:
                plain_installer.copyfile(self.path / 'install' / ('digsby_setup_%s.exe' % name))

        plain_installer.copyfile(self.path / 'install' / plain_installer.name)

        if not prompt("Upload installers?", bool, True):
            self.cancel = True

    def do(self):
        if self.cancel:
            return

        with helpers.cd(self.path):
            self.upload_dir_to_s3('install', compress=False, mimetypes=True)

