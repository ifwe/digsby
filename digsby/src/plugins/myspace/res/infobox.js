var transitionDefault = 200;

var fxAttrs = [
    // height animations
    [ "height", "marginTop", "marginBottom", "paddingTop", "paddingBottom" ],
    // width animations
    [ "width", "marginLeft", "marginRight", "paddingLeft", "paddingRight" ],
    // opacity animations
    [ "opacity" ]
];

function ms_clear_error(callback){
    error = $(".activity-data").find('.error_section');
    var do_clear = function (){
        error.html('');
        if (callback){ callback(); };
    }
    do_clear();
    if (error.css('display') === 'block'){
        error.slideUp(transitionDefault / 2);
    } else if (!error.css('display')) {
        error.css('display', 'none');
        //do_clear();
    } else {
        //do_clear();
    }
}

function genFx( type, num ){
    var obj = {};
    jQuery.each( fxAttrs.concat.apply([], fxAttrs.slice(0,num)), function(){
        obj[ this ] = type;
    });
    return obj;
}

var MS_SLIDE_UP = genFx('hide', 1);

var ms_commentFieldPadding;

$(function(){
    var t = $("<textarea/>").css({'position':'fixed', 'right':'-500px', 'bottom':'-500px'}).appendTo(document.body);
    ms_commentFieldPadding =  t.outerWidth() - t.width();
    t.remove();
})

function ms_hide_this_comment_box(self, animate) {
    if (animate === undefined)
        animate = true;

    if (self === undefined){
        alert('need self')
    } else {
        var me2 = $(self);
    }
    var comment_box_disabled = $(me2.parents(".activity-data")[0]).find('[name="comment_input"]')[0].disabled;
    if (!comment_box_disabled){
        me2.parents(".activity-data").find('.likes_comments_section').css('-webkit-user-select','none');
        var end2 = $(me2.parents(".activity-data")[0]).find(".comments_end");
        var comment_button_section = me2.parents(".activity-data").find(".comment_button_section");
        var likes_comment_section = me2.parents('.activity-data').find('.comments_section');
        var time = animate ? transitionDefault : 0;
        if (time) {
            end2.animate(MS_SLIDE_UP, {queue:false, duration:time});
            offset_top = me2.parents(".activity-data").offset().top;
            var pageYOffset = window.pageYOffset;
            var offsetHeight = document.body.offsetHeight;
            if (offset_top < pageYOffset){
                $('html, body').animate({
                    scrollTop: offset_top
                }, {queue:false, duration:time});
            }
            likes_comment_section.slideUp(time, function(){
                likes_comment_section.css('-webkit-user-select','text');
            });
            comment_button_section.show();
        } else {
            end2.hide();
            comment_button_section.show();
            likes_comment_section.hide();
            likes_comment_section.css('-webkit-user-select','text');
        }
    }
    return false;
};

