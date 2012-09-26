from __future__ import with_statement
from pyaspell import Aspell
from util.net import isurl
from common.spelling.dicts import MakeDigsbyDict
from common.filetransfer import ManualFileTransfer
from common import profile, pref

from common.notifications import fire

objget = object.__getattribute__

import wx, os
import syck
import tarfile
import subprocess, _subprocess
from path import path

from util import callsback, threaded, autoassign, program_dir
import stdpaths
from common import setpref
from traceback import print_exc

import logging
log = logging.getLogger('spellchecker')

#L_O_G = log

ASPELLBINDIR = (program_dir() /'lib' / Aspell.LIBNAME).parent

from subprocess import Popen, PIPE, CalledProcessError

ASPELL_CMD = './lib/aspell/bin/aspell %s -a --ignore-case'
ASPELL_OPT = '--%s="%s"'
ASPELL_DFT = ASPELL_CMD % '--lang=en --encoding=utf-8 --keyboard=standard --sugMode=normal'

def FormAspellCommand(parameters):

    options = ' '.join([ASPELL_OPT %(key,parameters[key].replace('\\','/')) for key in parameters])
    cmd = ASPELL_CMD % options

    return cmd


class NullSpellEngine(object):
    """
        Fake SpellEngine for when there is none
    """
    lang = None
    def check(self, word):
        return True
    def suggest(self, word):
        return []
    def kill(self):
        pass
    def add(self):
        pass

class SpellEngine(object):
    """
        Wraps a asepell process so the SpellCheck class can treat it as an object
    """
    def __init__(self, parameters = None):

        self.vLog = pref('messaging.spellcheck.verbose_log', default=False)

        if parameters:
            self.lang = parameters['lang']
            self.cmd = FormAspellCommand(parameters)
        else:
            self.lang = 'en'
            self.cmd = ASPELL_DFT

        self.start()



    def __nonzero__(self):
        """
            If the process is till running the value of a SpellEnging is True
            Otherwise it is False
        """
        return self.aspell.poll() is None



    def start(self):
        """
            Start aspell process
        """

        log.info('Starting aspell process with %s', self.cmd)

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = _subprocess.SW_HIDE

        self.aspell = Popen(self.cmd.encode('filesys'), stdin=PIPE, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo)

        exitCode = self.aspell.poll()
        if exitCode != None:
            log.error('Aspell failed to start with exit code %s with comand: \n%s', exitCode, self.cmd)

        startupstring = self.aspell.stdout.readline()
        if startupstring == '':
            log.error('Aspell failed to start and is exiting')
            raise CalledProcessError(0,'ZOMG')

    def kill(self):
        """
            Kill the aspell process
        """

        log.info('Killing Aspell')
        self.aspell.stdin.close()

    def add(self, word):
        """
            Add a word to the aspell dictionary and save it to disk
        """

        self.resuscitate()

        #L_O_G.info('Adding "%s" to dictionary', word)

        # in aspell &word saves word in the personal dictionary, and sending # saves the changes to disk
        try:
            self.aspell.stdin.write('*%s\n#\n' % word)
        except:
            log.error('Failed communicating to aspell process, poll result: %s;', self.aspell.poll())

    def resuscitate(self):
        """
            Starts a new aspell process if the process is dead
        """

        aspellIsDead = self.aspell.poll() is not None
        if aspellIsDead:
            log.info('Resuscitating aspell')
            self.start()

    def suggest(self, word):
        """
            Return a list of words that are possible corrections to word if word is misspelled
        """

        self.resuscitate()

        #L_O_G.info('Looking up suggestions for "%s"', word)

        try:
            self.aspell.stdin.write(('$$cs sug-mode,normal\n')) #switch mode to normal
            self.aspell.stdin.write(('^%s\n' % word)) #prepend ^ to the word to make sure it's checked and not treated as a command
            self.aspell.stdin.write(('$$cs sug-mode,ultra\n'))  #switch mode back to ultra
        except IOError:
            log.error('Failed communicating to aspell process, poll result: %s;', self.aspell.poll())
            return []

        output = self.aspell.stdout.readline()


        #return an empty list if the word is correct(*) or no suggestions(#)
        if not output or output[0] in '*#':
            while output != '\r\n' and output != '':
                output = self.aspell.stdout.readline()
            return []

        # expected format of aspell responce:
        #    & [original] [count] [offset]: [miss], [miss], ...
        cutindex = output.find(':') + 2
        output = output[cutindex:].strip()

        suggestions = output.split(', ')

        #L_O_G.info('Suggested %s', suggestions)

        #flush stdout
        while output != '\r\n' and output != '':
            #L_O_G.info('Output %s', output)
            output = self.aspell.stdout.readline()

        return suggestions

    def check(self, word):
        """
            Return True if the word is correctly spelled False otherwise
        """

        self.resuscitate()


        #L_O_G.info('Checking %s...;', word)

        try:
            self.aspell.stdin.write(('^%s\n' % word))
        except IOError:
            log.error('Failed communicating to aspell process, poll result: %s;', self.aspell.poll())
            return True

        output = self.aspell.stdout.readline()
        if not output:
            log.error('Aspell is likely dead, empty string read from stdout, poll result: %s;', self.aspell.poll())
            return True

        #Correct spelling is signified by a '*'
        correct = output[0] == '*'

        #L_O_G.info('Checked. %s is %s;', word,'OK' if correct else 'INCORRECT')

        #flush stdout
        while output != '\r\n':
            output = self.aspell.stdout.readline()

        return correct

