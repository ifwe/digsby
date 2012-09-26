import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://schemas.xmlsoap.org/ws/2004/08/addressing
##############################

class soapwsa:
    targetNamespace = NS.WSA200408.ADDRESS

    class EndpointReferenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA200408.ADDRESS
        type = (schema, "EndpointReferenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = soapwsa.EndpointReferenceType_Def.schema
            TClist = [GTD(NS.WSA200408.ADDRESS,"AttributedURI",lazy=False)(pname=(ns,"Address"), aname="_Address", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.WSA200408.ADDRESS,"ReferencePropertiesType",lazy=False)(pname=(ns,"ReferenceProperties"), aname="_ReferenceProperties", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.WSA200408.ADDRESS,"ReferenceParametersType",lazy=False)(pname=(ns,"ReferenceParameters"), aname="_ReferenceParameters", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.WSA200408.ADDRESS,"AttributedQName",lazy=False)(pname=(ns,"PortType"), aname="_PortType", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(NS.WSA200408.ADDRESS,"ServiceNameType",lazy=False)(pname=(ns,"ServiceName"), aname="_ServiceName", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
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
                    self._Address = None
                    self._ReferenceProperties = None
                    self._ReferenceParameters = None
                    self._PortType = None
                    self._ServiceName = None
                    self._any = []
                    return
            Holder.__name__ = "EndpointReferenceType_Holder"
            self.pyclass = Holder

    class ReferencePropertiesType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA200408.ADDRESS
        type = (schema, "ReferencePropertiesType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = soapwsa.ReferencePropertiesType_Def.schema
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
            Holder.__name__ = "ReferencePropertiesType_Holder"
            self.pyclass = Holder

    class ReferenceParametersType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA200408.ADDRESS
        type = (schema, "ReferenceParametersType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = soapwsa.ReferenceParametersType_Def.schema
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
            Holder.__name__ = "ReferenceParametersType_Holder"
            self.pyclass = Holder

    class ServiceNameType_Def(ZSI.TC.QName, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA200408.ADDRESS
        type = (schema, "ServiceNameType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["PortName"] = ZSI.TC.AnyType()
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.QName.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class Relationship_Def(ZSI.TC.URI, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA200408.ADDRESS
        type = (schema, "Relationship")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["RelationshipType"] = ZSI.TC.QName()
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.URI.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class RelationshipTypeValues_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSA200408.ADDRESS
        type = (schema, "RelationshipTypeValues")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class ReplyAfterType_Def(ZSI.TCnumbers.InonNegativeInteger, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA200408.ADDRESS
        type = (schema, "ReplyAfterType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCnumbers.InonNegativeInteger.__init__(self, pname, **kw)
            class Holder(int):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class RetryAfterType_Def(ZSI.TCnumbers.InonNegativeInteger, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA200408.ADDRESS
        type = (schema, "RetryAfterType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCnumbers.InonNegativeInteger.__init__(self, pname, **kw)
            class Holder(int):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class FaultSubcodeValues_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSA200408.ADDRESS
        type = (schema, "FaultSubcodeValues")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class AttributedQName_Def(ZSI.TC.QName, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA200408.ADDRESS
        type = (schema, "AttributedQName")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.QName.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class AttributedURI_Def(ZSI.TC.URI, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA200408.ADDRESS
        type = (schema, "AttributedURI")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.URI.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class EndpointReference_Dec(ElementDeclaration):
        literal = "EndpointReference"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"EndpointReference")
            kw["aname"] = "_EndpointReference"
            if soapwsa.EndpointReferenceType_Def not in soapwsa.EndpointReference_Dec.__bases__:
                bases = list(soapwsa.EndpointReference_Dec.__bases__)
                bases.insert(0, soapwsa.EndpointReferenceType_Def)
                soapwsa.EndpointReference_Dec.__bases__ = tuple(bases)

            soapwsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "EndpointReference_Dec_Holder"

    class MessageID_Dec(ElementDeclaration):
        literal = "MessageID"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"MessageID")
            kw["aname"] = "_MessageID"
            if soapwsa.AttributedURI_Def not in soapwsa.MessageID_Dec.__bases__:
                bases = list(soapwsa.MessageID_Dec.__bases__)
                bases.insert(0, soapwsa.AttributedURI_Def)
                soapwsa.MessageID_Dec.__bases__ = tuple(bases)

            soapwsa.AttributedURI_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "MessageID_Dec_Holder"

    class RelatesTo_Dec(ElementDeclaration):
        literal = "RelatesTo"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"RelatesTo")
            kw["aname"] = "_RelatesTo"
            if soapwsa.Relationship_Def not in soapwsa.RelatesTo_Dec.__bases__:
                bases = list(soapwsa.RelatesTo_Dec.__bases__)
                bases.insert(0, soapwsa.Relationship_Def)
                soapwsa.RelatesTo_Dec.__bases__ = tuple(bases)

            soapwsa.Relationship_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RelatesTo_Dec_Holder"

    class To_Dec(ElementDeclaration):
        literal = "To"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"To")
            kw["aname"] = "_To"
            if soapwsa.AttributedURI_Def not in soapwsa.To_Dec.__bases__:
                bases = list(soapwsa.To_Dec.__bases__)
                bases.insert(0, soapwsa.AttributedURI_Def)
                soapwsa.To_Dec.__bases__ = tuple(bases)

            soapwsa.AttributedURI_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "To_Dec_Holder"

    class Action_Dec(ElementDeclaration):
        literal = "Action"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"Action")
            kw["aname"] = "_Action"
            if soapwsa.AttributedURI_Def not in soapwsa.Action_Dec.__bases__:
                bases = list(soapwsa.Action_Dec.__bases__)
                bases.insert(0, soapwsa.AttributedURI_Def)
                soapwsa.Action_Dec.__bases__ = tuple(bases)

            soapwsa.AttributedURI_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Action_Dec_Holder"

    class From_Dec(ElementDeclaration):
        literal = "From"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"From")
            kw["aname"] = "_From"
            if soapwsa.EndpointReferenceType_Def not in soapwsa.From_Dec.__bases__:
                bases = list(soapwsa.From_Dec.__bases__)
                bases.insert(0, soapwsa.EndpointReferenceType_Def)
                soapwsa.From_Dec.__bases__ = tuple(bases)

            soapwsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "From_Dec_Holder"

    class ReplyTo_Dec(ElementDeclaration):
        literal = "ReplyTo"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"ReplyTo")
            kw["aname"] = "_ReplyTo"
            if soapwsa.EndpointReferenceType_Def not in soapwsa.ReplyTo_Dec.__bases__:
                bases = list(soapwsa.ReplyTo_Dec.__bases__)
                bases.insert(0, soapwsa.EndpointReferenceType_Def)
                soapwsa.ReplyTo_Dec.__bases__ = tuple(bases)

            soapwsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ReplyTo_Dec_Holder"

    class FaultTo_Dec(ElementDeclaration):
        literal = "FaultTo"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"FaultTo")
            kw["aname"] = "_FaultTo"
            if soapwsa.EndpointReferenceType_Def not in soapwsa.FaultTo_Dec.__bases__:
                bases = list(soapwsa.FaultTo_Dec.__bases__)
                bases.insert(0, soapwsa.EndpointReferenceType_Def)
                soapwsa.FaultTo_Dec.__bases__ = tuple(bases)

            soapwsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "FaultTo_Dec_Holder"

    class ReplyAfter_Dec(ElementDeclaration):
        literal = "ReplyAfter"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"ReplyAfter")
            kw["aname"] = "_ReplyAfter"
            if soapwsa.ReplyAfterType_Def not in soapwsa.ReplyAfter_Dec.__bases__:
                bases = list(soapwsa.ReplyAfter_Dec.__bases__)
                bases.insert(0, soapwsa.ReplyAfterType_Def)
                soapwsa.ReplyAfter_Dec.__bases__ = tuple(bases)

            soapwsa.ReplyAfterType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ReplyAfter_Dec_Holder"

    class RetryAfter_Dec(ElementDeclaration):
        literal = "RetryAfter"
        schema = NS.WSA200408.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA200408.ADDRESS,"RetryAfter")
            kw["aname"] = "_RetryAfter"
            if soapwsa.RetryAfterType_Def not in soapwsa.RetryAfter_Dec.__bases__:
                bases = list(soapwsa.RetryAfter_Dec.__bases__)
                bases.insert(0, soapwsa.RetryAfterType_Def)
                soapwsa.RetryAfter_Dec.__bases__ = tuple(bases)

            soapwsa.RetryAfterType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RetryAfter_Dec_Holder"

# end class soapwsa (tns: http://schemas.xmlsoap.org/ws/2004/08/addressing)
