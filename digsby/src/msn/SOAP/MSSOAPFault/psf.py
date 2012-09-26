import ZSI
import ZSI.TCcompound
from ZSI.schema import LocalElementDeclaration, ElementDeclaration, TypeDefinition, GTD, GED
from ZSI.generate.pyclass import pyclass_type

import ZSI.wstools.Namespaces as NS
from msn.SOAP import Namespaces as MSNS

class psf:
    targetNamespace = MSNS.PPCRL.FAULT

    class ppHeaderType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "ppHeaderType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = psf.ppHeaderType_Def.schema
            TClist = [GED(MSNS.PPCRL.FAULT,"serverVersion",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"PUID",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"configVersion",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"uiVersion",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"authstate",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"reqstatus",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"serverInfo",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"cookies",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"browserCookies",lazy=False, isref=True)(minOccurs=0, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"credProperties",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"extProperties",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded")), GED(MSNS.PPCRL.FAULT,"response",lazy=False, isref=True)(minOccurs=1, maxOccurs=1, nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._serverVersion = None
                    self._PUID = None
                    self._configVersion = None
                    self._uiVersion = None
                    self._authstate = None
                    self._reqstatus = None
                    self._serverInfo = None
                    self._cookies = None
                    self._browserCookies = None
                    self._credProperties = None
                    self._extProperties = None
                    self._response = None
                    return
            Holder.__name__ = "ppHeaderType_Holder"
            self.pyclass = Holder

    class serverVersionType_Def(ZSI.TCnumbers.Iinteger, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "serverVersionType")
        def __init__(self, pname, **kw):
            ZSI.TCnumbers.Iinteger.__init__(self, pname, pyclass=None, **kw)
            class Holder(int):
                typecode = self
            self.pyclass = Holder

    class PUIDType_Def(ZSI.TC.String, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "PUIDType")
        def __init__(self, pname, **kw):
            ZSI.TC.String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class configVersionType_Def(ZSI.TC.String, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "configVersionType")
        def __init__(self, pname, **kw):
            ZSI.TC.String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class uiVersionType_Def(ZSI.TC.String, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "uiVersionType")
        def __init__(self, pname, **kw):
            ZSI.TC.String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class authstateType_Def(ZSI.TC.String, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "authstateType")
        def __init__(self, pname, **kw):
            ZSI.TC.String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class reqstatusType_Def(ZSI.TC.String, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "reqstatusType")
        def __init__(self, pname, **kw):
            ZSI.TC.String.__init__(self, pname, pyclass=None, **kw)
            class Holder(str):
                typecode = self
            self.pyclass = Holder

    class serverInfoType_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = MSNS.PPCRL.FAULT
        type = (schema, "serverInfoType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["ServerTime"] = ZSI.TCtimes.gDateTime()
            self.attribute_typecode_dict["LocVersion"] = ZSI.TCnumbers.Iinteger()
            self.attribute_typecode_dict["RollingUpgradeState"] = ZSI.TC.String()
            self.attribute_typecode_dict["Path"] = ZSI.TC.String()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class browserCookieType_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = MSNS.PPCRL.FAULT
        type = (schema, "browserCookieType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Name"] = ZSI.TC.String()
            self.attribute_typecode_dict["URL"] = ZSI.TC.URI()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class browserCookieCollectionType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "browserCookieCollectionType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = psf.browserCookieCollectionType_Def.schema
            TClist = [GED(MSNS.PPCRL.FAULT,"browserCookie",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._browserCookie = None
                    return
            Holder.__name__ = "browserCookieCollectionType_Holder"
            self.pyclass = Holder

    class credPropertyType_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = MSNS.PPCRL.FAULT
        type = (schema, "credPropertyType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["Name"] = ZSI.TC.String()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class credPropertyCollectionType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "credPropertyCollectionType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = psf.credPropertyCollectionType_Def.schema
            TClist = [GED(MSNS.PPCRL.FAULT,"credProperty",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._credProperty = None
                    return
            Holder.__name__ = "credPropertyCollectionType_Holder"
            self.pyclass = Holder

    class extPropertyType_Def(ZSI.TC.String, TypeDefinition):
        # ComplexType/SimpleContent derivation of built-in type
        schema = MSNS.PPCRL.FAULT
        type = (schema, "extPropertyType")
        def __init__(self, pname, **kw):
            if getattr(self, "attribute_typecode_dict", None) is None: self.attribute_typecode_dict = {}
            # attribute handling code
            self.attribute_typecode_dict["IgnoreRememberMe"] = ZSI.TC.Boolean()
            self.attribute_typecode_dict["Domains"] = ZSI.TC.String()
            self.attribute_typecode_dict["Expiry"] = ZSI.TC.String()
            self.attribute_typecode_dict["Name"] = ZSI.TC.String()
            ZSI.TC.String.__init__(self, pname, **kw)
            class Holder(str):
                __metaclass__ = pyclass_type
                typecode = self
            self.pyclass = Holder

    class extPropertyCollectionType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "extPropertyCollectionType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = psf.extPropertyCollectionType_Def.schema
            TClist = [GED(MSNS.PPCRL.FAULT,"extProperty",lazy=False, isref=True)(minOccurs=0, maxOccurs="unbounded", nillable=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._extProperty = None
                    return
            Holder.__name__ = "extPropertyCollectionType_Holder"
            self.pyclass = Holder

    class internalerrorType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "internalerrorType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = psf.internalerrorType_Def.schema
            TClist = [ZSI.TCnumbers.IunsignedInt(pname=(ns,"code"), aname="_code", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), ZSI.TC.String(pname=(ns,"text"), aname="_text", minOccurs=0, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._code = None
                    self._text = None
                    return
            Holder.__name__ = "internalerrorType_Holder"
            self.pyclass = Holder

    class errorType_Def(ZSI.TCcompound.ComplexType, TypeDefinition):
        schema = MSNS.PPCRL.FAULT
        type = (schema, "errorType")
        def __init__(self, pname, ofwhat=(), attributes=None, extend=False, restrict=False, **kw):
            ns = psf.errorType_Def.schema
            TClist = [ZSI.TCnumbers.IunsignedInt(pname=(ns,"value"), aname="_value", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded")), GTD(MSNS.PPCRL.FAULT,"internalerrorType",lazy=False)(pname=(ns,"internalerror"), aname="_internalerror", minOccurs=1, maxOccurs=1, nillable=False, typed=False, encoded=kw.get("encoded"))]
            self.attribute_typecode_dict = attributes or {}
            if extend: TClist += ofwhat
            if restrict: TClist = ofwhat
            ZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, **kw)
            class Holder:
                __metaclass__ = pyclass_type
                typecode = self
                def __init__(self):
                    # pyclass
                    self._value = None
                    self._internalerror = None
                    return
            Holder.__name__ = "errorType_Holder"
            self.pyclass = Holder

    class pp_Dec(ElementDeclaration):
        literal = "pp"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"pp")
            kw["aname"] = "_pp"
            if psf.ppHeaderType_Def not in psf.pp_Dec.__bases__:
                bases = list(psf.pp_Dec.__bases__)
                bases.insert(0, psf.ppHeaderType_Def)
                psf.pp_Dec.__bases__ = tuple(bases)

            psf.ppHeaderType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "pp_Dec_Holder"

    class serverVersion_Dec(ElementDeclaration):
        literal = "serverVersion"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"serverVersion")
            kw["aname"] = "_serverVersion"
            if psf.serverVersionType_Def not in psf.serverVersion_Dec.__bases__:
                bases = list(psf.serverVersion_Dec.__bases__)
                bases.insert(0, psf.serverVersionType_Def)
                psf.serverVersion_Dec.__bases__ = tuple(bases)

            psf.serverVersionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "serverVersion_Dec_Holder"

    class PUID_Dec(ElementDeclaration):
        literal = "PUID"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"PUID")
            kw["aname"] = "_PUID"
            if psf.PUIDType_Def not in psf.PUID_Dec.__bases__:
                bases = list(psf.PUID_Dec.__bases__)
                bases.insert(0, psf.PUIDType_Def)
                psf.PUID_Dec.__bases__ = tuple(bases)

            psf.PUIDType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "PUID_Dec_Holder"

    class configVersion_Dec(ElementDeclaration):
        literal = "configVersion"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"configVersion")
            kw["aname"] = "_configVersion"
            if psf.configVersionType_Def not in psf.configVersion_Dec.__bases__:
                bases = list(psf.configVersion_Dec.__bases__)
                bases.insert(0, psf.configVersionType_Def)
                psf.configVersion_Dec.__bases__ = tuple(bases)

            psf.configVersionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "configVersion_Dec_Holder"

    class uiVersion_Dec(ElementDeclaration):
        literal = "uiVersion"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"uiVersion")
            kw["aname"] = "_uiVersion"
            if psf.uiVersionType_Def not in psf.uiVersion_Dec.__bases__:
                bases = list(psf.uiVersion_Dec.__bases__)
                bases.insert(0, psf.uiVersionType_Def)
                psf.uiVersion_Dec.__bases__ = tuple(bases)

            psf.uiVersionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "uiVersion_Dec_Holder"

    class authstate_Dec(ElementDeclaration):
        literal = "authstate"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"authstate")
            kw["aname"] = "_authstate"
            if psf.authstateType_Def not in psf.authstate_Dec.__bases__:
                bases = list(psf.authstate_Dec.__bases__)
                bases.insert(0, psf.authstateType_Def)
                psf.authstate_Dec.__bases__ = tuple(bases)

            psf.authstateType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "authstate_Dec_Holder"

    class reqstatus_Dec(ElementDeclaration):
        literal = "reqstatus"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"reqstatus")
            kw["aname"] = "_reqstatus"
            if psf.reqstatusType_Def not in psf.reqstatus_Dec.__bases__:
                bases = list(psf.reqstatus_Dec.__bases__)
                bases.insert(0, psf.reqstatusType_Def)
                psf.reqstatus_Dec.__bases__ = tuple(bases)

            psf.reqstatusType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "reqstatus_Dec_Holder"

    class serverInfo_Dec(ElementDeclaration):
        literal = "serverInfo"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"serverInfo")
            kw["aname"] = "_serverInfo"
            if psf.serverInfoType_Def not in psf.serverInfo_Dec.__bases__:
                bases = list(psf.serverInfo_Dec.__bases__)
                bases.insert(0, psf.serverInfoType_Def)
                psf.serverInfo_Dec.__bases__ = tuple(bases)

            psf.serverInfoType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "serverInfo_Dec_Holder"

    class cookies_Dec(ZSI.TC.AnyType, ElementDeclaration):
        literal = "cookies"
        schema = MSNS.PPCRL.FAULT
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"cookies")
            kw["aname"] = "_cookies"
            ZSI.TC.AnyType.__init__(self, **kw)

    class browserCookie_Dec(ElementDeclaration):
        literal = "browserCookie"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"browserCookie")
            kw["aname"] = "_browserCookie"
            if psf.browserCookieType_Def not in psf.browserCookie_Dec.__bases__:
                bases = list(psf.browserCookie_Dec.__bases__)
                bases.insert(0, psf.browserCookieType_Def)
                psf.browserCookie_Dec.__bases__ = tuple(bases)

            psf.browserCookieType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "browserCookie_Dec_Holder"

    class browserCookies_Dec(ElementDeclaration):
        literal = "browserCookies"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"browserCookies")
            kw["aname"] = "_browserCookies"
            if psf.browserCookieCollectionType_Def not in psf.browserCookies_Dec.__bases__:
                bases = list(psf.browserCookies_Dec.__bases__)
                bases.insert(0, psf.browserCookieCollectionType_Def)
                psf.browserCookies_Dec.__bases__ = tuple(bases)

            psf.browserCookieCollectionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "browserCookies_Dec_Holder"

    class credProperty_Dec(ElementDeclaration):
        literal = "credProperty"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"credProperty")
            kw["aname"] = "_credProperty"
            if psf.credPropertyType_Def not in psf.credProperty_Dec.__bases__:
                bases = list(psf.credProperty_Dec.__bases__)
                bases.insert(0, psf.credPropertyType_Def)
                psf.credProperty_Dec.__bases__ = tuple(bases)

            psf.credPropertyType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "credProperty_Dec_Holder"

    class credProperties_Dec(ElementDeclaration):
        literal = "credProperties"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"credProperties")
            kw["aname"] = "_credProperties"
            if psf.credPropertyCollectionType_Def not in psf.credProperties_Dec.__bases__:
                bases = list(psf.credProperties_Dec.__bases__)
                bases.insert(0, psf.credPropertyCollectionType_Def)
                psf.credProperties_Dec.__bases__ = tuple(bases)

            psf.credPropertyCollectionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "credProperties_Dec_Holder"

    class extProperty_Dec(ElementDeclaration):
        literal = "extProperty"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"extProperty")
            kw["aname"] = "_extProperty"
            if psf.extPropertyType_Def not in psf.extProperty_Dec.__bases__:
                bases = list(psf.extProperty_Dec.__bases__)
                bases.insert(0, psf.extPropertyType_Def)
                psf.extProperty_Dec.__bases__ = tuple(bases)

            psf.extPropertyType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "extProperty_Dec_Holder"

    class extProperties_Dec(ElementDeclaration):
        literal = "extProperties"
        schema = MSNS.PPCRL.FAULT
        substitutionGroup = None
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"extProperties")
            kw["aname"] = "_extProperties"
            if psf.extPropertyCollectionType_Def not in psf.extProperties_Dec.__bases__:
                bases = list(psf.extProperties_Dec.__bases__)
                bases.insert(0, psf.extPropertyCollectionType_Def)
                psf.extProperties_Dec.__bases__ = tuple(bases)

            psf.extPropertyCollectionType_Def.__init__(self, **kw)
            if self.pyclass is not None: self.pyclass.__name__ = "extProperties_Dec_Holder"

    class response_Dec(ZSI.TC.AnyType, ElementDeclaration):
        literal = "response"
        schema = MSNS.PPCRL.FAULT
        def __init__(self, **kw):
            kw["pname"] = (MSNS.PPCRL.FAULT,"response")
            kw["aname"] = "_response"
            ZSI.TC.AnyType.__init__(self, **kw)

# end class psf (tns: http://schemas.microsoft.com/Passport/SoapServices/SOAPFault)

