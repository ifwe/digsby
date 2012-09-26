var transitionDefault = 200;
$(add_link_class_to_a_tags);
/*
$(clear_previous_time_containers);
$(function () {add_time_containers("li.news-item");});
*/
$(clear_previous_date_separators);
$(function () {add_date_separators(".news-item[timestamp]");});

var fxAttrs = [
    // height animations
    [ "height", "marginTop", "marginBottom", "paddingTop", "paddingBottom" ],
    // width animations
    [ "width", "marginLeft", "marginRight", "paddingLeft", "paddingRight" ],
    // opacity animations
    [ "opacity" ]
];

function li_clear_error(callback) {
    error = $('.news-item-content').find('.error_section');
    var do_clear = function () {
        error.html('');
        if (callback) { callback(); };
    }

    if (error.css('display') === 'block') {
        error.slideUp(transitionDefault / 2);
    } else if (!error.css('display')) {
        error.css('display', 'none');
    } else {

    }

    do_clear();
}

function genFx( type, num ){
    var obj = {};
    jQuery.each( fxAttrs.concat.apply([], fxAttrs.slice(0,num)), function(){
        obj[ this ] = type;
    });
    return obj;
}

var LI_SLIDE_UP = genFx('hide', 1);
var li_commentFieldPadding;

$(function(){
    var t = $("<textarea/>").css({'position':'fixed', 'right':'-500px', 'bottom':'-500px'}).appendTo(document.body);
    li_commentFieldPadding =  t.outerWidth() - t.width();
    t.remove();
})

function li_hide_this_comment_box(self, animate) {
    if (animate === undefined) {
        animate = true;
    }

    var me = $(self);
    var nic = me.parents(".news-item-content");

    var comment_box_disabled = $(nic[0]).find('[name="comment_input"]')[0].disabled

    if (comment_box_disabled) {
        return false;
    }

    nic.find('.comments_section').css('-webkit-user-select', 'none');
    var end = $(nic[0]).find('.comments_end');
    var comment_button_section = nic.find(".comment_button_section");
    var likes_comment_section = nic.find(".comments_section");

    var time = animate ? transitionDefault : 0;

    if (time) {
        end.animate(LI_SLIDE_UP, {queue:false, duration:time});
        offset_top = nic.offset().top;

        var pageYOffset = window.pageYOffset;
        var offsetHeight = document.body.offsetHeight;
        if (offset_top < pageYOffset) {
            $('html, body').animate({scrollTop: offset_top},
                                    {queue : false, duration : time});
        }

        likes_comment_section.slideUp(time, function() {
            likes_comment_section.css('-webkit-user-select', 'text');
        });
        comment_button_section.show();
    } else {
        end.hide();
        comment_button_section.show();
        likes_comment_section.hide();
        likes_comment_section.css('-webkit-user-select', 'text');
    }

    return false;
}

function li_show_comment_box(self) {
    var me = $(self);
    li_clear_error();
    var comment_link = me.parents(".news-item-content").find(".comment_button_section");
    me.parents(".news-item-content").find(".comments_section").css("-webkit-user-select", "none");

    var end = me.parents(".news-item-content").find(".comments_end");
    var txt;

    if (end.find(".form_wrapper").length == 0) {
        end.html('<div class="form_wrapper"><textarea name="comment_input" rows="1" class="input_area expanding minor_border" /></div>');
        txt = end.find("textarea");

        var haveFocus = false;
        var blurFunc = function(animate) {
            if (!haveFocus) {
                return true;
            }

            $(txt).unbind('keydown', 'esc');
            $(txt).unbind('keydown', 'shift+return');
            $(txt).unbind('keydown', 'return');

            li_hide_this_comment_box(txt, animate);
            li_clear_error();

            haveFocus = false;
            return true;
        }

        $(txt.parents('.form_wrapper')[0]).css('padding-right', li_commentFieldPadding);

        txt.focus( function () {
            if (haveFocus) {
                return;
            }

            haveFocus = true;

            $(this).bind('keydown', 'esc', function() {txt.blur();});
            $(this).bind('keydown', 'shift+return', function (){
                var start = this.selectionStart;
                var end   = this.selectionEnd;
                this.value = this.value.substr(0, start) + '\n' + this.value.substr(end, this.value.length);
                this.selectionStart = start + 1;
                this.selectionEnd = start + 1;
                return false;
            });
            $(this).bind("keydown", 'return', function() {
                if (this.value && !this.disabled) {
                    li_post_comment(this);
                }
                return false;
            });

            swapOut(function() {blurFunc(false);});
            onHide(function() {blurFunc(false);});
        });
        txt.blur(blurFunc);
    }

    txt = end.find('textarea');
    txt.parents('.news-item-content').find('.comments_section').slideDown(transitionDefault/2,
    function () {
        comment_link.hide();
        end.slideDown(transitionDefault/2, function () {
            txt[0].value = '';
            txt[0].disabled = false;
            txt.jGrow();
            txt.focus();
            me.parents(".news-item-content").find('.comments_section').css('-webkit-user-select', 'text');
        });
    });

    txt.focus();

}


