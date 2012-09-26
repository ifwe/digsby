from gui.prototypes.fontdropdown import FontDropDown
import wx
from wx import Size, TOP, BOTTOM, EXPAND, ALIGN_LEFT, RIGHT, LEFT, HORIZONTAL, \
    FULL_REPAINT_ON_RESIZE, BufferedPaintDC, RectS, Point
from gui import skin
from UberButton import UberButton
from simplemenu import SimpleMenu,SimpleMenuItem
from gui.uberwidgets.umenu import UMenu
from gui.toolbox import OverflowShow
from gui.uberwidgets import UberWidget
from gui.skin.skinobjects import Margins,SkinColor
from cgui import SimplePanel
from util.primitives.funcs import Delegate
wxWindow_Show = wx.Window.Show

class UberBar(SimplePanel, UberWidget):
    """
    Has at least two uses as a ButtonBar
    automatically resizes to biggest button, then resizes all other buttons to
    fit height

    will have support for other items later but not yet
    skinning will be passed
    all items in the bar should think of it as there parent

    """
    def __init__(self, parent, id = wx.ID_ANY, skinkey = None, overflowmode = False,
                 name = 'UberBar', alignment = None):

        SimplePanel.__init__(self, parent, FULL_REPAINT_ON_RESIZE)
        UberWidget.__init__(self,'toolbar')

        self.ChildPaints = Delegate()

        # Initing variables
        self.alignment = alignment if alignment and not overflowmode else ALIGN_LEFT
        self.overflowmode   = overflowmode
        self.navimode       = False
        self.active         = None
        self.children       = []
        self.staticchildren = []
        self.overflowed     = []
        self.focus          = None
        self.lastheight     = 0


        Bind = self.Bind
        Bind(wx.EVT_PAINT, self.OnBGPaint)
        Bind(wx.EVT_SIZE,  self.OnReSize)

        self.keyletters={}

        self.tlmargins = Size()
        self.brmargins = Size()

        #Start setting up an alternaitve Native Menubar for native mode

        self.SetSkinKey(skinkey,True)

        self.content = wx.BoxSizer(HORIZONTAL)
        sizer = self.Sizer = wx.GridBagSizer()
        sizer.SetEmptyCellSize(wx.Size(0, 0))

        contentFlag = TOP | BOTTOM | (self.alignment | EXPAND if self.alignment == ALIGN_LEFT else self.alignment)

        sizer.Add(self.content,(1,1),flag = contentFlag, border = self.padding.y)
        sizer.Add(Size(self.margins.left,self.margins.top),(0,0))
        sizer.Add(Size(self.margins.right,self.margins.bottom),(2,2))
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableRow(1, 1)
#

        #Set up the menu for the overflowed items if overflow mode
        if overflowmode:
            self.overflowmenu   = SimpleMenu(self,self.menuskin)
            self.overflowbutton = UberButton(self, skin=self.buttonskin,type='menu',menu=self.overflowmenu)
            self.content.Add( (self.padding.x, 1), 1, EXPAND )
            self.content.Add(self.overflowbutton,0, RIGHT | EXPAND, self.padding.x)
            self.staticchildren.append(self.overflowbutton)
        else:
            spacersizer = self.spacersizer = wx.BoxSizer(wx.HORIZONTAL)
            spacersizer.Add((self.padding.x, 1),0,EXPAND)
            self.content.Add(spacersizer, 0, EXPAND )

        self.GenWidthRestriction()

    def UpdateSkin(self):
        """
            Update local skin references
            and updates skins for buttons
        """

        key = self.skinkey
        self.native = not key
        if self.native:
            if self.uxthemeable:
                self.OpenNativeTheme()
                self.bg = None
            else:
                self.bg = SkinColor(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DFACE))

            self.padding = Point(2,2)
            self.margins = Margins([0,0,0,0])

            self.buttonskin = None
            self.menuskin   = None

        else:

            self.CloseNativeTheme()

            self.padding=skin.get(key+'.padding', Point(2,2))
            self.margins = skin.get(key+'.margins', Margins([0,0,0,0]))

            self.bg=skin.get(key+'.background',lambda: SkinColor(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DFACE)))
            self.buttonskin=skin.get(key+'.buttonskin',None)
            self.menuskin=skin.get(key+'.menuskin',None)

        s = self.Sizer
        if s:
            s.Detach(1)
            s.Detach(1)
            s.Add(Size(self.margins.left, self.margins.top), (0, 0))
            s.Add(Size(self.margins.right, self.margins.bottom), (2, 2))
            s.Children[0].SetBorder(self.padding.y)
            for child in self.content.Children:
                child.SetBorder(self.padding.x)

        for object in self.children + self.staticchildren:
            if isinstance(object, UberButton):
                object.SetSkinKey(self.buttonskin, True)
                if object.menu:
                    object.menu.SetSkinKey(self.buttonskin)

            elif isinstance(object, FontDropDown):
                object.SetSkinKey(self.buttonskin)
                object.SetMenuSkinKey(self.menuskin)

        if hasattr(self,'overflowbutton'):
            self.overflowbutton.SetSkinKey(self.buttonskin)
            self.overflowmenu.SetSkinKey(self.menuskin)

        if not self.overflowmode and hasattr(self,'content'):
            spacersizer = self.spacersizer
            spacersizer.Detach(0)
            spacersizer.Add((self.padding.x, 1), 0, EXPAND)

        wx.CallAfter(self.Layout)

    def GentAltCals(self):
        """
            This Goes through and generates the keyboard shortcuts for the
            menus in menubar mode
        """
        self.keyletters = {}
        for child in self.children:
            amp_idx = child.label.find('&')
            if isinstance(child, UberButton) and amp_idx != -1:
                self.keyletters[child.label[amp_idx + 1].upper()] = child

    def Add(self, object, expand = False, calcSize = True):
        'Add object ot end of bar.'

        return self.Insert(len(self.children), object, expand, calcSize = calcSize)

    def AddMany(self, objects, expand = False):
        for object in objects:
            self.Add(object, expand)

    def AddStatic(self,object,expand=False):
        'Add object to end of bar on right of menu in overflow mode.'

        if self.overflowmode:
            if isinstance(object, UMenu):
                object = UberButton(self, -1, object.GetTitle(), self.buttonskin,
                                    type='menu', menu=object)
            elif isinstance(object, UberButton):
                object.SetSkinKey(self.buttonskin,True)
            else:
                raise TypeError('Only buttons can be added to UberBar in overflow mode.')

            self.content.Insert(self.content.GetChildCount()-1, object, expand, RIGHT | EXPAND, self.padding.x)
            self.staticchildren.append(object)
            self.GenWidthRestriction()
        else:
            raise AssertionError('Static items are only availible in OverFlowMode')

    def AddMenuItem(self,item):
        """
            Append a SimpleMenuItem to the overflow menu
        """
        if self.overflowmode:
            self.overflowmenu.AppendItem(item)

    def AddSpacer(self):
        """
            Inserts a spacer to separate the items at the end of the current set
        """
        if not self.overflowmode:
            self.content.Add( (4*self.padding.x, 1), 1, EXPAND )
            self.GenWidthRestriction()

    def AddStretchSpacer(self, prop = 1):
        self.content.AddStretchSpacer(prop)
        self.GenWidthRestriction()

    def InsertSpacer(self,pos):
        """
            Inserts a spacer to separate the items at the pos
        """
        if not self.overflowmode:
            self.content.Insert(pos,(4*self.padding.x, 1), 1, EXPAND)
            self.GenWidthRestriction()

    def Remove(self, object, calcSize=True):
        """
        untested
        removes specified object
        """
        if object.menuitem:
            self.overflowmenu.RemoveItem(object.menuitem)

        try:
            self.overflowed.remove(object)
        except ValueError:
            pass

        self.content.Detach(object)
        self.children.remove(object)

        if calcSize:
            self.OnUBSize()


    def InsertNew(self, pos, thingy, id = -1, label = '',**args):
        """
        Inserts a new object so you don't have to create the object beforehand
        returns the id of new object
        """

        object = thingy(self, id = id, label = label, **args)

        self.Insert(pos, object)

        return id

    def Insert(self, pos, object, expand = False, calcSize = True):
        'Add object to certain position on the bar.'

        # Wrap UMenus in an UberButton
        if isinstance(object, UMenu):
            object = UberButton(self, -1, object.GetTitle(), self.buttonskin, type='menu',
                                menu = object)

        # Prepare overflow values if this is in overflow mode
        elif self.overflowmode:
            if not isinstance(object,UberButton):
                raise TypeError('Can only add buttons or menus to an UberBar in overflow mode silly!')

            object.menuitem   = None
            object.shouldshow = True
            object.Show       = OverflowShow

        # updates skins of uberbuttons
        if isinstance(object, UberButton):
            object.SetSkinKey(self.buttonskin, True)
            if object.menu:
                object.menu.SetSkinKey(self.buttonskin)
        elif isinstance(object, FontDropDown):
            object.SetSkinKey(self.buttonskin)
            object.SetMenuSkinKey(self.menuskin)

        # adds the item to content sizer and child list then updates values
        self.content.Insert(pos, object, expand, LEFT | EXPAND, self.padding.x)
        self.children.insert(pos, object)

        if calcSize:
            self.OnUBSize()

    def OnBGPaint(self,event):
        'Handles wx.EVT_ERASE_BACKGROUND.'

        dc   = wx.AutoBufferedPaintDC(self)#wx.BufferedDC(wx.ClientDC(self))

        if self.bg:
            rect = RectS(self.Size)
            self.bg.Draw(dc,rect)
        else:
            self.DrawNativeLike(dc, 0, 0, wx.RectS(self.Size))

        self.ChildPaints(dc)

