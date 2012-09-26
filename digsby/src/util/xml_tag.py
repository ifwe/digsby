import urllib2
import traceback
from xml.sax import make_parser
from xml.sax.handler import ContentHandler, DTDHandler, EntityResolver, feature_namespaces, \
                            feature_external_ges, feature_external_pes
from xml.sax.saxutils import escape, unescape
from logging import getLogger
log = getLogger('xml_tag')

__all__ = ['tag_parse', 'tag', 'post_xml', 'plist']


ATTR_BLACKLIST = ('bogu5_123_aTTri8ute', 'mro',
 'func_closure', 'func_code', 'func_defaults', 'func_dict', 'func_doc',
 'func_globals', 'func_name')

class LooseNSDict(dict):
    def __contains__(self, thing):
        return True
    def __getitem__(self, thing):
        try:
            return dict.__getitem__(self, thing)
        except KeyError:
            dict.__setitem__(self, thing, 'unknown')
            return 'unknown'

def tag_parse(s, ns=None):
    if ns is None:
        ns = {}
    elif not ns:
        # don't care about namespaces
        ns = LooseNSDict()

    h = TagHandler()

    if type(s) is unicode:
        s = s.encode('utf-8')


    try:
        parser = make_parser()

        features=((feature_namespaces, 0), (feature_external_ges, 0), (feature_external_pes, 0))

        for key, value in features:
            parser.setFeature(key, value)

        parser.setContentHandler(h)
        parser.feed(s, True)
    except Exception:
        traceback.print_exc()
        log.error('bad xml: %r', s)
        log.error('tag handler obj: %r', h)
        log.error('handler root: %r', h.root)
        raise

    h.root._source = s
    assert h.root is not None
    return h.root

class TagHandler(ContentHandler, DTDHandler, EntityResolver):
    def __init__(self):
        ContentHandler.__init__(self)
        #DTDHandler.__init__(self) # DTDHandler has no __init__ (?)
        #EntityResolver.__init__(self) # neither does EntityResolver
        self.data = ''
        self.stack = []
        self.root = None
        self.ns_dict = {}

    def characters(self, data):
        #if data.strip():
        self.stack[-1](data)

    def startElement(self, name, attrs):
        # take stupid mapping type object and
        # make it a map, while taking stupid
        # unicode strings and making them strings

        kwargs = {}

        for k,v in attrs.items():
            if ':' in k:
                xmlns, ns = k.split(':', 1)
                if xmlns == 'xmlns':
                    ns_uri = v
                    self.ns_dict[ns] = ns_uri
                else:
                    assert xmlns in self.ns_dict, (xmlns, self.ns_dict)
                    kwargs[str(k)] = unicode(v)
            else:
                kwargs[str(k)] = unicode(v)

        if ':' in name:
            ns, name = name.rsplit(':', 1)
            name = (ns, name)

        t = tag(name, _ns_dict=self.ns_dict, **kwargs)

        if self.stack:
            self.stack[-1](t)
        else:
            self.root = t

        self.stack.append(t)

    def endElement(self, name):
        if ':' in name:
            ns, name = name.rsplit(':', 1)


        assert(name == self.stack[-1]._name), (name, self.stack[-1]._name)

        self.stack.pop()

    def startElementNS(self, name, attrs):
        import warnings
        warnings.warn("Namespaced elements and attributes are not officially supported!")

#    def ignorableWhitespace(self, whitespace):
#        self.stack[-1](whitespace)

class tag(object):
    _pretty_sep = ' ' * 2
