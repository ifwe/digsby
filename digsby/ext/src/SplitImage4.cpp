#include "SplitImage4.h"
#include <stdio.h>

#if __WXMSW__
#include <windows.h>
#endif

Extend extendCopy(const Extend& e)
{
    return Extend(e.up, e.down, e.left, e.right);
}

/*
static void print_rect(const wxRect& r) {
    fprintf(stderr, "(%d, %d, %d, %d)\n", r.x, r.y, r.width, r.height);
}
*/

long getObjectRef(wxObject* obj) {
    return (long)obj->GetRefData();
}


int max(const int& val1, const int& val2){
    if(val1>val2) return val1;
    return val2;
}


SplitImage4::SplitImage4(const ImageData& idata){
    SetImage(idata);
}

//break up the image and store the pieces, also figures out any statistics it can early
void SplitImage4::SetImage(const ImageData& idata){

    // Zero out all the pointers
    splitimage.c1 = 0;
    splitimage.c2 = 0;
    splitimage.c3 = 0;
    splitimage.c4 = 0;
    splitimage.top = 0;
    splitimage.bottom = 0;
    splitimage.left = 0;
    splitimage.right = 0;
    splitimage.center = 0;

    path = idata.source;
    
    //Load the image
    wxImage image(idata.source);

    if (!image.HasAlpha())
        image.InitAlpha();

    //Get the base height and width
    const int width  = image.GetWidth() - 1;
    const int height = image.GetHeight() - 1;

    Size = wxSize(width+1, height+1);

    //Localize the cuts for adjustment
    int x1 = idata.x1;
    int x2 = idata.x2;
    int y1 = idata.y1;
    int y2 = idata.y2;

    left   =  idata.x1;
    top    =  idata.y1;
    right  = -idata.x2;
    bottom = -idata.y2;

    //Associate the cuts to (0,0)
    if (x1<0)
        x1 = width+x1+1;
    if (x2<0)
        x2 = width+x2+1;
    if (y1<0)
        y1 = height+y1+1;
    if (y2<0)
        y2 = height+y2+1;

    //Determine the minimum size based on the cut positions
    MinSize=wxSize(x1+(x2>0? width-x2 : 0),y1+(y2>0? height-y2 : 0));

    //Determine left right top and bottom edges based of center extends and cuts
    bool L = x1 && !idata.center.extends.left;
    bool R = x2 && !idata.center.extends.right;
    bool T = y1 && !idata.center.extends.up;
    bool B = y2 && !idata.center.extends.down;

    // fprintf(stderr, "Edges: %d %d %d %d\n", L, R, T, B);

    //determine if each corner exists
    bool c1 = !(L && idata.left.extends.up) && !(T && idata.top.extends.left) && (x1 && y1);
    bool c2 = !(R && idata.right.extends.up) && !(T && idata.top.extends.right) && (x2 && y1);
    bool c3 = !(L && idata.left.extends.down) && !(B && idata.bottom.extends.left) && (x1 && y2);
    bool c4 = !(R && idata.left.extends.down) && !(B && idata.top.extends.right) && (x2 && y2);

    //creates the ratio of each edge region to the minsize of the image
    ratio[0] = c1&&c2? (float)x1/(float)MinSize.GetWidth() : !c1?0:1;
    ratio[1]= 1.0-ratio[0];
    ratio[2]= c1&&c3? (float)y1/(float)MinSize.GetHeight() : !c1?0:1;
    ratio[3]= 1.0-ratio[2];

    //cut each corner and store them in the ImageCluster
    if(c1)
        splitimage.c1 = new wxImage(image.GetSubImage(wxRect(wxPoint(0,0),wxPoint(x1-1,y1-1))));
    if(c2)
        splitimage.c2 = new wxImage(image.GetSubImage(wxRect(wxPoint(x2,0),wxPoint(width,y1-1))));
    if(c3)
        splitimage.c3 = new wxImage(image.GetSubImage(wxRect(wxPoint(0,y2),wxPoint(x1-1,height))));
    if(c4)
        splitimage.c4 = new wxImage(image.GetSubImage(wxRect(wxPoint(x2,y2),wxPoint(width,height))));

    //cut each side and store them in the ImageCluster
    wxPoint pos1, pos2;

    if(T)
    {
        splitimage.top=new Slice;
        pos1 = splitimage.top->pos = c1?wxPoint(x1,0):wxPoint(0,0);
        pos2 = c2?wxPoint(x2-1,y1-1):wxPoint(width,y1-1);
        splitimage.top->image=image.GetSubImage(wxRect(pos1,pos2));
        splitimage.top->hstyle = idata.top.hstyle;
        splitimage.top->vstyle = idata.top.vstyle;
        splitimage.top->offset = idata.top.offset;
        splitimage.top->align  = idata.top.align;
    }

    if(L)
    {
        splitimage.left=new Slice;
        pos1 = splitimage.left->pos=c1?wxPoint(0,y1):wxPoint(0,0);
        pos2 = c3?wxPoint(x1-1,y2-1):wxPoint(x1,height);
        splitimage.left->image=image.GetSubImage(wxRect(pos1,pos2));
        // fprintf(stderr, "L rect: ");
        // print_rect(wxRect(pos1, pos2));
        splitimage.left->hstyle = idata.left.hstyle;
        splitimage.left->vstyle = idata.left.vstyle;
        splitimage.left->offset = idata.left.offset;
        splitimage.left->align  = idata.left.align;
    }

    if(R)
    {
        splitimage.right=new Slice;
        pos1 = splitimage.right->pos = c2?wxPoint(x2,y1):wxPoint(x2,0);
        pos2 = c4?wxPoint(width,y2-1):wxPoint(width,height);
        splitimage.right->image=image.GetSubImage(wxRect(pos1,pos2));
        splitimage.right->hstyle = idata.right.hstyle;
        splitimage.right->vstyle = idata.right.vstyle;
        splitimage.right->offset = idata.right.offset;
        splitimage.right->align  = idata.right.align;

    }

    if(B)
    {
        splitimage.bottom=new Slice;
        pos1 = splitimage.bottom->pos = c3?wxPoint(x1,y2):wxPoint(0,y2);

        pos2 = c4 ? wxPoint(x2 - 1, height) : wxPoint(width, height);
        splitimage.bottom->image = image.GetSubImage(wxRect(pos1,pos2));
        splitimage.bottom->hstyle = idata.bottom.hstyle;
        splitimage.bottom->vstyle = idata.bottom.vstyle;
        splitimage.bottom->offset = idata.bottom.offset;
        splitimage.bottom->align  = idata.bottom.align;

    }

    //The center too
    splitimage.center = new Slice;

    // fprintf(stderr, "cuts: %d %d %d %d\n", x1, y1, x2, y2);

    pos1 = splitimage.center->pos = wxPoint((L ? x1 : 0),(T ? y1 : 0));
    pos2 = wxPoint(R?x2-1:width,B?y2-1:height);
    splitimage.center->image = image.GetSubImage(wxRect(pos1,pos2));

    // fprintf(stderr, "center rect");
    // print_rect(wxRect(pos1, pos2));

    splitimage.center->hstyle = idata.center.hstyle;
    splitimage.center->vstyle = idata.center.vstyle;
    splitimage.center->offset = idata.center.offset;
    splitimage.center->align  = idata.center.align;
}