def LocalAspellDataDir(more = ''):
    """
        Build a return data directory
    """
    return (stdpaths.userlocaldata / ('aspell%s'%Aspell.VERSION) / 'dict' / more) #@UndefinedVariable

class SpellChecker(object):

    def __init__(self, lang_override = None):

        #L_O_G.info('init spellchecker')

        self.spellengine = None
        self.lang = None
        self._need_to_download = None
        self.currentDownloads = set()
        self.expectedNext = None

        # load YAML file describing the dictionaries

        filename = program_dir() / 'res' / ('dictionaries-%s.yaml' % Aspell.VERSION)
        try:
            with open(filename) as f:
                self.dict_info = syck.load(f)
                if not isinstance(self.dict_info, dict):
                    raise ValueError('invalid YAML in %s' % filename)
        except Exception:
            print_exc()
            self.dict_info = {}

        # load an engine using swap engine, if no engine is failed use the NullSpellEngine
        if not self.SwapEngine(lang_override):
            self.spellengine = NullSpellEngine()

        profile.prefs.add_observer(self.on_prefs_change, #@UndefinedVariable
                                   'messaging.spellcheck.enabled',
                                   'messaging.spellcheck.engineoptions.lang',
                                   'messaging.spellcheck.engineoptions.encoding',
                                   'messaging.spellcheck.engineoptions.keyboard',
                                   'messaging.spellcheck.engineoptions.sug-mode') #@UndefinedVariable

    def CreateEngine(self, lang_override=None):
        '''
            Create an Aspell engine from the values in prefs. Optional lang_override allows for creating an engine in a different
            language.

            http://aspell.net/man-html/The-Options.html

            TODO: take lots of kwargs and use them to override the options going into the Aspell engine

            Returns the new Aspell object if it was created.
            Returns None if the requested language was not found.

            Raises all unknown errors.
        '''

        if (not self._pref('enabled')) or \
                pref('messaging.spellcheck.engineoptions.lang') not in self.dict_info:
            return NullSpellEngine()

        #Time to build the args

        #first set of args comes from the prefs
        spellprefs = 'lang encoding keyboard'.split()
        parameters = dict((str(key), str(pref('messaging.spellcheck.engineoptions.' + key))) for key in spellprefs)

        #so check is fast
        parameters['sug-mode'] = 'ultra'

        if lang_override is not None:
            parameters['lang'] = lang_override

        lang = parameters['lang']

        #set the directories
        local_dir = LocalAspellDataDir()
        parameters['local-data-dir'] = local_dir.encode('filesys')
        parameters['add-word-list-path'] = local_dir.encode('filesys')

        home_dir = local_dir / profile.username
        if not home_dir.isdir():
            home_dir.makedirs()
        parameters['home-dir'] = home_dir.encode('filesys')

        if not lang.startswith('en'):
            parameters['dict-dir'] = local_dir.encode('filesys')

        #If the digsby dict for this language doesn't exist, make it, mostly just for english the first time you run it
        #other languages should lready have it at this point
        digsby_dict_location = local_dir / ('digsby-%s.rws' % lang)
        if not digsby_dict_location.isfile():
            try:
                MakeDigsbyDict(lang, local_dir)
            except CalledProcessError, e:
                log.error("failed to create Digsby Dictionary in '%s' at '%s', probable cause: dict not yet downloaded, exception was '%s'", lang, local_dir, e)
                return None

        parameters['add-extra-dicts'] = digsby_dict_location.encode('filesys')

        #encode for filesystem
        for k,v in parameters.items():
            if isinstance(v, unicode):
                parameters[k] = v.encode('filesys')

        try:
            speller = SpellEngine(parameters)
        except CalledProcessError:
            log.error('SpellEngine failed to load, returning None')
            speller = None

        return speller

    def __nonzero__(self):
        """
            True if aspell is running, false otherwise
        """
        return self.aspell.poll() == None

    def on_prefs_change(self, *a, **k):
        '''
            This is the function that watches the related prefs. currently we just create a new engine and toss the old one.
        '''
        log.info('Spelling prefs changed, switching engines')
        self.SwapEngine()

    def SwapEngine(self, lang_override=None, shouldDownloadOnFail = True):
        '''
            Toss the old spellengine and create a new one using CreateEngine().
            If creation fails, the last language used is substituted and the '_need_to_download' attribute
            is set to the requested language.

            Takes an optional lang_override to create another spell checker. This is passed directly to CreateEngine
            Returns True if a new engine was created and False if the old one was retained.
        '''

        #L_O_G.info('SwapEngine')
        try:
            newengine = self.CreateEngine(lang_override)
        except Exception:
            log.error('Something just went horribly wrong in CreateEngine...')
            print_exc()
            return False

        if not newengine and shouldDownloadOnFail: # fail, but download
            self._need_to_download = lang_override or self._pref('engineoptions.lang')
            wx.CallAfter(self.DownloadDict)
            return False
        elif newengine: #success
            if self.spellengine is not None:
                self.spellengine.kill()
            self.spellengine = newengine
            self.lang = self.spellengine.lang
            log.info('Speller switched to %r', self.lang)

            return True
        else: #Epic Fail
            log.error("Language not loaded but already attempted retrieving it")
            return False

    def _pref(self, name, default=sentinel, type=sentinel):
        '''
            Convenience method to get a pref prefixed with 'messaging.spellcheck'
        '''
        return pref('messaging.spellcheck.'+name, default=default, type=type)

    def _get_encoding(self):
        return self._pref('engineoptions.encoding', type=str, default='utf-8')

    def _encode(self, s):
        '''
            Encode a string using the encoding determined by the user's spellcheck prefs
        '''
        if isinstance(s, unicode):
            return s.encode(self._get_encoding())
        else:
            return s
    def _decode(self, s):
        '''
            Decode a string using the encoding determined by the user's spellcheck prefs
        '''
        if isinstance(s, str):
            return s.decode(self._get_encoding())
        else:
            return s

    def Check(self,text):
        """
            Returns True if the word is correctly spelled, false otherwise
        """

        if self.spellengine is None or not text:
            return True

        puretext = self._encode(text)

        return puretext.isdigit() or isurl(puretext) or self.spellengine is None or self.spellengine.check(puretext)

    def Suggest(self,word,count=None):
        """
            Return a list of suggested replacement words if the word is spelled incorrectly
            Returns an empty list if the word is correctly spelled
        """
        if self.spellengine is None:
            return []


        if not word:
            return []

        if not count:
            count = self._pref("max_suggestions")

        suggestions = self.spellengine.suggest(self._encode(word))

        if len(suggestions) > count:
            suggestions = suggestions[:count]

        return [self._decode(s) for s in suggestions]

    def Add(self, word):
        """
            Add a word to the dictionary
        """
        if self.spellengine is None:
            return

        self.spellengine.add(self._encode(word))

    def DownloadDict(self):
        """
            Get everything set for, then call, DownloadAndInstall
        """

        # decide if we actualy need to get the language
        self._need_to_download, need = None, self._need_to_download
        if not need or need == self.lang:
            log.error('not downloading dictionary')
            return

        #set what langugae is expected next
        self.expectedNext = need
        if need in self.currentDownloads:
            log.info('Already downloading dictionary, returning')
            return

        #Get the full name of the language
        langInfo = self.dict_info[need]
        langName = langInfo['name_english']#'name_native' if 'name_native' in langInfo else

        #ask the user about downloading
        log.info('Download %s?', need)
        userResponse = wx.MessageBox(_('You need to download the {langname} dictionary to use it. Would you like to download this dictionary now?').format(langname=langName),
                                     _('Download Dictionary?'),
                                     wx.YES_NO)

        #if the user answered no, inform them of how to download and return
        if userResponse == wx.NO:

            lastlang = self.spellengine.lang
            if lastlang:
                setpref('messaging.spellcheck.engineoptions.lang', lastlang)

            dictcancel_hdr = _('Dictionary not downloaded.')
            dictcancel_msg = _('To download it later, select it in the Conversation Preferences.')

            wx.MessageBox(u'%s\n\n%s' % (dictcancel_hdr, dictcancel_msg),
                          _('Download Dictionary Canceled'),
                          wx.OK)
            return


        #build URL
        remote_repo = pref('messaging.spellcheck.aspell_mirror', type=str, default='http://dict.digsby.com/')
        remote_path = remote_repo + langInfo['location']



        def on_install_success():
            log.info('%r has been installed.', need)

            #Swap out the language if the new language is still selected
            if self.expectedNext == need:
                #Attempt the swap and fire a notification on success
                if self.SwapEngine(shouldDownloadOnFail=False):
                    fire('dictionary.install',
                         title=_('Dictionary Set'),
                         msg=_('Spellcheck language has been set to {langname}.').format(langname=langName),
                         popupid='dict_install_%s' % self.lang)
                #If successfull download and install, but fails to load, fire a error notification
                else:
                    fire('dictionary.install',
                         title=_('Spellcheck error'),
                         msg=_('Failed setting up dictionary. Try reselecting desired language in the preferences.'),
                         popupid='dict_install_%s' % self.lang)

            #if no longer the set language announce the install was complete
            else:
                fire('dictionary.install',
                     title=_('Dictionary Installed'),
                     msg=_('You can set this language in the conversation preferences.'),
                     popupid='dict_install_%s' % self.lang)

            #Remove the language from current downloads
            self.currentDownloads.discard(need)

        #if there's an error, log it
        def on_install_error():
            log.error('There was an error installing %s', need)

            self.currentDownloads.discard(need)

        def on_install_cancel():
            log.info('Dictionary download cancelled by user.')

            self.currentDownloads.discard(need)

            lastlang = self.spellengine.lang
            if lastlang:
                setpref('messaging.spellcheck.engineoptions.lang', lastlang)


        #add to the current downloads set to pervent duplicate downloads
        self.currentDownloads.add(need)

        #Start download
        log.info('Downloading %r from %r', need, remote_path)
        DownloadAndInstall(need, langName, remote_path,
                           cancel  = on_install_cancel,
                           success = on_install_success,
                           error   = on_install_error)

