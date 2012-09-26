#ifndef __SPLITIMAGE4__
#define __SPLITIMAGE4__

#include "wx/wx.h"

long getObjectRef(wxObject* obj);


class Extend{
public:
    Extend(bool up = false, bool down = false, bool left = false, bool right = false):
        up(up),
        down(down),
        left(left),
        right(right) {}


    ~Extend() {}

    bool up, down, left, right;
};


Extend extendCopy(const Extend& e);

class Region{
public:
    Region(const Extend& extends, int hstyle, int vstyle, int align, wxPoint offset):
        extends(extends),
        hstyle(hstyle),
        vstyle(vstyle),
        align(align),
        offset(offset) {}

    Region(const Region& r)
        : extends(extendCopy(r.extends))
        , hstyle(r.hstyle)
        , vstyle(r.vstyle)
        , align(r.align)
        , offset(r.offset) {}


    Region() {}
    ~Region() {}

    Extend extends;
    int hstyle;
    int vstyle;
    int align;
    wxPoint offset;
};

class ImageData{
public:
    ImageData(const wxString& source):
        source(source) {}

    ImageData(const ImageData& idata)
        : source(idata.source)
        , x1(idata.x1)
        , y1(idata.y1)
        , x2(idata.x2)
        , y2(idata.y2)
        , left(idata.left)
        , right(idata.right)
        , top(idata.top)
        , bottom(idata.bottom)
        , center(idata.center) {}

    ImageData() {}
    ~ImageData() {}

    wxString source;
    int x1,y1,x2,y2;
    Region left,right,top,bottom,center;
};

class Slice{
public:
    Slice() {}
    ~Slice() {}

    wxImage image;
    int hstyle,vstyle;
    wxPoint pos,offset;
    int align;
};

class ImageCluster{
public:
    ImageCluster() {}
    ~ImageCluster() {}

    Slice *center,*left,*right,*top,*bottom;
    wxImage *c1,*c2,*c3,*c4;
};

class SplitImage4{
private:
    wxString path;
    
public:
    ImageCluster splitimage;

    wxSize Size;
    wxSize MinSize;
    
    wxString GetPath() const;

    int top, bottom, left, right;

#ifdef SPLIT_IMAGE_DEBUG
    int linen;
#endif

    float ratio[8];

    SplitImage4(const ImageData& idata);
    ~SplitImage4();

    void SetImage(const ImageData& idata);

    void Draw(wxDC* dc, const wxRect& rect, int n = 0);
    wxBitmap GetBitmap(const wxSize& size, bool center = true);
    void PreRender(wxDC* dc,const Slice& slice, const int& posx, const int& posy, const int& width, const int& height);
    void Render(wxDC* dc, const int &w, const int &h, const int& x=0, const int& y=0, const bool& center=true);

};

#endif //__SPLITIMAGE4__