void SplitImage4::Draw(wxDC* dc, const wxRect& rect, int){
    //Just forword to Render

    //Get the width and the height for the render
    int w = rect.GetWidth()  == -1 ? Size.GetWidth()  : rect.GetWidth();
    int h = rect.GetHeight() == -1 ? Size.GetHeight() : rect.GetHeight();

    //if width or hight is less than 1 pixel abort
    if (w < 1 || h < 1)
        return;

    Render(dc, w, h, rect.x, rect.y);
}

//return bitmap
wxBitmap SplitImage4::GetBitmap(const wxSize& size, bool center){

    //Get the width and the height for the render
    int w = size.GetWidth()  == -1 ? Size.GetWidth()  : size.GetWidth();
    int h = size.GetHeight() == -1 ? Size.GetHeight() : size.GetHeight();

    //if width or hight is less than 1 pixel abort
    if (w < 1 || h < 1)
        return wxBitmap(1,1);

    wxImage image(w,h);
    if (!image.HasAlpha())
        image.InitAlpha();
    memset(image.GetAlpha(), 0, w * h);
    wxMemoryDC dc;
    wxBitmap returner(image);
    dc.SelectObject(returner);

    Render(&dc, w, h, 0, 0, center);

    dc.SelectObject(wxNullBitmap);

    return returner;
}

