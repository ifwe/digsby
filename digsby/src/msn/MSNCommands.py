import io
import logging
import msn
import traceback
import email

from rfc822 import Message as RfcMsg
from util import pythonize, Storage
from util.primitives.funcs import autoassign, get, isint

_payload_commands = "MSG UUX UBX PAG IPG NOT GCF ADL UUN UBN RML FQY 241 508 UBM UUM PUT NFY SDG".split()
def is_payload_command(dlist, payload_commands = _payload_commands):
    cmd = dlist[0]
    if cmd in payload_commands:
        return True
    if cmd in ('201', '204', '500', '801', '252', '731', '240', '933', '715') and len(dlist) == 3:
        return True

    return False

def three_part_email_parse(data):
    return MultiPartMime.parse(data)

class CommandProcessor(object):
    def __init__(self, log = None):
        self.log = log or logging.getLogger(type(self).__name__)
        self.process_cmd = Storage(success=self.on_message, error=self.on_error)

    def on_message(self, msg):
        """
        This function is called by MSNSockets when a new
        command is receieved
        """
        if self.log: self.log.log_s(1,"Got message: %r", str(msg)[:100].strip('\r\n'))
        mname = 'recv_%s' % pythonize(msg.cmd)
        getattr(self, mname, self.unknown_cmd)(msg)

    def on_error(self, msg):
        assert msg.is_error
        self.log.error('MSNError! %r', msg)

    def unknown_cmd(self, msg):
        self.log.warning('Received unknown message from transport. Message is <%r>', msg)


class MsgPayload(RfcMsg):
    def __len__(self):
        return len(self.body())

class Message(object):
    argnames = []
    def __init__(self, cmd, *args, **kws):
        '''
        @param cmd:       Three letter (or number) code for which command this is
        @type  cmd:       string

        @param *args:     The arguments for this command. Must be str()able
        @type  *args:     Any object with a __str__ method

        @keyword trid:    The TrID to use for this command. Default is 0 and means there is none.
        @type    trid:    int

        @keyword payload: Payload for this command. If None, then the payload command
                          form will not be used
        @type    payload: None (for no payload) or string
        '''
        self.cmd = cmd.upper()
        self.args = list(args)
        self.trid = int(kws.pop('trid',0))
        self.payload = kws.pop('payload',None) or None
        assert not kws


    @property
    def length(self):
        if self.is_payload:
            return len(str(self.payload))
        else:
            return 0

    @property
    def is_trid(self):
        return bool(isint(self.trid) and int(self.trid))

    @property
    def is_payload(self):
        return self.payload is not None

    @property
    def is_error(self):
        return bool(self.error_code)

    @property
    def error_str(self):
        return msn.error_codes.get(self.error_code, 'Undocumented error')

    @property
    def error_code(self):
        try:     return int(self.cmd)
        except:  return None

    def __iter__(self):
        return iter(self.args)

    def __str__(self):
        res = [self.cmd]
        if self.is_trid:
            res.append(str(self.trid))

        res.extend(map(str,self.args))

        if self.is_payload:
            res.append(str(self.length)+'\r\n'+str(self.payload))

        return ' '.join(filter(None,res)) + ('\r\n' if not self.is_payload else '')

    def __repr__(self):

        err_str = ('error_str=%s, error_code=%s, ' % (self.error_str, self.error_code)) \
                   if self.is_error else ''

        if type(self) is Message:
            typestr = Message.__name__
        else:
            typestr = '%s(%s)' % (Message.__name__, type(self).__name__)
        return '<%s %s trid=%s, %sargs=%r, len(payload)=%s>' % \
                (typestr, self.cmd, self.trid, err_str, self.args,
                 len(self.payload) if self.is_payload else None)

    def __getattr__(self, attr):
        if attr in self.argnames:
            return self.args[self.argnames.index(attr)]
        else:
            return object.__getattribute__(self, attr)

    def get(self, key, default=sentinel):
        try:
            return self[key]
        except KeyError:
            if default is sentinel: raise
            else: return default


    def __getitem__(self, *a):
        return self.args.__getitem__(*a)

    @classmethod
    def from_net(cls, data, is_payload = None):
        if is_payload is None:
            is_payload = is_payload_command(data.split(' ', 1))

        if is_payload:
            cmdline, payload = data.split('\r\n',1)
        else:
            cmdline, payload = data, None

        cmdline = cmdline.strip('\r\n ')
        dlist = cmdline.split(' ')
        cmd = dlist.pop(0)

        if dlist and isint(dlist[0]):
            trid = int(dlist.pop(0))
        else:
            trid = 0

        if is_payload:
            try:
                l = dlist.pop()
            except IndexError:
                # oops, the TrID was the payload length
                l,trid = trid, 0
            try:
                assert isint(l) and int(l) == len(payload), (cmdline, len(payload))
            except AssertionError:
                assert cmd in ('ADL', 'RML') and (not isint(l) or len(payload) == int(l)), (cmdline, dlist, l, len(payload))
                dlist.append(l)
                payload = payload.strip() or None

        args = list(dlist)

        if cmd == 'MSG':
            ctype = MsgPayload(payload).get('content-type', '').split(';')[0]
            subcmd = msn.util.msgtypes.get(ctype, '')
            cls = globals().get(cmd+subcmd, MSG)
        else:
            cls = globals().get(cmd, cls)

        return cls(cmd, trid=trid, payload=payload, *args)

    def copy(self):
        return type(self)(self.cmd, trid = self.trid, payload = self.payload, *self.args)


