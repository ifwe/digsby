'''
injects ads into social news feeds
'''

if __name__ == '__main__':
    import gettext; gettext.install('Digsby')
    import Digsby

import os.path
import lxml.etree
import lxml.html
import datetime
import traceback
import threading
import hooks
import time
import random
import common
from path import path
import common.asynchttp as asynchttp
from util import LRU
from util.net import UrlQuery, bitly_shortener
from util.primitives.mapping import Storage as S
from util.primitives.funcs import Delegate
from util.primitives.error_handling import traceguard, try_this
from operator import itemgetter

from logging import getLogger; log = getLogger('feed_trends')

SHUFFLE_ADS = True
SHORTEN_AD_URLS = False
HELP_PREF = 'social.feed_ads_help'
MAX_ADS = 100 # number of ads to keep in memory
KEEP_OLD_ADS = False

#
# hooks
#

def on_social_feed_updated(context, ids):
    if feed_ads_enabled():
        feed_ads().feed_for_context(context).update_ids(ids)

def on_social_feed_created(ctx):
    if feed_ads_enabled():
        feed_ads().start_ad_request()

def on_social_feed_iterator(info):
    if feed_ads_enabled():
        return feed_ads().wrap_iterator(info)
    else:
        return info

def on_getresource(resource_name):
    if resource_name == 'trend_details.tenjin':
        return _get_feed_trend_resource(resource_name)

def _get_feed_trend_resource(resource_name, context=None):
    return path(os.path.join(os.path.dirname(__file__), 'res', resource_name)).abspath()

def get_param(args, name):
    return args.get('params', [{}])[0].get(name, None)

def get_ad(args):
    ad_id = get_param(args, 'ad_id')
    return feed_ads().get_ad_by_id(ad_id)

def share_ad(ad):
    if ad.shortened_url is None:
        return append_ad_link(ad, share_ad)

    series = filter(None, [ad.source or None, ad.title or None])

    value = u' - '.join(series)
    if ad.shortened_url:
        value += ' - %s' % ad.shortened_url

    # only fire "share" when user sets the ad as their status.
    def submit_callback(message, accounts):
        hooks.notify('digsby.statistics.feed_ads.share')

    import wx
    wx.GetApp().SetStatusPrompt('ALL', value, submit_callback=submit_callback)

def on_share_ad(account_key, args):
    ad = get_ad(args)
    if ad is not None:
        share_ad(ad)

    return True

def on_click_ad(account_key, args):
    ad = get_ad(args)
    if ad is not None:
        ad.notify_click()

    return True

_sent_impression = dict()
MAX_IMPRESSIONS_SENT = 100

def prune_sent_impressions(impressions):
    over = len(impressions) - MAX_IMPRESSIONS_SENT
    if over <= 0:
        return

    by_time = sorted(impressions.iteritems(), key = itemgetter(1))
    for ad_id, time in by_time[:over]:
        impressions.pop(ad_id)

def on_ad_impression(account_key, args):
    ad = get_ad(args)
    if ad is not None:
        ad_id = ad.id
        if ad_id not in _sent_impression:
            _sent_impression[ad_id] = time.time()
            prune_sent_impressions(_sent_impression)
            ad.notify_impression()
            log.debug('ad impression: %r', ad_id);

    return True

def on_disable_trends_help(account_key, args):
    common.setpref(HELP_PREF, False)
    return True


