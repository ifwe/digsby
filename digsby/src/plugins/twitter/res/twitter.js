/**
 * An HTML5 twitter client operating in a WebKit window as Digsby's twitter plugin.
 */

var TRENDS_UPDATE_MINS = 60;
var IDLE_THRESHOLD_MS = 10 * 60 * 1000;

var INVITE_TEXT = "Hey, I've been using Digsby and thought you might find it useful. Check out the demo video: ";
var INVITE_URL  = "http://bit.ly/clMDW5";

// javascript's RegExp \w character class doesn't include common extended characters. this string
// includes some common latin characters, at least.
var wordchars = '\\w¿»Ã“Ÿ‡ËÏÚ˘¡…Õ”⁄›·ÈÌÛ˙˝¬ Œ‘€‚ÍÓÙ˚√—’„ÒıƒÀœ÷‹‰ÎÔˆ¸°øÁ«ﬂÿ¯≈Â∆Êﬁ˛–';

/* linkify @usernames */
var atify_regex = new RegExp('(?:(?:^@([\\w]+))|(?:([^\\w])@([' + wordchars + ']+)))(/[' + wordchars + ']+)?', 'g');

var atifyOnClick = 'onclick="javascript:return tweetActions.openUser(this);"';

function atify(s) {
    return s.replace(atify_regex, function(m, sn1, extra, sn2, listName) {
        var screenname = (sn1 || sn2) + (listName ? listName : '');
        return (extra || '') + '@<a class="userLink" href="http://twitter.com/' + screenname + '"' +
            ' ' + atifyOnClick +
            '>' + screenname + '</a>';
    });
}

/* linkify #hastags */
var hashifyRegex = new RegExp('(?:(?:^)|(?:([^/&' + wordchars + '])))(#([' + wordchars + ']{2,}))', 'g');

function hashify(s) {
    return s.replace(hashifyRegex, function(m, extra, outerSearch, search) {
         return (extra || '') + '<a href="http://search.twitter.com/search?q=%23' + search + '">' + outerSearch + '</a>';
    });
}

function twitterLinkify(s) {
    return atify(hashify(linkify(s)));
}

var infoColumns = [
    ['key', 'TEXT'],
    ['value', 'TEXT']
];

// detect malformed databases and ask the account to delete all local data if we do
function executeSql(tx, query, args, success, error) {
    function _error(tx, err) {
        if (err.message === 'database disk image is malformed')
            D.notify('corrupted_database');
        else
            return error(tx, err);
    }

    return tx.executeSql(query, args, success, _error);
}

var tweetColumns = [
    // [JSON name, sqlite datatype]
    ['id',         'TEXT UNIQUE'],
    ['created_at', 'TEXT'],
    ['text',       'TEXT'],
    ['source',     'TEXT'],
    ['truncated',  'TEXT'],
    ['in_reply_to_status_id', 'TEXT'],
    ['in_reply_to_user_id',   'INTEGER'],
    ['favorited',  'BOOLEAN'],
    ['in_reply_to_screen_name', 'TEXT'],
    ['user',       'INTEGER'],

    // custom
    ['read',       'INTEGER'], // is read
    ['mention',    'BOOLEAN'], // has @username in text
    ['search',     'TEXT'],    // came from a search

    // search tweets are returned with just the username, not an ID, so for these
    // tweets we only have from_user and profile_image_url
    ['from_user',  'TEXT'],
    ['profile_image_url', 'TEXT']
];

var directColumns = [
    ['id',           'TEXT UNIQUE'],
    ['sender_id',    'INTEGER'],
    ['text',         'TEXT'],
    ['recipient_id', 'INTEGER'],
    ['created_at',   'TEXT'],

    ['read',         'INTEGER'],
];

var userColumns = [
    ['id',          'INTEGER UNIQUE'],
    ['name',        'TEXT'],
    ['screen_name', 'TEXT'],
    ['location',    'TEXT'],
    ['description', 'TEXT'],
    ['profile_image_url', 'TEXT'],
    ['url',         'TEXT'],
    ['protected',   'TEXT'],
    ['followers_count', 'INTEGER'],
    ['profile_background_color', 'TEXT'],
    ['profile_text_color', 'TEXT'],
    ['profile_link_color', 'TEXT'],
    ['profile_sidebar_fill_color', 'TEXT'],
    ['profile_sidebar_border_color', 'TEXT'],
    ['friends_count',  'INTEGER'],
    ['created_at',     'TEXT'],
    ['favourites_count', 'INTEGER'],
    ['utc_offset',     'INTEGER'],
    ['time_zone',      'TEXT'],
    ['profile_background_image_url', 'TEXT'],
    ['profile_background_tile', 'TEXT'],
    ['statuses_count', 'INTEGER'],
    ['notifications',  'TEXT'],
    ['following',      'TEXT']
];

var tweetsByTime = cmpByKey('created_at_ms');
var tweetsById = cmpByKey('id');

function twitterPageLoaded(window)
{
    guard(function() {
    // TODO: account should not be a global on the window.
    var account = window.opener.account;
    account.window = window;
    window.db = window.opener.db;
    window.timeline.account = account;
    var timeline = account.timeline = window.timeline;
    timeline.dataMap = account.tweets;

    // update timestamps every minute.
    window.timestampTimer = window.setInterval(function() { timeline.updateTimestamps(); }, 1000 * 60);

    // use a temporary function on the window here hardcoded into feed.html's <body onunload> handler
    // until http://dev.jquery.com/ticket/4791 is fixed (jquery child window unloads get registered
    // on parent windows)
    window.feedUnload = function() {
        console.log('unload handler called');
        account.recordReadTweets();
    };

    var feedToOpen = window.opener.feedToOpen || 'timeline';

    //console.warn('calling changeView from twitterPageLoaded');
    account.changeView(feedToOpen);
    account.notifyFeeds();
    delete window.opener.feedToOpen;
    });
}

function TwitterAccount(username, password, opts) {
    if (!username)
        throw "Need username";

    //console.warn('TwitterAccount(' + username + ', ' + password + ', ' + oauthToken + ', ' + oauthConsumerSecret + ')');

    var self = this;
    this.showAllRealtime = false;
    this.clients = [];
    this.username = username;
    //this.selfScreenNameLower = username.toLowerCase();
    this.password = password;

    // OAUTH
    if (opts.oauthTokenKey)
        this.oauth = {
            tokenKey: opts.oauthTokenKey,
            tokenSecret: opts.oauthTokenSecret,
            consumerKey:  opts.oauthConsumerKey,
            consumerSecret: opts.oauthConsumerSecret
        };

    this.users = {};   // {user id: user object}

    this.sql = {
        'tweets':  new SQLDesc('Tweets',  tweetColumns),
        'users':   new SQLDesc('Users',   userColumns),
        'info':    new SQLDesc('Info',    infoColumns),
        'directs': new SQLDesc('Directs', directColumns)
    };
}

function dropAllTables() {
    var tables = objectKeys(window.account.sql);

    window.db.transaction(function(tx) {
        console.log('dropping tables: ' + tables.join(', '));
        $.each(tables, function (i, table) {
            executeSql(tx, 'drop table if exists ' + table);
        });
    }, function(error) { console.error(error.message); });
}


function tweetsEqual(t1, t2) { return t1.id === t2.id; }

function errorFunc(msg) {
    return function (err) {
        var extra = '';
        if (err !== undefined && err.message !== undefined)
            extra = ': ' + err.message;
        console.error(msg + extra);
    };
}

