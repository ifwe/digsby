var SmoothOperator = function(doc) {
    // prepare a template node for "in reply to..." links
    this.inReplyTo = document.createElement('span');
    this.inReplyTo.className = 'in_reply_to';
    this.inReplyTo.innerHTML = ' <a href="" onclick="javascript:tweetActions.inReplyTo(this); return false;">in reply to...</a>';

    this._directTargetNode = document.createElement('span');
    this._directTargetNode.className = 'directTarget';
};

function onProfileImageError(evt) {
    this.onerror = null;
    this.setAttribute('src', SmoothOperator.prototype.emptyImageUrl);
}

var deleteSrc = 'img/delete.gif';

var controls = {
    reply:    '<a href="" title="Reply" onclick="tweetActions.reply(this); return false;"><img src="img/reply.png" width="16" height="16" /></a>',
    retweet:  '<a href="" title="Retweet" onclick="tweetActions.retweet(this); return false;"><img src="img/retweet.gif" width="16" height="16" /></a>',
    direct:   '<a href="" title="Direct" onclick="tweetActions.direct(this); return false;"><img src="img/direct.gif" width="16" height="16" /></a>',
    favorite: '<a href="" title="Favorite" onclick="tweetActions.favorite(this); return false;"><img class="favoriteButton" src="img/star_off.gif" width="18" height="16" /></a>',
    trash:    '<a href="" title="Delete" onclick="tweetActions.trash(this); return false;"><img class="deleteButton" src="' + deleteSrc + '" width="16" height="16" /></a>'
};

with (controls) var controlTypeHTML = {
    timeline: reply + retweet + direct + favorite,
    mention:  reply + retweet + direct + favorite,
    sent:     trash + favorite,
    direct:   direct,
    search:   reply + retweet + favorite
};

