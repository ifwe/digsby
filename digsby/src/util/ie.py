import collections
import logging
log = logging.getLogger('iebrowser')
#log.setLevel(logging.NOTSET)

import pythoncom
import win32com.client as com

#pythoncom.CoInitialize()

def COMEvent(f):
    def wrapper(self, *a, **k):
        ename = f.__name__
        if self.debug:
            print 'Calling %s event with args: %r, %r' % (ename, a, k)
        cancel = self._OnEvent(ename, *a, **k)
        if not cancel: f(self, *a, **k)
    return wrapper

class IEEvents(object):
    debug = False
    def __init__(self):
        self._bound = collections.defaultdict(list)

    def _OnEvent(self, e_name, *e_args, **e_kwargs):
        cbs = self._bound.get(e_name, [])
        if not cbs: return

        for cb in cbs:
            try:
                cb((e_args, e_kwargs))
            except StopIteration:
                pass

    def _Bind(self, ename, callback):
        assert callable(getattr(self, ename)), '%s is not an event of the WebBrowser or WebBrowser2 interface!' %ename
        if callback not in self._bound[ename]:
            self._bound[ename].append(callback)

    def _UnBind(self, ename, callback):
        assert callback in self._bound[ename], '%r not bound to %s' % (callback, ename)
        self._bound[ename].remove(callback)


    ##### START:webbrowser2 events #####
    @COMEvent
    def OnUpdatePageStatus(self, pDisp=sentinel, nPage=sentinel, fDone=sentinel):
        """Fired when a page is spooled. When it is fired can be changed by a custom template."""
    @COMEvent
    def OnFileDownload(self, ActiveDocument=sentinel, Cancel=sentinel):
        """Fired to indicate the File Download dialog is opening"""
    @COMEvent
    def OnDownloadComplete(self):
        """Download of page complete."""
    @COMEvent
    def OnBeforeNavigate2(self, pDisp=sentinel, URL=sentinel, Flags=sentinel,
                          TargetFrameName=sentinel, PostData=sentinel, Headers=sentinel,
                          Cancel=sentinel):
        """Fired before navigate occurs in the given WebBrowser (window or frameset element). The processing of this navigation may be modified."""
    @COMEvent
    def OnSetSecureLockIcon(self, SecureLockIcon=sentinel):
        """Fired to indicate the security level of the current web page contents"""
    @COMEvent
    def OnProgressChange(self, Progress=sentinel, ProgressMax=sentinel):
        """Fired when download progress is updated."""
    @COMEvent
    def OnNavigateError(self, pDisp=sentinel, URL=sentinel, Frame=sentinel,
                        StatusCode=sentinel, Cancel=sentinel):
        """Fired when a binding error occurs (window or frameset element)."""
    @COMEvent
    def OnCommandStateChange(self, Command=sentinel, Enable=sentinel):
        """The enabled state of a command changed."""
    @COMEvent
    def OnClientToHostWindow(self, CX=sentinel, CY=sentinel):
        """Fired to request client sizes be converted to host window sizes"""
    @COMEvent
    def OnTitleChange(self, Text=sentinel):
        """Document title changed."""
    @COMEvent
    def OnWindowSetWidth(self, Width=sentinel):
        """Fired when the host window should change its width"""
    @COMEvent
    def OnDocumentComplete(self, pDisp=sentinel, URL=sentinel):
        """Fired when the document being navigated to reaches ReadyState_Complete."""
    @COMEvent
    def OnMenuBar(self, MenuBar=sentinel):
        """Fired when the menubar should be shown/hidden"""
    @COMEvent
    def OnPrivacyImpactedStateChange(self, bImpacted=sentinel):
        """Fired when the global privacy impacted state changes"""
    @COMEvent
    def OnPropertyChange(self, szProperty=sentinel):
        """Fired when the PutProperty method has been called."""
    @COMEvent
    def OnToolBar(self, ToolBar=sentinel):
        """Fired when the toolbar  should be shown/hidden"""
    @COMEvent
    def OnTheaterMode(self, TheaterMode=sentinel):
        """Fired when theater mode should be on/off"""
    @COMEvent
    def OnWindowSetTop(self, Top=sentinel):
        """Fired when the host window should change its Top coordinate"""
    @COMEvent
    def OnStatusTextChange(self, Text=sentinel):
        """Statusbar text changed."""
    @COMEvent
    def OnWindowClosing(self, IsChildWindow=sentinel, Cancel=sentinel):
        """Fired when the WebBrowser is about to be closed by script"""
    @COMEvent
    def OnStatusBar(self, StatusBar=sentinel):
        """Fired when the statusbar should be shown/hidden"""
    @COMEvent
    def OnWindowSetResizable(self, Resizable=sentinel):
        """Fired when the host window should allow/disallow resizing"""
    @COMEvent
    def OnNewWindow2(self, ppDisp=sentinel, Cancel=sentinel):
        """A new, hidden, non-navigated WebBrowser window is needed."""
    @COMEvent
    def OnPrintTemplateTeardown(self, pDisp=sentinel):
        """Fired when a print template destroyed."""
    @COMEvent
    def OnPrintTemplateInstantiation(self, pDisp=sentinel):
        """Fired when a print template is instantiated."""
    @COMEvent
    def OnFullScreen(self, FullScreen=sentinel):
        """Fired when fullscreen mode should be on/off"""
    @COMEvent
    def OnQuit(self):
        """Fired when application is quiting."""
    @COMEvent
    def OnWindowSetLeft(self, Left=sentinel):
        """Fired when the host window should change its Left coordinate"""
    @COMEvent
    def OnWindowSetHeight(self, Height=sentinel):
        """Fired when the host window should change its height"""
    @COMEvent
    def OnNavigateComplete2(self, pDisp=sentinel, URL=sentinel):
        """Fired when the document being navigated to becomes visible and enters the
        navigation stack."""
    @COMEvent
    def OnDownloadBegin(self):
        """Download of a page started."""
    @COMEvent
    def OnVisible(self, Visible=sentinel):
        """Fired when the window should be shown/hidden"""
    #### END: webbrowser2 events ####

    #### START: webbrowser events ####
    #### Note: events overriden by webbrowser2 interface are commented out ####
    @COMEvent
    def OnNavigateComplete(self, URL=sentinel):
        """Fired when the document being navigated to becomes visible and enters the
        navigation stack."""
