LinkifyTest = TestCase('LinkifyTest');

LinkifyTest.prototype.testLinkify = function() {
    function link(url) {
        return '<a href="' + url + '" title="' + url + '">' + url + '</a>';
    }

    function check(expected, s) {
        assertEquals(expected, linkify(s));
    }

    check('pics...' + link('http://bit.ly/3PxLCn'),
          'pics...http://bit.ly/3PxLCn');

    check('check it out ' + link('http://digs.by/a'),
          'check it out http://digs.by/a')

    //unicode checks disabled--something with loading utf8 files is wrong?

    //check('　' + link('http://google.com') + '　',
          //'　http://google.com　');

    // this example comes from b150107. the spaces before and after the link are "full width spaces" and should not
    // be considered part of the link.
    //check('がぬいぐるみ化　' + link('http://journal.mycom.co.jp/news/2010/10/20/008/index.html') + '　あら',
    //      'がぬいぐるみ化　http://journal.mycom.co.jp/news/2010/10/20/008/index.html　あら');
};

