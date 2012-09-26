'''
copies digsby TRUNK to tags named after the time
'''

digsbyroot = 'http://mini/svn/dotSyntax/digsby'

import os
import sys
from datetime import datetime


def shell(cmd):
    print cmd

    proc = os.popen(cmd)
    res = proc.read()
    print res
    retCode = proc.close()
    if retCode is not None:
        raise Exception('subprocess %r failed with error %s' % (cmd, retCode))

    return res

def timestamp():
    'iso formatted utcnow without secs and microsecs'
    return datetime.utcnow().isoformat('_')[:-10]

def dotag(m='Tagging for release'):
    t = timestamp()
    message = '%s at %s' % (m, t)
    shell('svn copy %s/trunk %s/tags/%s -m "%s"' % (digsbyroot, digsbyroot, t, message))

def dobranch(m='Branching for release'):
    t = timestamp()
    message = '%s at %s' % (m, t)

    from package import _get_svn_rev
    rev = _get_svn_rev(['%s/trunk' % digsbyroot])
    branchname = 'maint-%s' % rev
    shell('svn copy %s/trunk %s/branches/%s -m "%s"' % (digsbyroot, digsbyroot, branchname, message))

if __name__ == '__main__':
    operation = sys.argv[1]
    if operation == 'branch':
        do = dobranch
    elif operation == 'tag':
        do = dotag
    else:
        raise Exception("Unknown operation %r" % operation)

    if len(sys.argv) > 2:
        do(sys.argv[1])
    else:
        do()
