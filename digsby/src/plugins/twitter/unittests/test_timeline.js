TimelineTest = TestCase('TimelineTest');

function MockAccount() {
}

MockAccount.prototype.isSelfTweet = function(t) { return false; }

TimelineTest.prototype.testTimeline = function() {
    /*:DOC += <div id="container"></div> */

    var container = document.getElementById('container');
    assertNotNull(container);

    var skin = new SmoothOperator(document);

    var t = new Timeline(container, skin);

    var account = t.account = new MockAccount();


    return; // broken since the advent of timeline2.js

    var tweets = [];
    t.insertSorted(tweets);

    var children = container.childNodes;
    assertEquals(0, children.length);

    arrayExtend(tweets, [
        {id: 7, created_at_ms: 122, text: 'test2'},
        {id: 3, created_at_ms: 123, text: 'test'},
    ]);

    t.dataMap = account.tweets = {};

    function addTweets(tweets) {
        $.each(tweets, function(i, t) {
            account.tweets[t.id] = t;
        });
    }

    addTweets(tweets);

    t.insertSorted(tweets);

    assertEquals(2, container.childNodes.length);
    assertEquals(7, children[0].id);
    assertEquals(3, children[1].id);
}

TimelineTest.prototype.testFeedView = function() {
    var self = this;
    function letterId(letter) { return 'letter_' + letter; }
    function toNode(letter) {
        var div = document.createElement('div');
        div.id = letterId(letter);
        div.innerHTML = letter;
        div.title = letter;
        return div;
    }
    function nodeKey(letterDiv) {
        return letterDiv.title;
    }
    function itemKey(letter) { return letter; }


    function makeFeedView() { 
        var container = document.createElement('div');
        document.body.appendChild(container)
        return new FeedView(container, toNode, letterId, nodeKey, itemKey);
    }

    var f = makeFeedView();

    function getVisual(feedView) {
        var visual = [];
        var children = feedView.container.childNodes;
        for (var i = 0; i < children.length; ++i) {
            visual.push(children[i].title);
        }
        return visual;
    }

    function syncAndCheck(feed, items, resetStats) {
        if (resetStats || resetStats === undefined)
            feed.resetStats();

        feed.sync(items);
        assertEquals(getVisual(feed), items);
    }

    syncAndCheck(f, ['A', 'B', 'D']);
    assertEquals(1, f.stats.inserts);

    syncAndCheck(f, ['E']);
    assertEquals(3, f.stats.deletes);
    assertEquals(1, f.stats.inserts);

    f2 = makeFeedView();
    syncAndCheck(f2, ['D', 'E', 'F']);

    syncAndCheck(f2, ['A', 'B', 'C', 'D', 'E']);
    assertEquals(1, f2.stats.inserts);
    assertEquals(1, f2.stats.deletes);

    syncAndCheck(f2, ['C']);
    syncAndCheck(f2, ['C', 'E', 'F']);
    assertEquals(1, f2.stats.inserts);
    assertEquals(0, f2.stats.deletes);
}

