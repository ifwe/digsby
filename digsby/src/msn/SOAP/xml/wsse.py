import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type


##############################
# targetNamespace
# http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd
##############################

class wsse:
    targetNamespace = NS.OASIS.WSSE

    class SecurityTokenReferenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.OASIS.WSSE
        type = (schema, "SecurityTokenReferenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsse.SecurityTokenReferenceType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax"), GED(NS.OASIS.WSSE,"Reference",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.String()
                self.attribute_typecode_dict["Usage"] = ZSI.TC.String()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    self._Reference = None
                    return
            Holder.__name__ = "SecurityTokenReferenceType_Holder"
            self.pyclass = Holder

    class SecurityHeaderType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.OASIS.WSSE
        type = (schema, "SecurityHeaderType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsse.SecurityHeaderType_Def.schema
            TClist = [GED(NS.OASIS.WSSE,"UsernameToken",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")),
                      GED(NS.OASIS.UTILITY,"Timestamp",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")),
                      #GED("urn:oasis:names:tc:SAML:1.0:assertion","Assertion",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))
                      ]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._UsernameToken = None
                    self._Timestamp = None
                    self._Assertion = None
                    return
            Holder.__name__ = "SecurityHeaderType_Holder"
            self.pyclass = Holder

    class UsernameTokenType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.OASIS.WSSE
        type = (schema, "UsernameTokenType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsse.UsernameTokenType_Def.schema
            TClist = [GTD(NS.OASIS.WSSE,"AttributedString",lazy=False)(pname=(ns,"Username"), aname="_Username", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.OASIS.WSSE,"PasswordString",lazy=False)(pname=(ns,"Password"), aname="_Password", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.OASIS.UTILITY,"Id")] = ZSI.TC.AnyType()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Username = None
                    self._Password = None
                    return
            Holder.__name__ = "UsernameTokenType_Holder"
            self.pyclass = Holder

    class AttributedString_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.OASIS.WSSE
        type = (schema, "AttributedString")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Id"] = ZSI.TC.String()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class PasswordString_Def(TypeDefinition):
        # ComplexType/SimpleContent derivation of user-defined type
        schema = NS.OASIS.WSSE
        type = (schema, "PasswordString")
        def __init__(self, pname, **kw):
            ns = wsse.PasswordString_Def.schema
            if wsse.AttributedString_Def not in wsse.PasswordString_Def.__bases__:
                bases = list(wsse.PasswordString_Def.__bases__)
                bases.insert(0, wsse.AttributedString_Def)
                wsse.PasswordString_Def.__bases__ = tuple(bases)

            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            wsse.AttributedString_Def.__init__(self, pname, **kw)

    class EncodedString_Def(TypeDefinition):
        # ComplexType/SimpleContent derivation of user-defined type
        schema = NS.OASIS.WSSE
        type = (schema, "EncodedString")
        def __init__(self, pname, **kw):
            ns = wsse.EncodedString_Def.schema
            if wsse.AttributedString_Def not in wsse.EncodedString_Def.__bases__:
                bases = list(wsse.EncodedString_Def.__bases__)
                bases.insert(0, wsse.AttributedString_Def)
                wsse.EncodedString_Def.__bases__ = tuple(bases)

            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            wsse.AttributedString_Def.__init__(self, pname, **kw)

    class ReferenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.OASIS.WSSE
        type = (schema, "ReferenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsse.ReferenceType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["URI"] = ZSI.TC.URI()
                self.attribute_typecode_dict["ValueType"] = ZSI.TC.QName()
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "ReferenceType_Holder"
            self.pyclass = Holder

    class KeyIdentifierType_Def(TypeDefinition):
        # ComplexType/SimpleContent derivation of user-defined type
        schema = NS.OASIS.WSSE
        type = (schema, "KeyIdentifierType")
        def __init__(self, pname, **kw):
            ns = wsse.KeyIdentifierType_Def.schema
            if wsse.EncodedString_Def not in wsse.KeyIdentifierType_Def.__bases__:
                bases = list(wsse.KeyIdentifierType_Def.__bases__)
                bases.insert(0, wsse.EncodedString_Def)
                wsse.KeyIdentifierType_Def.__bases__ = tuple(bases)

            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            wsse.EncodedString_Def.__init__(self, pname, **kw)

    class BinarySecurityTokenType_Def(TypeDefinition):
        # ComplexType/SimpleContent derivation of user-defined type
        schema = NS.OASIS.WSSE
        type = (schema, "BinarySecurityTokenType")
        def __init__(self, pname, **kw):
            ns = wsse.BinarySecurityTokenType_Def.schema
            if wsse.EncodedString_Def not in wsse.BinarySecurityTokenType_Def.__bases__:
                bases = list(wsse.BinarySecurityTokenType_Def.__bases__)
                bases.insert(0, wsse.EncodedString_Def)
                wsse.BinarySecurityTokenType_Def.__bases__ = tuple(bases)

            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            wsse.EncodedString_Def.__init__(self, pname, **kw)

    class FaultcodeEnum_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.OASIS.WSSE
        type = (schema, "FaultcodeEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class SecurityTokenReference_Dec(ElementDeclaration):
        literal = "SecurityTokenReference"
        schema = NS.OASIS.WSSE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.WSSE,"SecurityTokenReference")
            kw["aname"] = "_SecurityTokenReference"
            if wsse.SecurityTokenReferenceType_Def not in wsse.SecurityTokenReference_Dec.__bases__:
                bases = list(wsse.SecurityTokenReference_Dec.__bases__)
                bases.insert(0, wsse.SecurityTokenReferenceType_Def)
                wsse.SecurityTokenReference_Dec.__bases__ = tuple(bases)

            wsse.SecurityTokenReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SecurityTokenReference_Dec_Holder"

    class Security_Dec(ElementDeclaration):
        literal = "Security"
        schema = NS.OASIS.WSSE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.WSSE,"Security")
            kw["aname"] = "_Security"
            if wsse.SecurityHeaderType_Def not in wsse.Security_Dec.__bases__:
                bases = list(wsse.Security_Dec.__bases__)
                bases.insert(0, wsse.SecurityHeaderType_Def)
                wsse.Security_Dec.__bases__ = tuple(bases)

            wsse.SecurityHeaderType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Security_Dec_Holder"

    class UsernameToken_Dec(ElementDeclaration):
        literal = "UsernameToken"
        schema = NS.OASIS.WSSE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.WSSE,"UsernameToken")
            kw["aname"] = "_UsernameToken"
            if wsse.UsernameTokenType_Def not in wsse.UsernameToken_Dec.__bases__:
                bases = list(wsse.UsernameToken_Dec.__bases__)
                bases.insert(0, wsse.UsernameTokenType_Def)
                wsse.UsernameToken_Dec.__bases__ = tuple(bases)

            wsse.UsernameTokenType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "UsernameToken_Dec_Holder"

    class KeyIdentifier_Dec(ElementDeclaration):
        literal = "KeyIdentifier"
        schema = NS.OASIS.WSSE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.WSSE,"KeyIdentifier")
            kw["aname"] = "_KeyIdentifier"
            if wsse.KeyIdentifierType_Def not in wsse.KeyIdentifier_Dec.__bases__:
                bases = list(wsse.KeyIdentifier_Dec.__bases__)
                bases.insert(0, wsse.KeyIdentifierType_Def)
                wsse.KeyIdentifier_Dec.__bases__ = tuple(bases)

            wsse.KeyIdentifierType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "KeyIdentifier_Dec_Holder"

    class Reference_Dec(ElementDeclaration):
        literal = "Reference"
        schema = NS.OASIS.WSSE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.WSSE,"Reference")
            kw["aname"] = "_Reference"
            if wsse.ReferenceType_Def not in wsse.Reference_Dec.__bases__:
                bases = list(wsse.Reference_Dec.__bases__)
                bases.insert(0, wsse.ReferenceType_Def)
                wsse.Reference_Dec.__bases__ = tuple(bases)

            wsse.ReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Reference_Dec_Holder"

    class BinarySecurityToken_Dec(ElementDeclaration):
        literal = "BinarySecurityToken"
        schema = NS.OASIS.WSSE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.OASIS.WSSE,"BinarySecurityToken")
            kw["aname"] = "_BinarySecurityToken"
            if wsse.BinarySecurityTokenType_Def not in wsse.BinarySecurityToken_Dec.__bases__:
                bases = list(wsse.BinarySecurityToken_Dec.__bases__)
                bases.insert(0, wsse.BinarySecurityTokenType_Def)
                wsse.BinarySecurityToken_Dec.__bases__ = tuple(bases)

            wsse.BinarySecurityTokenType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "BinarySecurityToken_Dec_Holder"

    class PolicyReference_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "PolicyReference"
        schema = NS.OASIS.WSSE
        def __init__(self, **kw):
            ns = wsse.PolicyReference_Dec.schema
            TClist = []
            kw["pname"] = (NS.OASIS.WSSE,"PolicyReference")
            kw["aname"] = "_PolicyReference"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            # attribute handling code
            self.attribute_typecode_dict["URI"] = ZSI.TC.URI()
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "PolicyReference_Holder"
            self.pyclass = Holder

# end class wsse (tns: http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd)
