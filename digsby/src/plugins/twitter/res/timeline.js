var _feedId = 0;
function nextFeedId() { return _feedId++; }

function FeedModel() {
    this.feedId = nextFeedId();
}

FeedModel.prototype = {
    has: function(item) {
        return false;
    }
};

function TwitterFeedModel(tweets) {
    this.tweets = tweets;
    this.listeners = [];

    FeedModel.call(this);
    this.filterUserIds = {};
    this.merges = {};

    this.all = {};
    this.items = [];
    this.unreadCount = 0;
}

TwitterFeedModel.inheritsFrom(FeedModel, {
    limit: 100,
    autoUpdates: true,

    // Returns true if the tweet is in this feed.
    hasTweet: function(item) {
        return item.id in this.all;
    },

    /**
     * called when changing to this view. should return true if it's time to
     * do a "manual" update.
     */
    shouldUpdateOnView: function () {
        if (!this.autoUpdates && this.source) {
            var now = new Date().getTime();
            return (now - this.source.lastUpdateTime) >= this.manualUpdateFrequency;
        }
        return false;
    },

    // frequency to allow updates when switching to views like favorites
    manualUpdateFrequency: 1000 * 60 * 5,

    addsToUnreadCount: function() { return true; },
    toString: function() {
        return '<' + this.constructor.name + ' (' + this.unreadCount + '/' + this.items.length + ' unread)>';
    },

    makeSource: function(account) {
        if (!this.sourceURL)
            return;

        var url = account.apiRoot + this.sourceURL;
        var source = new TwitterTimelineSource(account, url, this.sourceData);
        if (this.limitById !== undefined)
            source.limitById = this.limitById;
        this.source = source;
        source.feed = this;
        return source;
    },

    updateSourceNow: function() {
        if (!this.source) return;
        var self = this;
        var done = function() {
            callEach(self.listeners, 'finish', false);
        };
        var obj = {success: done, error: done};
        this.source.update(obj);
    },

    markedAsRead: function(item) {
        this.unreadCount -= 1;
        if (this.unreadCount < 0) {
            console.warn('WARNING: unreadCount went below 0');
            this.unreadCount = 0;
        }
    },

    add: function(item, search) {
        var isnew = !(item.id in this.all);
        if (isnew) {
            this.all[item.id] = item;

            if (search) {
                var key = function(t) { return t.created_at_ms; };
                var i = binarySearch(this.items, item, key);
                arrayExtend(this.items, [item], i);
            } else {
                this.items.push(item);
            }

            this.addItemListener(item);
            if (isnew && !item.read)
                this.unreadCount += 1;
        } else {
            var myitem = this.all[item.id];
            var wasread = myitem.read;
            for (var k in item)
                myitem[k] = item[k];
            myitem.read = wasread || item.read;
        }
        return isnew;
    },

    removeItem: function(item) {
        if (item.id in this.all) {
            this.removeItemListener(item);
            var found = false;
            this.items = $.grep(this.items, function (i) {
                found = true;
                return i.id !== item.id;
            });
            if (found) this.refreshUnreadCount();
        }
    },

    removeAllItems: function() {
        var self = this;
        $.each(this.items, function (i, item) {
            self.removeItemListener(item);
        });
        this.unreadCount = 0;
        this.items = [];
        this.all = {};
    },

    addSorted: function(items, source, notifyNow, opts) {
        var self = this;
        assert(items);
        var newItems = [];
        var maxCreatedAt = 0;
        var maxId = '0';

        if (verbose) console.log('addSorted(' + items.length + ' items) from ' + source);

        var search = true;//(items.length && this.items.length !== 0 && 
            //((items[0].created_at_ms < this.items[this.items.length-1].created_at_ms) ||
             //(items[items.length-1].created_at_ms > this.items[0].created_at_ms)));

        var account = opts.account;
        $.each(items, function (i, item) {
            if (self.has(item, account)) {
                var added = self.add(item, search);
                if (added) {
                    maxId = compareIds(item.id, maxId) > 0 ? item.id : maxId;
                    maxCreatedAt = item.created_at_ms > maxCreatedAt ? item.created_at_ms : maxCreatedAt;
                    newItems.push(item);
                }
            }
        });

        this.trim();

        if (0) {
        for (var i = 0; i < self.items.length-1; ++i) {
            var a = self.items[i];
            var b = self.items[i+1];
            assert(a.created_at_ms <= b.created_at_ms,
                   'created_at_ms wrong: ' +a+ ' (' +a.created_at_ms+ ') and ' +b+ ' (' +b.created_at_ms+ ')');
        }
        }

        if (notifyNow)
            callEach(this.listeners, 'finish', opts && opts.scroll);

        if (!opts.ignoreIds && self.source && (self.source === source || source === undefined))
            self.source.updateMinMax(maxId);
    },
    
    refreshUnreadCount: function () {
        var count = 0;
        var items = this.items;
        for (var i = items.length-1; i >= 0; --i) {
            if (!items[i].read)
                count++;
        }
        this.unreadCount = count;
    },

    trim: function() {
        var self = this;
        if (this.items.length > this.limit) {
            var numToDelete = this.items.length - this.limit;
            $.each(this.items, function (i, item) {
                if (i >= numToDelete)
                    return false;

                delete self.all[item.id];
                self.removeItemListener(item);
                if (!item.read)
                    self.unreadCount -= 1;
            });
            
            var deletedItems = self.items.slice(0, numToDelete);
            console.log(this + ' trimmed ' + deletedItems.length + ' items');
            self.items = self.items.slice(numToDelete);
        }
    },

    addItemListener: function (item) {
        if (!('feeds' in item)) item.feeds = {};
        item.feeds[this.feedId] = this;
    },

    removeItemListener: function (item) {
        if (item.feeds !== undefined)
            delete item.feeds[this.feedId];
    },

    addFeedListener: function (listener) { this.listeners.push(listener); },

    removeFeedListener: function (listener) {
        this.listeners = $.grep(this.listeners, function (item, i) {
            return listener !== item;
        });
    }
});

