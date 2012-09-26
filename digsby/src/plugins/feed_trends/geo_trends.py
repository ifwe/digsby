'''
citygrid trends
'''

import hooks
import random
from util.net import UrlQuery
from util import Storage as S
import common.asynchttp as asynchttp
import common

import lxml.etree as ET
from logging import getLogger
log = getLogger('geo_trends')

active_geoip = None
did_receive_geoip = False

def on_geoip(geoip, *a, **k):
    global did_receive_geoip
    did_receive_geoip = True

    global active_geoip
    active_geoip = geoip

class PlacementMethodReprMeta(type):
    def __repr__(cls):
        return '<PlacementMethod %r>' % cls.__name__

class PlacementMethod(object):
    __metaclass__ = PlacementMethodReprMeta
    @classmethod
    def supports_location(cls, location):
        return all(location.get(a, None) for a in cls.location_attrs)

class citystate(PlacementMethod):
    location_attrs = 'city', 'state'
    @staticmethod
    def urlargs(location):
        return dict(where='%s, %s' % (location['city'], location['state']))

class ipaddress(PlacementMethod):
    location_attrs = 'ip',
    @staticmethod
    def urlargs(location):
        return dict(client_ip='%s' % (location['ip']))

class zipcode(PlacementMethod):
    location_attrs = 'postal',
    @staticmethod
    def urlargs(location):
        return dict(where='%s' % (location['postal']))

location_methods = [
    citystate,
    ipaddress,
    zipcode,
]

def _get_possible_methods(location):
    if not location:
        return []

    return [method for method in location_methods
            if method.supports_location(location)]

from feed_trends import NewsItem
class CityGridNewsItem(NewsItem):
    __slots__ = ()

    def notify_click(self):
        ppe = self.content['net_ppe']
        if ppe is not None:
            cents = int(ppe*100)
            hooks.notify('digsby.statistics.feed_ads.citygrid.click_cents', cents)

        hooks.notify('digsby.statistics.feed_ads.citygrid.click')

    def _notify_impression_hook(self):
        hooks.notify('digsby.statistics.feed_ads.citygrid.impression')

ad_keywords = '''
    food
    lunch
    restaurant
    cuisine
    bar
    pub
    clothing
    shopping
    beauty
    spa
    automotive
    jewelry
    furniture
    fitness
    education
'''.strip().split()

def _get_ad_url(location, method, keyword):
    url_kwargs = dict(
        placement=method.__name__,
        what=keyword)

    publisher = common.pref('social.feed_ads_publisher', 'digsby')
    if publisher and publisher.lower() != 'none':
        url_kwargs['publisher'] = publisher

    url_kwargs.update(method.urlargs(location))

    # TODO: make UrlQuery accept an encoding argument to encode
    # values automatically.
    url_kwargs = dict((k, to_utf8(v)) for k, v in url_kwargs.iteritems())

    url = UrlQuery('http://api.citygridmedia.com/ads/custom/v2/where', **url_kwargs)
    return url

def to_utf8(s):
    return s.encode('utf8') if isinstance(s, unicode) else s

httpopen = asynchttp.httpopen

class CityGridAdSource(object):

    def __init__(self, campaign):
        self.set_location(active_geoip)

    @classmethod
    def enabled(cls):
        return active_geoip and active_geoip.get('country', '').upper() == 'US'

    def set_location(self, location):
        self.location = location

    def request_ads(self, success, error=None):
        from feed_trends import NewsItemList

        if error is None:
            def error(*a):
                print 'ERROR:', a or None

        location = self.location

        possible_methods = _get_possible_methods(location)
        if not possible_methods:
            return success([])

        placement_method = random.choice(possible_methods)

        NUM_KEYWORDS = 2

        keywords_copy = ad_keywords[:]
        random.shuffle(keywords_copy)
        chosen_keywords = keywords_copy[:NUM_KEYWORDS]
        used_urls = []

        ctx = dict(count=0)
        all_ads = []
        all_errors = []

        def maybe_done():
            ctx['count'] += 1
            if ctx['count'] < NUM_KEYWORDS:
                return

            if all_ads:
                self.endpoints = []
                ad_objects = []
                for url, data, ads, kwd in all_ads:
                    ad_objects.extend(ads)
                    from datetime import datetime
                    self.endpoints.append(S(
                        last_received_xml = prettyxml(data),
                        last_keyword = kwd,
                        last_url = url,
                        last_update_time = datetime.now().isoformat()))

                return success(NewsItemList(1, 0, 0, items=ad_objects))

            error(all_errors[0] if all_errors else None)

        def _url_success(url, data, ads, keyword):
            all_ads.append((url, data, ads, keyword))
            maybe_done()

        def _url_error(url, e, keyword):
            all_errors.append(e)
            maybe_done(keyword)

        for kwd in chosen_keywords:
            url = _get_ad_url(location, placement_method, kwd)

            def on_success(req, resp, url=url, keyword=kwd):
                try:
                    data = resp.read()
                    ads = newsitems_from_citygrid_xml(data)
                except Exception as e:
                    _url_error(url, e, keyword)
                else:
                    _url_success(url, data, ads, keyword)

            httpopen(url, success=on_success, error=_url_error)

_default_image_url_path = None
def _default_image_url():
    from path import path
    global _default_image_url_path
    if _default_image_url_path is None:
        _default_image_url_path = (path(__file__).parent / 'res' / 'information.png').url()

    return _default_image_url_path

def newsitems_from_citygrid_xml(xmlstring):
    from feed_trends import NewsItemList, strip_html
    xml = ET.fromstring(xmlstring)

    items = []
    for ad in xml:
        if ad.tag != 'ad': # ignore comment
            continue

        def find(s):
            elem = ad.find(s)
            return elem.text if elem is not None else ''

        def findtext(s):
            text = find(s)
            return strip_html(text) if text else text

        def findurl(s):
            url = find(s)

            # some urls returned from CityGrid do not begin with http
            if url and not url.startswith('http'):
                url = 'http://' + url

            return url

        def findfloat(s):
            f = find(s)
            try:
                return float(f)
            except Exception:
                return None

        name = findtext('name')
        tagline = findtext('tagline')
        snippet = tagline if name else (findtext('description') or '')

        item = CityGridNewsItem(
            title=name or tagline,
            display_url=findurl('ad_display_url'),
            snippet=snippet,
            source='',
            source_logo_url=findurl('ad_image_url') or _default_image_url(),
            redirect_url=findurl('ad_destination_url'),
            tracking_url='',
            shortened_url=None,
            keyword=_('Featured Content'),
            content=dict(
                street=findtext('street'),
                phone=findtext('phone'),
                reviews=findtext('reviews'),
                net_ppe=findfloat('net_ppe'),
            ),
            show_snippet=True,
        )
        items.append(item)

    return NewsItemList(version='1',
        time=0,
        max_age=60*60*300, # TODO: remove max_age entirely
        items=items)

def prettyxml(xml):
    'Returns your XML string with nice whitespace.'

    if isinstance(xml, basestring):
        xml = ET.fromstring(xml)
    return ET.tostring(xml, pretty_print = True)
