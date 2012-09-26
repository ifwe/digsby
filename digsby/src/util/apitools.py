import inspect
import util.net as net
import util.callbacks as callbacks
import util.mimehelpers as mimehelpers

class API_Sender_FormPost(object):
    '''
    Specifies how to send an API_MethodCall with an HTTP form post.
    '''
    def _info_for_argument(self, arg):
        value = arg.value
        
        extra = {}
        if arg.spec.type == 'data':
            if isinstance(value, unicode):
                value = value.encode('utf8')
                
        if arg.spec.type == 'image-noenc':
            extra.update(disposition = dict(filename = 'image'))

        return dict(name = arg.spec.name, type = arg.spec.type, value = arg.value, **extra)
    def serialize_method_call(self, api, call):

        parts = map(self._info_for_argument, call.bound_args)
        mime_form = mimehelpers.form_builder(parts)
        
        return call.get_endpoint(api.API_BASE), {}, mime_form #dict(mime_headers), mime_data

class API_MethodArgSpec(object):
    '''
    Specifies an argument of a method. Has a name, type, and an "optional" flag.
    '''
    # TODO: default value?
    def __init__(self, name, type, optional = False):
        self.name = name
        self.type = type
        self.optional = optional
        
    def __repr__(self):
        return '%s(name = %r, type = %r, optional = %r)' % (type(self).__name__, self.name, self.type, self.optional)
    
    def __call__(self, val):
        arg = API_MethodArg(val, self)
        arg.typecheck()
        return arg
        

class API_MethodArg(object):
    '''
    Represents an argument to a method call. Has a "spec" (type and optional specification) and
    a value. 
    '''
    _typecheckers = {
        'data'        : lambda x: isinstance(x, basestring) or hasattr(x, 'read'),
        'image-noenc' : bytes,
        'image'       : bytes,
    }
    def __init__(self, value, argspec):
        self.value = value
        self.spec = argspec
        
    def typecheck(self):
        failed = False
        
        if self.spec.type in self._typecheckers:
            # String value for the type. check known types dictionary and
            # use the callable there to verify correctness of the value
            if not self._typecheckers[self.spec.type](self.value):
                failed = True
        elif type(self.spec.type) is type:
            # type is a class object, do isinstance check
            if not isinstance(self.value, self.spec.type):
                failed = True
        else:
            failed = True

        if failed:
            raise TypeError('%r does not match argument specification: %r', self.value, self.spec)
        
    def __repr__(self):
        return '<%r(%r)>' % (self.spec, self.value)

class API_Method(object):
    '''
    Represents a method of an external API. Has arguments (= API_MethodArgSpec objects), return type, 
    and potentially more properties. 
    '''
    def __init__(self, *argspec, **properties):
        # TODO: get return type out of properties
        self.__dict__.update(properties)
        self.argspecs = argspec
        
        names = set()
        for spec in argspec:
            if spec.name in names:
                # Already found an arg with this name
                raise TypeError("Duplicate argument %r in function definition", spec.name)
            names.add(spec.name)

    def get_endpoint(self, base = None, name = None):
        # Since the method can be created fairly loosely, the way to determine the "endpoint" (url) 
        # of a method is not 100% simple. Still pretty straightforward, though.
        if base and name:
            # Provided in the arguments to this function
            return net.httpjoin(base, name)
        
        endpoint = getattr(self, 'endpoint', None)
        
        if endpoint is None:
            base = getattr(self, 'api_base', base)
            name = getattr(self, 'name', name)
            if None in (base, name):
                raise ValueError("No known endpoint")
            
            endpoint = net.httpjoin(base, name)
        
        return endpoint

    def __call__(self, *args, **kwargs):
        # Returns an API_MethodCall instance.
        return API_MethodCall(self, *args, **kwargs)
    
    def __repr__(self):
        name = getattr(self, 'name', 'unnamed-function')
        
        args_strs = ['%s : %s' % (arg.name, arg.type) for arg in self.argspecs if not arg.optional]
        args_strs.extend('%s = None : %s' % (arg.name, arg.type) for arg in self.argspecs if arg.optional)
        args_str = ', '.join(args_strs)
        return "<%s(%s)>" % (name, args_str)
    
