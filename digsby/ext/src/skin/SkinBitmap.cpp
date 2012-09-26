#include "SkinBitmap.h"

SkinBitmap::SkinBitmap(const wxImage& img)
    : cache_limit(5)
    , bitmap(0)
    , image(img)
{
}

SkinBitmap::~SkinBitmap()
{
    for (size_t i = 0; i < bitmap_cache.size(); ++i)
        delete bitmap_cache[i].second;

    bitmap_cache.clear();
}

void SkinBitmap::Draw(wxDC& dc, const wxRect& rect, int /*n*/)
{
    wxSize draw_size(rect.GetSize());

    /* if the size is our original size, just draw it */
    if (draw_size.x == image.GetWidth() && draw_size.y == image.GetHeight()) {
        Draw(dc, rect.GetTopLeft());
        return;
    }

    fprintf(stderr, "resizing image to (%d, %d)\n", draw_size.x, draw_size.y);

    for (size_t i = 0; i < bitmap_cache.size(); ++i) {
        BitmapCacheEntry e = bitmap_cache[i];
        if (e.first == draw_size) {
            dc.DrawBitmap(*e.second, rect.x, rect.y, true);
            return;
        }
    }

    wxBitmap resized_bitmap = *CacheResizedBitmap(draw_size);
    dc.DrawBitmap(resized_bitmap, rect.x, rect.y, true);
}

void SkinBitmap::Draw(wxDC& dc, const wxPoint& point)
{
    if (!bitmap)
        bitmap = new wxBitmap(image);

    dc.DrawBitmap(*bitmap, point.x, point.y, true);
}

const wxBitmap* SkinBitmap::CacheResizedBitmap(const wxSize& size)
{
    wxImage resized_img(image.Scale(size.x, size.y, wxIMAGE_QUALITY_HIGH));
    wxBitmap* resized_bitmap = new wxBitmap(resized_img);

    /* don't let the cache overflow past cacheLimit() */
    if (bitmap_cache.size() > cacheLimit()) {
        for (size_t i = 0; i < bitmap_cache.size() - 1; ++i)
            bitmap_cache[i] = bitmap_cache[i + 1];

        delete bitmap_cache[bitmap_cache.size() - 1].second;
        bitmap_cache.pop_back();
    }

    BitmapCacheEntry entry;
    entry.first = size;
    entry.second = resized_bitmap;
    bitmap_cache.push_back(entry);

    return resized_bitmap;
}



