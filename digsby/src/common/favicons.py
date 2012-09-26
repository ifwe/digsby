'''

downloads and caches favicons

TODO:
  - <link rel> style favicons
  - use "http://www.google.com/s2/favicons?domain=www.reddit.com" as a backup?
'''

from __future__ import with_statement

from threading import RLock, currentThread
from time import time
import wx

from util.primitives.funcs import WeakDelegate
from util.cacheable import get_cache_root
from common import netcall
import common.asynchttp as asynchttp

from logging import getLogger; log = getLogger('favicons')

__all__ = 'favicon',

FETCHING = object()
EMPTY    = object()

FAVICON_EXPIRE_SECS = 60 * 60 * 24 * 30  # one month
FAVICON_EXPIRE_ERROR_SECS = 60 * 60 * 24 # one day

FAVICON_CACHE_DIR = 'favicons'  # directory in the cache folder to store favicons
ICON_EXT = '.ico'
LINK_EXT = '.redirect'          # extension for domain shortcuts

MAX_SUBDOMAIN_CHECK = 5         # don't attempt to strip more than this many subdomains
                                # (i.e, www.abc.foo.com -> abc.foo.com -> foo.com)

_favicons_lru = {}              # caches {domain: wxBitmap}
_domain_lru = {}                # caches {domain: real_domain}

manual_redirects = {
    'gmail.com':              'mail.google.com',
    'facebookmail.com':       'www.facebook.com',
    'papajohns-specials.com': 'papajohns.com',
    'papajohnsonline.com' :   'papajohns.com',
}

def favicon(domain):
    'Fetches an icon for the given domain.'

    assert currentThread().getName() == 'MainThread', "favicon must be called from the main thread"
    assert isinstance(domain, basestring), "favicon takes a string, you gave %r" % domain

    cached = get_cached(domain)

    if cached in (FETCHING, EMPTY):
        return None
    elif cached is not None:
        return cached
    else:
        fetch_favicon(domain)

    return None


# delegate to inform the GUI when new icons arrive
# called with one argument--the domain
on_icon = WeakDelegate()

def cache_path():
    "Returns the path to the favicon cache directory, making it if it doesn't exist."

    p = get_cache_root() / FAVICON_CACHE_DIR
    if not p.isdir():
        p.makedirs()

    return p

def clear_cache():
    'Clears the favicon cache.'

    cache_path().rmtree()

def get_icon_domain(domain):
    domain = manual_redirects.get(domain, domain)

    if domain in _domain_lru:
        return _domain_lru[domain]

    root = cache_path()
    p = root / (domain + LINK_EXT)

    if p.isfile():
        # if there is a domain.domainlink file for this domain,
        # read the real domain from the file and use that instead.
        result = p.bytes()
    else:
        result = domain

    _domain_lru[domain] = result
    return result

def get_cached(domain, done_fetching = False):
    domain = get_icon_domain(domain)

    # is it already stored in memory?
    if domain in _favicons_lru:
        return _favicons_lru[domain]

    # do we already have a pending HTTP request for this domain?
    if not done_fetching and is_fetching(domain):
        return FETCHING

    cache_file = cache_path() / domain + ICON_EXT

    # no file means no cached icon
    if not cache_file.isfile():
        return None

    # if the icon is older than our expiration length, return None to
    # to redownload
    age = time() - cache_file.mtime
    if not done_fetching:
        if age > FAVICON_EXPIRE_SECS or age < 0:
            log.info('expiring favicon for %s' % domain)
            cache_file.remove()
            return None

    # empty file means we've already looked it up, and didn't find anything
    if cache_file.size == 0:
        if age > FAVICON_EXPIRE_ERROR_SECS:
            log.info('expiring empty favicon cache file for %s' % domain)
            cache_file.remove()
            return None

        log.debug('%s has an empty cache file', domain)
        _favicons_lru[domain] = EMPTY
        return EMPTY

    # try loading the image
    try:
        log.debug('loading favicon cache file for %s', domain)

        bitmap = wx.Bitmap(cache_file)
        if not bitmap.IsOk():
            raise Exception('bitmap.IsOk() != True')
    except Exception, e:
        log.warning("Error loading image file: %s" % e)

        # if it fails, remove bad the image
        cache_file.remove()
    else:
        # return the wxBitmap
        _favicons_lru[domain] = bitmap

        # notify any listeners that we've got a new icon
        on_icon(domain)
        return bitmap

