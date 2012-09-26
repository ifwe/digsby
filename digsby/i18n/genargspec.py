#__LICENSE_GOES_HERE__
# -*- coding: utf-8 -*-

def get_argspec(encodings = ['', 'l', 'u'],
                domains   = ['', 'd'],
                plurals   = ['', 'n'],
                contexts  = ['', 'p'],
                postfix='gettext',
                spec=True):
    out = []
    for context in contexts:
        for domain in domains:
            for plural in plurals:
                for encoding in encodings:
                    positions = ['1based', 'domain', 'context', 'm1', 'm2']
                    if not plural:
                        positions.remove('m2')
                    if not domain:
                        positions.remove('domain')
                    if not context:
                        positions.remove('context')
                    argspec = []
                    if context:
                        argspec.append('%dc' % positions.index('context'))
                    argspec.append('%d' % positions.index('m1'))
                    if plural:
                        argspec.append('%d' % positions.index('m2'))
                    out.append(encoding + domain + plural + context + postfix + \
                               (':' + ','.join(argspec) if spec else ''))
    return out

if __name__ == "__main__":
    print "base:"
    print get_argspec(encodings=[''], spec=False)
    print "local:"
    print get_argspec(encodings=['l'], spec=False)
    print "unicode:"
    print get_argspec(encodings=['u'], spec=False)