def on_infoboxjs(account):
    return '''
window.shareAd = function(id) {
    D.notify('share_ad', {ad_id: id});
}

window.adClick = function(id) {
    D.notify('ad_click', {ad_id: id});
}

// called any time a feed we're injecting ads into scrolls.
function _adScroll() {

    var pageY = window.pageYOffset;
    var pageBottom = pageY + window.innerHeight;

    function visible(elem) {
        var offset = $(elem).offset();
        return offset.top >= pageY && offset.top < pageBottom;
    }

    var divs = document.getElementsByClassName('adImpressionDiv');

    for (var i = 0; i < divs.length; ++i) {
        var div = divs[i];

        function notifyImpression() {
            div.setAttribute('did_impression', true);
            var ad_id = parseInt(div.getAttribute('ad_id'), 10);
            D.notify('ad_impression', {ad_id: ad_id});
        }

        var src = div.getAttribute('lazy_src');
        if (src !== undefined && visible(div)) {
            notifyImpression();

            div.removeAttribute('lazy_src');
            div.className = '';

            // load the OneRiot tracking gif
            var img = document.createElement('img');
            img.setAttribute('width', 1);
            img.setAttribute('height', 1);
            img.setAttribute('src', src);

        } else if (!div.getAttribute('did_impression'))
            notifyImpression();
    }
}

swapIn(function() { $(window).bind('scroll', _adScroll); });
swapOut(function() { $(window).unbind('scroll', _adScroll); });
swapIn(function() { setTimeout(_adScroll, 500); });

window.trendsHelp = function() {
    $('body').append("<div id='trendHelpBg' style='z-index: 10000; background-image: url(<<BGURL>>); position: fixed; top: 0px; left: 0px; width: 100%; height: 100%; text-align: center;'>");
    $('#trendHelpBg').click(function() { $(this).remove(); });
    var popup = $("<div id='trendHelpText' style='border: 1px #c0c0c0 solid; padding: 10px; font-family: arial; font-size: 10pt; z-index: 10001; background-color: #fff; position: fixed; top: 30px; width: 90%; left: auto; text-align: left; color: #000;'>");
    popup.html("Digsby can now bring trending news stories to your social feeds! Top stories come from <a style='font-size: 10pt; font-family: arial;' href='http://oneriot.com'>OneRiot</a> and are chosen based on what Twitter, Facebook, and Myspace are buzzing about today. Some stories are sponsored by publishers and help support Digsby development. You can enable or disable this feature in Preferences > General & Profile.<p><div style='text-align:right;'><a style='font-size: 10pt; font-family: arial;' href='javascript:closeTrendsHelp();'>Close</a></div>");
    popup.css('visibility', 'hidden');
    $('#trendHelpBg').append(popup);
    popup.css('top', $(window).height()/2 - $('#trendHelpText').height()/2);
    popup.css('visibility', 'visible');
    D.notify('disable_trends_help');
}

window.closeTrendsHelp = function() {
    $('#trendHelpBg').remove();
}

swapOut(closeTrendsHelp);

'''.replace('<<BGURL>>', (path(__file__).parent / 'helpbg.png').url())

def on_infoboxcontext(ctx, acct):
    opts = feed_ads().opts

    if opts['pinned']:
        show_timestamp = False
    else:
        show_timestamp = True

    ctx.update(feed_trends_help=common.pref(HELP_PREF, default=True),
               feed_trends_classes=feed_ads().opts['css_classes'],
               feed_trends_show_timestamp=show_timestamp,
               feed_trends_resource=_get_feed_trend_resource)


#
#
#

def feed_ads_enabled():
    return common.pref('social.feed_ads', default=True)

# How many feed item positions to skip before showing another ad.
SHOW_AD_EVERY = 7

def oneriot_ad_url(appId):
    return UrlQuery('http://api.ads.oneriot.com/search',
        appId=appId,
        version='1.1',
        limit='20',
        format='XML')

class AdPlaceholder(object):
    '''
    Acts as a container for an ad in a social feed. Held in AdPlacememt's "ids"
    list. self.ad may be None if the ad hasn't returned from the network yet.
    '''
    def __init__(self):
        self.ad = None

    def __repr__(self):
        return '<AdPlaceholder %r>' % self.ad

    def finished(self):
        return self.ad is not None and self.ad is not sentinel

def isadspot(o):
    return isinstance(o, AdPlaceholder)

def isfinishedad(o):
    return isadspot(o) and o.finished()