function TwitterTimelineFeedModel(tweets) {
    TwitterFeedModel.call(this, tweets);
}

TwitterTimelineFeedModel.inheritsFrom(TwitterFeedModel, {
    name: 'timeline',
    serialize: function() {
        return {
            count: this.unreadCount, 
            label: "Timeline", 
            name: 'timeline', 
            type: 'timeline'
        }; 
    },
    sourceURL: 'statuses/home_timeline.json',

    addMerge: function(name, mergeFunc) {
        this.merges[name] = mergeFunc;
    },

    removeMerge: function(name) {
        if (name in this.merges) {
            delete this.merges[name];
            return this.pruneItems();
        } else
            console.warn('removeMerge(' + name + ') called, but not in this.merges');

        return 0;
    },

    pruneItems: function() {
        var self = this;
        var oldCount = this.items.length;
        this.items = $.grep(this.items, function(i) { return self.has(i); });
        var delta = oldCount-this.items.length;
        console.log('pruneItems removed ' + delta);
        return delta;
    },

    addFilterIds: function(ids) {
        var filterIds = this.filterUserIds;
        $.extend(filterIds, set(ids));

        // filter out existing items
        this.items = $.grep(this.items, function (i) {
            return !(i.user in filterIds);
        });

        this.refreshUnreadCount();
    },

    feedAdded: function(account, feed) {
        if (feed.type === 'group') {
            if (feed.filter)
                this.addFilterIds(feed.ids);
        } else if (feed.type === 'search') {
            if (feed.merge) {
                var q = feed.query;
                this.addMerge(q, function tweetHasQuery(t) {
                    return t.search === q && !account.isMention(t);
                });
            }
        }
    },

    feedDeleted: function(feed, customFeeds) {
        var self = this;
        console.log('feedDeleted: ' + feed + ' ' + feed.type);
        if (feed.type === 'group') {
            if (feed.filter) {
                // clear the id map and re-add all the ids from remaining feeds
                this.filterUserIds = {};
                $.each(customFeeds, function (i, customFeed) {
                    if (customFeed.name !== feed.name && customFeed.filter)
                        self.addFilterIds(customFeed.userIds);
                });
            }
        } else if (feed.type === 'search') {
            if (feed.merge)
                return this.removeMerge(feed.query);
        } else
            console.warn('feedDeleted got unknown type: ' + feed.type);
    },

    // Returns true if the tweets should be added to this feed.
    has: function(item, account) {
        // filter out any tweets with ids in this.filterUserIds
        if (item.user in this.filterUserIds) return false;

        // include directs
        if (item.sender_id && account.selfUser) {
            if (isDirectInvite(account.selfUser.id, item, account.invite_message))
                return false; // leave out direct message invites

            return true;
        }

        // include all non search tweets
        if (!item.search)
            return true;
        else {
            // see if its a merged search
            var foundMerge = false;
            $.each(this.merges, function (name, merge) {
                if (merge(item)) {
                    foundMerge = true;
                    return false; // stop .each
                }
            });

            return foundMerge;
        }

        return true;
    }
});

function isDirectInvite(selfId, item, message) {
    return item.sender_id === selfId && item.text === message;
}