#    def OnQuit(self, Cancel=sentinel):
#        """Fired when application is quiting."""
    @COMEvent
    def OnFrameNavigateComplete(self, URL=sentinel):
        """Fired when a new hyperlink is being navigated to in a frame."""
#    def OnProgressChange(self, Progress=sentinel, ProgressMax=sentinel):
#        """Fired when download progress is updated."""
    @COMEvent
    def OnWindowResize(self):
        """Fired when window has been sized."""
    @COMEvent
    def OnWindowMove(self):
        """Fired when window has been moved."""
#    def OnDownloadComplete(self):
#        """Download of page complete."""
    @COMEvent
    def OnNewWindow(self, URL=sentinel, Flags=sentinel, TargetFrameName=sentinel,
                    PostData=sentinel
            , Headers=sentinel, Processed=sentinel):
        """Fired when a new window should be created."""
    @COMEvent
    def OnWindowActivate(self):
        """Fired when window has been activated."""
#    def OnStatusTextChange(self, Text=sentinel):
#        """Statusbar text changed."""
    @COMEvent
    def OnFrameBeforeNavigate(self, URL=sentinel, Flags=sentinel, TargetFrameName=sentinel,
                              PostData=sentinel
            , Headers=sentinel, Cancel=sentinel):
        """Fired when a new hyperlink is being navigated to in a frame."""
    @COMEvent
    def OnFrameNewWindow(self, URL=sentinel, Flags=sentinel, TargetFrameName=sentinel,
                         PostData=sentinel
            , Headers=sentinel, Processed=sentinel):
        """Fired when a new window should be created."""
#    def OnCommandStateChange(self, Command=sentinel, Enable=sentinel):
#        """The enabled state of a command changed"""
#    def OnDownloadBegin(self):
#        """Download of a page started."""
#    def OnTitleChange(self, Text=sentinel):
#        """Document title changed."""
    @COMEvent
    def OnBeforeNavigate(self, URL=sentinel, Flags=sentinel, TargetFrameName=sentinel,
                         PostData=sentinel
            , Headers=sentinel, Cancel=sentinel):
        """Fired when a new hyperlink is being navigated to."""
#    def OnPropertyChange(self, Property=sentinel):
#        """Fired when the PutProperty method has been called."""
    #### END: webbrowser events ####

