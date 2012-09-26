from __future__ import with_statement

if __name__ == '__main__':
    import gettext; gettext.install('Digsby')

from gui.imwin.styles.stripformatting import *


def printline(): print '*'*80

if __name__ == '__main__2':

    #print remove_style('background: blue;', 'background')


    s = soupify('<font face="verdana" back="red"><span style="background: blue;">test</span></font>')

    print convert_back(s)

    #convert_back(s)
    #print s.prettify()


if __name__ == '__main__3':

    with file('formattedhtml.html', 'r') as f:
        t = f.read()

    def dorun(t, msg, formatting, colors):
        print 'stripping', msg
        printline()
        print strip(t, formatting = formatting, colors = colors)

    dorun(t, 'everything', formatting = True, colors = True)
    dorun(t, 'formatting', formatting = True, colors = False)
    dorun(t, 'colors',     formatting = False, colors = True)

if __name__ == '__main__4':
    t = '<HTML><BODY BGCOLOR="#ffffff"><B><FONT COLOR="#0000ff" LANG="0">ok </B></FONT></BODY></HTML>'

    #print t
    #print soupify(t)
    import sys

    sys.stdout.flush()
    t = strip(t, formatting = True, colors = False, emoticons = False)

    for x in xrange(5): sys.stderr.flush()

    print
    print
    print t

if __name__ == '__main__':
    text = 'http://www.amazon.com/gp/offer-listing/B0009VXBAQ/ref=dp_olp_1?ie=UTF8&qid=1210776182&sr=1-1'
    soup = soupify(text)
    print soup
#    removed = defaultdict(list)
#    print strip_formatting(soup, removed)
#    print removed
#    print soup

