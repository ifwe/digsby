
function format_time(sec, how) {
 var unix = parseInt(sec, 10);
 var millis = sec * 1000;
 millis = (millis);

 var now = new Date();
 var d = new Date(millis);

 if (how === "pretty") {
  return prettyDate(d);
 } else if (how === "smart") {
  if (_isSameMonth(d, now) || _isLastMonth(d, now)) {
    return d.format("shortTime");
  } else if (d.getFullYear() >= (now.getFullYear() - 1)) { // this year or last year
   return d.format("mmmm d");
  } else {
   return d.format("mmmm d");
  }
 } else {
  return d.format(how);
 }
}

function convert_timestamps_to_text(tree) {
 if (!tree) { tree = $(); }

 var _do_convert = function(node) {
   if (node === parseInt(node,10)) {
    node = $(this);
   } else {
    node = $(node);
   }
   var tx_text = null;
   try {

     ts_text = format_time(node.attr("timestamp"), node.attr("timestyle"));
   } catch (e) {
       console.log("error formatting text:" + e + "/" + node.attr("timestamp"));
   }

   try {
     node.find(".time-container").text(ts_text);
   } catch (e) {
       console.log("error attaching text:" + e);
   }
  }

 if (tree.attr("timestamp")) _do_convert(tree);
 else tree.find("[timestamp]").each(_do_convert);
}

function get_today() {
  return dayOfDate(new Date());
}

function _isSameMonth(t1, t2) {
    if (!t2) {
        t2 = new Date();
    }

    return ((t1.getFullYear() == t2.getFullYear()) && (t1.getMonth() == t2.getMonth()));
}

function _isLastMonth(t1, sinceWhen) {
    if (!sinceWhen) {
        sinceWhen = new Date();
    }

    t1 = dayOfDate(t1);
    t2 = dayOfDate(sinceWhen);

    t2.setDate(0);
    t2 = new Date(t2.valueOf() - 1);
    // t2 is now the last millisecond of the previous month

    return _isSameMonth(t1, t2);
}

function relevant_time_diff(t1, t2) {
    // Return a timestamp with granularity appropriate for the difference between
    // the two provided timestamps.
    t1 = dayOfDate(t1);
    if (!t2) t2 = new Date();
    t2 = dayOfDate(t2);

    var t1v = t1.valueOf();
    var t2v = t2.valueOf();

    var diff_v = t2v - t1v;

    // was it in the same day?
    if (diff_v === 0) {
        return t1;
    // yesterday?
    } else if (diff_v <= (1000 * 60 * 60 * 24)) {
        return t1;
    } else if (_isSameMonth(t1, t2)) {
        return t1;
    // last month?
    } else if (_isLastMonth(t1, t2)) {
        // timeframe is the first of the month
        return t1;
    } else if (t1.getFullYear() >= (t2.getFullYear() - 1)) {
        t1.setDate(1)
        return t1;
    } else {
        // timeframe is first of january
        t1.setMonth(0);
        t1.setDate(1); // this must be the fabled "poor date handling" in javascript. starts at 1?
        return t1;
    }
}

function _get_timestamp(el) {
  return new Date(parseInt($(el).attr("timestamp"), 10)*1000);
}

