
function useStringIdentifiers(obj, properties) {
    for (var i = 0; i < properties.length; ++i)
        useStringIdentifier(obj, properties[i]);
}

// adaptive function for the new string IDs for Twitter API objects (Snowflake)
function useStringIdentifier(obj, property) {
  var property_str = property + "_str";
  if (!obj) {
   return;
  }

  if (obj[property_str]) {
    obj[property] = obj[property_str].toString();
    delete obj[property_str];
  } else if (obj[property]) {
    obj[property] = obj[property].toString();
  }
}

function shallowCopy(obj) {
    var o = {};
    for (var k in obj)
        o[k] = obj[k];
    return o;
}
function last(array) {
    return array[array.length-1];
}

function get(obj, attr, def) {
    if (typeof obj === 'undefined')
        return def;
    else
        var val = obj[attr];
        return typeof val === 'undefined' ? def : val;
}

function sum(array, start) {
    if (typeof start === 'undefined')
        start = 0;
    for (var i = array.length-1; i >= 0; --i) start += array[i];
    return start;
}

function joinSingleQuotedStringArray(arr, joinStr) {
    var res = "";
    for (var i = 0; i < arr.length; ++i) {
        res += "'" + arr[i] + "'";
        if (i != arr.length - 1)
            res += joinStr;
    }
    return res;
}

function arraysEqual(a, b, cmp) {
    if (a.length !== b.length)
        return false;

    for (var i = 0; i < a.length; ++i) {
        if (cmp(a[i], b[i]) !== 0)
            return false;
    }

    return true;
}

function isSorted(a, sortFunc) {
    var copy = Array.apply(null, a);
    copy.sort(sortFunc);
    return arraysEqual(a, copy, sortFunc);
}

function objectLength(self) {
    var count = 0;
    for (var key in self)
        ++count;
    return count;
}

function objectKeys(self) {
    assert(self !== undefined);
    var keys = [];
    for (var key in self)
        keys.push(key);
    return keys;
}

function objectValues(self) {
    assert(self !== undefined);
    var values = [];
    for (var key in self)
        values.push(self[key]);
    return values;
}

/**
 * Inserts the items in array2 into array at pos. If pos is not given, the
 * elements are inserted at the end.
 */
function arrayExtend(array, array2, pos) {
    if (pos === undefined)
        pos = array.length;

    array.splice.apply(array, [pos, 0].concat(array2));
}

Function.prototype.inheritsFrom = function(superClass, functions) {
    var proto = this.prototype = new superClass();
    proto.constructor = this;
    if (functions)
        $.extend(proto, functions);
};


function AssertionError(message) { this.message = message; }
AssertionError.prototype.toString = function() { return 'AssertionError(' + this.message + ')'; };

function assert(x, message) {
    if (!x) {
        console.error('ASSERT FAILED: ' + (message || ''));
        printStackTrace();
        throw new AssertionError(message || '');
    }
}

/**
 * given an Array, makes an Object where each element in the array is a key with a value of true
 */
function set(seq) {
    var set = {};
    for (var i = seq.length - 1; i >= 0; --i)
        set[seq[i]] = true;
    return set;
}

function setsEqual(a, b) {
    for (var key in a)
        if (!(key in b))
            return false;
    for (var key in b)
        if (!(key in a))
            return false;
    return true;
}

function urlQuery(url, args, do_escape) {
    do_escape = (do_escape === undefined ? true : do_escape);
    var pairs = [];
    for (var k in args)
        pairs.push(k + '=' + (do_escape ? encodeURIComponent(args[k]) : args[k]));

    var separator = url.search(/\?/) == -1 ? '?' : '&';
    return url + separator + pairs.join('&');
}

/**
 * Turns '?key=value&foo' into {key: 'value', foo: true}
 */
function queryParse(query) {
    if (query.indexOf('?') === 0)
        query = query.substring(1);

    query = query.split('&');
    var args = {};

    for (var i = 0; i < query.length; ++i) {
        var arg = query[i];
        var j = arg.indexOf('=');
        var key, value;
        if (j == -1) {
            key = arg;
            value = true;
        } else {
            key = arg.substring(0, j);
            value = arg.substring(j + 1);
        }

        args[key] = value;
    }

    return args;
}

