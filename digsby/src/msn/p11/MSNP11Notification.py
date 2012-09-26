import logging
import hashlib
import rfc822
import struct
import string
import re

import util
import util.primitives.funcs as funcs
import util.xml_tag
import msn

from util.Events import event

from msn.p10 import Notification as Super


log = logging.getLogger('msn.p11.ns')
defcb = dict(trid=True, callback=sentinel)

MAX_SINT = 0x7fffffff
psmurl_re = re.compile(r'\<PSMUrl\>(.*?)\</PSMUrl\>', re.IGNORECASE)
format_re = re.compile(r'%\((.*?)\)s')

def psm_url_fix(datatag_str):
    match = psmurl_re.search(datatag_str)

    if match:
        url = match.group(1)
        start, end = match.span()
        newmsg = datatag_str[:start] + datatag_str[end:]
    else:
        url = ''
        newmsg = datatag_str

    return newmsg, url

def transform_format_groups(fmtstring):
    '''
    Takes a python formatting string and returns a .NET style formatting string, and a list of keys.

    >>> fmt = '%(title)s - %(artist)s - %(title)s [stopped]'
    >>> transform_format_groups(fmt) == ('{0} - {1} - {0} [stopped]', ['title', 'artist'])
    True
    '''
    fixed, keys = [], []
    last_end = 0
    match = format_re.search(fmtstring, last_end)
    while match:
        key = match.group(1)
        if key not in keys:
            keys.append(key)
        fixed.append(fmtstring[last_end:match.start()])
        fixed.append('{%d}' % keys.index(key))
        last_end = match.end()
        match = format_re.search(fmtstring, last_end)

    fixed.append(fmtstring[last_end:])

    return ''.join(fixed), keys


def format_mediainfo(info):
    '''
    * Application - This is the app you are using. Usually empty (iTunes and Winamp are the only ones known to be accepted)
    * Type - This is the type of PSM, either 'Music', 'Games' or 'Office'
    * Enabled - This is a boolean value (0/1) to enable/disable the Current Media setting
    * Format - A formatter string (you may be familiar with this syntax if you've used .NET); for example, "{0} - {1}"
    * First line - The first line (Matches {0} in the Format)
    * Second line - The second line (Matches {1} in the Format)
    * Third line - The third line (Matches {2} in the Format)
    '''

    return repr(info)

