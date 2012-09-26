'''
Provides a RoomList control to the IM window, and the splitter that holds the
roomlist and the message area.
'''

import wx
from util import callsback, Storage as S
from gui.toolbox import local_settings
from common import profile

ROOMLIST_MINSIZE = (110, 10)

class RoomListMixin(object):
    def toggle_roomlist(self):
        self.show_roomlist(not self.is_roomlist_shown())

        self.roomlist_has_been_shown = getattr(self, 'roomlist_has_been_shown', False) or self.is_roomlist_shown()

    def is_roomlist_constructed(self):
        return hasattr(self, 'roomlist')

    def is_roomlist_shown(self):
        return self.is_roomlist_constructed() and self.roomlist.IsShown()

    def show_roomlist(self, show):
        '''Shows or hides the roomlist.'''

        if show == self.is_roomlist_shown():
            return False

        with self.Frozen():
            multichat = self.GetButton('multichat')
            if multichat is not None and multichat.IsActive() != show:
                multichat.Active(show)

            # Hide the roomlist.
            if not show:
                self.roomlist_splitter.Unsplit(self.roomlist)
                self.FocusTextCtrl()
                return

            # Show the roomlist.
            if not hasattr(self, 'roomlist'):
                self.construct_roomlist()
                self.roomlist.SetConversation(self.convo)
                # if we try to set the sash pos higher than the roomlist minsize,
                # then it is "frozen" for the first
                #
                self.roomlist.SetMinSize(ROOMLIST_MINSIZE)

            self.roomlist_splitter.SplitVertically(self.message_area, self.roomlist)
            self._restore_roomlist_splitter()

        self.roomlist_has_been_shown = getattr(self, 'roomlist_has_been_shown', False) or show

    @callsback
    def _on_invite_buddy(self, buddy, callback=None):
        original_convo = self.convo
        protocol = original_convo.protocol

        def doinvite(convo, buddy, callback=None):
            protocol.invite_to_chat(buddy, convo, callback=callback)

        if self.convo.ischat:
            self.roomlist.model.add_pending_contact(buddy)
            return doinvite(original_convo, buddy, callback)

        def success(convo):
            self.set_conversation(convo)

        buddies_to_invite = original_convo.other_buddies
        if buddy not in buddies_to_invite:
            self.roomlist.model.add_pending_contact(buddy)
            buddies_to_invite.append(buddy)

        protocol.make_chat_and_invite(buddies_to_invite, convo=original_convo, success=success)
        return True

    def construct_roomlist(self):
        '''
        roomlist is constructed lazily
        '''

        from gui.uberwidgets.skinsplitter import SkinSplitter
        from gui.imwin.imwin_gui import MSGSPLIT_FLAGS

        sash_pos = self.input_splitter.GetSashPosition()

        # construct the splitter
        self.roomlist_splitter = SkinSplitter(self.input_splitter, MSGSPLIT_FLAGS)
        self.roomlist_splitter.SetSashGravity(1)
        self.roomlist_splitter.Bind(wx.EVT_LEFT_UP, self._save_roomlist_splitter)

        def _on_top_maximize(e):
            e.Skip()

            # HACK: maximizing the IM window sometimes makes the roomlist splitter resize really big.
            # restore the size 100ms after a maximize to fix this problem.
            wx.CallLater(100, self._restore_roomlist_splitter)

        self.Top.Bind(wx.EVT_MAXIMIZE, _on_top_maximize)

        self.message_area.Reparent(self.roomlist_splitter)

        # construct the roomlist
        from gui.imwin.roomlist import RoomListPanel
        self.roomlist = RoomListPanel(self.roomlist_splitter,
                                      inviteCallback = self._on_invite_buddy,
                                      accountCallback = lambda: S(connection=self.convo.protocol))

        self.do_input_split(self.roomlist_splitter)
        self.input_splitter.SetSashPosition(sash_pos)

    def GetSectionName(self):
        from common import profile
        username = getattr(profile, 'username', None)

        return ' '.join(["Roomlist", username])

    def _save_roomlist_splitter(self, e=None):
        if e is not None:
            e.Skip()

        profile.localprefs["roomlist_width"] = str(self.roomlist_splitter.Parent.Size.width - self.roomlist_splitter.GetSashPosition() + 3)


    def _restore_roomlist_splitter(self):
        if "roomlist_width" in profile.localprefs:
            sash_pos = self.roomlist_splitter.Parent.Size.width - int(profile.localprefs["roomlist_width"]) - 3
        else:
            sash_pos = self.roomlist_splitter.Parent.Size.width - ROOMLIST_MINSIZE[0] - 3

        self.roomlist_splitter.SetSashPosition(sash_pos)

