'''

Information specific to creating accounts on the different protocols.


'''

from util.primitives.mapping import ostorage as oS, Storage as S, dictadd, odict
from util.primitives.structures import enum, oset as set
from util.introspect import import_function
from threading import RLock

jcrypt_opts = enum('Use TLS if Possible',
                   'Require TLS',
                   'Force SSL',
                   'No Encryption')

jabber_details = [
    {'type':'enum',
     'store':'encryption',
     'elements':jcrypt_opts},
    {'type':'bool',
     'store':'ignore_ssl_warnings',
     'label':'Ignore SSL Warnings'},
    {'type':'bool',
     'store':'allow_plaintext',
     'label':'Allow Plaintext Login'},
]


jabber_defaults = {
   'encryption': jcrypt_opts['Use TLS if Possible'],
   'ignore_ssl_warnings': False,
   'allow_plaintext': True,
   'autologin': False,
   'server': ('', 5222),
   'block_unknowns': False,
   'hide_os':False,
   'dataproxy':'',
}

jabber_statuses = [[N_('Available'),N_('Free For Chat')],
                   [N_('Away'),N_('Do Not Disturb'),N_('Extended Away')]]

alt_gtalk_opts = [dict(server=('talk.google.com', 443),
                       do_tls= False,
                       require_tls= False,
                       verify_tls_peer= False,
                       do_ssl = True,),
                  dict(server=('talk.google.com',80),
                       do_tls= True,
                       require_tls= True,
                       verify_tls_peer= False,
                       do_ssl = False,),
                  dict(server=('talk.google.com', 5223),
                       do_tls= False,
                       require_tls= False,
                       verify_tls_peer= False,
                       do_ssl = True,),
                  ]

gtalk_alt_conn_lock = RLock()

email_defaults = dict(
  updatefreq = 300,
)

smtp_defaults = dict(
        smtp_port = 25,
        smtp_port_ssl = 465,
        smtp_require_ssl  = False,
        smtp_server = '',
        smtp_username = '',
        smtp_password = u'',
        email_address = '',
)

pop_defaults = dict(popport     = 110,
                    popport_ssl = 995,
                    require_ssl = False)

imap_defaults = dict(imapport         = 143,
                     imapport_ssl     = 993,
                     default_ssl_port = 993, #TODO: replace uses of this with the more standardly named imapport_ssl
                     require_ssl      = False)

update_mixin_opts   = set(['enabled', 'updatefreq', 'alias'])
email_accounts_opts = update_mixin_opts
smtp_acct_opts      = email_accounts_opts | set('smtp_server smtp_port smtp_require_ssl smtp_username email_address'.split())
imap_acct_opts      = smtp_acct_opts | set('imapserver imapport require_ssl'.split())
social_net_opts     = update_mixin_opts - set(['updatefreq'])

protocols = oS()

protocols.digsby = S(
      service_provider = 'dotsyntax',
      name = 'Digsby',
      name_truncated = 'digs',
      path = 'digsby.protocol',
      username_desc = 'Digsby ID',
      newuser_url = 'http://www.digsby.com',
      password_url = 'http://www.digsby.com',
      form = 'jabber',
      more_details = jabber_details,
      defaults = dictadd(jabber_defaults,
                          {'priority': 5,
                           'resource': 'Digsby'}),
      statuses = [['Available'],['Away']],
      type='im',
      allow_contact_add = False,
   )

def compatible(*protos):
    for p1 in protos:
        for p2 in protos:
            compat = protocols[p1].setdefault('compatible', set())
            compat.add(p2)

def protos_of_type(s):
    return odict((k,v) for (k,v) in protocols.items() if v.get('component_type', v.get('type', None)) == s)

def is_compatible(one, theother):
    '''
    returns True iff one is compatible with theother. this is not necessarily commutative
    '''
    return theother in protocols[one].compatible

def proto_init(proto_name):
    return import_function(protocols[proto_name].path)

improtocols = odict()
emailprotocols = odict()
socialprotocols = odict()

def proto_update_types():
    global protocols
    global improtocols
    global emailprotocols
    global socialprotocols
    improtocols.update(     protos_of_type('im')     )
    emailprotocols.update(  protos_of_type('email')  )
    socialprotocols.update( protos_of_type('social') )

    improtocols.pop('digsby', None) #incase updates do something funny.

    popularity_key = lambda d: d.get('popularity') #default None

    improtocols.sort_values(key=popularity_key, reverse=True)
    emailprotocols.sort_values(key=popularity_key, reverse=True)
    socialprotocols.sort_values(key=popularity_key, reverse=True)

    global fix_shortname
    fix_shortname = dict((v.name_truncated, k) for k,v in protocols.items())

    # make sure protos can talk to themselves
    for name, proto in protocols.items():
        proto['compatible'] = set(proto.setdefault('compatible', ()))
        proto['compatible'].add(name)

    # given a service, which services can we talk to?
    global SERVICE_MAP
    SERVICE_MAP = dict((k, sorted(protocols[k].get('compatible', []), key=(lambda x: x!=k))) for k in protocols)

    # given a buddy service, which protocols can talk to it
    global REVERSE_SERVICE_MAP
    REVERSE_SERVICE_MAP = RSM = dict()
    for k in SERVICE_MAP.keys():

        for i in SERVICE_MAP[k]:
            if i not in RSM:
                RSM[i] = []
            if k not in RSM[i]:
                RSM[i].append(k)

proto_update_types()

_name_exceptions = {
                    'msn'    :'MSN Messenger',
                    'yahoo'  :'Yahoo Messenger',
                    'ymail'  :'Yahoo Mail',
                    'aolmail':'AOL Mail',
                    'pop'    :'POP',
                    'imap'   :'IMAP',
                    }
def nice_name_for_proto(proto):
    '''
    Get the user-displayable name for a protocol.
    This is currently only used by Facebook & MySpace 'achievement' modules for putting the name
    of the services on the web (in newsfeeds, etc).
    '''
    return _name_exceptions.get(proto, protocols.get(proto, {}).get('name', proto))

_icon_exceptions = {
                    'imap'   :'email',
                    'pop'    :'email',
                    'aolmail':'aol',
                    'msim'   :'myspace',

                    'tw20'   :'twitter',
                    'fb20'   :'facebook',
                    }

_icon_location = "http://img.digsby.com/service/64/%s.png"
def web_icon_url(proto):
    return _icon_location % _icon_exceptions.get(proto, proto)

