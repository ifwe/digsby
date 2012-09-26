#ifndef AnimationPlatformWx_h
#define AnimationPlatformWx_h

#include <wx/bitmap.h>
#include <wx/gdicmn.h>
#include <wx/geometry.h>
#include <wx/graphics.h>
#include <wx/string.h>
#include <wx/timer.h>

#define ANIMATION_PLATFORM_WX

#include <google/sparse_hash_map>
using google::sparse_hash_map;
#include <wx/msw/winundef.h>

#include <cairo.h>
#include <cairo-win32.h>

typedef double Time;

struct Point {
    double x;
    double y;

    Point()
        : x(0)
        , y(0)
    {}

    Point(const wxPoint& pt)
    {
        x = pt.x;
        y = pt.y;
    }

    Point(double x_val, double y_val)
        : x(x_val)
        , y(y_val)
    {}

    Point operator*(double f)
    {
        return Point(x*f, y*f);
    }

    Point operator+(const Point& p)
    {
        return Point(x + p.x, y + p.y);
    }

    Point operator-(const Point& p)
    {
        return Point(x - p.x, y - p.y);
    }
};

typedef cairo_matrix_t Transform;
typedef cairo_surface_t* Bitmap;
typedef cairo_t GraphicsContext;
typedef cairo_matrix_t Matrix;
typedef cairo_font_face_t* Font;

typedef wxString String;
typedef wxRect2DDouble Rect;
typedef wxColour Color;

inline Time GetCurrentTimeSeconds()
{
    return static_cast<Time>(wxGetLocalTimeMillis().ToDouble() / 1000.0);
}


#endif // AnimationPlatformWx_h

