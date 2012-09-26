// timestamps

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

var FB_SLIDE_UP = genFx('hide', 1);

function format_time(sec, how) {
 unix = parseInt(sec);
 millis = sec * 1000;

 now = new Date();
 d = new Date(millis);

 if (how === "pretty") {
  return prettyDate(d);
 } else if (how === "smart") {
  if (Math.abs(((now.getMonth() - d.getMonth()) % 12) < 2 ) && (now.getFullYear() == d.getFullYear())) {
   return d.format("shortTime");
  } else if (d.getFullYear() != now.getFullYear()){ // not this year
   return d.format("mmmm");
  } else { // Between 1 month and 1 year old
   return d.format("mmmm d");
  }
 } else {
  return d.format(how);
 }
}
    function convert_time(sec){
        var t = new Date;
        t.setTime(parseInt(sec * 1000));
        return t.toLocaleTimeString();
    }

function do_convert_time(){
    try {
        var t = format_time($(this).attr("timestamp"), 'smart')
        $(this).text(t);
    } catch (err) {}
}
// end timestamps

// image sizing
function size_images(){
        var suggested_max = 64;
        var imgs = $($(this).parents(".messagecell")[0]).find(".picturelink[complete=true]")
        var max = suggested_max;
//        var max = 0;
        if (imgs.length > 0){
            for (var i = 0; i < imgs.length; i++){
                img = imgs[i];
                if (img.width > img.height) {
                    max = Math.min(img.naturalHeight, Math.max(max, suggested_max));
//                    max = Math.max(max, suggested_max);
                } else {
                    max = Math.min(max,
                            Math.min(img.naturalHeight,
                                    Math.max(max,
                                            Math.max(Math.round(img.naturalHeight/(img.naturalWidth/suggested_max)),
                                                    suggested_max))));
//                    max = Math.max(max, Math.max(Math.round(img.naturalHeight/(img.naturalWidth/suggested_max)), suggested_max));
                }
            };

            if (max > 0) {
                imgs.css({'max-height': max + 'px', 'visibility':'visible'});
//                for exact size
//                imgs.css("max-width", Math.round((max/img.naturalHeight)*img.naturalWidth) + "px");
            }
        };
        $(this).show();
    };
// end image sizing


function hide_this_comment_box(self, animate) {
    if (animate === undefined)
        animate = true;

    if (self === undefined){
        alert('need self')
    } else {
        var me2 = $(self);
    }
    var comment_box_disabled = $(me2.parents(".messagecell")[0]).find('[name="foo"]')[0].disabled;
    if (!comment_box_disabled){
        me2.parents(".messagecell").find('.likes_comments_section').css('-webkit-user-select','none');
        var end2 = $(me2.parents(".messagecell")[0]).find(".comments_end");
        var comment_button_section = me2.parents(".messagecell").find(".comment_button_section");
        var likes_comment_section = me2.parents('.messagecell').find('.likes_comments_section');
        var time = animate ? transitionDefault : 0;
        if (time) {
            end2.animate(FB_SLIDE_UP, {queue:false, duration:time});
            offset_top = me2.parents(".messagecell").offset().top;
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



function error_text(self, text, error_obj, callback){
    error = self.parents(".messagecell").find('.error_section');
    if (error_obj !== undefined && error_obj !== null) {
        if (error_obj.error_code){
            text += '<br/>' + error_obj.error_code + ': ';
        };
        if (error_obj.error_msg){
            text += error_obj.error_msg;
        };
        if (error_obj.grant) {
            text += ' - <a href="javascript:null;" title="Opens a login window at facebook.com" class="do_grant">Grant Permission</a>'
        };
    }

    error.html(text);
    if (error.css('display') === 'none'){
        error.slideDown(transitionDefault, callback);
    } else if (!error.css('display')) {
        error.css('display', 'block');
        if (callback){
            callback();
        };
    } else {
        if (callback){
            callback();
        };
    }
}

function fb_clear_error(self, callback){
    error = self.parents(".messagecell").find('.error_section');
    var do_clear = function (){
        error.html('');
        if (callback){ callback(); };
    }
    if (error.css('display') === 'block'){
        error.slideUp(transitionDefault / 2, do_clear);
    } else if (!error.css('display')) {
        error.css('display', 'none');
        do_clear();
    } else {
        do_clear();
    }
}

function refresh_row(params){
    params = params[0];
    var post_id = params.post_id;
    var newhtml = params.newhtml;
    var row = $($('.post_row[id="' + post_id + '"]')[0]);
    row.hide();
    row.replaceWith(newhtml);
    var row2 = $($('.post_row[id="' + post_id + '"]')[0]);
    row2.find(".time").each(function(){
        $(this).text(format_time($(this).attr("timestamp"), 'smart'));
    });
    row2.find(".picturelink").bind("load",size_images);
    row2.show();

};

function remove_comment(comment_id){
    var comment = $("#comment_" + comment_id);
    comment.slideUp((transitionDefault ? transitionDefault/2 : 0), function(){comment.remove();});
};

var commentFieldPadding;

$(function(){
    var t = $("<textarea/>").css({'position':'fixed', 'right':'-500px', 'bottom':'-500px'}).appendTo(document.body);
    commentFieldPadding =  t.outerWidth() - t.width();
    t.remove();
})

function fb_buddyicon_click(){
    var me = $(this);
    $('.post_row').not(':has(.buddyicon[src=' + me.attr('src') + '])').toggle();
}

function fb_near_bottom(){
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

