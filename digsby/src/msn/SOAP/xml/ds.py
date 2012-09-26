import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://www.w3.org/2000/09/xmldsig#
##############################

class ds:
    targetNamespace = NS.DSIG.BASE

    class CryptoBinary_Def(ZSI.TC.Base64String, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "CryptoBinary")
        def __init__(self, pname, **kw):
            ZSI.TC.Base64String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class SignatureType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "SignatureType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.SignatureType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"SignedInfo",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"SignatureValue",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"KeyInfo",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"Object",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._SignedInfo = None
                    self._SignatureValue = None
                    self._KeyInfo = None
                    self._Object = None
                    return
            Holder.__name__ = "SignatureType_Holder"
            self.pyclass = Holder

    class SignatureValueType_Def(ZSI.TC.Base64String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.DSIG.BASE
        type = (schema, "SignatureValueType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            ZSI.TC.Base64String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class SignedInfoType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "SignedInfoType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.SignedInfoType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"CanonicalizationMethod",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"SignatureMethod",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"Reference",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._CanonicalizationMethod = None
                    self._SignatureMethod = None
                    self._Reference = None
                    return
            Holder.__name__ = "SignedInfoType_Holder"
            self.pyclass = Holder

    class CanonicalizationMethodType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "CanonicalizationMethodType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.CanonicalizationMethodType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="strict")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Algorithm"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "CanonicalizationMethodType_Holder"
            self.pyclass = Holder

    class SignatureMethodType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "SignatureMethodType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.SignatureMethodType_Def.schema
            TClist = [GTD(NS.DSIG.BASE,"HMACOutputLengthType",lazy=False)(pname=(ns,"HMACOutputLength"), aname="_HMACOutputLength", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="strict")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Algorithm"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._HMACOutputLength = None
                    self._any = []
                    return
            Holder.__name__ = "SignatureMethodType_Holder"
            self.pyclass = Holder

    class ReferenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "ReferenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.ReferenceType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"Transforms",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"DigestMethod",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"DigestValue",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
                self.attribute_typecode_dict["URI"] = ZSI.TC.URI()
                self.attribute_typecode_dict["Type"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Transforms = None
                    self._DigestMethod = None
                    self._DigestValue = None
                    return
            Holder.__name__ = "ReferenceType_Holder"
            self.pyclass = Holder

    class TransformsType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "TransformsType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.TransformsType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"Transform",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Transform = None
                    return
            Holder.__name__ = "TransformsType_Holder"
            self.pyclass = Holder

    class TransformType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "TransformType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.TransformType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax"), ZSI.TC.String(pname=(ns,"XPath"), aname="_XPath", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Algorithm"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    self._XPath = []
                    return
            Holder.__name__ = "TransformType_Holder"
            self.pyclass = Holder

    class DigestMethodType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "DigestMethodType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.DigestMethodType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Algorithm"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "DigestMethodType_Holder"
            self.pyclass = Holder

    class DigestValueType_Def(ZSI.TC.Base64String, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "DigestValueType")
        def __init__(self, pname, **kw):
            ZSI.TC.Base64String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class KeyInfoType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "KeyInfoType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.KeyInfoType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"KeyName",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"KeyValue",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"RetrievalMethod",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"X509Data",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"PGPData",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"SPKIData",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"MgmtData",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._KeyName = None
                    self._KeyValue = None
                    self._RetrievalMethod = None
                    self._X509Data = None
                    self._PGPData = None
                    self._SPKIData = None
                    self._MgmtData = None
                    self._any = []
                    return
            Holder.__name__ = "KeyInfoType_Holder"
            self.pyclass = Holder

    class KeyValueType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "KeyValueType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.KeyValueType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"DSAKeyValue",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"RSAKeyValue",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs=1, nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._DSAKeyValue = None
                    self._RSAKeyValue = None
                    self._any = None
                    return
            Holder.__name__ = "KeyValueType_Holder"
            self.pyclass = Holder

    class RetrievalMethodType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "RetrievalMethodType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.RetrievalMethodType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"Transforms",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["URI"] = ZSI.TC.URI()
                self.attribute_typecode_dict["Type"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Transforms = None
                    return
            Holder.__name__ = "RetrievalMethodType_Holder"
            self.pyclass = Holder

    class X509DataType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "X509DataType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.X509DataType_Def.schema
            TClist = [GTD(NS.DSIG.BASE,"X509IssuerSerialType",lazy=False)(pname=(ns,"X509IssuerSerial"), aname="_X509IssuerSerial", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.Base64String(pname=(ns,"X509SKI"), aname="_X509SKI", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname=(ns,"X509SubjectName"), aname="_X509SubjectName", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.Base64String(pname=(ns,"X509Certificate"), aname="_X509Certificate", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.Base64String(pname=(ns,"X509CRL"), aname="_X509CRL", minOccurs=0, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._X509IssuerSerial = []
                    self._X509SKI = []
                    self._X509SubjectName = []
                    self._X509Certificate = []
                    self._X509CRL = []
                    self._any = []
                    return
            Holder.__name__ = "X509DataType_Holder"
            self.pyclass = Holder

    class X509IssuerSerialType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "X509IssuerSerialType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.X509IssuerSerialType_Def.schema
            TClist = [ZSI.TC.String(pname=(ns,"X509IssuerName"), aname="_X509IssuerName", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TCnumbers.Iinteger(pname=(ns,"X509SerialNumber"), aname="_X509SerialNumber", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._X509IssuerName = None
                    self._X509SerialNumber = None
                    return
            Holder.__name__ = "X509IssuerSerialType_Holder"
            self.pyclass = Holder

    class PGPDataType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "PGPDataType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.PGPDataType_Def.schema
            TClist = [ZSI.TC.Base64String(pname=(ns,"PGPKeyID"), aname="_PGPKeyID", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")),
                      ZSI.TC.Base64String(pname=(ns,"PGPKeyPacket"), aname="_PGPKeyPacket", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")),
                      ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._PGPKeyID = None
                    self._PGPKeyPacket = None
                    self._any = []
                    self._PGPKeyPacket = None
                    self._any = []
                    return
            Holder.__name__ = "PGPDataType_Holder"
            self.pyclass = Holder

    class SPKIDataType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "SPKIDataType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.SPKIDataType_Def.schema
            TClist = [ZSI.TC.Base64String(pname=(ns,"SPKISexp"), aname="_SPKISexp", minOccurs=1, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._SPKISexp = []
                    self._any = []
                    return
            Holder.__name__ = "SPKIDataType_Holder"
            self.pyclass = Holder

    class ObjectType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "ObjectType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.ObjectType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
                self.attribute_typecode_dict["MimeType"] = ZSI.TC.String()
                self.attribute_typecode_dict["Encoding"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "ObjectType_Holder"
            self.pyclass = Holder

    class ManifestType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "ManifestType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.ManifestType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"Reference",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Reference = None
                    return
            Holder.__name__ = "ManifestType_Holder"
            self.pyclass = Holder

    class SignaturePropertiesType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "SignaturePropertiesType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.SignaturePropertiesType_Def.schema
            TClist = [GED(NS.DSIG.BASE,"SignatureProperty",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._SignatureProperty = None
                    return
            Holder.__name__ = "SignaturePropertiesType_Holder"
            self.pyclass = Holder

    class SignaturePropertyType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "SignaturePropertyType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.SignaturePropertyType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Target"] = ZSI.TC.URI()
                self.attribute_typecode_dict["Id"] = ZSI.TC.AnyType()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, mixed=True, mixed_aname="_text", **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "SignaturePropertyType_Holder"
            self.pyclass = Holder

    class HMACOutputLengthType_Def(ZSI.TCnumbers.Iinteger, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "HMACOutputLengthType")
        def __init__(self, pname, **kw):
            ZSI.TCnumbers.Iinteger.__init__(self, pname, pyclass=None, **kw)
            class Holder(int):
                typecode = self
            self.pyclass = Holder

    class DSAKeyValueType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "DSAKeyValueType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.DSAKeyValueType_Def.schema
            TClist = [GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"P"), aname="_P", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"Q"), aname="_Q", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"G"), aname="_G", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"Y"), aname="_Y", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"J"), aname="_J", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"Seed"), aname="_Seed", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"PgenCounter"), aname="_PgenCounter", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._P = None
                    self._Q = None
                    self._G = None
                    self._Y = None
                    self._J = None
                    self._Seed = None
                    self._PgenCounter = None
                    return
            Holder.__name__ = "DSAKeyValueType_Holder"
            self.pyclass = Holder

    class RSAKeyValueType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.DSIG.BASE
        type = (schema, "RSAKeyValueType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = ds.RSAKeyValueType_Def.schema
            TClist = [GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"Modulus"), aname="_Modulus", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.DSIG.BASE,"CryptoBinary",lazy=False)(pname=(ns,"Exponent"), aname="_Exponent", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Modulus = None
                    self._Exponent = None
                    return
            Holder.__name__ = "RSAKeyValueType_Holder"
            self.pyclass = Holder

    class Signature_Dec(ElementDeclaration):
        literal = "Signature"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"Signature")
            kw["aname"] = "_Signature"
            if ds.SignatureType_Def not in ds.Signature_Dec.__bases__:
                bases = list(ds.Signature_Dec.__bases__)
                bases.insert(0, ds.SignatureType_Def)
                ds.Signature_Dec.__bases__ = tuple(bases)

            ds.SignatureType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Signature_Dec_Holder"

    class SignatureValue_Dec(ElementDeclaration):
        literal = "SignatureValue"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"SignatureValue")
            kw["aname"] = "_SignatureValue"
            if ds.SignatureValueType_Def not in ds.SignatureValue_Dec.__bases__:
                bases = list(ds.SignatureValue_Dec.__bases__)
                bases.insert(0, ds.SignatureValueType_Def)
                ds.SignatureValue_Dec.__bases__ = tuple(bases)

            ds.SignatureValueType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SignatureValue_Dec_Holder"

    class SignedInfo_Dec(ElementDeclaration):
        literal = "SignedInfo"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"SignedInfo")
            kw["aname"] = "_SignedInfo"
            if ds.SignedInfoType_Def not in ds.SignedInfo_Dec.__bases__:
                bases = list(ds.SignedInfo_Dec.__bases__)
                bases.insert(0, ds.SignedInfoType_Def)
                ds.SignedInfo_Dec.__bases__ = tuple(bases)

            ds.SignedInfoType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SignedInfo_Dec_Holder"

    class CanonicalizationMethod_Dec(ElementDeclaration):
        literal = "CanonicalizationMethod"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"CanonicalizationMethod")
            kw["aname"] = "_CanonicalizationMethod"
            if ds.CanonicalizationMethodType_Def not in ds.CanonicalizationMethod_Dec.__bases__:
                bases = list(ds.CanonicalizationMethod_Dec.__bases__)
                bases.insert(0, ds.CanonicalizationMethodType_Def)
                ds.CanonicalizationMethod_Dec.__bases__ = tuple(bases)

            ds.CanonicalizationMethodType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "CanonicalizationMethod_Dec_Holder"

    class SignatureMethod_Dec(ElementDeclaration):
        literal = "SignatureMethod"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"SignatureMethod")
            kw["aname"] = "_SignatureMethod"
            if ds.SignatureMethodType_Def not in ds.SignatureMethod_Dec.__bases__:
                bases = list(ds.SignatureMethod_Dec.__bases__)
                bases.insert(0, ds.SignatureMethodType_Def)
                ds.SignatureMethod_Dec.__bases__ = tuple(bases)

            ds.SignatureMethodType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SignatureMethod_Dec_Holder"

    class Reference_Dec(ElementDeclaration):
        literal = "Reference"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"Reference")
            kw["aname"] = "_Reference"
            if ds.ReferenceType_Def not in ds.Reference_Dec.__bases__:
                bases = list(ds.Reference_Dec.__bases__)
                bases.insert(0, ds.ReferenceType_Def)
                ds.Reference_Dec.__bases__ = tuple(bases)

            ds.ReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Reference_Dec_Holder"

    class Transforms_Dec(ElementDeclaration):
        literal = "Transforms"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"Transforms")
            kw["aname"] = "_Transforms"
            if ds.TransformsType_Def not in ds.Transforms_Dec.__bases__:
                bases = list(ds.Transforms_Dec.__bases__)
                bases.insert(0, ds.TransformsType_Def)
                ds.Transforms_Dec.__bases__ = tuple(bases)

            ds.TransformsType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Transforms_Dec_Holder"

    class Transform_Dec(ElementDeclaration):
        literal = "Transform"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"Transform")
            kw["aname"] = "_Transform"
            if ds.TransformType_Def not in ds.Transform_Dec.__bases__:
                bases = list(ds.Transform_Dec.__bases__)
                bases.insert(0, ds.TransformType_Def)
                ds.Transform_Dec.__bases__ = tuple(bases)

            ds.TransformType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Transform_Dec_Holder"

    class DigestMethod_Dec(ElementDeclaration):
        literal = "DigestMethod"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"DigestMethod")
            kw["aname"] = "_DigestMethod"
            if ds.DigestMethodType_Def not in ds.DigestMethod_Dec.__bases__:
                bases = list(ds.DigestMethod_Dec.__bases__)
                bases.insert(0, ds.DigestMethodType_Def)
                ds.DigestMethod_Dec.__bases__ = tuple(bases)

            ds.DigestMethodType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "DigestMethod_Dec_Holder"

    class DigestValue_Dec(ElementDeclaration):
        literal = "DigestValue"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"DigestValue")
            kw["aname"] = "_DigestValue"
            if ds.DigestValueType_Def not in ds.DigestValue_Dec.__bases__:
                bases = list(ds.DigestValue_Dec.__bases__)
                bases.insert(0, ds.DigestValueType_Def)
                ds.DigestValue_Dec.__bases__ = tuple(bases)

            ds.DigestValueType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "DigestValue_Dec_Holder"

    class KeyInfo_Dec(ElementDeclaration):
        literal = "KeyInfo"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"KeyInfo")
            kw["aname"] = "_KeyInfo"
            if ds.KeyInfoType_Def not in ds.KeyInfo_Dec.__bases__:
                bases = list(ds.KeyInfo_Dec.__bases__)
                bases.insert(0, ds.KeyInfoType_Def)
                ds.KeyInfo_Dec.__bases__ = tuple(bases)

            ds.KeyInfoType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "KeyInfo_Dec_Holder"

    class KeyName_Dec(ZSI.TC.String, ElementDeclaration):
        literal = "KeyName"
        schema = NS.DSIG.BASE
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"KeyName")
            kw["aname"] = "_KeyName"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_KeyName_immutable_holder"
            ZSI.TC.String.__init__(self, **kw)

    class MgmtData_Dec(ZSI.TC.String, ElementDeclaration):
        literal = "MgmtData"
        schema = NS.DSIG.BASE
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"MgmtData")
            kw["aname"] = "_MgmtData"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_MgmtData_immutable_holder"
            ZSI.TC.String.__init__(self, **kw)

    class KeyValue_Dec(ElementDeclaration):
        literal = "KeyValue"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"KeyValue")
            kw["aname"] = "_KeyValue"
            if ds.KeyValueType_Def not in ds.KeyValue_Dec.__bases__:
                bases = list(ds.KeyValue_Dec.__bases__)
                bases.insert(0, ds.KeyValueType_Def)
                ds.KeyValue_Dec.__bases__ = tuple(bases)

            ds.KeyValueType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "KeyValue_Dec_Holder"

    class RetrievalMethod_Dec(ElementDeclaration):
        literal = "RetrievalMethod"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"RetrievalMethod")
            kw["aname"] = "_RetrievalMethod"
            if ds.RetrievalMethodType_Def not in ds.RetrievalMethod_Dec.__bases__:
                bases = list(ds.RetrievalMethod_Dec.__bases__)
                bases.insert(0, ds.RetrievalMethodType_Def)
                ds.RetrievalMethod_Dec.__bases__ = tuple(bases)

            ds.RetrievalMethodType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RetrievalMethod_Dec_Holder"

    class X509Data_Dec(ElementDeclaration):
        literal = "X509Data"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"X509Data")
            kw["aname"] = "_X509Data"
            if ds.X509DataType_Def not in ds.X509Data_Dec.__bases__:
                bases = list(ds.X509Data_Dec.__bases__)
                bases.insert(0, ds.X509DataType_Def)
                ds.X509Data_Dec.__bases__ = tuple(bases)

            ds.X509DataType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "X509Data_Dec_Holder"

    class PGPData_Dec(ElementDeclaration):
        literal = "PGPData"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"PGPData")
            kw["aname"] = "_PGPData"
            if ds.PGPDataType_Def not in ds.PGPData_Dec.__bases__:
                bases = list(ds.PGPData_Dec.__bases__)
                bases.insert(0, ds.PGPDataType_Def)
                ds.PGPData_Dec.__bases__ = tuple(bases)

            ds.PGPDataType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "PGPData_Dec_Holder"

    class SPKIData_Dec(ElementDeclaration):
        literal = "SPKIData"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"SPKIData")
            kw["aname"] = "_SPKIData"
            if ds.SPKIDataType_Def not in ds.SPKIData_Dec.__bases__:
                bases = list(ds.SPKIData_Dec.__bases__)
                bases.insert(0, ds.SPKIDataType_Def)
                ds.SPKIData_Dec.__bases__ = tuple(bases)

            ds.SPKIDataType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SPKIData_Dec_Holder"

    class Object_Dec(ElementDeclaration):
        literal = "Object"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"Object")
            kw["aname"] = "_Object"
            if ds.ObjectType_Def not in ds.Object_Dec.__bases__:
                bases = list(ds.Object_Dec.__bases__)
                bases.insert(0, ds.ObjectType_Def)
                ds.Object_Dec.__bases__ = tuple(bases)

            ds.ObjectType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Object_Dec_Holder"

    class Manifest_Dec(ElementDeclaration):
        literal = "Manifest"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"Manifest")
            kw["aname"] = "_Manifest"
            if ds.ManifestType_Def not in ds.Manifest_Dec.__bases__:
                bases = list(ds.Manifest_Dec.__bases__)
                bases.insert(0, ds.ManifestType_Def)
                ds.Manifest_Dec.__bases__ = tuple(bases)

            ds.ManifestType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Manifest_Dec_Holder"

    class SignatureProperties_Dec(ElementDeclaration):
        literal = "SignatureProperties"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"SignatureProperties")
            kw["aname"] = "_SignatureProperties"
            if ds.SignaturePropertiesType_Def not in ds.SignatureProperties_Dec.__bases__:
                bases = list(ds.SignatureProperties_Dec.__bases__)
                bases.insert(0, ds.SignaturePropertiesType_Def)
                ds.SignatureProperties_Dec.__bases__ = tuple(bases)

            ds.SignaturePropertiesType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SignatureProperties_Dec_Holder"

    class SignatureProperty_Dec(ElementDeclaration):
        literal = "SignatureProperty"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"SignatureProperty")
            kw["aname"] = "_SignatureProperty"
            if ds.SignaturePropertyType_Def not in ds.SignatureProperty_Dec.__bases__:
                bases = list(ds.SignatureProperty_Dec.__bases__)
                bases.insert(0, ds.SignaturePropertyType_Def)
                ds.SignatureProperty_Dec.__bases__ = tuple(bases)

            ds.SignaturePropertyType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SignatureProperty_Dec_Holder"

    class DSAKeyValue_Dec(ElementDeclaration):
        literal = "DSAKeyValue"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"DSAKeyValue")
            kw["aname"] = "_DSAKeyValue"
            if ds.DSAKeyValueType_Def not in ds.DSAKeyValue_Dec.__bases__:
                bases = list(ds.DSAKeyValue_Dec.__bases__)
                bases.insert(0, ds.DSAKeyValueType_Def)
                ds.DSAKeyValue_Dec.__bases__ = tuple(bases)

            ds.DSAKeyValueType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "DSAKeyValue_Dec_Holder"

    class RSAKeyValue_Dec(ElementDeclaration):
        literal = "RSAKeyValue"
        schema = NS.DSIG.BASE
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.DSIG.BASE,"RSAKeyValue")
            kw["aname"] = "_RSAKeyValue"
            if ds.RSAKeyValueType_Def not in ds.RSAKeyValue_Dec.__bases__:
                bases = list(ds.RSAKeyValue_Dec.__bases__)
                bases.insert(0, ds.RSAKeyValueType_Def)
                ds.RSAKeyValue_Dec.__bases__ = tuple(bases)

            ds.RSAKeyValueType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RSAKeyValue_Dec_Holder"

# end class ds (tns: http://www.w3.org/2000/09/xmldsig#)
