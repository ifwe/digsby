import ZSI
import ZSI.TCcompound
import ZSI.wstools.Namespaces as NS
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# http://schemas.xmlsoap.org/ws/2004/09/policy
##############################

class wsp:
    targetNamespace = NS.WSP.POLICY

    class AppliesTo_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "AppliesTo"
        schema = NS.WSP.POLICY
        def __init__(self, **kw):
            ns = wsp.AppliesTo_Dec.schema
            TClist = [GED(NS.WSA.ADDRESS,"EndpointReference",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            kw["pname"] = (NS.WSP.POLICY,"AppliesTo")
            kw["aname"] = "_AppliesTo"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._EndpointReference = None
                    return
            Holder.__name__ = "AppliesTo_Holder"
            self.pyclass = Holder

    class PolicyReference_Dec(ZSI.TCcompound.ComplexType, ElementDeclaration):
        literal = "PolicyReference"
        schema = NS.WSP.POLICY
        def __init__(self, **kw):
            ns = wsp.PolicyReference_Dec.schema
            TClist = []
            kw["pname"] = (NS.WSP.POLICY,"PolicyReference")
            kw["aname"] = "_PolicyReference"
            self.attribute_typecode_dict = {}
            ZSI.TCcompound.ComplexType.__init__(self,None,TClist,inorder=0,**kw)
            # attribute handling code
            self.attribute_typecode_dict["URI"] = ZSI.TC.String()
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "PolicyReference_Holder"
            self.pyclass = Holder

# end class wsp (tns: http://schemas.xmlsoap.org/ws/2004/09/policy)
