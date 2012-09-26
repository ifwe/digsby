import logging

import struct
import hooks

import oscar
import oscar.rendezvous as RDV

log = logging.getLogger('oscar.rdv.icqrelay')

class IcqServerRelayer(RDV.peer.OscarPeer):
    def __init__(self, protocol, screenname, cookie):
        RDV.peer.OscarPeer.__init__(self, protocol, screenname, cookie, oscar.capabilities.by_name['extended_msgs'])

    def handle_request(self, reqtlvs):
        log.info("request: %r", reqtlvs)

        data = reqtlvs.extended_data

        fmt = ( ('length1', 'H'),
                ('chunk1',  's',   'length1'),
                ('length2', 'H'),
                ('chunk2',  's',   'length2')
        )

        # chunk1 and 2 don't seem to have any useful information.
        # XXX: Not sure if the number of chunks is always the same or not
        _, chunk1, _, chunk2, data = oscar.unpack(fmt, data, byte_order='<')

        fmt = ( ('type',     'B'),
                ('flags',    'B'),
                ('status',   'H'),
                ('priority', 'H'),
                ('length',   'H'),
                ('message',  's',    'length'),
        )

        type,flags,status,priority,_,message,data = oscar.unpack(fmt, data, byte_order='<')

        if message:
            assert message[-1] == '\0'
            message = message[:-1]

            # this is wrong...seems to always be true
            auto = (flags & 0x2) == 0x2

            if message:
                self.protocol.incoming_rtf_message(self.buddy, message, )#auto)
            return

        fmt = (('length', 'H'),
               ('unknown', 's', 18),
               ('req_length', 'I'),
               ('request', 's', 'req_length'),
               ('phase', 'B'),
               ('unknown2', 's', 16),
               ('length2', 'I'),
               ('response_length', 'I'),
               ('response', 's', 'response_length'),
               ('enc_length', 'I'),
               ('encoding', 's', 'enc_length'),
               )

        try:
            _, _, _, request, phase, _, _, _, response, _, content_type, data = oscar.unpack(fmt, data, byte_order = '<')
            log.info('request = %r, phase = %r, response = %r, encoding = %r, data = %r', request, phase, response, content_type, data)
        except Exception:
            import traceback; traceback.print_exc()

        log.info('parsed request! %r', locals())

        # All observed headers for this data have been identical, but instead of having a magic byte string,
        # here it is broken down (as wireshark does):
        ex_data_header = struct.pack('<HH16sHIBHHH12sBBHHH',
                                     27,                        # length
                                     9,                         # version
                                     '\x00'*16,                 # plugin GUID (null = None)
                                     0,                         # unknown
                                     0,                         # client capability flags
                                     0,                         # unknown
                                     0x64,                      # "Downcounter?"
                                     14,                        # length
                                     0x64,                      # "Downcounter?"
                                     '\x00'*12,                 # unknown
                                     0x1a,                      # message type. 0x1a = plugin message described by text string
                                     0,                         # message flags
                                     0,                         # status code
                                     0,                         # priority code
                                     0)                         # text length

        ex_data = self.build_ex_data(request, phase, response, content_type)

        self.protocol.send_snac(*oscar.snac.send_x04_x0b(self.cookie, 0x2, self.screenname, 0x3,
                                                         ex_data_header +
                                                         ex_data,
                                                         ))

    def build_ex_data(self, request, phase, response, content_type):
        if phase != 0: # this is the only observed value as of 2010-01-04
            return ''

        if request:
            response_data = self.build_response_data(request, content_type)
        else:
            response_data = ''

        magic_header_bytes = '\x81\x1a\x18\xbc\x0el\x18G\xa5\x91o\x18\xdc\xc7o\x1a\x01\x00'
        response_encoding_data = (struct.pack('<I', len(response_data)) + response_data +
                                  struct.pack('<I', len(content_type)) + content_type)

        ex_data = (magic_header_bytes + struct.pack('<I', len(request)) + request +
                   '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
                   struct.pack('<I', len(response_encoding_data)) + response_encoding_data)

        return struct.pack('<H', 39 + len(request)) + ex_data

    def build_response_data(self, request, content_type):
        if request != 'Away Status Message': # this is the only observed value for this so far
            return ''

        # currently ignores requested content_type
        status_message = self.protocol.self_buddy.status_message
        if status_message is None:
            return ''
        else:
            return status_message.encode('utf8')


def initialize():
    log.info('\tloading rendezvous handler: extended messages')
    import oscar.rendezvous.peer as peer
    peer.register_rdv_factory('extended_msgs', IcqServerRelayer)

hooks.Hook('oscar.rdv.load').register(initialize)

