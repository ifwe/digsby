var TODAY_TEXT = "";

var ACTIVE_FILTERS = ['nf', '__trend__'];

function fb_comments_updater(self, slide, clear_error) {
    return function(args) {
        var comments_html = $($(args.comments_html)[0]);
        var comment_link_html = $($(args.comment_link_html)[0]);
        var comments = $(comments_html[0]).find(".comment");
        var count = args.count;

        var new_comment;

        if ((comments.length) && (slide == "new")) {
            new_comment = $(comments[comments.length-1]);
            new_comment.hide();
        } else {
            new_comment = null;
        }
        comment_link_html.hide();
        //comments_html.hide();
        comments_html.find(".time").each(do_convert_time);
        fb_init_comment_a(comments_html);
        $(self).parents('.messagecell').find('.comments').replaceWith(comments_html);
        //only want the "Comment ()" chunk, not the "()" after likes -----v
        $($(self).parents(".messagecell").find('.comment_button_section')[0]).replaceWith(comment_link_html);
        comment_box = $($(self).parents(".form_wrapper")[0]).find("textarea[name='foo']");

        if (slide == "new") {
            slide_element = new_comment;
        } else if (slide == "all") {
            slide_element = comments_html;
        }

        if (clear_error) {
            fb_clear_error(function(){
                slide_element.slideDown(transitionDefault, function(){
                    $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                    comment_box[0].value = '';
                    comment_box[0].disabled = false;
                    comment_box.jGrow();
                });
            });
        } else {
            //slide_element.slideDown(transitionDefault);
        }
        comment_box.focus();
    };
}

var show_comment_box = function(self){
    var me = $(self);
    me.parents(".messagecell").find('.comment_button_section').hide(); // placeholder
    me.parents(".messagecell").find('.likes_comments_section').css('-webkit-user-select','none');

    var end = me.parents(".messagecell").find(".comments_end");
    var txt;
    if (end.text() =="placeholder"){
        end.html('<div class="form_wrapper"><textarea name="foo" rows="1" class="input_area expanding minor_border"/></div>');
        txt = end.find('textarea');

        var haveFocus = false;

        var blurFunc = function(animate) {
            if (!haveFocus) {
                return true;
            }
//            if ($(txt).parents(".post_row").hasClass('mouseover')){
//                return true;
//            }
            $(txt).unbind('keydown', 'esc');
            $(txt).unbind('keydown', 'shift+return');
            $(txt).unbind('keydown', 'return');
            hide_this_comment_box(txt, animate);
            haveFocus = false;
            return true; //blur should continue, so that we don't keep focus and possibly trigger another blur event.
        }

        $(txt.parents('.form_wrapper')[0]).css('padding-right', commentFieldPadding);

        txt.focus( function() {
            if (haveFocus) {
                return;
            }
            haveFocus = true;
            $(this).bind('keydown', 'esc', function(){ txt.blur(); });
            $(this).bind('keydown', 'shift+return', function(){
                var start = this.selectionStart;
                var end   = this.selectionEnd;
                this.value = this.value.substr(0, start)
                    + '\n'
                    + this.value.substr(end, this.value.length);
                this.selectionStart = start + 1;
                this.selectionEnd = start + 1;
                return false;
            });
            $(this).bind('keydown', 'return', function(){
                if (this.value && !this.disabled) {
                    post_comment(this);
                } else {
                    //hide_this_comment_box();
                }
                return false;
            });
            haveFocus = true;
            // When hiding the infobox, blur any active textboxes.
            //TODO: fix/create the necessary functions so that things that don't need to happen don't
            swapOut(function() { blurFunc(false); });
            onHide(function() { blurFunc(false); });
        });

        txt.blur(blurFunc);
    }
    txt = end.find('textarea');
//    txt.parents('.messagecell').find('.comment_block, .likes').show();
    txt.parents('.messagecell').find('.likes_comments_section').slideDown(transitionDefault/2, function(){
        end.slideDown(transitionDefault/2, function(){
            txt.jGrow();
            txt.focus();
            //me.parents('.messagecell').find('.likes_comments_section').show();
            me.parents(".messagecell").find('.likes_comments_section').css('-webkit-user-select','text');
        });
    });

    if (me.parents(".messagecell").find('.comments').hasClass('have_comments') ) {
        //return false;
    }
    comment_textfield = txt[0];
    comment_textfield.disabled = true;
    $(txt.parents(".form_wrapper")[0]).append(loader_img);

    var post_id = $($(self).parents(".post_row")[0]).attr('id');
    D.rpc("get_comments",
          {'post_id':post_id},
          function (args) {
            fb_comments_updater(self, "all")(args);
            txt[0].disabled = false;
            $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
            txt.focus();
          },
          function(error_obj){
                if (error_obj.error_msg == "no_change") {
                  txt[0].disabled = false;
                  $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                  txt.focus();
                  return;
                }
                error_text(comment_textfield, 'Error retrieving comments.', error_obj, function(){
                    $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                    txt[0].disabled = true;
                    //me.parents(".activity-data").find('.comment_button_section').show();
                    txt.slideUp();
                });
            }
        );
    return false;
}

