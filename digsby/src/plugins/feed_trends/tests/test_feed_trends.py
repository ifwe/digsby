if __name__ == '__main__':
    from tests.testapp import testapp
    import netextensions
    app = testapp()

import unittest
import os.path
import simplejson
from util.primitives.mapping import Storage as S

import feed_trends.feed_trends as feed_trends
import feed_trends.geo_trends as geo_trends
from social.network import SocialFeed

class MockTwitter(object):
    def __init__(self, tweets):
        self.recent_timeline = tweets

        from twitter.twitter import htmlize_tweets
        username = 'ninjadigsby'
        mock_protocol = S(username=username, trends=[], unread_counts=[], self_tweet=None)
        id = 'twitter_' + username
        context = 'twitter_feed'
        self.social_feed = SocialFeed(id, context, self.get_tweet_feed,
                lambda tweets, ctx: htmlize_tweets(mock_protocol, tweets))

        ids = [t['id'] for t in self.recent_timeline]
        self.social_feed.new_ids(ids)

    def get_tweet_feed(self):
        return self.recent_timeline

class FeedAdTests(unittest.TestCase):
    def setUp(self):
        feed_trends.SHOW_AD_EVERY = 10
        unittest.TestCase.setUp(self)

    def test_insert_new_ads(self):
        from feed_trends.feed_trends import insert_new_ads
        assert [] == insert_new_ads([], 0)

    def test_inject_ads(self):
        with fakeads():
            tweets = load_sample_tweets()
            mock_twitter = MockTwitter(tweets)
            assert len(list(mock_twitter.social_feed.get_iterator())) > len(tweets)

    def test_prune_impressions(self):
        from random import randint
        from feed_trends.feed_trends import prune_sent_impressions, MAX_IMPRESSIONS_SENT

        i = dict((x, randint(1, 10000)) for x in xrange(MAX_IMPRESSIONS_SENT*2))
        prune_sent_impressions(i)
        assert len(i) == MAX_IMPRESSIONS_SENT

    def test_feed_updates(self):
        return # disabled since restructuring. TODO: fix!
        self._now = 0
        def fake_timer():
            return self._now

        f = feed_trends.FeedAds(source=TestAdSource(), time_secs=fake_timer)
        @f.active_ads
        def on_ads(ads):
            assert len(ads) == 10
            self._now = self._now + ads.max_age - 1

            def cb(ads2):
                # should not have updated yet.
                assert len(ads2) == 10
                assert ads == ads2
                self._now += 3
                t = ads2.time

                def cb2(ads3):
                    # now it should have updated
                    assert len(ads3) == 20
                    assert ads3.time > t, (ads3.time, t)
                    def on_ad(ad):
                        def on_ads(ads):
                            assert ad == ads[0], (ad, ads[0])
                        TestAdSource(ad_xml=example_ads_xml2).request_ads(on_ads)
                    f.get_new_ad(on_ad)

                f.source.invalidate_ads(example_ads_xml2)
                f.active_ads(cb2, force_update=f._should_update_ads())


            f.active_ads(cb, force_update=f._should_update_ads())

    def test_ads_rotate(self):
        f = feed_trends.FeedAds(TestAdSource())

        ctx = dict(i=0)
        def on_ad(ad):
            done = False
            ctx['i'] += 1
            if ctx['i'] in (11, 21):
                assert ad == ctx['first_ad'], (ad, ctx['first_ad'])
                if ctx['i'] == 21:
                    done = True
            elif ctx['i'] == 1:
                ctx['first_ad'] = ad
            if not done:
                f.get_new_ad(on_ad)


        f.get_new_ad(on_ad)

    def test_test_source(self):
        s = TestAdSource()
        def cb(ads):
            # pretend to be a source that expires and serves new ads
            assert len(ads) == 10
            s.invalidate_ads(example_ads_xml2)

            def cb2(ads2):
                assert ads2 != ads
                assert ads2[0] != ads[0]
                assert ads2.time > ads.time, (ads2.time, ads.time)

            s.request_ads(cb2)

        s.request_ads(cb)

    def test_feed_item_deleted(self):
        first_ad_spot = 2
        with fakeads(first_ad_index=first_ad_spot):

            ids=None
            def get_content():
                return [S(id=c) for c in ids]

            ids_1 = [1, 2, 3, 4, 5]

            def getitem(t, ctx):
                return t

            sf = SocialFeed('foo_test', 'feed', get_content, getitem)

            # ensure ads are inserted
            sf.new_ids(ids_1); ids = ids_1
            feed = list(sf.get_iterator())

            def show():
                #print '$$$$ feed:
                from pprint import pprint
                pprint(feed)

            show()
            assert feed_trends.isad(feed[2]), feed[2]

            # ensure the ad moves as new items come in
            ids_2 = [6, 7, 8, 1, 2, 4, 5]
            sf.new_ids(ids_2); ids = ids_2

            feed = list(sf.get_iterator())
            show()
            assert feed_trends.isad(feed[5])

            # ensure that new ads appear
            ids_3 = [11, 12, 13, 14, 15, 16, 6, 7, 8, 1, 2, 4, 5]
            sf.new_ids(ids_3); ids = ids_3

            feed = list(sf.get_iterator())
            show()
            assert feed_trends.isad(feed[1]), feed[1]
            assert feed_trends.isad(feed[-3])

            # no more than 2 ads will ever appear
            ids_4 = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111] + ids_3
            sf.new_ids(ids_4); ids = ids_4
            feed = list(sf.get_iterator())
            self.assertEquals(2, sum(1 if feed_trends.isad(a) else 0 for a in feed))

    def test_parse_xml(self):
        items = feed_trends.NewsItemList.from_xml(example_ads_xml)