function li_error_text(self, text, error_obj, callback){
    error = $(self).parents(".news-item").find('.error_section');
    if (error_obj !== undefined && error_obj !== null) {
        if (error_obj.error_msg) {
            text += " "  + error_obj.error_msg;
        }
    }
    console.log("text =  " + text);
    error.html(text);
    if (error.css('display') === 'none'){
        error.slideDown(transitionDefault, callback);
        return; // don't call callback, slideDown will do it.
    } else if (!error.css('display')) {
        error.css('display', 'block');
    }

    if (callback){
        callback();
    };
}

function li_comments_updater(self, slide, clear_error) {
    var _inner = function(args) {
        console.log("CALLBACK");
        var comments_html = $($(args.comments_html)[0]);
        var comment_link_html = $($(args.comment_link_html)[0]);

        comments = $(comments_html[0]).find(".comment");

        if ((comments.length) && (slide == "new")) {
            new_comment = $(comments[comments.length - 1]);
            new_comment.hide();
        } else {
            new_comment = null;
        }

        comment_link_html.hide();
        console.log("got new comment html, initing");
        li_init(comments_html);
        console.log("inited comment html");
        $(self).parents('.news-item-content').find('.comments').replaceWith(comments_html);

        $($(self).parents(".news-item-content").find('.comment_button_section')[0]).replaceWith(comment_link_html);

        comment_box = $($(self).parents('.form_wrapper')[0]).find("textarea[name='comment_input']");

        if (slide == "new") {
            slide_element = new_comment;
        } else if (slide == "all") {
            slide_element = $(self).parents(".comments_section");
        }

        console.log("got slide element");
        if (clear_error) {
            console.log("clear error");
            li_clear_error(function() {
                var after = function() {
                    $($(self).parents('.form_wrapper')[0]).find('.loader_img').remove();
                    comment_box[0].value = '';
                    comment_box[0].disabled = false;
                    comment_box.jGrow();
                };
                if (slide_element != null){
                    slide_element.slideDown(transitionDefault, after);
                } else {
                    after();
                }
            });
        }

        comment_box.focus();
        console.log("done with new html");
    }

    return _inner;
}

var li_post_comment = function (self) {
    self.disabled = true;

    var comment_box = $(self);
    var comment = comment_box.attr('value');
    var post_id = $(comment_box.parents(".news-item")[0]).attr("id");

    $(comment_box.parents(".form_wrapper")[0]).append(loader_img);
    D.rpc('post_comment', {'comment' : comment, 'post_id' : post_id},
          li_comments_updater(self, 'new', true),
          function (error_obj) {
              console.log("error posting comment");
              li_error_text(comment_box, 'Error posting comment.', error_obj, function(){
                  $(comment_box.parents(".form_wrapper")[0]).find('.loader_img').remove();
                  comment_box[0].disabled = false;
                  comment_box.focus();
              });
          }
    );

    return false;
}

function li_liked(like, args) {
    var me = args.me;
    var item_html = $(args['item_html']);
    li_clear_error(function(){
        li_init(item_html);
        me.parents('.news-item').replaceWith(item_html);
        //me.parents('.messagecell').find('.' + like + 's').replaceWith(likes_html);
        //me.parents('.messagecell').find('.' + like +'_link_block').replaceWith(link_html);
    });
}