class AdPlacement(object):
    '''
    keeps track of the placement of ads in one feed
    '''
    def __init__(self, feed_ads, context):
        self.feed_ads = feed_ads
        self.context = context

        # the latest known list of ids. AdPlaceholder objects are inserted into
        # this list by update_ids
        self.ids = []

        self.afters = {}

        self.lock = threading.RLock()

    def update_ids(self, new_ids):
        '''
        Repositions existing ads, and inserts new ones if necessary based on the
        ids given in new_ids.
        '''

        new_ids = new_ids[:]
        with self.lock:
            newads = self.position_ads(new_ids)
            self.ids = new_ids

            if newads:
                assert all(adp.ad is None for adp in newads)
                self.feed_ads.request_new_ads(newads, self._update_afters)

    def position_ads(self, new_ids):
        opts = self.feed_ads.opts
        first_index = self.feed_ads.first_ad_index()

        if opts['pinned']:
            if (not self.ids or
                self.ids[1:] != new_ids[:len(self.ids)-1] or
                not isadspot(self.ids[0])):
                newads = pin_single_ad(new_ids, self.ids, first_index)
            else:
                new_ids.insert(0, self.ids[0])
                newads = []
        else:
            reposition_existing_ads(self.ids, new_ids)
            newads = insert_new_ads(new_ids, self.feed_ads.first_ad_index())

        return newads

    def _update_afters(self):
        with self.lock:
            old_afters = self.afters
            self.afters = dict((self.ids[i-1], id) for i, id in enumerate(self.ids) if isfinishedad(id))
            if old_afters != self.afters:
                hooks.notify('social.feed.mark_dirty', self.context)

    def ad_first(self):
        if self.ids and isfinishedad(self.ids[0]):
            return self.ids[0].ad

    def ad_after_id(self, id):
        'returns a NewsItem object if it should follow the id given.'

        try:
            ad_placeholder = self.afters[id]
        except KeyError:
            return None
        else:
            return ad_placeholder.ad

def reposition_existing_ads(old_ids, new_ids):
    '''Given old_ids (a list of ids and AdPlaceholder objects) attempts to insert those
    same AdPlaceholder objects into new_ids so that they are in the same position relative
    to the ids around them in old_ids.'''

    # find any existing ads, and keep track of the set of ids that appeared before each
    before = [(id, set(old_ids[:i])) for i, id in enumerate(old_ids) if isadspot(id)]

    # attempt to place those ads in the same locations in the new_ids list
    for ad, ids_before in before:
        for i in range(len(new_ids)-1, -1, -1):
            if new_ids[i] in ids_before:
                new_ids.insert(i+1, ad)
                break

def pin_single_ad(new_ids, old_ids, first_index):
    if old_ids and isadspot(old_ids[0]) and not getattr(old_ids[0].ad, 'did_notify_impression', False):
        # pinned ads which haven't been seen yet just stay at the top
        new_ids.insert(first_index, old_ids[0])
        return []
    else:
        newad = AdPlaceholder()
        new_ids.insert(first_index, newad)
        return [newad]

def insert_new_ads(new_ids, first_index):
    '''
    Given a list of ids and AdPlaceholder objects, inserts new AdPlaceholder objects into
    new_ids at the correct locations.

    Returns a sequence of the new AdPlaceholder objects (which are all now also in their
    spots in new_ids).
    '''

    if not new_ids:
        return []

    # find the index of the existing ad closest to the top of the feed
    for i, id in enumerate(new_ids):
        if isadspot(id):
            earliest_ad_index = i
            break
    else:
        earliest_ad_index = -1

    newads = []
    def new_ad(i):
        newad = AdPlaceholder()
        newads.append(newad)
        new_ids.insert(i, newad)

    # if there are no ads, then insert one early in the feed, and then every so many after that
    if earliest_ad_index == -1:
        i = first_index
        new_ad(i)
        i += SHOW_AD_EVERY
        while i < len(new_ids) and len(newads) < 2:
            new_ad(i)
            i += SHOW_AD_EVERY
    else:
        # otherwise, insert new ads every so many positions away from the ones that are already there.
        while earliest_ad_index - SHOW_AD_EVERY > 0:
            new_ad(earliest_ad_index - SHOW_AD_EVERY)
            earliest_ad_index -= SHOW_AD_EVERY

        # only allow two ads on any one feed.
        remove_old_ads(new_ids)

    return newads