TwitterAccount.prototype = {
    timerMs: 1000 * 60,
    webRoot: 'http://twitter.com/',
    apiRoot: 'https://api.twitter.com/1/',
    searchApiRoot: 'http://search.twitter.com/',

    showTimelinePopup: function(n) {
        var items = this.feeds.timeline.items;
        if (n !== undefined)
            items = items.slice(0, n);

        showPopupsForTweets(this, items);
    },

    stopTimers: function(reason) {
        console.warn('stopTimers:' + reason);
        if (this.updateTimer)
            clearInterval(this.updateTimer);
    },

    maybeUpdate: function(forceUpdate, sources) {
        var self = this;
        var now = new Date().getTime();
        var srcs;
        var checkIdle = false;

        if (sources) {
            srcs = sources;
        } else if (forceUpdate) {
            console.warn('forcing update');
            srcs = $.map(self.sources, function(s) { return s.feed.autoUpdates ? s : null; });
        } else {
            checkIdle = true;
            // only update sources whose needsUpdate returns true
            srcs = $.map(self.sources, function(s) { return s.needsUpdate(now) ? s : null; });
        }

        if (srcs.length === 0)
            return;

        function _doUpdate() {
            if (self.returnFromIdleTimer) {
                clearInterval(self.returnFromIdleTimer);
                self.returnFromIdleTimer = undefined;
            }

            // any successful update triggers online state
            function success() {
                self.didUpdate = true;
                self.notifyClients('didReceiveUpdates');
            }
            console.debug('UpdateNotification being created with ' + srcs.length);
            var updateNotification = new UpdateNotification(self, srcs.length, {
                success: success,
                onDone: function(tweets) {
                    self.notifyClients('didReceiveWholeUpdate');
                },
            });

            var markRead = false;
            if (self.firstUpdate) {
                self.firstUpdate = false;
                markRead = true;
            }

            for (var c = 0; c < srcs.length; ++c) {
                var src = srcs[c];
                if (markRead)
                    src.markNextUpdateAsRead();
                src.update(updateNotification);
            }
        }

        if (!checkIdle) {
            _doUpdate();
            return;
        }

        D.rpc('get_idle_time', {}, function(args) {
            if (args.idleTime > IDLE_THRESHOLD_MS) {
                if (!self.returnFromIdleTimer) {
                    // once idle, check idle time every 10 seconds so that
                    // we can update soon after you come back.
                    self.returnFromIdleTimer = setInterval(function() {
                        self.maybeUpdate();
                    }, 10 * 1000);
                }
            } else _doUpdate();
        }, _doUpdate);
    },

    discardOldTweets: function() {
        var self = this,
            idsToDelete = [],
            usersToKeep = {};

        var doc, toInsertMap;
        if (this.timeline) {
            doc = this.timeline.container.ownerDocument;
            console.debug('** discardOldTweets this.timeline.toInsert: ' + this.timeline.toInsert);
            if (this.timeline.toInsertMap)
                toInsertMap = this.timeline.toInsertMap;
        }

        doc = this.timeline ? this.timeline.container.ownerDocument : undefined;

        //console.warn('** discardOldTweets toInsertMap: ' + toInsertMap);

        function shouldDelete(tweet) {
            if (!doc || !doc.getElementById(tweet.id))
                if (!tweet.feeds || !objectKeys(tweet.feeds).length)
                    if (!toInsertMap || !(tweet.id in toInsertMap))
                        return true;
        }

        function discard(items) {
            // discard references to all tweets not in a feed
            $.each(items, function (i, tweet) {
                if (shouldDelete(tweet))
                    idsToDelete.push(tweet.id);
                else {
                    $.each(['user', 'recipient_id', 'sender_id'], function (i, attr) {
                        if (tweet[attr])
                            usersToKeep[tweet[attr]] = true;
                    });
                }
            });

            $.each(idsToDelete, function (i, id) {
                //console.log('DELETING ' + id + ' ' + items[id].text + ' ' + objectLength(items[id].feeds))
                delete items[id];
            });
        }

        discard(this.tweets);

        // discard all users not referenced by tweets or directs or groups

        $.each(this.getUsersToKeep(), function(i, id) {
            usersToKeep[id] = true;
        });

        var usersToDelete = [];
        $.each(this.users, function (id, user) {
            if (user.screen_name.toLowerCase() !== this.selfScreenNameLower)
                if (!(id in usersToKeep))
                    usersToDelete.push(id);
        });

        if (usersToDelete.length) {
            $.each(usersToDelete, function (i, id) { delete self.users[id]; });
        }
    },

    forceUpdate: function() {
        this.maybeUpdate(true);
    },

    setupTimers: function() {
        var self = this;
        this.updateTimer = setInterval(function() { self.maybeUpdate(); }, this.timerMs);
        this.maybeUpdate();

        // update trends periodically.
        this.trendsTimer = setInterval(function() { self.getTrends(); },
                                       1000 * 60 * TRENDS_UPDATE_MINS);
    },

    initialize: function(feeds, accountopts) {
        var self = this;

        if (accountopts) {
            console.warn('apiRoot: ' + accountopts.apiRoot);
            console.debug(JSON.stringify(accountopts));
            if (accountopts.timeCorrectionSecs !== undefined) {
                var diffMs = accountopts.timeCorrectionSecs * 1000;
                var d = new Date(new Date().getTime() - diffMs);
                receivedCorrectTimestamp(d, true);
            }

            if (accountopts.webRoot) self.webRoot = accountopts.webRoot;
            if (accountopts.apiRoot) self.apiRoot = accountopts.apiRoot;
            if (accountopts.searchApiRoot) self.searchApiRoot = accountopts.searchApiRoot;

        }

        function success(tx) {
            self.initializeFeeds(tx, feeds, accountopts, function() {
                if (self.offlineMode) {
                    self.didUpdate = true;
                    self.notifyClients('didReceiveUpdates');
                    self.notifyFeeds();
                    self.doNotifyUnread();
                } else {
                    self.getFollowing(function() {
                        // we don't know which users to discard until we know who we're following.
                        self.discardOldUsers();
                    });
                    self.getTrends();
                    self.setupTimers();
                    self.notifyFeeds();
                }
            }, function() {
                self.connectionFailed();
            });
        }

        function error(tx, error) {
            console.error('error creating tables: ' + error.message);
        }

        account.setupSql(success, error);
    },

    refreshFeedItems: function(feed) {
        feed.removeAllItems();
        this.addAllSorted(feed, this.timeline && this.timeline.feed === feed);
    },

    addAllSorted: function(feed, deleted) {
        var tweets = objectValues(this.tweets);
        tweets.sort(tweetsByTime);

        console.debug('##########\nsorting all tweets for addSorted on ' + feed + ' ' + tweets.length + ' tweets');
        var scroll = this.timeline && this.timeline.feed === this.feeds.timeline;
        feed.addSorted(tweets, undefined, true, {
            scroll: scroll,
            setSorted: deleted,
            account: this
        });
    },

    deleteFeed: function(opts) {
        var self = this, name = opts.feedName;
        if (!name) return;

        console.log('deleteFeed: ' + name);

        var didFind = false;
        $.each(this.customFeeds, function (i, feed) {
            if (feed.name !== name) return;
            didFind = true;

            if (feed.source) {
                if (!arrayRemove(self.sources, feed.source))
                    console.error('did not remove source ' + feed.source);
            }

            self.customFeeds.splice(i, 1);

            // when deleting a custom feed, the timeline may change
            // b/c of filtering and merging
            var timeline = self.feeds.timeline;
            if (timeline && feed !== timeline) {
                var deleted = timeline.feedDeleted(feed.serialize(), self.customFeeds);
                self.addAllSorted(timeline, deleted);
            }

            delete self.feeds[name];
            self.notifyFeeds();
            self.doNotifyUnread();
            return false;
        });

        if (!didFind) console.warn('deleteFeed ' + name + ' did not find a feed to delete');
    },

    uniqueFeedName: function(type) {
        var name;
        var i = 1;
        do { name = type + ':' + i++;
        } while (name in this.feeds);
        return name;
    },

    editFeed: function(feedDesc) {
        var name = feedDesc.name; assert(name);
        var feed = this.feeds[name]; assert(feed);
        var timeline = this.feeds.timeline;

        timeline.feedDeleted(feed.serialize(), this.customFeeds);

        var needsUpdate = feed.updateOptions(feedDesc);

        timeline.feedAdded(this, feed.serialize());

        if (needsUpdate) {
            this.refreshFeedItems(feed);
            this.addAllSorted(timeline, true);
        }

        this.notifyFeeds();
        if (needsUpdate)
            this.doNotifyUnread();
    },

    findFeed: function(feedDesc) {
        console.log('findFeed: ' + JSON.stringify(feedDesc));

        if (feedDesc['type'] === 'search' && feedDesc['query']) {
            var foundFeed;
            $.each(this.feeds, function(i, feed) {
                if (feed.query && feed.query === feedDesc['query']) {
                    foundFeed = feed;
                    return false;
                }
            });

            if (foundFeed)
                return foundFeed;
        }
    },

    getAllGroupIds: function() {
        var allIds = [];
        $.each(this.customFeeds, function (i, feed) {
            var userIds = feed.userIds;
            if (userIds)
                for (var i = 0; i < userIds.length; ++i)
                    allIds.push(userIds[i]);
        });
        return allIds;
    },

    addFeed: function(feedDesc, shouldChangeView) {
        console.debug('addFeed(' + JSON.stringify(feedDesc) + ')');
        console.log(JSON.stringify(feedDesc));

        var existingFeed = this.findFeed(feedDesc);
        if (existingFeed) {
            console.log('returning existing feed ' + existingFeed);
            if (this.timeline.feed !== existingFeed)
                this.changeView(existingFeed['name']);
            return existingFeed;
        }

        if (shouldChangeView === undefined)
            shouldChangeView = true;

        // assign user created feeds a unique name
        if ((feedDesc.type === 'group' || feedDesc.type === 'search' || feedDesc.type === 'user') &&
            feedDesc.name === undefined)
            feedDesc.name = this.uniqueFeedName(feedDesc.type);

        if (feedDesc.type === 'search' && !feedDesc.save)
            D.notify('hook', 'digsby.statistics.twitter.new_search')

        var self = this,
            feed = createFeed(this.tweets, feedDesc);

        if (shouldChangeView)
            this.addAllSorted(feed);

        var source = feed.makeSource(self);
        if (source) {
            this.sources.push(source);
            if (shouldChangeView) {
                var done = function() { self.timeline.finish(); };
                var obj = {success: done, error: done};
                console.log('in addFeed, updating source ' + source + ' now');
                source.update(obj);
            }
        }

        this.feeds[feed.name] = feed;
        this.customFeeds.push(feed);

        if (shouldChangeView) {
            this.notifyFeeds();
            this.changeView(feed['name']);
        }

        if (feed !== this.feeds.timeline) {
            //console.debug('calling feedAdded: ' + JSON.stringify(feedDesc));
            this.feeds.timeline.feedAdded(this, feedDesc);
        } else
            console.warn('feed is timeline, skipping feedAdded');

        return feed;
    },

    addGroup: function(feedDesc, shouldChangeView) {
        return this.addFeed(feedDesc, shouldChangeView);
    },

    // map of {feedName: [account option name, default minutes to update]}
    account_opts_times: {timeline: ['friends_timeline', 2],
                         directs:  ['direct_messages', 10],
                         mentions: ['replies', 2]},

    setAccountOptions: function(opts) {
        if (!this.feeds)
            return;

        console.warn('setAccountOptions: apiRoot ' + opts.apiRoot);
        if (opts.apiRoot)
            this.apiRoot = opts.apiRoot;

        var invite_url = opts.demovideo_link ? opts.demovideo_link : INVITE_URL;
        this.invite_message = INVITE_TEXT + invite_url;

        // opts may have values for the updateFrequency of the main feeds.
        var self = this;
        console.debug('setAccountOptions');
        $.each(this.feeds, function (name, feed) {
            if (feed.name in self.account_opts_times) {
                var feedopts = self.account_opts_times[feed.name];
                var optName = feedopts[0];
                var defaultUpdateMins = feedopts[1];
                var minutes = optName in opts ? opts[optName] : defaultUpdateMins;

                console.debug('feed: ' + feed.name + ' ' + minutes);
                feed.source.setUpdateFrequency(1000 * 60 * minutes);
            }
        });

        this.searchUpdateFrequency = 1000 * 60 * get(opts, 'search_updatefreq', 2);

        settings.autoscroll_when_at_bottom = get(opts, 'autoscroll_when_at_bottom', true);

        this.offlineMode = opts.offlineMode;
        if (this.offlineMode)
            console.warn('twitter is in offline mode');
    },

    initializeFeeds: function(tx, userFeeds, opts, success, error) {
        var self = this;

        if (!this.selfUser && !this.selfScreenNameLower) {
            // if we haven't looked up our own id yet, then do so first
            this.verifyCredentials(function() { self.initializeFeeds(undefined, userFeeds, opts, success, error); },
                                   error);
            return;
        }

        var tweets = this.tweets = {};

        // the base set of all feeds
        this.customFeeds = [];
        var feeds = this.feeds = {
            favorites: new TwitterFavoritesFeedModel(tweets),
            history: new TwitterHistoryFeedModel(tweets, {screen_name: this.selfScreenNameLower})
        };

        self.sources = $.map(objectValues(feeds), function(f) { return f.makeSource(self) || null; });
        console.warn('created ' + self.sources.length + ' self.sources');

        if (userFeeds.length) {
            // Construct feeds here. Take care to construct the main timeline
            // view first, since it needs to be around when we construct the other
            // feeds, which may affect it via filtering and merging.
            var userFeedsRearranged = Array.apply(null, userFeeds);
            userFeedsRearranged.sort(function(a, b) {
                // timeline goes first
                return -cmp(a.type==='timeline', b.type==='timeline');
            });
            $.each(userFeedsRearranged, function (i, feedOpts) { self.addFeed(feedOpts, false); });

            // Rearrange the feeds back into their original user order.
            this.setFeeds(userFeeds);
        }

        this.setAccountOptions(opts);

        var successCount = 0;
        function _success(tablename, tweets) {
            console.log('loaded ' + tweets.length + ' cached tweets');
            assert(feeds);
            self.newTweets(tweets);

            var toDeleteIds = [];

            assert(tweets);

            // discard any tweets that we pulled out of the cache, but
            // not added to any timelines
            $.each(tweets, function (i, tweet) {
                if (!tweet.feeds || !objectKeys(tweet.feeds).length)
                    toDeleteIds.push(tweet.id);
            });

            console.debug('discarding ' + toDeleteIds.length + ' ' + tablename);
            self.discard(tablename, toDeleteIds);
            if (++successCount === 2 && success)
                success();
        }

        function _error(err) {
            console.error('error: ' + err.message);
            if (error) error(err);
        }

        self.loadAllCached({tx: tx,
                            success: _success,
                            error: _error});
    },

    setFeeds: function(newFeeds) {
        // rearrange feeds
        var feeds = this.feeds;
        this.customFeeds = $.map(newFeeds, function(f) {
            return feeds[f.name];
        });
        this.notifyFeeds();
    },

    changeView: function (feed) {
        console.warn('changeView(' + JSON.stringify(feed) + ')');
        console.warn('  typeof feed is ' + (typeof feed));

        if (typeof feed !== 'string') {
            // can be a new feed description
            console.log('got a feed description, calling addFeed');
            feed = this.addFeed(feed, true);
            return;
        }

        var self = this;

        var timeline = this.timeline;
        timeline.pauseMarkAsRead(true);
        timeline.viewChanged(feed);

        timeline.pauseMarkAsRead(false, function() {
            if (self.feeds[feed].scrollToBottom)
                // history and favorites start scrolled to the bottom
                timeline.scrollToBottom();
            else
                timeline.scrollToNew();
        });

        console.warn('changeView: ' + feed);

        // switching away from a non-saved search feed deletes it.
        var toDelete = [];
        $.each(this.feeds, function (i, f) {
            if (f.query && !f.save && f.name !== feed)
                toDelete.push(f.name);
        });

        if (toDelete.length)
            $.each(toDelete, function (i, name) { self.deleteFeed({feedName: name}); });

        this.notifyClients('viewChanged', feed);
    },

    timelineClosing: function() {
        console.log('timelineClosing');
        var self = this;
        var feed = this.timeline.feed;
        if (feed.query && !feed.save) {
            console.log('yes');
            setTimeout(function() { self.deleteFeed({feedName: feed.name}); }, 50);
        }
    },

    setupSql: function (success, error) {
        function _success(tx) {
            executeSql(tx,
                'create table if not exists info_keyed (' +
                'key text primary key, ' +
                'value text)', [],
                success, error);
        }

        var self = this;
        var makeTables = function (tx, sqls) {
            if (sqls.length === 0)
                _success(tx);
            else
                sqls[0].ensureTableExists(tx, function (tx, result) {
                    makeTables(tx, sqls.slice(1));
                }, error);
        };

        function didCheckForExistingTweets(tx) {
            makeTables(tx, objectValues(self.sql));
        }

        // Assume that if the "Tweets" table does not exist, this is a new account. We'll mark
        // tweets from the first update as already read.
        window.db.transaction(function (tx) {
            executeSql(tx, "select * from Tweets limit 1", [],
                didCheckForExistingTweets,
                function (tx, err) { self.firstUpdate = true; didCheckForExistingTweets(tx); }
            );
        });
    },

    isSelfTweet: function(t) {
        var user = this.users[t.user];
        if (user) {
            if (this.selfUser)
                return user.id === this.selfUser.id;
            else
                return user.screen_name.toLowerCase() === this.selfScreenNameLower;
        }
    },

    isMention: function(t) {
        // consider tweets with your @username not at the beginning
        // still a mention
        return (
            t.text.toLowerCase().search('@' + this.selfScreenNameLower) !== -1)
            ? true : false;
    },

    isDirect: function(t) {
        return t.recipient_id ? true : false;
    },

    verifyCredentials: function(done, onError, retried) {
        var self = this;

        loadServerTime(function() {

            function onJSON(json) {
                self.selfUser = self.users[json.id] = self.sql.users.fromJSON(json);
                self.selfScreenNameLower = self.selfUser.screen_name.toLowerCase();
                if (done) done();
            }

            function cacheCredentials(data) {
                var json = JSON.stringify(data);
                console.log('caching credentials');
                window.db.transaction(function(tx) {
                    executeSql(tx, "insert or replace into info_keyed values (?, ?)",
                                  [self.username, json]);
                }, errorFunc('error caching credentials'));
            }

            function doVerifyRequest() {
                var url = self.apiRoot + 'account/verify_credentials.json';
                self.urlRequest(url,
                    function (data) {
                        console.log('verify_credentials call returned successfully');
                        cacheCredentials(data);
                        onJSON(data);
                    },
                    function (error) {
                        console.error('could not verify credentials: ' + error.message);
                        if (retried) {
                            console.error('onError is ' + onError);
                            if (onError) onError();
                        } else {
                            console.error('retrying in 1min.');
                            setTimeout(function() {
                                self.verifyCredentials(done, onError, true);
                            }, 1000 * 60);
                        }
                    }
                );
            }

            console.log('checking for credentials in database.');
            window.db.transaction(function(tx) {
                function success(tx, result) {
                    if (result.rows.length) {
                        onJSON(JSON.parse(result.rows.item(0).value));
                    } else {
                        doVerifyRequest();
                    }
                }
                executeSql(tx, "select value from info where key == ?",
                    [self.username], success, doVerifyRequest);
            });
        });
    },

    getTweetType: function(t) {
        var tweet_type = 'timeline';

        if (this.isSelfTweet(t))
            tweet_type = 'sent';
        else if (t.mention)
            tweet_type = 'mention';
        else if (t.search)
            tweet_type = 'search';
        else if (t.sender_id)
            tweet_type = 'direct';
        return tweet_type;
    },

    getFollowingUsers: function() {
        var self = this,
            url = this.apiRoot + 'statuses/friends.json';
        this.pagedUrlRequest(url, {
            itemsKey: 'users',
            success: function (users) {
                if (!users.length)
                    console.warn('no users returned in success callback for getFollowingUsers');
                else
                    // save users out to database.
                    window.db.transaction(function (tx) {
                        $.each(users, function(i, user) {
                            self.sql.users.insertOrReplace(tx, user);
                        });
                    }, function (err) {
                        console.error('error caching users following: ' + err);
                    });
            },
            error: function (xhr, error) {
                console.error('error getting users we are following: ' + error);
            }
        });
    },

    getFollowing: function(opts) {
        var opts = opts || {};

        var self = this;
        if (!this.didGetFollowing) {
            this.didGetFollowing = true;
            var followingUrl = this.apiRoot + 'friends/ids.json';
            function success(data) {
                self.notifyClients('didReceiveFollowing', data);
                var following = JSON.parse('['+data+']');
                self.maybeGetAllUsers(following);
                self.following_ids = set(following);
                if (opts.success)
                    opts.success();
            }
            this.urlRequest(followingUrl, success, errorFunc('retreiving IDs the user is following'),
                            {dataType: undefined});
        }
    },

    maybeGetAllUsers: function(following) {
        // if there are any IDs in following that we don't have users for, go
        // get them from the network.
        var self = this, missing = false;
        $.each(following, function (i, id) {
            if (!(id in self.users)) {
                self.getFollowingUsers();
                return false;
            }
        });
    },

    getTrends: function() {
        var self = this;
        function success(data) { self.notifyClients('didReceiveTrends', data); }
        var url = this.searchApiRoot + 'trends/current.json';
        this.urlRequest(url, success, errorFunc('error retrieving trends'));
    },

    onRealTimeTweet: function(tweetjson) {
        var self = this;

        if ('delete' in tweetjson)
            return this.onRealTimeDeleteTweet(tweetjson);

        // realtime tweet stream also includes @replys to people in the following
        // list, so filter out any tweets from users not in our following_ids set
        if (this.showAllRealtime ||
            (this.following_ids && tweetjson.user.id in this.following_ids)) {

            // filter out replies from people we're following to people we are
            // NOT following, to match the website. (settting?)
            var reply_to = tweetjson.in_reply_to_user_id;
            if (!reply_to || reply_to in this.following_ids) {
                var tweet = this.makeTweetFromNetwork(tweetjson);
                assert(tweet !== undefined);
                self.appendTweet(tweet);
                if (!this.isSelfTweet(tweet))
                    showPopupsForTweets(this, [tweet]);
                this.cacheTweets([tweet]);
                this.doNotifyUnread();
            }
        }
    },

    onRealTimeDeleteTweet: function(tweetjson) {
        console.log('TODO: streaming API sent delete notice for status ' + tweetjson.status.id);
    },

    getUsers: function(opts, justFollowing) {
        if (justFollowing === undefined)
            justFollowing = true;

        // if justFollowing is true (the default), only return users with ids
        // in this.following_ids
        var usersMap;
        if (justFollowing && this.following_ids) {
            usersMap = {};
            var followingIds = this.following_ids;
            $.each(this.users, function (id, user) {
                if (id in followingIds) usersMap[id] = user;
            });
        } else
            usersMap = this.users;

        if (opts.success)
            opts.success(usersMap);
    },

    addClient: function(client) {
        this.clients.push(client);
    },

    changeState: function(state) {
        console.warn('changeState: ' + state);

        if (state === 'oautherror' && this.state !== 'oautherror') {
            this.state = state;
            this.notifyClients('stateChanged', 'oautherror');
            this.stopTimers('oautherror');
        } else if (state === 'autherror') {
            this.state = state;
            this.notifyClients('stateChanged', 'autherror');
            this.stopTimers('autherror');
        } else if (state == 'connfail') {
            if (this.state !== 'autherror') { // do not go from autherror to connfail
                this.state = state;
                this.notifyClients('stateChanged', 'connfail');
                this.stopTimers('connection fail');
            }
        } else if (state == 'online') {
            if (this.state === undefined) {
                this.state = 'online';
                this.notifyClients('stateChanged', 'online');
            }
        } else {
            console.error('changeState got unknown state: ' + state);
        }
    },

    notifyClients: function(funcName/*, *args */) {
        var args = Array.apply(null, arguments);
        args.shift();

        $.each(this.clients, function(i, client) {
            client[funcName].apply(client, args);
        });
    },

    notifyFeeds: function(name) {
        var feedsJSON = $.map(this.customFeeds, function (feed) {
            return feed.serialize ? feed.serialize() : null;
        });
        this.notifyClients(name || 'feedsUpdated', feedsJSON);
    },

    getTweet: function(id, success, error) {
        var self = this;

        // first, try loading the tweet from the cache
        var cacheSuccess = function(tx, tweets) {
            if (tweets.length !== 1) {
                console.log('cacheSuccess expected one tweet, got ' + tweets.length);
                return loadFromNetwork();
            }
            success(tweets[0]);
        };

        var cacheError = function(err) {
            console.error('could not retreive tweet ' + id + ' from the database: ' + err.message);
            loadFromNetwork();
        };

        // if that fails, grab it from the network
        var loadFromNetwork = function() {
            function urlSuccess(data) {
                var tweet = self.makeTweetFromNetwork(data);
                self.cacheTweets([tweet], function() { success(tweet); });
            }

            var url = self.apiRoot + 'statuses/show/' + id + '.json';
            self.urlRequest(url, urlSuccess, error);
        };

        this.loadCachedTweets({id: id, limit: 1, success: cacheSuccess, error: cacheError});
    },

    /**
     * Handles X-RateLimit- HTTP response headers indicating API request
     * limits.
     */
    handleRateLimits: function(xhr, textStatus) {
        var r = {limit:     xhr.getResponseHeader('X-RateLimit-Limit'),
                 remaining: xhr.getResponseHeader('X-RateLimit-Remaining'),
                 reset:     xhr.getResponseHeader('X-RateLimit-Reset')};

        var dateStr = xhr.getResponseHeader('Date');
        if (dateStr) {
            var date = new Date(dateStr);
            if (date) receivedCorrectTimestamp(date, true);
        }


        if (r.limit && r.remaining && r.reset) {
            this.rateLimit = r;
            if (parseInt(r.remaining, 10) < 20)
                console.log('remaining API requests: ' + r.remaining);
        }
    },

    /**
     * Sends a tweet or direct.
     *   replyTo   can be an id that the tweet is in reply to
     *   success   is called with the tweet object
     *   error     is called with an exception object
     */
    tweet: function(text, replyTo, success, error) {
        // make "d screen_name message" a direct message
        var direct = text.match(/^d\s+(\S+)\s+(.+)/);
        if (direct) {
            var screen_name = direct[1];
            if (screen_name.charAt(screen_name.length-1) === ':')
                screen_name = screen_name.slice(0, screen_name.length-1);
            text = direct[2];
            return this.direct(screen_name, text, success, error);
        }

        var self = this;
        var opts = {status: text,
                    source: 'digsby'};
        if (replyTo)
            opts.in_reply_to_status_id = replyTo;

        var url = this.apiRoot + 'statuses/update.json';

        function _success(data) {
            self.notifyClients('statusUpdated');
            var tweet = self.makeTweetFromNetwork(data);
            self.appendTweet(tweet, {ignoreIds: true});
            self.cacheTweets([tweet], function() {
                var t = notifyTweet(self, tweet);
                self.notifyClients('selfTweet', t);
                if (success) success(t);
            });
        }

        this.urlRequest(url, _success, error, {type: 'POST', data: opts});
    },

    direct: function(screen_name, text, success, error) {
        var self = this,
            opts = {text: text, screen_name: screen_name},
            url = this.apiRoot + 'direct_messages/new.json';

        var _success = function(data) {
            self.notifyClients('directSent');
            var direct = self.makeDirectFromNetwork(data);
            self.appendTweet(direct);
            self.cacheDirects([direct], function() {
                if (success) success(notifyTweet(self, direct));
            });
        };

        this.urlRequest(url, _success, extractJSONError('Error sending direct message', error), {type: 'POST', data: opts});
    },

    deleteTweet: function(opts) {
        return this.deleteItem('tweets', 'statuses/destroy/', opts);
    },

    deleteDirect: function(opts) {
        return this.deleteItem('directs', 'direct_messages/destroy/', opts);
    },

    deleteItem: function(sql, urlPart, opts) {
        var self = this;

        function success(tweet) {
            useStringIdentifiers(tweet, ['id', 'in_reply_to_status_id']);
            console.log('successfully deleted ' + sql + ' ' + tweet.id);
            self.discard(sql, [tweet.id]); // remove from sql cache
            delete self.tweets[tweet.id];  // remove from memory cache
            // remove from any feeds.
            $.each(self.feeds, function (i, feed) { feed.removeItem(tweet); });

            if (opts.success) {
                // scroll to bottom if necessary.
                if (self.timeline)
                    self.timeline.scrollToBottomIfAtBottom(function() { opts.success(tweet); });
                else
                    opts.success(tweet);
            }
        }

        return this.urlRequest(this.apiRoot + urlPart + opts.id + '.json',
                               success,
                               opts.error,
                               {type: 'POST'});
    },

    follow: function(opts) {
        console.warn('follow: ' + JSON.stringify(opts));

        if (opts.screen_name) {
            function success(data) {
                console.warn('follow success:');
                console.warn(JSON.stringify(data));
                if (opts.success)
                    opts.success();
            }

            function error(err) {
                console.error('error following' + opts.screen_name);
                printException(err);
                if (opts.error) opts.error(err);
            }

            this.urlRequest(this.apiRoot + 'friendships/create.json',
                            success, opts.error || errorFunc('error following'),
                            {type: 'POST', data: {screen_name: opts.screen_name}});
        }
    },

    appendTweet: function(tweet, opts) {
        if (this.timeline) {
            var self = this;
            this.timeline.scrollToBottomIfAtBottom(function() {
                opts = opts || {};
                opts.scroll = false;
                self.newTweets([tweet], undefined, true, opts);
            });
        }
    },

    newTweets: function (tweets, source, updateNow, opts) {
        if (opts === undefined) opts = {};
        opts.account = this;
        callEach(this.feeds, 'addSorted', tweets, source, updateNow, opts);
        var timeline = this.feeds.timeline;
        if (this.lastNotifiedMaxId === undefined ||
            this.lastNotifiedMaxId !== timeline.source.maxId) {
            var recentTweets = timeline.items.slice(-200);
            this.notifyClients('recentTimeline', recentTweets);
        }
    },

    /**
     * twitter API has paged requests using a "cursor" parameter
     */
    pagedUrlRequest: function(url, opts) {
        if (opts.itemsKey === undefined)
            throw 'pagedUrlRequest: must provide "itemsKey" in opts'

        var self = this,
            nextCursor = -1;
            allData = [];

        function _success(data) {
            // append data
            arrayExtend(allData, data[opts.itemsKey]);
            nextCursor = data.next_cursor;

            if (nextCursor === 0 || nextCursor === undefined) // next_cursor 0 means we hit the end
                return opts.success(allData);
            else
                nextRequest();
        }

        function nextRequest() {
            opts.data = {cursor: nextCursor};
            self.urlRequest(url, _success, opts.error, opts);
        }

        nextRequest();
    },

    /* currently unused */
    getFollowedBy: function(_success) {
        var self = this;
        var url = this.apiRoot + 'followers/ids.json';
        this.pagedUrlRequest(url, {
            itemsKey: 'ids',
            success: function (ids) {
                self.followers = set(ids);
                if (_success)
                    _success(ids);
            },
            error: errorFunc('retreiving followers')
        });
    },

    urlRequest: function(url, success, error, opts) {
        var self = this;
        opts = opts || {};

        function _error(xhr, textStatus, errorThrown) {
            if (xhr.status === 401) {
                console.error('authentication error');

                if (!self.didUpdate) {
                    if (self.oauth)
                        self.changeState('oautherror');
                    else
                        // ignore auth errors after already connected
                        self.changeState('autherror');
                }
            }

            if (error)
                error(xhr, textStatus, errorThrown);
        }

        var httpType = opts.type || 'GET';
        console.log(httpType + ' ' + url);
        if (opts.data)
            console.log(JSON.stringify(opts.data));

        var basicAuthUsername, basicAuthPassword;
        var authHeader;

        if (url.substr(0, this.searchApiRoot.length) !== this.searchApiRoot) {
            if (this.oauth) {
                if (!opts.data) opts.data = {};
                authHeader = this.getOAuthHeader({url: url, method: httpType, data: opts.data});
            } else {
                basicAuthUsername = encodeURIComponent(this.username);
                basicAuthPassword = encodeURIComponent(this.password);
            }
        }

        return $.ajax({
            url: url,
            success: success,
            error: _error,
            type: httpType,
            data: opts.data,

            dataType: opts.dataType || 'json',
            dataFilter: function (data, type) {
                var obj;
                if (type.toLowerCase() === 'json') {
                    try {
                        obj = JSON.parse(data);
                    } catch (err) {
                        // show what the bad data was, if it wasn't JSON
                        console.error('ERROR parsing JSON response, content was:');
                        console.error(data);
                        throw err;
                    }

                    return obj;
                } else
                    return data;
            },

            username: basicAuthUsername,
            password: basicAuthPassword,

            complete: this.handleRateLimits,
            beforeSend: function(xhr) {
                xhr.setRequestHeader('User-Agent', 'Digsby');
                if (authHeader)
                    xhr.setRequestHeader('Authorization', authHeader);
            }
        });
    },

    getOAuthHeader: function(opts) {
        var paramList = [];
        for (var k in opts.data)
            paramList.push([k, opts.data[k]]);

        paramList.sort(function(a, b) {
            if (a[0] < b[0]) return -1;
            if (a[0] > b[0]) return 1;
            return 0;
        });

        var message = {
            action: opts.url,
            method: opts.method,
            parameters: paramList
        };

        var accessor = {
            consumerKey: this.oauth.consumerKey,
            consumerSecret: this.oauth.consumerSecret,

            token: this.oauth.tokenKey,
            tokenSecret: this.oauth.tokenSecret
        };

        OAuth.completeRequest(message, accessor);
        return OAuth.getAuthorizationHeader(undefined, message.parameters)
    },

    favorite: function(tweet, onSuccess, onError) {
        var self = this;
        var url, favoriting;
        if (tweet.favorited) {
            url = this.apiRoot + 'favorites/destroy/' + tweet.id + '.json';
            favoriting = false;
        } else {
            url = this.apiRoot + 'favorites/create/' + tweet.id + '.json';
            favoriting = true;
        }

        // TODO: this is the same as getTweet
        function urlSuccess(data) {
            var tweet = self.makeTweetFromNetwork(data);
            tweet.favorited = favoriting;
            self.cacheTweets([tweet], function() { if (onSuccess) {onSuccess(tweet);} });
        }

        this.urlRequest(url, urlSuccess, onError, {type: 'POST'});
    },

    cacheFavorited: function(tweetIds, favorited) {
        var ids = '(' + joinSingleQuotedStringArray(tweetIds, ', ') + ')';
        var sql = 'update or ignore tweets set favorited = ' + (favorited ? '1' : '0') + ' where id in ' + ids;
        window.db.transaction(function(tx) {
            executeSql(tx, sql, [], null, errorFunc('error unfavoriting items'));
        });
    },

    makeTweetFromNetwork: function(item, markRead) {
        useStringIdentifiers(item, ['id', 'in_reply_to_status_id']);

        if (item.id in this.tweets)
            return this.tweets[item.id];

        item = transformRetweet(item);

        var tweet = this.makeTweet(item);
        var user = tweet.user;
        // tweets from network have full User JSON
        this.users[user.id] = user;
        // but we'll just store ID in memory and on disk
        tweet.user = user.id;
        // categorize mentions as such if they contain @username
        tweet.mention = this.isMention(tweet);

        if (this.isSelfTweet(tweet)) {
            this.maybeNotifySelfTweet(tweet);
            tweet.read = 1;
        } else if (markRead) {
            tweet.read = 1;
        } else {
            tweet.read = 0;
        }

        return tweet;
    },

    makeDirect: function(item, override) {
        var direct = this.sql.directs.fromJSON(item, override);
        this.tweets[direct.id] = direct;
        direct.toString = directToString;
        direct.created_at_ms = new Date(direct.created_at).getTime();
        direct.user = direct.sender_id;
        return direct;
    },

    makeDirectFromNetwork: function(item, markRead) {
        useStringIdentifiers(item, ['id']);
        if (item.id in this.tweets)
            return this.tweets[item.id];
        var direct = this.makeDirect(item);

        this.users[direct.user] = item.sender;
        direct.read = (markRead || this.isSelfTweet(direct)) ? 1 : 0;

        return direct;
    },

    makeTweet: function(item, override) {
        var tweet = this.sql.tweets.fromJSON(item, override);
        this.tweetIn(tweet);
        return tweet;
    },

    tweetIn: function(tweet) {
        var oldTweet = this.tweets[tweet.id];
        if (oldTweet && oldTweet.read !== undefined)
        	tweet.read = oldTweet.read;
        this.tweets[tweet.id] = tweet;
        tweet.toString = tweetToString;
        tweet.created_at_ms = new Date(tweet.created_at).getTime();
    },

    cacheTweets: function (tweets, ondone) {
        return this.cacheItems(tweets, ondone, this.sql.tweets);
    },

    cacheDirects: function (directs, ondone) {
        return this.cacheItems(directs, ondone, this.sql.directs);
    },

    cacheItems: function (tweets, ondone, sql) {
        if (tweets.length === 0) {
            if (ondone) guard(ondone);
            return;
        }

        console.log("cacheItems() is saving " + tweets.length + " items to " + sql);

        var self = this;
        window.db.transaction(function(tx) {
            // insert tweets
            $.each(tweets, function (i, tweet) {

                sql.insertOrReplace(tx, tweet);
            });

            // update users
            $.each(tweets, function (i, tweet) {
                if (tweet.user !== null)
                    self.sql.users.insertOrReplace(tx, self.users[tweet.user]);
            });

        }, function (error) {
            console.error('Failed to cache tweets to database: ' + error.message);
            if (ondone) ondone();
        }, function () {
            if (ondone) ondone();
        });
    },

    discard: function(tablename, ids) {
        if (ids.length === 0) return;
        ids = '(' + joinSingleQuotedStringArray(ids, ', ') + ')';
        var deleteStatement = 'delete from ' + tablename + ' where id in ' + ids;
        window.db.transaction(function (tx) {
            executeSql(tx, deleteStatement, [], null, errorFunc('discarding ' + tablename));
        });
    },

    markAllAsRead: function() {
        this.markTweetsAsRead(this.tweets);
    },

    markFeedAsRead: function(name) {
        if (name in this.feeds)
            this.markTweetsAsRead(this.feeds[name].items);
    },

    toggleAddsToCount: function(name) {
        var feed = this.feeds[name];
        if (feed) {
            feed.noCount = !feed.noCount;
            this.notifyFeeds();
            this.doNotifyUnread();
        }
    },

    markTweetsAsRead: function(tweets) {
        var self = this;
        $.each(tweets, function (i, t) { self.markAsRead(t); });
    },

    markAsRead: function(item) {
        var self = this;

        if (!item || item.read) return;
        var id = item.id;

        //console.log('markAsRead: ' + item.text);
        item.read = 1;
        if (item.feeds)
            $.each(item.feeds, function(i, feed) { feed.markedAsRead(item); });

        self.doNotifyUnread();

        if (this.markAsReadLater === undefined)
            this.markAsReadLater = {};

        this.markAsReadLater[id] = true;

        if (this.markAsReadTimer === undefined) {
            var unreadTimerCb = function () {
                self.recordReadTweets();
            };
            this.markAsReadTimer = this.ownerWindow.setTimeout(unreadTimerCb, 1000);
        }
    },

    connectionFailed: function() {
        this.notifyClients('connectionFailed');
        if (!this.didUpdate)
            // if this is the first login attempt, just stop timers and die
            this.stopTimers('connectionFailed');
    },
    /**
     * calls onRead on all clients with {name: unreadCount, ...} for
     * each feed.
     */
    doNotifyUnread: function(force) {
        var self = this;
        if (this.notifyUnreadTimer === undefined)
            this.notifyUnreadTimer = setTimeout(function() {
                self._notifyUnread(self);
            }, 200);
    },

    _notifyUnread: function(self) {
        delete self.notifyUnreadTimer;
        var unread = {};
        var feeds = $.map(self.customFeeds, function (feed) {
            if (!feed.addsToUnreadCount())
                // don't include tweets from unsaved searches
                return null;

            $.each(feed.items, function (i, tweet) {
                if (!tweet.read)
                    unread[tweet.id] = true;
            });

            return feed.serialize();
        });

        self.notifyClients('onUnread', {
            feeds: feeds,
            total: objectKeys(unread).length
        });
    },

    recordReadTweets: function() {
        delete this.markAsReadTimer;

        var ids = [];
        for (var id in this.markAsReadLater) {
            if (this.markAsReadLater[id])
                ids.push(id);
        }

        this.markAsReadLater = [];

        if (ids.length) {
            var idsSql = joinSingleQuotedStringArray(ids, ', ');
            var sql1 = 'UPDATE Tweets SET read=1 WHERE Tweets.id IN (' + idsSql + ')';
            // TODO: hack. we're using two tables, don't do this
            var sql2 = 'UPDATE Directs SET read=1 WHERE Directs.id IN (' + idsSql + ')';
            window.db.transaction(function(tx) {
                executeSql(tx, sql1);
                executeSql(tx, sql2);
            }, function (error) {
                console.error('failed to mark as read: ' + error.message);
                console.error('sql was:');
                console.error(sql1);
                console.error(sql2);
            });
        }
    },

    loadAllCached: function(opts) {
        var self = this, allTweets = [];

            self.loadCachedUsers({tx: opts.tx, error: opts.error, success: function(tx) {
                self.loadCachedTweets({tx: tx, error: opts.error, success: function(tx, tweets) {
                    opts.success('tweets', tweets);

                    // immediately notify the GUI of the newest self tweet we know about.
                    self.possibleSelfTweets(tweets);

                    self.loadCachedDirects({tx: tx, error: opts.error, success: function (tx, directs) {
                        opts.success('directs', directs);
                    }});
                }});
            }})
    },

    possibleSelfTweets: function (tweets) {
        var selfTweet = this.findNewestSelfTweet(tweets);
        if (selfTweet) this.maybeNotifySelfTweet(selfTweet);
    },

    maybeNotifySelfTweet: function(tweet) {
        if (!this.newestSelfTweet || this.newestSelfTweet.created_at_ms < tweet.created_at_ms) {
            this.newestSelfTweet = notifyTweet(this, tweet);
            this.notifyClients('selfTweet', this.newestSelfTweet);
        }
    },

    findNewestSelfTweet: function (tweets) {
        var self = this, newest;
        $.each(tweets, function (i, tweet) {
            if (self.isSelfTweet(tweet) && tweet.created_at_ms &&
                (!newest || tweet.created_at_ms > newest.created_at_ms))
                newest = tweet;
        });

        if (newest)
            return newest;
    },

    addGroupsFromLists: function() {
        var self = this;
        this.getLists(function (groups) {
            $.each(groups, function (i, group) {
                self.addGroup(group, false);
            });
        });
    },

    getLists: function(success) {
        var self = this,
            urlPrefix = this.apiRoot + this.selfScreenNameLower + '/';

        var getListsSuccess = success;
        var groups = [];

        self.pagedUrlRequest(urlPrefix + 'lists.json', {
            itemsKey: 'lists',
            error: errorFunc('could not get list ids'),
            success: function (lists) {
                var i = 0;

                function nextGroup() {
                    var list = lists[i++];
                    if (!list) return getListsSuccess(groups);
                    var group = {type: 'group', groupName: list.name,
                                 filter: false, popups: false, ids: []};
                    var url = urlPrefix + list.slug + '/members.json';
                    self.pagedUrlRequest(url, {
                        itemsKey: 'users',
                        error: errorFunc('error retrieving ' + url),
                        success: function (users) {
                            $.each(users, function (i, user) { group.ids.push(user.id); });
                            groups.push(group);
                            nextGroup();
                        }
                    });
                }

                nextGroup();
            }
        });
    },

    cachedDirectColumnNames: 'directs.id as direct_id, users.id as user_id, *',

    loadCachedDirects: function(opts) {
        var self = this;

        function success(tx, result) {
            var directs = [];
            for (var i = 0; i < result.rows.length; ++i) {
                var row = result.rows.item(i);
                var direct_id = row.direct_id, user_id = row.user_id;
                if (user_id)
                    self.users[user_id] = self.sql.users.fromJSON(row, {id: user_id});
                var direct = self.makeDirect(row, {id: direct_id});
                directs.push(direct);
            }
            directs.reverse();
            if (opts.success) opts.success(tx, directs);
        }

        function error(tx, err) {
            if (opts.error) opts.error(err);
            else console.error('could not load cached directs: ' + err.message);
        }

        return this.loadCachedItems(opts, this.cachedDirectColumnNames, 'Directs', 'sender_id', success, error);
    },

    cachedTweetColumnNames: 'tweets.id as tweet_id, users.id as user_id, tweets.profile_image_url as tweet_image, users.profile_image_url as user_image, *',

    loadCachedTweets: function(opts) {
        var self = this;

        function success(tx, result) {
            var tweets = [];
            for (var i = 0; i < result.rows.length; ++i) {
                var row = result.rows.item(i);

                // avoid id name clash
                var tweet_id = row.tweet_id,
                    user_id = row.user_id,
                    user_image = row.user_image,
                    tweet_image = row.tweet_image;

                if (user_id)
                    self.users[user_id] = self.sql.users.fromJSON(row, {id: user_id, profile_image_url: user_image});
                var tweet = self.makeTweet(row, {id: tweet_id, profile_image_url: tweet_image});

                tweets.push(tweet);
            }

            tweets.reverse();

            if (opts.success)
                opts.success(tx, tweets);
        }

        function error(tx, err) {
            if (opts.error) opts.error(err);
            else console.error('could not load cached tweets: ' + err.message);
        }

        return this.loadCachedItems(opts, this.cachedTweetColumnNames, 'Tweets', 'user', success, error);
    },

    loadCachedItems: function(opts, columnNames, tableName, userColumn, success, error) {
        /* id: adds 'WHERE tweet.id == <id>'
           limit: adds 'LIMIT <limit>' */

        var self = this;

        var args = [];
        var innerQuery = "SELECT " + columnNames + " FROM " + tableName +
                         " LEFT OUTER JOIN Users ON " + tableName + "." + userColumn + " = Users.id";

        // WHERE tweet_id
        if (opts.id) {
            innerQuery += ' WHERE tweet_id==?';
            args.push(opts.id);
        }

        innerQuery += " ORDER BY " + tableName + ".id DESC";

        // LIMIT clause
        if (opts.limit) {
            innerQuery += ' LIMIT ?';
            args.push(opts.limit);
        }

        var query = "SELECT * FROM (" + innerQuery + ")";

        console.log(query);
        useOrCreateTransaction(opts.tx, query, args, success, error);
    },

    getUsersToKeep: function() {
        var excludedUserIds = [];
        if (this.following_ids)
            arrayExtend(excludedUserIds, objectKeys(this.following_ids));
        var groupIds = this.getAllGroupIds();
        if (groupIds)
            arrayExtend(excludedUserIds, groupIds);
        if (this.selfUser)
            excludedUserIds.push(this.selfUser.id);
        return excludedUserIds;
    },

    discardOldUsers: function(opts) {
        // discards all users not referenced by tweets or directs
        opts = opts || {};

        var excludedUserIds = this.getUsersToKeep();

        // don't discard users we're following either
        var appendClause = '';
        if (excludedUserIds.length) {
            var usersFollowing = excludedUserIds.join(', ');
            appendClause = 'and id not in (' + usersFollowing + ')';
        }

        var query = 'delete from users where id not in (select sender_id from directs union select user from tweets union select recipient_id from directs)' + appendClause;
        useOrCreateTransaction(opts.tx, query, [], opts.success, opts.error);
    },

    loadCachedUsers: function(opts) {
        var self = this,
            query = 'SELECT * FROM Users';

        function success(tx, result) {
            var added = 0;
            for (var i = 0; i < result.rows.length; ++i) {
                var row = result.rows.item(i);
                if (!(row.id in self.users)) {
                    self.users[row.id] = self.sql.users.fromJSON(row);
                    added += 1;
                }
            }

            console.log('loadCachedUsers loaded ' + added + ' users');
            if (opts.success)
                opts.success(tx);
        }

        function error(err) {
            console.error('error loading cached users: ' + err);
            if (opts.error)
                opts.error(err);
        }

        useOrCreateTransaction(opts.tx, query, [], success, error);
    },

    inviteFollowers: function() {
        var self = this;
        function cb(followers) {
            followers = $.grep(followers, function() { return true; });
            console.log('followers:');
            console.log(JSON.stringify(followers));

            if (!followers.length)
                return;

            // pick up to 200 random
            arrayShuffle(followers);
            var f2 = [];
            for (var i = 0; i < 200 && i < followers.length; ++i)
                f2.push(followers[i]);
            followers = f2;

            var idx = 0, errCount = 0;
            var errCount = 0;

            function _err() { if (++errCount < 5) _direct(); }

            function _direct() {
                var id = followers[idx++];
                if (id === undefined) return;
                var data = {text: self.invite_message, user_id: id};
                self.urlRequest(self.apiRoot + 'direct_messages/new.json',
                                _direct, _err, {type: 'POST', data: data});
            }

            _direct();
        }

        if (this.followers)
            cb(this.followers);
        else
            this.getFollowedBy(cb);
    }
};

