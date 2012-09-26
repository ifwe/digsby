import path

def a(name):
    return (name, '_string')

def c(name):
    return (name, '_primitive')

def e(name):
    return (name, '_array')

def d(clsname, name = None):
    return (name or clsname, clsname)

def f(name):
    return (name, '_enum')

#def j(name):
#    return (name, '_date')

def g(name):
    return (name, '_object')

def j(name):
    return (name, '_oArray')

class B(object):
    def rfc(self, name, args):
        args_string = '\n'.join('''\
        (%r, %r),''' % arg for arg in args)

        return '''\
class %s(FppClass):
    _fields_ = [
%s
        ]
''' % (name, args_string)

    def rfm(self, name, args, method_name, tm, g, namespace):
        return (args, name, tm, g, namespace)

    def __getattr__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            return attr

b = B()
null = None
class Network:
    class Type:
        XMLPost = 0

known_js_filenames = ['i0a.js', 'i1a.js', 'i2a.js', 'i3a.js', 'i4a.js']
def download_src(buildnum, localdir = "d:\\src\\hotmail\\", remote_base="http://gfx6.hotmail.com/mail/"):
    import urllib2, js_scrape
    build_dir = path.path(localdir) / buildnum
    if not build_dir.isdir():
        build_dir.makedirs()
    for fname in known_js_filenames:
        with open(build_dir / fname, 'wb') as f:
            f.write(js_scrape.Cleanup_JS(urllib2.urlopen(remote_base + buildnum + "/" + fname).read()))

import sys; sys.path.append("d:\\workspace\\js_scrape")
