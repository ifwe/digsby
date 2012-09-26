import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://schemas.xmlsoap.org/ws/2003/03/rm
##############################

class wsrm:
    targetNamespace = NS.WSA.RM

    class SequenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "SequenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsrm.SequenceType_Def.schema
            TClist = [GED(NS.WSU.UTILITY,"Identifier",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TCnumbers.IunsignedLong(pname=(ns,"MessageNumber"), aname="_MessageNumber", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyType(pname=(ns,"LastMessage"), aname="_LastMessage", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
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
                    self._Identifier = None
                    self._MessageNumber = None
                    self._LastMessage = None
                    self._any = []
                    return
            Holder.__name__ = "SequenceType_Holder"
            self.pyclass = Holder

    class AckRequestedType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "AckRequestedType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsrm.AckRequestedType_Def.schema
            TClist = [GED(NS.WSU.UTILITY,"Identifier",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
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
                    self._Identifier = None
                    self._any = []
                    return
            Holder.__name__ = "AckRequestedType_Holder"
            self.pyclass = Holder

    class PolicyAssertionType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "PolicyAssertionType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsrm.PolicyAssertionType_Def.schema
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
            Holder.__name__ = "PolicyAssertionType_Holder"
            self.pyclass = Holder

    class DeliveryAssuranceEnum_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "DeliveryAssuranceEnum")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class FaultCodes_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "FaultCodes")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class SequenceFaultType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "SequenceFaultType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsrm.SequenceFaultType_Def.schema
            TClist = [GED(NS.WSU.UTILITY,"Identifier",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.QName(pname=(ns,"FaultCode"), aname="_FaultCode", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=1, maxOccurs=1, nillable=False, processContents="strict")]
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
                    self._Identifier = None
                    self._FaultCode = None
                    self._any = None
                    return
            Holder.__name__ = "SequenceFaultType_Holder"
            self.pyclass = Holder

    class SequenceRefType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "SequenceRefType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = wsrm.SequenceRefType_Def.schema
            TClist = [ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Identifier"] = ZSI.TC.URI()
                self.attribute_typecode_dict["Match"] = wsrm.MatchChoiceType_Def(None)
                self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._any = []
                    return
            Holder.__name__ = "SequenceRefType_Holder"
            self.pyclass = Holder

    class MatchChoiceType_Def(ZSI.TC.QName, TypeDefinition):
        schema = NS.WSA.RM
        type = (schema, "MatchChoiceType")
        def __init__(self, pname, **kw):
            ZSI.TC.QName.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class Sequence_Dec(ElementDeclaration):
        literal = "Sequence"
        schema = NS.WSA.RM
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.RM,"Sequence")
            kw["aname"] = "_Sequence"
            if wsrm.SequenceType_Def not in wsrm.Sequence_Dec.__bases__:
                bases = list(wsrm.Sequence_Dec.__bases__)
                bases.insert(0, wsrm.SequenceType_Def)
                wsrm.Sequence_Dec.__bases__ = tuple(bases)

            wsrm.SequenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Sequence_Dec_Holder"

    class SequenceTerminate_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "SequenceTerminate"
        schema = NS.WSA.RM
        def __init__(self, **kw):
            ns = wsrm.SequenceTerminate_Dec.schema
            TClist = [GED(NS.WSU.UTILITY,"Identifier",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            kw["pname"] = (NS.WSA.RM,"SequenceTerminate")
            kw["aname"] = "_SequenceTerminate"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Identifier = None
                    self._any = []
                    return
            Holder.__name__ = "SequenceTerminate_Holder"
            self.pyclass = Holder

    class SequenceAcknowledgment_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "SequenceAcknowledgment"
        schema = NS.WSA.RM
        def __init__(self, **kw):
            ns = wsrm.SequenceAcknowledgment_Dec.schema
            TClist = [GED(NS.WSU.UTILITY,"Identifier",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), self.__class__.AcknowledgmentRange_Dec(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            kw["pname"] = (NS.WSA.RM,"SequenceAcknowledgment")
            kw["aname"] = "_SequenceAcknowledgment"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            # attribute handling code
            self.attribute_typecode_dict[(NS.SCHEMA.BASE,"anyAttribute")] = ZSI.TC.AnyElement()
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Identifier = None
                    self._AcknowledgmentRange = []
                    self._any = []
                    return
            Holder.__name__ = "SequenceAcknowledgment_Holder"
            self.pyclass = Holder


        class AcknowledgmentRange_Dec(ZSI.TCcompound.ComplexType, LocalElementDeclaration):
            literal = "AcknowledgmentRange"
            schema = NS.WSA.RM
            def __init__(self, **kw):
                ns = wsrm.SequenceAcknowledgment_Dec.AcknowledgmentRange_Dec.schema
                TClist = []
                kw["pname"] = (NS.WSA.RM,"AcknowledgmentRange")
                kw["aname"] = "_AcknowledgmentRange"
                self.attribute_typecode_dict = {}
                ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
                # attribute handling code
                self.attribute_typecode_dict["Upper"] = ZSI.TCnumbers.IunsignedLong()
                self.attribute_typecode_dict["Lower"] = ZSI.TCnumbers.IunsignedLong()
                class Holder:
                    __metaclass__ = pyclass_type
                    typecode = self
                    def __init__(self):
                        # pyclass
                        return
                Holder.__name__ = "AcknowledgmentRange_Holder"
                self.pyclass = Holder




    class AckRequested_Dec(ElementDeclaration):
        literal = "AckRequested"
        schema = NS.WSA.RM
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.RM,"AckRequested")
            kw["aname"] = "_AckRequested"
            if wsrm.AckRequestedType_Def not in wsrm.AckRequested_Dec.__bases__:
                bases = list(wsrm.AckRequested_Dec.__bases__)
                bases.insert(0, wsrm.AckRequestedType_Def)
                wsrm.AckRequested_Dec.__bases__ = tuple(bases)

            wsrm.AckRequestedType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "AckRequested_Dec_Holder"

    class InactivityTimeout_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "InactivityTimeout"
        schema = NS.WSA.RM
        def __init__(self, **kw):
            ns = wsrm.InactivityTimeout_Dec.schema
            TClist = []
            kw["pname"] = (NS.WSA.RM,"InactivityTimeout")
            kw["aname"] = "_InactivityTimeout"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "InactivityTimeout_Holder"
            self.pyclass = Holder

    class BaseRetransmissionInterval_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "BaseRetransmissionInterval"
        schema = NS.WSA.RM
        def __init__(self, **kw):
            ns = wsrm.BaseRetransmissionInterval_Dec.schema
            TClist = []
            kw["pname"] = (NS.WSA.RM,"BaseRetransmissionInterval")
            kw["aname"] = "_BaseRetransmissionInterval"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "BaseRetransmissionInterval_Holder"
            self.pyclass = Holder

    class ExponentialBackoff_Dec(ElementDeclaration):
        literal = "ExponentialBackoff"
        schema = NS.WSA.RM
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.RM,"ExponentialBackoff")
            kw["aname"] = "_ExponentialBackoff"
            if wsrm.PolicyAssertionType_Def not in wsrm.ExponentialBackoff_Dec.__bases__:
                bases = list(wsrm.ExponentialBackoff_Dec.__bases__)
                bases.insert(0, wsrm.PolicyAssertionType_Def)
                wsrm.ExponentialBackoff_Dec.__bases__ = tuple(bases)

            wsrm.PolicyAssertionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "ExponentialBackoff_Dec_Holder"

    class AcknowledgementInterval_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "AcknowledgementInterval"
        schema = NS.WSA.RM
        def __init__(self, **kw):
            ns = wsrm.AcknowledgementInterval_Dec.schema
            TClist = []
            kw["pname"] = (NS.WSA.RM,"AcknowledgementInterval")
            kw["aname"] = "_AcknowledgementInterval"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "AcknowledgementInterval_Holder"
            self.pyclass = Holder

    class DeliveryAssurance_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "DeliveryAssurance"
        schema = NS.WSA.RM
        def __init__(self, **kw):
            ns = wsrm.DeliveryAssurance_Dec.schema
            TClist = []
            kw["pname"] = (NS.WSA.RM,"DeliveryAssurance")
            kw["aname"] = "_DeliveryAssurance"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "DeliveryAssurance_Holder"
            self.pyclass = Holder

    class SequenceFault_Dec(ElementDeclaration):
        literal = "SequenceFault"
        schema = NS.WSA.RM
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.RM,"SequenceFault")
            kw["aname"] = "_SequenceFault"
            if wsrm.SequenceFaultType_Def not in wsrm.SequenceFault_Dec.__bases__:
                bases = list(wsrm.SequenceFault_Dec.__bases__)
                bases.insert(0, wsrm.SequenceFaultType_Def)
                wsrm.SequenceFault_Dec.__bases__ = tuple(bases)

            wsrm.SequenceFaultType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SequenceFault_Dec_Holder"

    class SequenceRef_Dec(ElementDeclaration):
        literal = "SequenceRef"
        schema = NS.WSA.RM
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (NS.WSA.RM,"SequenceRef")
            kw["aname"] = "_SequenceRef"
            if wsrm.SequenceRefType_Def not in wsrm.SequenceRef_Dec.__bases__:
                bases = list(wsrm.SequenceRef_Dec.__bases__)
                bases.insert(0, wsrm.SequenceRefType_Def)
                wsrm.SequenceRef_Dec.__bases__ = tuple(bases)

            wsrm.SequenceRefType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SequenceRef_Dec_Holder"

# end class wsrm (tns: http://schemas.xmlsoap.org/ws/2003/03/rm)
