import sys

RT_MANIFEST = 24
DEBUG = hasattr(sys, 'gettotalrefcount')
if DEBUG:
    WINXP_MANIFEST = '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
    <noInheritable></noInheritable>
    <assemblyIdentity type="win32" name="Microsoft.VC90.DebugCRT" version="9.0.30729.1" processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b"></assemblyIdentity>
    <file name="msvcr90d.dll" hashalg="SHA1" hash="77c2dcb12982a6855302844f8803e68ce360fcc9"><asmv2:hash xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#"><dsig:Transforms><dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity"></dsig:Transform></dsig:Transforms><dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></dsig:DigestMethod><dsig:DigestValue>WA59/AbhIDaZgmB1cN9MFlDi2g4=</dsig:DigestValue></asmv2:hash></file> <file name="msvcp90d.dll" hashalg="SHA1" hash="b2fa2a05ee7e6a2595c16547246753a62e9bf398"><asmv2:hash xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#"><dsig:Transforms><dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity"></dsig:Transform></dsig:Transforms><dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></dsig:DigestMethod><dsig:DigestValue>Rxofhw9S95owIW2MDmCg2zStQgs=</dsig:DigestValue></asmv2:hash></file> <file name="msvcm90d.dll" hashalg="SHA1" hash="6cfc0c6330724d86db3e2ef295d4e1d75a43514a"><asmv2:hash xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#"><dsig:Transforms><dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity"></dsig:Transform></dsig:Transforms><dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></dsig:DigestMethod><dsig:DigestValue>iOxEMZK3fufMDQFuKGZ4VdAYzWY=</dsig:DigestValue></asmv2:hash></file>
</assembly>'''
else:
    WINXP_MANIFEST = '''
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
    <assemblyIdentity
        version="5.0.0.0"
        processorArchitecture="x86"
        name="Program"
        type="win32"
    />
    <description>Program</description>
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



if DEBUG:
    manifest = '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
    <noInheritable></noInheritable>
    <assemblyIdentity type="win32" name="Microsoft.VC90.DebugCRT" version="9.0.30729.1" processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b"></assemblyIdentity>
    <file name="msvcr90d.dll" hashalg="SHA1" hash="77c2dcb12982a6855302844f8803e68ce360fcc9"><asmv2:hash xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#"><dsig:Transforms><dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity"></dsig:Transform></dsig:Transforms><dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></dsig:DigestMethod><dsig:DigestValue>WA59/AbhIDaZgmB1cN9MFlDi2g4=</dsig:DigestValue></asmv2:hash></file> <file name="msvcp90d.dll" hashalg="SHA1" hash="b2fa2a05ee7e6a2595c16547246753a62e9bf398"><asmv2:hash xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#"><dsig:Transforms><dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity"></dsig:Transform></dsig:Transforms><dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></dsig:DigestMethod><dsig:DigestValue>Rxofhw9S95owIW2MDmCg2zStQgs=</dsig:DigestValue></asmv2:hash></file> <file name="msvcm90d.dll" hashalg="SHA1" hash="6cfc0c6330724d86db3e2ef295d4e1d75a43514a"><asmv2:hash xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#"><dsig:Transforms><dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity"></dsig:Transform></dsig:Transforms><dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"></dsig:DigestMethod><dsig:DigestValue>iOxEMZK3fufMDQFuKGZ4VdAYzWY=</dsig:DigestValue></asmv2:hash></file>

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

</assembly>'''

    msvc9_private_assembly = '''\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
    <noInheritable></noInheritable>
    <assemblyIdentity type="win32" name="Microsoft.VC90.DebugCRT" version="9.0.30729.1" processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b"></assemblyIdentity>
    %s
</assembly>'''
else:
    manifest = '''<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
    <assembly xmlns='urn:schemas-microsoft-com:asm.v1' manifestVersion='1.0'>'''
    manifest += '''
      <dependency>
        <dependentAssembly>
          <assemblyIdentity
                type='win32'
                name='Microsoft.VC90.CRT'
                version='9.0.21022.8'
                processorArchitecture='x86'
                publicKeyToken='1fc8b3b9a1e18e3b'
            />
        </dependentAssembly>
      </dependency>'''
    manifest+='''  <dependency>
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
    </assembly>'''

    msvc9_private_assembly = '''\
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <!-- Copyright (c) Microsoft Corporation.  All rights reserved. -->
    <assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
        <noInheritable/>
        <assemblyIdentity
            type="win32"
            name="Microsoft.VC90.CRT"
            version="9.0.21022.8"
            processorArchitecture="x86"
            publicKeyToken="1fc8b3b9a1e18e3b"
        />
        %s
    </assembly>'''

