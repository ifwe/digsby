#include "splash.h"

#define SHOW_DELAY_MS 1000   // milliseconds to wait before showing

HBITMAP digsbyBmp;           // the Bitmap to show on the banner
HFONT   mainFont;
SIZE    digsbyBmpSize;
POINT   digsbyBmpPos;
POINT   msgPos;
HWND    hwnd;
UINT_PTR timer;

wchar_t *theMsg; //The string to show in the banner

#define ID_TIMER 1

// show delay timer callback
VOID CALLBACK TimerProc(HWND hParent, UINT uMsg, UINT uEventID, DWORD dwTimer){
    ShowWindow(hwnd, SW_SHOWNORMAL);
    KillTimer(hwnd, timer);
    timer = 0;
}


// handles the paint messages for the window
DWORD OnPaint(HWND hwnd){

    //Device Contexts
    PAINTSTRUCT paintStruct;
    HDC hDC = BeginPaint(hwnd, &paintStruct);
    
    if(digsbyBmp){
        HDC digsbyBmpDC = CreateCompatibleDC(0);
        SelectObject(digsbyBmpDC, digsbyBmp);

        // Draw Image
        BitBlt(hDC, digsbyBmpPos.x, digsbyBmpPos.y, digsbyBmpSize.cx, digsbyBmpSize.cy, digsbyBmpDC, 0, 0, SRCCOPY);
        //cleanup
        DeleteDC(digsbyBmpDC);
    }
    
    // Draw Text
    SetTextColor(hDC, COLORREF(0x00000000));
    SelectObject(hDC, mainFont);
    TextOut(hDC, msgPos.x, msgPos.y, theMsg, (int)wcslen(theMsg));

    // Cleanup
    EndPaint(hwnd, &paintStruct);
    return 0;
}

//Message handerler callback for the window
LRESULT CALLBACK WndProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam){

    switch(message){
        case WM_CREATE:
            return 0;
        case WM_CLOSE:
            return 0;
        case WM_PAINT:
            OnPaint(hwnd);
            break;
        default:
            break;
    }

    return DefWindowProc(hwnd, message, wParam, lParam);
}