def remove_old_ads(ids):
    count = 0
    for i, id in enumerate(ids[:]):
        if isinstance(id, AdPlaceholder):
            count += 1
            if count > 2:
                ids.remove(id)

def default_ad_source(campaign):
    # return OneRiotAdSource(campaign)
    return CompositeAdSource(campaign)

class FeedAds(object):

    def __init__(self, source=None, time_secs=time.time, opts=None):
        self.feeds = {}

        self.opts = opts if opts is not None else choose_ad_options()

        log.info('feed trends chose option set: %r', self.opts)

        if source is None:
            source = default_ad_source(self.opts['campaign'])

        self.ads_by_ids = LRU(MAX_ADS)
        self.ad_queue = AdQueue(source, time_secs)

        self.new_ad_request_serial = 0
        self.new_ad_request_count = 0

    def first_ad_index(self):
        idx = self.opts['startpos']

        if isinstance(idx, tuple): # tuple means "choose random number in range"
            return random.randint(*idx)

        return idx

    source = property(lambda self: self.ad_queue.source,
                      lambda self, src: setattr(self.ad_queue, 'source', src))

    append_short_links = property(lambda self: self.ad_queue.append_short_links,
                                  lambda self, v: setattr(self.ad_queue, 'append_short_links', v))

    def start_ad_request(self):
        self.ad_queue.once_have_ads(None)

    def ad_created(self, ad):
        self.ads_by_ids[hash(ad)] = ad

    def get_ad_by_id(self, id):
        return self.ads_by_ids.get(id)

    def feed_for_context(self, context):
        try:
            feed = self.feeds[context]
        except KeyError:
            feed = self.feeds[context] = AdPlacement(self, context)

        return feed

    def request_new_ads(self, new_ads, on_done):
        #print 'request_new_ads', len(new_ads)

        self.new_ad_request_serial += len(new_ads)

        ctx = dict()
        new_ads = new_ads[:]

        ctx['i'] = 0
        new_ads[ctx['i']].ad = sentinel
        def on_ad(ad):
            if ad is not None:
                new_ads[ctx['i']].ad = ad
                self.ad_created(ad)
                ctx['i'] += 1
                if ctx['i'] >= len(new_ads):
                    on_done()
                else:
                    self.get_new_ad(on_ad)
            else:
                on_done()

        self.get_new_ad(on_ad)

    def wrap_iterator(self, info):
        original_iterator = iter(info.iterator)

        #print
        #print
        #print '-'*80
        #print 'wrapping iterator, afters:'
        #from pprint import pprint

        feed = self.feed_for_context(info.id)

        #pprint(afters)

        def feedad(ad, prev_item=None):
            return transform_ad(info, ad, prev_item, self.opts['linkstyle'])

        def newiter():
            first_item = original_iterator.next()

            first_ad = feed.ad_first()
            if first_ad is not None:
                yield feedad(first_ad, first_item)

            prev_item, prev_id = first_item, first_item.id
            yield first_item

            for i, item in enumerate(original_iterator):
                id = item.id
                if prev_item is not None:
                    ad = feed.ad_after_id(prev_id)
                    if ad is not None:
                        yield feedad(ad, prev_item)

                prev_item, prev_id = item, id
                yield item

        info.iterator = newiter()
        return info

    def get_new_ad(self, cb):
        self.new_ad_request_count += 1
        self.ad_queue.next_ad(cb)

