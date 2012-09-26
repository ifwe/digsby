'''
Created on Apr 11, 2012

@author: "Michael Dougherty <mdougherty@tagged.com>"
'''
import os
import urllib2
import deploy
import random
import yaml
import config

from digsby_s3upload import S3Uploader

class DigsbyUpdaterDeploy(deploy.Deploy, S3Uploader):
    strategy = 'updater'
    def pre(self):
        super(DigsbyUpdaterDeploy, self).pre()
        for key, val in self.s3options.items():
            setattr(self, key, val)

    def do(self):
        import util.net as net
        from buildutil.promptlib import prompt

        updateyaml_data = None
        abs_source = net.httpjoin(self.server, self.source)
        while updateyaml_data is None:
            try:
                print 'Fetching', abs_source
                res = urllib2.urlopen(abs_source)
            except Exception, e:
                tryagain = prompt("Error opening %r (e = %r). Try again?" % (abs_source, e),
                                  bool, True)
                if not tryagain:
                    break
            else:
                updateyaml_data = res.read()

        if updateyaml_data is None:
            print 'Could not retrieve current update.yaml. This release has not been activated, you\'ll have to upload the update.yaml file yourself.'
            return

        info = yaml.load(updateyaml_data)
        currentplatname = config.platformName

        manifest_ext = ''
        if currentplatname == 'mac':
            manifest_ext = '.mac'

        new_manifest_url = net.httpjoin(self.server, self.build_identifier + '/' + 'manifest' + manifest_ext)
        done = False

        while not done:
            platname = prompt("Enter platform", str, currentplatname)
            platdict = info.setdefault(platname, {})
            if platdict:
                release_names = prompt('Enter releases to update', list, default = ['alpha'])
            else:
                release_names = [prompt('No releases present for platform %r. Enter new release name.' % platname,
                                        str, default = 'release')]

            done = prompt('Release types %r for platform %r will be set to %r. Is this ok?' % (release_names, platname, new_manifest_url),
                          bool, False)
            if not done:
                if prompt('What next?', options = ['make changes', 'cancel'], default = 'make changes') == 'cancel':
                    return

        self.release_tags = release_names
        for name in release_names:
            platdict[name] = new_manifest_url

        new_yaml = yaml.dump(info)
        try:
            with open(self.source, 'wb') as f:
                f.write(new_yaml)

            party_strings = ['party', 'soiree', 'extravaganza',
                             'get-together', 'festival', 'celebration',
                             'gala', 'shindig', 'hoe-down', 'fiesta',
                             'mitzvah']

            party = random.choice(party_strings)
            should_upload = prompt('To upload %r to S3 and make this release (%r) live' %
                                   (self.source, self.build_identifier),
                                   'confirm', party)
            if not should_upload:
                print 'Cancelling automated release. You\'ll have to upload update.yaml yourself.'
                return

            self.upload_file_to_s3(self.source, compress = False)
        finally:
            if os.path.exists(self.source):
                try:
                    os.remove(self.source)
                except Exception:
                    pass