function li_like_button_mousedown(e) {
    var like = null;
    if ($(e.target).hasClass("like_button")) {
        like = "like";
    } else if ($(e.target).hasClass("dislike_button")) {
        like = "dislike";
    }

    if (like == null) {
        return false;
    }

    me = $(this);
    me.parents('.news-item').find('.' + like + '_link_block').hide();
    var post_id = $(me.parents(".news-item")[0]).attr('id');
    console.log("post id = " + post_id);
    D.rpc('do_' + like, {"post_id":post_id},
        function(args) {
            args.me = me;
            return li_liked(like, args);
        },
        function(error_obj){
            var msg = 'Error adding ' + like + '.';
            li_error_text(me, msg, error_obj, function(){
                me.parents('.messagecell').find('.' + like + '_button_section, .num_' + like + 's').show();
            });
        }
    );
    return false;
}

var li_comment_button_mousedown = function(){ li_show_comment_box(this); return true;}

function li_false() {
    return false;
}

var li_inited = null;

swapIn(function () {

   $("a[href]").each(function() {
       $(this).removeAttr("target");
       if ($(this).attr("href").match("^/")) {
           $(this).attr("href", "http://www.linkedin.com" + $(this).attr("href"));
       }
    })
});

var li_inited = false;
var li_active = false;
var li_scrollRequestOutstanding = false;

var myName = currentContentName;

D.notify('initialize_feed');

function li_near_bottom() {
    return ( window.pageYOffset >= ( document.body.offsetHeight - ( window.innerHeight * 2.0 ) ) );
}

function li_on_scroll() {
    if (!li_inited || myName !== currentContentName){
        console.log('li_on_scroll ' + myName + ' shortcircut1: ' + currentContentName);
        return;
    }
    if (li_scrollRequestOutstanding){
        return;
    }
    li_scrollRequestOutstanding = true;
    if (!(li_active && li_near_bottom())) {
        li_scrollRequestOutstanding = false;
        return;
    }
    rows = $(".news-item");
    var parent = $($(".news-item-list")[0]);
    var rows = parent.find(".news-item");
    last_item_id = $(rows[rows.length-1]).attr('id');

    D.rpc('next_item',
        {},
        function (args) {
            //console.log("next item success");
            if (!li_scrollRequestOutstanding)
                return;
            if (!li_inited || myName !== currentContentName){
                li_scrollRequestOutstanding = false;
                return;
            }
            //var dateparent = $('<div></div>');
            //dateparent.append(args.html);
            //html = dateparent.contents().remove();
            //html.remove();
            //dateparent.remove();
            var html = $(args.html);
            html.appendTo(parent);
            li_init(html);

            clear_previous_date_separators();
            var rows2 = $().find(".news-item[timestamp]");
            add_date_separators(rows2);

            li_scrollRequestOutstanding = false;
            li_on_scroll();
        },
        function (args) {
            console.log("next item fail: error with rpc thing:" + args);
        }
    );
}

swapOut(function() {console.log('*** linkedin SWAP OUT'); });
swapIn(function() {console.log('*** linkedin SWAP IN'); });

function li_init(tree) {
    TODAY_TEXT = '';
    if (!tree) {
        if (li_inited) {
            return;
        }
        li_inited = true;
        tree = $();
    }
    clip_imgs(tree);
    convert_timestamps_to_text(tree);
}

var _linkedin_positioned_no_news = false;

swapIn(function () {
    if (!_linkedin_positioned_no_news) {
        _linkedin_positioned_no_news = true;
        try {
            $(".no-news-today").insertBefore($(".date-separator:not(.static,.today)")[0]);
        } catch (e) {};
    }
});

swapIn(li_init);

swapIn(function() {
    li_active = true;
    //D = DCallbacks(currentContentName);
    myName = currentContentName;
    console.log('swapin: '+ currentContentName + '/' + myName);

    $(window).bind('scroll', li_on_scroll);
    $(".comment_button").live("mousedown", li_comment_button_mousedown);
    $(".like_button").live("mousedown", li_false);
    $(".like_button").live("click", li_like_button_mousedown);
    $(".dislike_button").live("mousedown", li_false);
    $(".dislike_button").live("click", li_like_button_mousedown);

    li_on_scroll();
} );
swapOut(function() {
    console.log('swapout: '+ currentContentName + '/' + myName);
    li_active = false;
    $(window).unbind('scroll');
    $(".comment_button").die("mousedown", li_comment_button_mousedown);
    $(".like_button").die("mousedown", li_false);
    $(".like_button").die("click", li_like_button_mousedown);
    $(".dislike_button").die("mousedown", li_false);
    $(".dislike_button").die("click", li_like_button_mousedown);
} );

swapOut(li_clear_error);
onHide(li_clear_error);

