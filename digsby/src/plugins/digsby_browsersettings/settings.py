import logging
import ConfigParser as CF
import json

import stdpaths
import path

import common
import util
import peak.util.addons as addons
import gui.native.win.process as processes

from contextlib import closing

log = logging.getLogger("browsersettings")

HOMEPAGE_URL = 'http://search.digsby.com'
DIGSBY_SEARCH_URL = 'http://searchbox.digsby.com/search?q={searchTerms}&ie=utf-8&oe=utf-8&aq=t'
DIGSBY_SEARCH_UUID_IE = "{3326ab56-742e-5603-906f-290517220122}"

class BrowserSettingsEditor(object):
    process_name = None

    def is_installed(self):
        return False

    def can_edit(self):
        return not self.is_running()

    def is_running(self):
        return self.process_name in processes.process_list()

    def set_homepage(self):
        return False

    def set_search(self):
        return False

    def __repr__(self):
        return '<%s>' % (type(self).__name__,)

class InternetExplorer(BrowserSettingsEditor):
    process_name = 'iexplore.exe'

    def can_edit(self):
        return True

    def is_installed(self):
        # even if it's not (EU? user uninstalled?) we can still edit the registry.
        return True

    def set_homepage(self):
        '''
        Function AddGoogleHomePage_IE
          WriteRegStr HKCU "Software\Microsoft\Internet Explorer\Main" "Start Page" "http://search.digsby.com"
        FunctionEnd
        '''
        log.info("setting homepage for %r", self.process_name)
        import _winreg

        with util.traceguard:
            k = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, '''Software\\Microsoft\\Internet Explorer\\Main\\''', 0, _winreg.KEY_SET_VALUE)
            _winreg.SetValueEx(k, 'Start Page', None, _winreg.REG_SZ, 'http://search.digsby.com')
            k.Close()

        return True

    def set_search(self):
        '''
        Function AddGoogleSearchEngine_IE
            WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\${DIGSBY_SEARCH_UUID_IE}" DisplayName "Google Powered Digsby Search"
            WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\${DIGSBY_SEARCH_UUID_IE}" URL "http://searchbox.digsby.com/search?q={searchTerms}&amp;ie=utf-8&amp;oe=utf-8&amp;aq=t"
            WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes" DefaultScope ${DIGSBY_SEARCH_UUID_IE}
            WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchUrl" "" http://searchbox.digsby.com/search?q=%s
            WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\Main" "Use Search Asst" no
            WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\Main" "Search Page" http://searchbox.digsby.com/
            WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\Main" "Search Bar" http://searchbox.digsby.com/ie
            WriteRegStr HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Internet Explorer\Search" SearchAssistant http://searchbox.digsby.com/ie
            WriteRegStr HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Internet Explorer\Main" "Search Page" http://searchbox.digsby.com/
        FunctionEnd
        '''
        log.info("setting search for %r", self.process_name)

        import _winreg

        with util.traceguard:
            k = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Internet Explorer\\SearchScopes\\', 0, _winreg.KEY_ALL_ACCESS)
            _winreg.SetValueEx(k, 'DefaultScope', None, _winreg.REG_SZ, DIGSBY_SEARCH_UUID_IE)
            k2 = _winreg.CreateKey(k, DIGSBY_SEARCH_UUID_IE)
            _winreg.SetValueEx(k2, 'DisplayName', None, _winreg.REG_SZ, "Google Powered Digsby Search")
            _winreg.SetValueEx(k2, 'URL', None, _winreg.REG_SZ, DIGSBY_SEARCH_URL.encode('xml'))
            k3 = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Internet Explorer\\Main', 0, _winreg.KEY_ALL_ACCESS)
            k4 = _winreg.CreateKey(k3, "Main")
            _winreg.SetValueEx(k4, "Use Search Asst", None, _winreg.REG_SZ, "no")
            _winreg.SetValueEx(k4, "Search Page", None, _winreg.REG_SZ, "http://searchbox.digsby.com/")
            _winreg.SetValueEx(k4, "Search Bar", None, _winreg.REG_SZ, "http://searchbox.digsby.com/ie")
            #FaviconURLFallback http://www.live.com/favicon.ico
            #SuggestionsURLFallback http://api.search.live.com/qsml.aspx?Query={searchTerms}&Market={Language}&FORM=IE8SSC
            k.Close()
            k2.Close()
            k3.Close()
            k4.Close()

        with util.traceguard:
            l = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Internet Explorer\\Main', 0, _winreg.KEY_ALL_ACCESS)
            _winreg.SetValueEx(l, "Search Page", None, _winreg.REG_SZ, "http://searchbox.digsby.com/")
            l2 = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Internet Explorer\\Search', 0, _winreg.KEY_ALL_ACCESS)
            _winreg.SetValueEx(l2, "SearchAssistant", None, _winreg.REG_SZ, "http://searchbox.digsby.com/ie")
            l.Close()
            l2.Close()

        return True

