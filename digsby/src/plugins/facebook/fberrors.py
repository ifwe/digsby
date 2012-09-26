class FacebookError(Exception):
    def __init__(self, tag):
        self.tag = tag
        self.code = int(self.tag.error_code) if self.tag.error_code else 0
        Exception.__init__(self)
    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, ' '.join('%s=%r' % i for i in vars(self).items()))

    @property
    def message(self):
        return self.tag.error_msg

class FacebookGraphError(FacebookError):
    def __init__(self, data):
        Exception.__init__(self)
        self.__dict__.update(data)

class FacebookParseFail(FacebookError):
    def __init__(self, msg):
        self.msg = msg
    def __repr__(self):
        return repr(self.msg)


error_codes = \
{
#>>> b = lxml.html.parse('http://fbdevwiki.com/wiki/Error_codes')
#>>> tables = b.xpath("//table[@class='error_codes']")
#>>> sections = b.xpath('//li[@class="toclevel-2"]/a[span]/span[@class="toctext"]/text()')
#>>> res = res = zip(sections, (dict((int(tr.findall('td')[0].text.strip()), (''.join([tr.findall('td')[2].text]) + ' '.join(tr.findall('td')[2].xpath('*/text()'))).strip()) for tr in t.findall('tr')[1:]) for t in tables))
#>>> for section_name, errors in res:
#...     print "#", section_name
#...     for k,v in sorted(errors.items()):
#...         print "%5d: '%s'," % (k,v)


# General Errors
    0: 'Success',
    1: 'An unknown error occurred',
    2: 'Service temporarily unavailable',
    3: 'Unknown method',
    4: 'Application request limit reached',
    5: 'Unauthorized source IP address',
    6: 'This method must run on api.facebook.com',
    7: 'This method must run on api-video.facebook.com',
    8: 'This method requires an HTTPS connection',
    9: 'User is performing too many actions',
   10: 'Application does not have permission for this action',
   11: 'This method is deprecated',
   12: 'This API version is deprecated',
# Parameter Errors
  100: 'Invalid parameter',
  101: 'Invalid API key',
  102: 'Session key invalid or no longer valid',
  103: 'Call_id must be greater than previous',
  104: 'Incorrect signature',
  105: 'The number of parameters exceeded the maximum for this operation',
  110: 'Invalid user id',
  111: 'Invalid user info field',
  112: 'Invalid user field',
  113: 'Invalid email',
  120: 'Invalid album id',
  121: 'Invalid photo id',
  130: 'Invalid feed publication priority',
  140: 'Invalid category',
  141: 'Invalid subcategory',
  142: 'Invalid title',
  143: 'Invalid description',
  144: 'Malformed JSON string',
  150: 'Invalid eid',
  151: 'Unknown city',
  152: 'Invalid page type',
# User Permission Errors
  200: 'Permissions error',
  210: 'User not visible',
  211: 'Application has no developers.',
  220: 'Album or albums not visible',
  221: 'Photo not visible',
  230: 'Permissions disallow message to user',
  240: 'Desktop applications cannot set FBML for other users',
  250: 'Updating status requires the extended permission status_update',
  260: 'Modifying existing photos requires the extended permission photo_upload',
  270: 'Permissions disallow sms to user.',
  280: 'Creating and modifying listings requires the extended permission create_listing',
  281: 'Managing notes requires the extended permission create_note.',
  282: 'Managing shared items requires the extended permission share_item.',
  290: 'Creating and modifying events requires the extended permission create_event',
  291: 'FBML Template isn\'t owned by your application.',
  292: 'An application is only allowed to send LiveMessages to users who have accepted the TOS for that application.',
  299: 'RSVPing to events requires the extended permission create_rsvp',
# Data Editing Errors
  300: 'Edit failure',
  310: 'User data edit failure',
  320: 'Photo edit failure',
  321: 'Album is full',
  322: 'Invalid photo tag subject',
  323: 'Cannot tag photo already visible on Facebook',
  324: 'Missing or invalid image file',
  325: 'Too many unapproved photos pending',
  326: 'Too many photo tags pending',
  327: 'Input array contains a photo not in the album',
  328: 'Input array has too few photos',
  329: 'Template data must be a JSON-encoded dictionary, of the form {\'key-1\': \'value-1\', \'key-2\': \'value-2\', ...}',
  330: 'Failed to set markup',
  340: 'Feed publication request limit reached',
  341: 'Feed action request limit reached',
  342: 'Feed story title can have at most one href anchor',
  343: 'Feed story title is too long',
  344: 'Feed story title can have at most one fb:userlink and must be of the user whose action is being reported',
  345: 'Feed story title rendered as blank',
  346: 'Feed story body is too long',
  347: 'Feed story photo could not be accessed or proxied',
  348: 'Feed story photo link invalid',
  350: 'Video file is too large',
  351: 'Video file was corrupt or invalid',
  352: 'Video file format is not supported',
  360: 'Feed story title_data argument was not a valid JSON-encoded array',
  361: 'Feed story title template either missing required parameters, or did not have all parameters defined in title_data array',
  362: 'Feed story body_data argument was not a valid JSON-encoded array',
  363: 'Feed story body template either missing required parameters, or did not have all parameters defined in body_data array',
  364: 'Feed story photos could not be retrieved, or bad image links were provided',
  365: 'The template for this story does not match any templates registered for this application',
  366: 'One or more of the target ids for this story are invalid. They must all be ids of friends of the acting user',
  370: 'The email address you provided is not a valid email address',
  371: 'The email address you provided belongs to an existing account',
  372: 'The birthday provided is not valid',
  373: 'The password provided is too short or weak',
  374: 'The login credential you provided is invalid.',
  375: 'Failed to send confirmation message to the specified login credential.',
  376: 'The login credential you provided belongs to an existing account',
  377: 'Sorry, we were unable to process your registration.',
  378: 'Your password cannot be blank.  Please try another.',
  379: 'Your password contains invalid characters.  Please try another.',
  380: 'Your password must be at least 6 characters long.  Please try another.',
  381: 'Your password should be more secure.  Please try another.',
  382: 'Our automated system will not approve this name.',
  383: 'You must fill in all of the fields.',
  384: 'You must indicate your full birthday to register.',
  385: 'Please enter a valid email address.',
  386: 'The email address you entered has been disabled. Please contact disabled@facebook.com with any questions.',
  387: 'There was an error with your registration. Please try registering again.',
  388: 'Please select either Male or Female.',
# Authentication Errors
  400: 'Invalid email address',
  401: 'Invalid username or password',
  402: 'Invalid application auth sig',
  403: 'Invalid timestamp for authentication',
# Session Errors
  450: 'Session key specified has passed its expiration time',
  451: 'Session key specified cannot be used to call this method',
  452: 'Session key invalid. This could be because the session key has an incorrect format, or because the user has revoked this session',
  453: 'A session key is required for calling this method',
  454: 'A session key must be specified when request is signed with a session secret',
  455: 'A session secret is not permitted to be used with this type of session key',
# Application Messaging Errors
  500: 'Message contains banned content',
  501: 'Missing message body',
  502: 'Message is too long',
  503: 'User has sent too many messages',
  504: 'Invalid reply thread id',
  505: 'Invalid message recipient',
  510: 'Invalid poke recipient',
  511: 'There is a poke already outstanding',
  512: 'User is poking too fast',
# FQL Errors
  600: 'An unknown error occurred in FQL',
  601: 'Error while parsing FQL statement',
  602: 'The field you requested does not exist',
  603: 'The table you requested does not exist',
  604: 'Your statement is not indexable',
  605: 'The function you called does not exist',
  606: 'Wrong number of arguments passed into the function',
  607: 'FQL field specified is invalid in this context.',
  608: 'An invalid session was specified',
# Ref Errors
  700: 'Unknown failure in storing ref data. Please try again.',
# Application Integration Errors
  750: 'Unknown Facebook application integration failure.',
  751: 'Fetch from remote site failed.',
  752: 'Application returned no data.  This may be expected or represent a connectivity error.',
  753: 'Application returned user had invalid permissions to complete the operation.',
  754: 'Application returned data, but no matching tag found.  This may be expected.',
  755: 'The database for this object failed.',
# Data Store API Errors
  800: 'Unknown data store API error',
  801: 'Invalid operation',
  802: 'Data store allowable quota was exceeded',
  803: 'Specified object cannot be found',
  804: 'Specified object already exists',
  805: 'A database error occurred. Please try again',
  806: 'Unable to add FBML template to template database.  Please try again.',
  807: 'No active template bundle with that ID or handle exists.',
  808: 'Template bundle handles must contain less than or equal to 32 characters.',
  809: 'Template bundle handle already identifies a previously registered template bundle, and handles can not be reused.',
  810: 'Application has too many active template bundles, and some must be deactivated before new ones can be registered.',
  811: 'One of more of the supplied action links was improperly formatted.',
  812: 'One or more of your templates is using a token reserved by Facebook, such as {*mp3*} or {*video*}.',
# Mobile/SMS Errors
  850: 'Invalid sms session.',
  851: 'Invalid sms message length.',
  852: 'Over user daily sms quota.',
  853: 'Unable to send sms to user at this time.',
  854: 'Over application daily sms quota/rate limit.',
  855: 'User is not registered for Facebook Mobile Texts',
  856: 'User has SMS notifications turned off',
  857: 'SMS application disallowed by mobile operator',
# Application Information Errors
  900: 'No such application exists.',
# Batch API Errors
  950: 'Each batch API can not contain more than 20 items',
  951: 'begin_batch already called, please make sure to call end_batch first.',
  952: 'end_batch called before begin_batch.',
  953: 'This method is not allowed in batch mode.',
# Events API Errors
 1000: 'Invalid time for an event.',
# Info Section Errors
 1050: 'No information has been set for this user',
 1051: 'Setting info failed. Check the formatting of your info fields.',
# LiveMessage Errors
 1100: 'An error occurred while sending the LiveMessage.',
 1101: 'The event_name parameter must be no longer than 128 bytes.',
 1102: 'The message parameter must be no longer than 1024 bytes.',
# Chat Errors
 1200: 'An error occurred while sending the message.',
# Facebook Page Errors
 1201: 'You have created too many pages',
# Facebook Links Errors
 1500: 'The url you supplied is invalid',
# Facebook Notes Errors
 1600: 'The user does not have permission to modify this note.',
# Comment Errors
 1700: 'An unknown error has occurred.',
 1701: 'The specified post was too long.',
 1702: 'The comments database is down.',
 1703: 'The specified xid is not valid. xids can only contain letters, numbers, and underscores',
 1704: 'The specified user is not a user of this application',
 1705: 'There was an error during posting.',

}