SmoothOperator.prototype = {
    preload: function() {
        var images = ['top_left', 'top_center', 'top_right',
                      'middle_left', 'middle_right', 'bottom_left',
                      'bottom_right', 'bottom_center', 'middle_center'];
        arrayExtend(images, $.map(images, function (e) { return 'context_'+e; }));
        $.preload(images, {
            base: 'images/',
            ext: '.png'
        });
    },
    emptyImageUrl:  'img/twitter_no_icon.png',
    loadedLazy: {},
    controlTemplates: {},
    controlTemplate: function(doc, type) {
        if (type in this.controlTemplates)
            return this.controlTemplates[type];

        var node = doc.createElement('span');
        node.className = 'control';
        var html = controlTypeHTML[type];
        if (html)
            node.innerHTML = html;
        else
            console.log('ERROR: no controlTypeHTML for ' + type);
        this.controlTemplates[type] = node;
        return node;
    },

    directTargetNode: function(name) {
        var node = this._directTargetNode.cloneNode(true);
        node.innerHTML = name;
        return node;
    },

    /**
     * returns a template node from which we clone new ones
     */
    createTemplateItem: function(doc) {
        var node = doc.createElement('div');
        node.className = 'container';

        node.innerHTML =
            '<div class="top_left"></div>' +
            '<div class="top_center"></div>' +
            '<div class="top_right"></div>' +
            '<div class="middle_left"></div>' +
            '<div class="middle_right"></div>' +
            '<div class="bottom_left"></div>' +
            '<div class="bottom_center"></div>' +
            '<div class="bottom_right"></div>' +
            '<div class="middle_center"></div>' +
            '<div class="sender incoming">' +
                '<span class="senderstring">' +
                '</span>' +
            '</div>' +
            '<div class="time_initial">' +
                  /* twitter control buttons 
                  '<span class="control">' +
                    // stuff
                  '</span>' +
                  */
            '</div>' +
            '<div class="buddyicon">' +
                '<img class="feedImage" src="' + this.emptyImageUrl + '" />' +
            '</div>' +
            '<div class="message">' +
                '<p></p>' +
            '</div>';

        return node;
    },

    createItem: function(doc, attrs) {
        if (this.templateItem === undefined)
            this.templateItem = this.createTemplateItem(doc);
        
        var node = this.templateItem.cloneNode(true);
        var children = node.childNodes;

        if (attrs.classNames)
            node.className += ' ' + attrs.classNames;

        // id
        if (attrs.id)
            node.setAttribute('id', attrs.id);

        // sender
        var senderDiv = children[9];
        if (attrs.sender)
            senderDiv.firstChild.innerHTML = attrs.sender;

        if (attrs.reply)
            senderDiv.firstChild.appendChild(this.inReplyTo.cloneNode(true));
        else if (attrs.directTarget)
            senderDiv.firstChild.appendChild(this.directTargetNode(attrs.directTarget));

        // controls
        var timeNode = children[10];
        timeNode.appendChild(this.controlTemplate(doc, attrs.type).cloneNode(true));

        // favorite
        if (attrs.favorited)
            this.setFavorite(node, true);
        
        if (attrs.time) {
            var timeSpan = doc.createElement('span');
            timeSpan.className = 'timeDescription';
            timeSpan.innerHTML = attrs.time;
            if (attrs.timeToolTip)
                timeSpan.setAttribute('title', attrs.timeToolTip);

            timeNode.appendChild(timeSpan);
        }

        // Set "lazy_src" attribute on the <img> tag, unless we have already
        // lazily loaded the href before.
        var lazy_image = attrs.lazy_image;
        var imageNode = children[11].firstChild;
        if (lazy_image)
            imageNode.setAttribute(
                lazy_image in this.loadedLazy ? 'src' : 'lazy_src',
                lazy_image);
        imageNode.onerror = onProfileImageError;
        
        if (attrs.message) {
            var messagePara = children[12].firstChild;
            messagePara.innerHTML = attrs.message;
            if (0 && attrs.source) {
                var source = doc.createElement('span');
                source.className = 'source';
                source.innerHTML = ' from ' + attrs.source;
                messagePara.appendChild(source);
            }
        }

        return node;
    },

    getMessage: function(node) {
        return node.childNodes[12].firstChild.innerHTML;
    },

    // image manipulation
    getImage: function(node) { return node.childNodes[11].firstChild; },
    isEmptyImage: function(node) { return this.getImage(node).getAttribute('src') === this.emptyImageUrl; },

    loadAllLazy: function(node) {
        var image = this.getImage(node);
        if (image === undefined) return;

        var src = image.getAttribute('lazy_src');
        if (src === undefined) return;

        // loop over all images manually--jquery was slow
        var images = document.getElementsByClassName('feedImage');
        for (var i = images.length-1; i >= 0; --i) {
            var img = images[i];
            var lazy_src = img.getAttribute('lazy_src');
            if (lazy_src && lazy_src === src) {
                img.setAttribute('src', lazy_src);
                this.loadedLazy[lazy_src] = true;
                img.removeAttribute('lazy_src');
            }
        }
    },

    makeReplyArrow: function() {
        if (this.replyArrowTemplate === undefined) {
            var img = document.createElement('img');
            img.className = 'replyArrow';
            img.setAttribute('src', 'img/inreply.png');
            img.setAttribute('width', 16);
            img.setAttribute('height', 20);

            this.replyArrowTemplate = img;
        }
        return this.replyArrowTemplate.cloneNode(true);
    },

    /*
     * favorites
     */

    pendingSrc: 'img/pending.png',

    favoritedSrc: 'img/star_on.gif',
    notFavoritedSrc: 'img/star_off.gif',

    getFavoriteButton: function(node) {
        return node.childNodes[10].firstChild.getElementsByClassName('favoriteButton')[0];
    },

    getDeleteButton: function(node) {
        return node.childNodes[10].firstChild.getElementsByClassName('deleteButton')[0];
    },

    getFavorite: function(node) {
        var src = this.getFavoriteButton(node).src;
        if (src === this.pendingSrc)
            return 'pending';
        else if (src === this.favoritedSrc)
            return true;
        else
            return false;
    },

    setFavorite: function(node, state) {
        var src;
        if (state === 'pending') src = this.pendingSrc;
        else if (state)          src = this.favoritedSrc;
        else                     src = this.notFavoritedSrc;

        this.getFavoriteButton(node).src = src;
    },

    setDelete: function(node, state) {
        var src;
        if (state === 'pending') src = this.pendingSrc;
        else                     src = deleteSrc;
        this.getDeleteButton(node).src = src;
    },

    hiddenClassname: 'hiddenFeedItem',

    setHidden: function(node, hidden) {
        if (hidden)
            $(node).addClass(this.hiddenClassname);
        else
            $(node).removeClass(this.hiddenClassname);
    },

    visualReadClass: 'context',    

    isMarkedAsRead: function(node) { return $(node).hasClass(this.visualReadClass); },

    markAsRead: function(node, read) {
        node = $(node);
        if (read)
            node.addClass(this.visualReadClass);
        else
            node.removeClass(this.visualReadClass);
    },

    FOOTER_CLASS: 'statusFooter',

    clearFooter: function() {
        var nodes = document.getElementsByClassName(this.FOOTER_CLASS);
        while(nodes.length) {
            var node = nodes[0];
            node.parentNode.removeChild(node);
            nodes = document.getElementsByClassName(this.FOOTER_CLASS);
        }
    },

    setFooter: function(footer) {
        var self = this;
        this.clearFooter();
        if (!footer)
            return;

        function makeDiv() {
            div = document.createElement('div');
            div.className = 'status_container ' + self.FOOTER_CLASS;

            dodiv('status_message', 0);
            dodiv('status_time', 1);

            function dolink(onclick, text) {
                var link = document.createElement('a');
                link.setAttribute('href', '');
                link.innerHTML = text;
                link.onclick = function() {
                    guard(function() { onclick.call(this); });
                    return false;
                };
                return link;
            }

            function dodiv(classname, index) {
                var innerdiv = document.createElement('div');
                innerdiv.className = classname;
                var footerItem = footer[index];
                innerdiv.appendChild(dolink(footerItem[0], footerItem[1]));

                div.appendChild(innerdiv);
            }
            
            return div;
        }

        var container = document.getElementById(CONTAINER_ID);
        container.parentNode.insertBefore(makeDiv(), container.nextSibling);
        container.parentNode.insertBefore(makeDiv(), container);
    }
};

