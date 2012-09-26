#include <wx/textctrl.h>
#include <wx/log.h>

#include <windows.h>
#include <richedit.h>

bool GetRichEditParaFormat(HWND handle, PARAFORMAT2* pf)
{
    pf->cbSize = sizeof(PARAFORMAT2);

    if (!::SendMessage(handle, EM_GETPARAFORMAT, 0, (LPARAM)pf)) {
        fprintf(stderr, "SendMessage(EM_GETPARAFORMAT) failed");
        return false;
    }

    return true;
}

bool SetRichEditParaFormat(HWND handle, PARAFORMAT2* pf)
{
    if (!::SendMessage(handle, EM_SETPARAFORMAT, 0, (LPARAM)pf)) {
        fprintf(stderr, "SendMessage(EM_SETPARAFORMAT) failed");
        return false;
    }

    return true;
}

int GetRichEditParagraphAlignment(HWND handle)
{
    PARAFORMAT2 pf;
    if (!GetRichEditParaFormat(handle, &pf))
        return 0;

    return pf.wAlignment;
}

bool SetRichEditParagraphAlignment(HWND handle, int alignment)
{
    PARAFORMAT2 pf;
    pf.cbSize = sizeof(PARAFORMAT2);
    pf.dwMask = PFM_ALIGNMENT | PFM_RTLPARA;

    /* affects position/alignment of text */
    pf.wAlignment = alignment;

    /* affects sentence direction */
    pf.wEffects = (alignment & PFA_RIGHT ? PFE_RTLPARA : 0);

    return SetRichEditParaFormat(handle, &pf);
}

int GetRichEditParagraphAlignment(wxTextCtrl* textCtrl)
{
    return GetRichEditParagraphAlignment((HWND)textCtrl->GetHWND());
}

bool SetRichEditParagraphAlignment(wxTextCtrl* textCtrl, int alignment)
{
    return SetRichEditParagraphAlignment((HWND)textCtrl->GetHWND(), alignment);
}


