from util.primitives.mapping import groupify
from .yahooP2Psocket import YahooP2PSocket
from .yahoolookup import commands, statuses
from .yahooutil import yiter_to_dict
from util.lrucache import ExpiringLRU

#MESSAGES_TO_REMEMBER = 30
REMEMBER_MESSAGES_FOR = 5 * 60 #seconds

ACK_LIST = '430'

def ack_message(yahoo_connection, d, buddy_key):
    '''
    sends a message ack
    '''
    ret = True
    lru = getattr(yahoo_connection, '_msg_acks', None)
    if lru is None:
        lru = yahoo_connection._msg_acks = ExpiringLRU(REMEMBER_MESSAGES_FOR)
    ack_message_key = get_ack_message_key(d, buddy_key)
    if ack_message_key is not None:
        if ack_message_key in lru:
            c1 = dict(lru[ack_message_key])
            c2 = dict(d)
            s1 = c1.pop('send_attempt', None)
            s2 = c2.pop('send_attempt', None)
            if (s1 is not s2 is not None) and s1 != s2:
                if c1['msgid'] == c2['msgid'] and c1.get('message') == c2.get('message'):
                    ret = False
            if not ret:
                #refresh the RU in LRU
                lru[ack_message_key] = lru[ack_message_key]
            else:
                lru[ack_message_key] = d
        else:
            lru[ack_message_key] = d
    dout = type(d)()
    dout['frombuddy'] = d['to']
    dout['to'] = d[buddy_key]
    for k in ['msgid', 'send_attempt']:
        if k in d:
            if k == 'msgid':
                dout['begin_mode'] = ACK_LIST
                dout['msgid_ack'] = d['msgid']
                dout['end_mode'] = ACK_LIST
                dout.pop('message', None)
            else:
                dout[k] = d[k]
#            d[252] = ('a'*22).encode('b64')
    yahoo_connection.send('msg_ack', 'available', ydict=dout)
    return ret

def get_ack_message_key(d, buddy_key):
    if 'msgid' in d:
        return (d[buddy_key], d['to'], buddy_key, d['msgid'])


class YahooP2P(object):
    def __init__(self, yahoo, buddy, me, remote_client, session_id):
        self.yahoo  = yahoo
        self.buddy  = buddy
        self.me     = me
        self.rc     = remote_client

        self.socket = YahooP2PSocket(self, self.rc, session_id)
        self.socket.connect(self.rc)

    def incoming_message_raw(self, ydict_iter):
        return getattr(self.yahoo, 'incoming_message_raw')(ydict_iter)
    def message_notinoffice_raw(self, ydict_iter):
        return getattr(self.yahoo, 'message_notinoffice_raw')(ydict_iter)
    def message_brb_raw(self, ydict_iter):
        return getattr(self.yahoo, 'message_brb_raw')(ydict_iter)

    def message_offline_raw(self, ydict_iter):
        out = list(ydict_iter)
        i = list(out)
        print 'i', i
        messages = groupify(i)
        for d in messages:
            d = yiter_to_dict(d.iteritems())
            if 'message' not in d:
                continue
            if 'frombuddy' not in d:
                continue
            if 'msgid' not in d:
                d['buddy'] = d['frombuddy']
                d.pop('frombuddy')
                for k in d.keys():
                    if k not in ['message', 'buddy', 'to']:
                        d.pop(k)
#            d[252] = ('a'*22).encode('b64')
                self.send('message', 'brb', ydict=d)
                continue
            else: #'msgid' in d
                ack_message(self, d, 'frombuddy')
        return getattr(self.yahoo, 'message_offline_raw')(iter(out))

    def notify_typing(self, typing_status, flag):
        self.yahoo.notify_brb(self.buddy, typing_status, flag)

    def on_close(self):
        foo = self.yahoo.peertopeers.pop(self.buddy)
        assert foo is self

    def on_connect(self):
        self.send('p2pfilexfer', 'available', buddy=self.me, to=self.buddy,
                  flag='1', typing_status='PEERTOPEER', **{'2':'1'})

    def p2pfilexfer_available(self, buddy, to, flag, typing_status, **k):
        if flag == '5':
            self.send('p2pfilexfer', 'available', buddy=to, to=buddy, flag='6',
                      typing_status='PEERTOPEER')
        elif flag == '7':
            self.send('p2pfilexfer', 'available', buddy=to, to=buddy, flag='7',
                      typing_status='PEERTOPEER')

    def send(self, command, status, ydict={}, **kw):
        'Sends a Yahoo dictionary over the network.'
        if isinstance(ydict, dict):
            ydict.update(kw)
        else:
            [ydict.extend([k, v]) for k, v in kw.iteritems()]

        self.socket.ysend(commands[command],statuses[status],
                          data=ydict)

    def Disconnect(self):
        self.socket.close()
        foo = self.yahoo.peertopeers.pop(self.buddy)
        assert foo is self

