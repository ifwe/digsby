var commentFieldPaddingX;
var commentFieldPaddingY;

$(function(){
    var t = $("<textarea/>").css({'position':'fixed', 'right':'-500px', 'bottom':'-500px'}).appendTo(document.body);
    commentFieldPaddingX =  t.outerWidth() - t.width();
    commentFieldPaddingY =  t.outerHeight() - t.height();
    t.remove();
})

var changeView = function(name) {
    D.notify('infobox_hide');
    D.notify('change_view', name);
}
swapIn(function() { window.changeView = changeView; });
swapOut(function() { delete window.changeView; });

var TWITTER_INFOBOX_INPUT = true;

var transitionDefault = 200;

var fxAttrs = [
    // height animations
    [ "height", "marginTop", "marginBottom", "paddingTop", "paddingBottom" ],
    // width animations
    [ "width", "marginLeft", "marginRight", "paddingLeft", "paddingRight" ],
    // opacity animations
    [ "opacity" ]
];

function genFx( type, num ){
    var obj = {};
    jQuery.each( fxAttrs.concat.apply([], fxAttrs.slice(0,num)), function(){
        obj[ this ] = type;
    });
    return obj;
}

var TW_SLIDE_UP = genFx('hide', 1);

var tw_show_reply_box = function(self, start_text){
    var me = $(self);
    var txt = me.parents(".tweetContent").find(".input_area");
    var name = tw_get_replyto_name(self);
    var tweet_id = tw_get_tweet_id(self);

    var val_set = false;

//    var text_adjust = 0;
    var last_val = txt.data('last_val') || '';
    if (start_text === 'RT ') {
        last_val = start_text + '@' + name + ': ' + tw_get_tweet_text(self);
//        text_adjust = last_val.length;
    } else if (!last_val) {
        last_val = start_text + name + ' ';
//        text_adjust = last_val.length;
    } else {
        if (last_val.substring(0,1) === '@') {
            last_val = start_text + last_val.substring(1);
//            text_adjust = start_text.length - '@'.length;
        } else if (last_val.substring(0,2) === 'd ') {
            last_val = start_text + last_val.substring(2);
//            text_adjust = start_text.length - 'd '.length;
        } else {
            last_val = start_text + name + ' ';
//            text_adjust = last_val.length;
        }
    }
    txt.data('last_val', last_val);
//    txt.data('text_adjust', text_adjust);

    if (!txt.hasClass("tw_bound")) {
        txt.addClass("tw_bound")
        var haveFocus = false;

        var _text_changed = function (self) {
            $(self).parents('.form_wrapper').find('.char_count').text(140-self.value.length);
            if (self.value.length > 140){
                $(self).addClass('input_area_over_limit');
            } else {
                $(self).removeClass('input_area_over_limit');
            }
        }
        var text_changed = function () {
            return _text_changed(this);
        }

        var blurFunc = function(animate) {
            if (!haveFocus) {
                return true;
            }
            $(txt).unbind('keydown', 'esc');
            $(txt).unbind('keydown', 'shift+return');
            $(txt).unbind('keydown', 'return');
            $(txt).unbind('keydown', text_changed);
            $(txt).unbind('keyup', text_changed);
            $(txt).unbind('keypress', text_changed);
            $(txt).unbind('change', text_changed);
            txt.data('last_val', this.value);
            this.value = '';
            if (animate != false){
                txt.parents('.tweetContent').find('.form_wrapper').animate(TW_SLIDE_UP, {queue:false, duration:100});
                txt.parents('.tweetContent').find('.controls').slideDown(100);
            } else {
                txt.parents('.tweetContent').find('.form_wrapper').hide();
                txt.parents('.tweetContent').find('.controls').show();
            }

            haveFocus = false;
            return true; //blur should continue, so that we don't keep focus and possibly trigger another blur event.
        }

        $(txt.parents('.form_wrapper')[0]).css('padding-right', commentFieldPaddingX);

        txt.focus( function() {
            if (haveFocus) {
                return;
            }
            haveFocus = true;
//            var text_adjust = txt.data('text_adjust');
//            if (!val_set) {this.focus(); val_set=true;}
            this.focus();
            this.value = txt.data('last_val') || '';
            _text_changed(this);
            $(this).jGrow();
//            if (text_adjust){
//                var start = this.selectionStart;
//                var end = this.selectionEnd;
//                this.selectionStart = start + text_adjust;
//                this.selectionEnd = end + text_adjust;
//            }

            $(this).bind('keydown', 'esc', function(){ txt.blur(); return false;});
            $(this).bind('keydown', 'shift+return', function(){
                var start = this.selectionStart;
                var end   = this.selectionEnd;
                this.value = this.value.substr(0, start)
                    + '\n'
                    + this.value.substr(end, this.value.length);
                _text_changed(this);
                this.selectionStart = start + 1;
                this.selectionEnd = start + 1;
                return false;
            });
            $(this).bind('keydown', 'return', function(){
                if (this.value && !this.disabled) {
                    var opts = {status:this.value};
                    if (this.value.substring(0,1) === '@') {
                        opts['reply_id'] = tweet_id;
                    }
                    D.notify('send_tweet', opts);
                    this.value = '';
                    _text_changed(this);
                    val_set=false;
                    txt.blur();
                } else if (!this.value) {
                    //hide_this_comment_box();
                }
                return false;
            });

            $(this).bind('keydown', text_changed);
            $(this).bind('keyup', text_changed);
            $(this).bind('keypress', text_changed);
            $(this).bind('change', text_changed);
            haveFocus = true;
            // When hiding the infobox, blur any active textboxes.
            //TODO: fix/create the necessary functions so that things that don't need to happen don't
            swapOut(function() { blurFunc(false); });
            onHide(function() { blurFunc(false); });
        });

        txt.blur(blurFunc);

    }
    txt.parents('.tweetContent').find('.controls').animate(TW_SLIDE_UP, {queue:false, duration:100});
    txt.parents('.tweetContent').find('.form_wrapper').slideDown(100, function(){
        txt.focus();
    });
}