function tweetUserImage(account, tweet) {
    var userId = tweet.user;
    if (userId) {
        var user = account.users[userId];
        if (user)
            return user.profile_image_url;
    }

    return tweet.profile_image_url;
}

function tweetUserName(account, tweet) {
    var userId = tweet.user;
    if (userId) {
        var user = account.users[userId];
        if (user) return user.name;
    }

    return tweet.from_user;
}

function tweetScreenName(account, tweet) {
    var userId = tweet.user;
    if (userId) {
        var user = account.users[userId];
        if (user) return user.screen_name;
    }

    return tweet.from_user;
}

function directTargetScreenName(account, direct) {
    var userId = direct.recipient_id;
    if (userId) {
        var user = account.users[userId];
        if (user) return user.screen_name;
    }
}

function TimelineSource() {
    this.maxId = '0';
}

TimelineSource.prototype = {
    toString: function() {
        return '<' + this.constructor.name + ' ' + this.url + '>';
    }
};

function TwitterTimelineSource(account, url, data) {
    if (account === undefined) // for inheritance
        return;

    this.account = account;
    this.url = url;
    this.data = data;
    this.count = 100;
    this.lastUpdateTime = 0;
    this.lastUpdateStatus = undefined;
    this.limitById = true;
    this._updateFrequency = 1000 * 60;
}

