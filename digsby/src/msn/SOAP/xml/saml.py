import ZSI
import ZSI.TCcompound
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

##############################
# targetNamespace
# urn:oasis:names:tc:SAML:1.0:assertion
##############################

class saml:
    targetNamespace = "urn:oasis:names:tc:SAML:1.0:assertion"

    class DecisionType_Def(ZSI.TC.String, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "DecisionType")
        def __init__(self, pname, **kw):
            ZSI.TC.String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class AssertionType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AssertionType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.AssertionType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","Conditions",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","Advice",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","Statement",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","SubjectStatement",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","AuthenticationStatement",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","AuthorizationDecisionStatement",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","AttributeStatement",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"Signature",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["MajorVersion"] = ZSI.TCnumbers.Iinteger()
                self.attribute_typecode_dict["MinorVersion"] = ZSI.TCnumbers.Iinteger()
                self.attribute_typecode_dict["AssertionID"] = ZSI.TC.AnyType()
                self.attribute_typecode_dict["Issuer"] = ZSI.TC.String()
                self.attribute_typecode_dict["IssueInstant"] = ZSI.TCtimes.gDateTime()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._Conditions = None
                    self._Advice = None
                    self._Statement = None
                    self._SubjectStatement = None
                    self._AuthenticationStatement = None
                    self._AuthorizationDecisionStatement = None
                    self._AttributeStatement = None
                    self._Signature = None
                    return
            Holder.__name__ = "AssertionType_Holder"
            self.pyclass = Holder

    class ConditionsType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "ConditionsType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.ConditionsType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","AudienceRestrictionCondition",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","DoNotCacheCondition",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","Condition",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["NotBefore"] = ZSI.TCtimes.gDateTime()
                self.attribute_typecode_dict["NotOnOrAfter"] = ZSI.TCtimes.gDateTime()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._AudienceRestrictionCondition = None
                    self._DoNotCacheCondition = None
                    self._Condition = None
                    return
            Holder.__name__ = "ConditionsType_Holder"
            self.pyclass = Holder

    class ConditionAbstractType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "ConditionAbstractType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.ConditionAbstractType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "ConditionAbstractType_Holder"
            self.pyclass = Holder

    class AudienceRestrictionConditionType_Def(TypeDefinition):
        #complexType/complexContent extension
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AudienceRestrictionConditionType")
        def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):
            ns = saml.AudienceRestrictionConditionType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","Audience",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            attributes = self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            if saml.ConditionAbstractType_Def not in saml.AudienceRestrictionConditionType_Def.__bases__:
                bases = list(saml.AudienceRestrictionConditionType_Def.__bases__)
                bases.insert(0, saml.ConditionAbstractType_Def)
                saml.AudienceRestrictionConditionType_Def.__bases__ = tuple(bases)

            saml.ConditionAbstractType_Def.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)

    class DoNotCacheConditionType_Def(TypeDefinition):
        #complexType/complexContent extension
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "DoNotCacheConditionType")
        def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):
            ns = saml.DoNotCacheConditionType_Def.schema
            TClist = []
            attributes = self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            if saml.ConditionAbstractType_Def not in saml.DoNotCacheConditionType_Def.__bases__:
                bases = list(saml.DoNotCacheConditionType_Def.__bases__)
                bases.insert(0, saml.ConditionAbstractType_Def)
                saml.DoNotCacheConditionType_Def.__bases__ = tuple(bases)

            saml.ConditionAbstractType_Def.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)

    class AdviceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AdviceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.AdviceType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","AssertionIDReference",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","Assertion",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), ZSI.TC.AnyElement(aname="_any", minOccurs=0, maxOccurs="unbounded", nillable=False, processContents="lax")]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._AssertionIDReference = None
                    self._Assertion = None
                    self._any = []
                    return
            Holder.__name__ = "AdviceType_Holder"
            self.pyclass = Holder

    class StatementAbstractType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "StatementAbstractType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.StatementAbstractType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "StatementAbstractType_Holder"
            self.pyclass = Holder

    class SubjectStatementAbstractType_Def(TypeDefinition):
        #complexType/complexContent extension
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "SubjectStatementAbstractType")
        def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):
            ns = saml.SubjectStatementAbstractType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","Subject",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            attributes = self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            if saml.StatementAbstractType_Def not in saml.SubjectStatementAbstractType_Def.__bases__:
                bases = list(saml.SubjectStatementAbstractType_Def.__bases__)
                bases.insert(0, saml.StatementAbstractType_Def)
                saml.SubjectStatementAbstractType_Def.__bases__ = tuple(bases)

            saml.StatementAbstractType_Def.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)

    class SubjectType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "SubjectType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.SubjectType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","NameIdentifier",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","SubjectConfirmation",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","SubjectConfirmation",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._NameIdentifier = None
                    self._SubjectConfirmation = None
                    self._SubjectConfirmation = None
                    return
            Holder.__name__ = "SubjectType_Holder"
            self.pyclass = Holder

    class NameIdentifierType_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "NameIdentifierType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["NameQualifier"] = ZSI.TC.String()
            self.attribute_typecode_dict["Format"] = ZSI.TC.URI()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class SubjectConfirmationType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "SubjectConfirmationType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.SubjectConfirmationType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","ConfirmationMethod",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","SubjectConfirmationData",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(NS.DSIG.BASE,"KeyInfo",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._ConfirmationMethod = None
                    self._SubjectConfirmationData = None
                    self._KeyInfo = None
                    return
            Holder.__name__ = "SubjectConfirmationType_Holder"
            self.pyclass = Holder

    class AuthenticationStatementType_Def(TypeDefinition):
        #complexType/complexContent extension
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AuthenticationStatementType")
        def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):
            ns = saml.AuthenticationStatementType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","SubjectLocality",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","AuthorityBinding",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            attributes = self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["AuthenticationMethod"] = ZSI.TC.URI()
                self.attribute_typecode_dict["AuthenticationInstant"] = ZSI.TCtimes.gDateTime()
            if saml.SubjectStatementAbstractType_Def not in saml.AuthenticationStatementType_Def.__bases__:
                bases = list(saml.AuthenticationStatementType_Def.__bases__)
                bases.insert(0, saml.SubjectStatementAbstractType_Def)
                saml.AuthenticationStatementType_Def.__bases__ = tuple(bases)

            saml.SubjectStatementAbstractType_Def.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)

    class SubjectLocalityType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "SubjectLocalityType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.SubjectLocalityType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["IPAddress"] = ZSI.TC.String()
                self.attribute_typecode_dict["DNSAddress"] = ZSI.TC.String()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "SubjectLocalityType_Holder"
            self.pyclass = Holder

    class AuthorityBindingType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AuthorityBindingType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.AuthorityBindingType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["AuthorityKind"] = ZSI.TC.QName()
                self.attribute_typecode_dict["Location"] = ZSI.TC.URI()
                self.attribute_typecode_dict["Binding"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "AuthorityBindingType_Holder"
            self.pyclass = Holder

    class AuthorizationDecisionStatementType_Def(TypeDefinition):
        #complexType/complexContent extension
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AuthorizationDecisionStatementType")
        def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):
            ns = saml.AuthorizationDecisionStatementType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","Action",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","Evidence",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            attributes = self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["Resource"] = ZSI.TC.URI()
                self.attribute_typecode_dict["Decision"] = saml.DecisionType_Def(None)
            if saml.SubjectStatementAbstractType_Def not in saml.AuthorizationDecisionStatementType_Def.__bases__:
                bases = list(saml.AuthorizationDecisionStatementType_Def.__bases__)
                bases.insert(0, saml.SubjectStatementAbstractType_Def)
                saml.AuthorizationDecisionStatementType_Def.__bases__ = tuple(bases)

            saml.SubjectStatementAbstractType_Def.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)

    class ActionType_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "ActionType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Namespace"] = ZSI.TC.URI()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class EvidenceType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "EvidenceType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.EvidenceType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","AssertionIDReference",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded")), GED("urn:oasis:names:tc:SAML:1.0:assertion","Assertion",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._AssertionIDReference = None
                    self._Assertion = None
                    return
            Holder.__name__ = "EvidenceType_Holder"
            self.pyclass = Holder

    class AttributeStatementType_Def(TypeDefinition):
        #complexType/complexContent extension
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AttributeStatementType")
        def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):
            ns = saml.AttributeStatementType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","Attribute",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            attributes = self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            if saml.SubjectStatementAbstractType_Def not in saml.AttributeStatementType_Def.__bases__:
                bases = list(saml.AttributeStatementType_Def.__bases__)
                bases.insert(0, saml.SubjectStatementAbstractType_Def)
                saml.AttributeStatementType_Def.__bases__ = tuple(bases)

            saml.SubjectStatementAbstractType_Def.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)

    class AttributeDesignatorType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AttributeDesignatorType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = saml.AttributeDesignatorType_Def.schema
            TClist = []
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            else:
                # attribute handling code
                self.attribute_typecode_dict["AttributeName"] = ZSI.TC.String()
                self.attribute_typecode_dict["AttributeNamespace"] = ZSI.TC.URI()
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    return
            Holder.__name__ = "AttributeDesignatorType_Holder"
            self.pyclass = Holder

    class AttributeType_Def(TypeDefinition):
        #complexType/complexContent extension
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        type = (schema, "AttributeType")
        def __init__(self, pname, ofwhat=(), extend=False, restrict=False, attributes=None, **kw):
            ns = saml.AttributeType_Def.schema
            TClist = [GED("urn:oasis:names:tc:SAML:1.0:assertion","AttributeValue",lazy=False, isref=True)(minOccurs=1, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            attributes = self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            if saml.AttributeDesignatorType_Def not in saml.AttributeType_Def.__bases__:
                bases = list(saml.AttributeType_Def.__bases__)
                bases.insert(0, saml.AttributeDesignatorType_Def)
                saml.AttributeType_Def.__bases__ = tuple(bases)

            saml.AttributeDesignatorType_Def.__init__(self, pname, ofwhat=TClist, extend=True, attributes=attributes, **kw)

    class AssertionIDReference_Dec(ZSI.TC.AnyType, ElementDeclaration):
        literal = "AssertionIDReference"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AssertionIDReference")
            kw["aname"] = "_AssertionIDReference"
            ZSI.TC.AnyType.__init__(self, **kw)

    class Assertion_Dec(ElementDeclaration):
        literal = "Assertion"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Assertion")
            kw["aname"] = "_Assertion"
            if saml.AssertionType_Def not in saml.Assertion_Dec.__bases__:
                bases = list(saml.Assertion_Dec.__bases__)
                bases.insert(0, saml.AssertionType_Def)
                saml.Assertion_Dec.__bases__ = tuple(bases)

            saml.AssertionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Assertion_Dec_Holder"

    class Conditions_Dec(ElementDeclaration):
        literal = "Conditions"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Conditions")
            kw["aname"] = "_Conditions"
            if saml.ConditionsType_Def not in saml.Conditions_Dec.__bases__:
                bases = list(saml.Conditions_Dec.__bases__)
                bases.insert(0, saml.ConditionsType_Def)
                saml.Conditions_Dec.__bases__ = tuple(bases)

            saml.ConditionsType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Conditions_Dec_Holder"

    class Condition_Dec(ElementDeclaration):
        literal = "Condition"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Condition")
            kw["aname"] = "_Condition"
            if saml.ConditionAbstractType_Def not in saml.Condition_Dec.__bases__:
                bases = list(saml.Condition_Dec.__bases__)
                bases.insert(0, saml.ConditionAbstractType_Def)
                saml.Condition_Dec.__bases__ = tuple(bases)

            saml.ConditionAbstractType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Condition_Dec_Holder"

    class AudienceRestrictionCondition_Dec(ElementDeclaration):
        literal = "AudienceRestrictionCondition"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AudienceRestrictionCondition")
            kw["aname"] = "_AudienceRestrictionCondition"
            if saml.AudienceRestrictionConditionType_Def not in saml.AudienceRestrictionCondition_Dec.__bases__:
                bases = list(saml.AudienceRestrictionCondition_Dec.__bases__)
                bases.insert(0, saml.AudienceRestrictionConditionType_Def)
                saml.AudienceRestrictionCondition_Dec.__bases__ = tuple(bases)

            saml.AudienceRestrictionConditionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "AudienceRestrictionCondition_Dec_Holder"

    class Audience_Dec(ZSI.TC.URI, ElementDeclaration):
        literal = "Audience"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Audience")
            kw["aname"] = "_Audience"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_Audience_immutable_holder"
            ZSI.TC.URI.__init__(self, **kw)

    class DoNotCacheCondition_Dec(ElementDeclaration):
        literal = "DoNotCacheCondition"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","DoNotCacheCondition")
            kw["aname"] = "_DoNotCacheCondition"
            if saml.DoNotCacheConditionType_Def not in saml.DoNotCacheCondition_Dec.__bases__:
                bases = list(saml.DoNotCacheCondition_Dec.__bases__)
                bases.insert(0, saml.DoNotCacheConditionType_Def)
                saml.DoNotCacheCondition_Dec.__bases__ = tuple(bases)

            saml.DoNotCacheConditionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "DoNotCacheCondition_Dec_Holder"

    class Advice_Dec(ElementDeclaration):
        literal = "Advice"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Advice")
            kw["aname"] = "_Advice"
            if saml.AdviceType_Def not in saml.Advice_Dec.__bases__:
                bases = list(saml.Advice_Dec.__bases__)
                bases.insert(0, saml.AdviceType_Def)
                saml.Advice_Dec.__bases__ = tuple(bases)

            saml.AdviceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Advice_Dec_Holder"

    class Statement_Dec(ElementDeclaration):
        literal = "Statement"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Statement")
            kw["aname"] = "_Statement"
            if saml.StatementAbstractType_Def not in saml.Statement_Dec.__bases__:
                bases = list(saml.Statement_Dec.__bases__)
                bases.insert(0, saml.StatementAbstractType_Def)
                saml.Statement_Dec.__bases__ = tuple(bases)

            saml.StatementAbstractType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Statement_Dec_Holder"

    class SubjectStatement_Dec(ElementDeclaration):
        literal = "SubjectStatement"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","SubjectStatement")
            kw["aname"] = "_SubjectStatement"
            if saml.SubjectStatementAbstractType_Def not in saml.SubjectStatement_Dec.__bases__:
                bases = list(saml.SubjectStatement_Dec.__bases__)
                bases.insert(0, saml.SubjectStatementAbstractType_Def)
                saml.SubjectStatement_Dec.__bases__ = tuple(bases)

            saml.SubjectStatementAbstractType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SubjectStatement_Dec_Holder"

    class Subject_Dec(ElementDeclaration):
        literal = "Subject"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Subject")
            kw["aname"] = "_Subject"
            if saml.SubjectType_Def not in saml.Subject_Dec.__bases__:
                bases = list(saml.Subject_Dec.__bases__)
                bases.insert(0, saml.SubjectType_Def)
                saml.Subject_Dec.__bases__ = tuple(bases)

            saml.SubjectType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Subject_Dec_Holder"

    class NameIdentifier_Dec(ElementDeclaration):
        literal = "NameIdentifier"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","NameIdentifier")
            kw["aname"] = "_NameIdentifier"
            if saml.NameIdentifierType_Def not in saml.NameIdentifier_Dec.__bases__:
                bases = list(saml.NameIdentifier_Dec.__bases__)
                bases.insert(0, saml.NameIdentifierType_Def)
                saml.NameIdentifier_Dec.__bases__ = tuple(bases)

            saml.NameIdentifierType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "NameIdentifier_Dec_Holder"

    class SubjectConfirmation_Dec(ElementDeclaration):
        literal = "SubjectConfirmation"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","SubjectConfirmation")
            kw["aname"] = "_SubjectConfirmation"
            if saml.SubjectConfirmationType_Def not in saml.SubjectConfirmation_Dec.__bases__:
                bases = list(saml.SubjectConfirmation_Dec.__bases__)
                bases.insert(0, saml.SubjectConfirmationType_Def)
                saml.SubjectConfirmation_Dec.__bases__ = tuple(bases)

            saml.SubjectConfirmationType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SubjectConfirmation_Dec_Holder"

    class SubjectConfirmationData_Dec(ZSI.TC.AnyType, ElementDeclaration):
        literal = "SubjectConfirmationData"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","SubjectConfirmationData")
            kw["aname"] = "_SubjectConfirmationData"
            ZSI.TC.AnyType.__init__(self, **kw)

    class ConfirmationMethod_Dec(ZSI.TC.URI, ElementDeclaration):
        literal = "ConfirmationMethod"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","ConfirmationMethod")
            kw["aname"] = "_ConfirmationMethod"
            class IHolder(str): typecode=self
            kw["pyclass"] = IHolder
            IHolder.__name__ = "_ConfirmationMethod_immutable_holder"
            ZSI.TC.URI.__init__(self, **kw)

    class AuthenticationStatement_Dec(ElementDeclaration):
        literal = "AuthenticationStatement"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AuthenticationStatement")
            kw["aname"] = "_AuthenticationStatement"
            if saml.AuthenticationStatementType_Def not in saml.AuthenticationStatement_Dec.__bases__:
                bases = list(saml.AuthenticationStatement_Dec.__bases__)
                bases.insert(0, saml.AuthenticationStatementType_Def)
                saml.AuthenticationStatement_Dec.__bases__ = tuple(bases)

            saml.AuthenticationStatementType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "AuthenticationStatement_Dec_Holder"

    class SubjectLocality_Dec(ElementDeclaration):
        literal = "SubjectLocality"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","SubjectLocality")
            kw["aname"] = "_SubjectLocality"
            if saml.SubjectLocalityType_Def not in saml.SubjectLocality_Dec.__bases__:
                bases = list(saml.SubjectLocality_Dec.__bases__)
                bases.insert(0, saml.SubjectLocalityType_Def)
                saml.SubjectLocality_Dec.__bases__ = tuple(bases)

            saml.SubjectLocalityType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "SubjectLocality_Dec_Holder"

    class AuthorityBinding_Dec(ElementDeclaration):
        literal = "AuthorityBinding"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AuthorityBinding")
            kw["aname"] = "_AuthorityBinding"
            if saml.AuthorityBindingType_Def not in saml.AuthorityBinding_Dec.__bases__:
                bases = list(saml.AuthorityBinding_Dec.__bases__)
                bases.insert(0, saml.AuthorityBindingType_Def)
                saml.AuthorityBinding_Dec.__bases__ = tuple(bases)

            saml.AuthorityBindingType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "AuthorityBinding_Dec_Holder"

    class AuthorizationDecisionStatement_Dec(ElementDeclaration):
        literal = "AuthorizationDecisionStatement"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AuthorizationDecisionStatement")
            kw["aname"] = "_AuthorizationDecisionStatement"
            if saml.AuthorizationDecisionStatementType_Def not in saml.AuthorizationDecisionStatement_Dec.__bases__:
                bases = list(saml.AuthorizationDecisionStatement_Dec.__bases__)
                bases.insert(0, saml.AuthorizationDecisionStatementType_Def)
                saml.AuthorizationDecisionStatement_Dec.__bases__ = tuple(bases)

            saml.AuthorizationDecisionStatementType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "AuthorizationDecisionStatement_Dec_Holder"

    class Action_Dec(ElementDeclaration):
        literal = "Action"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Action")
            kw["aname"] = "_Action"
            if saml.ActionType_Def not in saml.Action_Dec.__bases__:
                bases = list(saml.Action_Dec.__bases__)
                bases.insert(0, saml.ActionType_Def)
                saml.Action_Dec.__bases__ = tuple(bases)

            saml.ActionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Action_Dec_Holder"

    class Evidence_Dec(ElementDeclaration):
        literal = "Evidence"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Evidence")
            kw["aname"] = "_Evidence"
            if saml.EvidenceType_Def not in saml.Evidence_Dec.__bases__:
                bases = list(saml.Evidence_Dec.__bases__)
                bases.insert(0, saml.EvidenceType_Def)
                saml.Evidence_Dec.__bases__ = tuple(bases)

            saml.EvidenceType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Evidence_Dec_Holder"

    class AttributeStatement_Dec(ElementDeclaration):
        literal = "AttributeStatement"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AttributeStatement")
            kw["aname"] = "_AttributeStatement"
            if saml.AttributeStatementType_Def not in saml.AttributeStatement_Dec.__bases__:
                bases = list(saml.AttributeStatement_Dec.__bases__)
                bases.insert(0, saml.AttributeStatementType_Def)
                saml.AttributeStatement_Dec.__bases__ = tuple(bases)

            saml.AttributeStatementType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "AttributeStatement_Dec_Holder"

    class AttributeDesignator_Dec(ElementDeclaration):
        literal = "AttributeDesignator"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AttributeDesignator")
            kw["aname"] = "_AttributeDesignator"
            if saml.AttributeDesignatorType_Def not in saml.AttributeDesignator_Dec.__bases__:
                bases = list(saml.AttributeDesignator_Dec.__bases__)
                bases.insert(0, saml.AttributeDesignatorType_Def)
                saml.AttributeDesignator_Dec.__bases__ = tuple(bases)

            saml.AttributeDesignatorType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "AttributeDesignator_Dec_Holder"

    class Attribute_Dec(ElementDeclaration):
        literal = "Attribute"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","Attribute")
            kw["aname"] = "_Attribute"
            if saml.AttributeType_Def not in saml.Attribute_Dec.__bases__:
                bases = list(saml.Attribute_Dec.__bases__)
                bases.insert(0, saml.AttributeType_Def)
                saml.Attribute_Dec.__bases__ = tuple(bases)

            saml.AttributeType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "Attribute_Dec_Holder"

    class AttributeValue_Dec(ZSI.TC.AnyType, ElementDeclaration):
        literal = "AttributeValue"
        schema = "urn:oasis:names:tc:SAML:1.0:assertion"
        def __init__(self, **kw):
            kw["pname"] = ("urn:oasis:names:tc:SAML:1.0:assertion","AttributeValue")
            kw["aname"] = "_AttributeValue"
            ZSI.TC.AnyType.__init__(self, **kw)

# end class saml (tns: urn:oasis:names:tc:SAML:1.0:assertion)

