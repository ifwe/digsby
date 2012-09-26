import wx
import string
import time
import struct
import oscar.ssi
import gui

class SSIViewer(wx.Frame):
    def __init__(self, o, parent, id = -1):
        print "new ssiViewer"
        self.o = o
        wx.Frame.__init__(self, parent, id, "SSIs")
        gui.toolbox.persist_window_pos(self, close_method=self.on_close)
        self.content = wx.BoxSizer(wx.VERTICAL)

        #generate new tree control
        tree_id = wx.NewId()
        self.tree = wx.TreeCtrl(self, tree_id)
        self.content.Add(self.tree,1,wx.GROW)

        #populate tree with root of tree
        rootId = self.tree.AddRoot("Root")
        #get groups (not including root group
        rootgroup = self.o.ssimanager.ssis[(0,0)]

        groups = []
        #sort groups by data in TLV 0xc8 in root gropu
        if rootgroup.tlvs and 0xc8 in rootgroup.tlvs:
            for group_id in rootgroup.tlvs[0xc8]:
                groups.append(self.o.ssimanager.ssis[(group_id,0)])
        rootMemberId = self.tree.AppendItem(rootId, rootgroup.name)
        #add tlvs to root group item (treeroot->rootitem->tlvs)
        if rootgroup.tlvs:
            for key in rootgroup.tlvs.keys():
                self.tree.AppendItem(rootMemberId, printTLV(key,rootgroup.tlvs[key]))
        #populate stuff in root (treeroot->rootitem->items)
        self.addrootgroup(rootMemberId)
        #add groups (treeroot->groups)
        for group in groups:
            groupitem_id = self.tree.AppendItem(rootId, "Name: \"" + group.name + "\" Group: 0x%04X" % group.group_id)
            #populate group (treeroot->group->items)
            self.addgroup(group,groupitem_id)

        self.SetSizer(self.content);

    def addgroup(self,group,treeId):
        ssilist = []
        if group.tlvs and 0xc8 in group.tlvs:
            for short in group.tlvs[0xc8]:
                ssilist.append(self.o.ssimanager.ssis[(group.group_id, short)])
        #add items in order (treeroot->group->items)
        for member in ssilist:
            memberId = self.tree.AppendItem(treeId, "Name: \"" + member.name + "\" "
                                            + " Item #: 0x%04X" % member.item_id)
            #populate tlvs for this item (treeroot->group->item->tlvs)
            if member.tlvs:
                for key in member.tlvs.keys():
                    self.tree.AppendItem(memberId, printTLV(key,member.tlvs[key]))

    def addrootgroup(self,treeId):
        #get the junk in the root group
        ssilist = self.o.ssimanager.get_ssis_in_group(0)
        for member in ssilist:
            member = member.clone()
            #add items (treeroot->rootitem->items)
            if member.type in oscar.ssi.buddy_types:
                type = oscar.ssi.buddy_types[member.type]
            else:
                type = "Unknown flag type 0x%04X" % member.type
            memberId = self.tree.AppendItem(treeId, "Name: \"" + member.name + "\" "
                                            + " Item #: 0x%04X" % member.item_id
                                            + " Type: " + type
                                            )
            if member.tlvs:
                #add tlvs for this item (treeroot->rootitem->item->tlvs)
                for key in member.tlvs.keys():
                    try:
                        self.tree.AppendItem(memberId, printTLV(key,member.tlvs[key]))
                    except Exception:
                        print 'couldnt add tlv to tree: %r' % ((key, member.tlvs[key]),)

    def on_close(self, e):
        self.Destroy()

def printTLV(tlvtype, tlvdata):
    import util
    tlvstring = "0x%04X" % tlvtype + ": "
    if tlvtype == 0x006D:
        (dateint,) = struct.unpack("!I", tlvdata[:4])
        tlvstring = tlvstring + '"' + time.asctime(time.localtime(dateint)) + '" + '
        tlvdata = tlvdata[4:]
    if tlvtype in (0x0067, 0x154, 0x0160, 0x01C3, 0x01C4, 0x01C5):
        (dateint,) = struct.unpack("!I", tlvdata)
        tlvstring = tlvstring + '"' + time.asctime(time.localtime(dateint)) + '"'
        tlvdata = None
    if tlvtype == 0x006E:
        pass
    if tlvtype == 0x00C8:
        for short in tlvdata:
            tlvstring += "%04X" % short + " "
        tlvstring = tlvstring[:-1]
        tlvdata = None
    if tlvtype == 0x0131:
        tlvstring += "Alias: \"" + return_printable(tlvdata)
        tlvdata = None
    if tlvtype == 0x0137:
        tlvstring += "mail: \"" + return_printable(tlvdata)
        tlvdata = None
    if tlvtype == 0x0137:
        tlvstring += "SMS: \"" + return_printable(tlvdata)
        tlvdata = None
    if tlvtype == 0x013C:
        tlvstring += "Comment: \"" + return_printable(tlvdata)
        tlvdata = None
    if tlvtype == 0x014B:
        tlvstring += "Metadata: " + repr(tlvdata)
        tlvdata = None
    if tlvtype == 0x0D5:
       pass
    if tlvdata:
        try:
            tlvstring += '"' + util.to_hex(tlvdata) + '"'
        except Exception:
#            import traceback;traceback.print_exc()
            print tlvtype, tlvdata
            raise
    return tlvstring

def return_printable(string_):
    retval = ""
    if not string_: return ''
    for char in string_:
        if char in string.printable:
            retval += char
        else:
            retval += "."
    return retval + "\""
