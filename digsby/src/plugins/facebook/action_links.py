import util.net
from util.primitives.structures import oset
from util.primitives.mapping import odict
import branding
UrlQuery = util.net.UrlQuery

__all__ = []

def BASE():
    return UrlQuery('http://www.digsby.com/')

#def STATUS_CAMPAIGN():
#    return UrlQuery(BASE(), utm_medium='fb', utm_campaign='fbstatus')

def NEWSFEED_CAMPAIGN():
    campaign = branding.get('digsby.facebook.newsfeed.campaign', 'digsby_facebook', 'fbnewsfeed')
    return UrlQuery(BASE(), utm_medium='fb', utm_campaign=campaign)

#ACTION_LINKS1 =[
#    [('Sent using Digsby', UrlQuery(STATUS_CAMPAIGN, utm_source='fbVIA',     utm_term='VIA'))],
#    [('Download Digsby',   UrlQuery(STATUS_CAMPAIGN, utm_source='fbDL',      utm_term='DL' ))],
#    [('Get Digsby',        UrlQuery(STATUS_CAMPAIGN, utm_source='fbGET',     utm_term='GET'))],
#    * Two action links v1:
#    [('Sent using Digsby', UrlQuery(STATUS_CAMPAIGN, utm_source='fbBothDL',  utm_term='VIA')),
#     ('Download Digsby',   UrlQuery(STATUS_CAMPAIGN, utm_source='fbBothDL',  utm_term='DL' ))],
#    * Two action links v2
#    [('Sent using Digsby', UrlQuery(STATUS_CAMPAIGN, utm_source='fbBothGet', utm_term='VIA')),
#     ('Get Digsby',        UrlQuery(STATUS_CAMPAIGN, utm_source='fbBothGet', utm_term='GET'))],
#    ]

#ACTION_LINKS = [[dict(text=text, href=href) for text,href in l] for l in ACTION_LINKS1]

def MERGED_URL():
    return UrlQuery(NEWSFEED_CAMPAIGN(), utm_source='merged')

def ACCT_BASE(protocol):
    return UrlQuery(NEWSFEED_CAMPAIGN(), utm_source=str(protocol))

def COUNT_BASE(type_):
    return UrlQuery(NEWSFEED_CAMPAIGN(), utm_source=type_)

def clicksrc(base, source):
    return UrlQuery(base, utm_term=source)

protocol_ordering = oset(['fbchat', 'facebook'])

def get_acct_name(protocol):
    from common import protocolmeta
    return protocolmeta.nice_name_for_proto(protocol)

def get_accts_text(type_=''):
    from common import profile, protocolmeta
    protos = oset(a.protocol for a in getattr(profile.account_manager, type_ + 'accounts'))
    protos = (protocol_ordering & protos) | protos
    return ', '.join(protocolmeta.nice_name_for_proto(name) for name in protos)

def get_acct_properties(href):
    s_text  = get_accts_text('social')
    im_text = get_accts_text('')
    e_text  = get_accts_text('email')
    props = odict()

    if s_text:
        props['Social Networks'] = {'text': s_text,
                                    'href': clicksrc(href, 'SOCIAL')}
    if im_text:
        props['IM Accounts']     = {'text': im_text,
                                    'href': clicksrc(href, 'IM')}
    if e_text:
        props['Email Accounts']  = {'text': e_text,
                                    'href': clicksrc(href, 'EMAIL')}
    assert props
    return props

def his_her_their(s):
    if s == 'female': return 'her'
    elif s == 'male': return 'his'
    else: return 'their'