TwitterTimelineSource.prototype = new TimelineSource();
TwitterTimelineSource.prototype.constructor = TwitterTimelineSource;

TwitterTimelineSource.prototype.updateFrequency = function() {
    return this._updateFrequency;
};

TwitterTimelineSource.prototype.setUpdateFrequency = function(updateFreqMs) {
    this._updateFrequency = updateFreqMs;
};

TwitterTimelineSource.prototype.shouldMarkIncomingAsRead = function() {
    var markReadNow = this.markRead;
    if (this.markRead)
        this.markRead = false;
    return markReadNow;
};

TwitterTimelineSource.prototype.markNextUpdateAsRead = function() {
    this.markRead = true;
}

TwitterTimelineSource.prototype.ajaxSuccess = function(data, status, success, error, since_id) {
    try {
        var self = this;
        data.reverse();

        var newTweets = [];

        var markRead = self.shouldMarkIncomingAsRead();
        $.each(data, function (i, item) {
            var tweet = self.account.makeTweetFromNetwork(item, markRead);
            if (since_id && compareIds(tweet.id, since_id) < 0) {
                console.warn('IGNRORING TWEET WITH ID ' + tweet.id + ' LESS THAN since_id ' + since_id);
            } else {
                if (self.feed.alwaysMentions)
                    tweet.mention = 1;
                self.updateMinMax(tweet.id);
                newTweets.push(tweet);
            }
        });

        console.log("requestTweets loaded " + data.length + " tweets from the network");

        if (success) guard(function() {
            success(newTweets);
        });
    } catch (err) {
        if (error) {
            printStackTrace();
            error(err);
        }
        else throw err;
    }
};