class Chrome(BrowserSettingsEditor):
    process_name = 'chrome.exe'
    keyword = 'digsby-searchbox'

    @property
    def profile_dir(self):
        return (stdpaths.userlocalconfig / 'Google' / 'Chrome' / 'User Data'/ 'Default')

    def is_installed(self):
        return self.profile_dir.isdir()

    def write_prefs(self, new_prefs):
        self.update_json_file('Preferences', new_prefs)

    def update_json_file(self, fname, new_dict):
        fpath = self.profile_dir / fname
        with fpath.open('rb') as f:
            info = json.loads(f.read())

        info.update(new_dict)

        with fpath.open('wb') as f:
            f.write(json.dumps(info))

    def set_homepage(self):
      log.info("setting homepage for %r", self.process_name)
      self.write_prefs({'homepage' : HOMEPAGE_URL,
                        "homepage_is_newtabpage": False,})
      return True

    def set_search(self):
        log.info("setting search for %r", self.process_name)
        db_fpath = self.profile_dir / 'Web Data'
        import sqlite3 as sqlite
        with closing(sqlite.connect(db_fpath)) as c:
            id = None
            with closing(c.execute('SELECT id FROM keywords WHERE keyword = "%(keyword)s";' % dict(keyword = self.keyword))) as r:
                log.info("chrome checking existing row")
                for row in r:
                    id, = row

            search_provider_info = dict(
                short_name = "Digsby Powered Google",
                url = "http://searchbox.digsby.com/search?q={searchTerms}&ie=utf-8&oe=utf-8&aq=t",
                suggest_url = "{google:baseSuggestURL}search?client=chrome&hl={language}&q={searchTerms}",
                favicon_url = "http://www.google.com/favicon.ico",
                keyword = self.keyword,
                input_encodings = 'UTF-8',
                id = id,
                show_in_default_list = 1,
                safe_for_autoreplace = 0,
                originating_url = "",
            )

            if id is None:
                # must create
                search_provider_info.pop('id')
                with closing(c.execute("INSERT INTO keywords (%s) VALUES (%s)" %
                                       (','.join(x[0] for x in sorted(search_provider_info.items())),
                                        ','.join(repr(x[1]) for x in sorted(search_provider_info.items()))))) as r:
                    log.info("chrome creating row")
                    pass

                with closing(c.execute('SELECT id FROM keywords WHERE short_name = "%(short_name)s"' % search_provider_info)) as r:
                    log.info("chrome getting new id")
                    for row in r:
                        id = search_provider_info['id'], = row
                    log.info("\tresult = %r", id)

            search_provider_info['search_url'] = search_provider_info['url']
            search_provider_info['encodings'] = search_provider_info['input_encodings']
            search_provider_info['icon_url'] = search_provider_info['favicon_url']

            # Update fields to make sure they're right
            with closing(c.execute((
              'UPDATE keywords SET '
              'url="%(url)s", '
              'short_name="%(short_name)s", '
              'keyword="%(keyword)s", '
              'suggest_url="%(suggest_url)s", '
              'favicon_url="%(icon_url)s" '
              'WHERE id=%(id)d')
              % search_provider_info)) as r:
                log.info("chrome updating row")
                pass

            c.commit()

        with closing(sqlite.connect(db_fpath)) as c:
            with closing(c.execute('UPDATE meta SET value = %(id)d WHERE key = "Default Search Provider ID";' % search_provider_info)) as r:
                log.info("chrome updating meta table")
                pass
            c.commit()

        search_provider_info.update(enabled = True)
        self.write_prefs({"default_search_provider": search_provider_info})

        return True