/*
 * JavaScript Pretty Date
 * Copyright (c) 2008 John Resig (jquery.com)
 * Licensed under the MIT license.
 */
// Takes an ISO time and returns a string representing how
// long ago the date represents.
function prettyDate(time){
	var date = new Date((time || "").replace(/-/g,"/").replace(/[TZ]/g," ")),
		diff = (((new Date()).getTime() - date.getTime()) / 1000),
		day_diff = Math.floor(diff / 86400);
			
	if ( isNaN(day_diff) || day_diff < 0 )
		return 'just now';//longDateFormat(date);
			
	return day_diff === 0 && (
			diff < 60 && "just now" ||
			diff < 120 && "1 minute ago" ||
			diff < 3600 && Math.floor( diff / 60 ) + " minutes ago" ||
			diff < 7200 && "1 hour ago" ||
			diff < 86400 && Math.floor( diff / 3600 ) + " hours ago") ||
		day_diff === 1 && "Yesterday" ||
		day_diff < 7 && day_diff + " days ago" ||
	    Math.ceil( day_diff / 7 ) + " weeks ago";
}

function longDateFormat(date) {
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

function uniquify(seq, key) {
    var seen = {};
    var items = [];
    for (var i = 0; i < seq.length; ++i) {
        var k = key(seq[i]);
        if (!(k in seen)) {
            seen[k] = true;
            items.push(seq[i]);
        }
    }

    return items;
}

function all(seq) {
    for (var i = 0; i < seq.length; ++i) {
        if (!seq[i])
            return false;
    }

    return true;
}

function binarySearch(o, v, key) {
    /*
     * o: an ordered Array of elements
     * v: the value to search for
     * key: an optional key function
     *
     * thanks http://jsfromhell.com/array/search
     */
    if (key === undefined) key = function(o) { return o; };
    var vkey = key(v);
    var h = o.length, l = -1, m;

    while(h - l > 1)
        if (key(o[m = h + l >> 1]) < vkey) l = m;
        else h = m;

    return h;
};

function stackTrace() {
    var curr  = arguments.callee.caller,
        FUNC  = 'function', ANON = "{anonymous}",
        fnRE  = /function\s*([\w\-$]+)?\s*\(/i,
        stack = [],j=0,
        fn,args,i;

    var count = 0;
    while (curr && count++ < 40) {
        fn    = fnRE.test(curr.toString()) ? RegExp.$1 || ANON : ANON;
        if (fn === ANON)
            fn = curr.toString();
        args  = stack.slice.call(curr.arguments);
        i     = args.length;

        while (i--) {
            switch (typeof args[i]) {
                case 'string'  : args[i] = '"'+args[i].replace(/"/g,'\\"')+'"'; break;
                case 'function': args[i] = FUNC; break;
            }
        }

        stack[j++] = fn + '(' + args.join().toString().slice(0, 80) + ')';
        stack[j++] = '--------------------------------';
        curr = curr.caller;
    }

    return stack;
}

function printStackTrace() {
    console.error(stackTrace().join('\n'));
}

function printException(e) {
    console.error(e.name + ' ' + e.sourceURL + '(' + e.line + '): ' + e.message);
}

function guard(f) {
    try {
        f();
    } catch (err) {
        printStackTrace();
        printException(err);
    }
}

function callEach(seq, funcName) {
    var args = Array.apply(null, arguments);
    var results = [];
    args.shift();
    args.shift();

    $.each(seq, function (i, obj) {
        results.push(obj[funcName].apply(obj, args));
    });

    return results;
}


// Mozilla 1.8 has support for indexOf, lastIndexOf, forEach, filter, map, some, every
// http://developer-test.mozilla.org/docs/Core_JavaScript_1.5_Reference:Objects:Array:lastIndexOf
function arrayIndexOf (array, obj, fromIndex) {
    if (fromIndex == null) {
        fromIndex = 0;
    } else if (fromIndex < 0) {
        fromIndex = Math.max(0, array.length + fromIndex);
    }
    for (var i = fromIndex; i < array.length; i++) {
        if (array[i] === obj)
            return i;
    }
    return -1;
};

function arrayRemove(array, obj) {
	var i = arrayIndexOf(array, obj);
	if (i != -1) {
		array.splice(i, 1);
        return true;
    }

    return false;
};

(function($){

	var $preload = $.preload = function( original, settings ){
		if( original.split ) // selector
			original = $(original);

		settings = $.extend( {}, $preload.defaults, settings );
		var sources = $.map( original, function( source ){
			if( !source ) 
				return; // skip
			if( source.split ) // URL Mode
				return settings.base + source + settings.ext;
			var url = source.src || source.href; // save the original source
			if( typeof settings.placeholder == 'string' && source.src ) // Placeholder Mode, if it's an image, set it.
				source.src = settings.placeholder;
			if( url && settings.find ) // Rollover mode
				url = url.replace( settings.find, settings.replace );
			return url || null; // skip if empty string
		});

		var data = {
			loaded:0, // how many were loaded successfully
			failed:0, // how many urls failed
			next:0, // which one's the next image to load (index)
			done:0, // how many urls were tried
			/*
			index:0, // index of the related image			
			found:false, // whether the last one was successful
			*/
			total:sources.length // how many images are being preloaded overall
		};
		
		if( !data.total ) // nothing to preload
			return finish();
		
		var imgs = $(Array(settings.threshold+1).join('<img/>'))
			.load(handler).error(handler).bind('abort',handler).each(fetch);
		
		function handler( e ){
			data.element = this;
			data.found = e.type == 'load';
			data.image = this.src;
			data.index = this.index;
			var orig = data.original = original[this.index];
			data[data.found?'loaded':'failed']++;
			data.done++;

			// This will ensure that the images aren't "un-cached" after a while
			if( settings.enforceCache )
				$preload.cache.push( 
					$('<img/>').attr('src',data.image)[0]
				);

			if( settings.placeholder && orig.src ) // special case when on placeholder mode
				orig.src = data.found ? data.image : settings.notFound || orig.src;
			if( settings.onComplete )
				settings.onComplete( data );
			if( data.done < data.total ) // let's continue
				fetch( 0, this );
			else{ // we are finished
				if( imgs && imgs.unbind )
					imgs.unbind('load').unbind('error').unbind('abort'); // cleanup
				imgs = null;
				finish();
			}
		};
		function fetch( i, img, retry ){
			// IE problem, can't preload more than 15
			if( img.attachEvent /* msie */ && data.next && data.next % $preload.gap == 0 && !retry ){
				setTimeout(function(){ fetch( i, img, true ); }, 0);
				return false;
			}
			if( data.next == data.total ) return false; // no more to fetch
			img.index = data.next; // save it, we'll need it.
			img.src = sources[data.next++];
			if( settings.onRequest ){
				data.index = img.index;
				data.element = img;
				data.image = img.src;
				data.original = original[data.next-1];
				settings.onRequest( data );
			}
		};
		function finish(){
			if( settings.onFinish )
				settings.onFinish( data );
		};
	};

	 // each time we load this amount and it's IE, we must rest for a while, make it lower if you get stack overflow.
	$preload.gap = 14; 
	$preload.cache = [];
	
	$preload.defaults = {
		threshold:2, // how many images to load simultaneously
		base:'', // URL mode: a base url can be specified, it is prepended to all string urls
		ext:'', // URL mode:same as base, but it's appended after the original url.
		replace:'' // Rollover mode: replacement (can be left empty)
		/*
		enforceCache: false, // If true, the plugin will save a copy of the images in $.preload.cache
		find:null, // Rollover mode: a string or regex for the replacement
		notFound:'' // Placeholder Mode: Optional url of an image to use when the original wasn't found
		placeholder:'', // Placeholder Mode: url of an image to set while loading
		onRequest:function( data ){ ... }, // callback called every time a new url is requested
		onComplete:function( data ){ ... }, // callback called every time a response is received(successful or not)
		onFinish:function( data ){ ... } // callback called after all the images were loaded(or failed)
		*/
	};

	$.fn.preload = function( settings ){
		$preload( this, settings );
		return this;
	};

})(jQuery);


function cmp(a, b) {
    if (a < b)
        return -1;
    else if (b < a)
        return 1;
    else
        return 0;
}

function cmpByKey(key, a, b) {
    return function(a, b) { return cmp(a[key], b[key]); };
}

function pp(obj) {
    var s = [];
    for (var key in obj)
        s.push(key + ': ' + obj[key]);

    console.log('{' + s.join(', ') + '}');
}

/*!
 * linkify - v0.3 - 6/27/2009
 * http://benalman.com/code/test/js-linkify/
 * 
 * Copyright (c) 2009 "Cowboy" Ben Alman
 * Licensed under the MIT license
 * http://benalman.com/about/license/
 * 
 * Some regexps adapted from http://userscripts.org/scripts/review/7122
 */

// Turn text into linkified html.
// 
// var html = linkify( text, options );
// 
// options:
// 
//  callback (Function) - default: undefined - if defined, this will be called
//    for each link- or non-link-chunk with two arguments, text and href. If the
//    chunk is non-link, href will be omitted.
// 
//  punct_regexp (RegExp | Boolean) - a RegExp that can be used to trim trailing
//    punctuation from links, instead of the default.
// 
// This is a work in progress, please let me know if (and how) it fails!

window.linkify = (function(){
  var
    PROTOCOLS = 'ftp|https?|gopher|msnim|icq|telnet|nntp|aim|file|svn',
    SCHEME = "(?:" + PROTOCOLS + ")://",
    IPV4 = "(?:(?:[0-9]|[1-9]\\d|1\\d{2}|2[0-4]\\d|25[0-5])\\.){3}(?:[0-9]|[1-9]\\d|1\\d{2}|2[0-4]\\d|25[0-5])",
    HOSTNAME = "(?:(?:[^\\s!@#$%^&*()_=+[\\]{}\\\\|;:'\",.<>/?]+)\\.)+",
    TLD = "(?:ac|ad|aero|ae|af|ag|ai|al|am|an|ao|aq|arpa|ar|asia|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|biz|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|cat|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|coop|com|co|cr|cu|cv|cx|cy|cz|de|dj|dk|dm|do|dz|ec|edu|ee|eg|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gov|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|info|int|in|io|iq|ir|is|it|je|jm|jobs|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mil|mk|ml|mm|mn|mobi|mo|mp|mq|mr|ms|mt|museum|mu|mv|mw|mx|my|mz|name|na|nc|net|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|org|pa|pe|pf|pg|ph|pk|pl|pm|pn|pro|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|st|su|sv|sy|sz|tc|td|tel|tf|tg|th|tj|tk|tl|tm|tn|to|tp|travel|tr|tt|tv|tw|tz|ua|ug|uk|um|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|xn--0zwm56d|xn--11b5bs3a9aj6g|xn--80akhbyknj4f|xn--9t4b11yi5a|xn--deba0ad|xn--g6w251d|xn--hgbk6aj7f53bba|xn--hlcj6aya9esc7a|xn--jxalpdlp|xn--kgbechtv|xn--zckzah|ye|yt|yu|za|zm|zw)",
    HOST_OR_IP = "(?:" + HOSTNAME + TLD + "|" + IPV4 + ")",
    PATH = "(?:[;/][^#?<>\\s]*)?",
    QUERY_FRAG = "(?:\\?[^#<>\\s]*)?(?:#[^<>\\s\\u3000]*)?", // include \\u3000 here and in the line below--webkit's js engine does not for \s
    URI1 = "\\b" + SCHEME + "[^<>\\s\\u3000]+",
    URI2 = "\\b" + HOST_OR_IP + PATH + QUERY_FRAG + "(?!\\w)",
    
    MAILTO = "mailto:",
    EMAIL = "(?:" + MAILTO + ")?[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@" + HOST_OR_IP + QUERY_FRAG + "(?!\\w)",
    
    URI_RE = new RegExp( "(?:" + URI1 + "|" + URI2 + "|" + EMAIL + ")", "ig" ),
    SCHEME_RE = new RegExp( "^" + SCHEME, "i" ),
    
    quotes = {
      "'": "`",
      '>': '<',
      ')': '(',
      ']': '[',
      '}': '{',
      '»': '«',
      '›': '‹'
    },
    
    default_options = {
      callback: function( text, href ) {
        return href ? '<a href="' + href + '" title="' + href + '">' + text + '<\/a>' : text;
      },
      punct_regexp: /(?:[!?.,:;'"]|(?:&|&amp;)(?:lt|gt|quot|apos|raquo|laquo|rsaquo|lsaquo);)$/
    };
  
  return function( txt, options ) {
    if (!txt) return '';
    options = options || {};
    
    // Temp variables.
    var arr,
      i,
      link,
      href,
      
      // Output HTML.
      html = '',
      
      // Store text / link parts, in order, for re-combination.
      parts = [],
      
      // Used for keeping track of indices in the text.
      idx_prev,
      idx_last,
      idx,
      link_last,
      
      // Used for trimming trailing punctuation and quotes from links.
      matches_begin,
      matches_end,
      quote_begin,
      quote_end;
    
    // Initialize options.
    for ( i in default_options ) {
      if ( options[ i ] === undefined ) {
        options[ i ] = default_options[ i ];
      }
    }
    
    // Find links.
    while ( arr = URI_RE.exec( txt ) ) {
      
      link = arr[0];
      idx_last = URI_RE.lastIndex;
      idx = idx_last - link.length;
      
      // Not a link if preceded by certain characters.
      if ( /[\/:]/.test( txt.charAt( idx - 1 ) ) ) {
        continue;
      }
      
      // Trim trailing punctuation.
      do {
        // If no changes are made, we don't want to loop forever!
        link_last = link;
        
        quote_end = link.substr( -1 )
        quote_begin = quotes[ quote_end ];
        
        // Ending quote character?
        if ( quote_begin ) {
          matches_begin = link.match( new RegExp( '\\' + quote_begin + '(?!$)', 'g' ) );
          matches_end = link.match( new RegExp( '\\' + quote_end, 'g' ) );
          
          // If quotes are unbalanced, remove trailing quote character.
          if ( ( matches_begin ? matches_begin.length : 0 ) < ( matches_end ? matches_end.length : 0 ) ) {
            link = link.substr( 0, link.length - 1 );
            idx_last--;
          }
        }
        
        // Ending non-quote punctuation character?
        if ( options.punct_regexp ) {
          link = link.replace( options.punct_regexp, function(a){
            idx_last -= a.length;
            return '';
          });
        }
      } while ( link.length && link !== link_last );
      
      href = link;
      
      // Add appropriate protocol to naked links.
      if ( !SCHEME_RE.test( href ) ) {
        href = ( href.indexOf( '@' ) !== -1 ? ( !href.indexOf( MAILTO ) ? '' : MAILTO )
          : !href.indexOf( 'irc.' ) ? 'irc://'
          : !href.indexOf( 'ftp.' ) ? 'ftp://'
          : 'http://' )
          + href;
      }
      
      // Push preceding non-link text onto the array.
      if ( idx_prev != idx ) {
        parts.push([ txt.slice( idx_prev, idx ) ]);
        idx_prev = idx_last;
      }
      
      // Push massaged link onto the array
      parts.push([ link, href ]);
    };
    
    // Push remaining non-link text onto the array.
    parts.push([ txt.substr( idx_prev ) ]);
    
    // Process the array items.
    for ( i = 0; i < parts.length; i++ ) {
      html += options.callback.apply( window, parts[i] );
    }
    
    // In case of catastrophic failure, return the original text;
    return html || txt;
  };
  
})();

// t: current time, b: begInnIng value, c: change In value, d: duration
jQuery.easing['jswing'] = jQuery.easing['swing'];

jQuery.extend( jQuery.easing,
{
	def: 'easeOutQuad',
	swing: function (x, t, b, c, d) {
		//alert(jQuery.easing.default);
		return jQuery.easing[jQuery.easing.def](x, t, b, c, d);
	},
	easeInQuad: function (x, t, b, c, d) {
		return c*(t/=d)*t + b;
	},
	easeOutQuad: function (x, t, b, c, d) {
		return -c *(t/=d)*(t-2) + b;
	},
	easeInOutQuad: function (x, t, b, c, d) {
		if ((t/=d/2) < 1) return c/2*t*t + b;
		return -c/2 * ((--t)*(t-2) - 1) + b;
	},
	easeInCubic: function (x, t, b, c, d) {
		return c*(t/=d)*t*t + b;
	},
	easeOutCubic: function (x, t, b, c, d) {
		return c*((t=t/d-1)*t*t + 1) + b;
	},
	easeInOutCubic: function (x, t, b, c, d) {
		if ((t/=d/2) < 1) return c/2*t*t*t + b;
		return c/2*((t-=2)*t*t + 2) + b;
	},
	easeInQuart: function (x, t, b, c, d) {
		return c*(t/=d)*t*t*t + b;
	},
	easeOutQuart: function (x, t, b, c, d) {
		return -c * ((t=t/d-1)*t*t*t - 1) + b;
	},
	easeInOutQuart: function (x, t, b, c, d) {
		if ((t/=d/2) < 1) return c/2*t*t*t*t + b;
		return -c/2 * ((t-=2)*t*t*t - 2) + b;
	},
	easeInQuint: function (x, t, b, c, d) {
		return c*(t/=d)*t*t*t*t + b;
	},
	easeOutQuint: function (x, t, b, c, d) {
		return c*((t=t/d-1)*t*t*t*t + 1) + b;
	},
	easeInOutQuint: function (x, t, b, c, d) {
		if ((t/=d/2) < 1) return c/2*t*t*t*t*t + b;
		return c/2*((t-=2)*t*t*t*t + 2) + b;
	},
	easeInSine: function (x, t, b, c, d) {
		return -c * Math.cos(t/d * (Math.PI/2)) + c + b;
	},
	easeOutSine: function (x, t, b, c, d) {
		return c * Math.sin(t/d * (Math.PI/2)) + b;
	},
	easeInOutSine: function (x, t, b, c, d) {
		return -c/2 * (Math.cos(Math.PI*t/d) - 1) + b;
	},
	easeInExpo: function (x, t, b, c, d) {
		return (t==0) ? b : c * Math.pow(2, 10 * (t/d - 1)) + b;
	},
	easeOutExpo: function (x, t, b, c, d) {
		return (t==d) ? b+c : c * (-Math.pow(2, -10 * t/d) + 1) + b;
	},
	easeInOutExpo: function (x, t, b, c, d) {
		if (t==0) return b;
		if (t==d) return b+c;
		if ((t/=d/2) < 1) return c/2 * Math.pow(2, 10 * (t - 1)) + b;
		return c/2 * (-Math.pow(2, -10 * --t) + 2) + b;
	},
	easeInCirc: function (x, t, b, c, d) {
		return -c * (Math.sqrt(1 - (t/=d)*t) - 1) + b;
	},
	easeOutCirc: function (x, t, b, c, d) {
		return c * Math.sqrt(1 - (t=t/d-1)*t) + b;
	},
	easeInOutCirc: function (x, t, b, c, d) {
		if ((t/=d/2) < 1) return -c/2 * (Math.sqrt(1 - t*t) - 1) + b;
		return c/2 * (Math.sqrt(1 - (t-=2)*t) + 1) + b;
	},
	easeInElastic: function (x, t, b, c, d) {
		var s=1.70158;var p=0;var a=c;
		if (t==0) return b;  if ((t/=d)==1) return b+c;  if (!p) p=d*.3;
		if (a < Math.abs(c)) { a=c; var s=p/4; }
		else var s = p/(2*Math.PI) * Math.asin (c/a);
		return -(a*Math.pow(2,10*(t-=1)) * Math.sin( (t*d-s)*(2*Math.PI)/p )) + b;
	},
	easeOutElastic: function (x, t, b, c, d) {
		var s=1.70158;var p=0;var a=c;
		if (t==0) return b;  if ((t/=d)==1) return b+c;  if (!p) p=d*.3;
		if (a < Math.abs(c)) { a=c; var s=p/4; }
		else var s = p/(2*Math.PI) * Math.asin (c/a);
		return a*Math.pow(2,-10*t) * Math.sin( (t*d-s)*(2*Math.PI)/p ) + c + b;
	},
	easeInOutElastic: function (x, t, b, c, d) {
		var s=1.70158;var p=0;var a=c;
		if (t==0) return b;  if ((t/=d/2)==2) return b+c;  if (!p) p=d*(.3*1.5);
		if (a < Math.abs(c)) { a=c; var s=p/4; }
		else var s = p/(2*Math.PI) * Math.asin (c/a);
		if (t < 1) return -.5*(a*Math.pow(2,10*(t-=1)) * Math.sin( (t*d-s)*(2*Math.PI)/p )) + b;
		return a*Math.pow(2,-10*(t-=1)) * Math.sin( (t*d-s)*(2*Math.PI)/p )*.5 + c + b;
	},
	easeInBack: function (x, t, b, c, d, s) {
		if (s == undefined) s = 1.70158;
		return c*(t/=d)*t*((s+1)*t - s) + b;
	},
	easeOutBack: function (x, t, b, c, d, s) {
		if (s == undefined) s = 1.70158;
		return c*((t=t/d-1)*t*((s+1)*t + s) + 1) + b;
	},
	easeInOutBack: function (x, t, b, c, d, s) {
		if (s == undefined) s = 1.70158; 
		if ((t/=d/2) < 1) return c/2*(t*t*(((s*=(1.525))+1)*t - s)) + b;
		return c/2*((t-=2)*t*(((s*=(1.525))+1)*t + s) + 2) + b;
	},
	easeInBounce: function (x, t, b, c, d) {
		return c - jQuery.easing.easeOutBounce (x, d-t, 0, c, d) + b;
	},
	easeOutBounce: function (x, t, b, c, d) {
		if ((t/=d) < (1/2.75)) {
			return c*(7.5625*t*t) + b;
		} else if (t < (2/2.75)) {
			return c*(7.5625*(t-=(1.5/2.75))*t + .75) + b;
		} else if (t < (2.5/2.75)) {
			return c*(7.5625*(t-=(2.25/2.75))*t + .9375) + b;
		} else {
			return c*(7.5625*(t-=(2.625/2.75))*t + .984375) + b;
		}
	},
	easeInOutBounce: function (x, t, b, c, d) {
		if (t < d/2) return jQuery.easing.easeInBounce (x, t*2, 0, c, d) * .5 + b;
		return jQuery.easing.easeOutBounce (x, t*2-d, 0, c, d) * .5 + c*.5 + b;
	}
});

function nodeInAll(n) {
    for (var i = 0; i < document.all.length; ++i)
        if (document[i] === n)
            return true;

    return false;
}

function arrayShuffle(o) {
	for(var j, x, i = o.length; i; 
        j = parseInt(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);

	return o;
}

function htmlEntitiesEscape(html) {
  return html.
    replace(/&/gmi, '&amp;').
    replace(/"/gmi, '&quot;').
    replace(/>/gmi, '&gt;').
    replace(/</gmi, '&lt;')
}

var stripLeading = function(s) {
    return s.replace(/^[ 0]+/g, '');
};

function compareIds(a, b) {
    a = stripLeading(a.toString());
    b = stripLeading(b.toString());

    if (a.length > b.length)
        return 1;
    else if (b.length > a.length)
        return -1;

    for (var i = 0; i < a.length; ++i) {
        var x = a[i], y = b[i];
        if (x > y) return 1;
        else if (y > x) return -1;
    }

    return 0;
}