/**
 * returns a simple jsonable object that gets passed to fire()
 */
var notifyTweet = function(account, t) {
    return {text: t.text,
            user: {screen_name: tweetScreenName(account, t),
                   profile_image_url: tweetUserImage(account, t)},
            id: t.id,
            favorited: t.favorited,
            created_at: t.created_at,
            created_at_ms: t.created_at_ms,
            tweet_type:account.getTweetType(t),

            // directs
            sender_id: t.sender_id,
            recipient_id: t.recipient_id};
};

function UpdateNotification(account, count, opts)
{
    assert(account);
    assert(count !== undefined);

    this.account = account;
    this.count = count;
    this.tweets = [];
    this.opts = opts || {};
    this.successCount = 0;
}

UpdateNotification.prototype = {
    success: function(source, tweets) {
        this.successCount++;

        assert(source && tweets);
        arrayExtend(this.tweets, tweets);
        this.onDone();

        if (this.opts.success)
            this.opts.success(source, tweets);
    },

    error: function(source) {
        this.onDone();
    },

    onDone: function() {
        //console.warn('UpdateNotification.onDone: ' + (this.count-1));
        var account = this.account;
        if (--this.count === 0) {
            if (!this.successCount)
                account.connectionFailed();
            else {
                showPopupsForTweets(account, this.tweets);
                if (account.timeline)
                    account.timeline.finish(false);

                if (this.opts.onDone)
                    this.opts.onDone(this.tweets);

                account.discardOldTweets();
                account.doNotifyUnread();
            }
        }
    }
};