var fb_comment_button_mousedown = function() {
//    get_comments(this);
    show_comment_box(this);
    return true;
}

var get_comments = function(self) {
    var post_id = $($(self).parents(".post_row")[0]).attr('id');
    $(self).parents('.messagecell').find('.comments').html('<span></span>');
    D.rpc('get_comments', {'post_id':post_id},
            function(args){
                var comments_html = args.comments_html;
                var comment_link_html = args.comment_link_html;
                var foo = $(comments_html);
                var bar = $(comment_link_html);
                foo.hide();
                foo.find(".time").each(do_convert_time);
                fb_init_comment_a(foo);
                $(self).parents('.messagecell').find('.comments').replaceWith(foo);
                //only want the "Comment ()" chunk, not the "()" after likes -----v
                var oldbar = $($(self).parents(".messagecell").find('.comment_button_section')[0]);
                if (oldbar.css('display') === 'none') {
                    bar.hide();
                }
                oldbar.replaceWith(bar);
                foo.slideDown(transitionDefault);
            },
            function(error_obj){
                error_text($(self), 'Error retrieving comments.', error_obj, function(){
                    $(self).parents('.messagecell').find('.comments').find('.loader_img').remove();
                });
            }
        );
}

var post_comment = function (self){
    self.disabled = true;
    var comment_box = $(self);
    var comment = $(self).attr('value');
    var post_id = $($(self).parents(".post_row")[0]).attr('id');
    $($(self).parents(".form_wrapper")[0]).append(loader_img);
    D.rpc('post_comment', {'comment':comment, 'post_id':post_id},
            function(args){
                var comment_html = args.comment_html;
                var comment_link_html = args.comment_link_html;
                var comment_post_link = args.comment_post_link;
                var foo = $(comment_html);
                var bar = $(comment_link_html);
                foo.hide();
                bar.hide();
                foo.find(".time").each(do_convert_time);
                fb_init_comment_a(foo);
                $(self).parents('.messagecell').find('.comments').append(foo);
                if ($(self).parents('.messagecell').find('.comment_post_link').length){
                    $(self).parents('.messagecell').find('.comment_post_link').replaceWith(comment_post_link);
                } else {
                    $(self).parents('.messagecell').find('.comments').after(comment_post_link);
                }
                //only want the "Comment ()" chunk, not the "()" after likes -----v
                $($(self).parents(".messagecell").find('.comment_button_section')[0]).replaceWith(bar);
                fb_clear_error(comment_box, function(){
                    foo.slideDown(transitionDefault, function(){
                        $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                        comment_box[0].value = '';
                        comment_box[0].disabled = false;
                        comment_box.jGrow();
                        comment_box.focus();
                    });
                });
            },
            function(error_obj){
                error_text(comment_box, 'Error posting comment.', error_obj, function(){
                    $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                    comment_box[0].disabled = false;
                    comment_box.focus();
                });
            }
        );
    return false;
}

function fb_liked(args) {
    var me = args.me;
    var likes_html = args.likes_html;
    var link_html = args.link_html;
    fb_clear_error(me, function(){
        me.parents('.messagecell').find('.likes').replaceWith(likes_html);
        me.parents('.messagecell').find('.like_link_block').replaceWith(link_html);
    });
}

