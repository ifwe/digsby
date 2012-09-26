import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://www.w3.org/2005/08/addressing
##############################

class wsa:
    targetNamespace = NS.WSA.ADDRESS

    class EndpointReferenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.ADDRESS
        type = (schema, "EndpointReferenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsa.EndpointReferenceType_Def.schema
            TClist = [GTD(NS.WSA.ADDRESS,"AttributedURIType",lazy=False)(pname=(ns,"Address"), aname="_Address", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GED(NS.WSA.ADDRESS,"ReferenceParameters",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.WSA.ADDRESS,"Metadata",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
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
                    self._ReferenceParameters = None
                    self._Metadata = None
                    self._any = []
                    return
            Holder.__name__ = "EndpointReferenceType_Holder"
            self.pyclass = Holder

    class ReferenceParametersType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.ADDRESS
        type = (schema, "ReferenceParametersType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsa.ReferenceParametersType_Def.schema
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
            Holder.__name__ = "ReferenceParametersType_Holder"
            self.pyclass = Holder

    class MetadataType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.ADDRESS
        type = (schema, "MetadataType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsa.MetadataType_Def.schema
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
            Holder.__name__ = "MetadataType_Holder"
            self.pyclass = Holder

    class RelatesToType_Def(ZSI.TC.URI, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA.ADDRESS
        type = (schema, "RelatesToType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["RelationshipType"] = wsa.RelationshipTypeOpenEnum_Def(None)
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.URI.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class RelationshipTypeOpenEnum_Def(ZSI.TC.Union, TypeDefinition):
        memberTypes = [(NS.WSA.ADDRESS, u'RelationshipType'), (NS.SCHEMA.BASE, u'anyURI')]
        schema = NS.WSA.ADDRESS
        type = (schema, "RelationshipTypeOpenEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.Union.__init__(self, pname, **kw)

    class RelationshipType_Def(ZSI.TC.URI, TypeDefinition):
        schema = NS.WSA.ADDRESS
        type = (schema, "RelationshipType")
        def __init__(self, pname, **kw):
            ZSI.TC.URI.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class AttributedURIType_Def(ZSI.TC.URI, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA.ADDRESS
        type = (schema, "AttributedURIType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.URI.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class FaultCodesOpenEnumType_Def(ZSI.TC.Union, TypeDefinition):
        memberTypes = [(NS.WSA.ADDRESS, u'FaultCodesType'), (NS.SCHEMA.BASE, u'QName')]
        schema = NS.WSA.ADDRESS
        type = (schema, "FaultCodesOpenEnumType")
        def __init__(self, pname, **kw):
            ZSI.TC.Union.__init__(self, pname, **kw)

    class FaultCodesType_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSA.ADDRESS
        type = (schema, "FaultCodesType")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class AttributedUnsignedLongType_Def(ZSI.TCnumbers.IunsignedLong, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA.ADDRESS
        type = (schema, "AttributedUnsignedLongType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCnumbers.IunsignedLong.__init__(self, pname, **kw)
            class Holder(long):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class AttributedQNameType_Def(ZSI.TC.QName, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = NS.WSA.ADDRESS
        type = (schema, "AttributedQNameType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TC.QName.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class ProblemActionType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.ADDRESS
        type = (schema, "ProblemActionType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsa.ProblemActionType_Def.schema
            TClist = [GED(NS.WSA.ADDRESS,"Action",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.URI(pname=(ns,"SoapAction"), aname="_SoapAction", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
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
                    self._Action = None
                    self._SoapAction = None
                    return
            Holder.__name__ = "ProblemActionType_Holder"
            self.pyclass = Holder

    class EndpointReference_Dec(ElementDeclaration):
        literal = "EndpointReference"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"EndpointReference")
            kw["aname"] = "_EndpointReference"
            if wsa.EndpointReferenceType_Def not in wsa.EndpointReference_Dec.__bases__:
                bases = list(wsa.EndpointReference_Dec.__bases__)
                bases.insert(0, wsa.EndpointReferenceType_Def)
                wsa.EndpointReference_Dec.__bases__ = tuple(bases)

            wsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "EndpointReference_Dec_Holder"

    class ReferenceParameters_Dec(ElementDeclaration):
        literal = "ReferenceParameters"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"ReferenceParameters")
            kw["aname"] = "_ReferenceParameters"
            if wsa.ReferenceParametersType_Def not in wsa.ReferenceParameters_Dec.__bases__:
                bases = list(wsa.ReferenceParameters_Dec.__bases__)
                bases.insert(0, wsa.ReferenceParametersType_Def)
                wsa.ReferenceParameters_Dec.__bases__ = tuple(bases)

            wsa.ReferenceParametersType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ReferenceParameters_Dec_Holder"

    class Metadata_Dec(ElementDeclaration):
        literal = "Metadata"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"Metadata")
            kw["aname"] = "_Metadata"
            if wsa.MetadataType_Def not in wsa.Metadata_Dec.__bases__:
                bases = list(wsa.Metadata_Dec.__bases__)
                bases.insert(0, wsa.MetadataType_Def)
                wsa.Metadata_Dec.__bases__ = tuple(bases)

            wsa.MetadataType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Metadata_Dec_Holder"

    class MessageID_Dec(ElementDeclaration):
        literal = "MessageID"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"MessageID")
            kw["aname"] = "_MessageID"
            if wsa.AttributedURIType_Def not in wsa.MessageID_Dec.__bases__:
                bases = list(wsa.MessageID_Dec.__bases__)
                bases.insert(0, wsa.AttributedURIType_Def)
                wsa.MessageID_Dec.__bases__ = tuple(bases)

            wsa.AttributedURIType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "MessageID_Dec_Holder"

    class RelatesTo_Dec(ElementDeclaration):
        literal = "RelatesTo"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"RelatesTo")
            kw["aname"] = "_RelatesTo"
            if wsa.RelatesToType_Def not in wsa.RelatesTo_Dec.__bases__:
                bases = list(wsa.RelatesTo_Dec.__bases__)
                bases.insert(0, wsa.RelatesToType_Def)
                wsa.RelatesTo_Dec.__bases__ = tuple(bases)

            wsa.RelatesToType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RelatesTo_Dec_Holder"

    class ReplyTo_Dec(ElementDeclaration):
        literal = "ReplyTo"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"ReplyTo")
            kw["aname"] = "_ReplyTo"
            if wsa.EndpointReferenceType_Def not in wsa.ReplyTo_Dec.__bases__:
                bases = list(wsa.ReplyTo_Dec.__bases__)
                bases.insert(0, wsa.EndpointReferenceType_Def)
                wsa.ReplyTo_Dec.__bases__ = tuple(bases)

            wsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ReplyTo_Dec_Holder"

    class From_Dec(ElementDeclaration):
        literal = "From"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"From")
            kw["aname"] = "_From"
            if wsa.EndpointReferenceType_Def not in wsa.From_Dec.__bases__:
                bases = list(wsa.From_Dec.__bases__)
                bases.insert(0, wsa.EndpointReferenceType_Def)
                wsa.From_Dec.__bases__ = tuple(bases)

            wsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "From_Dec_Holder"

    class FaultTo_Dec(ElementDeclaration):
        literal = "FaultTo"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"FaultTo")
            kw["aname"] = "_FaultTo"
            if wsa.EndpointReferenceType_Def not in wsa.FaultTo_Dec.__bases__:
                bases = list(wsa.FaultTo_Dec.__bases__)
                bases.insert(0, wsa.EndpointReferenceType_Def)
                wsa.FaultTo_Dec.__bases__ = tuple(bases)

            wsa.EndpointReferenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "FaultTo_Dec_Holder"

    class To_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "To"
        schema = NS.WSA.ADDRESS
        def __init__(self, **kw):
            ns = wsa.To_Dec.schema
            TClist = []
            kw["pname"] = (NS.WSA.ADDRESS,"To")
            kw["aname"] = "_To"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "To_Holder"
            self.pyclass = Holder

    class Action_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "Action"
        schema = NS.WSA.ADDRESS
        def __init__(self, **kw):
            ns = wsa.Action_Dec.schema
            TClist = []
            kw["pname"] = (NS.WSA.ADDRESS,"Action")
            kw["aname"] = "_Action"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "Action_Holder"
            self.pyclass = Holder

    class RetryAfter_Dec(ElementDeclaration):
        literal = "RetryAfter"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"RetryAfter")
            kw["aname"] = "_RetryAfter"
            if wsa.AttributedUnsignedLongType_Def not in wsa.RetryAfter_Dec.__bases__:
                bases = list(wsa.RetryAfter_Dec.__bases__)
                bases.insert(0, wsa.AttributedUnsignedLongType_Def)
                wsa.RetryAfter_Dec.__bases__ = tuple(bases)

            wsa.AttributedUnsignedLongType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "RetryAfter_Dec_Holder"

    class ProblemHeaderQName_Dec(ElementDeclaration):
        literal = "ProblemHeaderQName"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"ProblemHeaderQName")
            kw["aname"] = "_ProblemHeaderQName"
            if wsa.AttributedQNameType_Def not in wsa.ProblemHeaderQName_Dec.__bases__:
                bases = list(wsa.ProblemHeaderQName_Dec.__bases__)
                bases.insert(0, wsa.AttributedQNameType_Def)
                wsa.ProblemHeaderQName_Dec.__bases__ = tuple(bases)

            wsa.AttributedQNameType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ProblemHeaderQName_Dec_Holder"

    class ProblemIRI_Dec(ElementDeclaration):
        literal = "ProblemIRI"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"ProblemIRI")
            kw["aname"] = "_ProblemIRI"
            if wsa.AttributedURIType_Def not in wsa.ProblemIRI_Dec.__bases__:
                bases = list(wsa.ProblemIRI_Dec.__bases__)
                bases.insert(0, wsa.AttributedURIType_Def)
                wsa.ProblemIRI_Dec.__bases__ = tuple(bases)

            wsa.AttributedURIType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ProblemIRI_Dec_Holder"

    class ProblemAction_Dec(ElementDeclaration):
        literal = "ProblemAction"
        schema = NS.WSA.ADDRESS
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.ADDRESS,"ProblemAction")
            kw["aname"] = "_ProblemAction"
            if wsa.ProblemActionType_Def not in wsa.ProblemAction_Dec.__bases__:
                bases = list(wsa.ProblemAction_Dec.__bases__)
                bases.insert(0, wsa.ProblemActionType_Def)
                wsa.ProblemAction_Dec.__bases__ = tuple(bases)

            wsa.ProblemActionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ProblemAction_Dec_Holder"

# end class wsa (tns: http://www.w3.org/2005/08/addressing)