function uniqueSortedTweets(tweets, timeline) {
    function tweetCmp(a, b) {
        // directs first, then mentions, then by id, then if it's in the timeline
        return (-cmp(account.isDirect(a), account.isDirect(b))
                || -cmp(account.isMention(a), account.isMention(b))
                || -cmp(timeline.hasTweet(a), timeline.hasTweet(b))
                || cmp(a.created_at_ms, b.created_at_ms)
                || compareIds(a.id, b.id));
    }

    tweets.sort(tweetCmp);
    return uniquify(tweets, function(a) { return a.id; });
}

var shownPopupIds = {};
var lastPopupIdTrim = 0;
var ONE_HOUR_MS = 60 * 1000 * 60;

function maybeTrimPopupIds(now) {

    if (now - lastPopupIdTrim < ONE_HOUR_MS)
        return;

    lastPopupIdTrim = now;

    var toDelete = [];
    $.each(shownPopupIds, function (id, time) {
        if (now - time > ONE_HOUR_MS)
            toDelete.push(id);
    });

    $.each(toDelete, function (i, id) { delete shownPopupIds[id]; });
}

function firePopup(tweets, opts) {
    if (opts === undefined)
        opts = {};

    opts.topic = 'twitter.newtweet';
    opts.tweets = tweets;

    D.rpc('fire', opts);
}

