

class RTFToX
{
%TypeHeaderCode
#include "RTFToX.h"
#include "HTMLEncoder.h"
#include "MSIMEncoder.h"
#include "MSNEncoder.h"
#include "XHTMLEncoder.h"
#include "YahooEncoder.h"
%End

public:

    static SIP_PYTUPLE EncoderTypes();
%MethodCode
    sipRes = Py_BuildValue("(sssss)",
        "html",
        "msim",
        "msn",
        "xhtml",
        "yahoo");
%End

    SIP_PYOBJECT Convert(const wxString& rtf, const wxString& encoder, const wxString& format, const wxTextAttr* style = 0);
%MethodCode

    Encoder* encoder = 0;

#ifdef ENC
#error enc already defined!!
#endif

    if (0);
#define ENC(type, encoderType) else if (*a1 == type) encoder = new encoderType()
    ENC(L"html", HTMLEncoder);
    ENC(L"msim", MSIMEncoder);
    ENC(L"msn",  MSNEncoder);
    ENC(L"xhtml", XHTMLEncoder);
    ENC(L"yahoo", YahooEncoder);
#undef ENC

    wxString res;
    if (encoder) {
        res = sipCpp->Convert(*a0, *encoder, *a2, a3);
        sipRes = PyUnicode_FromWideChar((const wchar_t*)res.c_str(), res.Len());
        delete encoder;
    } else {
        sipIsErr = 1;
        PyErr_SetString(PyExc_ValueError, "Invalid encoder type");
    }

%End

};
