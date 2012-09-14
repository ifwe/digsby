import time
import logging
import traceback

import util.allow_once as once
from util import callsback, RoundRobinProducer, strip_html, Timer
from util.primitives.funcs import get
from util.Events import event

import common
from util.observe import ObservableDict
from common import Conversation, pref

from msn import NSSBAdapter, oim

from msn.MSNCommands import MSNTextMessage

log = logging.getLogger('msn.conv')

class MSNConversation(Conversation):
    MAX_MESSAGE_LENGTH = 1664
    CONNECT_TIME_LIMIT = 10

    class States:
        OFFLINE    = 'offline'    # offline
        IDLE       = 'idled'      # offline due to idle or other buddies left
        READY      = 'ready'      # ready to chat
        EMPTY      = 'empty'      # ready but no other principals
        CALLING    = 'calling'    # calling another principal (for the first time)
        CONNECTING = 'connecting' # opening socket and authenticating

    reset_allow_once = once.reset_allow_once
    _runonce_verbose = False

    def __init__(self, msn, switchboard=None, to_invite=()):
        self.client = msn
        self._to_invite = set(to_invite)

        # if inviting multiple people, make "ischat" immediately true.
        if len(self._to_invite) > 1:
            self._waschat = True

        Conversation.__init__(self, msn)
        self.protocol.register_conv(self)

        self.__prodq = []

        self._connect_cb = None

        self._type_override = None

        log.info('Added %r to msn\'s conversations list', self)

        if len(to_invite) >= 1:
            self.__chatbuddy = to_invite[0]
        else:
            self.__chatbuddy = None

        self.sb = None
        self._set_switchboard(switchboard)

        self.state = self.States.CONNECTING if self.sb else self.States.OFFLINE
        self._queued = []
        self.buddies = {}
        self.typing_status = ObservableDict()
        self.__connecting_time = 0

        self.room_list.append(self.self_buddy)

    chat_room_name = None

    def _bind_reconnect(self):
        pass # do not reconnect to MSN conferences.

    def _check_connect_time(self):
        now = time.time()
        conntime = self.__connecting_time

        if not conntime:
            if self.state == self.States.CONNECTING:
                log.info('Was in connecting but didnt have a __connecting_time set, starting over')
                self.state = self.States.OFFLINE
                self.connect()
            return

        if (now - conntime) > self.CONNECT_TIME_LIMIT:
            self._connection_error(Exception('timeout'))

    @property
    def _closed(self):
        return (not self.sb) or (self.sb._closed)

    def maybe_queue(self, f, *args, **kws):
        operation = (f, args, kws)
        if operation not in self._queued:
            self._queued.append(operation)

    @property
    def name(self):

        names = self._clean_list()
        count = len(names)
        aliases = [self.protocol.get_buddy(n).alias for n in names if n != self.self_buddy.name]
        if count == 2:
            who = aliases[0]
        elif count == 3:
            who = '%s and %s' % tuple(sorted(aliases))
        else:
            who = '%d people' % (count - 1)

        return who

    @property
    def type(self):

        if self._type_override == 'offline' and self.sb is not None:
            # we set this as an offline conversation before
            if self.buddy.online:
                # but the buddy is back online! revert back to 'fresh' conversation
                log.info('%r is online, clearing OfflineSBAdapter and resetting conversation state.', self.buddy)
                self.state = self.States.OFFLINE
                self._type_override = None
                self.Disconnect()

        if self._type_override is not None:
            # This is the ONLY way that a conversatino can become 'offline'
            return self._type_override

        try:
            if self.ischat:
                return 'chat'

            if self.buddy._btype == 'fed':
                return 'fed'

            # XXX: comment these two lines to never send mobile messages from the "IM" tab of the im window
            if self.buddy._status == 'offline' and self.buddy.mobile:
                return 'mobile'

            return 'im'

        except Exception, e:
            log.error('Got error while trying to determine type. Returning IM.')
            log.error('  Error was: %r', e)

        return 'im'

    _waschat = False

    @property
    def ischat(self):
        self._waschat = self._waschat or len(self._clean_list()) > 2
        return self._waschat

    @property
    def buddy(self):
        l = self._clean_list()

        try:
            l.remove(self.self_buddy.name)
        except ValueError:
            pass

        if len(l) == 1:
            answer = l[0]
            if isinstance(answer, basestring):
                answer = self.protocol.get_buddy(answer)
            return answer

        return self.protocol.get_buddy(self.__chatbuddy)

    def _clean_list(self):
        l = set(x.name for x in self.room_list) | set(self._to_invite)

        return list(l)

    @property
    def self_buddy(self):
        return self.protocol.self_buddy

    def _set_switchboard(self, switchboard):
        self.reset_allow_once(self._request)
        log.debug('_set_switchboard: self=%r, self.sb=%r, new switchboard=%r', self, self.sb, switchboard)

        if switchboard is None and self.sb is None:
            return

        evt_table = (
            ('on_conn_success', self.sb_connected),
            ('needs_auth',      self.provide_auth),
            ('on_authenticate', self.sb_authed),
            ('recv_action',     self.on_action_recv),
            ('recv_text_msg',   self.on_message_recv),
            ('send_text_msg',   self.on_message_send),
            ('on_buddy_join',   self.on_buddy_join),
            ('on_buddy_leave',  self.on_buddy_leave),
            ('on_buddy_timeout',self.on_buddy_timeout),
            ('typing_info',     self.on_typing_notification),
            ('disconnect',      self.exit),
            ('recv_p2p_msg',    self.on_p2p_recv),
            ('recv_error',      self.on_proto_error),
            ('transport_error', self._connection_error),
        )

        oldsb, self.sb = self.sb, switchboard

        if oldsb:
            log.info('Unbinding events from %r', oldsb)
            for evt, handler in evt_table:
                oldsb.unbind(evt, handler)
            oldsb.leave()

        self.sb = switchboard

        if self.sb:
            log.info('Binding events to %r', self.sb)
            for evt, handler in evt_table:
                self.sb.bind(evt, handler)

        elif self.state != self.States.OFFLINE:
            self.state = self.States.OFFLINE

    def provide_auth(self):
        self.sb.authenticate(self.self_buddy.name)

    def sb_connected(self, sb):
        #assert self.state == self.States.CONNECTING, self.state
        assert self.sb is sb

    def sb_authed(self):
        self.reset_allow_once('_request')
        if self.sb.principals:
            self.state = self.States.READY
            log.info('SB Authed and buddies present. Flushing queue.')
            self._flush_queue()
        else:
            self.state = self.States.EMPTY

        self.__connecting_time = 0

        log.info('Got auth event. State is now: %s', self.state)
        self._process_invites()

        if self._connect_cb is not None:
            ccb, self._connect_cb = self._connect_cb, None
            ccb.success(self)

    def _process_invites(self):
        log.info('Processing invites:')

        present_names = set(x.name for x in self.room_list)
        if self.__chatbuddy not in present_names:  # If they're not in here, they need to be invited
            self._to_invite.add(self.__chatbuddy)

        if self._to_invite:
            for contact in set(self._to_invite):
                if contact not in present_names:
                    log.info('  %r', contact)
                    self.invite(contact)
                else:
                    log.info('  %r skipped, already present', contact)
        else:
            log.info('  No one to invite.')

    def _flush_queue(self):
        self._invite_timeout = 0
        self.just_had_error = False
        q, self._queued[:] = self._queued[:], []
        while q:
            f, a, k = q.pop(0)
            log.info('Calling %s%s', f,a)
            f(*a, **k)

        log.debug('Done flushing call queue, moving on to prodq')
        self._processq()

    @callsback
    def _send_message(self, text, callback=None, **k):
        self._stop_exit_timer()
        getattr(self, '_send_message_%s' % self.type, self._send_message_im)(text, callback=callback, **k)

    def _send_message_fed(self, text, **k):
        self._send_message_im(text)

    def on_chat_connect_error(self, e=None):
        if not getattr(self, 'just_had_error', False):
            self.system_message(_('There was a network error creating a chat session.'))
            self.just_had_error = True
        self.queue_error(e)

    def _send_message_im(self, msg, callback=None, **k):

        cl = set(self._clean_list())
        cl -= set([self.self_buddy.name])
        if not cl:
            callback.error()
            self.system_message('You can\'t message yourself using MSN.')
            return

        if not self.sb:
            log.info('_send_message_im was called but there is no SB. Setting %r state to offline.', self)
            self.state = self.States.OFFLINE

        if self.state != self.States.READY:
            k.update(format=format)
            self.maybe_queue(self._send_message, msg, callback=callback, **k)

            if self.state != self.States.CALLING:
                if self.state == self.States.OFFLINE:
                    self.connect(error=self.on_chat_connect_error)
                elif self.state in (self.States.IDLE, self.States.EMPTY):
                    self._process_invites()
                else:
                    log.info('Not sending message because state is %r', self.state)
                    self._check_connect_time()
            return
        else:

            body = msg.format_as('msn')

            def check_nak(emsg):
                log.error('Error sending message: %r', emsg)
                cmd = getattr(emsg, 'cmd', None)
                if cmd == 'NAK':
                    self._send_message_im(msg, callback=callback)
                else:
                    callback.error(emsg)

            self.sb.send_text_message(body, error=check_nak)
            callback.success()

    def _send_message_mobile(self, fmsg, **k):
        self.client.send_sms(self.buddy.phone_mobile, fmsg.format_as('plaintext')),

    def _send_message_offline(self, fmsg, callback=None, **k):
        log.info('MSNConversation._send_message_offline got %r, %r', fmsg, k)
        self.sb.send_message(fmsg, callback=callback)

    @callsback
    def invite(self, name, callback=None):
        getattr(self, 'invite_%s' % self.type, self.invite_im)(name, callback=callback)

    @callsback
    def invite_im(self, name, callback=None):
        # allow passing buddies
        name = getattr(name, 'name', name)

        if name == self.self_buddy.name:
            log.info('Not inviting self_buddy, that\'s silly')
            return

        if self.state in (self.States.OFFLINE, self.States.CONNECTING):
            self.maybe_queue(self.invite, name)

        if self.state != self.States.CALLING or (self.state == self.States.CALLING and self.type == "chat"):

            if self.sb and not self.sb.connected():
                log.info('%r\'s SB socket is gone. Setting switchboard to None', self)
                self._set_switchboard(None)

            if self.state == self.States.CONNECTING:
                if self.sb is not None:
                    self._set_switchboard(None)
                self.maybe_queue(self.invite, name)
            elif self.sb is None:
                log.info('%r has no switchboard. Requesting one from %r.', self, self.protocol)
                if not self.client.request_sb(success=lambda sb: (self._set_switchboard(sb), sb.connect()),
                                              error  =self.connection_error):
                    log.info('Forcing exit because client said %r couldn\'t have a switchboard', self)
                    self.state = self.States.OFFLINE
                    self.exit(force_close = True)
                    return
            else:
                log.info('Calling invite(%s) on SB. State is now: %s', name, self.state)
                self.sb.invite(name, error=lambda sck,e: self._invite_error(name,e))

                def timeout():
                    if self.state == self.States.CALLING:
                        self._invite_error(name, 'timeout')

                wait_for = pref('msn.messaging.invite_wait_time', type=int, default=25)
                log.info('Starting timeout for invite. duration: %d seconds', wait_for)
                Timer(wait_for, timeout).start()

        if self.state in (self.States.EMPTY, self.States.IDLE):
            self.state = self.States.CALLING

    def invite_mobile(self, name):
        pass

    def _invite_error(self, name, e):
        log.info('Error inviting %r: %r', name, e)
        if (self.room_list == [self.self_buddy]) or (self.room_list == []):
            self.state = self.States.EMPTY

        if getattr(e, 'error_code', None) == 215:
            # Already in list! this means they're here already.
            log.info('Invite error indicates buddy is already in room. Assuming they\'re here and carrying on...')
            self.on_buddy_join(name)
            return

        if self.sb is not None:
            self._set_switchboard(None)

        if e == 'timeout':
            log.info('%r never responded to invite', name)
            setattr(self, '_invite_timout', getattr(self, '_invite_timeout', 0))
            if getattr(self, '_invite_timeout', 0) < common.pref('msn.messaging.max_invite_timeouts', type=int, default=3):
                # just... try again. /sigh
                log.info('Attempting invite for %r again...', name)
                return self.invite(name)

        elif e.error_code == 217: # Contact offline or self appearing invisible
            log.info('Disconnecting old switchboard- don\'t need it because buddy is offline')
            self.Disconnect()
            self._type_override = 'offline'
            # process queue now that we're offline
            log.info('%r\'s type is now: %r', self, self.type)

            self.connect() # this will call connect_offline
            self._flush_queue()
            return

        self.queue_error(e)

    @callsback
    def invite_offline(self, name, callback = None):
        log.info('Calling invite(%r) on %r', name, self.sb)
        self.sb.invite(name)
        callback.success()

    def queue_error(self, e=None):
        log.info('Message queue for %r is being cleared, calling error callbacks', self)

        ccb, self._connect_cb = self._connect_cb, None
        log.info('calling connect_cb.error: %r (error = %r)', ccb, e)

        if ccb is not None:
            ccb.error()

        old_queued, self._queued[:] = self._queued[:], []
        for (f, args, kws) in old_queued:
            cb = kws.get('callback', None)
            if cb is not None:
                try:
                    log.info('\t\tCalling %r(%r)', cb.error, e)
                    cb.error(e)
                except Exception, ex:
                    traceback.print_exc()
                    continue

    def connection_error(self, emsg=None):
        log.info('Error requesting SB server: %r', emsg)
        ecode = getattr(emsg, 'error_code', None)
        estr = getattr(emsg, 'error_str', None)
        msg = None
        if estr and ecode:
            msg = "Error(%s:%s)" % (emsg.error_code, emsg.error_str)
        elif estr:
            msg = "Error(%s)" % estr

        if msg is not None:
            self.system_message(msg)

        if ecode == 800:
            self.system_message(_("Your messages could not be sent because too many conversation sessions have been requested."))

        self._connection_error(emsg)

    def _connection_error(self, e=None):
        self.reset_allow_once('_request')
        self.state = self.States.OFFLINE
        if self.sb is not None:
            self._set_switchboard(None)
        self.queue_error(e)

    def _cleanup(self, force_close = False):
        '''
        returns true if connection should stay active
        '''

        if force_close:
            del self._queued[:]
            return False

        if self._queued:
            self.maybe_queue(self.exit)

            if self.state == self.States.READY:
                self._flush_queue()
            elif self.state in (self.States.EMPTY, self.States.IDLE):
                self._process_invites()
            elif self.state in (self.States.CALLING, self.States.CONNECTING):
                pass # _flush_queue will be called once this state is exited.
            elif self.state == self.States.OFFLINE:
                self.connect()

            return True
        else:
            return False

    @once.allow_once
    def _exit(self):
        log.info('exiting conversation')
        if self._closed:
            log.info('SB is already closed. Adding all participants into "invite" list.')
            self._to_invite.update(x.name for x in self.room_list)
            del self.room_list[:]
        else:
            self._to_invite = set()

        log.info('_to_invite is now %r (for SB = %r)', self._to_invite, self)

        self._to_invite.add(self.__chatbuddy)
        self._type_override = None

    def exit(self, force_close = False):
        is_chat = self.type == 'chat'

        more_to_send = self._cleanup(force_close)
        if more_to_send and not is_chat:
            return

        def really_exit():
            log.info('Checking if %r should "really_exit"', self)
            self._exit()

            if getattr(self, 'p2p_clients', 0) > 0 and not force_close and not is_chat:
                log.info('P2P clients still active. Not disconnecting.')
                return

            self.Disconnect()

        if force_close or is_chat:
            self._stop_exit_timer()
            really_exit()

        else:
            self._start_exit_timer(really_exit)

        Conversation.exit(self)

    def _start_exit_timer(self, f):
        log.info('Starting exit timer for %r. will call %r in %r seconds', self, f, 10)
        self._stop_exit_timer()

        self._exit_timer = Timer(10, f)
        self._exit_timer.start()

    def _stop_exit_timer(self):
        et, self._exit_timer = getattr(self, '_exit_timer', None), None
        if et is not None:
            log.info('Exit timer for %r has been stopped', self)
            et.cancel()

    @once.allow_once
    def Disconnect(self):
        self.p2p_clients = 0
        log.info('Disconnecting. unregistering %r from client (%r)', self, self.client)
        self.client.unregister_conv(self)
        p2p_manager = getattr(self.client, '_p2p_manager', None)
        if p2p_manager is not None:
            p2p_manager._unregister_transport(self)

        if get(self, 'sb', None):
            self._set_switchboard(None)
            self._to_invite = set(self._clean_list())
            self._to_invite.add(self.__chatbuddy)
            self._to_invite.discard(self.self_buddy.name)
            self.room_list[:] = []
        self.state = self.States.OFFLINE

    def on_message_send(self, msg):
        pass

    def on_message_recv(self, name, msg, sms=False):
        self._stop_exit_timer()
        buddy = self.buddies[name] = self.protocol.get_buddy(name)
        self.typing_status[buddy] = None

        if hasattr(msg, 'html'):
            message = msg.html().replace('\n', '<br />')
            content_type = 'text/html'
        else:
            message = msg
            content_type = 'text/plain'

        did_receive = self.received_message(buddy, message, sms=sms, content_type = content_type)

        if name != self.self_buddy.name and did_receive:
            Conversation.incoming_message(self)

    def on_action_recv(self, name, action_type, action_text):
        self._stop_exit_timer()

        buddy = self.buddies[name] = self.protocol.get_buddy(name)

        if action_type == 'custom':
            if action_text is not None:
                #Translators: ex: Frank nudged you!
                message = _('{name} {action}').format(name = buddy.alias, action = action_text)
                self.system_message(message)
        else:
            text = dict(
                        wink  = _('{name} winked at you!'),
                        nudge = _('{name} nudged you!'),
                        ).get(action_type, None)
            if text is not None:
                message = text.format(name = buddy.alias)
                self.system_message(message)

    def on_typing_notification(self, name, typing):
        self._stop_exit_timer()
        buddy = self.buddies[name] = self.protocol.get_buddy(name)
        self.typing_status[buddy] = 'typing' if typing else None

        log.info('%s is %styping', name, '' if typing else 'not ')

    def on_proto_error(self, errmsg):
        log.error('Unexpected protocol error from switchboard(%r): %r', self.sb, errmsg)
        self.queue_error(errmsg)

    def on_buddy_join(self, name):

        buddy = self.buddies[name] = self.protocol.get_buddy(name)