class OUT(Message):
    argnames = ['reason']

class SDG(Message):
    argnames = ['length']

    def __init__(self, *a, **k):
        if not a or a[0] != 'SDG':
            a = ("SDG",) + a

        Message.__init__(self, *a, **k)
        self.payload = three_part_email_parse(self.payload)

    @property
    def type(self):
        return pythonize(self.payload.get("Message-Type"))

    @property
    def name(self):
        return self.payload.get("From").split(':', 1)[-1].split(';')[0]

    @classmethod
    def from_net(cls, data, is_payload = None):
        obj = Message.from_net(data, is_payload)
        obj.payload = three_part_email_parse(obj.payload)

        return obj

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__,
                           ' '.join('%s=%r' % x for x in vars(self).items()))

class MSG(Message):
    argnames = 'name nick length'.split()

    def __init__(self, *a, **k):
        if a[0] != 'MSG':
            a = ('MSG',) + a

        Message.__init__(self, *a, **k)
        self.type = msn.util.msgtypes.setdefault(self.payload['content-type'].split(';')[0],
                                                 'unknown')
    def __getitem__(self, *a, **k):
        try:
            return Message.__getitem__(self, *a, **k)
        except:
            return self.payload.__getitem__(*a, **k)

    def _get_payload(self):
        return self._payload

    def _set_payload(self, payload):
        self._payload = MsgPayload(payload)

    payload = property(_get_payload, _set_payload)

    def from_net(self, data, is_payload = None):
        assert data[:4] == type(self).__name__
        data = data[4:]
        res = Message.from_net(data, is_payload)
        if res.trid:
            tr, res.trid = res.trid, 0
            res.args = ('%d' % tr,) + res.args
        return res


    def __repr__(self):
        super = Message.__repr__(self)
        return '%s type=%s>' % (super.rstrip('>'), self.type)

class MSGdatacast(MSG):

    def _get_payload(self):
        return MSG._get_payload(self)

    def _set_payload(self, payload):
        MSG._set_payload(self, payload)
        self.contents = MsgPayload(self.payload.body())

    payload = property(_get_payload, _set_payload)

    def __getattr__(self, attr):
        if attr in ('id','data'):
            return get(self.contents, attr)
        else:
            return MSG.__getattr__(self,attr)

class UBM(Message):

    def __init__(self, *a, **k):
        Message.__init__(self, *a, **k)
        self.type = msn.util.msgtypes.setdefault(self.payload['content-type'].split(';')[0],
                                                 'unknown')

    def _get_payload(self):
        return self._payload

    def _set_payload(self, payload):
        self._payload = MsgPayload(payload)

    payload = property(_get_payload, _set_payload)

    def __getitem__(self, *a, **k):
        try:
            return Message.__getitem__(self, *a, **k)
        except:
            return self.payload.__getitem__(*a, **k)



class MSNSB_Message(Message):
    def __init__(self, contenttype, body, acktype='N', headers={}, **moreheaders):
        moreheaders.update(headers)
        content = []

        content.append('MIME-Version: 1.0')
        content.append('Content-Type: text/x-%s' % contenttype)

        for header in moreheaders.items():
            content.append('%s: %s' % header)

        content.append('')
        payload = '\r\n'.join(content) + body

        Message.__init__(self, 'MSG', acktype, payload=payload)


