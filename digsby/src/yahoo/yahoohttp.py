from logging import getLogger
from traceback import print_exc
from util.callbacks import callsback
from util.xml_tag import tag, post_xml
import urllib2
import httplib

log = getLogger('yahoohttp')

def y_webrequest(url, data, cookies):
    headers = {'Cookie': cookies['Y'] + '; ' + cookies['T'],
               'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5)',
               'Cache-Control': 'no-cache'}

    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    return response.read()

# holds already-looked up mobile carriers
_carriers = {}

@callsback
def get_carrier(yahoo, sms_number, callback = None):
    '''
    Uses a Yahoo webservice to find a carrier string (like 'pcsms.us.version') for
    a mobile phone number.

    Requires Yahoo web cookies (in the yahoo.cookie_str property).

    These carrier strings can be used to send SMS messages through the Yahoo servers
    (see the send_sms function below).
    '''

    # has this number's carrier already been looked up?
    global _carriers
    if sms_number in _carriers:
        return callback.success(_carriers[sms_number])

    # options for the request
    version = '8.1.0.209'
    intl    = 'us'

    # build request XML
    validate = tag('validate', intl = intl, version = version, qos = '0')
    validate.mobile_no['msisdn'] = sms_number
    validate._cdata = '\n'

    # setup callbacks
    def on_response(validate):
        log.info('HTTP response to get_carrier:\n%s', validate._to_xml())

        status = unicode(validate.mobile_no.status)

        log.info('<status> tag contents: %s', status)

        if status == 'Valid':
            # got a valid carrier string; memoize it and return to the success callback.
            carrier = str(validate.mobile_no.carrier)
            _carriers[sms_number] = carrier
            log.info('carrier for %s: %s', sms_number, carrier)
            return callback.success(carrier)

        elif status == 'Unknown':
            log.critical('unknown carrier for %s', sms_number)
            return callback.error()

        else:
            log.critical('unknown XML returned from mobile carrier lookup service')
            return callback.error()

    def on_error(validate):
        log.critical('could not connect to mobile carrier lookup web service')
        return callback.error()

    # setup HTTP POST
    url = 'http://validate.msg.yahoo.com/mobileno?intl=%s&version=%s' % (intl, version)

    headers = {'Cookie':         yahoo.cookie_str,
               'User-Agent':    'Mozilla/4.0 (compatible; MSIE 5.5)',
               'Cache-Control': 'no-cache'}

    log.info('POSTing SMS carrier request to %s', url)
    xmlstr = validate._to_xml(self_closing = False, pretty = False)
    log.info(xmlstr)

    # POST
    post_xml(url, xmlstr, success = on_response, error = on_error, **headers)
    '''
    POST /mobileno?intl=us&version=8.1.0.209 HTTP/1.1
    Cookie: T=z=Vr0OGBVxJPGB9u7bOG1linxMjI2BjUyNjA2NU81NzA-&a=QAE&sk=DAAGhaQDlIYJTS&d=c2wBTlRVeEFUSTFNVGN4TWpneU1EYy0BYQFRQUUBenoBVnIwT0dCZ1dBAXRpcAFCV0JvaUE-; path=/; domain=.yahoo.com; Y=v=1&n=50s9nph28dhu3&l=386i1oqs/o&p=m2g0e3d012000000&r=g6&lg=us&intl=us&np=1; path=/; domain=.yahoo.com ;B=a6d0ooh2qsp2r&b=3&s=ko
    User-Agent: Mozilla/4.0 (compatible; MSIE 5.5)
    Host: validate.msg.yahoo.com
    Content-Length: 105
    Cache-Control: no-cache

    <validate intl="us" version="8.1.0.209" qos="0"><mobile_no msisdn="17248406085"></mobile_no>
    </validate>
    '''

    success = \
    '''
    HTTP/1.1 200 OK
    Date: Fri, 04 May 2007 15:09:26 GMT
    P3P: policyref="http://p3p.yahoo.com/w3c/p3p.xml", CP="CAO DSP COR CUR ADM DEV TAI PSA PSD IVAi IVDi CONi TELo OTPi OUR DELi SAMi OTRi UNRi PUBi IND PHY ONL UNI PUR FIN COM NAV INT DEM CNT STA POL HEA PRE GOV"
    Content-Length: 140
    Connection: close
    Content-Type: text/html

    <validate>
      <mobile_no msisdn="17248406085">
        <status>Valid</status>
        <carrier>pcsms.us.verizon</carrier>
      </mobile_no>
    </validate>
    '''

    error = \
    '''
    HTTP/1.1 200 OK
    Date: Fri, 04 May 2007 15:12:19 GMT
    P3P: policyref="http://p3p.yahoo.com/w3c/p3p.xml", CP="CAO DSP COR CUR ADM DEV TAI PSA PSD IVAi IVDi CONi TELo OTPi OUR DELi SAMi OTRi UNRi PUBi IND PHY ONL UNI PUR FIN COM NAV INT DEM CNT STA POL HEA PRE GOV"
    Content-Length: 117
    Connection: close
    Content-Type: text/html

    <validate>
      <mobile_no msisdn="12">
        <status>Unknown</status>
        <carrier></carrier>
      </mobile_no>
    </validate>
    '''

@callsback
def send_sms(yahoo, sms_number, message, callback = None):
    try:
        if isinstance(message, unicode):
            message = message.encode('utf-8')

        sms_number = format_smsnumber(sms_number)

        def on_carrier(carrier):
            log.info('sending Yahoo SMS packet to %s on carrier %s', sms_number, carrier)

            me = yahoo.self_buddy

            yahoo.send('sms_message', 'available', [
                       'frombuddy',   me.name,
                       'sms_alias',   me.remote_alias or me.name,
                       'to',          sms_number,
                       'sms_carrier', carrier,
                       'message',     message])

        get_carrier(yahoo, sms_number, success = on_carrier, error = callback.error)


    except:
        print_exc()

    callback.success()

def format_smsnumber(sms):
    'Yahoo carrier lookup/sms send requires a 1 in front of US numbers.'

    #TODO: international rules?

    if len(sms) == 10:
        return '1' + sms

    return sms


if __name__ == '__main__':

    cookies = {'Y':'v=1&n=3lutd2l220eoo&l=a4l8dm0jj4hisqqv/o&p=m2l0e8v002000000&r=fr&lg=us&intl=us; path=/; domain=.yahoo.com',
               'T':'z=/V2OGB/bLPGB9ZlmrY27n5q&a=YAE&sk=DAAcD2qurh0ujr&d=YQFZQUUBb2sBWlcwLQF0aXABQldCb2lBAXp6AS9WMk9HQmdXQQ--; path=/; domain=.yahoo.com'}

    headers = {
        'Cookie': '; '.join([cookies['Y'], cookies['T']]),
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5)',
        'Cache-Control': 'no-cache',
    }

    data = '<validate intl="us" version="8.1.0.209" qos="0"><mobile_no msisdn="17248406085"></mobile_no></validate>'

    conn = httplib.HTTPConnection("validate.msg.yahoo.com",80)
    conn.set_debuglevel(   10000 )
    conn.request('POST','/mobileno?intl=us&version=8.1.0.209', data, headers)

    resp = conn.getresponse()
    print resp.status, resp.reason
    if resp.status == 200:
        print resp.read()