function TwitterMentionFeedModel(tweets) {
    TwitterFeedModel.call(this, tweets);
}

TwitterMentionFeedModel.inheritsFrom(TwitterFeedModel, {
    sourceURL: 'statuses/mentions.json',
    alwaysMentions: true,
    serialize: function() { return {count: this.unreadCount, label: "Mentions", name: 'mentions', type: 'mentions'}; },
    name: 'mentions',
    has: function(item) { return item.mention; }
});

function TwitterGroupFeedModel(tweets, feedOpts) {
    TwitterFeedModel.call(this, tweets);

    assert(feedOpts.name);
    assert(feedOpts.type === 'group');

    this.name = feedOpts.name;
    this.groupName = feedOpts.groupName;
    this.userIds = feedOpts.ids;
    this.filter = feedOpts.filter;
    this.popups = feedOpts.popups;
    this.noCount = feedOpts.noCount;

    // for quick lookup
    this.userIdsSet = set(this.userIds);
}

TwitterGroupFeedModel.inheritsFrom(TwitterFeedModel, {
    addsToUnreadCount: function() { return !this.noCount; },

    serialize: function() {
        return {
            count: this.unreadCount, 
            filter: this.filter,
            ids: this.userIds,
            label: this.groupName, 
            name: this.name,
            groupName: this.groupName,
            popups: this.popups,
            type: 'group',
            noCount: this.noCount
        };
    },

    updateOptions: function(info) {
        var changed = false;

        assert(info.ids);
        assert(info.groupName);

        this.groupName = info.groupName;

        if (this.filter != info.filter) {
            this.filter = info.filter;
            changed = true;
        }

        var oldSet = this.userIdsSet;
        this.userIdsSet = set(info.ids);
        if (!setsEqual(oldSet, this.userIdsSet)) {
            this.userIds = info.ids;
            changed = true;
        }


        this.popups = info.popups;

        return changed;
    },

    has: function(item) {
        return item.user in this.userIdsSet;
    }
});

function TwitterSearchFeedModel(tweets, feedOpts) {
    TwitterFeedModel.call(this, tweets);

    assert(feedOpts.type === 'search');

    this.name = feedOpts.name;
    this.query = feedOpts.query;
    this.merge = feedOpts.merge;
    this.popups = feedOpts.popups;
    this.title = feedOpts.title;
    this.save = feedOpts.save || false;
    this.noCount = feedOpts.noCount;

    this.sourceURL = 'http://search.twitter.com/search.json';
    this.sourceData = {q: this.query};
}

TwitterSearchFeedModel.inheritsFrom(TwitterFeedModel, {
    addsToUnreadCount: function() {
        // only contribute to unread count when saved
        return this.save && !this.noCount;
    },

    has: function(item) { return item.search === this.query; },

    serialize: function() {
        return {count: this.unreadCount, 
                label: this.title || this.query,
                name: this.name,
                title: this.title,
                type: 'search',
                query: this.query,
                merge: this.merge,
                popups: this.popups,
                save: this.save,
                noCount: this.noCount};
    },

    updateOptions: function(feed) {
        var self = this, changed = false;

        if (feed.merge !== this.merge) { 
            this.merge = feed.merge;
            changed = true;
        }

        if (feed.query !== this.query) {
            this.source.searchQuery = this.query = feed.query;
            changed = true;
            this.updateSourceNow();
        }

        console.warn('search updateOptions:\n' + JSON.stringify(feed));

        this.popups = feed.popups;
        this.title = feed.title;
        this.save = feed.save || false;

        return changed;
    },

    makeSource: function(account) {
        var source = new TwitterTimelineSearchSource(account, this.query);
        this.source = source;
        source.feed = this;
        return source;
    }
});

function TwitterDirectsModel(tweets, feedOpts) {
    TwitterFeedModel.call(this, tweets);
}

TwitterDirectsModel.inheritsFrom(TwitterFeedModel, {
    name: 'directs',
    serialize: function() {
        return {
            count: this.unreadCount,
            label: 'Directs',
            name: 'directs',
            type: 'directs'
        };
    },

    has: function (item, account) {
        return item.sender_id && !isDirectInvite(account.selfUser.id, item, account.invite_message);
    },

    makeSource: function(account) {
        var source = new TwitterTimelineDirectSource(account);
        this.source = source;
        source.feed = this;
        return source;
    }
});

/**
 * Collects tweets that are favorited.
 */