class Firefox(BrowserSettingsEditor):
    process_name = 'firefox.exe'
    default_profile = None

    SEARCH_PLUGIN_TXT = \
'''<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"
    xmlns:moz="http://www.mozilla.org/2006/browser/search/">
    <ShortName>Google Powered Digsby Search</ShortName>
    <Description>Google Powered Digsby Search</Description>
    <InputEncoding>UTF-8</InputEncoding>
    <moz:UpdateUrl>http://digsby.com/digsbysearch.xml</moz:UpdateUrl>
    <moz:UpdateInterval>7</moz:UpdateInterval>
    <Image width="16" height="16">data:image/x-icon;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAaRJREFUeNpiVIg5JRURw0A0YAHio943kYV%2B%2Ff33%2BdvvX7%2F%2FMjEx8nKycrGzwKXOiPKzICvdeezLhCV3jp15%2Bfv%2FX0YGhv8MDDxMX2qKTIw0RK10eYD6QYqATvoPBkt3f5K0W9Ew4fjTFz%2F%2Bw8Dm3W8UPeZxqFa%2BevsFyD0twgfVsOfkRxHrtfV9u5BVQ8Crd98%2FffkGYQM1QJ20%2FfSPv79eNxQGYfpSVJADmcvEAHbr7oOX2dj%2FERNKIA2%2F%2F%2Fz%2FxfCDhYVoDUDw5P6vf9%2B5iY0HVmZGQWm%2BN3fff%2Fn2k4eLHS739x%2FDiRs%2Ff%2F%2F5x8HO%2FOHzN3djfqgNjIwMgc6qzLx%2Fpy47j2zY%2Feff06tXhOUucgxeun33AUZGpHh4%2Bvo7t8EyIJqz%2FhpasD59%2B5dNrqdnznZIsEL9ICXCsWuBCwvTv%2FymS5PWPP32ExEALz%2F%2BB5r848cPCJcRaMP9xaYQzofPPzfuvrnj0Jst%2B5%2F8%2Bc4sLPeDkYlRgJc93VPE18NIXkYUmJYQSQMZ%2FP3379uPH7%2F%2F%2FEETBzqJ0WqLGvFpe2LCC4AAAwAyjg7ENzDDWAAAAABJRU5ErkJggg%3D%3D</Image>
    <Url type="text/html" method="GET" template="http://searchbox.digsby.com/search?q={searchTerms}&amp;ie=utf-8&amp;oe=utf-8&amp;aq=t" />
    <Url type="application/x-suggestions+json" method="GET" template="http://suggestqueries.google.com/complete/search?output=firefox&amp;client=firefox&amp;hl={moz:locale}&amp;q={searchTerms}" />
    <moz:SearchForm>http://searchbox.digsby.com</moz:SearchForm>
</OpenSearchDescription>'''

    SEARCH_PREF_LINES = [
        'user_pref("browser.search.defaultenginename", "Google Powered Digsby Search");',
        'user_pref("keyword.URL", "http://searchbox.digsby.com/search?sourceid=navclient&gfns=1&q=");',
    ]

    HOMEPAGE_PREF_LINES = [
        'user_pref("browser.startup.homepage", "%s");' % HOMEPAGE_URL,
    ]


    @property
    def app_dir(self):
        return (stdpaths.userconfig / 'Mozilla' / 'Firefox')

    @property
    def profile_dir(self):
        if self.default_profile is None:
            self.find_default_profile()

        return self.app_dir / self.default_profile

    def find_default_profile(self):
        cf = CF.ConfigParser()
        if not cf.read(self.app_dir / 'profiles.ini'):
            return
        for section in cf.sections():
            if section == 'General':
                continue
            if cf.get(section, 'name') == 'default':
                self.default_profile = path.path(cf.get(section, 'path'))
                break

    def is_installed(self):
        return self.app_dir.isdir()

    def set_search(self):
        log.info("setting search for %r", self.process_name)
        searchplugins = self.profile_dir / 'searchplugins'
        if not searchplugins.isdir():
            with util.traceguard:
                searchplugins.makedirs()
        if searchplugins.isdir():
            with (searchplugins / 'digsby.xml').open('w') as f:
                f.write(self.SEARCH_PLUGIN_TXT)

            return self.write_prefs(self.SEARCH_PREF_LINES)

    def set_homepage(self):
        log.info("setting homepage for %r", self.process_name)
        return self.write_prefs(self.HOMEPAGE_PREF_LINES)

    def write_prefs(self, pref_lines):
        profileprefs = self.profile_dir / 'prefs.js'
        if not profileprefs.isfile():
            return False

        with util.traceguard:
            with profileprefs.open('a') as f:
                f.writelines(pref_lines)
                return True

