'''
Created on Dec 13, 2010

@author: Christopher
'''

from util.net import WebFormData, wget
from util.primitives.mapping import LazySortedDict
import hashlib
import hmac
import simplejson
import urllib
import pprint
from common import asynchttp

ICQ_API_KEY = 'gu19PNBblQjCdbMU'

ICQ_API = 'icq.com'
AIM_API = 'aol.com'


def hmac_sha256_base64(secret, password):
    return hmac.new(password, secret, digestmod=hashlib.sha256).digest().encode('b64')

def get_login_data(login, password, api = 'icq.com', callback=None):
    if callback is None:
        return simplejson.loads(wget('https://api.screenname.%s/auth/clientLogin?f=json' % api,
                    dict(k=ICQ_API_KEY, s=login, pwd=password)))
    else:
        return asynchttp.httpopen('https://api.screenname.%s/auth/clientLogin?f=json' % api,
                    data = dict(k=ICQ_API_KEY, s=login, pwd=password), callback=callback)

def get_login_cookie(login, password, api = 'icq.net', api2 = None):
    if api2 is None:
        api2 = api
    r = get_login_data(login,password,api2)
    sessionSecret = r['response']['data']['sessionSecret']
    token = r['response']['data']['token']['a']
    sessionKey = hmac_sha256_base64(sessionSecret, password)
    uri = "https://api.oscar.%s/aim/startOSCARSession" % api

    d = dict(a = token,
             f = 'json',
             k = ICQ_API_KEY,
             ts = r['response']['data']['hostTime'],
             useTLS = 1
             )

    queryString = WebFormData(d=LazySortedDict(d)).replace('+', '%20')
    hashData= "GET&" + urllib.quote(uri, safe = '') + "&"  + queryString.encode('url')

    digest = hmac_sha256_base64(hashData, sessionKey)

    url = uri + "?" + queryString + "&sig_sha256=" + digest
    ret = simplejson.loads(wget(url))
    return ret


if __name__ == "__main__":
    ret = get_login_cookie('digsby01', '%%%', AIM_API)
    pprint.pprint(ret)