class AdQueue(object):

    def __init__(self, source, time_secs):
        self.source = source

        self.request_callbacks = Delegate()
        self.requesting = False
        self.ads = None

        self.ad_index = -1

        self.append_short_links = SHORTEN_AD_URLS

    def needs_request(self):
        return self.ads is None or self.ad_index >= len(self.ads) - 2

    def next_ad(self, cb):
        def _have_ads():
            if not self.ads:
                return cb(None)
            else:
                self.ad_index += 1
                ad = self.ads[self.ad_index % len(self.ads)]
                cb(ad)

                @wx.CallAfter
                def after():
                    win = FeedTrendsDebugWindow.RaiseExisting()
                    if win is not None:
                        win.update_arrow(self.ad_index)

        self.once_have_ads(_have_ads)

    def once_have_ads(self, cb):
        if self.requesting:
            if cb is not None:
                self.request_callbacks.append(cb)
        elif self.needs_request():
            if cb is not None:
                self.request_callbacks.append(cb)
            self.request_new_ads()
        else:
            if cb is not None:
                cb()

    def request_new_ads(self, cb=None):
        self.requesting = True

        def on_ads(ads):
            if SHUFFLE_ADS:
                random.shuffle(ads)

            self.requesting = False

            if KEEP_OLD_ADS:
                if self.ads is not None:
                    ads.extend(self.ads)
                ads[:] = ads[:MAX_ADS]

            self.ads = ads
            self.ad_index = -1

            @wx.CallAfter
            def after():
                win = FeedTrendsDebugWindow.RaiseExisting()
                if win is not None:
                    log.info('updated feed trends debug window')
                    win.received_ads(feed_ads())

            self.request_callbacks.call_and_clear()

        def on_ads_error(req = None, resp=None):
            self.requesting = False
            self.request_callbacks.call_and_clear()

        log.info('requesting new ad pool')
        self.source.request_ads(on_ads, on_ads_error)

_feed_ad_obj = None
def feed_ads():
    'returns a global singleton FeedAds object used by the hooks'

    global _feed_ad_obj
    if _feed_ad_obj is None:
        _feed_ad_obj = FeedAds()
    return _feed_ad_obj

def transform_ad(info, ad, prev_item, linkstyle):
    t = datetime.datetime.now().isoformat()
    _ad = ad

    text = ad.feed_text()
    ad.set_linkstyle(linkstyle)

    if info.id.startswith('twitter_'):
        ad.set_created_time(prev_item.created_at if prev_item is not None else t)

        ad = S(id=hash(ad),
                 user=S(profile_image_url=ad.source_logo_url,
                        screen_name=ad.source),
                 text=text,
                 link_text=_ad.link_text,
                 tweet_type='timeline',
                 created_at=_ad.created_time,
                 has_controls=False,
                 user_url=ad.redirect_url,
                 tracking_url=ad.tracking_url,
                 keyword=ad.keyword,
                 content=ad.content,
                 redirect_url=ad.redirect_url)
    elif info.id.startswith('facebook_'):
        ad.set_created_time(prev_item.created_time if prev_item is not None else t)

        id = hash(ad)
        ad = S(**ad._asdict())
        ad.id=id
        ad.created_time=_ad.created_time
        ad.feed_text=lambda: text
        ad.link_text=_ad.link_text
    elif info.id.startswith('myspace_'):
        ad.set_created_time(prev_item.updated_parsed if prev_item is not None else t)

        id = hash(ad)
        ad = S(**ad._asdict())
        ad.id=id
        ad.updated_parsed = _ad.created_time
        ad.feed_text=lambda: text
        ad.link_text = _ad.link_text
    else:
        ad.set_created_time(getattr(prev_item, 'created_time', None) or time.time())

    try:
        ad._isad = True
    except AttributeError:
        pass

    return ad

def isad(ad):
    return isinstance(ad, NewsItem) or getattr(ad, '_isad', False)

