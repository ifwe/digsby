'''

AOLMail login cookie stuff

'''


HOST = 'kdc.uas.aol.com'
HOST2 = 'localhost:50000'

top = 'POST / HTTP/1.1\r\n' +\
      'Accept: application/x-snac\r\n' +\
      'Content-Type: application/x-snac\r\n' +\
      'User-Agent: CLC/1.0\r\n' +\
      'Host: '+ HOST + '\r\n' +\
      'Content-Length: %d'

top2 ='\r\n' +\
      'Connection: Keep-Alive\r\n' +\
      'Cache-Control: no-cache\r\n' +\
      '\r\n'

top3 ='\x05\x0c\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00'


#2 bytes

middle =  '\xc0\xa8\xd7\x80\x00\x00\x00\x01\x00\x00\x00\x06' +\
          '\x05' +\
          '\x00\x00\x00\x00\x02' +\
          '\x00\n' +\
          '\x00\x02\x00\x01\x00\x0b\x00\x04\x00\x10' +\
          '\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00' +\
          '\x00\x02US' +\
          '\x00\x02en' +\
          '\x00\x02\x00\x03' +\
          '\x00\x02US' +\
          '\x00\x04\x00\x02en' +\
          '\x00\x00\x00\x00\x00\x00'

#pstring(un)

m2     = '\x00\x0dTritonService' +\
         '\x00\x00\x00\x00\x00\x00\x00\x01' +\
         '\x00\x02'  #len(remainder) 2bytes


remainder = '@\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00' +\
            '\x00\x14urfaceisnotapassword' +\
            '\x00\x03\x00\x01' +\
            '\x00\x05UTF-8' +\
            '\x00\x02' +\
            '\x00\x02en' +\
            '\x00\x03' +\
            '\x00\x02US'

from util import pack_pstr, unpack_pstr
def make_remainder(password):
    return '@\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00' + pack_pstr(
            '\x00' + pack_pstr(password) +\
            '\x00\x03\x00\x01' +\
            '\x00\x05UTF-8' +\
            '\x00\x02' +\
            '\x00\x02en' +\
            '\x00\x03' +\
            '\x00\x02US')

import socket, ssl
from struct import pack

from util import fmt_to_dict

SiteState = fmt_to_dict('|',':')

def do_https(v):
    s = socket.SocketType()
    s.connect(('kdc.uas.aol.com', 443))
    s = ssl.wrap_socket(s)
    s.write(v)
    return s

def make_packet(un, password):
    #i0 are two "random bytes", not sure what the restrictions here are
    n = top3 + 'i0' + middle
    n += pack_pstr(un)
    n += m2
    r = make_remainder(password)
    n += pack('!H', len(r))
    n += r
    t = top % (len(n))
    return t + top2 + n

def get_krbtgt(un, password):
    n = make_packet(un, password)
    s = do_https(n);
    return s.read()

def make_packet2(un, password):
    n = top3 + 'i0' + middle
    n += pack_pstr(un.encode('ascii'))
    n += m2
    r = make_remainder(password)
    n += pack('!H', len(r))
    n += r
    return n

def get_krbtgt2(un, password):
    import urllib2
    n = make_packet2(un, password)
    loc = 'https://' + HOST + '/'
    req = urllib2.Request(loc, n, headers={'Content-Type': 'application/x-snac',
                                           'Accept': 'application/x-snac'})
    return urllib2.urlopen(req).read()



from struct import unpack
from datetime import datetime
import base64
from util import UrlQuery
from OscarUtil import s_tlv, s_tlv_list, tlv #@UnresolvedImport

def readshort(bytes):
    return unpack('!H', bytes[:2])[0], bytes[2:]

def readlen(bytes, _len):
    return bytes[:_len], bytes[_len:]

from logging import getLogger; xsnaclog = getLogger('X_SNAC')

class X_SNAC(object):
    def __init__(self, bytes):
        xsnaclog.info('bytes were %r', bytes)
        self.family, self.subtype = unpack('!HH', bytes[:4])
        bytes = bytes[4:]
        self.flags, bytes = bytes[:8], bytes[8:]
        self.reqid, bytes = bytes[:2], bytes[2:]
        self.date1 = datetime.fromtimestamp(unpack('!I', bytes[:4])[0])
        bytes = bytes[4:]
        self.unknown1, bytes = readlen(bytes, 4)
        plen, bytes = readshort(bytes)
        self.principal1, bytes = readlen(bytes, plen)
        plen, bytes = readshort(bytes)
        self.principal2, bytes = readlen(bytes, plen)
        num_tokens, bytes = readshort(bytes)
        self.tokens = []
        for i in range(num_tokens):
            d = {}
            self.tokens.append(d)
            d['main'], bytes = s_tlv(bytes)
            d['strs'] = []
            for j in range(4):
                l, bytes = readshort(bytes)
                s, bytes = readlen(bytes, l)
                d['strs'].append(s)
            d['0x10'], bytes = unpack('!B', bytes[0]), bytes[1:]
            l, bytes = readshort(bytes)
            d['footer_junk1'], bytes = readlen(bytes, l)
            d['footer_dates'], bytes = readlen(bytes, 0x18)
            dates = [d['footer_dates'][x:x+4] for x in range(0, 0x18, 4)]
            dates = [unpack('!I', date)[0] for date in dates]
            d['footer_dates'] = [datetime.fromtimestamp(date) for date in dates]
            d['footer_junk2'], bytes = readlen(bytes, 12)
            num_tlvs, bytes = readshort(bytes)
            d['footer_tlvs'], bytes = s_tlv_list(bytes, num_tlvs)
        num_tlvs, bytes = readshort(bytes)
        self.footer = s_tlv_list(bytes, num_tlvs)

