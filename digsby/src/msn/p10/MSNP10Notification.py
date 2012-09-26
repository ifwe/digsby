import logging
from uuid import UUID

from util import callsback
from util.primitives.funcs import get

import msn
from msn import Message
from msn.p9 import Notification as Super

log = logging.getLogger('msn.p10.ns')
defcb = dict(trid=True, callback=sentinel)


class GroupId(UUID):
    '''
    GroupIds in MSNP10 are GUIDs
    '''
    def __init__(self, id, *a, **k):

        if isinstance(id, UUID):
            id = str(id)

        try:
            UUID.__init__(self, id, *a, **k)
        except Exception, e:
            print 'error initializing contact id: ', a, k
            raise e

    def __repr__(self):
        return '<GroupId: %s>' % UUID.__repr__(self)

    def __eq__(self, other):
        return str(other) == str(self)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))

class ContactId(UUID):
    def __init__(self, *a, **k):
        try:
            UUID.__init__(self, *a, **k)
        except Exception, e:
            print 'error initializing contact id: ', a, k
            raise e

    def __repr__(self):
        return '<ContactId: %s>' % UUID.__repr__(self)

    def __eq__(self, other):
        return str(other) == str(self)

    def __ne__(self, other):
        return not self.__eq__(other)

def _rtrim_utf8url_bytes(s, maxlen):
    encode = lambda s: msn.util.url_encode(s.encode('utf-8'))

    bytes = encode(s)
    while len(bytes) > maxlen:
        s = s[:-1]
        bytes = encode(s)

    return bytes

class MSNP10Notification(Super):
    '''
    MSNP10 introduces GUIDs/CLSIDs as identifiers for buddies and groups.

    A side effect of this is that the ADD command is no longer allowed,
    being replaced by ADC. REA is also no longer allowed, in favor of
    PRP instead.
    '''
    cid_class = ContactId
    events = Super.events | set(
        ('contact_id_recv',
         )
    )

    versions = ['MSNP10']

    MAX_MFN_LENGTH = 387

    def _set_display_name(self, new_alias, callback):
        self.send_prp('MFN', _rtrim_utf8url_bytes(new_alias, self.MAX_MFN_LENGTH), callback)

    def _set_remote_alias(self, buddy, new_alias, callback):