class NewsItem(object):
    _isad = True
    __slots__ = '''_isad
                   title
                   display_url
                   snippet
                   source
                   source_logo_url
                   redirect_url
                   tracking_url
                   shortened_url
                   _text
                   _short_url
                   _long_url
                   link_text
                   created_time
                   keyword
                   content
                   show_snippet
                   did_notify_impression
                   '''.split()

    def __init__(self, title, display_url, snippet, source, source_logo_url, redirect_url, tracking_url, shortened_url=None, keyword=None, content=None, show_snippet=False):
        self.title = title
        self.display_url = display_url
        self.snippet = snippet
        self.source = source
        self.source_logo_url = source_logo_url
        self.redirect_url = redirect_url
        self.tracking_url = tracking_url
        self.shortened_url = shortened_url

        self._text = None
        self._short_url = None
        self._long_url = None
        self.link_text = None
        self.created_time = None

        self.keyword = keyword or _('Trending News')
        self.content = content if content is not None else {}
        self.show_snippet = show_snippet

        self.did_notify_impression = False

    def notify_click(self):
        hooks.notify('digsby.statistics.feed_ads.click')

    def notify_impression(self):
        self.did_notify_impression = True
        self._notify_impression_hook()

    def _notify_impression_hook(self):
        hooks.notify('digsby.statistics.feed_ads.impression')

    def shortened_url_html(self, display_text):
        shortened_url = self.redirect_url
        shortened_url_display = display_text

        return '<a onclick="adClick(%(id)s);" href="%(redirect)s" title="%(tooltip)s">%(short_display)s</a>' % \
                    dict(short=shortened_url, short_display=shortened_url_display,
                         redirect=self.redirect_url, tooltip=self.display_url, id=self.id)

    def feed_text(self):
        if self.show_snippet:
            return u'<a onclick="adClick(%s);" href="%s">%s</a> %s' % (
                self.id, self.redirect_url, self.title, self.snippet)

        return self._text or (u'%s' % self.title)

    def _serializable_attrs(self):
        return NewsItem.__slots__

    def _asdict(self):
        return dict((a, getattr(self, a)) for a in self._serializable_attrs())

    def __eq__(self, o):
        return self.__class__ == o.__class__ and self._hash_values() == o._hash_values()

    def _hash_values(self):
        # don't include snippet or shortened_url, which change
        return self.title, self.display_url, self.source

    def __neq__(self, o):
        return not self.__eq__(o)

    def __hash__(self):
        return hash(self._hash_values())

    def __repr__(self):
        return '<NewsItem %r>' % self.title

    def set_linkstyle(self, linkstyle):
        short_url, long_url = linkstyle(self)

        text = self.feed_text()

        if short_url is not None:
            short_url = self.shortened_url_html(short_url)
            text += ' ' + short_url

        if long_url is not None:
            long_url = self.shortened_url_html(long_url)

        self._text = text
        self._short_url = short_url
        self.link_text = self._long_url = long_url

    def set_created_time(self, t):
        self.created_time = t or datetime.datetime.now().isoformat()

    id = property(lambda self: hash(self))

def NewsItem_from_xml(ns, e, filter_html=True):
    def find(s):
        elem = e.find(ns + s)
        return elem.text if elem is not None else ''

    source_logo = e.find(ns+'source-logo')
    source_logo_url = source_logo.find(ns+'url') if source_logo is not None else None
    source_logo_url = source_logo_url.text if source_logo_url is not None else ''

    snippet = find('snippet')
    title = find('title')

    if filter_html:
        snippet = strip_html(snippet) if snippet is not None else None
        title = strip_html(title)

    return NewsItem(title = title,
                    display_url = find('display-url'),
                    snippet = snippet,
                    source = find('source'),
                    source_logo_url = source_logo_url,
                    redirect_url = find('redirect-url'),
                    tracking_url = find('tracking-url'),
                    shortened_url = None)