var tw_get_replyto_name = function(self) {return JSON.parse($(self).parents('.tweetContent').find('.sender_text').text());}

var tw_get_tweet_id = function(self) {return $(self).parents('.tweetContent').attr('id');}

var tw_get_tweet_text = function(self) {return JSON.parse($(self).parents('.tweetContent').find('.tweet_text_value').text());}

var tw_reply_click = function(){ tw_show_reply_box(this, '@'); return true;}

var tw_direct_click = function(){ tw_show_reply_box(this, 'd '); return true;}

var tw_retweet_click = function(){ tw_show_reply_box(this, 'RT '); return true;}

var tw_is_favorited = function(self){ return $(self).parents('.controls').hasClass('favorite_on'); }

var tw_trend_click = function() {
    var query = JSON.parse($(this).parents('.trend').find('.trendval').text());
    console.log('trend click: ' + query);
    D.notify('infobox_hide');
    D.notify('change_view', {
        "query": query,
        "save": false,
        "type": "search"
    });
   return false;
}

var tw_favorite_click = function() {
    var favorited = tw_is_favorited(this);
    console.log('classes: ' + $(this).parents('.controls').attr('class'));
    console.log('favorited: ' + favorited);
    $(this).parents('.controls').removeClass('favorite_on').removeClass('favorite_off').addClass('favorite_pending');
    var self = this;
    D.rpc('favorite_tweet', {tweet:{id:tw_get_tweet_id(this), favorited:favorited}},
        function(){
            $(self).parents('.controls').removeClass('favorite_pending').toggleClass('favorite_on', !favorited).toggleClass('favorite_off', favorited);
        },
        function(){
            $(self).parents('.controls').removeClass('favorite_pending').toggleClass('favorite_on', favorited).toggleClass('favorite_off', !favorited);
        });
    return false;
}

