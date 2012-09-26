#ifndef __SKINBITMAP_H__
#define __SKINBITMAP_H__

#include <wx/image.h>
#include <wx/bitmap.h>
#include <wx/gdicmn.h>

#include "skinobjects.h"

typedef std::pair<wxSize, wxBitmap*> BitmapCacheEntry;
typedef std::vector<BitmapCacheEntry> BitmapCache;

class SkinBitmap : public SkinBase
{
private:
    SkinBitmap(const SkinBitmap&);

public:
    SkinBitmap(const wxImage& image);
    virtual ~SkinBitmap();
    
    virtual void Draw(wxDC& dc, const wxRect& rect, int n = 0);
    virtual void Draw(wxDC& dc, const wxPoint& point);

    size_t cacheLimit() const { return static_cast<size_t>(cache_limit); }
   
protected:
    const wxBitmap* CacheResizedBitmap(const wxSize& size);

    wxImage image;
    wxBitmap* bitmap;

    BitmapCache bitmap_cache;

    unsigned char cache_limit;
};

#endif // __SKINBITMAP_H__
