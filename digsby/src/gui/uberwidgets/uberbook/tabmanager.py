import wx

from gui.windowfx import fadein, fadeout
from dragtimer import DragTimer,WinDragTimer
from OverlayImage import SimpleOverlayImage

from common import pref, profile
from weakref import ref

class TabManager(object):
    'This class allows transfers of tabs between notebooks.'

    def __init__(self):
        self.books=[]
        self.source=None
        self.destination=None

        self.fadeflag=True
        self.fadeobject=None
        self.dropmarker=None
        self.dragtimer=DragTimer(self)

    def Register(self,book):
        'Registers the book in the list of books.'

        self.books.append(ref(book))

    def UnRegister(self, book):
        'Removes the book from the list of books.'

        for bookref in self.books[:]:
            if bookref() is book:
                self.books.remove(bookref)

    def ReadyBook(self,currentbook,pos):
        """
        For when merging windows
        Knowing what window is being dragged figures out what window is being
        dragged into and sets up transfer
        """
        #if there is no destination or destination is not valid
        if not self.destination or not self.destination.window.Rect.Contains(pos):
            #Look through all books in the book list
            for bookref in self.books[:]:
                book = bookref()

                if book is None or wx.IsDestroyed(book):
                    self.books.remove(bookref)
                else:
                    #if not the same window that's being dragged
                    if book.window != currentbook.window:
                        rect = book.window.Rect
                        #if this is where the destination is but not set as destination yet
                        if rect.Contains(pos) and self.destination != book:
                            #Set as destination and show tabbar
                            self.destination=book
                            self.destination.tabbar.Toggle(True)
                        #if this book is the destination and is no longer valid
                        if self.destination and not rect.Contains(pos) and self.destination==book:
                            #reset variables back to normal state
                            tb = self.destination.tabbar
                            tb.Toggle()
                            tb.dragtarget=None
                            tb.dragorigin=None
                            tb.dropmarker.Show(False)
                            tb.dragside=None
                            self.destination=None
                            #reshow dragging window
                            if not self.fadeflag:
                                fadein(currentbook.window,pref('tabs.fade_speed',"normal"))
                                if currentbook.preview: currentbook.preview.Show(False)
                            self.fadeflag=True
        #if there is a destination
        if self.destination:
            barrect=self.destination.tabbar.Rect
            #if mouse is inside destination's tabbar
            if barrect.Contains(self.destination.ScreenToClient(pos)):
                #should do drag and drop stuff, showing of drop arrow
                self.destination.tabbar.DragCalc(self.destination.tabbar.ScreenToClient(pos))
                self.destination.tabbar.dragorigin=None
                #fadeout window
                if currentbook.preview: currentbook.preview.Move(wx.GetMousePosition()+(2,4))
                if self.fadeflag:
                    self.fadeobject=currentbook.window.Show(False)
                    if currentbook.preview: fadein(currentbook.preview,pref('tabs.fade_speed',"normal"),to=currentbook.preview.alpha)
                    self.fadeflag=False
                #show tabs
            #mouse is not in tabbar
            else:
                self.destination.tabbar.dropmarker.Show(False)
                #Fade in window
                if not self.fadeflag:
                    fadein(currentbook.window,pref('tabs.fade_speed',"normal"))
                    if currentbook.preview: currentbook.preview.Show(False)
                self.fadeflag=True

    def Transaction(self,currentbook):
        'Handles the moving of all the pages in one notebook to another notebook.'

        destination = self.destination
        #If there is a destination and that destination is still valid
        if destination and destination.tabbar.Rect.Contains(self.destination.ScreenToClient(wx.GetMousePosition())):
            #get a ordered list of all pages in the source notebook
            pages = [tab.page for tab in currentbook.tabbar.tabs]
            for i, page in enumerate(pages):
                destination.pagecontainer.Append(page)#addpage to destination
                destbar = destination.tabbar
                destbar.Add(page, page.tab.active, False) #create tab for page just added
                destbar.dragorigin=page.tab #set dragorigin to tab to order

                destbar.Notebook.did_add(page.panel)

                destbar.DragFinish(True) #run to do ordering

                destbar.dragtarget = page.tab#set new target to last placed tab
                destbar.dragside=1#set side to the right

            for tab in list(currentbook.tabbar.tabs):
                currentbook.tabbar.tabs.remove(tab)
                tab.Destroy()

            #fade out preview and close the source window
            if currentbook.preview: fadeout(currentbook.preview,pref('tabs.fade_speed',"normal"),currentbook.window.Close)


            self.fadeflag=True

        #if there is a destination do cleanup
        if destination:
            destination.tabbar.Toggle()
            destination.tabbar.dragtarget=None
            destination.tabbar.dragorigin=None
            destination.tabbar.dropmarker.Show(False)
            destination.tabbar.dragside=None

        self.destination=None

    def Notify(self, notebook = None):
        """
        Set the source notebook for moving a page between windows
        """
        self.source=notebook
        if self.source:
            self.dragtimer.Start(SimpleOverlayImage(notebook,self.source.tabbar.dragorigin))

    def Request(self,notebook=None):
        """
        Set the destination notebook for moving a page between windows
        """
        self.destination=notebook

    def Trigger(self):
        'Tells the source to trigger a dragfinish.'

        if self.source: self.source.tabbar.DragFinish()

    def ShowDropMarker(self, dropmarker = None):
        'Sets the new dropmarker and shows it.'

        if not dropmarker:
            if self.dropmarker and not wx.IsDestroyed(self.dropmarker):
                self.dropmarker.Show(False)
            return

        if self.dropmarker and not wx.IsDestroyed(self.dropmarker) and self.dropmarker is not dropmarker:
            self.dropmarker.Show(False)

        self.dropmarker = dropmarker
        self.dropmarker.Show(True)



class TabWindowManager(object):
    '''
    Generic tab window manager whose only argument is a callable which returns
    a new window for when tabs are dragged outside of their parents into empty
    space.
    '''

    def __init__(self, create_window_func):
        """
            Creates the window drag time and tabmanager.

            create_window_func - function used to generate new windows
        """
        self.factory = create_window_func

    def NewWindow(self, pos = wx.DefaultPosition, size = None):
        'Creates a new window with the callback function.'

        win = self.factory(pos, size)
        win.Show(False)
        fadein(win,'normal')
        return win



