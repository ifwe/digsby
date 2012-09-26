
function AssertionError(message) { this.message = message; }
AssertionError.prototype.toString = function() { return 'AssertionError(' + this.message + ')'; };
function assert(x, message) { if (!x) throw new AssertionError(message || ''); }

function urlQuery(url, args, do_escape) {
    do_escape = (do_escape === undefined ? true : do_escape);
    var pairs = [];
    for (var k in args)
        pairs.push(k + '=' + (do_escape ? escape(args[k]) : args[k]));

    var questionMark = url.search('?') == -1 ? '?' : '';
    return url + questionMark + pairs.join('&');
}

/*
 * JavaScript Pretty Date
 * Copyright (c) 2008 John Resig (jquery.com)
 * Licensed under the MIT license.
 */
// Takes an ISO time and returns a string representing how
// long ago the date represents.
function dateDiff(time1, time2) {

    if (typeof(time1) == typeof("")){
      var date = new Date((time1 || "").replace(/-/g,"/").replace(/[TZ]/g," "))
    } else {
      var date = new Date(time1);
    }

    time2 = time2 || new Date();

    return ((time2.getTime() - date.getTime()) / 1000);
}

function dayOfDate(date) {
 var day = new Date(date);
 day.setMilliseconds(0);
 day.setSeconds(0);
 day.setMinutes(0);
 day.setHours(0);
 return day;
}

function prettyDate(time){
    var diff = dateDiff(time),
        day_diff = Math.floor(diff / 86400);

    if ( isNaN(day_diff) || day_diff < 0 )
        return;

    return day_diff == 0 && (
            diff < 60 && "just now" ||
            diff < 120 && "1 minute ago" ||
            diff < 3600 && Math.floor( diff / 60 ) + " minutes ago" ||
            diff < 7200 && "1 hour ago" ||
            diff < 86400 && Math.floor( diff / 3600 ) + " hours ago") ||
        day_diff == 1 && "Yesterday" ||
        day_diff < 7 && day_diff + " days ago" ||
        day_diff < 31 && Math.ceil( day_diff / 7 ) + " weeks ago" ||
                day_diff < 365 && Math.ceil( day_diff / 30) + " months ago" ||
                Math.ceil( day_diff / 365) + " years ago";
}

function linkify(string, options) {
    if (!options) options = {};
    if (!options.limit) options.limit = 100;
    if (!options.tagFill) options.tagFill = '';

    var regex = /((http\:\/\/|https\:\/\/|ftp\:\/\/)|(www\.))+(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/gi;

    string = string.replace(regex, function(value) {
        value = value.toLowerCase();
        var m = value.match(/^([a-z]+:\/\/)/), nice, url;
        if (m) {
            nice = value.replace(m[1],'');
            url = value;
        } else {
            nice = value;
            url = 'http://' + nice;
        }

        return '<a href="' + url + '"' + (options.tagFill != '' ? (' ' + options.tagFill) : '')+ '>' + linkifyLabel(/*nice*/url, options.limit) + '</a>';
    });

    return string;
}


function linkifyLabel(text, limit) {
    if (!limit) return text;

    if (text.length > limit) {
        return text.substr(0, limit - 3) + '...';
    }

    return text;
}
