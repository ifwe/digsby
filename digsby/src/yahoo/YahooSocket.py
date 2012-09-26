'''
YahooSocket.py

For YMSG internals.

Pulls and pushes Yahoo packets from and to the network, using asynchat.
'''
from __future__ import with_statement
from logging import getLogger
from struct import pack
from util import to_storage, dictargcall, traceguard
from util.primitives.structures import unpack_named
from .yahooutil import YahooLoginError, format_packet, to_ydict, from_ydict, \
    from_ydict_iter, header_pack, header_size, header_desc
import common
import sys
import traceback
from . import yahoolookup as ylookup

DEFAULT_YMSG_VERSION = 17

log, loginlog = getLogger('yahoo'), getLogger('yahoo.login')

packets_log = getLogger('yahoo.packets')

class YahooConnectionBase(object):
    def __init__(self, yahoo):
        self.yahoo = yahoo                   # Reference to YahooProtocol object
        self.session_id = 0
        packets_log.debug('initializing active_gens, self.id: %d', id(self))
        self.active_gens = {}

    def handle_packet(self, header, data):
        'Handle an incoming packet.'

        self.session_id = header.session_id

        # The first possibility is that a generator is waiting on a packet
        # with the incoming command/status pair. If so, pass the packet off to
        # it.
        packets_log.debug('header %r', (header.command, header.status))
        packets_log.debug('active_gens %r', self.active_gens)
        if (header.command, header.status) in self.active_gens:
            gen = self.active_gens.pop((header.command, header.status))
            self.async_proc(gen, header, data)
            return

        # Otherwise: dynamic dispatch on the command/status....
        command_str = ylookup.commands.get(header.command, '')
        status_str = ylookup.statuses.get(header.status, '')
        target = self.yahoo


        # 1) is there a "raw" function which just wants an iterable?
        fnname = '%s_%s' % (command_str, status_str)

        with traceguard:
            packet_str = format_packet(data, sensitive = not getattr(sys, 'DEV', True))
            packets_log.debug("<== %s\n%s", fnname, packet_str)

        raw_fn = '%s_raw' % fnname

        if hasattr(target, raw_fn):
            try:
                return getattr(target, raw_fn)(self.from_ydict_iter(data))
            except Exception:
                traceback.print_exc()
            finally:
                return

        # No. Dictarg call to match yahoo dictionary keys -> argument names,
        # and call the respective function.

        if command_str and status_str:
            fn = "%s_%s" % (command_str, status_str)
            if hasattr(target, fn):
                func = getattr(target, fn)

                try:
                    return dictargcall(func, self.from_ydict(data), ylookup.ykeys)
                except Exception:
                    # Print out the exception
                    traceback.print_exc()

                    # and the function we WOULD have called.
                    print >> sys.stderr, '  File "%s", line %d, in %s' % \
                        (func.func_code.co_filename,
                         func.func_code.co_firstlineno, func.func_name)

                    return
            else:
                log.warning('no fn, %s', fn)

        # Unhandled packets get their contents dumped to the console.
        unhandled_text = ''.join([
            'unhandled packet: ',
            command_str if command_str else str(header.command),
            '_',
            status_str if status_str else str(header.status),
            '\n',
            '\n'.join('%s: %s' % (k, v) for k, v in self.from_ydict_iter(data))
            ])

        log.warning( "%s:::%r", unhandled_text, data)

    def async_proc(self, gen, header=None, data=None):
        'Processes one generator command.'

        try:
            # process a next iteration
            args = (header, data) if header else None

            # Send an incoming packet, if there is one, to the generator,
            # picking up where it left off.
            cmd, wait_on, packet = gen.send(args)

            # The generator yields a command:
            while cmd == 'send':
                self.push(packet)                 # Send a packet over the network
                cmd, wait_on, packet = gen.next() # And get the next command

            if cmd == 'wait':
                # On a wait, queue the generator and it's waiting condition.
                packets_log.debug('queueing: %r %r', wait_on, gen)
                self.active_gens[wait_on] = gen
                packets_log.debug('self.active_gens: %r', self.active_gens)

                # wait_on will be a command/status pair
                assert isinstance(wait_on, tuple)

        except StopIteration:
            # If the generator has stopped, it should definitely not be waiting
            # on a packet.
            assert gen not in self.active_gens.values()
        except YahooLoginError:
            self.yahoo.set_disconnected(self.yahoo.Reasons.BAD_PASSWORD)

    def gsend(self, command, status, data={}, **kwargs):
        """Generator send. Returns a command to async_proc to send the indicated
        packet."""

        # set a default version flag to 13
        if 'v' not in kwargs: v = DEFAULT_YMSG_VERSION
        else: v = kwargs['v']

        # lookup codes for command, status
        if isinstance(command, str): command = ylookup.commands[command]
        if isinstance(status,  str): status  = ylookup.statuses[status]

        # convert dictionary to a yahoo network dictionary
        assert isinstance(data, (dict, list))

        packet = self.make_ypacket(command, status, v, data)
        return ('send', None, packet)

    def gwait(self, command, status, err_fn):
        "Signals async_proc to wait for a specified packet type."

        command, status = ylookup.commands[command], ylookup.statuses[status]
        return ( 'wait', (command, status), err_fn )

    def make_ypacket(self, command, status, version=DEFAULT_YMSG_VERSION, data={}):
        '''
        Construct a Yahoo packet out of integers for command and status,
        an optional version number, and byte data.
        '''

        if not isinstance(command, (int, long)):
            raise TypeError("command is", command, "but should be an int!")
        if not isinstance(status, (int, long)):
            raise TypeError("status is", status, "but should be an int!")

        return self.ypacket_pack(command, status, version, data)

    def ysend(self, command, status, version=DEFAULT_YMSG_VERSION, data={}):
        assert isinstance(version, int)
        if getattr(sys, 'DEV', False):
            with traceguard:
                if isinstance(data, list):
                    group = lambda t, n: zip(*[t[i::n] for i in range(n)])
                    data_str = ''
                    for x, y in group(data, 2):
                        data_str += '    %r: %r\n' % (x, y)
                else:
                    from pprint import pformat
                    data_str = pformat(data)
                packets_log.debug("--> %s_%s\n%s", 
                    ylookup.commands.get(command),
                    ylookup.statuses.get(status),
                    data_str)
        packet = self.make_ypacket(command, status, version, data)
        self.push(packet)

