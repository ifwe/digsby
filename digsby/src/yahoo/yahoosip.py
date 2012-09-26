import uuid
import socket

server_ip_port = '98.138.26.129:443'

def send():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host, port = server_ip_port.split(':')
    port = int(port)
    print 'connecting to', (host, port)
    s.connect((host, port))
    packet = register('digsby01')
    print 'sending packet'
    s.sendall(packet)
    print 'receiving data'
    print s.recv(50)
    s.close()

def register(yahoo_username, branch=None, call_id=None):
    if branch is None:
        branch = uuid.uuid4()
    if call_id is None:
        call_id = uuid.uuid4()
    random_tag = uuid.uuid4().hex[:8]

    local_port_ip='127.0.0.1:5061'
    my_contact_ip='127.0.0.1:443'

    contact_id = '<sip:%s@%s;transport=tcp>' % (yahoo_username, my_contact_ip)
    to_id = '<sip:%s@%s;transport=tcp>' % (yahoo_username, server_ip_port)
    from_id = '<sip:%s@%s>;tag=%s' % (yahoo_username, server_ip_port, random_tag)
    call_id = 'f3e9ee72-6270-42d8-a058-a6c3f34cfce2' # generate

    lines = [
     ('Via', 'SIP/2.0/TCP %s;branch=%s' % (local_port_ip, branch)),
     ('Max-Forwards', '70'),
     ('Contact', contact_id),
     ('To', to_id),
     ('From', from_id),
     ('Call-ID', call_id),
     ('CSeq', '1 REGISTER'),
     ('Expires', '3600'),
     ('User-Agent', 'Yahoo Voice,2.0'),
     ('Content-Length', '0'),
     ('Y-User-Agent', 'intl=us; os-version=w-2-6-1; internet-connection=lan; cpu-speed=2653; pstn-call-enable=true; appid=10.0.0.1270'),
    ]


    verb = 'REGISTER'
    action = '%s sip:%s;transport=tcp SIP/2.0' % (verb, server_ip_port)

    header_lines = ['%s: %s' % (k, v) for k, v in lines]
    return '\r\n'.join([action] + header_lines) + '\r\n'

def main():
    send()

if __name__ == '__main__':
    main()
