#__LICENSE_GOES_HERE__
'''
commandline interface to buildbot status
'''

import sys
import time
from optparse import OptionParser
from xmlrpclib import ServerProxy

DEFAULT_XMLRPC_URL = 'http://mini/buildbot/xmlrpc'

def green(xmlrpc = DEFAULT_XMLRPC_URL):
    '''
    Returns true if all buildbots are green.
    '''

    return BuildBotClient(xmlrpc).recent_builds_status()

def main():
    parser = OptionParser()
    parser.add_option('--xmlrpc-url', dest='rpcurl')
    parser.set_defaults(rpcurl=DEFAULT_XMLRPC_URL)

    opts, args = parser.parse_args()

    client = BuildBotClient(opts.rpcurl)
    sys.exit(-1 if not client.recent_builds_status() else 0)

class BuildBotClient(object):
    def __init__(self, uri):
        self.server = ServerProxy(uri)

    def recent_builds_status(self):
        success = True
        builders = self.server.getAllBuilders()

        print 'builder results:'
        for builder in builders:
            result = self.server.getLastBuildResults(builder)
            print '  %s - %s' % (builder, result)
            success = success and result != 'failure'

        return success

def asunix(d):
    return time.mktime(d.timetuple())



if __name__ == '__main__':
    main()