class NewsItemList(list):
    __slots__ = 'version', 'time', 'max_age'

    def __init__(self, version, time, max_age, items):
        self.version = version
        self.time = time
        self.max_age = max_age
        self[:] = items

    @staticmethod
    def from_xml(xml, filter_html=True):
        if not xml or not xml.strip():
            return []

        results = lxml.etree.fromstring(xml)

        ns = results.nsmap.get(None, '')
        if ns: ns = '{%s}' % ns

        find = lambda s: results.find(ns + s)

        return NewsItemList(
            version = find('version'),
            time = try_this(lambda: int(find('time').text), 0),
            max_age = try_this(lambda: int(find('max-age').text), 1800),
            items = (NewsItem_from_xml(ns, e, filter_html=filter_html) for e in find('featured-result-list')))

class CompositeAdSource(object):

    def __init__(self, campaign):
        self.sources = [clz(campaign)
                        for clz in self._ad_source_classes()]

    def _ad_source_classes(self):
        DEFAULT_SOURCES = 'oneriot,citygrid'
        sources = common.pref('social.feed_ads_sources', default=DEFAULT_SOURCES)

        try:
            sources = sources.split(',')
        except ValueError:
            sources = DEFAULT_SOURCES.split(',')

        from .geo_trends import CityGridAdSource
        ad_sources = dict(
            oneriot=OneRiotAdSource,
            citygrid=CityGridAdSource)

        ad_sources = filter(None, [ad_sources.get(s, None) for s in sources])
        return [src for src in ad_sources if src.enabled()]

    def request_ads(self, success, error=None):
        sources = self.sources[:]
        results = {}

        def maybe_done():
            if len(results) != len(sources):
                return # not done yet.

            ads = []
            found = False
            err = None
            max_age = 1800
            max_time = 0
            for res, val in results.itervalues():
                if res:
                    ads.extend(val)
                    max_age = min(max_age, val.max_age)
                    max_time = max(max_time, val.time)
                    found = True
                elif err is None:
                    err = val

            if found:
                ads = NewsItemList(1, max_time, max_age, items=ads)
                success(ads)
            else:
                if error is None:
                    log.error('error retreiving ads: %r', results)
                else:
                    error()

        def result_success(source, ads):
            results[source] = (True, ads)
            maybe_done()

        def result_error(source, err):
            results[source] = (False, err)
            maybe_done()

        for source in sources:
            def _success(ads):
                result_success(source, ads)

            def _error(err):
                results[source] = result_error(err)

            source.request_ads(
                    success=lambda ads, src=source: result_success(src, ads),
                    error=lambda err, src=source: result_error(src, err))

class OneRiotAdSource(object):
    def __init__(self, appId):
        self.update_count = 0
        self.url = oneriot_ad_url(appId)

    @classmethod
    def enabled(cls):
        return True

    def request_ads(self, success, error=None):
        '''requests a set of ads from oneriot'''

        def on_success(req, resp):
            try:
                data = resp.read()
                ads = NewsItemList.from_xml(data, filter_html=True)
                log.info('got %d ads', len(ads) if ads else 0)
            except Exception as e:
                traceback.print_exc()
                if error is not None:
                    error(e)
                log.error('error retrieving ads')
            else:
                success(ads)

        log.info('requesting feed ads from %r' % self.url)
        self.update_count += 1
        asynchttp.httpopen(self.url, success=on_success, error=error)

def set_ad_source(source):
    old_source = feed_ads().source
    feed_ads().source = source
    return old_source

def strip_html(s):
    with traceguard:
        return lxml.html.fromstring(s).text_content()
    return s

# shorten ad urls with bitly using a special account for stats tracking.
ad_url_shortener = bitly_shortener(login='digsbynews',
                                   api_key='R_39035198ad2dea5e4133a9aaeb95c515')