var tw_delete_click = function() {
    $(this).parents('.controls').addClass('delete_pending');
    var self = this;
    D.rpc('delete_tweet', {tweet:{id:tw_get_tweet_id(this)}},
        function(){
            var tweet = $(self).parents('.tweet');
            var hr = tweet.next('hr.post_divider');
            tweet.remove();
            hr.remove();
            adjust_height();
        },
        function(){
            $(self).parents('.controls').removeClass('delete_pending');
        });
    return false;
}

var tw_status_update_clicked = function(){
    D.notify('status_update_clicked');
}

function tw_near_bottom(){
    var desired = window.digsby_infobox_desired_height;
    var window_inner_height = window.innerHeight;
    if (!desired || desired < window_inner_height) {
        desired = window_inner_height;
    }
    var pageYOffset = window.pageYOffset;
    var offsetHeight = document.body.offsetHeight;

    ret = ( pageYOffset >= ( offsetHeight - ( desired * 2.0 ) ) );
    return ret;
}

var inited = false;

var scrollRequestOutstanding = false;

var myName = currentContentName;

var didRequestIds = {};


var tw_on_scroll = function(post_table) {
    if (!inited || myName !== currentContentName) {
        console.log('tw_on_scroll ' + myName + ' shortcircut1: ' + currentContentName);
        return;
    }

    if (scrollRequestOutstanding)
        return;
    scrollRequestOutstanding = true;

    if (tw_Active && tw_near_bottom()) {
        var rows = $(post_table).find('.tweet');
        var last_post_id = $(rows[rows.length-1]).attr('id');

        // don't request past a certain ID more than once.
        /* //doesn't play nice with new SocialFeed injection.
        if (last_post_id in didRequestIds) {
            scrollRequestOutstanding = false;
            return;
        }
        didRequestIds[last_post_id] = true;
        */

        D.rpc('next_item', {},
                function(args) {
                    if (!scrollRequestOutstanding)
                        return;
                    if (!inited || myName !== currentContentName) {
                        scrollRequestOutstanding = false;
                        return;
                    }
                    var dateparent = $('<div></div>');
                    dateparent.append(args.html);
                    html = dateparent.contents().remove();
                    html.remove();
                    dateparent.remove();
                    html.appendTo($(post_table));
                    scrollRequestOutstanding = false;
                    tw_on_scroll(post_table);
                },
                function(args) {
                    scrollRequestOutstanding = false;
                }
            );
    } else {
        scrollRequestOutstanding = false;
    };
}

var post_table = null;

function tw_do_scroll(){
    tw_on_scroll(post_table);
}

var tw_Active = false;

swapOut(function(){
    tw_Active = false;
});

swapIn(function(){
    tw_Active = true;
    if (!inited){
        inited=true;
    };
});


swapIn(function() {
    $(".tw_reply_link").live("click", tw_reply_click);
    $(".tw_retweet_link").live("click", tw_retweet_click);
    $(".tw_direct_link").live("click", tw_direct_click);
    $(".tw_delete_link").live("click", tw_delete_click);
    $(".tw_favorite_link").live("click", tw_favorite_click);
    $(".trendlink").live("click", tw_trend_click);
    $(".status_updater").live("click", tw_status_update_clicked);
});

swapOut(function() {
    $(".tw_reply_link").die("click", tw_reply_click);
    $(".tw_retweet_link").die("click", tw_retweet_click);
    $(".tw_direct_link").die("click", tw_direct_click);
    $(".tw_delete_link").die("click", tw_delete_click);
    $(".tw_favorite_link").die("click", tw_favorite_click);
    $(".trendlink").die("click", tw_trend_click);
    $(".status_updater").die("click", tw_status_update_clicked);
});

D.notify('initialize_feed'); //before binding the scroll events, though those really happen later.

swapIn(function(){
    post_table = $(document).find('.tweets')[0];
    setDesiredHeightCallback(tw_do_scroll);
    $(window).bind('scroll',tw_do_scroll);
    tw_do_scroll();
    setTimeout(tw_do_scroll, 500);
});

swapOut(function(){
    $(window).unbind('scroll');
    setDesiredHeightCallback(null);
});