function fb_disliked(args) {
    var me = args.me;
    var likes_html = args.likes_html;
    var link_html = args.link_html;
    fb_clear_error(me, function(){
        me.parents('.messagecell').find('.dislikes').replaceWith(likes_html);
        me.parents('.messagecell').find('.dislike_link_block').replaceWith(link_html);
    });
}

function fb_like_button_mousedown(){
    me = $(this);
    me.parents('.messagecell').find('.like_button_section, .num_likes').hide();
    var post_id = $($(this).parents(".post_row")[0]).attr('id');
    D.rpc('do_like', {'post_id':post_id},
        function(args) {
            args.me = me;
            return fb_liked(args);
        },
        function(error_obj){
            var msg = 'Error adding like.';
            error_text(me, msg, error_obj, function(){
                me.parents('.messagecell').find('.like_button_section, .num_likes').show();
            });
        }
    );
    return false;
}

function fb_unlike_button_mousedown(){
    me = $(this);
    me.parents('.messagecell').find('.like_button_section, .num_likes').hide();
    var post_id = $($(this).parents(".post_row")[0]).attr('id');
    D.rpc('do_unlike', {'post_id':post_id},
        function(args) {
            args.me = me;
            return fb_liked(args);
        },
        function(error_obj){
            error_text(me, 'Error removing like.', error_obj, function(){
                me.parents('.messagecell').find('.like_button_section, .num_likes').show();
            });
        }
    );
    return false;
}

function fb_dislike_button_mousedown(){
    me = $(this);
    me.parents('.messagecell').find('.dislike_button_section, .num_dislikes').hide();
    var post_id = $($(this).parents(".post_row")[0]).attr('id');
    D.rpc('do_dislike', {'post_id':post_id},
        function(args) {
            args.me = me;
            return fb_disliked(args);
        },
        function(error_obj){
            var msg = 'Error adding dislike.';
            error_text(me, msg, error_obj, function(){
                me.parents('.messagecell').find('.dislike_button_section, .num_dislikes').show();
            });
        }
    );
    return false;
}

function fb_undislike_button_mousedown(){
    me = $(this);
    me.parents('.messagecell').find('.dislike_button_section, .num_dislikes').hide();
    var post_id = $($(this).parents(".post_row")[0]).attr('id');
    D.rpc('do_undislike', {'post_id':post_id},
        function(args) {
            args.me = me;
            return fb_disliked(args);
        },
        function(error_obj){
            var msg = 'Error removing dislike.';
            error_text(me, msg, error_obj, function(){
                me.parents('.messagecell').find('.dislike_button_section, .num_dislikes').show();
            });
        }
    );
    return false;
}

function fb_del_comment_link_mousedown(){
    me = $(this);
    $(me.parents('.del_comment')[0]).hide();
    var comment_id = $($(this).parents(".comment")[0]).attr('id').substring("comment_".length);
    D.rpc('remove_comment', {'comment_id':comment_id},
            function(args){
                var comment_link_html = args.comment_link_html;
                var comment_post_link = args.comment_post_link;
                var current_comment_link = $(me.parents(".messagecell").find('.comment_button_section')[0]);
                var current_comment_post_link =
                fb_clear_error(me, function(){
                    remove_comment(comment_id);
                    current_comment_link.replaceWith(comment_link_html);
                    me.parents(".messagecell").find('.comment_post_link').replaceWith(args.comment_post_link);
                });
            },
            function(error_obj){
                error_text(me, 'Error deleting comment.', error_obj, function(){
                    $(me.parents('.del_comment')[0]).show();
                });
            });
    return false;
}

//timestamps
function fb_init_time(tree){
    tree.find(".time").each(do_convert_time);
}

// end timestamps

function fb_init_pix(tree){
    var pix = tree.find(".picturelink");
    pix.hide();
    pix.css({'max-width':'100%'});
}
// end image sizing

function infoboxIsShowing() {
    if (onInfoboxShow) {
        onInfoboxShow();
        onInfoboxShow = undefined;
    };
}

