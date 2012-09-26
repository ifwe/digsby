import os.path
import shutil
import subprocess
import sys
import tempfile

def as_bool(value):
    if value.lower() in ('1', 'true'):
        return True
    return False

def run_commands(cmds, shell, check=True):
    cmds = cmds.strip()
    if not cmds:
        return
    if cmds:
        lines = cmds.split('\n')
        lines = [l.strip() for l in lines]
        dirname = tempfile.mkdtemp()

        print '----------'
        print '\n'.join(lines)
        print '----------'

        if sys.platform == 'win32':
            tmpfile = os.path.join(dirname, 'run.bat')
            
            if check:
                # add an error handler after each line so that we bail on a non-zero return code
                # (batch files are shit and don't do this by default)
                reallines = []
                for line in lines:
                    reallines.append('echo CMDRUNNER --> "' + line + '"')
                    reallines.append(line)
                    reallines.append('if %errorlevel% neq 0 exit /b %errorlevel%')
                lines = reallines

            lines.insert(0, '@echo off')
        else:
            tmpfile = os.path.join(dirname, 'run')
        open(tmpfile, 'w').write('\n'.join(lines))
        if sys.platform == 'win32':
            retcode = subprocess.call(tmpfile, shell=True)
        else:
            retcode = subprocess.call('%s %s' % (shell, tmpfile), shell=True)
        shutil.rmtree(dirname)
        if check and retcode != 0:
            raise Exception('non-zero return code for cmds:\n' + cmds)


class Cmd(object):
    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options

        self.on_install = as_bool(options.get('on_install', 'false'))
        self.on_update = as_bool(options.get('on_update', 'false'))
        self.check_return_code = as_bool(options.get('check_return_code', 'true'))
        self.shell = options.get('shell', 'sh')

    def install(self):
        if self.on_install:
            self.execute()
        return tuple()

    def update(self):
        """updater"""
        if self.on_update:
            self.execute()
        return tuple()

    def execute(self):
        """run the commands
        """
        cmds = self.options.get('cmds', '')
        run_commands(cmds, self.shell, self.check_return_code) 

def uninstallCmd(name, options):
    cmds = options.get('uninstall_cmds', '')
    shell = options.get('shell', 'sh')
    run_commands(cmds, shell)

class Python(Cmd):

    def execute(self):
        """run python code
        """
        cmds = self.options.get('cmds', '')
        cmds = cmds.strip()
        def undoc(l):
            l = l.strip()
            l = l.replace('>>> ', '')
            l = l.replace('... ', '')
            return l

        if not cmds:
            return
        if cmds:
            name = self.name
            buildout = self.buildout
            options = self.options
            lines = cmds.split('\n')
            lines = [undoc(line) for line in lines if line.strip()]
            dirname = tempfile.mkdtemp()
            tmpfile = os.path.join(dirname, 'run.py')
            open(tmpfile, 'w').write('\n'.join(lines))
            execfile(tmpfile)
            shutil.rmtree(dirname)