var _postfix_count = 0;
function showPopupForTweet(account, tweet) {
    _postfix_count++;
    return firePopup([notifyTweet(tweet)], {popupid_postfix: _postfix_count});
}

function showPopupsForTweets(account, tweets) {
    var feedsFilteringPopups = [];

    // collect feeds with popups: false
    $.each(account.feeds, function (name, feed) {
        if (feed.popups !== undefined && !feed.popups)
            feedsFilteringPopups.push(feed);
    });

    var notifyTweets = $.map(tweets, function (t) {
        // never show self tweets
        if (account.isSelfTweet(t))
            return null;

        // don't show repeats
        if (t.id in shownPopupIds)
            return null;

        if (t.read)
            return null;

        // exclude popups for feeds with popups: false
        for (var j = 0; j < feedsFilteringPopups.length; ++j) {
            if (feedsFilteringPopups[j].hasTweet(t, account))
                return null;
        }

        return notifyTweet(account, t);
    });

    if (!notifyTweets.length)
        return;

    notifyTweets = uniqueSortedTweets(notifyTweets, account.feeds.timeline);

    var now = new Date().getTime();
    $.each(notifyTweets, function (i, tweet) { shownPopupIds[tweet.id] = now; });
    maybeTrimPopupIds(now);

    return firePopup(notifyTweets);
}

TwitterTimelineSource.prototype.cache = function(tweets) {
    this.account.cacheTweets(tweets);
};

TwitterTimelineSource.prototype.update = function(updateNotification) {
    var self = this, account = this.account;

    if (this.updating) {
        console.warn('WARNING: ' + this + ' is already updating');
        this.updating.error(self);
    }

    this.updating = updateNotification;

    this.loadNewer(function (tweets, info) {
        if (info) {
            console.warn('url request got ' + tweets.length + ' tweets: ' + info.url);
        }
        var extraUpdate = (self.feed.extraUpdate || function(t, d) { d(t); });
        extraUpdate.call(self, tweets, function(tweets) {
            self.cache(tweets);
            account.newTweets(tweets, self);
            if (self.onUpdate)
                guard(function() { self.onUpdate(tweets); });
            if (updateNotification)
                updateNotification.success(self, tweets);
        });
        self.updating = undefined;
    }, function (error) {
        console.error('error updating source: ' + error.message + ' ' + error);
        self.updating = undefined;

        if (updateNotification)
            updateNotification.error(self, error);
    });
};

TwitterTimelineSource.prototype.didUpdate = function(status) {
    this.lastUpdateTime = new Date().getTime();
    this.lastUpdateStatus = status;
};

TwitterTimelineSource.prototype.needsUpdate = function(now) {
    if (!this.feed.autoUpdates ||
        !this.updateFrequency()) // updateFrequency may be 0 (never update this feed)
        return false;

    return now - this.lastUpdateTime >= this.updateFrequency();
};

TwitterTimelineSource.prototype.loadNewer = function(success, error, opts) {
    var self = this, account = this.account, url = this.url;

    function ajaxError(xhr, textStatus, errorThrown) {
        self.didUpdate('error');

        /*
        * search.twitter.com servers can sometimes return 403s if they don't like the since_id you're sending. see
        * http://groups.google.com/group/twitter-development-talk/browse_thread/thread/ed72429eef055cb3/23cf597ef030ca62?lnk=gst&q=search+403#23cf597ef030ca62
        *
        * if we get a 403 from search.twitter.com, try clearing maxId and trying again.
        */
        if (!self._didSearchHack && xhr.status === 403) {
            var searchUrl = 'http://search.twitter.com/search.json';
            if (url.substr(0, searchUrl.length) === searchUrl) {
                self.maxId = '0';
                self._didSearchHack = true;
                console.warn('clearing max id and restarting search');
                return self.loadNewer(success, error, opts);
            }
        }

        console.log('error for url: ' + url);
        console.log(' xhr.status: ' + xhr.status);
        console.log(' xhr.statusText: ' + xhr.statusText);
        if (errorThrown)
            console.log("error exception: " + errorThrown.message);
        if (textStatus)
            console.log("error with status: " + textStatus);

        if (error)
            error(xhr, textStatus, errorThrown);
    }

    var oldMaxId = self.maxId;
    console.info('requesting tweets, maxId is ' + oldMaxId + ': ' + url);

    function _success(data) {
        self.didUpdate('success');
        success(data, {url: url});
    }

    this.request = account.urlRequest(url, function(data, status) {
        //for (var i = 0; i < data.length; ++i)
            //if (compareIds(data[i].id_str, oldMaxId) < 0)
                //console.warn('OLDER ID: ' + data[i].id_str + ' older than old max ' + oldMaxId);
        return self.ajaxSuccess(data, status, _success, error, data.since_id);
    }, ajaxError, {data: this.makeData()});
};

TwitterTimelineSource.prototype.makeData = function() {
    var args = shallowCopy(this.data);
    args.count = this.count;
    if (this.limitById && compareIds(this.maxId, '0') > 0)
        args.since_id = this.maxId;

    return args;
};

TwitterTimelineSource.prototype.updateMinMax = function(id) {
    if (compareIds(id, this.maxId) > 0)
        this.maxId = id;
};

function TwitterTimelineDirectSource(account) {
    TwitterTimelineSource.call(this, account, account.apiRoot + 'direct_messages.json');
}

TwitterTimelineDirectSource.inheritsFrom(TwitterTimelineSource, {
    cache: function(directs) {
        this.account.cacheDirects(directs);
    },

    ajaxSuccess: function(data, status, success, error) {
        var self = this;
        var newDirects = [];
        data.reverse();

        var markRead = self.shouldMarkIncomingAsRead();
        function onData(data) {
            $.each(data, function (i, item) {
                var direct = self.account.makeDirectFromNetwork(item, markRead);
                self.updateMinMax(direct.id);
                newDirects.push(direct);
            });
        }

        onData(data);

        try {

            // 2nd, load send directs. this is a hack and needs to be abstracted into the idea of feeds having multiple sources.
            var _interim_success = function(data, status) {
                try {
                    onData(data);
                    console.log("loaded " + data.length + " directs from the network");
                    newDirects.sort(tweetsByTime);

                    if (success)
                        guard(function() { success(newDirects); });
                } catch (err) {
                    if (error) {
                        printException(err);
                        error(err);
                    } else throw err;
                }
            };

            var url2 = self.account.apiRoot + 'direct_messages/sent.json';
            var data = {};
            if (this.maxId && this.maxId !== '0')
                data.since_id = this.maxId;
            this.request = self.account.urlRequest(url2, _interim_success, error, {data: data});

        } catch (err) {
            if (error) {
                printException(err);
                error(err);
            } else throw err;
        }
    }
});

function TwitterTimelineSearchSource(account, searchQuery) {
    this.searchQuery = searchQuery;
    TwitterTimelineSource.call(this, account, account.searchApiRoot + 'search.json');
}

var searchTweetAttributes = ['id', 'text', 'from_user', 'source', 'profile_image_url', 'created_at'];


TwitterTimelineSearchSource.prototype = new TwitterTimelineSource();