#        if not buddy.online:
#            buddy.setnotifyif('status','available')

        if buddy is not self.self_buddy and self.self_buddy not in self.room_list:
            self.on_buddy_join(self.self_buddy.name)

        if buddy not in self.room_list:
            self.room_list.append(buddy)
        if not self.__chatbuddy:
            self.__chatbuddy = name

        self.event('contacts_changed')

        if self.state not in (self.States.READY,):
            self.state = self.States.READY
            log.debug('Calling flush_queue')
            self._flush_queue()

        log.info('Got buddy join event (%s). State is now: %s. self.ischat = %r', name, self.state, self.ischat)

        self.notify('ischat')

        super(MSNConversation, self).buddy_join(buddy)

        #assert self.state in (self.States.READY, self.States.CONNECTING), self.state

    def on_buddy_leave(self, name, notify=True):
        self._type_override = None
        buddy = self.buddies[name] = self.protocol.get_buddy(name)

        try:
            self.room_list.remove(buddy)
        except ValueError:
            log.info('Buddy %r wasn\'t in room but left anyway (?)', name)

        in_room = set(self._clean_list()) - self._to_invite
        in_room.discard(self.self_buddy.name)
        if not in_room:
            # this is not really a timeout, but the desired behavior
            # is the same.
            self.on_buddy_timeout(name)
        elif in_room and name != self.self_buddy.name:
            self._to_invite.discard(name)

        self.typing_status.pop(buddy, None)
        self.event('contacts_changed')
        super(MSNConversation, self).buddy_leave(buddy)

        self.notify('ischat')

    def on_buddy_timeout(self, name):
        self._type_override = None
        buddy = self.buddies[name] = self.protocol.get_buddy(name)

        if buddy in self.room_list:
            # since this function gets called from buddy_leave, buddy
            # might have already been removed
            self.room_list.remove(buddy)

        # Since they timed out, they will be reinvited on the next action
        if name not in self._to_invite:
            self._to_invite.add(name)

        # If out chatbuddy is missing, this will be our new chatbuddy
        if self.protocol.get_buddy(self.__chatbuddy) not in self.room_list:
            self.__chatbuddy = name

        # if our roomlist is empty, our last buddy left and our session is idle
        if (self.room_list == [self.self_buddy]) or (self.room_list == []):
            self.state = self.States.IDLE
            log.info('All buddies have disconnected. _to_invite is %r. State is now: %s',
                     self._to_invite, self.state)
            log.info('Producers: %r', self.__prodq)
            log.info('Queued: %r', self._queued)
            if self._queued:
                self._process_invites()
            else:
                log.info('No invites to perform and room list is empty. Disconnecting...')
                self.Disconnect()  # So we don't break stupid WLM9beta

        self.typing_status.pop(buddy, None)
        self.event('contacts_changed')

    def zero_connect_time(self, *a):
        self.__connecting_time = 0

    @callsback
    def connect(self, callback=None):
        self._stop_exit_timer()

        if self.state == self.States.OFFLINE:
            self.reset_allow_once()
        self.__connecting_time = time.time()

        callback.success += self.zero_connect_time

        if self._connect_cb is None:
            self._connect_cb = callback
        else:
            self._connect_cb.success += callback.success
            self._connect_cb.error   += callback.error

        log.info('msnconv.connect got callback: %r', callback)
        getattr(self, 'connect_%s' % self.type, self.connect_im)()

    def connect_im(self):

        if self._closed and self.sb is not None:
            self._set_switchboard(None)

        if self.sb is None:
            if self.state == self.States.CONNECTING:
                log.warning('No SB but state was connecting')
                return
            self._request()
        elif self.state == self.States.CONNECTING:
            log.info(' got connect request but one already queued')
        else:
            log.info('Not doing anything about connection request because there\'s already a SB '
                     '(or an active request for one): sb=%r, self.state=%r', self.sb, self.state)

            if (self.room_list == [self.self_buddy]) or (self.room_list == []):
                self.state = self.States.EMPTY
                self._process_invites()
            else:
                self.state = self.States.READY
                self._flush_queue()

    def _request_connection_error(self, e = None):
        log.info('connection error for SB: %r', e)
        self.reset_allow_once('_request')

    @once.allow_once
    def _request(self):
        if self._request_connection_error not in self._connect_cb.error:
            self._connect_cb.error += self._request_connection_error

        log.info('%r Requesting SB. State was %s, changing to CONNECTING', self, self.state)
        self.state = self.States.CONNECTING
        if not self.protocol.request_sb(success=lambda s: (self._set_switchboard(s), s.connect()),
                                        error  =self.connection_error):
            self.state = self.States.OFFLINE
            self.exit(force_close=True)
            return

        wait_for = pref('msn.messaging.connect_wait_time', type=int, default=25)
        log.info('Starting timeout for connect. duration: %d seconds', wait_for)
        Timer(wait_for, self.request_timeout).start()

    def request_timeout(self):
        if self.sb is None:
            log.error('SB request for %r has timed out', self)
            self._connection_error(Exception('timeout'))
        self.reset_allow_once('_request')


    def connect_fed(self, to_invite = ()):
        if self.state in (self.States.OFFLINE, self.States.CONNECTING):
            self.state = self.States.CONNECTING
            log.info('Setting up NSSBAdapter. State is now: %s', self.state)
            sb = self.protocol.make_sb_adapter(to_invite = to_invite)
            self._set_switchboard(sb)
            sb.connect()
        else:
            log.info('Didn\'t set up NSSBAdapter- state was incorrect (%r)', self.state)

    def connect_offline(self):

        if self.sb and self.sb.connected():
            log.info('Disconnecting old switchboard before connect_offline')
            self.Disconnect()

        if self.state in (self.States.OFFLINE, self.States.CONNECTING):
            self.state = self.States.CONNECTING
            log.info('Setting up OfflineSBAdapter. State is now: %s', self.state)
            sb = oim.OfflineSBAdapter(self.client, self.buddy)
            self._type_override = 'offline'
            self._set_switchboard(sb)
            sb.connect()
            log.info('OfflineSBAdapter all set up')
        else:
            log.info('Didn\'t set up OfflineSBAdapter- state was incorrect (%r)', self.state)

    def connect_mobile(self):
        pass

    def send_typing_status(self, status):
        """
        Status can be None, 'typed' or 'typing'. But, for MSN
        only 'typing' is understood.
        """
        self._stop_exit_timer()
        getattr(self, 'send_typing_status_%s' % self.type, self.send_typing_status_im)(status)

    def send_typing_status_im(self, status):
        if not all((self.sb, getattr(self.sb, 'connected', lambda: False)())):
            self.state = self.States.OFFLINE

        if status != 'typing':
            return

        if self.state != self.States.READY:
            if self.state == self.States.OFFLINE:
                self.connect()
            elif self.state in (self.States.IDLE, self.States.EMPTY):
                self._process_invites()
            else:
                log.info('Not sending typing status because state is %r', self.state)
                self._check_connect_time()
            return

        log.info('Typing status: %s (%r)', status, self)
        self.sb.send_typing_status(self.self_buddy.name, status)

    def send_typing_status_mobile(self, status):
        pass

    def send_typing_status_offline(self, status):
        log.debug('No typing status for offline contacts')

    def on_p2p_recv(self, name, data):
        self._stop_exit_timer()
        self.event('recv_data', self, name, data)
        #self._processq()

    @callsback
    def _processq(self, callback=None):

        while self.__prodq:
            next = self.__prodq[0]
            data = next.more()
            if data is None:
                log.debug('Data was None, popping producer')
                if self.__prodq:
                    self.__prodq.pop(0)
                continue
            else:
                recip = next.recipient
                log.log(1, 'Got %d bytes of data (+%d overhead) to send to %s',
                        len(data)-self.p2p_overhead, self.p2p_overhead, recip)
                assert recip is not None
                callback.success += lambda *a, **k:self._processq()
                self.p2p_send(recip, data, callback=callback)
                return

        log.info('Producer queue is empty')

    @callsback
    def push_with_producer(self, prod, callback=None):
        self.__prodq.append(prod)
        self._processq(callback=callback)

    def fed_message(self, msg):
        bname = msg.args[0]
        if self.sb is None:
            self.connect_fed(to_invite = (bname,))
        self.sb.incoming(msg)

    def connected(self):
        return self.sb is not None and self.sb.connected()
