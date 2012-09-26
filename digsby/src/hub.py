from __future__ import with_statement

import wx
from gui.authorizationdialog import AuthorizationDialog
from logging import getLogger
log = getLogger('hub'); info = log.info
from util.singletonmixin import Singleton
from util.primitives.error_handling import traceguard
from util.primitives.funcs import Delegate, get
from common import profile, fire, pref
from cStringIO import StringIO
from PIL import Image
import sys
from common.protocolmeta import protocols

# TODO: this class doesn't really seem like it's worth having around.
# It's sort of a controller between the protocols and the UI but
# we clearly don't use it for every place the two layers interact. We
# should either buff this class up or (more preferably) kill it off.

PROMOTE_STRING = '<br><br>I use <a href="http://www.digsby.com">digsby</a>!'

class Hub(Singleton):
    def __init__(self):
        Singleton.__init__(self)

        self._locale_obj = None
        self.getting_profile_for = None

    def signoff(self):
        'Called during signoff.'

    def filter_message(self, mobj=None, *a, **k):
        if mobj is None:
            return

        conv = mobj.conversation
        conn = conv.protocol
        buddy = mobj.buddy or mobj.conversation.buddy

        if conn.allow_message(buddy, mobj) is False: # can return None as well.
            log.debug('Message from %r is being ignored', buddy)
            log.debug_s('The message was %r', mobj)
            return Delegate.VETO

    def launchurl(self, url):
        wx.LaunchDefaultBrowser(url)

    def windowparent(self):
        wins = wx.GetTopLevelWindows()
        return wins[0] if wins else None

    def get_file(self, msg = 'Choose a file'):
        filediag = wx.FileDialog(self.windowparent(), msg)
        if filediag.ShowModal() == wx.ID_OK:
            return filediag.GetPath()

    def get_dir(self, msg = 'Choose a directory'):
        dirdiag = wx.DirDialog(self.windowparent(), msg)
        return dirdiag.GetPath() if dirdiag.ShowModal() == wx.ID_OK else None

    def on_conversation(self, convo, quiet = False):
        """
        The network has indicated that a conversation you are involved in is
        beginning.
        """

        log.critical('on_conversation is deprecated and does nothing')

    def send_message(self, buddy, message):
        buddy.protocol.send_message(buddy=buddy.name, msg=message)

    def user_message(self, message, title = ''):
        wx.CallAfter(wx.MessageBox, message, title)

    def on_error(self, e):
        import traceback
        log.error(traceback.format_exc())

        title = get(e, 'header', 'Error:')
        msg = get(e, 'major', '%s: %s'%(type(e).__name__,str(e)))
        details = get(e, 'minor', '')

        close = (_('Close'), lambda: None)

        fire('error',
             title = title, msg = msg, details = details,
             sticky = True, popupid = Exception, buttons = (close,), update = 'replace')


    def call_later(self, c, *a, **k):
        c(*a, **k)


    def on_file_request(self, protocol, xferinfo):
        'A protocol is asking you to receive a file.'

        if xferinfo not in profile.xfers:
            if pref('filetransfer.auto_accept_from_blist', default=False) and \
                    profile.blist.on_buddylist(xferinfo.buddy):
                profile.xfers.insert(0, xferinfo)
                wx.CallAfter(xferinfo.save)
            else:
                xferinfo.state = xferinfo.states.WAITING_FOR_YOU
                notifies = fire('filetransfer.request', buddy = xferinfo.buddy,
                                target = xferinfo)
                xferinfo.notifications = notifies
                profile.xfers.insert(0, xferinfo)

    def on_direct_connect(self, dc):
        caption = _('{protocolname} DirectIM').format(protocolname=dc.protocol.name.capitalize())
        msg = _("{name} wants to directly connect with you. (Your IP address will be revealed.)").format(name=dc.buddy.name)

        dc.accept() if self.popup(msg, caption) else dc.decline()

    def on_invite(self, protocol, buddy, room_name, message='',
                  on_yes = None,
                  on_no = None):
        'Someone has invited you to a chat room or conference.'

        if not pref('messaging.groupchat.enabled', False):
            log.warning('groupchat pref is off, ignoring chat invite')
            maybe_safe_call(on_no)
            return

        message = u'\n\n' + (message if message else _(u'Would you like to join?'))
        buddy_name = getattr(buddy, 'name', unicode(buddy))

        if buddy is not None:
            # an invite from a buddy.
            msg = (_(u'{name} has invited you to a group chat.').format(name=buddy_name)) + message
        else:
            # an anonymous invite. just say (mysteriously) that you have been invited
            msg = _(u'You have been invited to a group chat.') + message

        def cb(join):
            if join:
                on_yes() if on_yes is not None else protocol.join_chat_room(room_name)
            else:
                maybe_safe_call(on_no)

        res = fire('chatinvite.received', buddy=buddy, minor=msg,
                   buttons = [
                       (_('Join'), lambda *a: on_yes()),
                       (_('Ignore'), lambda *a: maybe_safe_call(on_no)),
                    ])

        @wx.CallAfter # allow popups to fire
        def after():
            if res.had_reaction('Popup'):
                return

            from gui.toolbox import SimpleMessageDialog
            protocol_name = protocol.account.protocol_info().name
            title = _('{protocol_name:s} Invite').format(protocol_name=protocol_name)
            diag = SimpleMessageDialog(None,
                title=title,
                message=msg.strip(),
                ok_caption=_('Join Chat'),
                icon = protocol.serviceicon.Resized(32),
                cancel_caption=_('Ignore Invite'),
                wrap=450)
            diag.OnTop = True
            diag.ShowWithCallback(cb)

    def authorize_buddy(self, protocol, buddy, message = "", username_added = None, callback = None):
        message = message.strip()
        if message:
            message = '\n\n"%s"' % message

        bname = getattr(buddy, 'name', None) or buddy

        if callback is None:
            callback = protocol.authorize_buddy

        if username_added is None:
            username_added = protocol.username

        if bname != protocol.self_buddy.name:
            diag_message = _(u'Allow {buddy} to add you ({you}) as a buddy on {protocol}?').format(
                buddy=bname,
                you=username_added,
                protocol=protocols[protocol.service].name)

            diag_message += message
            ad = AuthorizationDialog(protocol, buddy, diag_message, username_added, callback)
            ad.Show(True)
        else:
            callback(buddy, True, username_added)

    def on_mail(self, protocol, inbox_count, others_count=None):
        log.info('%s has %s new mail messages', protocol.username, inbox_count)
        if others_count:
            log.info('%s has %s new OTHER mail messages', protocol.username, others_count)

    def send_typing_status(self, buddy, status):
        buddy.protocol.send_typing_status(buddy.name,status)

    def set_buddy_icon(self, wximage):
        img = wximage.PIL
        w, h = img.size
        max = profile.MAX_ICON_SIZE

        # resize down to MAXSIZE if necessary.
        if w > max or h > max:
            img = img.Resized(max)

        # Save as PNG
        imgFile = StringIO()
        img.save(imgFile, 'PNG', optimize = True)

        self.set_buddy_icon_file(imgFile.getvalue())

    def set_buddy_icon_file(self, bytes):
        if hasattr(bytes, 'read'):
            bytes = bytes.read()
        if not isinstance(bytes, str): raise TypeError

        maxsz = profile.MAX_ICON_SIZE
        from digsby.abstract_blob import MAX_BLOB_SIZE as maxbytes

        nextsize = maxsz
        tries = 0
        while len(bytes) > maxbytes and tries < 10:
            log.warning("image (%dx%d) is larger than %d bytes, have to resize",
                        nextsize, nextsize, maxbytes)

            img = Image.open(StringIO(bytes)).Resized(nextsize)
            newimg = StringIO()
            img.save(newimg, 'PNG', optimize = True)
            bytes = newimg.getvalue()

            nextsize = max(20, nextsize - 10)
            tries += 1

        # Save out blob
        log.info('setting %d bytes of icon data (max is %d): %s',
                 len(bytes), maxbytes, bytes[:5])

        profile.save_blob('icon', bytes)

        for acct in profile.account_manager.connected_accounts:
            with traceguard:
                acct.connection.set_and_size_icon(bytes)

    def get_locale(self):
        # On *nix/Mac, locale.getdefaultlocale() requires LANG to be set in the
        # environment, but it appears it isn't set for app bundles, which causes this to
        # return (None, None). That in turn trips up ICQ/AIM loading. :( So use the wx
        # locale class instead, which gives us a valid result even in the app bundle case.
        # FIXME: is getfilesystemencoding() the correct encoding here?
        if not self._locale_obj:
            self._locale_obj = [wx.Locale(wx.LANGUAGE_DEFAULT).GetCanonicalName(), sys.getfilesystemencoding()]
        return self._locale_obj

    def get_lang_country(self):
        lang_country = self.get_locale()[0]
        lang,country = lang_country.split('_')

        # for things like sr_SR@latin
        # wish I knew what locale codes we were dealing with.
        # I see sr_SP and sr_SR@latin.
        # sr_SP, from python locale settings, I could not find a reference for on the internet,
        # though I didn't do much better for sr_SR.  The @latin is to differentiate from cyrillic
        # -chris
        return lang, country.lower().split('@')[0]

    def get_country(self):
        return self.get_lang_country()[1]

    country = property(get_country)

    def get_encoding(self):
        return self.get_locale()[1]

    def ProcessEvent(self, e):
        print 'ProcessEvent', e

    def get_language(self):
        return self.get_lang_country()[0]

    language = property(get_language)

    @classmethod
    def getThreadsafeInstance(cls):
        from events import ThreadsafeGUIProxy
        return ThreadsafeGUIProxy(cls.getInstance())


get_instance = Hub.getInstance

def diskspace_check(size):
    return True

def maybe_safe_call(cb):
    v = None
    if cb is not None:
        with traceguard:
            v = cb()

    return v
