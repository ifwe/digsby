#!/bin/env python
############################################################################
# Joshua Boverhof<JRBoverhof@lbl.gov>, LBNL
# Monte Goode <MMGoode@lbl.gov>, LBNL
# See Copyright for copyright notice!
###########################################################################
import exceptions, sys, optparse, os, warnings
import ZSI
from ConfigParser import ConfigParser
from ZSI.generate.wsdl2python import WriteServiceModule, ServiceDescription
from ZSI.wstools import WSDLTools, XMLSchema
from ZSI.wstools.logging import setBasicLoggerDEBUG
from ZSI.generate import containers, utility
from ZSI.generate.utility import NCName_to_ClassName as NC_to_CN, TextProtect

"""
wsdl2py

A utility for automatically generating client interface code from a wsdl
definition, and a set of classes representing element declarations and
type definitions.  This will produce two files in the current working
directory named after the wsdl definition name.

eg. <definition name='SampleService'>
    SampleService.py
    SampleService_types.py

"""
warnings.filterwarnings('ignore', '', exceptions.UserWarning)
def SetDebugCallback(option, opt, value, parser, *args, **kwargs):
    setBasicLoggerDEBUG()
    warnings.resetwarnings()


def SetPyclassMetaclass(option, opt, value, parser, *args, **kwargs):
    """set up pyclass metaclass for complexTypes"""
    from ZSI.generate.containers import TypecodeContainerBase, TypesHeaderContainer
    TypecodeContainerBase.metaclass = kwargs['metaclass']
    TypesHeaderContainer.imports.append(\
            'from %(module)s import %(metaclass)s' %kwargs
            )



def formatSchemaObject(fname, schemaObj):
    """ In the case of a 'schema only' generation (-s) this creates
        a fake wsdl object that will function w/in the adapters
        and allow the generator to do what it needs to do.
    """

    class fake:
        pass

    f = fake()

    if fname.rfind('/'):
        tmp = fname[fname.rfind('/') + 1 :].split('.')
    else:
        tmp = fname.split('.')

    f.name  = tmp[0] + '_' + tmp[1]
    f.types = { schemaObj.targetNamespace : schemaObj }

    return f

if __name__ == '__main__':
    def doCommandLine(**kw):
        op = optparse.OptionParser()

        # Basic options
        op.add_option("-f", "--file",
                      action="store", dest="file", default=None, type="string",
                      help="file to load wsdl from")
        op.add_option("-u", "--url",
                      action="store", dest="url", default=None, type="string",
                      help="URL to load wsdl from")
        op.add_option("-x", "--schema",
                      action="store_true", dest="schema", default=False,
                      help="process just the schema from an xsd file [no services]")
        op.add_option("-d", "--debug",
                      action="callback", callback=SetDebugCallback,
                      help="debug output")

        # WS Options
        op.add_option("-a", "--address",
                      action="store_true", dest="address", default=False,
                      help="ws-addressing support, must include WS-Addressing schema.")

        # pyclass Metaclass
        op.add_option("-b", "--complexType",
                      action="callback", callback=SetPyclassMetaclass,
                      callback_kwargs={'module':'ZSI.generate.pyclass',
                          'metaclass':'pyclass_type'},
                      help="add convenience functions for complexTypes, including Getters, Setters, factory methods, and properties (via metaclass).")

        # Extended generation options
        op.add_option("-e", "--extended",
                      action="store_true", dest="extended", default=False,
                      help="Do Extended code generation.")
        op.add_option("-z", "--aname",
                      action="store", dest="aname", default=None, type="string",
                      help="pass in a function for attribute name creation")
        op.add_option("-t", "--types",
                      action="store", dest="types", default=None, type="string",
                      help="file to load types from")
        op.add_option("-o", "--output-dir",
                      action="store", dest="output_directory", default=".", type="string",
                      help="file to load types from")
        op.add_option("-s", "--simple-naming",
                      action="store_true", dest="simple_naming", default=False,
                      help="Simplify generated naming.")
        op.add_option("-c", "--clientClassSuffix",
                      action="store", dest="clientClassSuffix", default=None, type="string",
                      help="Suffix to use for service client class (default \"SOAP\")")
        op.add_option("-m", "--pyclassMapModule",
                      action="store", dest="pyclassMapModule", default=None, type="string",
                      help="Python file that maps external python classes to a schema type.  The classes are used as the \"pyclass\" for that type.  The module should contain a dict() called mapping in the format: mapping = {schemaTypeName:(moduleName.py,className) }")

        (options, args) = op.parse_args()

        print options

        return options, args