function ms_error_text(self, text, error_obj, callback){
    error = $(self).parents(".activity-data").find('.error_section');
    if (error_obj !== undefined && error_obj !== null) {
        if (error_obj.error_msg) {
            text += " "  + error_obj.error_msg;
        }
        if (error_obj.permissions) {
            text += ' - <a href="javascript:null;" title="Opens a login window at myspace.com" class="do_permissions">Grant Permission</a>'
        };

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

function comments_updater(self, slide, clear_error) {
    return function(args) {
        var comments_html = $($(args.comments_html)[0]);
        var bottom_row_html = $($(args.bottom_row_html)[0]);
        comments = $(comments_html[0]).find(".comment");

        if ((comments.length) && (slide == "new")) {
            new_comment = $(comments[comments.length-1]);
            new_comment.hide();
        } else {
            new_comment = null;
        }
        bottom_row_html.find(".comment_button_section").hide();
        var old_comments_section = $(self).parents('.activity-data').find('.comments_section');
        old_comments_section.find(".likes")   .replaceWith(comments_html.find(".likes"));
        old_comments_section.find(".dislikes").replaceWith(comments_html.find(".dislikes"));
        old_comments_section.find(".comments").replaceWith(comments_html.find(".comments"));
        //only want the "Comment ()" chunk, not the "()" after likes -----v
        var old_bottom_row = $(self).parents(".activity-data").find('.bottom_row');
        $(old_bottom_row.find(".comment_button_section")[0]).replaceWith($(bottom_row_html.find(".comment_button_section")[0]));
        old_bottom_row.find(".like_link_block").replaceWith(bottom_row_html.find(".like_link_block"));
        old_bottom_row.find(".dislike_link_block").replaceWith(bottom_row_html.find(".dislike_link_block"));
        ms_init($($(self).parents(".activityItem")[0]).find(".comment_block"));
        comment_box = $($(self).parents(".form_wrapper")[0]).find("textarea[name='comment_input']");

        if (slide == "new") {
            slide_element = new_comment;
        } else if (slide == "all") {
            slide_element = comments;
        }

        if (clear_error) {
            ms_clear_error(function(){
                slide_element.slideDown(transitionDefault, function(){
                    $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                    comment_box[0].value = '';
                    comment_box[0].disabled = false;
                    comment_box.jGrow();
                });
            });
        }
        comment_box.focus();
    };
}

var ms_post_comment = function (self){
    self.disabled = true;
    var comment_box = $(self);
    var comment = $(self).attr('value');
    var post_id = $($(self).parents(".activityItem")[0]).attr('id');
    $($(self).parents(".form_wrapper")[0]).append(loader_img);
    D.rpc('post_comment', {'comment':comment, 'post_id':post_id},
            comments_updater(self, "new", true),
            function(error_obj){
                ms_error_text(comment_box, 'Error posting comment.', error_obj, function(){
                    $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                    comment_box[0].disabled = false;
                    comment_box.focus();
                });
            }
        );
    return false;
}
var ms_show_comment_box = function(self){
    var me = $(self);
    ms_clear_error();
    me.parents(".activity-data").find('.comment_button_section').hide(); // placeholder
    me.parents(".activity-data").find('.comments_section').css('-webkit-user-select','none');

    var end = me.parents(".activity-data").find(".comments_end");
    var txt;

    if (end.find(".form_wrapper").length == 0){
        end.html('<div class="form_wrapper"><textarea name="comment_input" rows="1" class="input_area expanding minor_border"/></div>');
        txt = end.find('textarea');

        var haveFocus = false;
        var blurFunc = function(animate) {
            if (!haveFocus) {
                return true;
            }
            haveFocus = false;

//            if ($(txt).parents(".post_row").hasClass('mouseover')){
//                return true;
//            }
            $(txt).unbind('keydown', 'esc');
            $(txt).unbind('keydown', 'shift+return');
            $(txt).unbind('keydown', 'return');
            
            ms_hide_this_comment_box(txt, animate);
            ms_clear_error();

            return true; //blur should continue, so that we don't keep focus and possibly trigger another blur event.
        }

        $(txt.parents('.form_wrapper')[0]).css('padding-right', ms_commentFieldPadding);

        txt.focus( function() {
            if (haveFocus) {
                return true;
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
                    ms_post_comment(this);
                } else {
                    //ms_hide_this_comment_box();
                }
                return false;
            });
            // When hiding the infobox, blur any active textboxes.
            //TODO: fix/create the necessary functions so that things that don't need to happen don't
            swapOut(function() { blurFunc(false); });
            onHide(function() { blurFunc(false); });
        });

        txt.blur(blurFunc);
    }
    txt = end.find('textarea');
//    txt.parents('.activity-data').find('.comment_block, .likes').show();
    txt.parents('.activity-data').find('.comments_section').slideDown(transitionDefault/2, function(){
        end.slideDown(transitionDefault/2, function(){
            txt.jGrow();
            txt.focus();
            //me.parents('.activity-data').find('.comments_section').show();
            me.parents(".activity-data").find('.comments_section').css('-webkit-user-select','text');
        });
    });
    txt.focus();

    comment_textfield = txt[0];
    comment_textfield.disabled = true;

    post_id = $(self).parents(".activityItem[id]").attr("id");
    D.rpc("load_comments",
          {'post_id':post_id},
          function (args) {
            comments_updater(self, "all")(args);
            comment_textfield.disabled = false;
            txt.focus();
          },
          function(error_obj){
                if (error_obj.error_msg == "no_change") {
                  comment_textfield.disabled = false;
                  txt.focus();
                  return;
                }
                ms_error_text(comment_textfield, 'Error retrieving comments.', error_obj,
                  function(){
                    $($(self).parents(".form_wrapper")[0]).find('.loader_img').remove();
                    comment_textfield.disabled = true;
                    me.parents(".activity-data").find('.comment_button_section').show();
                    txt.slideUp();
                });
            }
        );
    return false;
}

function ms_liked(like, args) {
    var me = args.me;
    var item_html = $(args['item_html']);
    ms_clear_error(function(){
        ms_init(item_html);
        me.parents('.activityItem').replaceWith(item_html);
    });
}

