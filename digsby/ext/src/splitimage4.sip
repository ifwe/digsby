%ModuleHeaderCode
#include "wx/wx.h"
#include "splitimage4.h"
%End

long getObjectRef(wxObject* obj);

class Extend
{
public:
    Extend(bool up = false, bool down = false, bool left = false, bool right = false);
    ~Extend();

    bool up;
    bool down;
    bool left;
    bool right;
};


//Extend extendCopy(const Extend& e);

class Region /PyName=SIRegion/
{
public:
    Region(const Extend& extends, int hstyle, int vstyle, int align, wxPoint offset);
    Region(const Region& r);
    Region();

    ~Region();

    Extend extends;
    int hstyle;
    int vstyle;
    int align;
    wxPoint offset;
};


ImageData ImageDataFromSource(const wxString& source);
%MethodCode
    sipRes = new ImageData(*a0);
%End

class ImageData
{
public:
    //ImageData(const wxString& source);
    ImageData(const ImageData& idata);
    ImageData();
    ~ImageData();

    wxString source;
    int x1;
    int y1;
    int x2;
    int y2;
    Region left;
    Region right;
    Region top;
    Region bottom;
    Region center;
};

class Slice
{
public:
    Slice();
    ~Slice();

    wxImage image;
    int hstyle;
    int vstyle;
    wxPoint pos;
    wxPoint offset;
    int align;
};

class ImageCluster
{
public:
    ImageCluster();
    ~ImageCluster();

    Slice *center;
    Slice *left;
    Slice *right;
    Slice *top;
    Slice *bottom;
    wxImage *c1;
    wxImage *c2;
    wxImage *c3;
    wxImage *c4;
};

class SplitImage4 /MainThreadDestructor/
{
public:
    ImageCluster splitimage;
    wxSize Size;
    wxSize MinSize;

    wxString GetPath() const;

    int top;
    int bottom;
    int left;
    int right;

    //float ratio[8];

    SplitImage4(const ImageData& idata);
    ~SplitImage4();

    void SetImage(const ImageData& idata);

    void Draw(wxDC* dc, const wxRect& rect, int n = 0);
    wxBitmap GetBitmap(const wxSize& size, bool center = true);
    void PreRender(wxDC* dc,const Slice& slice, const int& posx, const int& posy, const int& width, const int& height);
    void Render(wxDC* dc, const int &w, const int &h, const int& x=0, const int& y=0, const bool& center=true);
};