var LIGHTBOX_OPTIONS = {
    changeCounterAfterSlide: false,
    wrapNav: true,
    imageDir: LIGHTBOX_IMAGE_DIR,
    dataBoxFirst: true,
    containerBorderSize: 0,
    fixedDataBox: true,
    clickLoadingClose: false,
    clickBoxClose: false,
    txtImage: "",
    txtOf: "/",
    //imageContext: 'popout.gif',
    showContext: true,
    forceTitleBar: true,
    onShowFunction: function(){ D.notify('hook', 'digsby.facebook.photo_seen') },
}

jQuery.fn.sort = function() {
    return this.pushStack( [].sort.apply( this, arguments ), []);
};

function fb_init_picturelink(tree){
    tree.find(".media_row").each(function() {
        var photos = $($(this).find(".photolinklink").sort(function (a,b){ return parseInt($(a).attr('index'), 10) > parseInt($(b).attr('index'), 10) ? 1 : -1; }));
        var lightboxParent = $(this).find('.media_cell');
        var array_updated = false;
        var lightBoxHooks = photos.lightBox(jQuery.extend({},
                                      LIGHTBOX_OPTIONS,
                                      {parentSelector: lightboxParent,
                                       onInitFunction: function(){
                                                        if (array_updated){
                                                            return;
                                                        }
                                                        D.rpc('get_album',
                                                              {'aid':$(photos[0]).attr('aid')},
                                                              function (args) {
                                                                  var newdata = args.album;
                                                                  var newArray = [];
                                                                  for (var i = 0; i < newdata.length; i++){
                                                                      var obj = newdata[i];
                                                                      newArray.push(new Array(obj['src_big'], //href
                                                                                              obj['caption'], //title
                                                                                              obj['link'], //context
                                                                                              $(photos[0]).offset(), //?
                                                                                              '', //?
                                                                                              obj['pid'] // image id
                                                                                              )
                                                                                    );
                                                                  }
                                                                  array_updated = true;
                                                                  lightBoxHooks.updateImageArray(newArray);
                                                              }
                                                        )
                                                        },
                                       lengthTextFunction: function(arrayLen){
                                            if (!array_updated){
                                                return '?';
                                            } else {
                                                return arrayLen;
                                            }
                                       },
                                       realIndexFunction: function (arrayIdx) {
                                           if (!array_updated){
                                               return parseInt($(photos[arrayIdx]).attr('index'), 10);
                                           } else {
                                               return arrayIdx;
                                           }
                                       },
                                       imgIdFunction: function (obj) { return obj.getAttribute('pid'); },
                                      }));
    });
    var picturelink = tree.find(".picturelink");
    picturelink.bind("load", size_images);
//    picturelink.fullsize({'forceTitleBar':true, 'shadow':false});
}

function fb_uninit_picturelink(tree){
    var picturelink = tree.find(".picturelink");
    picturelink.unbind("load", size_images);
//    picturelink.fullsize({'forceTitleBar':true, 'shadow':false});
}

// our webkit does not support _blank links, so remove all "target" attributes
// from <a> tags (target="_blank" comes in with some types of posts)
function fb_init_a(tree) {
    tree.find('a').removeAttr('target');
}

function fb_init_comment_a(selector){
    selector.find('a').addClass('no_ondown_link');
}

function fb_initialize(tree){
    if (!tree){
        tree = $();
    };
    fb_init_time(tree);
    fb_init_pix(tree);
    fb_init_picturelink(tree);
    fb_init_a(tree);
    fb_init_comment_a(tree.find('.comment_block'));
    return tree;
}

function fb_initialize_swapin(tree){
    if (!tree){
        tree = $();
    };
    fb_init_picturelink(tree);
    return tree;
}

function fb_uninitialize(tree){
    if (!tree){
        tree = $();
    };
//    fb_uninit_time(tree);
//    fb_uninit_pix(tree);
    fb_uninit_picturelink(tree);
//    fb_uninit_a(tree);
    return tree;
}

function fb_uninitialize_swapout(tree){
    return fb_uninitialize(tree);
}

var inited = false;

var scrollRequestOutstanding = false;

var myName = currentContentName;

