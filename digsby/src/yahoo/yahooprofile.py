'''

Webscraping for Yahoo! Member profiles.

'''
from __future__ import with_statement
from util import threaded, soupify, odict, scrape_clean
from util.primitives.funcs import do
from util.BeautifulSoup import BeautifulStoneSoup
from itertools import izip
from logging import getLogger; log = getLogger('yahooprofile')
from urllib2 import urlopen

profile_url = 'http://profiles.yahoo.com/%s?warn=1'

@threaded
def get(yahooid):
    data = urlopen(profile_url % yahooid).read().decode('utf-8')
    return scrape_profile(data)

def scrape_profile(s):
    # fixup HTML
    s = s.replace(u'&nbsp;', u' ').replace(u'Hobbies:</dd>', u'Hobbies:</dt>')
    soup = BeautifulStoneSoup(s, convertEntities=BeautifulStoneSoup.ALL_ENTITIES,
                              fromEncoding = 'utf-8')
    profile = odict()

    # grab info
    for section in ('basics', 'more'):
        div = soup('div', id='ypfl-' + section)[0].dl
        if div is not None:
            info = [elem.renderContents(None) for elem in div if elem != u'\n']
            profile.update(dictfrompairs(info))

    # grab links
    links = dictfrompairs([e.renderContents(None).replace('<em>','').replace('</em>','')
                           for e in soup('dl', attrs = {'class':'mylinks'})[0].contents if e != u'\n'])

    # construct [list of] tuples for links
    if 'Home Page:' in links: links['Home Page:'] = anchor2tuple(links['Home Page:'])
    linktuples = [anchor2tuple(v) for k, v in sorted(links.items())
                  if k.startswith('Cool Link')]

    # insert newlines between the link tuples.
    finallinks = []
    for i, tuple in enumerate(linktuples):
        finallinks.append(tuple)
        if i != len(linktuples) - 1: finallinks.append(u'\n')
    links['Links:'] = finallinks

    do(links.pop(k) for k in links.keys() if k.startswith('Cool Link'))

    profile.update(links)

    # pull "member since" and "last update"
    for p in soup.findAll('p', attrs = {'class':'footnote'}):
        c = p.renderContents(None)
        for hdr in ('Member Since ', 'Last Update: '):
            if c.startswith(hdr):
                profile[hdr] = c[len(hdr):]

    # remove empty entries
    for k, v in dict(profile).iteritems():
        if isinstance(v, basestring):
            dict.__setitem__(profile, k,
                             None if v.strip() in ('', 'No Answer') else scrape_clean(v))

    profile.pop('Yahoo! ID:', None)

    return profile

def dictfrompairs(info):
    return dict(izip(info[::2], info[1::2]))  # make into a dict by zipping pairs

def anchor2tuple(s):
    '''
    Our profile box takes tuples for links.

    Returns (u"http://www.google.com", u"http://www.google.com") for
    <a href="http://www.google.com">http://www.google.com</a>.
    '''

    if not s: return None
    a = soupify(s).a
    return (a['href'], a.renderContents()) if a else None