TwitterTimelineSearchSource.prototype.updateFrequency = function() {
    // all searches get their update frequency from the account
    return this.account.searchUpdateFrequency;
}

TwitterTimelineSearchSource.prototype.makeData = function() {
    var args = shallowCopy(this.data);
    args.rpp = Math.min(100, this.count);
    args.q = this.searchQuery;
    if (compareIds(this.maxId, '0') > 0)
        args.since_id = this.maxId;

    return args;
};

TwitterTimelineSearchSource.prototype.ajaxSuccess = function(_data, status, success, error) {
    var self = this, data = _data.results, tweets = [];
    var account = self.account;

    data.reverse();
    //console.log('TwitterTimelineSearchSource.ajaxSuccess ' + data.length + ' results');

    window.db.transaction(function (tx) {
        function recurseBuild(i) {
            if (i === data.length) {
                //console.log('search retreived ' + i + ' tweets, calling success');
                if (success) success(tweets);
                return;
            }

            // TODO: use account.makeTweet here

            var searchTweet = data[i];
            useStringIdentifiers(searchTweet, ['id', 'in_reply_to_status_id']);
            var tweet = {truncated: null,
                         in_reply_to: null,
                         favorited: null,
                         in_reply_to_status_id: null,
                         in_reply_to_user_id: null,
                         in_reply_to_screen_name: null,

                         read: 0,
                         mention: account.isMention(searchTweet),
                         search: self.searchQuery};

            var username = searchTweet.from_user;
            var userId = null;

            executeSql(tx, 'SELECT * FROM Users WHERE Users.screen_name == ?', [username], function (tx, result) {
                if (result.rows.length) {
                    // if we already know about the user, use its real id.
                    var row = result.rows.item(0);
                    userId = row.id;
                    if (!account.users[userId])
                        account.users[row.user] = account.sql.users.fromJSON(row);
                }

                $.each(searchTweetAttributes, function (i, attr) { tweet[attr] = searchTweet[attr]; });
                tweet.user = userId;
                if (userId === null)
                    tweet.from_user = username;

                self.updateMinMax(tweet.id);
                account.tweetIn(tweet);
                tweets.push(tweet);

                return recurseBuild(i + 1);
            }, function (tx, errorObj) {
                console.error('error retrieving user w/ screen_name ' + username);
                if (error)
                    error(errorObj);
            });
        }

        recurseBuild(0);
    });
};

function TwitterHTTPClient(account) {
    this.account = account;
}

TwitterHTTPClient.prototype = {
    didFirstUpdate: false,

    didReceiveFollowing: function(following_json) {
        D.notify('following', {following: following_json});
    },

    didReceiveTrends: function(trends) {
        D.notify('trends', {trends: trends});
    },

    serverMessage: function(url, opts) {
        D.ajax({url: urlQuery('digsby://' + url, opts),
                type: 'JSON'});
    },

    onReply: function(tweet) {
        this.serverMessage('reply',
            {id: tweet.id,
             screen_name: tweetScreenName(this.account, tweet),
             text: tweet.text});
    },

    onRetweet: function(tweet) {
        this.serverMessage('retweet',
            {id: tweet.id,
             screen_name: tweetScreenName(this.account, tweet),
             text: tweet.text});
    },

    onDirect: function(tweet) {
        this.serverMessage('direct',
            {screen_name: tweetScreenName(this.account, tweet)});
    },

    onUnread: function(info)  {
        D.notify('unread', info);
    },

    selfTweet: function(tweet) {
        D.notify('selfTweet', {tweet: tweet});
    },

    feedsUpdated: function(feeds) {
        D.notify('feeds', feeds);
    },

    viewChanged: function(feedName) {
        D.notify('viewChanged', {feedName: feedName});
    },

    stateChanged: function(state) {
        D.notify('state', {state: state});
    },

    didReceiveUpdates: function() {
        if (this.didFirstUpdate)
            return;

        this.didFirstUpdate = true;
        this.account.changeState('online');
    },

    didReceiveWholeUpdate: function() {
        D.notify('received_whole_update');
    },

    connectionFailed: function() {
        if (this.didFirstUpdate)
            // connection problems after first update are ignored.
            return;

        this.account.changeState('connfail');
    },

    statusUpdated: function() {
        D.notify('hook', 'digsby.twitter.status_updated');
    },

    directSent: function() {
        D.notify('hook', 'digsby.twitter.direct_sent');
    },

    editFeed: function(feed) { D.notify('edit_feed', feed); },

    recentTimeline: function(tweets) {
        var acct = this.account;
        D.notify('recentTimeline', {
            tweets: $.map(tweets, function(t) { return notifyTweet(acct, t); })
        });
    }
};

var returnFalse = function() { return false; };

var tweetActions = {

    container: function(elem) { return $(elem).parents('.container')[0]; },

    favorite: function(elem) {
        var node = this.container(elem);
        var skin = account.timeline.skin;
        skin.setFavorite(node, 'pending');

        var tweet = account.timeline.nodeToElem(node);
        var originalFavorite = tweet.favorited;
        account.favorite(tweet, function (tweet) {
            skin.setFavorite(node, tweet.favorited);
        }, function (error) {
            console.log('error setting favorite');
            skin.setFavorite(node, originalFavorite);
        });
    },

    trash: function (elem) {
        var self = this;
        guard(function() {
        var node = self.container(elem);
        var tweet = account.timeline.nodeToElem(node);
        var skin = account.timeline.skin;
        var opts = {
            id: tweet.id,
            success: function (tweet) {
                // remove it visually
                node.parentNode.removeChild(node); // TODO: animate this
            },
            error: function(err) {
                printException(err);
                console.log('error deleting tweet');
                skin.setDelete(node);
            },
        };

        skin.setDelete(node, 'pending');
        if (tweet.sender_id)
            account.deleteDirect(opts);
        else
            account.deleteTweet(opts);
        });
    },

    action: function(action, elem) {
        account.notifyClients(action, account.timeline.nodeToElem(this.container(elem)));
    },

    reply: function(elem) { this.action('onReply', elem); },
    retweet: function(elem) { this.action('onRetweet', elem); },
    direct: function(elem) { this.action('onDirect', elem); },

    popupInReplyTo: function(id) {
        id = this.tweets[id].in_reply_to_status_id;
        if (!id) return;
        account.getTweet(id, function (tweet) {
            showPopupForTweet(tweet);
        });
    },

    inReplyTo: function(a) {
        var self = this;

        guard(function() {
            var timeline = account.timeline;
            var container = self.container(a);
            var tweet = timeline.nodeToElem(container);
            var id = tweet.in_reply_to_status_id;

            // if the CSS transformations here change, please also modify
            // feedSwitch in timeline2.js
            a.style.display = 'none';

            account.getTweet(id, function(tweet) {
                container.className += ' reply';
                timeline.insertAsParent(tweet, container);
                //spinner.parentNode.removeChild(spinner);
            }, function (error) {
                console.log('error retreiving reply tweet');
                printException(error);
            });

        });
    },

    openUser: function(a) {
        if (!settings.user_feeds)
            return true;

        guard(function() {
            var screen_name = a.innerHTML;
            console.log('openUser ' + screen_name);
            var feedDesc = {type: 'user', screen_name: screen_name};
            account.addFeed(feedDesc, true);
        });

        return false;
    },
};

function tweetToString() { return '<Tweet ' + this.id + '>'; }
function directToString() { return '<Direct ' + this.id + '>'; }

/**
 * twitter error responses come with nicely formatted error messages in
 * a JSON object's "error" key. this function returns an AJAX error handler
 * that passes that error message to the given function.
 */
function extractJSONError(errorMessage, errorFunc) {
    function error(xhr, textStatus, errorThrown) {
        console.error('xhr.repsonseText: ' + xhr.responseText);

        try {
            var err = JSON.parse(xhr.responseText).error;
            if (err) errorMessage += ': ' + err;
        } catch (err) {}

        console.error(errorMessage);
        errorFunc(errorMessage);
    }
    return error;
}

function transformRetweet(tweet) {
    var rt = tweet.retweeted_status;
    if (rt && rt.user && rt.user.screen_name)
        tweet.text = 'RT @' + rt.user.screen_name + ': ' + rt.text;

    return tweet;
}

function useOrCreateTransaction(tx, query, values, success, error) {
    function execQuery(tx) { executeSql(tx, query, values, success, error); }
    if (tx) execQuery(tx);
    else db.transaction(execQuery);
}

var didCacheTimestamp = false;

// called with the Twitter API server's current time
function receivedCorrectTimestamp(date, cache) {
    if (cache || !didCacheTimestamp) {
        OAuth.correctTimestamp(Math.floor(date.getTime() / 1000));
        cacheDiffMs(new Date().getTime() - date.getTime(), true);
    }
}

// caches the difference between our time and Twitter server time
lastCachedToDisk = null;

function cacheDiffMs(diffMs, cache) {
    diffMs = parseInt(diffMs, 10);

    // don't recache to disk if unnecessary.
    if (!cache && lastCachedToDisk !== null && Math.abs(lastCachedToDisk - diffMs) < 1000*60*2)
        return;

    console.log('cacheDiffMs(' + diffMs + ')');

    window.db.transaction(function(tx) {
        executeSql(tx, 'insert or replace into info_keyed values (?, ?)', ['__servertimediff__', diffMs], function() {
            didCacheTimestamp = true;
            lastCachedToDisk = diffMs;
        },
        function(e) {
            console.warn('cacheDiffMs DATABASE ERROR: ' + e);
        });
    }, errorFunc('error caching server time diff'));
}

function loadServerTime(done) {
    window.db.transaction(function(tx) {
        function success(tx, result) {
            if (result.rows.length) {
                var diffMs = result.rows.item(0).value;
                if (diffMs) {
                    diffMs = parseInt(diffMs, 10);
                    if (diffMs) {
                        var d = new Date(new Date().getTime() - diffMs);
                        receivedCorrectTimestamp(d);
                    }
                }
            } else
                console.warn('**** no server time cached');
            done();
        }
        executeSql(tx, "select value from info_keyed where key == ?", ['__servertimediff__'], success, done);
    });
}

