from __future__ import print_function
import sys


class SanityException(Exception):
    def __init__(self, name, message):
        self.component_name = name
        super(Exception, self).__init__(message)


def insane(name, message):
    raise SanityException(name, message)


def module_check(name):
    try:
        module = __import__(name)
        for part in name.split('.')[1:]:
            module = getattr(module, part)
        return module
    except (ImportError, AttributeError):
        insane(name, 'not found')


def sanity(name):
    if name == 'all':
        _print = lambda s, *a, **k: None
    else:
        _print = print

    _print("{name:.<20}".format(name = name), end = '')
    try:
        globals().get('sanity_%s' % name, lambda: insane(name, "sanity check not found"))()
    except:
        _print("FAIL")
        raise
    else:
        _print("OK")


def sanity_path():
    path = module_check('path')
    if not hasattr(path.path, 'openfolder'):
        insane('path.py', 'not patched for Digsby')


def sanity_ZSI():
    ZSI = module_check('ZSI')
    Namespaces = module_check('ZSI.wstools.Namespaces')

    if getattr(getattr(Namespaces, 'SOAP12'), 'ENC12', None) != 'http://www.w3.org/2003/05/soap-encoding':
        insane('ZSI', 'namespace modifications for Digsby not found')

    test_script = 'import ZSI.generate.pyclass as pyclass;\nif hasattr(pyclass, "pydoc"): raise Exception'
    try:
        if __debug__:
            import subprocess
            if subprocess.call([sys.executable, '-O', '-c', test_script]) != 0:
                raise Exception
        else:
            exec(test_script)
    except:
        insane('ZSI', 'pydoc is imported in non-debug mode')


def sanity_M2Crypto():
    M2Crypto = module_check('M2Crypto')
    RC4 = module_check('M2Crypto.RC4')

    try:
        if 'testdata' != RC4.RC4('key').update(RC4.RC4('key').update('testdata')):
            raise Exception
    except:
        insane('M2Crypto', 'crypto test failed')


def sanity_syck():
    syck = module_check('syck')

    try:
        if syck.load('---\ntest: works\n').get('test') != 'works':
            raise Exception
    except:
        insane('syck', 'failed to parse sample document')


def sanity_libxml2():
    libxml2 = module_check('libxml2')

    doc = None
    try:
        doc = libxml2.parseDoc('<root><child/></root>')
        if doc.children.name != 'root' or doc.children.children.name != 'child':
            raise Exception
    except:
        insane('libxml2', 'failed to process sample document')
    finally:
        if doc is not None:
            doc.freeDoc()


def sanity_PIL():
    from StringIO import StringIO
    Image = module_check('PIL.Image')

    image = None
    try:
        image = Image.new('RGB', (1, 1))
    except:
        insane('PIL', 'failed to create test image')

    try:
        image.save(StringIO(), 'jpeg')
    except:
        insane('PIL', 'does not have jpeg support')

    try:
        image.save(StringIO(), 'png')
    except:
        insane('PIL', 'does not have png support')

    try:
        image.save(StringIO(), 'ppm')
    except:
        insane('PIL', 'does not have ppm (freetype) suport')


def sanity_lxml():
    html = module_check('lxml.html')
    etree = module_check('lxml.etree')
    objectify = module_check('lxml.objectify')

    try:
        etree.tostring(etree.fromstring('<root><child/></root>'))
    except:
        insane('lxml', 'failed to process sample document')


def sanity_simplejson():
    json = module_check('simplejson')
    speedups = module_check('simplejson._speedups')

    try:
        json.dumps({}, use_speedups = False)
    except TypeError:
        insane('simplejson', 'does not allow disabling speedups')

def sanity_protocols():
    import inspect
    protocols = module_check('protocols')
    speedups = module_check('protocols._speedups')

    Adapter = protocols.Adapter
    if inspect.getargspec(Adapter.__init__).args != ['self', 'ob']:
        insane('protocols', 'constructor for Adapter is incorrect')

#  TODO: More verification for these modules
for simple_module in set(('blist', 'cgui', 'babel', 'socks', 'tenjin', 'certifi',
                          'dns', 'rauth', 'ClientForm', 'peak', '_xmlextra',
                          'sip', 'wx', 'wx.py', 'wx.calendar', 'wx.webview',
                          'wx.lib', 'wx.stc', 'feedparser', 'pkg_resources')):
    globals()['sanity_' + simple_module] = lambda _name=simple_module: module_check(_name)


def main(*args):
    dont_check = set(arg[1:] for arg in args if arg.startswith('-'))
    to_check = set(arg for arg in args if arg != 'all' and not arg.startswith('-'))

    if not to_check or 'all' in args:
        for func_name, sanity_check in globals().items():
            if func_name.startswith('sanity_') and callable(sanity_check):
                name = func_name[len('sanity_'):]
                to_check.add(name)

    for name in sorted(to_check - dont_check):
        try:
            sanity(name)
        except SanityException as e:
            print("SanityException: %s: %s" % (e.component_name, e), file = sys.stderr)


if __name__ == '__main__':
    main(*sys.argv[1:])