#        if self.native:
#            return event.Skip()


    def OnUBSize(self,event=None):
        "Does sizing when button changes it's size."

        self.GenWidthRestriction()


    def SetAlignment(self,alignment):
        """
            Can change the alignment of the buttons in the bar, left or center...
            and maybe right?
        """
        if self.alignment != alignment:
            self.alignment = alignment
            self.Sizer.Detach(self.content)
            self.Sizer.Add(self.content, 1 if alignment == ALIGN_LEFT else 0, self.alignment)
            self.Sizer.Layout()

    def OnReSize(self, event = None):
        'Updates width restriction information on Resize of bar.'
        if event is not None:
            event.Skip()

        self.GenWidthRestriction()


        if self.Size.height != self.lastheight:
            self.lastheight = self.Size.height
            wx.CallAfter(self.Parent.Layout)

    def GenWidthRestriction(self, flushoverflow = False):
        """
            When OverFlowMode is off this calculates the minimum size of the bar
            given the minimum size of the items

            In OverFlowMode it moves items in and out of the dropdown menu
            depending on bar size
        """
        if not self.overflowmode:
            return


        children       = [child for child in self.children if child.shouldshow] #all visible children
        staticchildren = self.staticchildren #all static
        overflowed     = self.overflowed #all the children already overflowed
        omenu          = self.overflowmenu #the menu, including overflowed items

        if flushoverflow:
            for thing in overflowed[:]:

                #Remove from menu
                if thing.menuitem:
                    omenu.RemoveItem(thing.menuitem)
                    thing.menuitem = None

                #show the button
                wxWindow_Show(thing, thing.shouldshow)

                #remove from overflow list and set overflowed flag to false
                overflowed.remove(thing)
                thing.overflowed = False

                #remove sizer if it's left as the first item
                while omenu.spine.items[0].id == -1:
                    omenu.RemoveItem(0)

                self.Layout()

        if children:

            #g the rightmost, non-overflowed child
            i = len(children) - len(overflowed) - 1
            laterchild = children[i]

            #find how much space there is for the children to show between the start of the bar and the dropdown button
            cutoffpoint = self.Size.width - (sum(staticchild.Size.width for staticchild in staticchildren) + (len(staticchildren)+1)*self.padding.x)#staticchildren[0].Position.x - self.padding.x

            #while not all the children are overflowed and the rightmost child is over the cutoffpoint
            while len(children) > len(overflowed) and (laterchild.Rect.Right >= cutoffpoint):

                #if it's the first overflowed item and there are other items in the menu
                #    add a separator
                if not len(overflowed) and omenu.spine.items and not omenu.spine.items[0].id==-1:
                    omenu.Insert(0, id = -1)

                #if this item is not overflowed yet, put it in the overflowed list
                overflowed.insert(0,laterchild)

                #add the now hidden item to the menu

                # let the button optionally have a different "overflowed" label and/or action than its usual ones
                menu_title = getattr(laterchild, 'overflow_label',    laterchild.label)
                menu_cb    = getattr(laterchild, 'overflow_callback', laterchild.SendButtonEvent)

                # add the icon, if it has one
                if laterchild.icon is not None:
                    menu_title = [laterchild.icon, menu_title]

                laterchild.menuitem = SimpleMenuItem(menu_title, id=laterchild.Id, method = lambda i,  mcb = menu_cb: mcb())
                omenu.InsertItem(0, laterchild.menuitem)

                #hide the item
                wxWindow_Show(laterchild, False)

                #move to check next child left
                i = len(children) - len(overflowed) - 1
                laterchild = children[i]

            #while there's enough room to fit the next overflowed item in the bar
            while overflowed and (cutoffpoint-(0 if len(overflowed)==len(children) else laterchild.Rect.Right)>overflowed[0].Size.width+self.padding.x):
                furtherchild = overflowed[0]

                if furtherchild.menuitem:

                    #remove the menu item
                    omenu.RemoveItem(furtherchild.menuitem)

                furtherchild.menuitem = None

                #show the button
                wxWindow_Show(furtherchild, True)

                #remove from overflow list
                overflowed.remove(furtherchild)

                #choose next laterchild
                i = len(children) - len(overflowed)-1
                laterchild = children[i]

                #remove sizer if it's left as the first item
                while omenu.spine.items[0].id == -1:
                    omenu.RemoveItem(0)

        self.Layout()
        self.Top.Layout()

    def MarkFocus(self, item):
        "Set the menu's focus to said item."

        index=self.children.index(item)
        if self.focus is not None and self.focus!=index:
            self.children[self.focus].ReleaseHover()
        self.focus=index

    def UpdateItemLabel(self, id, label):
        '''Updates the button or menu item for the given id with a new label.'''

        for item in (self.FindWindowById(id, self), self.overflowmenu.FindItemById(id)):
            if item is not None:
                item.SetLabel(label)