var fb_on_scroll = function(post_table) {
//    console.log('fb_on_scroll 1');
    if (!inited || myName !== currentContentName){
        console.log('fb_on_scroll ' + myName + ' shortcircut1: ' + currentContentName);
        return;
    }
    if (scrollRequestOutstanding){
        return;
    }
    scrollRequestOutstanding = true;
//    console.log('fb_on_scroll 2');
    if (fb_Active && fb_scroll_Active && fb_near_bottom()){
//        console.log('post_table: ' + post_table);
        var rows = $(post_table).find('.post_row');
        var last_post_id = $(rows[rows.length-1]).attr('id');
        D.rpc('next_item', {},
              function(args){
                  if (!scrollRequestOutstanding) {
                      return;
                  }
                  if (!inited || myName !== currentContentName) {
                      console.log('fb_on_scroll ' + myName + ' shortcircut2: ' + currentContentName);
                      scrollRequestOutstanding = false;
                      return;
                  }

                  var dateparent = $('<div></div>');
                  dateparent.append(args.html);
                  var rows2 = dateparent.find('.post_row');

                  if (ACTIVE_FILTERS.length) {
                      rows2.each(function() {
                          if (filtered($(this))) {
                              $(this).hide();
                          }
                      });
                  }

                  fb_maybe_add_date_separators(rows, rows2);
                  html = dateparent.contents().remove();
                  html.remove();
                  dateparent.remove();
                  fb_initialize(html);
                  html.appendTo($(post_table));
                  scrollRequestOutstanding = false;
                  fb_on_scroll(post_table);
              },
              function(args) {
                  scrollRequestOutstanding = false;
              }
        );
    } else {
        //console.log('fb_on_scroll end: ' + currentContentName);
        scrollRequestOutstanding = false;
    };
//    console.log('fb_on_scroll 3');

};

function apply_filters(filters){
    ACTIVE_FILTERS = filters;
    var unfiltered = [];
    $('.post_row').each(function(){
          if (filtered($(this))) {
              $(this).hide();
          } else {
              $(this).show();
              unfiltered.push($(this).attr('id'));
          }
    });
    clear_previous_date_separators($());
    fb_maybe_add_date_separators([], $('.post_row'));
    if (ACTIVE_FILTERS.length == 1 && ACTIVE_FILTERS[0] == '__notification__') {
        fb_scroll_Active = false;
        D.notify('notifications_markRead', {'notification_ids':unfiltered});
    } else {
        fb_scroll_Active = true;
    }
    fb_do_scroll();
}

function filtered(row){
    if (!ACTIVE_FILTERS.length) {
        return false;
    }
    for (var i = 0; i < ACTIVE_FILTERS.length; i++) {
        if (row.hasClass('fb_filter_' + ACTIVE_FILTERS[i])) {
            return false;
        }
    }
    return true;
}


function _insert_separator(el, the_date, today_text, today, do_count, initial) {
    do_count = do_count || (do_count === null) || (do_count === undefined);

    var date_sep = document.createElement("span");
    $(date_sep).addClass("date-separator");
    $(date_sep).addClass("title");

    the_date = dayOfDate(the_date);
    if (today === null || today === undefined) {
        today = get_today();
    }
    var text = null;
    var is_today = the_date.valueOf() == today.valueOf();

    if (is_today) {
        $(date_sep).addClass("today");
    }

    if (initial && is_today) {
        test = null;
    } else if (!initial && is_today) {
        text = "Today";
    } else if (_isSameMonth(the_date, today) || _isLastMonth(the_date, today)) {
        if ((today.valueOf() - the_date.valueOf()) <= (1000 * 60 * 60 * 24)) {
            text = "Yesterday";
        } else {
            text = the_date.format("mmmm d");
        }
    } else {
       text = the_date.format("mmmm");
    }

   if (do_count){
       separator_count++;
   }
   if (!text) { return };
   $(date_sep).text(text);

   $(date_sep).insertBefore($(el));
}

