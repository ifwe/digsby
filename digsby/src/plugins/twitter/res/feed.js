
var CONTAINER_TAG = 'div';
var CONTAINER_ID = 'Chat';

function Timeline(container, skin) {
    var self = this;

    this.container = container;
    this.skin = skin;

    $(window).keypress(function(e) { guard(function () {
        var key = String.fromCharCode(e.which);
        var delta;

        if (key.toLowerCase() === "j")
            delta = 1;
        else if (key.toLowerCase() === "k")
            delta = -1;
        else if (key === ' ')
            delta = e.shiftKey ? -1 : 1;
        else if (key === 'p') // show timeline tweets in a popup
            window.opener.account.showTimelinePopup();

        if (delta)
            self.scrollItems(delta);
    }); });

    this.feedView = new FeedView(container,
        function(e) { return self.elemToNode(e); },
        function(e) { return e.id; },
        function(n) { return n.created_at_ms; },
        function(e) { return e.created_at_ms; });
}

// called manually by TwitterFrame.OnActivate
// TODO: make wxWebKit document.onblur and onfocus work correctly and use
// those instead.
function onFrameActivate(active) {
    guard(function() { 
        window.focused = active;
        window.timeline.setActive(active);
    });
}

Timeline.prototype = {
    toString: function() {
        var count = 0;
        for (var key in this.dataMap) ++count;
        return '[Timeline with ' + count + ' items]';
    },

    // twitter specific stuff
    elemKey: function(e) {
        var ms = e.created_at_ms;
        if (ms === undefined)
            console.error('missing created_at_ms: ' + e);
        return ms;
    },

    elemToNode: function(e) {
        var id = e.id;
        var node = document.getElementById(e.id);
        if (node) return node;

        var screen_name = tweetScreenName(this.account, e);

        var username;
        if (get(settings, 'show_real_names', false))
            username = tweetUserName(this.account, e);
        else
            username = screen_name;


        var classnames = 'timeline';
        var visual_classnames = '';

        if (e.sender_id)
            classnames = 'direct';
        else if (this.account.isSelfTweet(e))
            classnames = 'sent';
        else if (e.mention)
            classnames = 'mention';
        else if (e.search)
            classnames = 'search';

        if (e.read && !this.displayAllAsUnread)
            visual_classnames += ' context';

        var time;
        if (e.created_at)
            time = prettyDate(e.created_at);

        //this.dataMap[id] = e;

        username = '<a onclick="javascript:return tweetActions.openUser(this);" href="http://twitter.com/' + screen_name + '">' + username + '</a>';

        var timeToolTip = longDateFormat(new Date(e.created_at));

        var directTarget;
        if (e.recipient_id)
            directTarget = ' to ' + directTargetScreenName(this.account, e);

        node = this.skin.createItem(this.container.ownerDocument,
            {id: id,
             type: classnames,
             sender: username,
             message: twitterLinkify(e.text),
             classNames: classnames + visual_classnames,
             time: time,
             timeToolTip: timeToolTip,
             reply: e.in_reply_to_status_id,
             directTarget: directTarget,
             source: e.source,
             lazy_image: tweetUserImage(this.account, e),
             favorited: e.favorited}
        );

        node.created_at_ms = e.created_at_ms;

        return node;
    },

    nodeToElem: function(n) {
        var id = n.getAttribute('id');
        var elem = this.dataMap[id];
        assert(elem !== undefined, 'could not find tweet for id ' + id);
        return elem;
    },

    insertAsParent: function(elem, node) {
        var self = this;
        var newNode = this.elemToNode(elem);
        node.appendChild(this.skin.makeReplyArrow());
        this.skin.setHidden(newNode, true);

        this.maintainNodePosition(node, function() {
            self.container.insertBefore(newNode, node);
            self.skin.setHidden(newNode, false);
        });

        this.skin.loadAllLazy(newNode);
    },

    maintainNodePosition: function (node, func) {
        this.pinnedItem = node;
        this.pinnedItemOffset = node.offsetTop;
        this.pinToBottom = false;

        guard(func);

        this.restoreItemPosition();
    },

    /**
     * called when the webpage is activated or deactivated
     */
    setActive: function(active) {
        var self = this;
        if (!active && settings.frame_focus_unread && !this.displayAllAsUnread) {
            // mark all read elements as read visually when the top level frame
            // is deactivated.
            $.each(this.container.childNodes, function (i, elem) {
                var id = elem.getAttribute('id');
                var item = self.dataMap[id];
                if (item && item.read && !self.skin.isMarkedAsRead(elem))
                    self.skin.markAsRead(elem, true);
            });
        }
    },

    onWindowResized: function() {
        this.restoreItemPosition();
    },

    restoreItemPosition: function() {
        if (this.pinnedItem !== undefined) {
            // during window resizing, maintains the vertical position of the first
            // visible element in container 
            //
            // TODO: figure out why scrollBy from within window.onresize
            // doesn't work in chrome/safari...
            var y;
            if (settings.autoscroll_when_at_bottom && this.pinToBottom)
                y = document.height;
            else
                y = this.pinnedItem.offsetTop - this.pinnedItemOffset;

            //console.warn('*** restoreItemPosition: delta ' + y);
            window.scrollBy(0, y);

            // hack to fix scrolling to almost bottom
            if (this.nearBottom())
                window.scrollTo(0, document.height);

            this.onWindowScrolled();
        }
    },

    loadImage: function(item) {
        if (this.skin.isEmptyImage(item))
            this.skin.loadAllLazy(item);
    },

    onStoppedScrolling: function() {
        this.stopScrollingTimer = undefined;

        if (this.topItem && this.bottomItem) {
            var item = this.topItem;
            while (item != this.bottomItem) {
                this.loadImage(item);
                item = item.nextSibling;
            }
            this.loadImage(item);
            
            item = item.nextSibling;
            this.loadImage(item);
        }
    },

    onWindowScrolled: function() {
        this.saveItemPosition();
    },

    saveItemPosition: function(markAsRead) {
        if (markAsRead === undefined)
            markAsRead = true;

        var self = this;
        var container = this.container;
        var children = container.childNodes;
        var containerOffset = container.offsetTop;
        var length = children.length;

        var pageY = window.pageYOffset;
        var pageBottom = pageY + window.innerHeight;

        // reset the scrolling timer
        if (this.stopScrollingTimer)
            clearTimeout(this.stopScrollingTimer);
        this.stopScrollingTimer = setTimeout(function() { self.onStoppedScrolling(); }, 300);
        
        // TODO: does zooming make these calculations inaccurate?
        this.topItem = undefined;
        this.bottomItem = undefined;

        var markElemAsRead;
        if (markAsRead && !this._pauseMarkAsRead)
            markElemAsRead = function (elem) {
                var id = elem.getAttribute('id');
                if (id) {
                    var item = self.dataMap[id];
                    self.account.markAsRead(item);
                    if (!self.displayAllAsUnread && !settings.frame_focus_unread)
                        self.skin.markAsRead(elem, true);
                }
            };
        else
            markElemAsRead = function(elem) {};

        this.pinToBottom = pageBottom >= document.height;

        var i, elem, offset;

        if (pageY > document.height/2) {
            // start from the bottom
            for (i = length-1; i >= 0; --i) {
                elem = children[i];
                offset = elem.offsetTop;
                if (this.bottomItem === undefined && offset + containerOffset + elem.offsetHeight < pageBottom) 
                    this.bottomItem = elem;

                if (this.bottomItem !== undefined) 
                    markElemAsRead(elem);

                if (offset + containerOffset < pageY) {
                    this.topItem = elem;
                    var item = i < children.length-1 ? children[i+1] : children[i];
                    this.pinnedItem = item;
                    this.pinnedItemOffset = item.offsetTop;
                    break;
                }
            }
        } else {
            // start from the top
            var foundPinned = false;
            for (i = 0; i < length; ++i) {
                elem = children[i];
                offset = elem.offsetTop;
                if (!foundPinned && offset + containerOffset >= pageY) {
                    foundPinned = true;
                    this.pinnedItem = elem;
                    this.pinnedItemOffset = offset;
                    this.topItem = i > 0 ? children[i-1] : children[i];
                    markElemAsRead(this.topItem);
                }

                var shouldBreak = false;
                if (i === length - 1)
                    this.bottomItem = elem;
                else if (offset + containerOffset + elem.offsetHeight >= pageBottom) {
                    var visualBottom = i > 0 ? children[i-1] : children[i];
                    this.bottomItem = children[i];
                    markElemAsRead(visualBottom);
                    shouldBreak = true;
                }

                if (shouldBreak) break;
                else if (foundPinned) markElemAsRead(elem);
            }
        }
    },

    atBottom: function() {
        return document.body.scrollTop >= 
            document.body.offsetHeight - window.innerHeight;
    },

    nearBottom: function(fuzz) {
        if (fuzz === undefined) fuzz = 12;
        var val = Math.abs(document.body.scrollTop - 
            (document.body.offsetHeight - window.innerHeight));
        return val < fuzz;
    },

    scrollToNew: function() {
        console.warn('scrollToNew');
        //printStackTrace();

        var self = this;
        var y = document.height;
        var found = false;

        $.each(this.container.childNodes, function (i, node) {
            var id = node.getAttribute('id');
            var elem = self.dataMap[id];
            if (elem && !elem.read) {
                found = true;
                y = node.offsetTop - 30;
                return false;
            }
        });

        document.body.offsetHeight; // force a layout
        // console.warn('*** scrollToNew: ' + y);
        if (!found) {
            window.scrollTo(window.pageOffsetX, y);
            this.onWindowScrolled();
        } else {
            window.scrollTo(window.pageOffsetX, y - window.innerHeight);

            var initialDelay = 0;
            var timeToScroll = 200;
            var easeEffect   = undefined;//'easeOutExpo';
            
            var animateFunc = function() {
                $('body').animate({scrollTop: y}, timeToScroll, easeEffect);
            };

            if (initialDelay) setTimeout(animateFunc, initialDelay);
            else animateFunc();
        }
    },

    viewChanged: function(feed) {
        var self = this;
        if (typeof feed === 'string')
            feed = this.account.feeds[feed];

        if (!feed || this.feed === feed)
            return;

        if (this.feed !== undefined)
            this.feed.removeFeedListener(this);
        this.feed = feed;
        this.feed.addFeedListener(this);

        console.log('viewChanged: ' + feed);

        this.displayAllAsUnread = feed.displayAllAsUnread;
        
        var footer;
        console.log('viewChanged - feed.type: ' + feed.type);
        if (feed.query) {
            if (!feed.save) {
                var save = function() {
                    self.account.notifyClients('editFeed', feed.serialize()); 
                }, hide = function() {
                    self.skin.setFooter();
                    self.scrollToBottom();
                };

                feed.footer = [ [save, 'save this search for later'],
                                     [hide, 'hide'] ];
            } else {
                feed.footer = undefined;
            }
        }

        this.sync();

        if (feed.shouldUpdateOnView()) {
            console.log('updating lazy source now: ' + feed.source);

            var onDone = function() { self.finish(true, {scrollToBottom: feed.scrollToBottom}); };
            var obj = {success: onDone, error: onDone};
            feed.source.update(obj);
        }
    },

    sync: function(footer) {
        var items = this.feed.items;
        this.feedView.sync(items);
        this.skin.setFooter(items.length ? this.feed.footer : undefined);
    },

    finish: function (scrollToNew, opts) {
        if (scrollToNew === undefined)
            scrollToNew = true;
        if (opts === undefined)
            opts = {};

        this.pauseMarkAsRead(true);

        console.warn('in finish');
        console.warn('  scrollToNew is ' + scrollToNew);
        console.warn('  opts are ' + JSON.stringify(opts));
        console.warn('  window.focused is ' + window.focused);

        if (!this.toDelete) this.toDelete = [];
        if (!this.toInsert) {
            this.toInsert = [];
            this.toInsertMap = {};
        }
        var self = this;

        if (!opts.scrollToBottom && !scrollToNew)
            this.saveItemPosition();

        this.sync();

        if (this.delayedFooter) {
            this.skin.setFooter(this.delayedFooter);
            this.delayedFooter = undefined;
        }

        this.pauseMarkAsRead(false, function() {
            if (opts.scrollToBottom)
                self.scrollToBottom();
            else if (scrollToNew)
                self.scrollToNew();
            else
                self.restoreItemPosition();
        });
    },

    pauseMarkAsRead: function(pause, func) {
        console.warn('pauseMarkAsRead: ' + pause);
        if (pause)
            this._pauseMarkAsRead = pause;
        else {
            func();
            this._pauseMarkAsRead = pause;
            this.saveItemPosition();
        }
    },

    scrollToBottom: function() {
        document.body.offsetHeight; // force a layout
        console.warn('scrollToBottom: ' + document.height);
        window.scrollTo(window.pageOffsetX, document.height);
    },

    scrollToBottomIfAtBottom: function(func) {
        console.warn('scrollToBottomIfAtBottom');
        var atBottom = this.atBottom();
        func();

        if (atBottom)
            this.scrollToBottom();
        else
            this.restoreItemPosition();
    },

    scrollItems: function(i) {
        var node = this.pinnedItem;
        if (i > 0) {
            while (node && i--) node = node.nextSibling;
        } else if (i < 0) {
            while (node && i++) node = node.previousSibling;
        }

        this.scrollToItem(node);
    },

    scrollToItem: function(node) {
        // console.warn('*** scrollToItem: ' + node.offsetTop);
        window.scrollTo(window.pageOffsetX, node.offsetTop);
    },

    registerEventHandlers: function(window) {
        var self = this;

        $(window).resize(function() {
            guard(function() { self.onWindowResized(); });
        });

        $(window).scroll(function() {
            guard(function() { self.onWindowScrolled(); });
        });
    },

    onClosing: function() {
        this.account.timelineClosing();
        this.account.timeline = undefined;
        this.feed.removeFeedListener(this);
    },

    updateTimestamps: function () {
        var self = this;
        $(".timeDescription").each(function (i, e) {
            var tweet = self.nodeToElem($(e).parents(".container")[0]);
            if (tweet) {
                var time = prettyDate(tweet.created_at);
                var timeToolTip = longDateFormat(new Date(tweet.created_at));
                if (e.innerHTML !== time)
                    e.innerHTML = time;
            }
        });
    }
};

