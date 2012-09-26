/**
 * This file provides an interface to the main digsby app. It uses the window's title
 * (which is never displayed) as a 'mailbox' for the python object that observs events
 * from the webkit control this javascript executes in. Supports callbacks.
 *
 * TODO: cleanup with jQuery.Deferred
 */
function DigsbyClass() {
    this.callbacks = {};
}

DigsbyClass.prototype = {
    requestOut: function(method, params, id, success, error, specifier) {
        var self = this;

        if (id) {
            self.callbacks[id] = {success:success, error:error};
        }
        self.jsonOut({'method':method, 'params':params, 'id':id, 'specifier':specifier});

    },

    requestIn: function(args) {
    window[args.method](args.params, args.id);
    },

    resultOut: function(result, error, id) {
        var self = this;
	self.jsonOut({'result':result, 'error':error, 'id':id});
    },

    successOut: function(result, id) {
        this.resultOut(result, null, id);
    },

    errorOut: function(error, id) {
        this.resultOut(null, error, id);
    },

    jsonOut: function(json_obj) {
        var url = "digsby://digsbyjsonrpc/json=" + encodeURIComponent(JSON.stringify(json_obj));
        document.title = url;
        document.title = "digsby://digsbyjsonrpc/clear";
    },

    resultIn: function(res) {
        var self = this;

        var result = res.result;
        var error  = res.error;
        var id     = res.id;
        if (result !== null) {
            self.successIn(result, id);
            if (error !== null) {
                console.log("got a result and error:" + result + "," + error + "," + id);
            }
            return;
        }
        if (error !== null) {
            self.errorIn(error, id);
            return;
        }
        console.log("got no result or error:" + id);

    },

    errorIn: function(error, id) {
        if (this.callbacks[id]){
            this.callbacks[id].error(error);
            delete this.callbacks[id];
        }
    },

    successIn: function(result, id) {
        if (this.callbacks[id]) {
            this.callbacks[id].success(result);
            delete this.callbacks[id];
        }
    }
};

var Digsby = new DigsbyClass();

function DCallbacks(specifier) {
    this.id_count  = 0;
    this.specifier = specifier === undefined ? null : specifier;
}

function callbackCall(params, id) {
    params = params[0];
    var method = params.method;
    var args   = params.args;

    function success(result) { Digsby.successOut(result, id); }
    function error(error_obj) { Digsby.errorOut(error_obj, id); }

    args.success = success;
    args.error = error;

    window[method](args);
}

// Here's the simple, easy interface.
// e.g.: D.rpc('get_comments', {'post_id' : 1}, success_func, error_func);
//
// Once this round-trips through python, your success or error handler
// will be called appropriately with a results dictionary or error object.

DCallbacks.prototype = {

    notify: function(method, params){
        Digsby.requestOut(method, [params], null, null, null, this.specifier);
    },

    rpc: function(method, params, success, error) {
        var id = (new Date()).getTime() + '_' + this.specifier + '_' + this.id_count++;
        //call digsby, wraps w/ an id and puts params in a list
        //also, unwraps the args dict from it's parent list for success
        Digsby.requestOut(method, [params], id, function(args) { success(args[0]); }, error, this.specifier);
    },

    ajax: function(args) {
        if (args.type != "JSON")
            console.log("ERROR: Digsby only does JSON");
        else
            this.rpc('ajax', {url:args.url, type:args.type}, args.success, args.error);
    }
};

var D = new DCallbacks();

