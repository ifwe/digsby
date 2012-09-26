import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd
##############################

class wsu_oasis:
    targetNamespace = NS.OASIS.UTILITY

    class tTimestampFault_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.OASIS.UTILITY
        type = (schema, "tTimestampFault")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class AttributedDateTime_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.OASIS.UTILITY
        type = (schema, "AttributedDateTime")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class AttributedURI_Def(ZSI.TC.URI, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.OASIS.UTILITY
        type = (schema, "AttributedURI")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.URI.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class TimestampType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.OASIS.UTILITY
        type = (schema, "TimestampType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsu_oasis.TimestampType_Def.schema
            TClist = [GED(NS.OASIS.UTILITY,"Created",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.OASIS.UTILITY,"Expires",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Created = None
                    self._Expires = None
                    self._any = []
                    return
            Holder.__name__ = "TimestampType_Holder"
            self.pyclass = Holder

    class Timestamp_Dec(ElementDeclaration):
        literal = "Timestamp"
        schema = NS.OASIS.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.UTILITY,"Timestamp")
            kw["aname"] = "_Timestamp"
            if wsu_oasis.TimestampType_Def not in wsu_oasis.Timestamp_Dec.__bases__:
                bases = list(wsu_oasis.Timestamp_Dec.__bases__)
                bases.insert(0, wsu_oasis.TimestampType_Def)
                wsu_oasis.Timestamp_Dec.__bases__ = tuple(bases)

            wsu_oasis.TimestampType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Timestamp_Dec_Holder"

    class Expires_Dec(ElementDeclaration):
        literal = "Expires"
        schema = NS.OASIS.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.UTILITY,"Expires")
            kw["aname"] = "_Expires"
            if wsu_oasis.AttributedDateTime_Def not in wsu_oasis.Expires_Dec.__bases__:
                bases = list(wsu_oasis.Expires_Dec.__bases__)
                bases.insert(0, wsu_oasis.AttributedDateTime_Def)
                wsu_oasis.Expires_Dec.__bases__ = tuple(bases)

            wsu_oasis.AttributedDateTime_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Expires_Dec_Holder"

    class Created_Dec(ElementDeclaration):
        literal = "Created"
        schema = NS.OASIS.UTILITY
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.UTILITY,"Created")
            kw["aname"] = "_Created"
            if wsu_oasis.AttributedDateTime_Def not in wsu_oasis.Created_Dec.__bases__:
                bases = list(wsu_oasis.Created_Dec.__bases__)
                bases.insert(0, wsu_oasis.AttributedDateTime_Def)
                wsu_oasis.Created_Dec.__bases__ = tuple(bases)

            wsu_oasis.AttributedDateTime_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Created_Dec_Holder"

# end class wsu_oasis (tns: http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd)