#    __ns_dict = {}
#    @staticmethod
#    def _set_ns_dict(new_ns):
#        tag.__ns_dict = new_ns

    def __init__(self, _name, _cdata=u'', _ns_dict=None, **attrs):

        # _nd_dict of False will make tag not care about namespaces and return 'unknown' for the ones
        #  with no value present

        if isinstance(_name, basestring) and _name.strip().startswith('<'):
            # Someone gave us xml, parse it and set our state
            self.__dict__ = tag_parse(_name, _ns_dict).__dict__
            self._source = _name
            return
        else:
            self._source = None

        if _ns_dict is None:
            _ns_dict = {}

        if 'xml' not in _ns_dict:
            _ns_dict['xml'] = 'http://www.w3.org'

        self.__ns_dict = _ns_dict

        self._cdata = unicode(_cdata)
        if type(_cdata) is bool:
            self._cdata = self._cdata.lower()

        self._children = []
        self._attrs = {}
        self._attrns = {}


        for k in attrs:
            if ':' in k:
                ns, attrname = k.rsplit(':',1)

                if ns == 'xmlns':
                    if attrname in self.__ns_dict:
                        assert self.__ns_dict[attrname] == k, (k, attrs[k],self.__ns_dict)
                    else:
                        self.__ns_dict[attrname] = attrs[k]
                else:
                    self._attrns[ns] = self.__ns_dict[ns]

        self._attrs = attrs

        if isinstance(_name, basestring):
            self._name = _name
            self._ns = (None, None)

            if 'xmlns' in self._attrs:
                self._ns = (True, self._attrs.pop('xmlns'))

        else:
            assert len(_name) == 2
            ns, self._name = _name
            if isinstance(ns, basestring):
                assert ns in self.__ns_dict, (_name, self.__ns_dict)
            else:
                assert len(ns) == 2
                ns, ns_uri = ns
                self.__ns_dict[ns] = ns_uri

            self._ns = (ns, self.__ns_dict[ns])


    def _find(self, *a, **k):
        '''
        Returns a list of all tags that match the given criteria.

        _name : string, matches the name of the tag if provided.
        _f    : callable predicate. is given one argument (the tag) and if bool(result) is true, the tag matches.
        **kwds: matches keywords against attributes of the tag.
        '''
        results = []
        if self._match(*a, **k):
            results.append(self)

        for res in (x._find(*a, **k) for x in self):
            results.extend(res)
        return results

    def _findOne(self, *a, **k):
        '''
        Searches for a tag that matches the given criteria, returning the first.

        _name : string, matches the name of the tag if provided.
        _f    : callable predicate. is given one argument (the tag) and if bool(result) is true, the tag matches.
        **kwds: matches keywords against attributes of the tag.
        '''
        if self._match(*a, **k):
            return self

        for x in self:
            res = x._findOne(*a, **k)
            if res is not None:
                return res

        return None

    def _match(self, _name='', _f=lambda t:True, **kwds):
        '''
        Attempt to match this tag against the provided criteria.

        _name : string, matches the name of the tag if provided.
        _f    : callable predicate. is given one argument (the tag) and if bool(result) is true, the tag matches.
        **kwds: matches keywords against attributes of the tag.
        '''
        if not self._name.startswith(_name):
            return False

        if not _f(self):
            return False

        for k,v in kwds.iteritems():
            if k not in self._attrs:
                return False
            if self._attrs[k] != v:
                return False

        return True

    def _write_to(self, xml_handler):
        xml_handler.startElement(self._name, self._attrs)
        if self._children:
            #children
            [child.write_to(xml_handler) for child in self._children]
        if self._cdata:
            #characters
            xml_handler.characters(self._cdata)
        xml_handler.endElement(self._name)

    def _add_child(self, *args, **kwargs):
        if '_ns_dict' not in kwargs:
            kwargs['_ns_dict'] = self.__ns_dict
        t = args[0] if isinstance(args[0], tag) else tag(*args, **kwargs)
        self._children.append(t)
        return self

    def _add_attrs(self, **kwargs):
        self._attrs.update(kwargs)
        return self

    def _add_cdata(self, data):
        '''
        >>> t = tag('name')
        >>> t._add_cdata('dot')
        >>> str(t)
        'dot'
        >>> t._add_cdata('Syntax')
        >>> str(t)
        'dotSyntax'
        >>> print t._to_xml()
        <name>
          dotSyntax
        </name>
        '''

        if type(data) is bool:
            data = unicode(data).lower()

        if not isinstance(data, basestring):
            data = unicode(data)

        if type(data) is str:
            data = unicode(data, 'utf-8')

        self._cdata += data
        return self

    def __call__(self, *args):
        for arg in args:
            if isinstance(arg, tag):
                self._add_child(arg)
            elif isinstance(arg, (tuple, list, set)):
                self._add_child(tag(*arg, **dict(_ns_dict=self.__ns_dict)))
            else:
                try:
                    self._add_cdata(arg)
                except:
                    raise ValueError, 'Couldn\'t add child from %r' % arg
        return self

    def __getattr__(self, attr):
        if attr.startswith('_') or attr in ATTR_BLACKLIST:
            return object.__getattribute__(self, attr)

        children = [child for child in self._children if child._name == attr]
        if len(children) == 1:
            children = children[0]
        elif len(children) == 0:
            children = tag(attr, _ns_dict = self.__ns_dict)
            self._add_child(children)

        return children

    def __getitem__(self, index):
        if isinstance(index, basestring):
            # pretend to be a dictionary with attr:val pairs
            return self._attrs[index]

        # pretend to be a list containing children
        return self._children[index]

    def __setattr__(self, attr, val):
        if attr.startswith('_'):
            return object.__setattr__(self, attr, val)

        child = getattr(self, attr)
        if isinstance(child, tag):
            if hasattr(val, '_to_xml') and val is not child:
                self._children[self._children.index(child)] = val
            elif val is not child:
                child._cdata = ''
                child(val)
        else:
            #print 'val:',val
            self._add_child(tag(attr, _ns_dict = self.__ns_dict)(val))

    def __setitem__(self, index, val):
        if isinstance(index, basestring):
            # pretend to be a dictionary
            self._attrs[index] = val
        else:
            # pretend to be a list
            self._children[index] = val

    def __iadd__(self, other):
        return self(other)

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    def __contains__(self, name):
        if isinstance(name, tag):
            name = name._name

        return  name in [c._name for c in self._children]

    def __hasattr__(self, attr):
        if attr.startswith('_'):
            return object.__hasattr__(self, attr)
        return attr in self._attrs

    def _to_xml(self, depth=0, pretty=True, self_closing=True, return_list=False):
        '''
        Not guaranteed to be valid xml...but pretty damn good so far!
        '''
        ns, ns_uri = self._ns

        if ns is not True:
            name = u'%s:%s' % (ns, self._name) if ns else self._name
        else:
            name = self._name

        indent = (u'\n' + self._pretty_sep*depth) * pretty
        s = [indent, '<']

        s.append(name)

        for k in self._attrs:
            s.extend([' ', k, '="', unicode(self._attrs[k]), '"'])

        if depth == 0:
            for ch_ns, ch_ns_uri in self._child_ns():
                if ch_ns is True:
                    s.extend([' xmlns="', ch_ns_uri, '"'])
                else:
                    s.extend([' xmlns:', ch_ns, '="', ch_ns_uri,'"'])

        if not self._cdata and not self._children and self_closing:
            s.append(' />')
            return s if return_list else ''.join(s)
        s.append('>')
        cleancdata = escape(self._cdata.strip())
        if cleancdata:
            s += [indent, self._pretty_sep*pretty,cleancdata]

        for child in self._children:
            s.extend(child._to_xml(depth+1, pretty, self_closing, return_list=True))

        s.extend([indent, '</', name, '>' ])

        if return_list:
            return s
        else:
            return u''.join(s)

    def _child_ns(self):
        ns_s = []
        for ch in self._children:
            ns_s.extend(ch._child_ns())