def append_ad_link(ad, on_done):
    '''calls on_done with a NewsItem object that has a bit.ly link to its redirect_url appended'''

    if ad.shortened_url is not None:
        on_done(ad)

    ad.shortened_url = '' # mark as pending

    def success(url):
        ad.shortened_url = url
        on_done(ad)

    def error(e=None):
        if e is not None:
            try:
                raise e
            except Exception:
                traceback.print_exc()

        on_done(ad)

    ad_url_shortener.shorten_async(ad.redirect_url, success, error)

#
# variations for improving click through rates
#

# link styles
def linkstyle_readmore(item):
    return _('read more...'), None

def linkstyle_fullpreview(item):
    url = item.display_url
    if not url.startswith('http'):
        url = 'http://' + url

    return None, url

ad_options_keys = [
    'campaign',   'startpos', 'pinned', 'linkstyle',             'css_classes']
ad_opts = [
    #('digsby01',  (1, 4),     False,    linkstyle_readmore,      ''),
    #('digsby02',  0,          False,    linkstyle_readmore,      ''),
    #('digsby03',  0,          False,    linkstyle_fullpreview,   ''),
    #('digsby04',  0,          False,    linkstyle_readmore,      'social_background_hover_on'),
    #('digsby05',  0,          False,    linkstyle_fullpreview,   'social_background_hover_on'),
    #('digsby06',  0,          True,     linkstyle_readmore,      'social_background_hover_on'),
     ('digsby07',  0,          True,     linkstyle_fullpreview,   'social_background_hover_on'),
]
ad_options = [dict(zip(ad_options_keys, opts)) for opts in ad_opts]

def choose_ad_options():
    # set this pref to a campaign name (i.e., 'digsby04') to choose one.
    # otherwise one will be chosen randomly
    variant = common.pref('social.feed_ads_variant', default=None)

    if variant is not None:
        for opts in ad_options:
            if opts['campaign'] == variant:
                return opts

    return random.choice(ad_options)

import wx
class FeedTrendsDebugWindow(wx.Frame):
    def __init__(self, parent=None):
        wx.Frame.__init__(self, parent, title=_('Feed Trends Debug'))

        from gui.browser.webkit.webkitwindow import WebKitWindow
        debug_html = path(__file__).parent / 'feed_trends_debug.html'
        assert debug_html.isfile()
        self.wk = WebKitWindow(self, url=debug_html.url())

        from gui.toolbox import persist_window_pos
        persist_window_pos(self)

    def update_arrow(self, n):
        self.wk.RunScript('updateArrow(%d);' % n)

    def received_ads(self, feed_ads):
        ads = feed_ads.ad_queue.ads
        sources = feed_ads.ad_queue.source.sources

        def tojson(a):
            d = a._asdict()
            d['text'] = a.feed_text()
            return d

        endpoints = []
        for source in sources:
            for endpoint in getattr(source, 'endpoints', []):
                endpoints.append(
                    dict(name=source.__class__.__name__,
                         xml=getattr(endpoint, 'last_received_xml', '(NONE)').encode('xml'),
                         url=getattr(endpoint, 'last_url', '<NONE>'),
                         keyword=getattr(endpoint, 'last_keyword', '<NONE>'),
                         updateTime=getattr(endpoint, 'last_update_time', '')))

        data = dict(sources = endpoints,
                    ads = [tojson(a) for a in ads],
                    adCounter=feed_ads.ad_queue.ad_index)

        import simplejson
        json = simplejson.dumps(data)

        script = '''receivedAds(%s);''' % json
        self.wk.RunScript(script)

def show_debug_window():
    win = FeedTrendsDebugWindow.MakeOrShow()
    wx.CallLater(500, lambda: win.received_ads(feed_ads()))
    #win.received_ads(feed_ads())

#
#
#

def main():
    from tests.testapp import testapp
    import netextensions

    with testapp():
        from pprint import pprint
        OneRiotAdSource('digsby01').request_ads(pprint)


if __name__ == '__main__':
    main()