function TwitterFavoritesFeedModel(tweets) { TwitterFeedModel.call(this, tweets); }
TwitterFavoritesFeedModel.inheritsFrom(TwitterFeedModel, {
    has: function(item) { return item.favorited ? true : false; },
    name: 'favorites',
    sourceURL: 'favorites.json',
    limitById: false,
    autoUpdates: false,
    displayAllAsUnread: true,
    scrollToBottom: true,
    makeSource: function(account) {
        var self = this,
            source = TwitterFeedModel.prototype.makeSource.call(this, account);

        source.onUpdate = function (tweets) {
            // mark any tweets cached as favorite but not returned in the favorites feed update
            // as non-favorited.
            var ids = set($.map(tweets, function (t) { return t.id; }));
            var toUnfavorite = [];
            $.each(source.account.tweets, function (id, tweet) {
                if (tweet.favorited && !(id in ids)) {
                    toUnfavorite.push(id);
                    tweet.favorited = 0;
                }
            });

            if (toUnfavorite.length) {
                console.log('unfavoriting cached tweets: ' + toUnfavorite.join(', '));
                source.account.cacheFavorited(toUnfavorite, false);
                account.refreshFeedItems(self);
            }
        };

        return source;
    }
});

/**
 * Collects tweets that have a certain user id.
 *
 * TODO: just use the Group model above?
 */
function TwitterUserFeedModel(tweets, feedDesc) {
    if (!tweets)
        return;
    TwitterFeedModel.call(this, tweets);
    if (feedDesc.name)
        this.name = feedDesc.name;
    this.userScreenName = feedDesc.screen_name;
    assert(this.userScreenName);
    this.sourceURL = 'statuses/user_timeline.json';
    this.sourceData = {screen_name: this.userScreenName};
}

TwitterUserFeedModel.inheritsFrom(TwitterFeedModel, {
    has: function(item, account) {
        var user = account.users[item.user];
        return user && user.screen_name && user.screen_name.toLowerCase() === this.userScreenName.toLowerCase();
    },
    autoUpdates: false,
    scrollToBottom: true,
    displayAllAsUnread: true,
    addsToUnreadCount: function() { return false; },
    serialize: function() {
        return {
            name: this.name,
            screen_name: this.userScreenName,
            label: this.userScreenName,
            type: 'user'
        };
    }
});

function TwitterHistoryFeedModel(tweets, feedDesc) {
    console.warn('TwitterHistoryFeedModel');
    console.warn(' tweets: ' + tweets);
    console.warn(' feedDesc: ' + JSON.stringify(feedDesc));

    TwitterUserFeedModel.call(this, tweets, feedDesc);
}

TwitterHistoryFeedModel.inheritsFrom(TwitterUserFeedModel, {
    serialize: undefined,
    name: 'history'
});

/**
 * as a hack, the first time friends_timeline gets checked, if there are
 * no self tweets in it, we go get user_timeline as well, so that we know
 * your last self tweet for sure.
 */
function selfUpdate(tweets, done) {
    if (this._didExtraUpdate) return done(tweets);
    this._didExtraUpdate = true;
    var self = this, account = this.account;

    var found;
    $.each(tweets, function (i, tweet) {
        if (account.isSelfTweet(tweet)) {
            found = tweet;
            return false;
        }
    });

    if (found)
        return guard(function() { 
            account.possibleSelfTweets(tweets);
            done(tweets);
        });

    // TODO: actually use feeds.history here.
    var url = account.apiRoot + 'statuses/user_timeline.json';
    var maxId = account.feeds.history.source.maxId;
    if (maxId && maxId !== '0')
        url = urlQuery(url, {since_id: maxId});

    function error(_error) {
        console.error('error retrieving user_timeline');
        done(tweets);
    }

    function _success(data, status) {
        function _done(selfTweets) {
            console.log('extra update got ' + data.length + ' self tweets');
            arrayExtend(tweets, selfTweets);
            tweets.sort(tweetsByTime);
            account.possibleSelfTweets(tweets);
            done(tweets);
        }
        self.ajaxSuccess(data, status, _done, error);
    }

    account.urlRequest(url, _success, error);
}

function createFeed(allTweets, feedDesc) {
    var feedTypes = {timeline: TwitterTimelineFeedModel,
                     mentions: TwitterMentionFeedModel,
                     directs: TwitterDirectsModel,
                     group:  TwitterGroupFeedModel,
                     search: TwitterSearchFeedModel,
                     user: TwitterUserFeedModel};

    var feedType = feedTypes[feedDesc.type];
    var feed = new feedType(allTweets, feedDesc);

    if (feedDesc.type === 'timeline')
        feed.extraUpdate = selfUpdate;

    return feed;
}

function hasSearchQuery(q) {
    return function tweetHasQuery(t) { return t.search === q; };
}