class MSNP11Notification(Super):

    versions = ['MSNP11']
    client_chl_id = challenge_id = "PROD0090YUAUV{2B"
    client_chl_code = "YMM8C_H7KCQ2S_KL"

    events = Super.events | set (
        ('contact_status_msg',
         'received_oims',
         )
    )

    def __init__(self, *a, **k):
        self.oims = []
        Super.__init__(self, *a, **k)

    def recv_sbs (self, msg):
        """
        SBS (???)

        There is talk that this has something to do with 'mobile credits'.
        See U{http://msnpiki.msnfanatic.com/index.php/MSNP11:Changes#SBS}
        """
        log.warning("Got SBS command")

    def recv_ubx(self, msmsg):
        '''
        UBX mike.dougherty@gmail.com 87\r\n
        <Data><PSM>this is status message</PSM><CurrentMedia></CurrentMedia><PSMUrl>http://bugs.digsby.com/?act=view&id=121</PSMUrl></Data>\r\n

        UBX name@host 222\r\n
        <Data><PSM>Xbox 360: Kameo (axiom1985)</PSM><CurrentMedia></CurrentMedia><PSMURL>http://live.xbox.com/profile/profile.aspx?GamerTag=axiom1985&appid=messenger</PSMURL><SiteID>66262</SiteID><MachineGuid></MachineGuid></Data>\r\n
        '''
        bname, = msmsg.args
        msg = msmsg.payload
        log.info('Got UBX for %s: %r', bname, str(msg))

        # Take PSMUrl tag out and snag the URL from it if it exists.
        # Seems like sometimes the URL is not XML escaped and so it breaks the parser for util.xml_tag.tag

        if not msg:
            msg = '<data />'

        msg, url = psm_url_fix(msg)

        try:
            msg = util.xml_tag.tag(msg)
        except Exception:
            import traceback;traceback.print_exc()

            msg = util.xml_tag.tag('<data />')

        status_message = ''
        now_playing = ''

        if msg.PSM:
            status_message = msg.PSM._cdata.decode('xml')
            log.info('%r has status message of: %r', bname, status_message)
        if msg.CurrentMedia:
            media_str = msg.CurrentMedia._cdata.decode('xml')
            media = media_str.split('\\0')
            unused_application, type, enabled, format = [media.pop(0) for i in range(4)]

            for i in range(len(media)):
                format = format.replace('{%d}'%i, media[i])

            if int(enabled):

                if type.lower() == 'music':
                    try:
                        from nowplaying.nowplaying import NOTES_SYMBOL
                        type = NOTES_SYMBOL
                    except:
                        type = unichr(9835)

                else:
                    type = type+':'

                now_playing = u"%s %s"  % (type, format)
                log.info('%r has NowPlaying status of: %r', bname, now_playing)

        if status_message and now_playing:
            status_message = u'%s\n%s' % (status_message, now_playing)
        else:
            status_message = status_message or now_playing

        self.event('contact_status_msg', bname, status_message)

        return msg

    def recv_chl(self, msg):
        log.debug('got chl')
        self.event('challenge', msg.args[0])

    def recv_uux(self, msg):
        unused_message = msg.payload

    def send_uux(self, message = None, mediainfo = None, url = None, callback=None):
        mtag = util.xml_tag.tag('Data')
        if message is not None:
            mtag.PSM._cdata = message
        else:
            mtag.PSM._cdata = ''

        if mediainfo is not None:
            mtag.CurrentMedia._cdata = mediainfo
        else:
            mtag.CurrentMedia._cdata = ''

        if url is not None:
            mtag.PSMUrl._cdata = url
        else:
            mtag.PSMUrl._cdata = ''

        message = mtag._to_xml(pretty=False).encode('utf-8')
        self.socket.send(msn.Message('UUX', payload=message), trid=True, callback=callback)

    def _set_status_message(self, *a, **k):
        return self.send_uux(*a, **k)

    def set_message_object(self, messageobj, callback):
        media = getattr(messageobj, 'media', None)
        log.debug('set_message_object got this for (messageobj, media): %r', (messageobj, media))
        if media is not None:
            #
            # fmt is
            #
            # %(title)s - %(artist)s
            #   or maybe just
            # %(title)s
            #
            # args is a dictionary for splatting into fmt
            #

            fmt, args = funcs.get(media,'format_string',''),  funcs.get(media, 'format_args', {})

            if fmt and args:

                fmtstring, keys = transform_format_groups(fmt)
                values = [args[key] for key in keys]

                application = media.get('app', '')
                type = media.get('type', 'Music')
                enabled = '1'
                # ITunes\\0Music\\01\\0{0} - {1}\\0Crownless\\0Nightwish\\0Wishmaster\\0
                array = '\\0'.join([application, type, enabled, fmtstring] + values + [''])

                '''
                * Application - This is the app you are using. Usually empty (iTunes and Winamp are the only ones known to be accepted)
                * Type - This is the type of PSM, either 'Music', 'Games' or 'Office'
                * Enabled - This is a boolean value (0/1) to enable/disable the Current Media setting
                * Format - A formatter string (you may be familiar with this syntax if you've used .NET); for example, "{0} - {1}"
                * First line - The first line (Matches {0} in the Format)
                * Second line - The second line (Matches {1} in the Format)
                * Third line - The third line (Matches {2} in the Format)
                '''

                self.send_uux(mediainfo = array, callback = callback)
            else:
                log.debug('msn not sending CurrentMedia because no fmt or args. (fmt=%r, args=%r)', fmt, args)
                self.send_uux(message = messageobj.message, callback=callback)

        else:
            log.debug('msn not sending CurrentMedia because media is None')
            self.send_uux(messageobj.message, callback = callback)

    def recv_msg_notification(self, msg):
        #name, passport = msg.args
        if msg.name == 'Hotmail':
            MD = self.extract_oim_info(msg)
            self.oims = msn.oim.OIMMessages(self, MD)
        else:
            log.warning('unknown msg/notification')

    def extract_oim_info(self, oim_info_msg):
        msg_obj = rfc822.Message(oim_info_msg.payload.body())
        maildata = msg_obj['Mail-Data']
        if 'too-large' in maildata:
            MD = None
        else:
            MD = util.xml_tag.tag(maildata)

#        unread = int(str(MD.E.IU))
#        others = int(str(MD.E.OU))

        return MD

    def recv_msg_oims(self, msg):
        if msg.name == 'Hotmail':
            MD = self.extract_oim_info(msg)
            self.oims += msn.oim.OIMMessages(self, MD)



    @event
    def received_oims(self, oims):
        return oims

    def _challenge_response(self, chl_str, challenge_key, mystery_num=0x0E79A9C1):
        '''
        the crazyness below was created from the pseudocode at:
        U{http://msnpiki.msnfanatic.com/index.php/MSNP11:Challenges}

        horrible, horrible math, bitshifting, and other suchness
        to stay connected to MSN
        '''

        hash = hashlib.md5(chl_str + challenge_key).digest()

        hash_ints = struct.unpack("<llll", hash)
        hash_ints = [(x & MAX_SINT) for x in hash_ints]

        chl_str += self.challenge_id
        chl_str += string.zfill("", 8 - len(chl_str) % 8)
        chl_nums = struct.unpack("<%di" % (len(chl_str)/4), chl_str)

        hi = lo = i = 0
        while i < len(chl_nums) - 1:
            j = chl_nums[i]
            j = (mystery_num * j) % MAX_SINT
            j += hi
            j = hash_ints[0] * j + hash_ints[1]
            j = j % MAX_SINT

            hi = (chl_nums[i + 1] + j) % MAX_SINT
            hi = hash_ints[2] * hi + hash_ints[3]
            hi = hi % MAX_SINT

            lo = lo + hi + j

            i += 2

        byteswap = lambda i, f:\
                    struct.unpack(">" + f, struct.pack("<" + f, i))[0]

        hi = byteswap((hi + hash_ints[1]) % MAX_SINT, 'L')
        lo = byteswap((lo + hash_ints[3]) % MAX_SINT, 'L')
        key = byteswap((hi << 32L) + lo, 'Q')

        ls = [byteswap(abs(byteswap(x,'Q') ^ key), 'Q')
              for x in struct.unpack(">QQ", hash)]

        return ''.join(('%x' % x).zfill(16).lower() for x in ls)


def __test():
    import doctest
    doctest.testmod(verbose=True)

if __name__ == '__main__':
    __test()
