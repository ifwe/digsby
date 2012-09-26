import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://www.w3.org/2003/05/soap-envelope
##############################

class wssoapenv:
    targetNamespace = NS.SOAP.ENV12

    class Envelope_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "Envelope")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.Envelope_Def.schema
            TClist = [GED(NS.SOAP.ENV12,"Header",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.SOAP.ENV12,"Body",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Header = None
                    self._Body = None
                    return
            Holder.__name__ = "Envelope_Holder"
            self.pyclass = Holder

    class Header_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "Header")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.Header_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "Header_Holder"
            self.pyclass = Holder

    class Body_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "Body")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.Body_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "Body_Holder"
            self.pyclass = Holder

    class Fault_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "Fault")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.Fault_Def.schema
            TClist = [GTD(NS.SOAP.ENV12,"faultcode",lazy=False)(pname=(ns,"Code"), aname="_Code", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.SOAP.ENV12,"faultreason",lazy=False)(pname=(ns,"Reason"), aname="_Reason", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.URI(pname=(ns,"Node"), aname="_Node", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.URI(pname=(ns,"Role"), aname="_Role", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.SOAP.ENV12,"detail",lazy=False)(pname=(ns,"Detail"), aname="_Detail", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Code = None
                    self._Reason = None
                    self._Node = None
                    self._Role = None
                    self._Detail = None
                    return
            Holder.__name__ = "Fault_Holder"
            self.pyclass = Holder

    class faultreason_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "faultreason")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.faultreason_Def.schema
            TClist = [GTD(NS.SOAP.ENV12,"reasontext",lazy=False)(pname=(ns,"Text"), aname="_Text", minOccurs=1, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Text = []
                    return
            Holder.__name__ = "faultreason_Holder"
            self.pyclass = Holder

    class reasontext_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.SOAP.ENV12
        type = (schema, "reasontext")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.XMLNS.XML,"lang")] = ZSI.TC.AnyType()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class faultcode_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "faultcode")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.faultcode_Def.schema
            TClist = [GTD(NS.SOAP.ENV12,"faultcodeEnum",lazy=False)(pname=(ns,"Value"), aname="_Value", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.SOAP.ENV12,"subcode",lazy=False)(pname=(ns,"Subcode"), aname="_Subcode", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Value = None
                    self._Subcode = None
                    return
            Holder.__name__ = "faultcode_Holder"
            self.pyclass = Holder

    class faultcodeEnum_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "faultcodeEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class subcode_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "subcode")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.subcode_Def.schema
            TClist = [ZSI.TC.QName(pname=(ns,"Value"), aname="_Value", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")),
                      #GTD(NS.SOAP.ENV12,"subcode",lazy=False)(pname=(ns,"Subcode"), aname="_Subcode", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))
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
                    self._Value = None
                    self._Subcode = None
                    return
            Holder.__name__ = "subcode_Holder"
            self.pyclass = Holder

    class detail_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "detail")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.detail_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "detail_Holder"
            self.pyclass = Holder

    class NotUnderstoodType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "NotUnderstoodType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.NotUnderstoodType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["qname"] = ZSI.TC.QName()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "NotUnderstoodType_Holder"
            self.pyclass = Holder

    class SupportedEnvType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "SupportedEnvType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.SupportedEnvType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["qname"] = ZSI.TC.QName()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "SupportedEnvType_Holder"
            self.pyclass = Holder

    class UpgradeType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.SOAP.ENV12
        type = (schema, "UpgradeType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wssoapenv.UpgradeType_Def.schema
            TClist = [GTD(NS.SOAP.ENV12,"SupportedEnvType",lazy=False)(pname=(ns,"SupportedEnvelope"), aname="_SupportedEnvelope", minOccurs=1, maxOccurs="unbounded", nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._SupportedEnvelope = []
                    return
            Holder.__name__ = "UpgradeType_Holder"
            self.pyclass = Holder

    class Envelope_Dec(ElementDeclaration):
        literal = "Envelope"
        schema = NS.SOAP.ENV12
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.SOAP.ENV12,"Envelope")
            kw["aname"] = "_Envelope"
            if wssoapenv.Envelope_Def not in wssoapenv.Envelope_Dec.__bases__:
                bases = list(wssoapenv.Envelope_Dec.__bases__)
                bases.insert(0, wssoapenv.Envelope_Def)
                wssoapenv.Envelope_Dec.__bases__ = tuple(bases)

            wssoapenv.Envelope_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Envelope_Dec_Holder"

    class Header_Dec(ElementDeclaration):
        literal = "Header"
        schema = NS.SOAP.ENV12
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.SOAP.ENV12,"Header")
            kw["aname"] = "_Header"
            if wssoapenv.Header_Def not in wssoapenv.Header_Dec.__bases__:
                bases = list(wssoapenv.Header_Dec.__bases__)
                bases.insert(0, wssoapenv.Header_Def)
                wssoapenv.Header_Dec.__bases__ = tuple(bases)

            wssoapenv.Header_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Header_Dec_Holder"

    class Body_Dec(ElementDeclaration):
        literal = "Body"
        schema = NS.SOAP.ENV12
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.SOAP.ENV12,"Body")
            kw["aname"] = "_Body"
            if wssoapenv.Body_Def not in wssoapenv.Body_Dec.__bases__:
                bases = list(wssoapenv.Body_Dec.__bases__)
                bases.insert(0, wssoapenv.Body_Def)
                wssoapenv.Body_Dec.__bases__ = tuple(bases)

            wssoapenv.Body_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Body_Dec_Holder"

    class Fault_Dec(ElementDeclaration):
        literal = "Fault"
        schema = NS.SOAP.ENV12
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.SOAP.ENV12,"Fault")
            kw["aname"] = "_Fault"
            if wssoapenv.Fault_Def not in wssoapenv.Fault_Dec.__bases__:
                bases = list(wssoapenv.Fault_Dec.__bases__)
                bases.insert(0, wssoapenv.Fault_Def)
                wssoapenv.Fault_Dec.__bases__ = tuple(bases)

            wssoapenv.Fault_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Fault_Dec_Holder"

    class NotUnderstood_Dec(ElementDeclaration):
        literal = "NotUnderstood"
        schema = NS.SOAP.ENV12
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.SOAP.ENV12,"NotUnderstood")
            kw["aname"] = "_NotUnderstood"
            if wssoapenv.NotUnderstoodType_Def not in wssoapenv.NotUnderstood_Dec.__bases__:
                bases = list(wssoapenv.NotUnderstood_Dec.__bases__)
                bases.insert(0, wssoapenv.NotUnderstoodType_Def)
                wssoapenv.NotUnderstood_Dec.__bases__ = tuple(bases)

            wssoapenv.NotUnderstoodType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "NotUnderstood_Dec_Holder"

    class Upgrade_Dec(ElementDeclaration):
        literal = "Upgrade"
        schema = NS.SOAP.ENV12
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.SOAP.ENV12,"Upgrade")
            kw["aname"] = "_Upgrade"
            if wssoapenv.UpgradeType_Def not in wssoapenv.Upgrade_Dec.__bases__:
                bases = list(wssoapenv.Upgrade_Dec.__bases__)
                bases.insert(0, wssoapenv.UpgradeType_Def)
                wssoapenv.Upgrade_Dec.__bases__ = tuple(bases)

            wssoapenv.UpgradeType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Upgrade_Dec_Holder"

# end class wssoapenv (tns: http://www.w3.org/2003/05/soap-envelope)
