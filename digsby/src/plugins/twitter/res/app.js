
timelineWindows = [];

var defaultSettings = {
    show_real_names: false,
    frame_focus_unread: true,
    autoscroll_when_at_bottom: true,
    user_feeds: false,
};

var settings = $.extend(true, {}, defaultSettings);

verbose = false;

function openWindow(feedName) {
    window.feedToOpen = feedName;
    var windowOptions = 'status=0,toolbar=0,width=400,height=800';
    var win = window.open((window.resdir ? window.resdir : '')+ '/feed.html', 'mywindow', windowOptions);

    if (win) {
        console.log('feed window opened successfully: ' + win);
        timelineWindows.push(win);
    } else
        console.error('could not open window');
}

function update() {
    window.account.forceUpdate();
}

function getPrefs(opts) {
    opts.success({user: settings, defaults: defaultSettings});
}

var addFeed = function(opts) { window.account.addFeed(opts.feed || opts.group); }
var addGroup = addFeed;

var favorite = function(opts) {
    window.account.favorite(opts.tweet,
                            function(tweet){opts.success('win_favorite');},
                            function(error_obj){opts.error('fail_favorite');}
    );
}

var deleteTweet = function(opts) {
    window.account.deleteTweet({id: opts.tweet.id,
                                success: function(tweet){opts.success('win_delete');},
                                error: function(error_obj){opts.error('fail_delete');}
    });
}

function editFeed(opts) {
    window.account.editFeed(opts.feed);
}

function setFeeds(opts) {
    window.account.setFeeds(opts.feeds);
}

function markAsRead(opts) {
    var tweet = window.account.tweets[opts.tweet_id];
    if (tweet) window.account.markAsRead(tweet);
}

function inviteFollowers() {
    window.account.inviteFollowers();
}

function markFeedAsRead(opts) {
    window.account.markFeedAsRead(opts.feedName);
}

function toggleAddsToCount(opts) {
    window.account.toggleAddsToCount(opts.feedName);
}

// globals that get forwarded to the global account
$.each(['markAllAsRead', 'deleteFeed', 'getUsers', 'setAccountOptions', 'follow'], function (i, name) {
    window[name] = function(opts) {
        return window.account[name](opts);
    };
});

function tweet(opts) {
    var success = opts.success,
        error = opts.error,
        status = opts.status,
        replyTo = opts.replyTo;

    window.account.tweet(status, replyTo, success, error);
}

function showReply(opts) {
    window.account.popupInReplyTo(opts.tweetId);
}

function onTweet(tweetjson) {
    window.account.onRealTimeTweet(tweetjson);
}

function signalCorruptedDatabase() {
    console.log('calling on_corrupted_database...');
    guard(function() {
        D.notify('corrupted_database');
    });
    console.log('called on_corrupted_database...');
}

function initializeDatabase(opts) {
    // open the global database connection used by all child windows
    
    if (window.db)
        return;

    try {
        window.db = window.openDatabase('digsbysocial_2_' + opts.username, "1.0", "Digsby Social Feed", 1024 * 5);
    } catch (err) {
        try { printException(err); } catch (_e) {}
        return signalCorruptedDatabase();
    }

    if (!window.db) {
        console.error('failed to open database.')
        return signalCorruptedDatabase();
    }

    return true;
}

function initialize(opts) {
    if (!initializeDatabase(opts))
        return;

    console.log('creating twitter account ' + opts.username);
    var acct = window.account = new TwitterAccount(opts.username, opts.password, opts);
    acct.ownerWindow = window;

    acct.addClient(new TwitterHTTPClient(acct));

    guard(function() {
        acct.initialize(opts.feeds, opts.accountopts);
    });

    // preload skin images
    SmoothOperator.prototype.preload();
}

function onLoad() {
    var creds = queryParse(window.location.search);
    if (creds.username && creds.password) {
        window.login.username.value = creds.username;
        window.login.password.value = creds.password;
        initialize(creds.username, creds.password);
    }
}

function onChildWindowLoaded(childWindow) {
    twitterPageLoaded(childWindow);
}

function onChildWindowUnloaded(childWindow) {
    timelineWindows.remove(childWindow);
}

$(onLoad);

