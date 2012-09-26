from contextlib import contextmanager
import sys
import traceback

try:
    sentinel
except NameError:
    sentinel = object()

def try_this(func, default = sentinel, allow = (NameError,), ignore = ()):
    if not callable(func):
        raise TypeError('try_this takes a callable as its first argument')

    try:
        return func()
    except ignore:
        assert default is sentinel
    except allow:
        raise
    except Exception:
        if default is sentinel:
            raise
        else:
            return default

def syck_error_message(e, fpath):
    msg, line, column = e

    msg  = '%s in %s:\n\n' % (msg, fpath)

    from path import path
    try:    error_line = path(fpath).lines()[line].strip()
    except: error_line = '(could not load line)'

    msg += 'line %d, column %d: "%s"' % (line, column, error_line)
    return msg

@contextmanager
def repr_exception(*args, **kwargs):
    '''
    Given local variables, prints them out if there's an exception before
    re-raising the exception.
    '''

    try:
        yield
    except:
        for item in args:
            found = False
            for k, v in sys._getframe(2).f_locals.iteritems():
                if v is item:
                    print >> sys.stderr, k, '-->', repr(item)
                    found = True
                    break

            if not found:
                print >> sys.stderr, repr(item)

        for k, v in kwargs.iteritems():
            print >> sys.stderr, repr(k), repr(v)
        raise

def with_traceback(func, *args, **kwargs):
    '''
    Any exceptions raised during the execution of "func" are are be printed
    and execution continues.
    '''
    try:
        return func(*args, **kwargs)
    except Exception:
        traceback.print_exc()

class traceguard(object):
    @classmethod
    def __enter__(cls): pass
    @classmethod
    def __exit__(cls, *a):
        try:
            if filter(None, a):
                try:
                    print >>sys.stderr, "The following exception has been squashed!"
                except Exception:
                    pass

                try:
                    exc_string = traceback.format_exc(a)
                except Exception:

                    # if there was an exception using format_exc, see if
                    # we stored an old one in _old_format_exc
                    exc_string = '(Could not format exception.)'

                    if hasattr(traceback, '_old_format_exc'):
                        try:
                            exc_string = traceback._old_format_exc(a)
                        except Exception:
                            pass
                try:
                    if isinstance(exc_string, unicode):
                        try:
                            exc_string = exc_string.encode('utf-8')
                        except Exception:
                            exc_string = "Error encoding this as utf8: %r" % (exc_string,)
                    print >>sys.stderr, exc_string
                except Exception:
                    try:
                        print >> sys.stderr, "could not print exception"
                    except Exception:
                        pass
        except Exception:
            #this method cannot be allowed to blow up.
            pass
        finally:
            del a
        return True