#        assert isinstance(new_alias, unicode)
        self.send_sbp(buddy.guid, 'MFN', _rtrim_utf8url_bytes(new_alias, self.MAX_MFN_LENGTH), callback)

    def recv_syn(self, msg):
        __, __, num_buddies, num_groups = msg.args
        self.event('contact_list_details', int(num_buddies), int(num_groups))

    def recv_lsg(self, msg):
        log.debug('got lsg: %r', msg)
        # same arguments, different order
        if msg.trid:
            msg.args = [str(msg.trid),] + msg.args
            msg.trid = 0

        try:
            name, group_id = msg.args[:2]
        except ValueError, e:
            if msg.args:
                try:
                    group_id = GroupId(msg.args[0])
                except Exception, e2:
                    name = msg.args[0]
                    import uuid
                    group_id = str(uuid.uuid4())
                else:
                    name = ''
            else:
                return

        self.event('group_receive', name.decode('url').decode('fuzzy utf8'), GroupId(group_id))

    def recv_lst(self, msg):
        args = list(msg.args)

        try:
            list_flags = int(args[-1])
            groups = []
            args.pop()
        except ValueError:
            groups = map(GroupId, args[-1].split(','))
            list_flags = int(args[-2])
            args.pop()
            args.pop()

        # The next 15 lines used to be 1: "info = dict(arg.split('=', 1) for arg in args)"
        # But apparently the server can send crappy data that includes spaces where they don't belong???
        split_args = []
        for arg in args:
            split = arg.split('=', 1)
            if len(split) != 2:
                split_args[-1][-1] += (' ' + split[0])
            else:
                split_args.append(split)

        try:
            info = dict(split_args)
        except ValueError:
            # ugh forget it. this message is screwed
            log.error("This data is so screwed up, maybe you can do something with it: %r", msg)
            return

        name, nick, guid = (info.get(k,'') for k in 'NFC')
        nick = nick.decode('url').decode('fuzzy utf8')

        self._last_bname = name

        self.event('recv_contact',    name, list_flags, groups, None, guid)
        self.event('contact_alias',   name, nick)

        if guid:
            self.event('contact_id_recv', name, ContactId(guid))

    def recv_adc(self, msg):
        '''
         ADC 16 FL N=passport@hotmail.com F=Display%20Name C=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\r\n
         ADC 13 AL N=passport@hotmail.com F=Display%20Name C=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\r\n
         ADC 19 FL C=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\r\n
        '''
        l_id = msg.args[0]
        info = list(msg.args[1:])

        if l_id == 'FL':
            if '=' not in info[-1]:
                g_id = GroupId(info.pop())
            else:
                g_id = None
        else:
            g_id = None

        has_equals = lambda i: '=' in i
        d = dict(arg.split('=',1) for arg in info if has_equals(arg))
        name, nick, guid = (d.get(k,'') for k in list('NFC'))

        nick = nick.decode('url').decode('fuzzy utf8')
        list_flags = dict(FL=1, AL=2, BL=4, RL=8, PL=16)[l_id]

        if guid:
            guid = ContactId(guid)
            id = guid
        else:
            id = name

        self.event('on_contact_add',  name, id, list_flags, [g_id])

        if name and guid:
            self.event('contact_id_recv', name, guid)

        if name:
            self.event('contact_alias',   name, nick)

    def recv_rem(self, msg):
        l_id = msg.args[0]
        try:
            c_id = ContactId(msg.args[1])
        except ValueError:
            c_id = msg.args[1] # buddy name!

        g_id = get(msg.args, 2, None)

        if g_id is not None:
            g_id = GroupId(g_id)

        self.event('contact_remove', c_id, l_id, g_id)

    def recv_adg(self, msg):
        log.debug('got adg')
        name, g_id = msg.args

        name = name.decode('url').decode('fuzzy utf8')
        g_id = GroupId(g_id)

        self.event('group_add',name, g_id)

    def _remove_group(self, groupid, callback=None):
        self.send_rmg(groupid, callback=callback)

    def recv_rmg(self, msg):
        log.debug('got rmg')

        g_id, = msg.args
        g_id = GroupId(g_id)

        self.event('group_remove', g_id)

    def recv_reg(self, msg):
        log.debug('got reg')
        g_id, name = msg.args
        g_id = GroupId(g_id)
        name = name.decode('url').decode('fuzzy utf8')

        self.event('group_rename', g_id, name)

    def recv_rea(self, msg):
        raise msn.WrongVersionException

    def recv_add(self, msg):
        raise msn.WrongVersionException

    def send_syn(self):
        log.debug('sending syn')
        self.socket.send(Message('SYN', '0','0'), **defcb)

    @callsback
    def send_adc(self, l_id, bname, bid, g_id='', callback=None):
        bname = getattr(bname, 'name', bname)
        binfo = 'N=%s' % bname
        if l_id == 'FL':
            binfo += ' F=%s' % bname

        if g_id and bid:
            binfo = 'C=%s' % bid

        adc_message = Message('ADC',l_id, binfo, g_id or '')
        adc_message.retries = 5
        adc_message.timeout = 4
        self.socket.send(adc_message, trid=True, callback=callback)

    send_add = send_adc

    @callsback
    def send_rem(self, l_id, bname, bid, g_id='', callback = None):

        if l_id == 'FL':
            id = bid
        else:
            id = bname

        if g_id is None:
            g_id = ''

        if not (id or g_id):
            log.info('Didnt get an id or gid. returning from send_rem. traceback to follow...')
            import traceback;traceback.print_stack()
            callback.success()
            return

        self.socket.send(Message('REM', l_id, id, g_id), trid=True, callback=callback)

    def send_prp(self, prp_type, new_val, callback):
        self.socket.send(Message('PRP', prp_type, new_val), trid=True, callback=callback)

    def send_sbp(self, b_guid, prp_type, new_val, callback):
        self.socket.send(Message('SBP', b_guid, prp_type, new_val), trid=True, callback=callback)

    def send_rea(self, *args, **kwargs):
        raise msn.WrongVersionException

