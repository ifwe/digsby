class SkinBitmap : SkinBase
{
%TypeHeaderCode
#include "SkinBitmap.h"
%End

private:
    SkinBitmap(const SkinBitmap&);

public:
    SkinBitmap(const wxImage& image);
    virtual ~SkinBitmap();
    
    
    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);
    virtual void Draw(wxDC& dc, const wxPoint& point);

    size_t cacheLimit() const;
};