function ms_like_button_mousedown(e) {
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
    me.parents('.activityItem').find('.' + like + '_link_block').hide();
    var post_id = $(me.parents(".activityItem")[0]).attr('id');
    console.log("post id = " + post_id);
    D.rpc('do_' + like, {"post_id":post_id},
        function(args) {
            args.me = me;
            return ms_liked(like, args);
        },
        function(error_obj){
            var msg = 'Error adding ' + like + '.';
            ms_error_text(me, msg, error_obj, function(){
                me.parents('.activityItem').find('.' + like + '_link_block').show();
            });
        }
    );
    return false;
}

var ms_comment_button_mousedown = function(){ ms_show_comment_box(this); return true;}

function change_photo_hrefs(tree) {
 tree.find("a.Photo").each(function() {
  if ($(this).attr("context")) {
   // already been here!
   return;
  }
  var img_child = $($(this).find("img")[0])
  var img_src_small = img_child.attr("src");
  var url_parts = img_src_small.split("/");

  var filename = url_parts.pop();
  var new_filename = "l_" + filename.substr(2);
  url_parts.push(new_filename);

  var img_src_large = url_parts.join("/");

  img_child.attr("longdesc", img_src_large);
  var old_link = $(this).attr("href");
  $(this).attr("context", old_link);
  $(this).attr("href", img_src_large);

 })
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
    parentSelector: "#myspace-activities",
    onShowFunction: function(){ D.notify('hook', 'digsby.myspace.photo_seen') },
}

function lightbox_galleries(tree) {
 tree.find(".ActivityTemplateMediaGallery").each(function () {
     $(this).find("a.Photo").lightBox(LIGHTBOX_OPTIONS);
  });
}

/*
function lightbox_galleries(tree) {
 tree.find(".ActivityTemplateMediaGallery").each(function () {
     $(this).find("a.Photo > img").fullsize({forceTitleBar: true});
  });
}
*/

// image sizing
function setup_dynamic_sized_images(tree) {
        var suggested_max = 64;
        tree.find(".thumbnailImage").bind("load", function(){

            var imgs = $($(this).parents(".activityMedia")[0]).find(".thumbnailImage[complete=true]")
            var max = suggested_max;
            var extra_height = 0;
            if (imgs.length > 0){
             for (var i = 0; i < imgs.length; i++){
              img = imgs[i];
              extra_height = Math.max(img.offsetHeight - img.naturalHeight, 0);
              if (img.width > img.height) {
               max = Math.min(img.naturalHeight, Math.min(max, suggested_max));
              } else {
               max = Math.min(max,
                      Math.min(img.naturalHeight,
                       Math.max(max,
                        Math.max(Math.round(img.naturalHeight/(img.naturalWidth/suggested_max)), suggested_max))));
              }
             };
             if (max > 0) {
              imgs.css({"max-height": max + "px", "visibility":"visible"});
              $(this).parents(".activityMedia").css({"height" : (max+extra_height)+"px"});
              //$(this).parents(".activityPreviews").hide();
             }
            };
            $(this).show();
        })
};

function hide_images(tree) {
        if (!tree) tree = $();
        var pix = tree.find(".thumbnailImage");
        pix.hide();
        pix.css({'max-width':'100%'});
};

_LOCAL_TIMEZONE = (new Date()).getTimezoneOffset() * 60 * 1000; // TimezoneOffset is returned in minutes


var TODAY_TEXT = "";

function add_major_to_appActivity(tree) {
    tree.find(".activityHeader").each(function() {
       $(this).addClass("major");
    });
};

function on_click_activity_preview_toggle(e) {
 previews = $(document.getElementById(e.attributes["for"].value));

 if (previews.is(":hidden")) {
  $(e).text("-");
 } else {
  $(e).text("+");
 }

 previews.toggle();
}

function add_border_to_tables(tree){
 if (!tree) tree = $();
 tree.find("table").attr("border", 1);
}

var DIGSBY_UTM = "utm_source=Digsby&utm_medium=MID&utm_campaign=Digsby_v1";

function add_digsby_utm_to_links(tree) {
 tree.find("a").each(function() {
 var href = $(this).attr("href");
  if (href.match("^http")) {
   var newval = href;
   if (newval.indexOf("?") > -1) {
    newval += "&";
   } else {
    newval += "?";
   }
   newval += DIGSBY_UTM;
   $(this).attr("href", newval);
  }
 });
}

function near_bottom() {
    return ( window.pageYOffset >= ( document.body.offsetHeight - ( window.innerHeight * 2.0 ) ) );
}

var inited = false;
var active = false;
var scrollRequestOutstanding = false;

var myName = currentContentName;

D.notify('initialize_feed');