class GeoTrendsTests(unittest.TestCase):
    def test_geo_methods(self):
        D = dict
        get_methods = geo_trends._get_possible_methods

        self.assertEqual(get_methods(D(state='PA')), [])

        self.assertEqual(get_methods(D(city='Rochester', state='NY')),
                         [geo_trends.citystate])

        location = dict(city='Rochester', state='NY', postal='14623')
        self.assertEqual(get_methods(location),
                         [geo_trends.citystate, geo_trends.zipcode])

    def test_geo_parse(self):
        from feed_trends.geo_trends import newsitems_from_citygrid_xml
        ads = newsitems_from_citygrid_xml(test_geo_xml)
        assert len(ads) == 1, len(ads)

def load_sample_tweets():
    from util.primitives.mapping import to_storage
    sample_tweets_jsonfile = os.path.join(os.path.dirname(__file__), 'sample_tweets.json')
    with open(sample_tweets_jsonfile, 'rb') as f:
        return [to_storage(t) for t in simplejson.loads(f.read())]

_fakeads = None

class TestAdSource(object):
    def __init__(self, ad_xml=None):
        self._fakeads = None

        if ad_xml is None:
            ad_xml = example_ads_xml
        self.ad_xml = ad_xml

    def request_ads(self, cb, error=None):
        '''loads example ads from disk instead of the network.'''

        if self._fakeads is None:
            self._fakeads = feed_trends.NewsItemList.from_xml(self.ad_xml)

        cb(self._fakeads)

    def invalidate_ads(self, new_xml):
        self._fakeads = None
        self.ad_xml = new_xml

class fakeads(object):
    def __init__(self, first_ad_index=2):
        self.first_ad_index=first_ad_index

    def __enter__(self):
        self.old_source = feed_trends.set_ad_source(TestAdSource())
        feed_ads = feed_trends.feed_ads()
        from feed_trends.feed_trends import linkstyle_readmore
        feed_ads.opts = dict(startpos=self.first_ad_index, pinned=False, linkstyle=linkstyle_readmore, css_classes='')
        self.old_append_short_links = feed_ads.append_short_links
        feed_ads.append_short_links = False

    def __exit__(self, type, value, tb):
        feed_trends.set_ad_source(self.old_source)
        feed_trends.feed_ads().append_short_links = self.old_append_short_links

