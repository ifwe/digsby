#include "Animation.h"
#include "EventLoop.h"
#include "Layer.h"
#include "TextLayer.h"
#include "WindowTarget.h"

#include <wx/wx.h>

#ifdef __WXMSW__
#include <wx/msw/private.h>
#endif
#include <wx/rawbmp.h>

class TestApp : public wxApp
{
    virtual bool OnInit();
};

class TestFrame : public wxFrame
{
public:

   TestFrame(const wxString& title, const wxPoint& pos, const wxSize& size);

   void OnQuit(wxCommandEvent&);
   void OnPaint(wxPaintEvent&);
   void OnAnimate(wxCommandEvent&);
   void OnPrintLayers(wxCommandEvent&);
   void OnIdle(wxIdleEvent&);
   void OnLeftDown(wxMouseEvent&);
   void OnTimer(wxTimerEvent&);

protected:
    WindowTarget* m_windowTarget;
    Layer* m_rootLayer;
    Point m_pos;

    DECLARE_EVENT_TABLE()
};

enum
{
    ID_QUIT = 1,
    ID_FirstAnimation,
    ID_Reposition,
    ID_Rotate,
    ID_FadeOut,
    ID_FadeIn,
    ID_LastAnimation,
    ID_PrintLayers,
    ID_StatusTimer
};

BEGIN_EVENT_TABLE(TestFrame, wxFrame)
    EVT_MENU(ID_QUIT, TestFrame::OnQuit)
    EVT_MENU_RANGE(ID_FirstAnimation, ID_LastAnimation, TestFrame::OnAnimate)
    EVT_MENU(ID_PrintLayers, TestFrame::OnPrintLayers)
    EVT_IDLE(TestFrame::OnIdle)
    EVT_TIMER(ID_StatusTimer, TestFrame::OnTimer)
END_EVENT_TABLE()

IMPLEMENT_APP(TestApp)

bool TestApp::OnInit()
{
    wxInitAllImageHandlers();

#ifdef __WXMSW__
    if (AllocConsole()) {
        freopen("CONOUT$", "w", stdout);
        SetConsoleTitle(wxT("Debug Console"));
        SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_RED);  
    }
#endif

    TestFrame* frame = new TestFrame(wxT("BuddyList Test"), wxPoint(50, 50), wxSize(450, 340));
    SetTopWindow(frame);
    frame->Show(true);
    return true;
}

static Bitmap AnimBitmapBroken(const wxBitmap& bmp)
{
    int width = bmp.GetWidth();
    int height = bmp.GetHeight();
    cairo_format_t format = CAIRO_FORMAT_ARGB32;
    int stride = cairo_format_stride_for_width (format, width);
    unsigned char* data = (unsigned char*)malloc(stride * height);
    printf("allocating %d bytes of data\n", stride * height);
    ZeroMemory(data, stride * height);

    printf("stride: %d\n", stride);
    cairo_surface_t* surface = cairo_image_surface_create_for_data (
        data, format, width, height, stride);

    return surface;
}

static Bitmap AnimBitmap(const wxBitmap& bmp)
{
    cairo_surface_t* surface;
    int bw = bmp.GetWidth();
    int bh = bmp.GetHeight();
    wxBitmap bmpSource = bmp;  // we need a non-const instance
    
    // Create a surface object and copy the bitmap pixel data to it.  if the
    // image has alpha (or a mask represented as alpha) then we'll use a
    // different format and iterator than if it doesn't...
    if (bmpSource.HasAlpha() || bmpSource.GetMask())
    {
        ScreenHDC screenHDC;
        surface = cairo_win32_surface_create_with_ddb(screenHDC, CAIRO_FORMAT_ARGB32, bw, bh);
        cairo_surface_t* img_surface = cairo_win32_surface_get_image(surface);
        ANIM_ASSERT(img_surface);

        unsigned char* buffer = cairo_image_surface_get_data(img_surface);
        ANIM_ASSERT(buffer);

        wxUint32* data = (wxUint32*)buffer;

        wxAlphaPixelData pixData(bmpSource, wxPoint(0,0), wxSize(bw, bh));
        ANIM_ASSERT(pixData);
        
        wxAlphaPixelData::Iterator p(pixData);
        for (int y=0; y<bh; y++)
        {
            wxAlphaPixelData::Iterator rowStart = p;
            for (int x=0; x<bw; x++)
            {
                // Each pixel in CAIRO_FORMAT_ARGB32 is a 32-bit quantity,
                // with alpha in the upper 8 bits, then red, then green, then
                // blue. The 32-bit quantities are stored native-endian.
                // Pre-multiplied alpha is used.
                unsigned char alpha = p.Alpha();
                if (alpha == 0)
                    *data = 0;
                else
                    *data = ( alpha                      << 24 
                              | (p.Red() * alpha/255)    << 16 
                              | (p.Green() * alpha/255)  <<  8 
                              | (p.Blue() * alpha/255) );
                ++data;
                ++p;
            }
            p = rowStart;
            p.OffsetY(pixData, 1);
        }        
    }
    else  // no alpha
    {
        ANIM_ASSERT(0);
        /*
        surface = cairo_image_surface_create_for_data(
            buffer, CAIRO_FORMAT_RGB24, bw, bh, bw*4);
        wxNativePixelData pixData(bmpSource, wxPoint(0,0), wxSize(bw, bh));
        ANIM_ASSERT(pixData);
        
        wxNativePixelData::Iterator p(pixData);
        for (int y=0; y<bh; y++)
        {
            wxNativePixelData::Iterator rowStart = p;
            for (int x=0; x<bw; x++)
            {
                // Each pixel in CAIRO_FORMAT_RGB24 is a 32-bit quantity, with
                // the upper 8 bits unused. Red, Green, and Blue are stored in
                // the remaining 24 bits in that order.  The 32-bit quantities
                // are stored native-endian.
                *data = ( p.Red() << 16 | p.Green() << 8 | p.Blue() );
                ++data;
                ++p;
            }
            p = rowStart;
            p.OffsetY(pixData, 1);
        }        
        */
    }

    return surface;
}