class MSNTextMessage(object):
    def __init__(self, body, fontname=None, color=None, rightalign=False,
                 bold=False, italic=False, underline=False, strike=False,
                 charset=0, family=22):

        autoassign(self, locals())

        if isinstance(self.fontname, str):
            self.fontname = self.fontname.decode('fuzzy utf8')
        if isinstance(self.body, str):
            self.body = self.body.decode('fuzzy utf8')

        self.effects = ''
        if self.bold:
            self.effects += 'B'
        if self.italic:
            self.effects += 'I'
        if self.underline:
            self.effects += 'U'
        if self.strike:
            self.effects += 'S'

        if self.color is not None:
            self.r, self.g, self.b = self.color[:3]
        else:
            self.r = self.g = self.b = None

        self.__html = u''

    def __str__(self):
        s = (u'\r\n'.join(['MIME-Version: 1.0',
                             'Content-Type: text/plain; charset=UTF-8',
                             'X-MMS-IM-Format: ' +
                             ('FN=%s; ' % self.fontname.encode('utf-8').encode('url').replace('%', '%%') if self.fontname is not None else '') +
                             ('EF=%(effects)s; ' if self.effects else '') +
                             ('CO=%(b)02X%(g)02X%(r)02X; ' if self.color else '') +
                             'CS=%(charset)d; PF=%(family)d',
                             '',
                            '%(body)s']))

        return (s % vars(self)).encode('utf-8')

    @classmethod
    def from_net(cls, rfc822msg):
        '''
        FN:        Font Name. URL-encoded name of font.
        EF:        Effects. B, I, U, S [bold, italic, underline, strikethru]
        CO:        Color. BBGGRR format (FFFFFF is white, 000000 is black. etc.)
        CS:        Charset (old pre-unicode windows stuff)
        PF:        Pitch and family - for figuring out a font if it's not available
        RL:        Right alignment. If 0, left-align. otherwise, right-align.
        '''
        m = rfc822msg
        fmt = m.get('X-MMS-IM-Format', '')
        body = m.get_payload().decode('fuzzy utf-8')

        msg = cls(body)


        if fmt:
            if fmt.strip().endswith(";"):
                fmt = fmt.strip()[:-1]
            try:
                fmt = msn.util.mime_to_dict(fmt)
            except Exception, e:
                traceback.print_exc()
                return msg

            _g = lambda k: get(fmt, k, None)

            fontname = _g('FN')
            msg.fontname = None if fontname is None else fontname.decode('url').decode('utf-8')

            color    = _g('CO')
            effects  = _g('EF')
            charset  = _g('CS')
            family   = _g('PF')
            ralign   = _g('RL')

            if color is not None:
                try:
                    color = int(msn.util.bgr_to_rgb(color), 16)
                except ValueError:
                    color = None
                else:
                    r = (color & 0xFF0000) >> 16
                    g = (color & 0x00FF00) >> 8
                    b = (color & 0x0000FF)
                    msg.color = (r,g,b)
                    msg.r = r
                    msg.g = g
                    msg.b = b

            if charset is not None:
                msg.charset = int(charset,16)

            if family is not None:
                msg.family = int(family)

            if ralign is not None:
                msg.rightalign = bool(int(ralign))

            if effects is not None:
                ef = lambda x: x in effects
                msg.bold      = ef('B')
                msg.italic    = ef('I')
                msg.underline = ef('U')
                msg.strike    = ef('S')
                msg.effects   = effects
        return msg

    def html(self):

        if self.__html:
            return self.__html

        from util.xml_tag import tag
        t = tag(u'font')

        if self.fontname:
            t[u'face']   = self.fontname
        if self.color:
            t[u'color']  = u'#' + (u''.join(map(lambda x: '%02x' % (x or 0), self.color[:3])))

        if self.rightalign:
            t[u'align']  = u'right'

        innermost = top = t
        for attr in ('bold','italic','underline','strike'):
            if getattr(self,attr):
                _tag = tag(attr[0])
                innermost += _tag
                innermost = _tag

        innermost._cdata = self.body

        self.__html = top._to_xml(pretty=False).strip()

        return self.__html

class MSNMime(email.Message.Message):
    def as_string(self, unixfrom = False, **k):
        from email.Generator import Generator
        fp = io.BytesIO()
        if 'maxheaderlen' not in k:
            k['maxheaderlen'] = 0
        g = Generator(fp, **k)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()

class MultiPartMime(object):
    def __init__(self, headers, body):
        self.parts = []
        for header_block in headers:
            self.add_header_block(header_block)

        del self.parts[-1]['Content-Length']
        self.parts[-1]['Content-Length'] = str(len(body))

        self.parts[-1].set_payload(body)

    def get_payload(self):
        return self.parts[-1].get_payload()

    def add_header_block(self, block):
        part = MSNMime()
        for header in block:
            key, val = header
            part.add_header(key, val)

        self.parts.append(part)

    def get(self, key, fallback = None):
        for part in self.parts:
            val = part.get(key, None)
            if val is not None:
                return val

        return fallback

    def __str__(self):
        result = []
        payload = self.get_payload()
        self.parts[-1].set_payload(None)
        msg_to_string = lambda x: x.as_string().replace('\n', '\r\n')
        for part in self.parts:
            result.append(msg_to_string(part))

        if payload is not None:
            result.append(str(payload))
            self.parts[-1].set_payload(payload)

        return ''.join(result)

    @classmethod
    def parse(cls, data):
        if not isinstance(data, basestring):
            return data

        content_length = None

        header_blocks = []

        while content_length is None:
            message = email.message_from_string(data, _class = MSNMime)
            header_blocks.append(message._headers)
            content_length = message.get('Content-Length')
            data = message.get_payload()
            message.set_payload(None)

        return cls(header_blocks, data)