#        for attr in self._attrs:
#            if ':' in attr:
#                ns, name = attr.rsplit(':',1)
#                ns_s.insert(0, (ns,self._attrns[ns]))
        for ns in self._attrns.items():
            ns_s.insert(0, ns)

#        if 'xmlns' in self._attrs:
#            ns_s.insert(0, (True,self._attrs['xmlns']))


        ns_s.insert(0,self._ns)
        # return all non-empty
        return set(tup for tup in ns_s if all(tup))

    def __repr__(self):
        return '<%s object %s at %s>' % (self.__class__.__name__,
                                         self._name, id(self))

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self._cdata

    def __int__(self):
        return int(self._cdata)

    def __nonzero__(self):
        if self._attrs and (self._attrs.get('xsi:nil',False) != 'true'):
            return True
        elif self._attrs:
            # xsi:nil must be present and true, so return False
            return False

        if self._children:
            return True

        if self._cdata:
            return True

        return False

    def _copy(self):
        new = tag((self._ns, self._name), self._cdata, _ns_dict = self.__ns_dict, **self._attrs)
        for child in self._children:
            new._add_child(child._copy())
        return new

    def _recurse_ns(self, ns):
        '''
        Set a namespace on this tag and all children.

        so to generate
        <ds:parent xmlns:ds="http://www.dotsyntax.com">
          <ds:ch1 />
          <ds:ch2 />
        </ds:parent>
        you just do:

        >>> t = tag('parent')
        >>> t._add_child(tag('ch1'))
        >>> t._add_child(tag('ch2'))
        >>> t._recurse_ns(('ds', "http://www.dotsyntax.com"))
        >>> print t._to_xml()
        <ds:parent xmlns:ds="http://www.dotsyntax.com">
          <ds:ch1 />
          <ds:ch2 />
        </ds:parent>
        '''
        if isinstance(ns, basestring):
            assert ns in self.__ns_dict
            ns = (ns, self.__ns_dict[ns])
        else:
            assert len(ns) == 2
            self.__ns_dict[ns[0]] = ns[1]

        self._ns = ns
        for ch in self._children:
            ch._recurse_ns(ns)