#https://my.screenname.aol.com/_cqr/login/login.psp?
#sitedomain=sns.webmail.aol.in
#siteState=OrigUrl%3dhttp%3A%2F%2Fwebmail%2Eaol%2Ein%2FSuite%2Easpx%3Fapp%253Dmail
#mcState=doAAMAuth
#authToken=%2FBcAG0cFBg0AAPdsAapki0cFBkkIbpTcSQ3QwQAAAA%3D%3D

def go_to_mail(un="digsby01", password="thisisapassword",
               baseurl='https://my.screenname.aol.com/_cqr/login/login.psp?',
               sitedomain='sns.webmail.aol.com',
               OrigUrl='http://webmail.aol.com/Suite.aspx?'):
    OrigUrl = UrlQuery(OrigUrl, app='mail')
    t = X_SNAC(get_krbtgt2(un, password))
    mytlv = t.tokens[1]['main'];
    authTok = base64.b64encode(tlv(mytlv.t, mytlv.v));
    out = UrlQuery(baseurl,
                   sitedomain=sitedomain,
                   lang='en',
                   locale='us',
                   siteState='OrigUrl=' + OrigUrl,
                   mcState='doAAMAuth',
                   authToken=authTok);
    import wx
    wx.LaunchDefaultBrowser(out)

def go_to_mail2(un="digsby01", password="passwordsshouldntbeinsourcecode", remainder=''):
    t = X_SNAC(get_krbtgt2(un, password))
    #should check the type of the tlv to find the right one.
    mytlv = t.tokens[1]['main']
    authTok = base64.b64encode(tlv(mytlv.t, mytlv.v))
    baseurl='https://my.screenname.aol.com/_cqr/login/login.psp?'
    out = UrlQuery(baseurl,authToken=authTok)
    import wx
    wx.LaunchDefaultBrowser(out+remainder)



def go_to_compose(un="digsby01", password="theresalotofthesepasswords", **k):
    xsnaclog.debug_s('go_to_compose %s', k)
    t = X_SNAC(get_krbtgt2(un, password))
    #should check the type of the tlv to find the right one.
    mytlv = t.tokens[1]['main']
    authTok = base64.b64encode(tlv(mytlv.t, mytlv.v))
    baseurl='https://my.screenname.aol.com/_cqr/login/login.psp?'
    from urllib import quote
    out = UrlQuery(baseurl,authToken=authTok,
                   mcState='doAAMAuth',
                   sitedomain='sns.webmail.aol.com',
                   siteState=SiteState({},ver='2',
                                       ac='WS',
                                       at='SNS',
                                       ld='webmail.aol.com',
                                       rp=quote(UrlQuery('mail/composemessage.aspx?', **k), safe=''),
                                       uv='AIM',
                                       lc='en-us'))
    import wx
    xsnaclog.debug_s('go_to_compose out: %r', out)
    wx.LaunchDefaultBrowser(out)

def go_to_msg(un="digsby01", password="howmanypasswordsdoesittaketochangealightbulb", msg='18282583'):
    t = X_SNAC(get_krbtgt2(un, password))
    #should check the type of the tlv to find the right one.
    mytlv = t.tokens[1]['main']
    authTok = base64.b64encode(tlv(mytlv.t, mytlv.v))
    baseurl='https://my.screenname.aol.com/_cqr/login/login.psp?'
    from urllib import quote
    out = UrlQuery(baseurl,authToken=authTok,
                   mcState='doAAMAuth',
                   sitedomain='sns.webmail.aol.com',
                   lang='en',
                   locale='us',
                   siteState='ver:2|ac:WS|at:SNS|ld:webmail.aol.com|rp:' +
                   quote(UrlQuery('Lite/MsgRead.aspx?',
                         dict(folder='Inbox',uid='1.' +msg, seq='1', start='0')), safe='')
                   +'|uv:AIM|lc:en-us')
    import wx
    wx.LaunchDefaultBrowser(out)
#'Lite/MsgRead.aspx%3Ffolder%3DInbox%26uid%3D1.18282583%26seq%3D1%26start%3D0'

#login2.go_to_mail2(un='digsby01', password='three',remainder='&mcState=doAAMAuth&sitedomain=sns.webmail.aol.com&lang=en&locale=us&siteState=ver:2|ac:WS|at:SNS|ld:webmail.aol.com|rp:mail%2fcomposemessage.aspx?to=test%26subject=test2%26body=test3|uv:AIM|lc:en-us')


#http://webmail.aol.com/30978/aim/en-us/Lite/MsgRead.aspx?folder=Inbox&uid=1.15292301&seq=1&start=0
#siteState='ver:2|ac:WS|at:SNS|ld:webmail.aol.com|rp:mail%2fcomposemessage.aspx?|uv:AIM|lc:en-us'
