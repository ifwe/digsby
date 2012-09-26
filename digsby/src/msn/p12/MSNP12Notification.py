from msn.p11 import Notification as Super
class MSNP12Notification(Super):
    versions = ['MSNP12']
    def recv_lst(self, msg):
        '''
        MSNP12's LST command is the same as MSNP11's except there is an
        additional mystery flag for all buddies. Its value is always 1 and
        does not appear to mean anything.
        '''
        args = list(msg.args)
        if args[-1].find('-') != -1:
            # pop groups off
            groups = args.pop()
            mystery_flag = args.pop()

            # now put the groups back for our super()'s function
            args.append(groups)
        else:
            mystery_flag = args.pop()

        msg.args = list(args)

        return Super.recv_lst(self, msg)

