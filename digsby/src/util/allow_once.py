import functools
import logging

log = logging.getLogger('util.allow_once')

class Cancel(object):
    '''Can be returned from a function to signify 
    it is not to be limited after the present call'''
    def __init__(self, value):
        self.value = value

def _key(f_or_name):
    if not isinstance(f_or_name, basestring):
        name = f_or_name.func_name
    else:
        name = f_or_name

    return '_called_%s' % name

def allow_once(f):
    varname = _key(f)
    
    @functools.wraps(f)
    def wrapper(self, *a, **k):
        try:
            d = getattr(self, '_runonce_history')
        except AttributeError:
            d = self._runonce_history = {}

        force = k.pop('_runonce_force', False)
        verbose = getattr(self, '_runonce_verbose', False)
        if force or not d.get(varname, False):
            d[varname] = True
            retval = f(self, *a, **k)

            if isinstance(retval, Cancel):
                if verbose: log.debug('Runonce protection disabled for %r', f)
                retval = retval.value
                d.pop(varname, None)
            else:
                if verbose: 
                    log.debug('Runonce protection enabled for %r', f)

            return retval
        else:
            if verbose:
                log.debug('Didn\'t call %r', f)

    return wrapper

def reset_allow_once(o, fname=None):
    verbose = getattr(o, '_runonce_verbose', False)
    d = getattr(o, '_runonce_history', {})

    if verbose:
        log.debug('Clearing runonce history for %r (key=%r)', o, fname)

    if fname is None:
        d.clear()
    else:
        d.pop(_key(fname), None)