//Draw each piece to the DC
void SplitImage4::Render(wxDC* dc, const int &w, const int &h, const int& x, const int& y, const bool& center){

#ifdef SPLIT_IMAGE_DEBUG
    linen=0;
#endif

    // Prepping variables
    int edge, ox, oy, width, height;
    int widthl = 0, widthr = 0, heightt = 0, heightb = 0;

    // if the size of the render is less than the splitimage's minsize
    bool underw = w < MinSize.GetWidth();
    bool underh = h < MinSize.GetHeight();

    //if undersized figure out the sizes based on ratio
    if (underw)
    {
        widthl = (int)((float)w * (float)ratio[0]);
        widthr = (int)((float)w * (float)ratio[1]);
        if ( w-(widthl+widthr) )widthr += (w-(widthl+widthr));
    }

    if (underh)
    {
        heightt = (int)((float)h * (float)ratio[2]);
        heightb = (int)((float)h * (float)ratio[3]);
        if ( h-(heightt+heightb) )heightb += (h-(heightt+heightb));
    }

    // create a memory DC for the blits
    wxMemoryDC pmdc;

    // create an array of pointers to the coreners for iterating
    wxImage* c[] = {splitimage.c1, splitimage.c2, splitimage.c3, splitimage.c4};

    // stamp each corner in place if it exists
    for (int i=0; i < 4; ++i)
    {
        if (c[i])
        {
            width  = underw? (i==0||i==2? widthl:widthr) : (c[i]->GetWidth());
            height = underh? (i==0||i==1? heightt:heightb) : (c[i]->GetHeight());
            ox = i == 0 || i == 2 ? 0 : w - width;
            oy = i < 2 ? 0 : h - height;

            if (width < 1 || height < 1)
                continue;

            //dc->DrawBitmap(wxBitmap(c[i]->Scale(width,height)),ox+x,oy+y,true);
            wxBitmap bmp = wxBitmap(c[i]->Scale(width,height));
            pmdc.SelectObject(bmp);
            dc->Blit(ox+x,oy+y,width,height,&pmdc,0,0, wxCOPY, true);
        }
    }
    //calculate the position and size of each edge and the center then prerender and stamp in place
    int rwidth = 0, bheight = 0;
    if(splitimage.top/* && !underw*/)
    {
        edge= splitimage.c2? w-splitimage.c2->GetWidth() : w;
        width= edge-splitimage.top->pos.x;
        height= underh? heightt: max(1,splitimage.top->image.GetHeight());
        PreRender(dc,*splitimage.top,splitimage.top->pos.x+x,splitimage.top->pos.y+y,width,height);
    }

    if(splitimage.bottom/* && !underw*/)
    {
        edge= splitimage.c4?w-splitimage.c4->GetWidth():w;
        width= edge-splitimage.bottom->pos.x;
        bheight = height= underh? heightb: splitimage.bottom->image.GetHeight();
        PreRender(dc,*splitimage.bottom,splitimage.bottom->pos.x+x,h-height+y,width,height);
    }

    if(splitimage.left/* && !underh*/)
    {
        edge= splitimage.c3?h-splitimage.c3->GetHeight():h;
        width= underw? widthl: splitimage.left->image.GetWidth();
        height= edge-splitimage.left->pos.y;
        PreRender(dc,*splitimage.left,splitimage.left->pos.x+x,splitimage.left->pos.y+y,width,height);
    }

    if(splitimage.right/* && !underh*/)
    {
        edge= splitimage.c4?h-splitimage.c4->GetHeight():h;
        rwidth =width= underw? widthr: splitimage.right->image.GetWidth();
        height= edge-splitimage.right->pos.y;
        PreRender(dc,*splitimage.right,w-width+x,splitimage.right->pos.y+y,width,height);
    }

    if(splitimage.center && center)
    {
        width= splitimage.right?w-rwidth-splitimage.center->pos.x:w-splitimage.center->pos.x;
        height= splitimage.bottom? h-bheight-splitimage.center->pos.y : h-splitimage.center->pos.y;
        PreRender(dc,*splitimage.center,splitimage.center->pos.x+x,splitimage.center->pos.y+y,width,height);
    }

    //Release the bitmap in the memory DC
    pmdc.SelectObject(wxNullBitmap);
}