example_ads_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<search-results xmlns="http://xmlns.oneriot.com/api/1.0/">
  <version>1.1</version>
  <time>1263328429</time>
  <max-age>1800</max-age>
  <featured-result-list>
    <featured-result>
      <title>&lt;b&gt;Michael&lt;/b&gt; &lt;b&gt;Jackson&lt;/b&gt; Death Investigation Complete</title>
      <display-url>www.tmz.com/.../michael-jackson-conrad-murray-death-investigation-lapd-mansla...</display-url>
      <snippet>The LAPD investigation into &lt;b&gt;Michael&lt;/b&gt; &lt;b&gt;Jackson's&lt;/b&gt; death has been completed and the case will go to the D.A. within weeks,  law enforcement sources tell TMZ</snippet>
      <source>TMZ</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/tmz.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F08%2Fmichael-jackson-conrad-murray-death-investigation-lapd-manslaughter%2F&amp;oid=e6bac4b192d567544179fc53fb1f4ec2&amp;appId=digsby01&amp;q=Michael+Jackson&amp;source=trendingads&amp;pos=1&amp;id=6503147041263328461201&amp;q=Michael+Jackson&amp;offset=0&amp;pos=1&amp;campaign=tmz_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F08%2Fmichael-jackson-conrad-murray-death-investigation-lapd-manslaughter%2F&amp;appId=digsby01&amp;source=trendingads&amp;pos=1&amp;id=6503147041263328461201&amp;q=Michael+Jackson&amp;offset=0&amp;pos=1&amp;campaign=tmz_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;YouTube&lt;/b&gt; faces 4chan porn attack | Media</title>
      <display-url>www.guardian.co.uk/media/pda/2010/jan/06/youtube-porn-attack-4chan-lukeywes1234</display-url>
      <snippet>Don't be surprised if you find some porn among the sport highlights, children's cartoons or music videos you are looking for on &lt;b&gt;YouTube&lt;/b&gt;  today.</snippet>
      <source>TheGuardian</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/theguardian.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.guardian.co.uk%2Fmedia%2Fpda%2F2010%2Fjan%2F06%2Fyoutube-porn-attack-4chan-lukeywes1234&amp;oid=4cb3a490aae8be8331a181b57260369e&amp;appId=digsby01&amp;q=YouTube&amp;source=trendingads&amp;pos=2&amp;id=17274122041263328461223&amp;q=YouTube&amp;offset=0&amp;pos=1&amp;campaign=guardian_6</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.guardian.co.uk%2Fmedia%2Fpda%2F2010%2Fjan%2F06%2Fyoutube-porn-attack-4chan-lukeywes1234&amp;appId=digsby01&amp;source=trendingads&amp;pos=2&amp;id=17274122041263328461223&amp;q=YouTube&amp;offset=0&amp;pos=1&amp;campaign=guardian_6</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Lady&lt;/b&gt; &lt;b&gt;Gaga&lt;/b&gt; for Polaroid</title>
      <display-url>www.examiner.com/x-21019-West-Palm-Beach-Fashion-Examiner~y2010m1d8-Lady-Gaga...</display-url>
      <snippet>There is no end to the adventures of &lt;b&gt;Lady&lt;/b&gt; &lt;b&gt;Gaga.&lt;/b&gt;  The best part is she doesn't steal anyones looks! Lady Gaga is not only the mistress of style for 2010,...</snippet>
      <source>Examiner</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/examiner.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.examiner.com%2Fx-21019-West-Palm-Beach-Fashion-Examiner%7Ey2010m1d8-Lady-Gaga-for-Polaroid%3Fcid%3Dchannel-rss-Style_and_Fashion&amp;oid=1f3e4150b088a9ed68523075208ebeef&amp;appId=digsby01&amp;q=Lady+Gaga&amp;source=trendingads&amp;pos=3&amp;id=838774181263328461278&amp;q=Lady+Gaga&amp;offset=0&amp;pos=1&amp;campaign=examiner_23</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.examiner.com%2Fx-21019-West-Palm-Beach-Fashion-Examiner%7Ey2010m1d8-Lady-Gaga-for-Polaroid%3Fcid%3Dchannel-rss-Style_and_Fashion&amp;appId=digsby01&amp;source=trendingads&amp;pos=3&amp;id=838774181263328461278&amp;q=Lady+Gaga&amp;offset=0&amp;pos=1&amp;campaign=examiner_23</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Miley&lt;/b&gt; &lt;b&gt;Cyrus&lt;/b&gt; Bags Her Boyfriend</title>
      <display-url>www.tmz.com/2010/01/05/miley-cyrus-liam-hemsworth-bag-purse-photo/</display-url>
      <snippet>&lt;b&gt;Miley&lt;/b&gt; &lt;b&gt;Cyrus,&lt;/b&gt; 17, and her boyfriend Liam Hemsworth, 19, like to share everything ... even her purse.  The shady couple held hands in Sydney on Monday,...</snippet>
      <source>TMZ</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/tmz.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F05%2Fmiley-cyrus-liam-hemsworth-bag-purse-photo%2F&amp;oid=d47a9aa08c92fc31a0e5343e3c942470&amp;appId=digsby01&amp;q=Miley+Cyrus&amp;source=trendingads&amp;pos=4&amp;id=7163186401263328461334&amp;q=Miley+Cyrus&amp;offset=0&amp;pos=1&amp;campaign=tmz_9</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F05%2Fmiley-cyrus-liam-hemsworth-bag-purse-photo%2F&amp;appId=digsby01&amp;source=trendingads&amp;pos=4&amp;id=7163186401263328461334&amp;q=Miley+Cyrus&amp;offset=0&amp;pos=1&amp;campaign=tmz_9</tracking-url>
    </featured-result>
    <featured-result>
      <title>Sherlock Holmes &lt;b&gt;iTunes&lt;/b&gt; Download</title>
      <display-url>www.qksrv.net/click-3707199-10576759?url=http://www.fandango.com/promo/sherlo...</display-url>
      <snippet>Buy tickets in advance for Sherlock Holmes and receive a free download of the song Holmes (Hans n' Guy Version) by Hans Zimmer  on &lt;b&gt;iTunes.&lt;/b&gt;</snippet>
      <source>Fandango</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/fandango.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.qksrv.net%2Fclick-3707199-10576759%3Furl%3Dhttp%3A%2F%2Fwww.fandango.com%2Fpromo%2Fsherlockholmes%3Fwssac%3D123%26wssaffid%3D11846&amp;oid=5d3b54f0f09394d3efc072ef6018e14c&amp;appId=digsby01&amp;q=iTunes&amp;source=trendingads&amp;pos=5&amp;id=14450055741263328461390&amp;q=iTunes&amp;offset=0&amp;pos=1&amp;campaign=fandango_5</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.qksrv.net%2Fclick-3707199-10576759%3Furl%3Dhttp%3A%2F%2Fwww.fandango.com%2Fpromo%2Fsherlockholmes%3Fwssac%3D123%26wssaffid%3D11846&amp;appId=digsby01&amp;source=trendingads&amp;pos=5&amp;id=14450055741263328461390&amp;q=iTunes&amp;offset=0&amp;pos=1&amp;campaign=fandango_5</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Lil'&lt;/b&gt; &lt;b&gt;Wayne's&lt;/b&gt; Lawyer -- No Charges for Drug Bust</title>
      <display-url>www.tmz.com/2009/12/19/lil-wayne-marijuana-texas-border-patrol/</display-url>
      <snippet>Looks like &lt;b&gt;Lil'&lt;/b&gt; &lt;b&gt;Wayne&lt;/b&gt; will walk away from yesterday's drug bust in Texas unscathed, at least according to his lawyer.  Lil' Wayne, along with 11 other...</snippet>
      <source>TMZ</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/tmz.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.tmz.com%2F2009%2F12%2F19%2Flil-wayne-marijuana-texas-border-patrol%2F&amp;oid=1370d8703558ac6cdb7c9236554d10e2&amp;appId=digsby01&amp;q=Lil%27+Wayne&amp;source=trendingads&amp;pos=6&amp;id=20558140731263328461446&amp;q=Lil%27+Wayne&amp;offset=0&amp;pos=1&amp;campaign=tmz_5</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.tmz.com%2F2009%2F12%2F19%2Flil-wayne-marijuana-texas-border-patrol%2F&amp;appId=digsby01&amp;source=trendingads&amp;pos=6&amp;id=20558140731263328461446&amp;q=Lil%27+Wayne&amp;offset=0&amp;pos=1&amp;campaign=tmz_5</tracking-url>
    </featured-result>
    <featured-result>
      <title>The Hillywood Show Takes on &lt;b&gt;New&lt;/b&gt; &lt;b&gt;Moon&lt;/b&gt;</title>
      <display-url>www.associatedcontent.com/article/.../the_hillywood_show_takes_on_new_moon.html</display-url>
      <snippet>I admit to being one of the many who was eagerly awaiting the release of the &lt;b&gt;New&lt;/b&gt; &lt;b&gt;Moon&lt;/b&gt; Parody, if I am perfectly honest I  was more eager to see the...</snippet>
      <source>AssociatedContent</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/associatedcontent.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2566769%2Fthe_hillywood_show_takes_on_new_moon.html&amp;oid=2b1f1dfc43d0d980c5207bcf4833a1c3&amp;appId=digsby01&amp;q=New+Moon&amp;source=trendingads&amp;pos=7&amp;id=5778898531263328461462&amp;q=New+Moon&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2566769%2Fthe_hillywood_show_takes_on_new_moon.html&amp;appId=digsby01&amp;source=trendingads&amp;pos=7&amp;id=5778898531263328461462&amp;q=New+Moon&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;TWILIGHT&lt;/b&gt;</title>
      <display-url>www.associatedcontent.com/article/2574641/twilight.html</display-url>
      <snippet>&lt;b&gt;Twilight&lt;/b&gt; star Kristen Stewart quotes on her co-stars, fame, herself, and more.
   By  Proverbial Faith Published 11/21/2009</snippet>
      <source>AssociatedContent</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/associatedcontent.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2574641%2Ftwilight.html&amp;oid=aa3d2a14294b891e82ffb62044c02596&amp;appId=digsby01&amp;q=Twilight&amp;source=trendingads&amp;pos=8&amp;id=7137331221263328461519&amp;q=Twilight&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2574641%2Ftwilight.html&amp;appId=digsby01&amp;source=trendingads&amp;pos=8&amp;id=7137331221263328461519&amp;q=Twilight&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>Did Selena Gomez break up &lt;b&gt;Taylor&lt;/b&gt; Lautner and &lt;b&gt;Taylor&lt;/b&gt; &lt;b&gt;Swift?&lt;/b&gt;</title>
      <display-url>www.examiner.com/x-1780-NY-Pop-Culture-Examiner~y2010m1d8-Did-Selena-Gomez-br...</display-url>
      <snippet>You know what they say - three's a crowd - and it seems that there just wasn't...   girlfriend Selena Gomez and his most recent flame, &lt;b&gt;Taylor&lt;/b&gt; &lt;b&gt;Swift.&lt;/b&gt;</snippet>
      <source>Examiner</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/examiner.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.examiner.com%2Fx-1780-NY-Pop-Culture-Examiner%7Ey2010m1d8-Did-Selena-Gomez-break-up-Taylor-Lautner-and-Taylor-Swift%3Fcid%3Dchannel-rss-Arts_and_Entertainment&amp;oid=df4c9ea4d75bb1ecce31e7e06e3728ca&amp;appId=digsby01&amp;q=Taylor+Swift&amp;source=trendingads&amp;pos=9&amp;id=19425868841263328461574&amp;q=Taylor+Swift&amp;offset=0&amp;pos=1&amp;campaign=examiner_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.examiner.com%2Fx-1780-NY-Pop-Culture-Examiner%7Ey2010m1d8-Did-Selena-Gomez-break-up-Taylor-Lautner-and-Taylor-Swift%3Fcid%3Dchannel-rss-Arts_and_Entertainment&amp;appId=digsby01&amp;source=trendingads&amp;pos=9&amp;id=19425868841263328461574&amp;q=Taylor+Swift&amp;offset=0&amp;pos=1&amp;campaign=examiner_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>Matt Kemp and &lt;b&gt;Rihanna&lt;/b&gt; dating?</title>
      <display-url>www.examiner.com/x-32213-Memphis-Headlines-Examiner~y2010m1d7-Matt-Kemp-and-R...</display-url>
      <snippet>Are Matt Kemp and &lt;b&gt;Rihanna&lt;/b&gt; dating ?  If photos that surfaced during the past couple of days are any indication, it appears as if the LA Dodgers and...</snippet>
      <source>Examiner</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/examiner.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.examiner.com%2Fx-32213-Memphis-Headlines-Examiner%7Ey2010m1d7-Matt-Kemp-and-Rihanna-dating%3Fcid%3Dchannel-rss-News&amp;oid=e02012aa8865909fbdb0948fd21a1659&amp;appId=digsby01&amp;q=Rihanna&amp;source=trendingads&amp;pos=10&amp;id=17835444881263328461634&amp;q=Rihanna&amp;offset=0&amp;pos=1&amp;campaign=examiner_14</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.examiner.com%2Fx-32213-Memphis-Headlines-Examiner%7Ey2010m1d7-Matt-Kemp-and-Rihanna-dating%3Fcid%3Dchannel-rss-News&amp;appId=digsby01&amp;source=trendingads&amp;pos=10&amp;id=17835444881263328461634&amp;q=Rihanna&amp;offset=0&amp;pos=1&amp;campaign=examiner_14</tracking-url>
    </featured-result>
  </featured-result-list>
</search-results>
'''

example_ads_xml2 = '''<?xml version="1.0" encoding="UTF-8"?>
<search-results xmlns="http://xmlns.oneriot.com/api/1.0/">
  <version>1.1</version>
  <time>1263938387</time>
  <max-age>1800</max-age>
  <featured-result-list>
    <featured-result>
      <title>Famous &lt;b&gt;YouTube&lt;/b&gt; Videos</title>
      <display-url>www.associatedcontent.com/article/2601237/famous_youtube_videos.html</display-url>
      <snippet>This list then, seeks to overlook the mediocre and to chronicle only the most famous videos that &lt;b&gt;YouTube&lt;/b&gt; has to offer. Charlie  bit my finger!...</snippet>
      <source>AssociatedContent</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/associatedcontent.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2601237%2Ffamous_youtube_videos.html&amp;oid=123446501c7fbec0cc5dab3b75e6e7e3&amp;appId=digsby01&amp;q=YouTube&amp;source=trendingads&amp;pos=1&amp;id=853093341263938405100&amp;q=YouTube&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2601237%2Ffamous_youtube_videos.html&amp;appId=digsby01&amp;source=trendingads&amp;pos=1&amp;id=853093341263938405100&amp;q=YouTube&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>Fashion helps &lt;b&gt;Haiti&lt;/b&gt;</title>
      <display-url>www.examiner.com/x-33875-East-Atlanta-Shopping-Examiner~y2010m1d19-Fashion-he...</display-url>
      <snippet>Its been one week since the devastating 7.0 earthquake that hit the impoverished &lt;b&gt;Haiti.&lt;/b&gt;  With the death toll now estimated at 200,000 everyone is trying...</snippet>
      <source>Examiner</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/examiner.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.examiner.com%2Fx-33875-East-Atlanta-Shopping-Examiner%7Ey2010m1d19-Fashion-helps-Haiti%3Fcid%3Dchannel-rss-Style_and_Fashion&amp;oid=8de9131b82f1bd7e40d73c3ac5a01251&amp;appId=digsby01&amp;q=Haiti&amp;source=trendingads&amp;pos=2&amp;id=2095158371263938405127&amp;q=Haiti&amp;offset=0&amp;pos=1&amp;campaign=examiner_23</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.examiner.com%2Fx-33875-East-Atlanta-Shopping-Examiner%7Ey2010m1d19-Fashion-helps-Haiti%3Fcid%3Dchannel-rss-Style_and_Fashion&amp;appId=digsby01&amp;source=trendingads&amp;pos=2&amp;id=2095158371263938405127&amp;q=Haiti&amp;offset=0&amp;pos=1&amp;campaign=examiner_23</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Sarah&lt;/b&gt; &lt;b&gt;Palin:&lt;/b&gt; I'm No Mad Hatter!</title>
      <display-url>www.tmz.com/.../sarah-palin-joh-mccain-presidential-campaign-hat-blacked-out-...</display-url>
      <snippet>&lt;b&gt;Sarah&lt;/b&gt; &lt;b&gt;Palin&lt;/b&gt; now says she meant no disrespect to Senator John McCain by blacking out his name on her visor,  claiming she -- like Clark Kent with his...</snippet>
      <source>TMZ</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/tmz.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.tmz.com%2F2009%2F12%2F17%2Fsarah-palin-joh-mccain-presidential-campaign-hat-blacked-out-hawaii-politico-incognito-%2F&amp;oid=e212ddacce40d2e1d27f7372934eb78c&amp;appId=digsby01&amp;q=Sarah+Palin&amp;source=trendingads&amp;pos=3&amp;id=1737536881263938405199&amp;q=Sarah+Palin&amp;offset=0&amp;pos=1&amp;campaign=tmz_4</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.tmz.com%2F2009%2F12%2F17%2Fsarah-palin-joh-mccain-presidential-campaign-hat-blacked-out-hawaii-politico-incognito-%2F&amp;appId=digsby01&amp;source=trendingads&amp;pos=3&amp;id=1737536881263938405199&amp;q=Sarah+Palin&amp;offset=0&amp;pos=1&amp;campaign=tmz_4</tracking-url>
    </featured-result>
    <featured-result>
      <title>&amp;quot;Real World&amp;quot; vs. &lt;b&gt;&amp;quot;Jersey&lt;/b&gt; &lt;b&gt;Shore&amp;quot;&lt;/b&gt;</title>
      <display-url>www.examiner.com/x-12184-Detroit-TV-Examiner~y2010m1d16-rw-vs-js?cid=channel-...</display-url>
      <snippet>-Snookers &lt;b&gt;&amp;quot;Jersey&lt;/b&gt; &lt;b&gt;Shore,&amp;quot;&lt;/b&gt; the special needs child of MTV, commands more attention than its quiet older sibling, &amp;quot;Real World.&amp;quot;  Loud, &amp;#8230;</snippet>
      <source>Examiner</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/examiner.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.examiner.com%2Fx-12184-Detroit-TV-Examiner%7Ey2010m1d16-rw-vs-js%3Fcid%3Dchannel-rss-Arts_and_Entertainment&amp;oid=5d5cb2d597d633a6a7b9eecc00f27324&amp;appId=digsby01&amp;q=Jersey+Shore&amp;source=trendingads&amp;pos=4&amp;id=17427427691263938405232&amp;q=Jersey+Shore&amp;offset=0&amp;pos=1&amp;campaign=examiner_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.examiner.com%2Fx-12184-Detroit-TV-Examiner%7Ey2010m1d16-rw-vs-js%3Fcid%3Dchannel-rss-Arts_and_Entertainment&amp;appId=digsby01&amp;source=trendingads&amp;pos=4&amp;id=17427427691263938405232&amp;q=Jersey+Shore&amp;offset=0&amp;pos=1&amp;campaign=examiner_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Pat&lt;/b&gt; &lt;b&gt;Robertson&lt;/b&gt;</title>
      <display-url>www.examiner.com/x-33113-Cincinnati-Christian-Living-Examiner~y2010m1d18-Pat-...</display-url>
      <snippet>Once again &lt;b&gt;Pat&lt;/b&gt; &lt;b&gt;Robertson&lt;/b&gt; has made himself a target for those who see religion as having it's place as long as those views do not  conflict with a...</snippet>
      <source>Examiner</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/examiner.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.examiner.com%2Fx-33113-Cincinnati-Christian-Living-Examiner%7Ey2010m1d18-Pat-Robertson%3Fcid%3Dchannel-rss-Religion_and_Spirituality&amp;oid=2dbc2e154eec87008cfa775b51dc7a3d&amp;appId=digsby01&amp;q=Pat+Robertson&amp;source=trendingads&amp;pos=5&amp;id=8685409791263938405302&amp;q=Pat+Robertson&amp;offset=0&amp;pos=1&amp;campaign=examiner_19</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.examiner.com%2Fx-33113-Cincinnati-Christian-Living-Examiner%7Ey2010m1d18-Pat-Robertson%3Fcid%3Dchannel-rss-Religion_and_Spirituality&amp;appId=digsby01&amp;source=trendingads&amp;pos=5&amp;id=8685409791263938405302&amp;q=Pat+Robertson&amp;offset=0&amp;pos=1&amp;campaign=examiner_19</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Gilbert&lt;/b&gt; &lt;b&gt;Arenas&lt;/b&gt; -- Dropped by Adidas</title>
      <display-url>www.tmz.com/2010/01/15/gilbert-arenas-dropped-by-adidas/</display-url>
      <snippet>Adidas has wasted no time -- they've decided to cut ties with &lt;b&gt;Gilbert&lt;/b&gt; &lt;b&gt;Arenas&lt;/b&gt; following his guilty plea today.  A rep for the company gave TMZ this ...</snippet>
      <source>TMZ</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/tmz.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F15%2Fgilbert-arenas-dropped-by-adidas%2F&amp;oid=8bc9256edeafec109d118a309e2c6fb8&amp;appId=digsby01&amp;q=Gilbert+Arenas&amp;source=trendingads&amp;pos=6&amp;id=6211443341263938405373&amp;q=Gilbert+Arenas&amp;offset=0&amp;pos=1&amp;campaign=tmz_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F15%2Fgilbert-arenas-dropped-by-adidas%2F&amp;appId=digsby01&amp;source=trendingads&amp;pos=6&amp;id=6211443341263938405373&amp;q=Gilbert+Arenas&amp;offset=0&amp;pos=1&amp;campaign=tmz_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Kate&lt;/b&gt; &lt;b&gt;Gosselin's&lt;/b&gt; Fame Gets an Extension</title>
      <display-url>www.tmz.com/2010/01/11/kate-gosselin-hair-extension-photo/</display-url>
      <snippet>America's favorite divorced mother of eight, &lt;b&gt;Kate&lt;/b&gt; &lt;b&gt;Gosselin,&lt;/b&gt; has traded in her trademark highlighted bi-level reverse mullet Midwest  raccoon weave for...</snippet>
      <source>TMZ</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/tmz.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F11%2Fkate-gosselin-hair-extension-photo%2F&amp;oid=e010551a59ac762bc0519564e17191b1&amp;appId=digsby01&amp;q=Kate+Gosselin&amp;source=trendingads&amp;pos=7&amp;id=14798068041263938405448&amp;q=Kate+Gosselin&amp;offset=0&amp;pos=1&amp;campaign=tmz_10</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.tmz.com%2F2010%2F01%2F11%2Fkate-gosselin-hair-extension-photo%2F&amp;appId=digsby01&amp;source=trendingads&amp;pos=7&amp;id=14798068041263938405448&amp;q=Kate+Gosselin&amp;offset=0&amp;pos=1&amp;campaign=tmz_10</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;Heidi&lt;/b&gt; &lt;b&gt;Montag&lt;/b&gt; and Plastic Surgery</title>
      <display-url>www.associatedcontent.com/article/2586321/heidi_montag_and_plastic_surgery.html</display-url>
      <snippet>Stand &lt;b&gt;Heidi&lt;/b&gt; &lt;b&gt;Montag,&lt;/b&gt; that's for sure.  In my opinion she promotes selfishness, narrow-mindedness, and just plain being dumb. There is nothing about...</snippet>
      <source>AssociatedContent</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/associatedcontent.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2586321%2Fheidi_montag_and_plastic_surgery.html&amp;oid=37163b64948ad65f2a108b7c7e6e905a&amp;appId=digsby01&amp;q=Heidi+Montag&amp;source=trendingads&amp;pos=8&amp;id=14202721231263938405526&amp;q=Heidi+Montag&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2586321%2Fheidi_montag_and_plastic_surgery.html&amp;appId=digsby01&amp;source=trendingads&amp;pos=8&amp;id=14202721231263938405526&amp;q=Heidi+Montag&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>No Brangelina confrontation for &lt;b&gt;Jennifer&lt;/b&gt; &lt;b&gt;Aniston&lt;/b&gt; at Golden Globes</title>
      <display-url>www.examiner.com/x-16808-Jennifer-Aniston-Examiner~y2010m1d13-No-Brangelina-c...</display-url>
      <snippet>Brad Pitt and Angelina Jolie won't be attending the Golden Globes this year AP photo January 13 - &lt;b&gt;Jennifer&lt;/b&gt; &lt;b&gt;Aniston&lt;/b&gt; can breathe  a sigh of relief knowing...</snippet>
      <source>Examiner</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/examiner.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.examiner.com%2Fx-16808-Jennifer-Aniston-Examiner%7Ey2010m1d13-No-Brangelina-confrontation-for-Jennifer-Aniston-at-Golden-Globes%3Fcid%3Dchannel-rss-Arts_and_Entertainment&amp;oid=9b206c5a6ae764927c82a069b0a9ac28&amp;appId=digsby01&amp;q=Jennifer+Aniston&amp;source=trendingads&amp;pos=9&amp;id=2616914481263938405595&amp;q=Jennifer+Aniston&amp;offset=0&amp;pos=1&amp;campaign=examiner_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.examiner.com%2Fx-16808-Jennifer-Aniston-Examiner%7Ey2010m1d13-No-Brangelina-confrontation-for-Jennifer-Aniston-at-Golden-Globes%3Fcid%3Dchannel-rss-Arts_and_Entertainment&amp;appId=digsby01&amp;source=trendingads&amp;pos=9&amp;id=2616914481263938405595&amp;q=Jennifer+Aniston&amp;offset=0&amp;pos=1&amp;campaign=examiner_1</tracking-url>
    </featured-result>
    <featured-result>
      <title>&lt;b&gt;The&lt;/b&gt; &lt;b&gt;Bachelor:&lt;/b&gt; &lt;b&gt;the&lt;/b&gt; &lt;b&gt;Bachelor&lt;/b&gt; Predictions - Jake - Spoilers Without Names</title>
      <display-url>www.associatedcontent.com/article/.../the_bachelor_the_bachelor_predictions.html</display-url>
      <snippet>Here, I've given hints and sneak peeks on &lt;b&gt;The&lt;/b&gt; &lt;b&gt;Bachelor&lt;/b&gt; predictions from RealitySteve.com . &lt;b&gt;The&lt;/b&gt; &lt;b&gt;Bachelor&lt;/b&gt; Predictions:  Jake - Episode 3 In this...</snippet>
      <source>AssociatedContent</source>
      <source-logo>
        <url>http://cdn.media.oneriot.com/images_source/associatedcontent.gif</url>
      </source-logo>
      <redirect-url>http://ord.oneriot.com/?target=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2588343%2Fthe_bachelor_the_bachelor_predictions.html&amp;oid=3d23b9e575b017f036c5bd9e50d532b9&amp;appId=digsby01&amp;q=The+Bachelor&amp;source=trendingads&amp;pos=10&amp;id=17004937921263938405626&amp;q=The+Bachelor&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</redirect-url>
      <tracking-url>http://ord.oneriot.com/tr/__t.gif?ad1=http%3A%2F%2Fwww.associatedcontent.com%2Farticle%2F2588343%2Fthe_bachelor_the_bachelor_predictions.html&amp;appId=digsby01&amp;source=trendingads&amp;pos=10&amp;id=17004937921263938405626&amp;q=The+Bachelor&amp;offset=0&amp;pos=1&amp;campaign=associated-contentd_1</tracking-url>
    </featured-result>
  </featured-result-list>
</search-results>'''

test_geo_xml = '''
<ads>
  <!-- Copyright 2009 Citysearch -->
  <ad id="56529682">
    <type>local PFP </type>
    <listingId>603902992</listingId>
    <name>Education Degree Online</name>
    <street/>
    <city/>
    <state/>
    <zip>0</zip>
    <latitude>0.0</latitude>
    <longitude>0.0</longitude>
    <phone/>
    <tagline>Learn about getting your teachers degree online. Visit our website to search our database of schools near you!</tagline>
    <description/>
    <overall_review_rating>0</overall_review_rating>
    <ad_destination_url>http://pfpc.citysearch.com/pfp/ad?listingId=603902992&amp;campProdId=16515742&amp;prodDetId=12&amp;adImpressionId=0a1bcdf57cbf48aab0b2de0d2c557a39&amp;adId=56529682&amp;publisher=digsby&amp;adType=pfp&amp;tierId=8&amp;initPublisher=digsby&amp;version=alpha&amp;marketId=null&amp;directUrl=http%3A%2F%2Fwww.smarter.com%2Fse--qq-Education%2BDegree%2BOnline.html%3Fsource%3Dcampaign5_keyword_Education%2BDegree%2BOnline</ad_destination_url>
    <ad_display_url>http://www.citysearch.com/profile/603902992</ad_display_url>

    <ad_image_url/>
    <net_ppe>0.35</net_ppe>
    <reviews>0</reviews>
    <offers/>
    <distance/>
  </ad>
</ads>
'''

if __name__ == '__main__':
    import unittest
    unittest.main()