class API_MethodCall(object):
    '''
    Represents a method and the args it is called with. Allows for fairly complex argument 
    passing, similar to python function semantics. Does argument checking on initialization. 
    '''
    def __init__(self, spec, *_args, **_kwargs):
        self.spec = spec
        self.argvals = _args
        self.kwargs = _kwargs
        
        args = dict((spec.name, (spec, None)) for spec in self.spec.argspecs)
        i = 0
        # Take care of A and B in F(A, B, C=d) (i.e. positional args)
        for i, (argval, argspec) in enumerate(zip(self.argvals, self.spec.argspecs)):
            arg = argspec(argval)
            if args[argspec.name][1] is not None:
                raise TypeError("%r got multiple values for argument %r", self.spec, argspec.name)
            
            args[argspec.name] = (argspec, arg)
            
        # Check the rest of the arguments list for things passed by keyword.
        # (i.e. C in F(A, B, C=d))
        for argspec in self.spec.argspecs[i:]:
            if argspec.name in self.kwargs:
                arg = argspec(self.kwargs[argspec.name])
                if args[argspec.name][1] is not None:
                    raise TypeError("%r got multiple values for argument %r", self.spec, argspec.name)
                
                args[argspec.name] = (argspec, arg)
                
        # Make sure all required arguments were provided.
        for argspec, argval in args.values():
            if argval is None and not argspec.optional:
                raise TypeError("Argument %r is required", argspec.name)
        
        self.bound_args = dict((argspec.name, args[argspec.name][1]) for argspec in self.spec.argspecs)
    
    def get_endpoint(self, base = None, name = None):
        return self.spec.get_endpoint(base = base, name = name)
        
    def __repr__(self):
        return '%r(%s)' % (self.spec, ', '.join('%s = %s' % (name, repr(arg.value)[:200]) for name, arg in self.bound_args.items() if arg is not None))

def apimethod_from_pyfunc(f, *_types, **k):
    pyspec = inspect.getargspec(f)
    args = []
    names = list(pyspec.args)
    types = list(_types)
    
    if 'self' == names[0]:
        names.pop(0)
    
    if pyspec.defaults is not None:
        defaults = list(pyspec.defaults)
        while defaults:
            default = defaults.pop(-1)
            argname = names.pop(-1)
            type = types.pop(-1)
            
            args.insert(0, API_MethodArgSpec(argname, type, optional = True))
    else:
        defaults = []
        
    while names and types:
        argname = names.pop(-1)
        type = types.pop(-1)
        args.insert(0, API_MethodArgSpec(argname, type, optional = False))
        
    if names or defaults or types:
        raise TypeError("Had extraneous stuff when defining an API method: names = %r, defaults = %r, types = %r", names, defaults, types)
    
    methodname = k.pop('name', f.__name__)
    methodspec = API_Method(name = methodname, *args, **k)
    
    return methodspec

def apicall(*_types, **kw):
    def funcwrapper(f):
        return apicaller(apimethod_from_pyfunc(f, *_types, **kw))
    return funcwrapper

def apicaller(methodspec):
    @callbacks.callsback
    def wrapper(api, *method_args, **method_kwargs):
        callback = method_kwargs.get('callback', None)
        method_call = methodspec(*method_args, **method_kwargs)
        
        # TODO: use return type of API_Method to create handler. don't require 
        # API to provide a callable. make recievers, similar to senders (e.g. API_Sender_FormPost)
        response_handler = api.get_response_handler(method_call, callback)
        api.send_method(method_call, success = response_handler, error = callback.error)
        
    return wrapper
