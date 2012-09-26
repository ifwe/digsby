import ZSI.schema as Schema
from wsdl2py import main as generate

import util.network.soap as soap

class MSNBinding(soap.Binding):
    def get_default_headers(self):
        headers = super(MSNBinding, self).get_default_headers()
        headers['User-Agent'] = 'MSN Explorer/9.0 (MSN 8.0; TmstmpExt)'
        # 'User-Agent'   : 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 6.1; WOW64; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; IDCRL 5.000.810.6; IDCRL-cfg 6.0.11409.0; App msnmsgr.exe, 14.0.8089.726, {7108E71A-9926-4FCB-BCC9-9A9D3F32E423})',
        return headers

class MSNBindingSOAP(soap.BindingSOAP):
    BindingClass = MSNBinding

import xml.wsu
import xml.wsu_oasis
import xml.wsrm
import xml.ds
import xml.soapenv
import xml.soapwsa
import xml.wsa
import xml.wsc
import xml.wsp
import xml.wsse
import xml.wst

import Namespaces

import MSNABSharingService
import MSNOIMStoreService
import MSNRSIService
import MSNSecurityTokenService
import MSNSpaceService
import MSNStorageService
import MSSOAPFault

import logging
log = logging.getLogger('msn.SOAP')

MODULES = (
           xml.wsu,
           xml.wsu_oasis,
           xml.wsrm,
           xml.ds,
           xml.soapenv,
           xml.soapwsa,
           xml.wsa,
           xml.wsc,
           xml.wsp,
           xml.wsse,
           xml.wst,
           MSNABSharingService,
           MSNOIMStoreService,
           MSNRSIService,
           MSNSecurityTokenService,
           MSNSpaceService,
           MSNStorageService,
           MSSOAPFault,
           )

#def do_gen(module):
#    import path
#    mod_dir = path.path(module.__file__).parent
#    for wsdlfile in mod_dir.files("*.wsdl"):
#        print wsdlfile
#        generate(file=wsdlfile, output_directory = mod_dir)
#
#for module in (MODULES):
#    do_gen(module)

def set_module_types(module, namespace):
    for clsname in namespace.__dict__:
        if clsname.endswith('_Def') or clsname.endswith('_Dec'):
            name = clsname[:-4]

            if clsname.endswith('_Dec'):
                pyclass = namespace.__dict__[clsname]().pyclass
            else:
                try:
                    pname = (namespace.targetNamespace, name)
                    pyclass = Schema.GTD(*pname)(pname).pyclass
                except AttributeError, e:
                    log.debug("Couldn't find name %s in namespace %s. The underlying error was: %r", name, namespace.targetNamespace, e)
                    continue

            if name in vars(module):
                if vars(module)[name] is not pyclass:
                    log.debug('Found two instances of the name "%s". (%r and %r)', name, vars(module)[name], pyclass)
                continue

            setattr(module, name, pyclass)

for module in MODULES:
    for k, v in vars(module).items():
        if hasattr(v, 'targetNamespace'):
            set_module_types(module, v)

