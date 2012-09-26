#!/usr/bin/env python
'''
    loginitem: shell tool to add/remove/query login items
    requires the PyObjC bridge and Python >= 2.3

    examples:

        loginitem --add /Applications/Utilities/Terminal.app
        loginitem --exists Terminal && echo "added successfully"
        loginitem --remove Terminal
'''

__author__  = 'Daniel Sandler (dsandler!toastycode.com)'
__date__    = '26-JUL-2007'
__license__ = 'BSD' # see __full_license__ at end of file
__version__ = '1.0'
__URL__     = 'http://toastycode.com/loginitem'
__usage__   = '''loginitem v%s: manipulate login items of currently logged-in user

usage:
  loginitem -a|--add[-hidden] <path> | add a login item by full path
  loginitem -r|--remove <appname>    | remove an item by name (not path!)
  loginitem -e|--exists <appname>    | exit code is 0 if exists, 1 otherwise
  loginitem -c|--count               | number of login items
  loginitem -l|--list                | list of item names, one per line, UTF-8
  loginitem -L|--list-paths          | list of item paths, one per line, UTF-8
''' % __version__

import getopt
import os
import sys
from codecs import utf_8_decode, utf_8_encode

class AppleEventError(Exception): pass

def doscript(x):
    from AppKit import NSAppleScript
    res = NSAppleScript.alloc().initWithSource_(x)\
        .executeAndReturnError_()
    if not res[1]: return res[0]
    raise AppleEventError(res[1])

def tellsysevent(x):
    return doscript('tell application "System Events" to %s' % x)

def usage(): sys.stdout.write(__usage__)

def aedesc_list_iter(d):
    for i in range(1,(d.numberOfItems()+1)):
        yield d.descriptorAtIndex_(i)

def die(why=None, code=1, showusage=False):
    if why: sys.stderr.write(why + "\n")
    if showusage: usage()
    sys.exit(code)
    
def hasitem(app):
    return tellsysevent('get exists login item "%s"' % app).booleanValue()

def additem(path, hidden=False):
    tellsysevent('make new login item with properties \
    { path: "%s", hidden:%s } at end' % (
        path, str(hidden))
        )
        
def removeitem(app):
    if hasitem(app):
        tellsysevent('delete login item "%s"' % app)
        return True
    else:
        return False

def main(args):
    try:
        opts, args = getopt.getopt(args,
            'hca:d:e:lL',
            ['help','count','add=','add-hidden=',
             'delete=','remove=','exists=','list','list-paths'])
    except getopt.GetoptError, e:
        die("error: %s" % str(e), showusage=True)

    try:
        for o, a in opts:
            if o in ('-a','--add','--add-hidden'):
                additem(utf_8_decode(a)[0], str(o == '--add-hidden'))
                sys.exit()
            elif o in ('-d','--remove','--delete'):
                app = utf_8_decode(a)[0]
                if not removeitem(app):
                    die('error: login item "%s" does not exist' % a)
                sys.exit()
            elif o in ('-e','--exists'):
                result = tellsysevent('get exists login item "%s"' %
                    utf_8_decode(a)[0]).stringValue()
                sys.exit({'true':0}.get(result,1))
            elif o in ('-c','--count'):
                print tellsysevent('get number of login items').stringValue()
                sys.exit()
            elif o in ('-l','--list','-L','--list-paths'):
                what = {True:'name',False:'path'}[o in ('-l','--list')]
                print '\n'.join(
                    [utf_8_encode(x.stringValue())[0]
                        for x in aedesc_list_iter(
                            tellsysevent('get %s of every login item'
                                % what))])
                sys.exit()
            elif o in ('-h', '--help'):
                usage()
                sys.exit()
    except AppleEventError, e:
        die("applescript error: " + str(e))
    
    die(showusage=True)

if __name__ == '__main__': main(sys.argv[1:])

license = '''\
* Copyright (c) 2007, Daniel Sandler.
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without
* modification, are permitted provided that the following conditions are met:
*     * Redistributions of source code must retain the above copyright
*       notice, this list of conditions and the following disclaimer.
*     * Redistributions in binary form must reproduce the above copyright
*       notice, this list of conditions and the following disclaimer in the
*       documentation and/or other materials provided with the distribution.
*     * Neither the name of the <organization> nor the
*       names of its contributors may be used to endorse or promote products
*       derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY <copyright holder> ``AS IS'' AND ANY
* EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
* DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
* DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
* (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
* ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
* SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