class IEBrowser(object):
    def __init__(self, events_cls=IEEvents):
        self._ie = com.DispatchWithEvents("InternetExplorer.Application", IEEvents)
        self._evt = self._ie._obj_
        if hasattr(self._evt, '_init'):
            self._evt._init(self)

    @classmethod
    def Barebones(cls, size = None):
        '''
        Popups an IE browser without status bar, address bar, or menu bar.

        If given a size, sizes to that size and centers itself on the screen.
        '''

        import wx
        ie = IEBrowser()
        ie.AddressBar = False
        ie.MenuBar = False
        ie.StatusBar = False
        ie.ToolBar = False

        if size is not None:
            ie.Width, ie.Height = size
            w, h = wx.Display(0).ClientArea[2:]
            ie.Left,  ie.Top    = w/2 - ie.Width/2, h/2 - ie.Height/2

        return ie

    def _Bind(self, *a, **k):
        self._evt._Bind(*a,**k)

    def _UnBind(self, *a, **k):
        self._evt._UnBind(*a,**k)

    def __getattr__(self, attr):
        if attr in (self.methods + self.properties):
            return getattr(self._ie, attr)
        else:
            object.__getattribute__(self, attr)

    def __setattr__(self, attr, val):
        if attr in (self.properties):
            return setattr(self._ie, attr, val)
        else:
            return object.__setattr__(self, attr, val)

    def __bool__(self):
        try:    self._ie.Visible = self._ie.Visible
        except: return False
        else:   return True

    def show(self,show=True):
        self._ie.Visible = int(show)

    def shown(self):
        return bool(self._ie.Visible)

    def hide(self):
        self.show(False)

    def RunScript(self, js):
        return self._ie.Document.parentWindow.execScript(js, 'JavaScript')

    ##### END:EVENTS #####

    ##### START:METHODS #####
    methods = '''
    ClientToWindow
    ExecWB
    GetProperty
    GoBack
    GoForward
    GoHome
    GoSearch
    Navigate
    Navigate2
    PutProperty
    QueryStatusWB
    Quit
    Refresh
    Refresh2
    ShowBrowserBar
    Stop
    '''.split()
    ##### END:METHODS #####


    ##### START: PROPS #####
    properties = '''
    AddressBar
    Application
    Busy
    Container
    Document
    FullName
    FullScreen
    Height
    HWND
    Left
    LocationName
    LocationURL
    MenuBar
    Name
    Offline
    Parent
    Path
    ReadyState
    RegisterAsBrowser
    RegisterAsDropTarget
    Resizable
    Silent
    StatusBar
    StatusText
    TheaterMode
    ToolBar
    Top
    TopLevelContainer
    Type
    Visible
    Width
    '''.split()
    ##### END: PROPS #####

class JavaScript(str):
    _SCRIPT = 'JavaScript'
    def __new__(cls, s, ie, return_val=None):
        return str.__new__(cls, s)
    def __init__(self, s, ie, return_val=None):
        self._ie = ie
        self._ret = return_val
        str.__init__(self, s)

    def __call__(self, *args):
        self._ie.Document.parentWindow.execScript(self % args, self._SCRIPT)
        if self._ret is not None:
            return getattr(self, self._ret)

    def __getattr__(self, attr):
        try:
            return str.__getattr__(self, attr)
        except:
            return getattr(self._ie.Document.parentWindow, attr)

def JavaScriptFactory(ie):
    def make_js(s, ret_val=None):
        return JavaScript(s, ie, ret_val)
    return make_js

import atexit
#
#def IEGenerator():
#    cur = None
#    next = IEBrowser()
#    atexit.register(lambda n=next: n.Quit() if not n.Visible else None)
#    while True:
#        cur, next = next, IEBrowser()
#        atexit.register(lambda n=next: n.Quit() if not n.Visible else None)
#        yield cur
#    print 'exiting IEGenerator'
#
#iegen = IEGenerator()
#iegen.next().Quit()
#def GetIE():
#    global iegen
#    try:
#        return iegen.next()
#    except:
#        iegen = IEGenerator()
#        return iegen.next()

def GetIE():
    ie = IEBrowser()
    def quit(i=ie):
        try:
            if not i.Visible:
                i.Quit()
        except:
            pass
    atexit.register(quit)
    return ie

if __name__ == '__main__':
    ie = IEBrowser()
    ie.show(True)
    #ie.Navigate2('file://./test.html')