//Create and show updateing banner
DWORD InitSplash(HINSTANCE hInstance, const wchar_t *imagePath, const wchar_t *msg){

    //Create global for the string so Onpaint can get to it
    theMsg = (wchar_t*)malloc(sizeof(wchar_t) * (wcslen(msg)+1));
    wcscpy(theMsg, msg);

//==Load Image Form Harddrive==================================================

    //TODO: Needs error branch
    //Load a .bmp file from the harddrive
    digsbyBmp = (HBITMAP)LoadImage(0, imagePath, IMAGE_BITMAP, 0, 0, LR_LOADFROMFILE | LR_DEFAULTCOLOR);
    

    //Get the information for the bitmap, needed for size info
    BITMAP digsbyBmpInfo;
    GetObject(digsbyBmp, sizeof(digsbyBmpInfo), &digsbyBmpInfo);


    //Sets the global size for painting and window size calculations
    digsbyBmpSize.cx = digsbyBmp? digsbyBmpInfo.bmWidth  : 0;
    digsbyBmpSize.cy = digsbyBmp? digsbyBmpInfo.bmHeight : 0;

//==Font Measurements, and window width and height========================

    int winWidth, winHeight;
    HDC screenDC = GetDC(0); //a DC is needed
    SIZE strSize;
    strSize.cx = 0;
    strSize.cy = 0;

    mainFont = (HFONT)GetStockObject(DEFAULT_GUI_FONT);
    SelectObject(screenDC, mainFont);

    //Get the measurements of the fonts from the system
    GetTextExtentPoint32(screenDC, msg, (int)wcslen(msg), &strSize);

    winWidth  = max(digsbyBmpSize.cx, strSize.cx) + 2*PADDING;
    winHeight = strSize.cy + digsbyBmpSize.cy + 3*PADDING;

    ReleaseDC(0, screenDC); //The DC is no longer needed now that the font is measured

//==Image and text positions===================================================

    //Calculate digsby image position
    digsbyBmpPos.x = winWidth/2 - digsbyBmpSize.cx/2;
    digsbyBmpPos.y = PADDING;

    //Calculate text position
    msgPos.x  = winWidth/2 - strSize.cx/2;
    msgPos.y = winHeight - strSize.cy - PADDING;

//==Window Position============================================================

    POINT pt;                   //point used to determine primary display
    MONITORINFO monInfo;        //storage to store monitor info
    HMONITOR hmon;              //handle for the monitor
    int scrWidth, scrHeight;    //screen width and height
    int winPosX, winPosY;       //position for the window

    pt.x = 1;  //point (1,1) is always on primary display
    pt.y = 1;

    //Find monitor that has point(1,1) on it
    hmon = MonitorFromPoint(pt, MONITOR_DEFAULTTOPRIMARY);

    //Get the monitor info structure to get size information
    monInfo.cbSize = sizeof(monInfo);
    GetMonitorInfo(hmon, &monInfo);

    //Get Screen width and height based off the rect in the monitor info
    scrWidth  = monInfo.rcWork.right  - monInfo.rcWork.left;
    scrHeight = monInfo.rcWork.bottom - monInfo.rcWork.top;

    //Determine center position for the window to be placed
    winPosX = scrWidth/2  - winWidth/2;
    winPosY = scrHeight/2 - winHeight/2;

//==Create Window==============================================================

    //create, setup, and register a custom class for a window
    WNDCLASSEX windowClass;
    windowClass.cbSize = sizeof(WNDCLASSEX);
    windowClass.style = CS_HREDRAW | CS_VREDRAW;                      //always do a full redraw
    windowClass.lpfnWndProc = &WndProc;                               //callback for windows messages
    windowClass.cbClsExtra = 0;
    windowClass.cbWndExtra = 0;
    windowClass.hInstance = hInstance;                                //The application instance handle
    windowClass.hIcon = LoadIcon(NULL, IDI_APPLICATION);              //Icon for Alt+Tab
    windowClass.hCursor = LoadCursor(NULL, IDC_ARROW);                //Mouse cursor
    windowClass.hbrBackground = (HBRUSH)GetStockObject(WHITE_BRUSH);  //Background brush
    windowClass.lpszMenuName = NULL;                                  //menubar
    windowClass.lpszClassName = L"DigsbyUpdateWindow";                //Classname...
    windowClass.hIconSm = LoadIcon(NULL, IDI_WINLOGO);                //icon in upper left hand corner

    //TODO: needs error branch
    //Registering the class just defined by the WNDCLASSEX struct
    RegisterClassEx(&windowClass);

    //Create window
    hwnd = CreateWindowEx(WS_EX_TOOLWINDOW,            //extended style - don't show in taskbar
                          L"DigsbyUpdateWindow",    //class name
                          L"Digsby Post Update",    //window name
                          WS_VISIBLE |
                          WS_POPUPWINDOW,           //window style
                          winPosX, winPosY,            //x/y coords
                          winWidth, winHeight,        //width,height
                          NULL,                        //handle to parent
                          NULL,                        //handle to menu
                          hInstance,                //application instance
                          NULL);                    //no extra parameters

    //if (hwnd) {
    //    // Show the window after a small delay.
    //    timer = SetTimer(hwnd, ID_TIMER, SHOW_DELAY_MS, &TimerProc);

    //    // If creating the timer failed, just show the window now.
    //    if (!timer) ShowWindow(hwnd, SW_SHOWNORMAL);
    //    
    //    
    //}

    //Manually tell window to draw
    UpdateWindow(hwnd);

    return 0;
}

//Close the window and general cleanup
void CloseSplash() {

    DestroyWindow(hwnd);
    DeleteObject(digsbyBmp);
    DeleteObject(mainFont);
    free(theMsg);
}