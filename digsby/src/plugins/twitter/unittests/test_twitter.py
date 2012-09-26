from tests import TestCase, test_main

class TestTwitter(TestCase):
    def test_twitter(self):
        import twitter.twitter_util as tu
        l = tu.twitter_linkify

        # don't linkify #1, etc
        self.assertEquals("we're #1", l("we're #1"))

        self.assertEquals('test <a href="http://search.twitter.com/search?q=%23foo">#foo</a>',
                          l('test #foo'))

        self.assertEquals('@<a href="http://twitter.com/ninjadigsby">ninjadigsby</a>',
                          l('@ninjadigsby'))

        self.assertEquals('@<a href="http://twitter.com/ninjadigsby/test">ninjadigsby/test</a>',
                          l('@ninjadigsby/test'))

        self.assertEquals('this is a @<a href="http://twitter.com/test">test</a>.',
                          l('this is a @test.'))

        self.assertEquals('L.A. <a href="http://www.creationent.com/cal/serenity.htm#events">http://www.creationent.com/cal/serenity.htm#events</a> Even',
                          l('L.A. http://www.creationent.com/cal/serenity.htm#events Even'))

        self.assertEquals('<a href="http://google.com/#test">http://google.com/#test</a>',
                          l('http://google.com/#test'))

        hashtag_linkify = tu.hashtag_linkify

        self.expect_equal('yo <a href="http://search.twitter.com/search?q=%23dawg">#dawg</a>',
                          hashtag_linkify('yo #dawg'))

        self.expect_equal('test <a href="http://search.twitter.com/search?q=%23dash-tag">#dash-tag</a>',
                          hashtag_linkify('test #dash-tag'))

        self.expect_equal('test <a href="http://search.twitter.com/search?q=%23underscore_tag">#underscore_tag</a>',
                          hashtag_linkify('test #underscore_tag'))

        self.expect_equal('test <a href="http://search.twitter.com/search?q=%23with_numbers123">#with_numbers123</a>',
                          hashtag_linkify('test #with_numbers123'))

        self.expect_equal(  u'daring fireball shortener: <a href="http://\u272adf.ws/g8g">http://\u272adf.ws/g8g</a>',
                          l(u'daring fireball shortener: http://\u272adf.ws/g8g'))


if __name__ == '__main__':
    test_main()