class DictionaryInstaller(object):
    SUFFIXES = '.alias .multi .cwl .rws .dat'.split()

    def __init__(self, id, bz2path):
        autoassign(self, locals())
        self.cwl_files = []

    @callsback
    def Install(self, callback=None):
        log.info('Installing Dictionary...')

        #fire a notification
        fire('dictionary.install', title=_('Installing Dictionary'), msg=_('Dictionary will be activated after install completes.'),
             popupid='dict_install_%s' % self.id)

        #go Extract, then Finalize on success
        self.Extract(error   = callback.error,
                     success = lambda:self.Finalize(callback=callback))


        log.info('Finished Installing Dictionary')

    @threaded
    def Extract(self):
        """
            Extract the usefull files from the tar.bz2 to the local dict directory
        """

        log.info('Extracting Dictionary...')

        log.info('Opening tar %s', self.bz2path)
        tar = tarfile.open(fileobj=open(self.bz2path, 'rb'), mode='r:bz2')
        log.info('Tar opened')
        fobj = None
        outfile = None
        try:
            #Extract any .alias, .multi, .cwl, .rws, and .dat files from the temp file
            log.info('Retrieving file information from tar')
            for fileinfo in tar:
                if not fileinfo.isfile():
                    continue

                fname = path(fileinfo.name.decode('filesys'))

                if fname.ext and fname.ext in self.SUFFIXES:
                    log.info('Extracting %s', fname)

                    ex_path = path(LocalAspellDataDir()) / fname.name

                    if fname.ext == '.cwl':
                        self.cwl_files.append(ex_path)

                    if not ex_path.parent.isdir():
                        ex_path.parent.makedirs()

                    fobj = tar.extractfile(fileinfo)
                    with open(ex_path, 'wb') as outfile:
                        while outfile.tell() < fileinfo.size:
                            outfile.write(fobj.read(16*1024))

                    log.info('Extracted %s', fname)

                else:
                    log.info('Ignoring %s', fname)

        except Exception:
            log.error('Failed extracting files')

        finally:
            #close all files
            for f in (tar, fobj, outfile):
                if f is not None:
                    f.close()


        log.info('Finished Extracting Dictionary...')

        return True

    @threaded
    def Finalize(self):
        """
            Decompress the CWLs to make RWSs
        """
        def quote_encode(s):
            return '"%s"' % s.encode('filesys')

        aspell_opts = ["--lang=%s" % self.id,
                       "--local-data-dir=%s" % quote_encode(LocalAspellDataDir().strip('\\')),
                       "create", "master"]
        decomp_opts = ['d']

        decomp_exe = ASPELLBINDIR/'word-list-compress.exe'
        aspell_exe = ASPELLBINDIR/'aspell.exe'

        startupinfo = subprocess.STARTUPINFO() #@UndefinedVariable
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW #@UndefinedVariable
        startupinfo.wShowWindow = subprocess.SW_HIDE #@UndefinedVariable

        log.info('Decompressing wordlists')
        for cwl in self.cwl_files:
            rws = path(LocalAspellDataDir()) / cwl.namebase + '.rws'
            command = ['cmd', '/c', quote_encode(decomp_exe)] + decomp_opts + \
                       ['<', quote_encode(cwl), '|', quote_encode(aspell_exe)] + aspell_opts + [quote_encode(rws)]

            command = ' '.join(command)
            # this will raise an exception if the command fails, and callsback will call our error callback
            log.info('Decompressing %s', cwl)
            log.info("Executing: %r", command)
            subprocess.check_call(command, shell=True, startupinfo=startupinfo)
            os.remove(cwl)

        os.remove(self.bz2path)

        #Make the digsby dict
        local_dir = LocalAspellDataDir()
        digsby_dict_location = local_dir / ('digsby-%s.rws' % id)
        if not digsby_dict_location.isfile():
            try:
                MakeDigsbyDict(self.id, local_dir)
            except Exception:
                log.error("failed to create Digsby Dictionary in '%s', probable cause: dict not yet downloaded", id)
                return None

        #dictionary installed notification
        fire('dictionary.install', title=_('Dictionary Installed'), msg=_('Setting spellcheck language...'),
             popupid='dict_install_%s' %  self.id)
        return True