class BrowserSettingsAddon(addons.AddOn):
    _setup = False
    interval = 5 * 60

    known_browsers = [
                      InternetExplorer,
                      Chrome,
                      Firefox,
                      ]

    def setup(self, *a):
        if self._setup:
            return
        self._setup = True
        self.timer = util.Timer(0, self.check)
        self.timer.start()

        all_browsers = [B() for B in self.known_browsers]
        self.browsers = [b for b in all_browsers if b.is_installed()]
        log.info("detected browsers: %r", self.browsers)

    def check(self):
        wrote_task_info = self.check_installer_files()
        tasks_remaining = self.check_browser_tasks()

        if tasks_remaining:
            self.timer = util.Timer(self.interval, self.check)
            self.timer.start()
            log.debug("rescheduling browser settings task for %r", self.interval)
        else:
            log.debug("all browser settings tasks complete. not rescheduling")

    def check_installer_files(self):
        search = _get_search_filepath()
        homepage = _get_homepage_filepath()
        dosearch = search.isfile()
        dohomepage = homepage.isfile()

        if dosearch or dohomepage:
            log.info("new tasks discovered: dosearch = %r, dohomepage = %r", dosearch, dohomepage)
            my_browser_names = [b.process_name for b in self.browsers]
            self.write_browser_task_info(my_browser_names if dosearch else [], my_browser_names if dohomepage else [])
            if dosearch:
                try:
                    search.remove()
                except Exception:
                    pass
                else:
                    log.debug("removed dosearch flag")
            if dohomepage:
                try:
                    homepage.remove()
                except Exception:
                    pass
                else:
                    log.debug("removed dohomepage flag")

            return True
        return False

    def write_browser_task_info(self, need_search, need_homepage):
        taskinfo_filepath = _get_taskinfo_filepath()
        if not need_search and not need_homepage:
            if taskinfo_filepath.isfile():
                taskinfo_filepath.remove()
                log.info("clearing browser task info data (nothing left to do)")
            return False

        info = {'search' : need_search,
                'homepage' : need_homepage}

        with _get_taskinfo_filepath().open('wb') as f:
            f.write(json.dumps(info))

        log.info("wrote browser task info: %r", info)

    def read_browser_task_info(self):
        taskinfo_path = _get_taskinfo_filepath()
        if not taskinfo_path.isfile():
            return None

        with taskinfo_path.open('rb') as f:
            info = json.loads(f.read())

        return info

    def check_browser_tasks(self):
        info = self.read_browser_task_info()
        log.info("browser settings task info loaded: %r", info)
        if info is None:
            return False

        need_search = info.get('search', [])
        need_homepage = info.get('homepage', [])

        for browser in self.browsers:
            if browser.process_name in need_search:
                if browser.can_edit() and browser.set_search():
                    need_search.remove(browser.process_name)
            if browser.process_name in need_homepage:
                if browser.can_edit() and browser.set_homepage():
                    need_homepage.remove(browser.process_name)

        # if the file was written
        browser_names = [b.process_name for b in self.browsers]
        for browser in need_search[:]:
            if browser not in browser_names:
                need_search.remove(browser)

        for browser in need_homepage[:]:
            if browser not in browser_names:
                need_homepage.remove(browser)

        self.write_browser_task_info(need_search, need_homepage)

        return bool(need_search or need_homepage)

def _get_taskinfo_filepath():
    return (stdpaths.userdata / 'taskinfo.json')

def _get_search_filepath():
    return (stdpaths.userdata / 'dosearch')

def _get_homepage_filepath():
    return (stdpaths.userdata / 'dohomepage')

def set_homepage():
    pass

def set_search():
    with _get_search_filepath().open('wb') as f:
        f.write("yes")

    BrowserSettingsAddon(common.profile()).check()

def set_homepage():
    with _get_homepage_filepath().open('wb') as f:
        f.write("yes")

    BrowserSettingsAddon(common.profile()).check()
