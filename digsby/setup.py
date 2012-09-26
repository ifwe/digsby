'''


Run me to create an EXE


'''

if __name__ == '__main__':

    import sys, os
    sys.path.insert(0, "src")
    from distutils.core import setup
    import py2exe

    # If run without args, build executables
    if len(sys.argv) == 1:
        sys.argv.append("py2exe")
        #sys.argv.append("-q")

    class Target:
        def __init__(self, **kw):
            self.version = "0.0.1"
            self.copyright = "(c)2006"
            self.__dict__.update(kw)

    manifest_template = '''
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
    <assemblyIdentity
        version="5.0.0.0"
        processorArchitecture="x86"
        name="%(prog)s"
        type="win32"
    />
    <description>%(prog)s Program</description>
    <dependency>
        <dependentAssembly>
            <assemblyIdentity
                type="win32"
                name="Microsoft.Windows.Common-Controls"
                version="6.0.0.0"
                processorArchitecture="X86"
                publicKeyToken="6595b64144ccf1df"
                language="*"
            />
        </dependentAssembly>
    </dependency>
    </assembly>
    '''

    RT_MANIFEST = 24

    digsby_exe = Target(
        # these values appear in explorer.exe's description
        name =         'digsby',
        description =  'multiprotocol IM client',
        version =      '0.0.1',
        company_name = 'dotSyntax',
        copyright =    'copyright 2006 dotSyntax LLC.',

        # what to build
        dest_base =   'digsby',        # .exe to build
        script    =   'Digsby.py',     # main script
        other_resources = [
           (RT_MANIFEST, 1, manifest_template % {"prog":"digsby"})
        ],
        icon_resources = [(1, "res/digsby.ico")],

        includes = ['src','lib','../pyxmpp'],
        optimize = 2,
        bundle_files = 3,
    )

    setup( console=[digsby_exe], windows = [digsby_exe] )