CONTAINER_TAG = 'div';
CONTAINER_ID = 'Chat';

function feed_onunload() {
    window.timeline.onClosing();
    window.opener.onChildWindowUnloaded(window);
}

function feed_onload() {
    guard(function() {
    console.log('feed_onload');
    var skin = new SmoothOperator();

    var container = document.createElement(CONTAINER_TAG);
    container.setAttribute('id', CONTAINER_ID);
    document.body.appendChild(container);

    window.timeline = new Timeline(container, skin);
    window.timeline.window = window;
    window.timeline.registerEventHandlers(window);
    window.opener.onChildWindowLoaded(window);

    // init history stuff
    var pageload = function(hash) {
        guard(function() {
            window.opener.account.changeView(hash);
        });
    };

    $.historyInit(pageload, "feed.html");
    });
}

function historyOnClick() {
    $.historyLoad(this.href.replace(/^.*#/, ''));
    return false;
}

(function() {
    function pad(n) { return n.toString().length == 1 ? '0' + n : n; }

    function dateFormat(d) {
        var a, h = d.getHours(), m = d.getMinutes();
        if (h > 12) {
            h -= 12;
            a = ' PM';
        } else {
            if (h === 0) h = 12;
            a = ' AM';
        }

        return pad(h) + ':' + pad(m) + a;
    }
    
    window.dateFormat = dateFormat;
})();