static Layer* addlayers(WindowTarget* windowTarget)
{
    /* text doesn't work ATM */
    /*
    TextLayer* textLayer = new TextLayer(wxT("digsby01"));
    printf("text layer is %x (pres is %x)\n", textLayer, textLayer->presentationLayer());
    m_rootLayer->addSublayer(textLayer);
    */

    wxBitmap bitmap(wxT("c:\\dev\\digsby\\res\\digsbybig.png"), wxBITMAP_TYPE_PNG);
    if (!bitmap.HasAlpha())
        bitmap.UseAlpha();
    ANIM_ASSERT(bitmap.Ok());

    printf("wxbitmap size: %d %d\n", bitmap.GetWidth(), bitmap.GetHeight());

    Bitmap contents = AnimBitmap(bitmap);

    Layer* root = new Layer(windowTarget);
    Layer* child = new Layer();
    root->addSublayer(child);
    child->setContents(contents);
    cairo_surface_destroy(contents);

    TextLayer* text = new TextLayer(wxT("digsby01"));
    root->addSublayer(text);

    print_layers(stdout, root);

    return root;
}

TestFrame::TestFrame(const wxString& title, const wxPoint& pos, const wxSize& size)
    : wxFrame((wxFrame*)NULL, wxID_ANY, title, pos, size, wxDEFAULT_FRAME_STYLE | wxWANTS_CHARS)
    , m_pos(10, 10)
{
    SetBackgroundStyle(wxBG_STYLE_CUSTOM);

    
    WindowTarget* windowTarget = new WindowTarget(this);
    m_windowTarget = windowTarget;
    windowTarget->Connect((wxEventType)wxEVT_LEFT_DOWN, (wxObjectEventFunction)&TestFrame::OnLeftDown, (wxObject*)0, this);

    m_rootLayer = addlayers(windowTarget);
    if (m_rootLayer)
        ;//m_rootLayer->setPosition(m_pos);

    wxMenu *menuFile = new wxMenu;
    menuFile->Append(ID_QUIT, wxT("E&xit"));

    wxMenu *menuAnimate = new wxMenu;

    menuAnimate->Append(ID_Reposition, wxT("&Position\tCtrl+P"));
    menuAnimate->Append(ID_Rotate, wxT("&Rotate\tCtrl+R"));
    menuAnimate->Append(ID_FadeOut, wxT("Fade &Out\tCtrl+O"));
    menuAnimate->Append(ID_FadeIn, wxT("Fade &In\tCtrl+I"));

    wxMenu *menuDebug = new wxMenu;
    menuDebug->Append(ID_PrintLayers, wxT("Print &Layers\tCtrl+L"));

    wxMenuBar *menuBar = new wxMenuBar;
    menuBar->Append(menuFile, wxT("&File"));
    menuBar->Append(menuAnimate, wxT("&Animate"));
    menuBar->Append(menuDebug, wxT("&Debug"));


    // update the statusbar with the cairo context's state
    SetMenuBar(menuBar);
    CreateStatusBar();
    (new wxTimer(this, ID_StatusTimer))->Start(500, false);
}

void TestFrame::OnTimer(wxTimerEvent& e)
{
    SetStatusText(m_windowTarget->lastStatus());
}

void TestFrame::OnLeftDown(wxMouseEvent& e)
{
    e.Skip();
    
    printf("%d, %d\n", e.GetPosition().x, e.GetPosition().y);
    m_rootLayer->setPosition(e.GetPosition());
}

void TestFrame::OnQuit(wxCommandEvent& e)
{
    e.Skip();
    Close();
}

void TestFrame::OnAnimate(wxCommandEvent& e)
{
    switch (e.GetId())
    {
        case ID_Reposition:
            m_rootLayer->setPosition(Point(50, 50));
            break;
        case ID_Rotate:
            break;
        case ID_FadeOut:
            m_rootLayer->setOpacity(0);
            break;
        case ID_FadeIn:
            m_rootLayer->setOpacity(1);
            break;
    }
}

void TestFrame::OnIdle(wxIdleEvent& e)
{
    processEvents();
}

void TestFrame::OnPrintLayers(wxCommandEvent&)
{
    print_layers(stdout, m_rootLayer->presentationLayer());
}