class YahooSocketBase(YahooConnectionBase):
    @staticmethod
    def to_ydict(data):
        return to_ydict(data)

    @staticmethod
    def from_ydict(data):
        return from_ydict(data)

    @staticmethod
    def from_ydict_iter(data):
        return from_ydict_iter(data)

    def ypacket_pack(self, command, status, version, data):
        data = self.to_ydict(data)
        #localize the values for debugging purposes
        vars = header_pack, "YMSG", version, 0, len(data), command, status, self.session_id
        return pack(*vars) + data


class YahooSocket(YahooSocketBase, common.socket):
    def __init__(self, yahoo, server):
        common.socket.__init__(self)
        YahooSocketBase.__init__(self, yahoo)

        assert isinstance(server, tuple) and len(server) == 2
        self.server = server
        # socket is either receiving a header or receiving the rest of the data
        self.set_terminator(header_size)
        self.getting_header = True
        self.data, self.byte_count = [], 0

    def __str__(self):
        return "YahooSocket(%s:%d, %d bytes in)" % \
                (self.server[0], self.server[1], self.byte_count)

    def __repr__(self):
        return '<%s(%s:%d) - sId: %s, bytes in: %d>' % \
            (self.__class__.__name__, self.server[0], self.server[1],
             self.session_id, self.byte_count)

    #
    # async_chat handlers
    #
    # These functions occur as respones to network events.
    #

    def handle_connect(self):
        raise NotImplementedError

    def handle_close(self):
        raise NotImplementedError

    def collect_incoming_data(self, data):
        self.data.append(data)
        self.byte_count += len(data)

    def handle_error(self, *a, **k):
        traceback.print_exc()
        raise NotImplementedError

    def handle_expt(self):
        raise NotImplementedError

    def found_terminator(self):
        '''
        Invoked by asynchat when either the end of a packet header has
        been reached, or when the end of packet data has been reached.
        '''
        datastr = ''.join(self.data)

        # Flip between receive header/data...
        # either the entire header has just arrived
        if self.getting_header:
            self.getting_header = False

            self.header = to_storage(unpack_named(
                                      *(header_desc + tuple([datastr]))))
            if self.header.ymsg != 'YMSG' or self.header.size < 0:
                return log.warning('invalid packet')

            if self.header.size > 0:
                # Tell asynchat to read _size_ more bytes of data.
                self.set_terminator(self.header.size)
            else:
                # In this case, there is no data--handle the packet now.
                self.getting_header = True
                self.set_terminator(header_size)
                self.handle_packet(self.header, datastr)
                self.data = []

        # or else we just got the rest of the packet
        else:
            self.getting_header = True
            self.set_terminator(header_size)
            self.handle_packet(self.header, datastr[header_size:])
            self.data = []

    def push(self, pkt):
        #print 'sending', repr(pkt)
        super(YahooSocket, self).push(pkt)