@callsback
def DownloadAndInstall(langID, langName, remotePath, cancel, callback=None):
    """
        Does what it says, via a DictionaryDownloader and DictionaryInstaller Objects, using alot of callbacks
    """

    log.info('Downloading dictionary...')

    ManualFileTransfer( _('{langname} Dictionary').format(langname=langName), remotePath,
                      lambda downloaded_path: DictionaryInstaller(langID, downloaded_path).Install(callback=callback),
                      cancel,
                      callback.error).manual_download()

'''
cd aspell
bin\word-list-compress.exe d < dict\es.cwl | bin\aspell.exe --lang=es create master es.rws
'''

class SpellCheckerMock(object):
    """
        Stuff to make it so there can only be one
    """
    def __getattr__(self, key, default = sentinel):
        try:
            spellchecker = object.__getattribute__(self, '_spellchecker')
        except AttributeError:
            #L_O_G.info('No old spellchecker found... Creating')
            try:
                spellchecker = SpellChecker()
            except:
                spellchecker = SpellChecker(lang_override='en')


            #L_O_G.info('Setting _spellchecker')
            object.__setattr__(self, '_spellchecker', spellchecker)

        if default is sentinel:
            return getattr(spellchecker, key)
        else:
            return getattr(spellchecker, key, default)

spellchecker = SpellCheckerMock()
