import uuid
import util.primitives.funcs as funcs

import email
import email.Message as Message

import msn.MSNCommands as MSNC

class RequestMethod:
    INVITE = "INVITE"
    BYE = "BYE"
    ACK = "ACK"

class SLPMessage(object):
    Encoding = 'utf8'

    def __repr__(self):
        varstr = ', ' .join('%s=%r' % i for i in vars(self).items())
        return '%s(%s)' % (type(self).__name__, varstr)

    def GetEndPointIDFromMailEPIDString(self, mailEPID):
        if ';' in mailEPID:
            return uuid.UUID(filter(None, mailEPID.split(';'))[-1])

        return uuid.UUID(int=0)

    def GetEmailAccount(self, mailEPID):
        if ';' in mailEPID:
            return filter(None, mailEPID.split(';'))[0]
        return mailEPID

    def __init__(self, data = None):
        if data is not None:
            self.ParseBytes(data)
        else:
            self.mimeHeaders = MSNC.MSNMime()
            self.mimeBodies = MSNC.MSNMime()

            self.Via = 'MSNSLP/1.0/TLP '
            self.Branch = uuid.uuid4()
            self.CSeq = 0
            self.CallId = uuid.uuid4()
            self.MaxForwards = 0
            self.ContentType = 'text/unknown'

    StartLine = funcs.iproperty('_get_StartLine', '_set_StartLine')

    def MaxForwards():
        def fget(self):
            return int(self.mimeHeaders.get('Max-Forwards', 0))

        def fset(self, value):
            del self.mimeHeaders['Max-Forwards']
            self.mimeHeaders['Max-Forwards'] = str(value)

        return locals()

    MaxForwards = property(**MaxForwards())

    def To():
        def fget(self):
            return self.mimeHeaders['To']
        def fset(self, value):
            del self.mimeHeaders['To']
            self.mimeHeaders['To'] = value
        return locals()

    To = property(**To())

    def From():
        def fget(self):
            return self.mimeHeaders['From']
        def fset(self, value):
            self.mimeHeaders['From'] = value
        return locals()

    From = property(**From())

    @property
    def FromEmailAccount(self):
        return self.GetEmailAccount(self.From.replace('<msnmsgr:', '').replace('>', ''))

    @property
    def ToEmailAccount(self):
        return self.GetEmailAccount(self.To.replace('<msnmsgr:', '').replace('>', ''))

    @property
    def FromEndPoint(self):
        return self.GetEndPointIDFromMailEPIDString(self.From.replace('<msnmsgr:', '').replace('>', ''))

    @property
    def ToEndPoint(self):
        return self.GetEndPointIDFromMailEPIDString(self.To.replace('<msnmsgr:', '').replace('>', ''))


    def Source():
        def fget(self):
            return self.From.replace('<msnmsgr:', '').replace('>', '')
        def fset(self, value):
            self.From = '<msnmsgr:%s>' % value

        return locals()
    Source = property(**Source())

    def Target():
        def fget(self):
            return self.To.replace('<msnmsgr:', '').replace('>', '')
        def fset(self, value):
            self.To = '<msnmsgr:%s>' % value

        return locals()
    Target = property(**Target())

    def Via():
        def fget(self):
            return self.mimeHeaders['Via']
        def fset(self, value):
            del self.mimeHeaders['Via']
            self.mimeHeaders['Via'] = value
        return locals()

    Via = property(**Via())

    def Branch():
        def fget(self):
            via_parts = self.mimeHeaders.get('Via', '').split('branch=', 1)
            if len(via_parts) == 2:
                return uuid.UUID(via_parts[1])
            else:
                return uuid.UUID(int = 0)
        def fset(self, value):
            old_via = self.mimeHeaders.get('Via')
            via = old_via.split(';')[0]
            new_via = (via+';branch={%s}') % (str(value).upper())
            del self.mimeHeaders['Via']
            self.mimeHeaders['Via'] = new_via
        return locals()

    Branch = property(**Branch())

    def CSeq():
        def fget(self):
            return int(self.mimeHeaders.get('CSeq', 0))

        def fset(self, value):
            del self.mimeHeaders['CSeq']
            self.mimeHeaders['CSeq'] = str(value)

        return locals()

    CSeq = property(**CSeq())

    def CallId():
        def fget(self):
            return uuid.UUID(self.mimeHeaders.get('Call-ID', str(uuid.UUID(int=0))))

        def fset(self, value):
            del self.mimeHeaders['Call-ID']
            self.mimeHeaders['Call-ID'] = '{' + str(value).upper() + '}'

        return locals()

    CallId = property(**CallId())

    def ContentType():
        def fget(self):
            return self.mimeHeaders.get('Content-Type')

        def fset(self, value):
            del self.mimeHeaders['Content-Type']
            self.mimeHeaders['Content-Type'] = value

        return locals()

    ContentType = property(**ContentType())

    @property
    def BodyValues(self):
        return self.mimeBodies

    def GetBytes(self, appendNull = True):
        body = self.mimeBodies.as_string().replace('\n', '\r\n') + ('\0' * appendNull)
        del self.mimeHeaders['Content-Length']
        self.mimeHeaders['Content-Length'] = str(len(body))

        return ''.join((self.StartLine.strip(), '\r\n',
                        self.mimeHeaders.as_string().replace('\n', '\r\n'),
                        body))

    def ParseBytes(self, data):
        self.StartLine, data = data.split('\r\n', 1)
        self.mimeHeaders = email.message_from_string(data, _class = MSNC.MSNMime)
        self.mimeBodies = email.message_from_string(self.mimeHeaders.get_payload(), _class = MSNC.MSNMime)
        self.mimeHeaders.set_payload(None)

    @classmethod
    def Parse(cls, data):
        if '\r\n' not in data:
            return None

        firstline = data.split('\r\n', 1)[0]
        if "MSNSLP" not in firstline:
            return None

        if firstline.startswith("MSNSLP/1.0"):
            return SLPStatusMessage(data)
        else:
            return SLPRequestMessage(data)


class SLPRequestMessage(SLPMessage):
    Method = 'UNKNOWN'
    Version = 'MSNSLP/1.0'

    def _get_StartLine(self):
        return '%s %s:%s %s' % (self.Method, 'MSNMSGR', self.Target, self.Version)

    def _set_StartLine(self, value):
        parts = value.split()
        self.Method = parts[0]
        self.Version = parts[2]

    def __init__(self, Data_or_To, Method = None):
        if Method is None:
            super(SLPRequestMessage, self).__init__(Data_or_To)
        else:
            super(SLPRequestMessage, self).__init__()
            self.Target = Data_or_To
            self.Method = Method

class SLPStatusMessage(SLPMessage):
    Version = 'MSNSLP/1.0'
    Code = 0
    Phrase = 'Unknown'

    def _get_StartLine(self):
        return '%s %s %s' % (self.Version, self.Code, self.Phrase)

    def _set_StartLine(self, value):
        parts = value.split()
        self.Version = parts.pop(0)
        self.Code = int(parts.pop(0))
        self.Phrase = ' '.join(parts).strip()

    def __init__(self, Data_or_To, Code = None, Phrase = None):
        if Code is None and Phrase is None:
            # Data to parse
            super(SLPStatusMessage, self).__init__(Data_or_To)
        else:
            super(SLPStatusMessage, self).__init__()
            self.Target = Data_or_To
            self.Code = Code or self.Code
            self.Phrase = Phrase or self.Phrase
