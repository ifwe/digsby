from util import callsback


import msn
from msn.p8 import Switchboard as Super

defcb = dict(trid=True, callback=sentinel)

class MSNP9Switchboard(Super):
    events = Super.events | set((
        'send_p2p_msg',
        'recv_p2p_msg',

    ))

#    def msg_p2p(self, socket, msg):
#        return
#        name = msg.args[0]
#        body = msg.payload.body()
#
#        try:
#            self.layer.incoming(body)
#        except AttributeError, e:
#            print 'P2PException!', str(e), repr(e), repr(self), type(self)
#            if 'INVITE' not in body:
#                log.critical('got p2p message but don\'t know where to send it')
#                return
#            print 'making new p2player + invited generator'
#            out_func = functools.partial(self.p2psend, name)
#            layer = msn.p2player.P2PLayer(self, None, out_func, 0)
#            recvr = msn.p2p.invited(layer, name, self)
#            layer.recv = recvr
#
#            #self.activities[name] = layer
#
#            layer.incoming(body)
#
#            if self.layer is not None:
#                print "Two p2players in one msnp9conversation?! UNPOSSIBLE!"
#                self.extra_layers.append(layer)
#            else:
#                self.layer = layer

    def send_p2p_message(self, to, data, callback):
        body = MSNP2PMessage(to, data)
        cmd = msn.MSNCommands.MSG('D', payload=str(body))

        self.socket.send(cmd, trid=True, callback=callback)
        self.event('send_p2p_msg', body)

    def recv_msg_p2p(self, msg):
        self.event('recv_p2p_msg', msg.args[0], msg.payload.body())

class MSNP2PMessage(object):

    def __init__(self, recvr, body):
        self.recvr = recvr
        self.body = body

    def __str__(self):
        return ('\r\n'.join(['MIME-Version: 1.0',
                             'Content-Type: application/x-msnmsgrp2p',
                             'P2P-Dest: %(recvr)s',
                             '',
                            '%(body)s'])) % vars(self)
