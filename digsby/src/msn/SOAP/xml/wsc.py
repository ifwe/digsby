import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://schemas.xmlsoap.org/ws/2005/02/sc
##############################

class wsc:
    # We use the proper name WSTRUST200502 instead of the alias WSTRUST
    # because not all WSTRUST versions have the CONV namespace.
    targetNamespace = NS.WSTRUST200502.CONV

    class SecurityContextTokenType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST200502.CONV
        type = (schema, "SecurityContextTokenType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsc.SecurityContextTokenType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.OASIS.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "SecurityContextTokenType_Holder"
            self.pyclass = Holder

    class DerivedKeyTokenType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST200502.CONV
        type = (schema, "DerivedKeyTokenType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsc.DerivedKeyTokenType_Def.schema
            TClist = [GED(NS.OASIS.WSSE,"SecurityTokenReference",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GTD(NS.WSTRUST200502.CONV,"PropertiesType",lazy=False)(pname=(ns,"Properties"), aname="_Properties", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TCnumbers.IunsignedLong(pname=(ns,"Generation"), aname="_Generation", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TCnumbers.IunsignedLong(pname=(ns,"Offset"), aname="_Offset", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TCnumbers.IunsignedLong(pname=(ns,"Length"), aname="_Length", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GED(NS.WSTRUST200502.CONV,"Label",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST200502.CONV,"Nonce",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.OASIS.UTILITY,"Id")] = ZSI.TC.AnyType()
                self.attribute_typecode_dict["Algorithm"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._SecurityTokenReference = None
                    self._Properties = None
                    self._Generation = None
                    self._Offset = None
                    self._Length = None
                    self._Label = None
                    self._Nonce = None
                    return
            Holder.__name__ = "DerivedKeyTokenType_Holder"
            self.pyclass = Holder

    class PropertiesType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST200502.CONV
        type = (schema, "PropertiesType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsc.PropertiesType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "PropertiesType_Holder"
            self.pyclass = Holder

    class FaultCodeType_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSTRUST200502.CONV
        type = (schema, "FaultCodeType")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class FaultCodeOpenEnumType_Def(ZSI.TC.Union, TypeDefinition):
        memberTypes = [(NS.WSTRUST200502.CONV, u'FaultCodeType'), (NS.SCHEMA.BASE, u'QName')]
        schema = NS.WSTRUST200502.CONV
        type = (schema, "FaultCodeOpenEnumType")
        def __init__(self, pname, **kw):
            ZSI.TC.Union.__init__(self, pname, **kw)

    class SecurityContextToken_Dec(ElementDeclaration):
        literal = "SecurityContextToken"
        schema = NS.WSTRUST200502.CONV
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST200502.CONV,"SecurityContextToken")
            kw["aname"] = "_SecurityContextToken"
            if wsc.SecurityContextTokenType_Def not in wsc.SecurityContextToken_Dec.__bases__:
                bases = list(wsc.SecurityContextToken_Dec.__bases__)
                bases.insert(0, wsc.SecurityContextTokenType_Def)
                wsc.SecurityContextToken_Dec.__bases__ = tuple(bases)

            wsc.SecurityContextTokenType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SecurityContextToken_Dec_Holder"

    class Identifier_Dec(ZSI.TC.URI, ElementDeclaration):
        literal = "Identifier"
        schema = NS.WSTRUST200502.CONV
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST200502.CONV,"Identifier")
            kw["aname"] = "_Identifier"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_Identifier_immutable_holder"
            ZSI.TC.URI.__init__(self, **kw)

    class Instance_Dec(ZSI.TC.String, ElementDeclaration):
        literal = "Instance"
        schema = NS.WSTRUST200502.CONV
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST200502.CONV,"Instance")
            kw["aname"] = "_Instance"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_Instance_immutable_holder"
            ZSI.TC.String.__init__(self, **kw)

    class DerivedKeyToken_Dec(ElementDeclaration):
        literal = "DerivedKeyToken"
        schema = NS.WSTRUST200502.CONV
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST200502.CONV,"DerivedKeyToken")
            kw["aname"] = "_DerivedKeyToken"
            if wsc.DerivedKeyTokenType_Def not in wsc.DerivedKeyToken_Dec.__bases__:
                bases = list(wsc.DerivedKeyToken_Dec.__bases__)
                bases.insert(0, wsc.DerivedKeyTokenType_Def)
                wsc.DerivedKeyToken_Dec.__bases__ = tuple(bases)

            wsc.DerivedKeyTokenType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "DerivedKeyToken_Dec_Holder"

    class Name_Dec(ZSI.TC.URI, ElementDeclaration):
        literal = "Name"
        schema = NS.WSTRUST200502.CONV
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST200502.CONV,"Name")
            kw["aname"] = "_Name"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_Name_immutable_holder"
            ZSI.TC.URI.__init__(self, **kw)

    class Label_Dec(ZSI.TC.String, ElementDeclaration):
        literal = "Label"
        schema = NS.WSTRUST200502.CONV
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST200502.CONV,"Label")
            kw["aname"] = "_Label"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_Label_immutable_holder"
            ZSI.TC.String.__init__(self, **kw)

    class Nonce_Dec(ZSI.TC.Base64String, ElementDeclaration):
        literal = "Nonce"
        schema = NS.WSTRUST200502.CONV
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST200502.CONV,"Nonce")
            kw["aname"] = "_Nonce"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_Nonce_immutable_holder"
            ZSI.TC.Base64String.__init__(self, **kw)

# end class wsc (tns: http://schemas.xmlsoap.org/ws/2005/02/sc)