import util
@util.threaded
def post_xml(url, data = None, xmldecl = True, verbose=False, **headers):
    '''
    Use HTTP POST to send XML to a URL.

    Optionally specify headers for urllib2 to use in the HTTP request.
    Returns a tag object. (The XML response from the server).
    '''

#    class Request(urllib2.Request):
#        def add_header(self, key, val):
#            self.headers[key] = val

    if isinstance(data, basestring):
        try:
            tag_parse(data)
        except:
            raise

    if isinstance(data, tag):
        data = data._to_xml(pretty = False).strip().encode('utf-8')

    if xmldecl and data and not data.startswith('<?xml'):
        data = "<?xml version='1.0' encoding='utf-8'?>" + data

    if type(data) is unicode:
        data = data.encode('utf-8')

    #data = unicode(data,'utf-8')
    headers.setdefault('Content-type','text/xml; charset=utf-8')

    req = urllib2.Request(url, data)
    req.headers = headers # avoid Title-Casing of headers

    if verbose:
        print '*'*80
        print req.headers
        print data
        print '*'*80

    e = None

    try:
        httpresp = urllib2.urlopen( req )
    except urllib2.HTTPError, e:
        print 'Error with request', e
        if e.fp is not None:
            httpresp = e.fp
        else: raise

    document = httpresp.read()
    tag_result = tag_parse( document )

    if (not tag_result) and e is not None:
        raise e

    if verbose or 'Fault' in tag_result:
        print httpresp.headers
        print document
        print '*'*80

    if 'Fault' in tag_result:
        raise SOAPException(tag_result)

    return tag_result

plist_types = {'string':  unicode,
               'integer': int,
               'true':    lambda *a: True,
               'false':   lambda *a: False}

class SOAPException(Exception):
    def __init__(self, t):
        self.t = t
        self.fault = fault = t.Body.Fault or t.Fault
        faultstring = str(self.fault.faultstring)

        if fault.detail:
            errorstring = str(fault.detail.errorstring)
            Exception.__init__(self, faultstring, errorstring)
        else:
            Exception.__init__(self, faultstring)


def plist(xml):
    'Apple PLIST xml -> ordered dict'

    from util.primitives import odict

    d = odict()

    for child in tag(xml).dict:
        contents = unicode(child)

        if child._name.lower() == 'key':
            key = contents
        else:
            d[key] = plist_types[child._name](contents)

    return d

def main():
    root = tag((('digsby','http://www.digsby.com'),'Root'),'some cdata', type='tag')

    root['font'] = 'Arial'
    root.Header.Security += 'test','testdata'
    print repr(root.Header.Security._children)
    root.Header.AuthInfo += ('digsby','Password'), 'pword'
    root.Header.Security += (('ps','longurl'),'HostingApp'), 'CLSID'
    print repr(root.Header.Security._children)
    print root.Header.Security._to_xml()
    print '-'*80
    print root.Header.Security.HostingApp._to_xml()
    print '-'*80
    root.Header.Security += ('ps','HostingApp'), 'CLSID2'
    print root.Header.Security.HostingApp
    print '-'*80
    root.Header.Security += ('ps','BinaryVersion'), 2
    root.Header.Security.TupledArg = 'whee'
    print root.Header.Security._to_xml()
    print '-'*80
    print root.Body._to_xml(self_closing=False)
    print '-'*80
    print 'iter:'
    for ch in root:
        print ch._name
    print '-'*80
    print 'original xml:'
    print root._to_xml()
    print '-'*80
    print 'parsed tag xml:'
    t = tag_parse(root._to_xml())
    print t._to_xml()
    print '-'*80
    print 'Parsed XML is equal to original XML?',root._to_xml() == t._to_xml()
    xml = tag(root._to_xml())
    print 'Constructed tag from xml. Constructed XML is equal to original?', xml._to_xml() == root._to_xml()

    xml = u"<?xml version='1.0' encoding='utf-8'?><foo>siempre co\xf1o</foo>"
    print repr(tag_parse(xml.encode('utf-8'))._to_xml())


if __name__ == '__main__': main()