function fb_maybe_add_date_separators(rows1, rows2, today) {
    if (today === null || today === undefined) {
        today = get_today();
    }
    var current_time_period = null;
    if (rows1.length > 0) {
        for (var j = rows1.length-1; j >= 0; j--) {
            if (filtered($(rows1[j]))) {
                continue;
            } else {
                current_time_period = relevant_time_diff(_get_timestamp(rows1[j]), today);
                break;
            }
        }
    }

    for (var i = 0; i < rows2.length; i++) {
        if (ACTIVE_FILTERS.length && filtered($(rows2[i]))) {
            continue;
        }
        var time_period = relevant_time_diff(_get_timestamp(rows2[i]), today);
        if ((!current_time_period) ||
            (time_period.valueOf() != current_time_period.valueOf())) {
             first_event_of_time_period = rows2[i];
             _insert_separator(rows2[i], time_period, TODAY_TEXT, today, false, (!current_time_period));
             current_time_period = time_period;
        }
    }
}

var fb_Active = false;
var fb_scroll_Active = true;

swapOut(function(){
    fb_Active = false;
});

swapIn(fb_initialize_swapin);
swapOut(fb_uninitialize_swapout);

function do_grant(){
    D.notify('do_grant');
}

function edit_status(){
    D.notify('edit_status');
}

function fb_false(){
    //need a way to fire link clicked event on mousedown.
//    D.rpc('link', {'href':$(this).attr('href')});
    return false;
}


function fb_do_click(){
    D.rpc('link', {'href':$(this).attr('href')});
    return false;
}

swapIn(function(){
    //console.log('in 1');
    $(".comment_button").live("mousedown", fb_comment_button_mousedown);
    //console.log('in 2');
    $(".like_button").live("mousedown", fb_false);
    $(".like_button").live("click", fb_like_button_mousedown);
    $(".dislike_button").live("mousedown", fb_false);
    $(".dislike_button").live("click", fb_dislike_button_mousedown);
    //console.log('in 3');
    $(".del_comment_link").live("mousedown", fb_false);
    $(".del_comment_link").live("click", fb_del_comment_link_mousedown);
    //console.log('in 4');
    $(".unlike_button").live("mousedown", fb_false);
    $(".unlike_button").live("click", fb_unlike_button_mousedown);
    $(".undislike_button").live("mousedown", fb_false);
    $(".undislike_button").live("click", fb_undislike_button_mousedown);

    $(".fb_filter___notification__").live("mousedown", fb_false);
    $(".fb_filter___notification__").live("click", fb_do_click);

    $(".notification_link").live("mousedown", fb_false);
    $(".notification_link").live("click", fb_do_click);

    $(".no_ondown_link").live("mousedown", fb_false);
    //console.log('in 5');
//    $(".buddyicon").live("click", fb_buddyicon_click);
    $(".do_grant").live("mousedown", fb_false);
    $(".do_grant").live("click", do_grant);
    //console.log('in 6');
    $(".edit_status").live("click", edit_status);
    //console.log('in 7');
    $("body").live("click", kill_filter_menu);
    kill_filter_menu();
});

swapOut(function(){
    //console.log('out 1');
    $(".comment_button").die("mousedown", fb_comment_button_mousedown);
    //console.log('out 2');
    $(".like_button").die("mousedown", fb_false);
    $(".like_button").die("click", fb_like_button_mousedown);
    $(".dislike_button").die("mousedown", fb_false);
    $(".dislike_button").die("click", fb_dislike_button_mousedown);
    //console.log('out 3');
    $(".del_comment_link").die("mousedown", fb_false);
    $(".del_comment_link").die("click", fb_del_comment_link_mousedown);
    //console.log('out 4');
    $(".unlike_button").die("mousedown", fb_false);
    $(".unlike_button").die("click", fb_unlike_button_mousedown);
    $(".undislike_button").die("mousedown", fb_false);
    $(".undislike_button").die("click", fb_undislike_button_mousedown);

    $(".fb_filter___notification__").die("mousedown", fb_false);
    $(".fb_filter___notification__").die("click", fb_do_click);

    $(".notification_link").die("mousedown", fb_false);
    $(".notification_link").die("click", fb_do_click);

    $(".no_ondown_link").die("mousedown", fb_false);
    //console.log('out 5');
//    $(".buddyicon").die("click", fb_buddyicon_click);
    $(".do_grant").die("mousedown", fb_false);
    $(".do_grant").die("click", do_grant);
    //console.log('out 6');
    $(".edit_status").die("click", edit_status);
    //console.log('out 7');
    $("body").die("click", kill_filter_menu);
});

swapIn(function(){
    fb_Active = true;
    if (!inited){
        fb_initialize();
        do_bind();
        inited=true;
    };
});


