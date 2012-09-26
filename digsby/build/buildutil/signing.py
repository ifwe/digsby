#__LICENSE_GOES_HERE__
from buildutil.buildfileutils import run
from buildutil.promptlib import prompt

def Authenticode(exe):
    print '*** signing executable %r ***' % exe
    # signtool should be in a path like: C:\Program Files\Microsoft SDKs\Windows\v6.0A\Bin
    # Add the directory to your %PATH%

    # You may also need the latest CAPICOM SDK, which was last seen at
    # http://www.microsoft.com/download/en/details.aspx?DisplayLang=en&id=25281
    try:
        run(["signtool", "sign", "/a", "/t", "http://timestamp.verisign.com/scripts/timstamp.dll", str(exe)])
    except Exception, e:
        print '\t\tError signing executable %r: %r' % (exe, e)
        keep_going = prompt("Continue?", bool, False)

        if not keep_going:
            raise e
    else:
        print '*** signed %r ***' % exe

