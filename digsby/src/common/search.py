'''
search utils
'''

def enabled_searches():
    return [e for e in searches if e.enabled]

class Search(object):
    'base class for all available external searches'

    def __init__(self, name, gui_name, enabled = True):
        self.name = name
        self.gui_name = gui_name
        self.enabled = enabled

    def dict(self, **kws):
        d = dict(name=self.name, enabled=self.enabled)
        d.update(kws)
        return d

class WebSearch(Search):
    'external searches whose action is to launch a browser URL'

    replstring = '$$query$$'

    def __init__(self, name, gui_name, url):
        Search.__init__(self, name, gui_name)
        self.url = url

    def search(self, query):
        url = self.url.replace(self.replstring, query.encode('url'))
        launch_browser(url)

    def __repr__(self):
        return '<WebSearch %s%s>' % (self.gui_name, '' if self.enabled else ' (disabled)')

# global list of search objects
searches = []

def launch_browser(url):
    import wx; wx.LaunchDefaultBrowser(url)

_did_link_prefs = False
def link_prefs(prefs):
    global _did_link_prefs

    if _did_link_prefs:
        return

    _did_link_prefs = True
    prefs.link('search.external', on_external_prefs,
            obj=on_external_prefs, callnow=True)

def on_external_prefs(external):
    global searches

    by_name = dict((engine.name, engine) for engine in all_search_engines)

    new_searches = []

    found_searches = set()
    to_remove = set()
    for ex in external:
        name, enabled = ex.get('name'), ex.get('enabled', False)
        found_searches.add(name)

        if name not in by_name:
            to_remove.add(name)
            continue

        engine = by_name[name]
        engine.enabled = enabled
        new_searches.append(engine)

    # Add all searches that were in defaults.yaml but not appearing in user prefs
    # (for when we add a new search). Maintain original position (will re-order users'
    # search list).
    for name in by_name:
        if name not in found_searches:
            v = {'name' : name,
                 'enabled': by_name[name].enabled}

            import common
            order = common.profile.defaultprefs.get('search.external', [])
            if v in order:
                default_pos = order.index(v)
            else:
                default_pos = len(new_searches)
            new_searches.insert(default_pos, by_name[name])
            external.append(v)

    # Remove preferences for unknown searches
    external[:] = [x for x in external if x.get('name') not in to_remove]

    searches[:] = new_searches

all_search_engines = [
    WebSearch('google', u'Google',
              'http://search.digsby.com/search.php?q=$$query$$&sa=Search&cx=partner-pub-0874089657416012:7ev7ao6zrit&cof=FORID%3A10&ie=UTF-8#1166'),

    WebSearch('amazon', u'Amazon',
              'http://www.amazon.com/gp/search?ie=UTF8&keywords=$$query$$&tag=digsby-20&index=blended&linkCode=ur2&camp=1789&creative=9325'),

    WebSearch('ebay', u'Ebay',
              'http://rover.ebay.com/rover/1/711-53200-19255-0/1?type=3&campid=5336256582&toolid=10001&referrer=www.digsby.com&customid=&ext=$$query$$&satitle=$$query$$'),

    WebSearch('newegg', u'NewEgg',
              'http://www.newegg.com/Product/ProductList.aspx?Submit=ENE&DEPA=0&Order=BESTMATCH&Description=$$query$$&x=0&y=0'),

    WebSearch('itunes', u'iTunes',
              'http://www.apple.com/search/ipoditunes/?q=$$query$$'),

    WebSearch('twitter', u'Twitter',
              'http://search.twitter.com/search?q=$$query$$'),

    WebSearch('facebook', u'Facebook',
              'http://www.facebook.com/s.php?init=q&q=$$query$$'),

    WebSearch('linkedin', u'LinkedIn',
              'http://www.linkedin.com/search?keywords=$$query$$&sortCriteria=Relevance&proposalType=Y&pplSearchOrigin=ADVS&newnessType=Y&searchLocationType=Y&viewCriteria=1&search='),

    WebSearch('youtube', u'YouTube',
              'http://www.youtube.com/results?search_type=&search_query=$$query$$'),

    WebSearch('wikipedia', u'Wikipedia',
              'http://en.wikipedia.org/wiki/Special:Search?search=$$query$$'),

    WebSearch('technorati', u'Technorati',
              'http://technorati.com/search/$$query$$'),

    WebSearch('oneriot', u'OneRiot',
              'http://www.oneriot.com/search?q=$$query$$&spid=eec0ecbd-1151-4b26-926d-82a155c73372&p=digsby&ssrc=blist'),

    WebSearch('bing', u'Bing',
              'http://www.bing.com/search?q=$$query$$'),
]