function ms_on_scroll() {
    if (!inited || myName !== currentContentName){
        console.log('ms_on_scroll ' + myName + ' shortcircut1: ' + currentContentName);
        return;
    }
    if (scrollRequestOutstanding){
        return;
    }
    scrollRequestOutstanding = true;
    if (!(active && near_bottom())) {
        scrollRequestOutstanding = false;
        return;
    }
    rows = $(".activityItem");
    var parent = $($(".activitiesContainer")[0]);
    var rows = parent.find(".activityItem");
    last_item_id = $(rows[rows.length-1]).attr('id');

    D.rpc('next_item',
        {},
        function (args) {
            if (!scrollRequestOutstanding)
                return;
            if (!inited || myName !== currentContentName){
                console.log('ms_on_scroll ' + myName + ' shortcircut2: ' + currentContentName);
                scrollRequestOutstanding = false;
                return;
            }
            var dateparent = $('<div></div>');
            dateparent.append(args.html);
            var rows2 = dateparent.find('.activityItem');

            ms_maybe_add_date_separators(rows, rows2);
            html = dateparent.contents().remove();
            html.remove();
            dateparent.remove();
            ms_init(html);
            html.appendTo(parent);
            scrollRequestOutstanding = false;
            on_scroll();
        },
        function (args) {
            console.log("error with rpc thing:" + args);
        }
    );
}

var on_scroll = ms_on_scroll;

_myspace_positioned_no_news = false;

swapIn(function () {
//    if (!_myspace_positioned_no_news) {
//        _myspace_positioned_no_news = true;
//        $(".no-news-today").insertBefore($(".date-separator:not(.static,.today)")[0]);
//    }
});

function destroy_lightbox() {
    var lb = window._activeLightBox;
    if (lb != null) {
        console.log('LB.DESTROY');
        lb.destroy();
    }
}


swapOut(destroy_lightbox);
onHide(destroy_lightbox);
//onHide(function() { console.log("*** myspace onHide"); });


/*

D.rpc("something", {arg1:something, arg2:something}, function (args){ success;}, function (args){error;});

*/

function do_permissions(){
    D.notify('do_permissions');
}

function ms_false() {
    return false;
}
swapIn(function(){
    active = true;
    $(".do_permissions").live("click", do_permissions);
    $(".do_permissions").live("mousedown", ms_false);
    $(".like_button").live("mousedown", ms_false);
    $(".like_button").live("click", ms_like_button_mousedown);
    $(".dislike_button").live("mousedown", ms_false);
    $(".dislike_button").live("click", ms_like_button_mousedown);

});

swapOut(function(){
    active = false;
    $(".do_permissions").die("click", do_permissions);
    $(".do_permissions").die("mousedown", ms_false);
    $(".like_button").die("mousedown", ms_false);
    $(".like_button").die("click", ms_like_button_mousedown);
    $(".dislike_button").die("mousedown", ms_false);
    $(".dislike_button").die("click", ms_like_button_mousedown);

});

//$(add_border_to_tables);
//swapOut(clear_previous_time_containers);
//swapIn(function () {add_time_containers(".activityHeader");});

function ms_maybe_add_date_separators(rows1, rows2, today) {
    if (today === null || today === undefined) {
        today = get_today();
    }
    var current_time_period = null;

    if (rows1.length > 0) {
        current_time_period = relevant_time_diff(_get_timestamp(rows1[rows1.length-1]), today);
    }

    for (var i = 0; i < rows2.length; i++) {
        var time_period = relevant_time_diff(_get_timestamp(rows2[i]), today);
        if ((!current_time_period) ||
            (time_period.valueOf() != current_time_period.valueOf())) {
             first_event_of_time_period = rows2[i];
             _insert_separator(rows2[i], time_period, TODAY_TEXT, today, false, (!current_time_period));
             current_time_period = time_period;
        }
    }
}

swapOut(function() {console.log('*** myspace SWAP OUT'); });
swapIn(function() {console.log('*** myspace SWAP IN'); });

function ms_init(tree){
    if (!tree) {
        if (inited) {
            return;
        }
        inited = true;
        tree = $();
    }
    clip_imgs(tree);
    add_major_to_appActivity(tree);
    add_digsby_utm_to_links(tree);
    change_photo_hrefs(tree);
    setup_dynamic_sized_images(tree);
    add_link_class_to_a_tags(tree);
    lightbox_galleries(tree);
    convert_timestamps_to_text(tree);
}

swapIn(ms_init)

swapIn(on_scroll);
swapIn(function() { $(window).bind('scroll', on_scroll); } );
swapIn(function() {$(".comment_button").live("mousedown", ms_comment_button_mousedown);});
swapOut(function() { $(window).unbind('scroll'); } );
swapOut(function() { $(".comment_button").die("mousedown", ms_comment_button_mousedown);} );

swapOut(ms_clear_error);
onHide(ms_clear_error);
