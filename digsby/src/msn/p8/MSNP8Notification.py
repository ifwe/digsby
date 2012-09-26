from hashlib import md5
from logging import getLogger
log = getLogger('msn.p8.ns')

import struct

import util
import util.xml_tag
from util import callsback, pythonize, myip, srv_str_to_tuple, fmt_to_dict
from util.primitives.funcs import do, get
from rfc822 import Message as RfcMsg

import msn
from msn.p import Notification as Super
from msn import Message
from util.Events import event

defcb = dict(trid=True, callback=sentinel)


class GroupId(int):
    '''
    GroupIds in MSNP8 are a number
    '''
    def __repr__(self):
        return '<GroupId: %s>' % int.__repr__(self)

    def __eq__(self, other):
        return str(other) == str(self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(int(self))

class MSNP8Notification(Super):

    events = Super.events | set((
        'on_contact_add',
        'on_auth_success',
        'on_recv_profile',
        'on_rl_notify',
        'on_blist_privacy',
        'recv_prop',
        'recv_contact',
        'recv_status',
        'recv_clientid',
        'challenge',
        'challenge_success',
        'connection_close',
        'other_user',

        'initial_mail',
        'subsequent_mail',

        'contact_list_details',

        'contact_remove',
        'contact_alias',
        'contact_offline',
        'contact_online_initial',
        'contact_online',

        'group_remove',
        'group_add',
        'group_rename',
        'group_receive',

        'ping_response',

        'switchboard_invite',
        'switchboard_request',
        'sb_request_error',

    ))

    versions = ['MSNP8']
    client_chl_id = 'msmsgs@msnmsgr.com'
    client_chl_code = 'Q1P7W2E4J9R8U3S5'

    def complete_auth(self, *tick):
        self.ticket = tick[0]

        if len(tick) is 3:
            self.tokens = tick[-1]
            tick = tick[:-1]
            log.info('Got tokens: %r', self.tokens)
        else:
            self.tokens = {}

        self.send_usr_s(*tick)


    def get_ticket(self, key=None):
        if key is None:
            return self.ticket

        else:
            return fmt_to_dict('&','=')(self.ticket)[key]


    def send_usr_s(self, *tickets):
        """
        send_usr_s(socket)

        send USeR (Subsequent) to socket to (hopefully) finish authentication
        """
        log.debug('sending usr_s')

        split = tuple(tickets[0][2:].split('&p='))

        self.cookie = 'MSPAuth=%s' % split[0]

        if split[1].strip():
            self.cookie += '; MSPProf=%s' % split[1]

        self.socket.send(Message('usr', self._auth_type, 'S', *tickets), **defcb)

    def on_auth_error(self, error):
        log.error(error)
        raise Exception(error)

    def on_complete_auth(self, msg):
        auth_type, username, mfn, verified = msg.args[:4]
        assert username == self.self_buddy.name
        self.self_buddy.remote_alias = mfn.decode('url').decode('fuzzy utf8') or None
        self.self_buddy.verified = bool(int(verified))

        Super.on_complete_auth(self, msg)

    def request_sb(self):
        if self.socket is None:
            self.recv_xfr_error(Exception('No NS socket. Request during shutdown?'))
        else:
            self.send_xfr()

    def send_xfr(self):
        self.socket.send(Message('XFR', 'SB'), trid = True, error = lambda sck,msg: self.recv_xfr_error(msg))

    def send_syn(self):
        log.debug('sending syn')
        self.socket.send(Message('SYN', '0'), **defcb)

    def recv_ver(self, msg):
        self.event('on_require_auth')

    def recv_syn(self, msg):
        log.debug('got syn')
        ver, num_buddies, num_groups = msg.args

        self.event('contact_list_details', int(num_buddies), int(num_groups))

    def recv_msg(self, msg):
        try:
            getattr(self, 'recv_msg_%s' % msg.type, self.recv_msg_unknown)(msg)
        except Exception as e:
            import traceback
            traceback.print_exc()

            log.error('Exception handling MSG: %r, msg = %r', e, msg)

    def recv_msg_unknown(self, msg):
        log.warning('Got an unknown type of MSG message: %r', msg)

    def recv_msg_profile(self, msg):
        log.debug('got msg_payload_profile')
        self.event('on_recv_profile', msg.payload)

    def recv_msg_init_email(self, msg):

        msg.contents = RfcMsg(msg.payload.body())

        inbox = int(msg.contents['Inbox-Unread'])
        other = int(msg.contents['Folders-Unread'])

        log.info('initial mail notification: %d in inbox, %d in folders',
                 inbox, other)

        self.event('initial_mail', (inbox, other))

    def recv_msg_new_email(self, msg_obj):
        log.info('Got a new mail message notification: %r', msg_obj)
        self.event('subsequent_mail', 1)

    def recv_out(self, msg):
        log.debug('got out')
        if msg.reason == 'OTH':
            self.event('other_user')
        else:
            self.event('connection_close')
            log.error('Unimplemented OUT reason: %r', msg.reason)

    def recv_gtc(self, msg):
        log.debug('got gtc')
        self.event('on_rl_notify', msg.args[0] == 'A')

    def recv_blp(self, msg):
        log.debug('got blp')

        v = msg.args[0] == 'AL'

        self.allow_unknown_contacts = v
        self.event('on_blist_privacy', v)

    def recv_lsg(self, msg):
        log.debug('got lsg')
        msg.args = (msg.trid,) + msg.args
        group_id, name = msg.args[:2]

        self.event('group_receive', name.decode('url').decode('fuzzy utf8'), GroupId(group_id))

    def recv_prp(self, msg):
        log.debug('got prp')
        type, val = msg.args
        type = pythonize(type)
        self.event('recv_prop', self._username, type, val)

    def recv_bpr(self, msg):
        log.debug('got bpr: %r', msg)
        args = list(msg.args)
        # 4 different forms:
        #
        # BPR HSB 1
        # BPR name@domain.com HSB 1
        # BPR PHM tel:+5551234567 0
        # BPR name@domain.com PHM tel:+5551234567 0
        #
        prop_or_name = args.pop(0)
        if prop_or_name.lower() in self.props:
            name = self._last_bname
            prop = prop_or_name
        else:
            name = prop_or_name
            prop = args.pop(0)

        val = args.pop(0)

        self.event('recv_prop', name, prop, val, args)

    def recv_lst(self, msg):
        """
        LST (LiST item)

        This command comes from the server after SYN, and gives you info
        about who is on your buddy list (and where).
        """
        log.debug('got lst')

        (name, nick, list_flags), groups = msg.args[:3], (msg.args[3:] or [''])[0]
        list_flags = int(list_flags)
        nick = nick.decode('url').decode('fuzzy utf8') or None

        if groups:
            groups = map(GroupId, groups.split(','))
        else:
            groups = []

        self._last_bname = name

        self.event('contact_alias', name, nick)
        self.event('recv_contact', name, list_flags, groups)

    def recv_chg(self, msg):
        log.debug('got chg')
        status = msg.args.pop(0)
        id = msg.args.pop(0)

        self.event('recv_status',   status)
        self.event('recv_clientid', self.parse_caps(id))

    def _parse_iln_nln(self, msg):
        log.debug('got iln/nln')
        (status, name, nick, client_id), __args = msg.args[:4], (msg.args[4:] or [])

        nick = nick.decode('url').decode('fuzzy utf8') or None
        client_id = self.parse_caps(client_id)

        return name, nick, status, client_id

    def parse_caps(self, caps):
        return int(caps)

    def recv_iln(self, msg):
        """
        ILN (Initial onLiNe)
        Tells us that a buddy was online before us

        NLN (oNLiNe)
        Tells us that a buddy has signed on or changed thier status.
        """

        args = self._parse_iln_nln(msg)
        self.event('contact_online_initial', *args)

    def recv_nln(self, msg):
        args = self._parse_iln_nln(msg)
        self.event('contact_online', *args)

    def recv_fln(self, msg):
        log.debug('got fln')
        name = msg.args[0]
        nick = None
        status = 'FLN'
        client_id = 0
        self.event('contact_offline', name, nick, status, client_id)

    def recv_chl(self, msg):
        log.debug('got chl')
        self.event('challenge', msg.args[0])

    def do_challenge(self, nonce):
        id   = self.client_chl_id
        code = self.client_chl_code

        self.send_qry(id, self._challenge_response(nonce, code))

    def _challenge_response(self, nonce, code):
        return md5(nonce + code).hexdigest()

    def send_qry(self, id, resp):
        log.debug('sending qry %r %r', id, resp)
        self.socket.send(Message('QRY', id, payload=resp), **defcb)

    def recv_qry(self, msg):
        '''
        yay we're still connected
        '''
        log.debug('got qry')
        self.event('challenge_success')

    def recv_add(self, msg):
        log.debug('got add')
        (l_id, ver, name, nick), g_id = msg[:4], (msg[4:] or [None])[0]

        nick = nick.decode('url').decode('fuzzy utf8') or None

        if g_id is not None:
            g_id = GroupId(g_id)

        list_flags = dict(FL=1, AL=2, BL=4, RL=8, PL=16)[l_id]

        self.event('contact_alias', name, nick)
        self.event('recv_contact', name, list_flags, [g_id])

    @event
    def on_contact_add(self, name, nick,l_id, g_id):
        return name, name, nick,l_id, g_id

    def recv_rem(self, msg):
        log.debug('got rem')
        (l_id, ver, name), g_id = msg.args[:3], get(msg, 3, None)

        if g_id is not None:
            g_id = GroupId(g_id)

        list_flags = dict(FL=1, AL=2, BL=4, RL=8, PL=16)[l_id]

        self.event('contact_remove', name, l_id, g_id)

    def recv_rmg(self, msg):
        log.debug('got rmg')
        ver, g_id = msg.args

        g_id = GroupId(g_id)
        self.event('group_remove', g_id)

    def recv_adg(self, msg):
        log.debug('got adg')
        ver, name, g_id, zero = msg.args
        name = name.decode('url').decode('fuzzy utf8')
        g_id = GroupId(g_id)

        self.event('group_add',name, g_id)

    def recv_rea(self, msg):
        log.debug('got rea')
        ver, name, nick = msg.args
        nick = nick.decode('url').decode('fuzzy utf8')

        self.event('contact_alias', name, nick)

    def recv_reg(self, msg):
        log.debug('got reg')
        ver, g_id, name, zero = msg.args
        g_id = GroupId(g_id)
        name = name.decode('url').decode('fuzzy utf8')

        self.event('group_rename', g_id, name)

    def recv_qng(self, msg):
        log.debug('got qng')
        self.event('ping_response', msg.trid)

    def recv_rng(self, msg):
        if msg.trid:
            msg.args = [msg.trid,] + msg.args
            msg.trid = 0

        session, server, auth_type, cookie, name, nick = msg.args[:6]
        server = srv_str_to_tuple(server, 1863)

        # The SB servers are mangling the encoding of names, so ignore it. If they ever fix themselves,
        # uncomment the two lines below.
        #nick = nick.decode('url').decode('fuzzy utf8')
        #self.event('contact_alias', name, nick)

        self.switchboard_invite(name, session, server, auth_type, cookie)

    @event
    def switchboard_invite(self, name, session, server, auth_type, cookie):
        return name, session, server, auth_type, cookie

    @event
    def switchboard_request(self, server, cookie):
        return server, cookie

    @event
    def sb_request_error(self, msg):
        return msg

    def send_chg(self, statuscode, client_id):
        """
        set_status(status)

        tells the Notification Server that we want to CHanGe our status to
        status. Valid statuses (stati?) are: online, busy, idle, brb, away,
        phone, lunch, and invisible(appear offline)
        """
        self.socket.send(Message('CHG', statuscode, str(client_id)), **defcb)

    def send_blp(self, new_val):
        assert new_val in ('AL','BL')
        self.socket.send(Message('BLP', new_val), **defcb)

    def send_gtc(self, new_val):
        assert new_val in 'AN'
        self.socket.send(Message('GTC', new_val), **defcb)

    def send_png(self):
        return NotImplemented

    def send_add(self, l_id, name, bid, g_id, callback):

        args = (l_id, name, name)
        if g_id is not None:
            args += (g_id,)

        self.socket.send(Message('ADD',*args), trid=True, callback=callback)

    def send_rem(self, lid, name, bid, gid, callback):
        args = (lid, name)
        if gid is not None:
            args += (gid,)

        self.socket.send(Message('REM', *args), trid=True, callback=callback)

    def send_rea(self, name, nick, callback):
        log.debug('sending rea')
        nick = msn.util.url_encode(nick.encode('utf-8'))

        if len(nick) > 128: nick = nick[:128]; log.warning('trimming nickname')
        self.socket.send(Message ('REA',name,nick), trid=True, callback=callback)

    def _add_group(self, name, callback):
        return self.send_adg(name, callback)

    def send_adg(self, name, callback):
        log.debug('sending adg')
        name = name.encode('utf-8').encode('url')

        if len(name) > 128:
            #name = name[:128];
            log.warning('name should have been trimmed')
        if len(name) > 61: log.warning('groupname too big, should get error')

        self.socket.send(Message('ADG', name, 0), trid=True, callback=callback)

    def send_rmg(self, gid, callback):
        log.debug('sending rmg')
        self.socket.send(Message('RMG', gid), trid=True, callback=callback)

    def send_reg(self, g_id, new_name, callback):
        log.debug('sending reg')
        new_name = msn.util.url_encode(new_name.encode('utf-8'))

        if len(new_name) > 128: new_name = new_name[:128]; log.warning('trimming groupname')

        self.socket.send(Message('REG', g_id, new_name, 0), trid=True, callback=callback)

    def _load_contact_list(self):
        self.send_syn()

    @callsback
    def _add_buddy(self, lid, bname, bid, gid, callback = None):
        self.send_add(lid, bname, bid, gid, callback=callback)

    @callsback
    def _add_buddy_to_list(self, bname, callback=None):
        self.send_add('FL', bname, None, None, callback=callback)

    def _add_buddy_to_group(self, bname, bid, gid, callback):
        self.send_add('FL', bname, bid, gid, callback=callback)

    @callsback
    def _remove_buddy(self, lid, buddy, group, callback=None):
        bname = getattr(buddy, 'name', buddy)
        bid = getattr(buddy,'id',None)
        self.send_rem(lid, bname, bid, group, callback=callback)

    def _remove_buddy_from_group(self, name, bid, g_id, callback):
        self.send_rem('FL',name, bid, g_id, callback=callback)

    def _authorize_buddy(self, buddy, authorize, callback):


        bname = buddy.name
        bid = buddy.id

        if authorize:
            self._add_buddy('AL', bname, bid, None)
            self._add_buddy('RL', bname, bid, None,
                            success = lambda *a: self._remove_buddy('PL', buddy, None, callback = callback),
                            error = callback.error)
        else:
            self._add_buddy('BL', bname, bid, None,
                            success = lambda *a: self._remove_buddy('PL', buddy, None, callback = callback),
                            error = callback.error)

    def _block_buddy(self, buddy, callback):
        bname = getattr(buddy, 'name', buddy)
        success = lambda sck, msg: self._remove_buddy('AL', bname, None, callback = callback)
        self._add_buddy('BL', bname, None, None, success=success, error=callback.error)


    def _unblock_buddy(self, buddy, callback):
        bname = getattr(buddy, 'name', buddy)
        success = lambda sck, msg: self._remove_buddy('BL', bname, None, callback=callback)
        self._add_buddy('AL', bname, None, None, success=success, error=callback.error)

    @callsback
    def add_to_block(self, buddy, callback=None):
        self._add_buddy('BL', buddy, None, None, callback=callback)

    @callsback
    def rem_from_block(self, buddy, callback=None):
        self._remove_buddy('BL', buddy, None, callback=callback)

    @callsback
    def add_to_allow(self, buddy, callback=None):
        self._add_buddy('AL', buddy, None, None, callback=callback)

    @callsback
    def rem_from_allow(self, buddy, callback=None):
        self._remove_buddy('AL', buddy, None, callback=callback)

    def _move_buddy(self, bname, bid, to_groupid, from_groupid, callback):
        #TODO: Implement, or move to MSNClient
        return NotImplemented

    def _set_display_name(self, new_alias, callback):
        self._set_remote_alias(self._username, new_alias, callback)

    def _set_remote_alias(self, buddy, new_alias, callback):
        if isinstance(buddy, basestring):
            name = buddy
        else:
            name = buddy.name

        if not new_alias.strip():
            new_alias = name

        self.send_rea(name, new_alias, callback)

    def _rename_group(self, group_id, name, callback):
        self.send_reg(group_id, name, callback)

    def _send_file(self, buddy, filepath, callback):
        return NotImplemented

    def _send_sms(self, phone, message, callback):
        #TODO: move to SB class?
        msgenc = message.encode('utf8') if isinstance(message, unicode) else message
        msgtag = util.xml_tag.tag('TEXT', msgenc, _ns_dict = {'xml': None}, **{'enc':'utf-8','xml:space':'preserve'})
        lcidtag = util.xml_tag.tag('LCID','1033')
        cstag = util.xml_tag.tag('CS','UTF-8')
        xml = lambda t:t._to_xml(pretty=False)

        import string
        _orig_phone = phone

        if not phone:
            return callback.error('Invalid phone number: %r' % _orig_phone)

        phone = ''.join(c for c in phone if c in string.digits)

        if not phone:
            return callback.error('Invalid phone number: %r' % _orig_phone)

        phone = 'tel:+' + phone

        msg = Message('pgd', phone, '1', payload=' '.join((xml(msgtag), xml(lcidtag), xml(cstag))))
        self.socket.send(msg, trid=True, error=self._sms_error(callback.error))
        log.info('Sent SMS. Waiting on response.')
        callback.success()

    def _sms_error(self, errorcb):
        def ohnoes(sck, e):
            errorcb(e.error_str)
        return ohnoes

    def _set_status(self, code, client_id, callback):
        self.send_chg(code, client_id)

    def _get_profile(self, buddy, callback):
        return NotImplemented
    def _set_buddy_icon(self, status, clientid, icon_data, callback):
        return NotImplemented
    def _get_buddy_icon(self, name, callback):
        return NotImplemented
    def _set_status_message(self, message, callback):
        return NotImplemented



#    def _move_buddy(self, contact, to_groupname, from_groupid, pos, callback):
#        (buddy, (bname, g_id)) = contact.buddy, contact.id
#
#        to_group = self.group_for_name(to_groupname)
#
##        if to_group is None:
##            return callback.error()
#
#        to_id = to_group.id
#
#        from_id = self.group_for_name(from_id).id
#
#        # omg teh logix!
#        #log.info('groups: %s' % self.groups)
#        if (contact in to_group):
##        if (contact in to_group or not (buddy in self.forward_list and from_id is None)):
#            callback.error()
#            return log.warning('move_buddy: could not find contact %s' % contact)
#
#        if to_id == 'Root':
#            callback.error()
#            raise msn.GeneralException("Can't move buddies to root group in MSNP8")
#
#        if from_id is not None :
#            self.remove_buddy(contact.id, from_id,
#                              success=lambda sck=None, msg=None: self.add_buddy(bname, to_id, callback=callback))
#

