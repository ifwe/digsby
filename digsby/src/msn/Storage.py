import uuid
import simplejson as json
import logging

import util
log = logging.getLogger('msn.storage')

from msn.SOAP import Namespaces as MSNS
import msn.SOAP.services as SOAPServices
import msn.SOAP.pysoap_util as pysoap

def extract_zsi_properties(zsiobj):
    return dict((k[1:], v) for k, v in vars(zsiobj).items())

class DocumentStream(pysoap.Serializable):
    @classmethod
    def from_zsi(cls, obj, **kwds):
        real_cls = {
                    (MSNS.MSWS.STORAGE, 'PhotoStream') : PhotoStream,
                    (MSNS.MSWS.STORAGE, 'DocumentStream') : DocumentStream,
                    }.get(obj.typecode.type)

        if cls is DocumentStream:
            DS = pysoap.Serializable.from_zsi.im_func(real_cls, obj, **kwds)
            # more stuff?
        else:
            DS = real_cls.from_zsi(obj, **kwds)

        DS.SHA1Hash = DS.SHA1Hash.encode('b64')

        return DS

class PhotoStream(pysoap.Serializable):
    pass

class Photo(pysoap.Serializable):
    ResourceID = None
    DocumentStreams = [DocumentStream]
    @classmethod
    def from_zsi(cls, obj, **kwds):
        P = pysoap.Serializable.from_zsi.im_func(cls, obj, **kwds)
        P.DocumentStreams = [DocumentStream.from_zsi(X) for X in P.DocumentStreams.DocumentStream]
        return P

class ExpressionProfile(pysoap.Serializable):
    Photo = Photo
    @classmethod
    def from_zsi(cls, obj, **kwds):
        EP = pysoap.Serializable.from_zsi.im_func(cls, obj, **kwds)
        EP.Photo = Photo.from_zsi(EP.Photo)
        return EP

class Profile(pysoap.Serializable):
    nonserialize_attributes = ['client']
    ExpressionProfile = ExpressionProfile
    def __init__(self, client = None, **kw):
        self.client = client
        super(Profile, self).__init__(**kw)

    @classmethod
    def from_zsi(cls, obj, **kwds):
        P = pysoap.Serializable.from_zsi.im_func(cls, obj, **kwds)
        P.ExpressionProfile = ExpressionProfile.from_zsi(P.ExpressionProfile)
        return P

def __main():
    import ZSI, ZSI.schema as schema
    data = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Header><AffinityCacheHeader xmlns="http://www.msn.com/webservices/storage/2008"><CacheKey>1p8CXNxj8mTbyfRy5cdbxUbNpOw5IAof_RjSy7XAotTIAs1eKcah9MQg</CacheKey></AffinityCacheHeader><StorageUserHeader xmlns="http://www.msn.com/webservices/storage/2008"><Puid>0</Puid><Cid>0</Cid><ApplicationId>0</ApplicationId><TicketToken>t=EwDoAW+jAAAUVwo8hY/Rg6HvEdmXr19KcNgO+7mAAA3oPdbFO1wSu82lRckR/LUL2fSAHbA7skahr3eq37BfYX1s7Dcj6PKkLco7bUKCEP9NPZGXeM5zLb6SgsnDwnrrgs6rjZrOAyz2Nf1Jg8tj0uDg4BzCtEm2lQi7P1LjGrHfvkD4bJKQTRW2Ot8W4zop6cCSPKjmKxH15v/cXqlkA2YAAAh2WM/FIDyMijgBvRY/ln+7e+GXZ+0dIb1AlHP47KUaEcX4HI1UgJMnKQ7Z2ybcWP19kthAYQLmc1QhCMfocKWTbniLzWO+H4EEwIf7VQGyGzgCsQ+L9Oz+oxad4A7WYOcmO58yIYEYETk7rYhRzPXYKbLM2fM/WVg6rrPC3LG/oyqMkbmQf6I0ebQxOPv/k7npSwpMnj4bMmMh/TjoA+4lSQrjx4iCT6ZJq9jmLRyRH5mlJ/ultaXCAFVttQ7dAEGYu7YuZOActLa5DyUYQ1/F/AK21k3VX+5YvTVvIXFE1ourC+YumAJlouczBvtGIy5DNvAwpCIXeqHDP6iYGQpID8cTiCf95Ctq3oK5pHmHSfCPi+wymbpBVzlVNlRF6kVuR64oxMFX+CojJLyQmv6UYSlU0YVZ1e9zi9pcBa42huJ5dQE=&amp;p=</TicketToken><IsAdmin>false</IsAdmin></StorageUserHeader></soap:Header><soap:Body><GetProfileResponse xmlns="http://www.msn.com/webservices/storage/2008"><GetProfileResult><ResourceID>C9133A4085E57C34!101</ResourceID><DateModified>2011-03-01T06:24:21.577-08:00</DateModified><ExpressionProfile><ResourceID>C9133A4085E57C34!130</ResourceID><DateModified>2011-02-28T15:00:25.977-08:00</DateModified><Photo><ItemType>Photo</ItemType><ResourceID>C9133A4085E57C34!132</ResourceID><DateModified>2011-02-28T15:00:26.713-08:00</DateModified><Name>Webcam</Name><DocumentStreams><DocumentStream xsi:type="PhotoStream"><DocumentStreamName>UserTileStatic</DocumentStreamName><MimeType>image/jpeg</MimeType><DataSize>2347</DataSize><PreAuthURL>http://sn2files.storage.msn.com/y1pSLNg0PlgMWDC0wQ8Qeriz4OKCmrd1fT-P6-GIgReDdlxsCQxX6c0-j_35MhEGCk0K1n8et_j8xjXVjSDxQ7dQg</PreAuthURL><PreAuthURLPartner>http://internal.sn2.pvt-livefilestore.com/y1pSLNg0PlgMWDC0wQ8Qeriz4OKCmrd1fT-P6-GIgReDdlxsCQxX6c0-j_35MhEGCk0K1n8et_j8xjXVjSDxQ7dQg</PreAuthURLPartner><WriteMode>Overwrite</WriteMode><SHA1Hash>rG952Xtm0+Ctn0o/LLeOorBBtik=</SHA1Hash><Genie>false</Genie><StreamVersion>258</StreamVersion><DocumentStreamType>UserTileStatic</DocumentStreamType><SizeX>96</SizeX><SizeY>96</SizeY></DocumentStream></DocumentStreams></Photo><PersonalStatus>- on www.ebuddy.com Web Messenger</PersonalStatus><PersonalStatusLastModified>2010-05-27T13:05:25-07:00</PersonalStatusLastModified><DisplayName>Michael</DisplayName><DisplayNameLastModified>2008-01-10T16:02:26-08:00</DisplayNameLastModified><StaticUserTilePublicURL>http://sn2files.storage.msn.com/y1pvl2Jn-4-_9Ofj9SL1vLwNeWQ5OcYt-g4qxVurMMylKIhNnQs6kWAFBc3RiEws2KTD8AV8EfPw6E</StaticUserTilePublicURL></ExpressionProfile></GetProfileResult></GetProfileResponse></soap:Body></soap:Envelope>'

    ps = ZSI.ParsedSoap(data)
    pname = ps.body_root.namespaceURI, ps.body_root.localName
    el_type = schema.GTD(*pname)
    if el_type is not None:
        tc = el_type(pname)
    else:
        tc = schema.GED(*pname)

    reply = ps.Parse(tc)

    profile = Profile.from_zsi(reply.GetProfileResult)
    try:
        print profile.serialize()
    except:
        import traceback; traceback.print_exc()

    return profile

if __name__ == '__main__':
    __main()
