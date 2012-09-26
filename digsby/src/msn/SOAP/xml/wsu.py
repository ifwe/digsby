import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://schemas.xmlsoap.org/ws/2002/07/utility
##############################

class wsu:
    targetNamespace = NS.WSU.UTILITY

    class tTimestampFault_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSU.UTILITY
        type = (schema, "tTimestampFault")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class tContextFault_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSU.UTILITY
        type = (schema, "tContextFault")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class AttributedDateTime_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSU.UTILITY
        type = (schema, "AttributedDateTime")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["ValueType"] = ZSI.TC.QName()
            self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class ReceivedType_Def(TypeDefinition):
        # ComplexType/SimpleContent derivation of user-defined type
        schema = NS.WSU.UTILITY
        type = (schema, "ReceivedType")
        def __init__(self, pname, **kw):
            ns = wsu.ReceivedType_Def.schema
            if wsu.AttributedDateTime_Def not in wsu.ReceivedType_Def.__bases__:
                bases = list(wsu.ReceivedType_Def.__bases__)
                bases.insert(0, wsu.AttributedDateTime_Def)
                wsu.ReceivedType_Def.__bases__ = tuple(bases)

            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Delay"] = ZSI.TCnumbers.Iint()
            self.attribute_typecode_dict["Actor"] = ZSI.TC.URI()
            wsu.AttributedDateTime_Def.__init__(self, pname, **kw)

    class AttributedURI_Def(ZSI.TC.URI, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSU.UTILITY
        type = (schema, "AttributedURI")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.URI.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class TimestampType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSU.UTILITY
        type = (schema, "TimestampType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsu.TimestampType_Def.schema
            TClist = [GED(NS.WSU.UTILITY,"Created",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSU.UTILITY,"Expires",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSU.UTILITY,"Received",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Created = None
                    self._Expires = None
                    self._Received = None
                    self._any = []
                    return
            Holder.__name__ = "TimestampType_Holder"
            self.pyclass = Holder

    class ContextType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSU.UTILITY
        type = (schema, "ContextType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsu.ContextType_Def.schema
            TClist = [GED(NS.WSU.UTILITY,"Expires",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSU.UTILITY,"Identifier",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Expires = None
                    self._Identifier = None
                    return
            Holder.__name__ = "ContextType_Holder"
            self.pyclass = Holder

    class PortReferenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSU.UTILITY
        type = (schema, "PortReferenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsu.PortReferenceType_Def.schema
            TClist = [GTD(NS.WSU.UTILITY,"AttributedURI",lazy=False)(pname=(ns,"Address"), aname="_Address", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
                self.attribute_typecode_dict[(NS.WSU.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Address = None
                    self._any = []
                    return
            Holder.__name__ = "PortReferenceType_Holder"
            self.pyclass = Holder

    class Timestamp_Dec(ElementDeclaration):
        literal = "Timestamp"
        schema = NS.WSU.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSU.UTILITY,"Timestamp")
            kw["aname"] = "_Timestamp"
            if wsu.TimestampType_Def not in wsu.Timestamp_Dec.__bases__:
                bases = list(wsu.Timestamp_Dec.__bases__)
                bases.insert(0, wsu.TimestampType_Def)
                wsu.Timestamp_Dec.__bases__ = tuple(bases)

            wsu.TimestampType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Timestamp_Dec_Holder"

    class Expires_Dec(ElementDeclaration):
        literal = "Expires"
        schema = NS.WSU.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSU.UTILITY,"Expires")
            kw["aname"] = "_Expires"
            if wsu.AttributedDateTime_Def not in wsu.Expires_Dec.__bases__:
                bases = list(wsu.Expires_Dec.__bases__)
                bases.insert(0, wsu.AttributedDateTime_Def)
                wsu.Expires_Dec.__bases__ = tuple(bases)

            wsu.AttributedDateTime_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Expires_Dec_Holder"

    class Created_Dec(ElementDeclaration):
        literal = "Created"
        schema = NS.WSU.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSU.UTILITY,"Created")
            kw["aname"] = "_Created"
            if wsu.AttributedDateTime_Def not in wsu.Created_Dec.__bases__:
                bases = list(wsu.Created_Dec.__bases__)
                bases.insert(0, wsu.AttributedDateTime_Def)
                wsu.Created_Dec.__bases__ = tuple(bases)

            wsu.AttributedDateTime_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Created_Dec_Holder"

    class Received_Dec(ElementDeclaration):
        literal = "Received"
        schema = NS.WSU.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSU.UTILITY,"Received")
            kw["aname"] = "_Received"
            if wsu.ReceivedType_Def not in wsu.Received_Dec.__bases__:
                bases = list(wsu.Received_Dec.__bases__)
                bases.insert(0, wsu.ReceivedType_Def)
                wsu.Received_Dec.__bases__ = tuple(bases)

            wsu.ReceivedType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Received_Dec_Holder"

    class Identifier_Dec(ElementDeclaration):
        literal = "Identifier"
        schema = NS.WSU.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSU.UTILITY,"Identifier")
            kw["aname"] = "_Identifier"
            if wsu.AttributedURI_Def not in wsu.Identifier_Dec.__bases__:
                bases = list(wsu.Identifier_Dec.__bases__)
                bases.insert(0, wsu.AttributedURI_Def)
                wsu.Identifier_Dec.__bases__ = tuple(bases)

            wsu.AttributedURI_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Identifier_Dec_Holder"

    class Context_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "Context"
        schema = NS.WSU.UTILITY
        def __init__(self, **kw):
            ns = wsu.Context_Dec.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            kw["pname"] = (NS.WSU.UTILITY,"Context")
            kw["aname"] = "_Context"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "Context_Holder"
            self.pyclass = Holder

    class PortReference_Dec(ElementDeclaration):
        literal = "PortReference"
        schema = NS.WSU.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSU.UTILITY,"PortReference")
            kw["aname"] = "_PortReference"
            if wsu.PortReferenceType_Def not in wsu.PortReference_Dec.__bases__:
                bases = list(wsu.PortReference_Dec.__bases__)
                bases.insert(0, wsu.PortReferenceType_Def)
                wsu.PortReference_Dec.__bases__ = tuple(bases)

            wsu.PortReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "PortReference_Dec_Holder"

# end class wsu (tns: http://schemas.xmlsoap.org/ws/2002/07/utility)

