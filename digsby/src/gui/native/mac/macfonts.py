'''
some Mac code from the internet

// Path to resource files in Mac bundle
wxString m_resourceDir;
// container of locally activated font
ATSFontContainerRef m_fontContainer;
FSSpec spec;

wxMacFilename2FSSpec(m_resourceDir + _T("Bank Gothic Light.ttf"),
&spec);
OSStatus status = ATSFontActivateFromFileSpecification(&spec,
kATSFontContextLocal, kATSFontFormatUnspecified, NULL,
kATSOptionFlagsDefault, &m_fontContainer);
wxASSERT_MSG(status == noErr, _T("font activation failed"));

and then anywhere in the app this works fine:
wxFont(9, wxFONTFAMILY_DEFAULT, wxFONTSTYLE_NORMAL |
wxFONTFLAG_ANTIALIASED, wxFONTWEIGHT_NORMAL, false, _T("Bank Gothic
Light"));
'''
import gui.native

def loadfont(fontpath, private = True, enumerable = False):
    gui.native.notImplemented()
    return False

def unloadfont(fontpath):
    gui.native.notImplemented()
    return False