function kill_filter_menu(){
    fkeys = $('.filter_keys');
    if (fkeys.hasClass('filter_keys_expanded')) {
        fkeys.removeClass('filter_keys_expanded');
        fkeys.find('.filter_key').not('.active_filter_key').hide();
    }
}

function set_active_filter_node(self) {
    $(self).parents('.filter_keys').find('.filter_key').removeClass('active_filter_key').removeClass('title').addClass('major');
    $(self).addClass('active_filter_key').addClass('title').removeClass('major');
    $(self).parents('.filter_keys').removeClass('filter_keys_expanded');
    $(self).parents('.filter_keys').find('.filter_key').not('.active_filter_key').slideUp(100);
    apply_filter_key(self);
}

function apply_filter_key(self, reset) {
    var filter_key_val = $(self).find('.filter_key_val');
    var show_back_to_feed = false;
    if (!reset && filter_key_val.size() > 0) {
        var filter_text = filter_key_val.text();
        if (filter_text == "__notification__") {
            var node = $(self).parents('.facebook').find('.notifications_alert a');
            $(node).parent().hide();
            if ($(node).parents('.alert_list').find('.alert_section').size() == 1) {
                $(node).parents('.alerts').hide();
            }
        }
        apply_filters([filter_text]);
        if (filter_text != 'nf') {
            show_back_to_feed = true;
        }
    } else {
        apply_filters(['nf', '__trend__']);
    }
    if (show_back_to_feed) {
        $(self).parents('.facebook').find('.showNewsfeedToggle').show();
    } else {
        $(self).parents('.facebook').find('.showNewsfeedToggle').hide();
    }
}

function hijack_active_filter_node(self, reset) {
    $(self).parents('.filter_keys').find('.filter_key').removeClass('active_filter_key').removeClass('title').addClass('major');
    $(self).addClass('active_filter_key').addClass('title').removeClass('major').show();
    $(self).parents('.filter_keys').removeClass('filter_keys_expanded');
    $(self).parents('.filter_keys').find('.filter_key').not('.active_filter_key').hide();
    apply_filter_key(self, reset);
}

function do_bind(tree){
    if (!tree){
        tree = $();
    };
    tree.find('.filter_key').css('cursor', 'pointer');
    tree.find('.filter_key').click(
    function () {
        if ($(this).parents('.filter_keys').hasClass('filter_keys_expanded')) {
            set_active_filter_node(this);
        } else {
            $(this).parents('.filter_keys').addClass('filter_keys_expanded');
            $(this).parents('.filter_keys').find('.filter_key').slideDown(100);
        }
        return false;
    });
    //tree.find('.filter_key a').click(function (){$(this).parent().click(); return false;});

    tree.find('.notifications_alert a').click(function (){
        hijack_active_filter_node($(tree.find('.filter_key_val:contains("__notification__")')[0]).parents('.filter_key')[0]);
        return false;
    });

    tree.find('.showNewsfeedToggle').click(function (){
        hijack_active_filter_node(tree.find('.filter_key:not(:has("filter_key_val"))')[0], true);
        $(this).hide();
        return false;
    });
}

var post_table = null;

D.notify('initialize_feed'); //before binding the scroll events, though those really happen later.

function fb_do_scroll(){
    fb_on_scroll(post_table)
}

swapIn(function(){
    console.log('swapin: '+ currentContentName);
    post_table = $(document).find('.post_table')[0];
    console.log('swapin2: '+ currentContentName);
    setDesiredHeightCallback(fb_do_scroll);
    console.log('swapin3: '+ currentContentName);
    $(window).bind('scroll',fb_do_scroll);
    console.log('swapin4: '+ currentContentName);
    fb_do_scroll();
    setTimeout(fb_do_scroll, 500);
});

swapOut(function(){
    console.log('swapout: '+ currentContentName);
    $(window).unbind('scroll');
    setDesiredHeightCallback(null);
});

console.log('infobox.js: ' + currentContentName);

onHide(function () {
    var lb = window._activeLightBox;
    if (lb != null) {
        console.log('LB.DESTROY');
        lb.destroy();
    }
    kill_filter_menu();
});
