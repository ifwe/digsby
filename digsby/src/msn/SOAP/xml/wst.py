import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type


##############################
# targetNamespace
# http://schemas.xmlsoap.org/ws/2005/02/trust
##############################

class wst:
    targetNamespace = NS.WSTRUST.BASE

    class RequestSecurityTokenType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestSecurityTokenType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.RequestSecurityTokenType_Def.schema
            TClist = [GED(NS.WSTRUST.BASE,"TokenType",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST.BASE,"RequestType",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSP.POLICY,"AppliesTo",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSP.POLICY,"PolicyReference",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.String()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._TokenType = None
                    self._RequestType = None
                    self._AppliesTo = None
                    self._PolicyReference = None
                    self._any = []
                    return
            Holder.__name__ = "RequestSecurityTokenType_Holder"
            self.pyclass = Holder

    class RequestTypeOpenEnum_Def(ZSI.TC.URI, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestTypeOpenEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.URI.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class RequestTypeEnum_Def(ZSI.TC.URI, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestTypeEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.URI.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class RequestSecurityTokenResponseType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestSecurityTokenResponseType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.RequestSecurityTokenResponseType_Def.schema
            TClist = [GED(NS.WSTRUST.BASE,"TokenType",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSP.POLICY,"AppliesTo",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST.BASE,"Lifetime",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST.BASE,"RequestedSecurityToken",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST.BASE,"RequestedAttachedReference",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST.BASE,"RequestedUnattachedReference",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST.BASE,"RequestedTokenReference",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSTRUST.BASE,"RequestedProofToken",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._TokenType = None
                    self._AppliesTo = None
                    self._Lifetime = None
                    self._RequestedSecurityToken = None
                    self._RequestedAttachedReference = None
                    self._RequestedUnattachedReference = None
                    self._RequestedTokenReference = None
                    self._RequestedProofToken = None
                    return
            Holder.__name__ = "RequestSecurityTokenResponseType_Holder"
            self.pyclass = Holder

    class RequestedTokenReferenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestedTokenReferenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.RequestedTokenReferenceType_Def.schema
            TClist = [GED(NS.OASIS.WSSE,"KeyIdentifier",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.OASIS.WSSE,"Reference",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._KeyIdentifier = None
                    self._Reference = None
                    return
            Holder.__name__ = "RequestedTokenReferenceType_Holder"
            self.pyclass = Holder

    class RequestedProofTokenType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestedProofTokenType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.RequestedProofTokenType_Def.schema
            TClist = [GED(NS.WSTRUST.BASE,"BinarySecret",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._BinarySecret = None
                    return
            Holder.__name__ = "RequestedProofTokenType_Holder"
            self.pyclass = Holder

    class BinarySecretType_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSTRUST.BASE
        type = (schema, "BinarySecretType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class BinarySecretTypeEnum_Def(ZSI.TC.URI, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "BinarySecretTypeEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.URI.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class BinarySecretTypeOpenEnum_Def(ZSI.TC.Union, TypeDefinition):
        memberTypes = [(NS.WSTRUST.BASE, u'BinarySecretTypeEnum'), (NS.SCHEMA.BASE, u'anyURI')]
        schema = NS.WSTRUST.BASE
        type = (schema, "BinarySecretTypeOpenEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.Union.__init__(self, pname, **kw)

    class RequestedSecurityTokenType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestedSecurityTokenType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.RequestedSecurityTokenType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=1, maxOccurs=1, nillable=False, processContents="lax"), GTD(NS.WSTRUST.BASE,"EncryptedDataType",lazy=False)(pname=(ns,"EncryptedData"), aname="_EncryptedData", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")),
                      GED(NS.OASIS.WSSE,"BinarySecurityToken",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")),
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
                    self._any = None
                    self._EncryptedData = None
                    self._BinarySecurityToken = None
                    self._Assertion = None
                    return
            Holder.__name__ = "RequestedSecurityTokenType_Holder"
            self.pyclass = Holder

    class LifetimeType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "LifetimeType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.LifetimeType_Def.schema
            TClist = [GED(NS.OASIS.UTILITY,"Created",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.OASIS.UTILITY,"Expires",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Created = None
                    self._Expires = None
                    return
            Holder.__name__ = "LifetimeType_Holder"
            self.pyclass = Holder

    class RequestSecurityTokenResponseCollectionType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "RequestSecurityTokenResponseCollectionType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.RequestSecurityTokenResponseCollectionType_Def.schema
            TClist = [GED(NS.WSTRUST.BASE,"RequestSecurityTokenResponse",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._RequestSecurityTokenResponse = None
                    return
            Holder.__name__ = "RequestSecurityTokenResponseCollectionType_Holder"
            self.pyclass = Holder

    class CipherDataType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "CipherDataType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.CipherDataType_Def.schema
            TClist = [ZSI.TC.String(pname=(ns,"CipherValue"), aname="_CipherValue", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._CipherValue = None
                    return
            Holder.__name__ = "CipherDataType_Holder"
            self.pyclass = Holder

    class EncryptedDataType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "EncryptedDataType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.EncryptedDataType_Def.schema
            TClist = [GTD(NS.WSTRUST.BASE,"EncryptionMethodType",lazy=False)(pname=(ns,"EncryptionMethod"), aname="_EncryptionMethod", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"KeyInfo",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GTD(NS.WSTRUST.BASE,"CipherDataType",lazy=False)(pname=(ns,"CipherData"), aname="_CipherData", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.String()
                self.attribute_typecode_dict["Type"] = ZSI.TC.String()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._EncryptionMethod = None
                    self._KeyInfo = None
                    self._CipherData = None
                    return
            Holder.__name__ = "EncryptedDataType_Holder"
            self.pyclass = Holder

    class EncryptionMethodType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSTRUST.BASE
        type = (schema, "EncryptionMethodType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wst.EncryptionMethodType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Algorithm"] = ZSI.TC.String()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "EncryptionMethodType_Holder"
            self.pyclass = Holder

    class RequestSecurityToken_Dec(ElementDeclaration):
        literal = "RequestSecurityToken"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"RequestSecurityToken")
            kw["aname"] = "_RequestSecurityToken"
            if wst.RequestSecurityTokenType_Def not in wst.RequestSecurityToken_Dec.__bases__:
                bases = list(wst.RequestSecurityToken_Dec.__bases__)
                bases.insert(0, wst.RequestSecurityTokenType_Def)
                wst.RequestSecurityToken_Dec.__bases__ = tuple(bases)

            wst.RequestSecurityTokenType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RequestSecurityToken_Dec_Holder"

    class TokenType_Dec(ZSI.TC.URI, ElementDeclaration):
        literal = "TokenType"
        schema = NS.WSTRUST.BASE
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"TokenType")
            kw["aname"] = "_TokenType"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_TokenType_immutable_holder"
            ZSI.TC.URI.__init__(self, **kw)

    class RequestType_Dec(ElementDeclaration):
        literal = "RequestType"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"RequestType")
            kw["aname"] = "_RequestType"
            if wst.RequestTypeOpenEnum_Def not in wst.RequestType_Dec.__bases__:
                bases = list(wst.RequestType_Dec.__bases__)
                bases.insert(0, wst.RequestTypeOpenEnum_Def)
                wst.RequestType_Dec.__bases__ = tuple(bases)

            wst.RequestTypeOpenEnum_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RequestType_Dec_Holder"

    class RequestSecurityTokenResponse_Dec(ElementDeclaration):
        literal = "RequestSecurityTokenResponse"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"RequestSecurityTokenResponse")
            kw["aname"] = "_RequestSecurityTokenResponse"
            if wst.RequestSecurityTokenResponseType_Def not in wst.RequestSecurityTokenResponse_Dec.__bases__:
                bases = list(wst.RequestSecurityTokenResponse_Dec.__bases__)
                bases.insert(0, wst.RequestSecurityTokenResponseType_Def)
                wst.RequestSecurityTokenResponse_Dec.__bases__ = tuple(bases)

            wst.RequestSecurityTokenResponseType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RequestSecurityTokenResponse_Dec_Holder"

    class RequestedAttachedReference_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "RequestedAttachedReference"
        schema = NS.WSTRUST.BASE
        def __init__(self, **kw):
            ns = wst.RequestedAttachedReference_Dec.schema
            TClist = [GED(NS.OASIS.WSSE,"SecurityTokenReference",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            kw["pname"] = (NS.WSTRUST.BASE,"RequestedAttachedReference")
            kw["aname"] = "_RequestedAttachedReference"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._SecurityTokenReference = None
                    return
            Holder.__name__ = "RequestedAttachedReference_Holder"
            self.pyclass = Holder

    class RequestedUnattachedReference_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "RequestedUnattachedReference"
        schema = NS.WSTRUST.BASE
        def __init__(self, **kw):
            ns = wst.RequestedUnattachedReference_Dec.schema
            TClist = [GED(NS.OASIS.WSSE,"SecurityTokenReference",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            kw["pname"] = (NS.WSTRUST.BASE,"RequestedUnattachedReference")
            kw["aname"] = "_RequestedUnattachedReference"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._SecurityTokenReference = None
                    return
            Holder.__name__ = "RequestedUnattachedReference_Holder"
            self.pyclass = Holder

    class RequestedTokenReference_Dec(ElementDeclaration):
        literal = "RequestedTokenReference"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"RequestedTokenReference")
            kw["aname"] = "_RequestedTokenReference"
            if wst.RequestedTokenReferenceType_Def not in wst.RequestedTokenReference_Dec.__bases__:
                bases = list(wst.RequestedTokenReference_Dec.__bases__)
                bases.insert(0, wst.RequestedTokenReferenceType_Def)
                wst.RequestedTokenReference_Dec.__bases__ = tuple(bases)

            wst.RequestedTokenReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RequestedTokenReference_Dec_Holder"

    class RequestedProofToken_Dec(ElementDeclaration):
        literal = "RequestedProofToken"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"RequestedProofToken")
            kw["aname"] = "_RequestedProofToken"
            if wst.RequestedProofTokenType_Def not in wst.RequestedProofToken_Dec.__bases__:
                bases = list(wst.RequestedProofToken_Dec.__bases__)
                bases.insert(0, wst.RequestedProofTokenType_Def)
                wst.RequestedProofToken_Dec.__bases__ = tuple(bases)

            wst.RequestedProofTokenType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RequestedProofToken_Dec_Holder"

    class BinarySecret_Dec(ElementDeclaration):
        literal = "BinarySecret"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"BinarySecret")
            kw["aname"] = "_BinarySecret"
            if wst.BinarySecretType_Def not in wst.BinarySecret_Dec.__bases__:
                bases = list(wst.BinarySecret_Dec.__bases__)
                bases.insert(0, wst.BinarySecretType_Def)
                wst.BinarySecret_Dec.__bases__ = tuple(bases)

            wst.BinarySecretType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "BinarySecret_Dec_Holder"

    class RequestedSecurityToken_Dec(ElementDeclaration):
        literal = "RequestedSecurityToken"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"RequestedSecurityToken")
            kw["aname"] = "_RequestedSecurityToken"
            if wst.RequestedSecurityTokenType_Def not in wst.RequestedSecurityToken_Dec.__bases__:
                bases = list(wst.RequestedSecurityToken_Dec.__bases__)
                bases.insert(0, wst.RequestedSecurityTokenType_Def)
                wst.RequestedSecurityToken_Dec.__bases__ = tuple(bases)

            wst.RequestedSecurityTokenType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RequestedSecurityToken_Dec_Holder"

    class Lifetime_Dec(ElementDeclaration):
        literal = "Lifetime"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"Lifetime")
            kw["aname"] = "_Lifetime"
            if wst.LifetimeType_Def not in wst.Lifetime_Dec.__bases__:
                bases = list(wst.Lifetime_Dec.__bases__)
                bases.insert(0, wst.LifetimeType_Def)
                wst.Lifetime_Dec.__bases__ = tuple(bases)

            wst.LifetimeType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Lifetime_Dec_Holder"

    class RequestSecurityTokenResponseCollection_Dec(ElementDeclaration):
        literal = "RequestSecurityTokenResponseCollection"
        schema = NS.WSTRUST.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSTRUST.BASE,"RequestSecurityTokenResponseCollection")
            kw["aname"] = "_RequestSecurityTokenResponseCollection"
            if wst.RequestSecurityTokenResponseCollectionType_Def not in wst.RequestSecurityTokenResponseCollection_Dec.__bases__:
                bases = list(wst.RequestSecurityTokenResponseCollection_Dec.__bases__)
                bases.insert(0, wst.RequestSecurityTokenResponseCollectionType_Def)
                wst.RequestSecurityTokenResponseCollection_Dec.__bases__ = tuple(bases)

            wst.RequestSecurityTokenResponseCollectionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RequestSecurityTokenResponseCollection_Dec_Holder"

# end class wst (tns: http://schemas.xmlsoap.org/ws/2005/02/trust)

