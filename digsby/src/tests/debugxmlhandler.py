import libxml2
class DebugXMLHandler(libxml2.SAXCallback):
    """SAX events handler for the python-only stream parser."""
    def __init__(self):
        pass

    def cdataBlock(self, data):
        print 'cdataBlock: %r' %data

    def characters(self, data):
        print 'characters: %r' % data

    def ignorableWhitespace(self, data):
        print 'ignorableWhitespace: %r' % data

    def comment(self, content):
        print 'comment: %r' % content

    def endDocument(self):
        print 'endDocument'

    def endElement(self, tag):
        print 'endElement(%s)' % tag

    def error(self, msg):
        print '### error: %s' % msg
        return True

    def fatalError(self, msg):
        print 'fatalError: %s' % msg

    def reference(self, name):
        print 'reference: &[%s];' % name

    def startDocument(self):
        print 'startDocument'

    def startElement(self, tag, attrs):
        print 'startElement(%r, %r)' % (tag, attrs)

    def warning(self, msg):
        print '### warning: %s' % msg
        return True

    def _stream_start(self,_doc):
        """Process stream start."""
        pass
    
    def stream_start(self,_doc):
        """Process stream start."""
        pass

    def _stream_end(self,_doc):
        """Process stream end."""
        pass

    def stream_end(self,_doc):
        """Process stream end."""
        pass
   
    def _stanza(self,*a):
        pass