def cache_icon(domain, linked_domains, data):
    assert isinstance(domain, basestring)
    assert all(isinstance(d, basestring) for d in linked_domains)
    assert isinstance(data, str)

    cp = cache_path()

    icon_file = cp / domain + ICON_EXT
    if icon_file.isfile():
        log.warning('caching file to %s but it already exists', icon_file)

    # write out the actual image data
    icon_file.write_bytes(data)

    # write out "shortcut" domains
    for d in linked_domains:
        (cp / d + LINK_EXT).write_bytes(domain)

    # invalidate the domain link cache
    _domain_lru.clear()

    # and tell the GUI thread to make an image (and cache the image in memory)
    # out of the new data
    wx.CallAfter(get_cached, domain, done_fetching = True)

    log.debug('cached %d bytes of data for %r (linked: %s)',
              len(data), domain, ', '.join(linked_domains))

def cache_noicon(domain, linked_domains):
    # Caching an empty string records that there was an error looking up the
    # icon, and that we shouldn't do it again (for awhile).
    return cache_icon(domain, linked_domains, '')

def link_tag_url(html):
    '''
    extracts a relative url from an HTML document's link tag, like

        <link rel="shortcut icon" href="images-template/favicon.ico" type="image/x-icon" />

    '''
    from lxml.etree import HTML
    doc = HTML(html)
    link_tag = doc.find('.//link[@rel="shortcut icon"]')
    if link_tag is not None:
        favicon_url = link_tag.get('href', '')
        if favicon_url:
            return favicon_url

def fetch_favicon(domain, linked_domains = None):
    start_domain = domain
    real_domain = get_icon_domain(domain)
    if linked_domains is None:
        linked_domains = []
    if real_domain != domain:
        linked_domains.append(domain)

    domain = real_domain

    wwwdomain = 'www.' + domain
    if not (domain.startswith('www') or wwwdomain in linked_domains):
        linked_domains.append(domain)
        domain = wwwdomain

    log.info('Using %r for %r (linked = %r)', domain, start_domain, linked_domains)
    url = 'http://' + domain + '/favicon.ico'

    def on_success(req, resp):
        data = resp.read()
        log.info('httpopen(%s): received %d bytes of data', url, len(data))
        log.info('%r', resp)
        cache_icon(domain, linked_domains, data)
        unset_fetching([domain])

    def on_error(req=None, resp=None):
        log.error('on_error for domain=%r, linked_domains=%r', domain, linked_domains)

        if 1 < domain.count('.') < MAX_SUBDOMAIN_CHECK:
            # try stripping a subdomain off and making another request
            new_domain = '.'.join(domain.split('.')[1:])
            wx.CallAfter(fetch_favicon, new_domain, linked_domains + [domain])

            # return now so that the original domain remains in the "fetching"
            # state.
            return
        else:
            log.error('No more subdomains to try for %r. Error response was: %r', domain, resp)
            cache_noicon(domain, linked_domains)

        unset_fetching(linked_domains + [domain])

    def on_redirect(req):
        if 'favicon' not in req.get_selector():
            new_url = 'http://%s/%s' % (req.get_host(), 'favicon.ico')
            old_req = req._orig_request
            checked_urls = getattr(old_req, '_favicons_checked_urls', set())
            if new_url in checked_urls:
                return None

            checked_urls.add(new_url)
            req = req.copy(url = new_url)
            req._favicons_checked_urls = old_req._favicons_checked_urls = checked_urls
            req._orig_request = old_req
        return req

    with fetch_lock:
        if domain in currently_fetching:
            log.info('already fetching %r', url)
            return
        else:
            log.info('getting %r', url)
            currently_fetching.add(domain)

    netcall(lambda: asynchttp.httpopen(url,
                                       success = on_success,
                                       error = on_error,
                                       on_redirect = on_redirect))

# keep a set (protected with a lock) of currently-fetching domains
# TODO: make asynchttp do this for us

fetch_lock = RLock()
currently_fetching = set()

def set_fetching(domain):
    global currently_fetching
    with fetch_lock:
        currently_fetching.add(domain)

def unset_fetching(domains):
    '''
    unsets 'fetching' for each domain in 'domains'
    '''
    global currently_fetching
    with fetch_lock:
        currently_fetching -= set(domains)

def is_fetching(domain):
    global currently_fetching
    with fetch_lock:
        return domain in currently_fetching