//Prerender each peice before drawing to the DC
void SplitImage4::PreRender(wxDC* dc, const Slice& slice, const int& posx, const int& posy, const int& width, const int& height){

    //Escapes if the region is undrawable
    if (width<1||height<1) return;

    //create a DC to draw from
    wxMemoryDC smdc;

    //set base sizes and position
    int iwidth = slice.image.GetWidth();
    int iheight = slice.image.GetHeight();

    //declare and init all variables used inthe math
    int xc,xb,xa,xo,yc,ya,yo,sl,st,sr,sb,x,y,w,h;
    xc=xb=xa=xo=yc=ya=yo=sl=st=sr=sb=x=y=w=h=0;

    //Find x position based off of horizontal alignment if static
    if (slice.hstyle==0){
        if (slice.align & wxALIGN_RIGHT)
            xa=width-iwidth;
        else if(slice.align & wxALIGN_CENTER_HORIZONTAL)
            xa=width/2-iwidth/2;
    }

    //Find y position based off of vertical alignment if static
    if(slice.vstyle==0){
        if (slice.align & wxALIGN_BOTTOM)
            ya=height-iheight;
        else if(slice.align & wxALIGN_CENTER_VERTICAL)
            ya=height/2-iheight/2;
    }

    //offset the x and y cursers from the alignment if static
    xc=xa + (slice.hstyle == 0? slice.offset.x : 0);
    yc=ya + (slice.vstyle == 0? slice.offset.y : 0);

    //If the canvas is off the stage to the left, reposition it at 0 and offset the origin x coord to make up for it
    if(xc<0){
        xo=-xc;
        xc=0;
        if(!(slice.align & wxALIGN_CENTER_HORIZONTAL) || slice.offset.x)
            sl=xo;
    }
    //If the canvas is off the stage to the right resizethe canvas
    if(xc+iwidth-sl>width)
        sr=xc+iwidth-width-sl;

    //If the canvas is off the stage to the top, reposition it at 0 and offset the origin y coord to make up for it
    if(yc<0){
        yo=-yc;
        yc=0;
        if(!(slice.align & wxALIGN_CENTER_VERTICAL) || slice.offset.y)
            st=yo;
    }
    //If the canvas is off the stage to the bottom resizethe canvas
    if(yc+iheight-st>height)
        sb=yc+iheight-height-st;


    //style 0 is where the actual image isn't resized
    if (slice.hstyle == 0 && slice.vstyle == 0) {

        wxBitmap stamp = wxBitmap(slice.image);


        smdc.SelectObject(stamp);

        //set position and size of canvas
        x = posx + xc;
        y = posy + yc;
        w = iwidth - sr - sl;
        h = iheight - sb - st;

        //Draw, this only hit if tiled on X axis
        dc->Blit(x, y, w, h, &smdc, xo, yo, wxCOPY, true);


    //style 2 fills the extra area with a tile of the image
    } else if (slice.hstyle == 2 || slice.vstyle == 2) {

        //create a stamp source
        wxBitmap stamp;

        //scale the image if necisary andconvert the bitmap
        if (slice.hstyle == 1)
            stamp = wxBitmap(slice.image.Scale(width,iheight,wxIMAGE_QUALITY_NORMAL));
        else if (slice.vstyle == 1)
            stamp = wxBitmap(slice.image.Scale(iwidth,height,wxIMAGE_QUALITY_NORMAL));
        else
            stamp = wxBitmap(slice.image);

        smdc.SelectObject(stamp);

        //while there's space fill the area with a tile of the image
        xb=xc;//set the xcurser base position
        while(yc<height){//tile on y axis
            while(xc<width && slice.hstyle == 2){//tile on x axis if horizantal tile

                //find position and size of canvas on stage
                x = posx + xc;
                y = posy + yc;
                w = width-xc>iwidth? iwidth : width-xc;
                if(slice.vstyle == 2)
                    h = height-yc>iheight? iheight: height-yc;
                else if(slice.vstyle == 0)
                    h = iheight - sb - st;
                else if (slice.vstyle == 1)
                    h=stamp.GetHeight();

                //Draw, only if tiled on the x axis
                dc->Blit(x, y, w, h, &smdc, xo, yo, wxCOPY, true);
                xc += iwidth;//incriment x cursor for next stamp
            }

            //If not tileing vertically escape the loop
            if (!(slice.vstyle == 2))
                break;

            //Else if not tiling horizontally, draw here
            else if(!(slice.hstyle == 2)){

                //find position and size of canvas on stage
                x = posx + xc;
                y = posy + yc;
                if(slice.hstyle==0)
                    w = iwidth - sr - sl;
                else if(slice.hstyle==1)
                    w = stamp.GetWidth();
                else if (slice.hstyle==2)
                    w = width-xb>stamp.GetWidth()? stamp.GetWidth() : width-xb;

                h = height-yc>iheight? iheight : height-yc;

                //Draw, Only if not tiles on the X axis
                dc->Blit(x, y, w, h, &smdc, xo, yo, wxCOPY, true);
            }

            xc=xb;//reset x cursor to base position for next pass
            yc += iheight;//incriment y cursor for next pass
        }


    //style 1 Scales the image to fit into the area
    } else if (slice.hstyle == 1 || slice.vstyle == 1) {

        //find scale for stamp
        w = slice.hstyle == 1? width : iwidth;
        h = slice.vstyle == 1? height : iheight;

        //scale the stamp
        wxBitmap stamp = wxBitmap(slice.image.Scale(w,h,wxIMAGE_QUALITY_NORMAL));

        //find position and size of canvas on stage
        x = slice.hstyle == 1? posx : posx + xc;
        y = slice.vstyle == 1? posy : posy + yc;
        w = slice.hstyle == 1? width : iwidth - sr - sl;
        h = slice.vstyle == 1? height : iheight - sb - st;

        smdc.SelectObject(stamp);

        //draw to canvas
        dc->Blit(x, y, w, h, &smdc, xo, yo, wxCOPY, true);
    }

    //cleanup
    smdc.SelectObject(wxNullBitmap);


#ifdef SPLIT_IMAGE_DEBUG
    //dc->SetTextForeground(wxColour(_("black")));
    wxString blarg;
    blarg<<linen;
    blarg.Append(wxT(" x: "));
    blarg<<x;
    blarg.Append(wxT(" y: "));
    blarg<<y;
    blarg.Append(wxT(" w: "));
    blarg<<w;
    blarg.Append(wxT(" h: "));
    blarg<<h;
    blarg.Append(wxT(" iwidth: "));
    blarg<<iwidth;
    blarg.Append(wxT(" iheight: "));
    blarg<<iheight;
    blarg.Append(wxT(" width: "));
    blarg<<width;
    blarg.Append(wxT(" height: "));
    blarg<<height;
    blarg.Append(wxT(" sl: "));
    blarg<<sl;
    blarg.Append(wxT(" st: "));
    blarg<<st;
    blarg.Append(wxT(" sr: "));
    blarg<<sr;
    blarg.Append(wxT(" sb: "));
    blarg<<sb;
    dc->DrawText(blarg,2,15*linen);
    blarg.Clear();
    blarg<<linen;
    dc->DrawText(blarg,posx,posy);
    ++linen;
#endif

}

wxString SplitImage4::GetPath() const
{
    return wxString(path);
}

//Cleanup
SplitImage4::~SplitImage4(void){

    if (splitimage.center)
        delete splitimage.center;
    if (splitimage.left)
        delete splitimage.left;
    if (splitimage.top)
        delete splitimage.top;
    if (splitimage.bottom)
        delete splitimage.bottom;
    if (splitimage.right)
        delete splitimage.right;

    if (splitimage.c1)
        delete splitimage.c1;
    if (splitimage.c2)
        delete splitimage.c2;
    if (splitimage.c3)
        delete splitimage.c3;
    if (splitimage.c4)
        delete splitimage.c4;
}