var separator_count = 0;
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

    if (today_text === null || today_text === undefined){
        today_text = TODAY_TEXT;
    }

    if (do_count && (separator_count === 0) && today_text) {
        text = today_text || TODAY_TEXT;
    } else if ((!do_count) && initial && today_text) {
        text = today_text || TODAY_TEXT;
    } else if (is_today) {
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

function add_date_separators(selector, do_count, initial) {
 if ($(".date-separator:not(.static)").length) return; // don't add date seperators more than once.
 // Get the last time that's still today (i.e. tomorrow - 1)
 var today = get_today();
 var first_event_of_time_period = null;
 var current_time_period = null;

 var acts = $(selector);
 for (var i = 0; i < acts.length; i++) {
   var ts = _get_timestamp(acts[i]);
   if (!ts) continue;
   var time_period = relevant_time_diff(ts, today);
   if ((!current_time_period) ||
       (time_period.valueOf() != current_time_period.valueOf())) {
    first_event_of_time_period = acts[i];
    current_time_period = time_period;
    _insert_separator(acts[i],
           //time_period,
           _get_timestamp(acts[i]),
           undefined, undefined, do_count, initial);
   }
 }
}

function clear_previous_date_separators(tree) {
 if (!tree){
        tree = $();
 };
 separator_count = 0;
 to_remove = tree.find(".date-separator:not(.static)");
 if (to_remove) to_remove.remove();
}

function add_time_containers(to_what) {
 $(to_what).each(function() {
  var myspan = document.createElement("span");
  $(myspan).addClass("time-container");
  $(myspan).addClass("minor");
  $(this).append(" ");
  $(this).after(myspan);
 });
}

function clear_previous_time_containers() {
 $(".time-container").remove();
}

function add_link_class_to_a_tags(tree) {
 if (!tree) { tree = $(); }
 tree.find("a").each(function(){
     $(this).addClass("link");
 });
}

var DIGSBY_LIB_CLASS = 'digsbylib';

if (window.digsbyLoadedLibs === undefined){
    window.digsbyLoadedLibs = {};
}

function ensureLibrariesLoaded(libraries) {
    var head = document.getElementsByTagName('head')[0];

    jQuery.each(libraries, function (i, libsrc) {
        if (!digsbyLoadedLibs[libsrc]) {
            console.log('loading script:' + libsrc);
            $(head).append('<script type="text/javascript" src="' + libsrc + '"/>');
            digsbyLoadedLibs[libsrc] = true;
        }
    });
}

var contentFragments = {};
var currentContentName = undefined;
function contentContainer() {
    return document.getElementById('digsby_app_content');
}

/**
 * Swap visible content to the one keyed by contentName.
 *
 * updateContent(contentName) must have been called prior.
 */

function swapToContent(contentName) {
    var container = contentContainer();

    if (currentContentName === contentName) {
        console.log('ignoring swapToContent("' + contentName + '") because it is currently active');
        return;
    }

    if (!contentFragments[contentName]) {
        console.log('ERROR: "' + contentName + '" content does not exist');
        return;
    }

    console.log('switching to content: ' + contentName + ' from: ' + currentContentName);

    // store current content in contentFragments
    callSwapOut(currentContentName);
    var fragment = document.createDocumentFragment();
    while (container.childNodes.length)
        fragment.appendChild(container.removeChild(container.firstChild));
    contentFragments[currentContentName] = fragment;
    var switchToNodes = contentFragments[contentName];

    while (switchToNodes.childNodes.length)
        container.appendChild(switchToNodes.removeChild(switchToNodes.firstChild));
    // switch to new content
    currentContentName = contentName;
    callSwapIn(contentName);
    console.log('switched to content: ' + contentName);

}

/**
 * functions for infobox.js clients to register "swap" functions that get called
 * when their content is being swapped in or out.
 */

var _swapFunctions = {};

function callSwapIn(name) {
    if (name in _swapFunctions)
        jQuery.each(_swapFunctions[name]['in'], function (i, f) { f(); });
}

function callSwapOut(name) {
    if (name in _swapFunctions)
        jQuery.each(_swapFunctions[name]['out'], function (i, f) { f(); });
}

function maybeCreateSwapDelegates(name) {
    if (!(name in _swapFunctions))
        _swapFunctions[name] = {'in': [], 'out': []};
}

function swapIn(func) {
    maybeCreateSwapDelegates(currentContentName);
    _swapFunctions[currentContentName]['in'].push(func);
}

function swapOut(func) {
    maybeCreateSwapDelegates(currentContentName);
    _swapFunctions[currentContentName]['out'].push(func);
}

/**
 * onHide: registers a function to be called when the infobox is hiding,
 * or when the current app content is being swapped out.
 */
var _onHide = [];

function onHide(func) {
    _onHide.push(func);
}

function callOnHide() {
    window.scroll(0, 0);
    jQuery.each(_onHide, function (i, f) { f(); });
}

function clearOnHide() {
    _onHide = [];
}

function jq_init_scripts(node){
    jQuery(node).find('script').each(function(_i, elem){
        jQuery.globalEval( elem.text || elem.textContent || elem.innerHTML || "" );
        if ( elem.parentNode )
            elem.parentNode.removeChild( elem );
    });
}

/**
 * Updates the content keyed by contentName with new data.
 *
 * Content can be HTML or a DocumentFragment.
 */
function updateContent(contentName, content) {
    console.log('updateContent start: ' + contentName);
    // clear swap functions

    if (currentContentName === contentName) {
        callSwapOut(currentContentName);
        updateCurrentContent(content);
        delete _swapFunctions[contentName];
        console.log('updateContent end1: ' + contentName);
        return;
    }

    delete _swapFunctions[contentName];


    if (contentFragments[contentName]){
        while (contentFragments[contentName].childNodes.length)
            jQuery(contentFragments[contentName].removeChild(contentFragments[contentName].firstChild)).remove();
        jQuery(contentFragments[contentName]).remove();
    }
    var newContent = document.createElement('div');
    if (typeof content === 'string') {
        console.log('updateContent(string of length ' + content.length + ')');
    } else {
        console.log('updateContent(node of length ' + content.length + ')');
    }
    if (typeof content === 'string')
        newContent.innerHTML = content;
    else
        newContent.appendChild(content);

    jq_init_scripts(newContent);
    var fragment = document.createDocumentFragment();

    while (newContent.childNodes.length)
        fragment.appendChild(newContent.removeChild(newContent.firstChild));

    contentFragments[contentName] = fragment;
    console.log('updateContent end2: ' + contentName);
}

/**
 * Updates the currently shown content with HTML or a DocumentFragment.
 */
function updateCurrentContent(content) {
    console.log('updateCurrentContent start');
    var container = contentContainer();
    while (container.childNodes.length)
        jQuery(container.removeChild(container.firstChild)).remove();

    if (typeof content === 'string') {
        console.log('updateCurrentContent(string of length ' + content.length + ')');
    } else
        console.log('updateCurrentContent(node of length ' + content.length + ')');
    var newContent = document.createElement('div');
    if (typeof content === 'string')
        newContent.innerHTML = content;
    else
        newContent.appendChild(content);

    jq_init_scripts(newContent);

    while (newContent.childNodes.length)
        container.appendChild(newContent.removeChild(newContent.firstChild));

    console.log('updateCurrentContent end');
}

/**
 * Returns the DocumentFragment for contentName.
 */
function getContent(contentName) {
    return contentFragments[contentName];
}

/**
 * Export a function called callWithInfoboxOnLoad which replaces $
 * with a fake onload register function that is immediately called after.
 */
(function() {
    var _jq = window.$;
    var callbacks = [];
    var onLoad = function(func) { callbacks.push(func); };
    var fake$ = function(selector, context) {
        return _jq.isFunction(selector) && !context ? onLoad(selector) : _jq(selector, context);
    };
    this.callWithInfoboxOnLoad = function(func) {
        window.$ = fake$;
        try { func(); }
        finally { $ = _jq; }
        for (var i = 0; i < callbacks.length; ++i)
            callbacks[i]();
        callbacks.length = 0;
    };
})();

function setDesiredHeightCallback(cb){
    window.desired_height_callback = cb;
}

function setInfoboxDesiredHeight(size) {
    window.digsby_infobox_desired_height = size;
    window.desired_height_callback();
}

function setViewport(img, dim) {
    var width = img.naturalWidth;
    var height = img.naturalHeight;
    var w = width;
    var h = height;

    if (width < 0 | height < 0){
        return;
    }

    if (width > height){
        if (height > dim) {
            img.height = dim;
        }
        height = img.height;
        width = img.width = w/h * height;
        x = (width - dim) / 2;
        y = (height - dim) / 2;
    } else {
        if (width > dim) {
            img.width = dim;
        }
        width = img.width;
        height = img.height = h/w * width;
        y = (height/3) - dim;
        x = 0;
    }

    width = height = dim;
    if (y < 0) {
        y = 0;
    }
    if (x < 0) {
        x = 0;
    }

    img.style.left = "-" + x + "px";
    img.style.top  = "-" + y + "px";

    if (width !== undefined) {
        $(img).parents()[0].style.width  = width  + "px";
        $(img).parents()[0].style.height = height + "px";
    }
}

function clip_imgs(tree){
    tree.find(".clipped").each(function(){
        $(this).load(function(){
            setViewport(this, 48);
        })
    });
    tree.find(".clipped-small").each(function(){
        $(this).load(function(){
            setViewport(this, 32);
        })
    });
}