else:
    def doCommandLine(complexType=True, debug=False, **kw):
        from util import Storage

        if debug:
            SetDebugCallback(None,None,None,None)

        if complexType:
            SetPyclassMetaclass(None,None,None,None,
                                **{'module':'ZSI.generate.pyclass',
                                   'metaclass':'pyclass_type'}
                                )

        options = Storage(
                          file=None,
                          url=None,
                          schema=False,
                          simple_naming=False,
                          clientClassSuffix=None,
                          aname=None,
                          pyclassMapModule=None,
                          address=False,
                          extended=False,
                          types=None,
                          output_directory='.',
                          )

        options.update(kw)

        return options, ()


def main(**kw):
    """ From a wsdl definition create a wsdl object and run the wsdl2python
        generator.
    """

    options, args = doCommandLine(**kw)

    location = options.file or options.url
    if options.schema is True:
        reader = XMLSchema.SchemaReader(base_url=location)
    else:
        reader = WSDLTools.WSDLReader()

    wsdl = None
    if options.file is not None:
        wsdl = reader.loadFromFile(location)
    elif options.url is not None:
        wsdl = reader.loadFromURL(location)

    if options.simple_naming:
        # Use a different client suffix
        WriteServiceModule.client_module_suffix = "_client"
        # Write messages definitions to a separate file.
        ServiceDescription.separate_messages = True
        # Use more simple type and element class names
        containers.SetTypeNameFunc( lambda n: '%s_' %(NC_to_CN(n)) )
        containers.SetElementNameFunc( lambda n: '%s' %(NC_to_CN(n)) )
        # Don't add "_" to the attribute name (remove when --aname works well)
        containers.ContainerBase.func_aname = lambda instnc,n: TextProtect(str(n))
        # write out the modules with their names rather than their number.
        utility.namespace_name = lambda cls, ns: utility.Namespace2ModuleName(ns)

    if options.clientClassSuffix:
        from ZSI.generate.containers import ServiceContainerBase
        ServiceContainerBase.clientClassSuffix = options.clientClassSuffix

    assert wsdl is not None, 'Must specify WSDL either with --file or --url'
    if options.schema is True:
        wsdl = formatSchemaObject(location, wsdl)

    if options.aname is not None:
        args = options.aname.rsplit('.',1)
        assert len(args) == 2, 'expecting module.function'
        # The following exec causes a syntax error.
        #exec('from %s import %s as FUNC' %(args[0],args[1]))
        assert callable(FUNC),\
            '%s must be a callable method with one string parameter' %options.aname
        from ZSI.generate.containers import TypecodeContainerBase
        TypecodeContainerBase.func_aname = staticmethod(FUNC)

    if options.pyclassMapModule != None:
        mod = __import__(options.pyclassMapModule)
        components = options.pyclassMapModule.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        extPyClasses = mod.mapping
    else:
        extPyClasses = None

    wsm = WriteServiceModule(wsdl, addressing=options.address, do_extended=options.extended, extPyClasses=extPyClasses)
    if options.types != None:
        wsm.setTypesModuleName(options.types)
    if options.schema is False:
         fd = open(os.path.join(options.output_directory, '%s.py' %wsm.getClientModuleName()), 'w+')
         # simple naming writes the messages to a separate file
         if not options.simple_naming:
             wsm.writeClient(fd)
         else: # provide a separate file to store messages to.
             msg_fd = open(os.path.join(options.output_directory, '%s.py' %wsm.getMessagesModuleName()), 'w+')
             wsm.writeClient(fd, msg_fd=msg_fd)
             msg_fd.close()
         fd.close()

    fd = open( os.path.join(options.output_directory, '%s.py' %wsm.getTypesModuleName()), 'w+')
    wsm.writeTypes(fd)
    fd.close()


if __name__ == '__main__':
    main()
