
from msn.p11 import Switchboard as Super

class MSNP12Switchboard(Super):
    def recv_joi(self, msg):
        msg.args = msg.args[:2]
        Super.recv_joi(self, msg)
