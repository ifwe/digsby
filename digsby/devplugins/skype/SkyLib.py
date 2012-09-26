#__LICENSE_GOES_HERE__

# -*- coding: utf-8 -*-
# module skylib
from skypekit import *

class ContactGroup(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "ContactGroup %s" % (self.object_id, )
  module_id = 10
  def OnPropertyChange(self, property_name): pass
  TYPE= {
    1 :'ALL_KNOWN_CONTACTS',
    2 :'ALL_BUDDIES',
    3 :'SKYPE_BUDDIES',
    4 :'SKYPEOUT_BUDDIES',
    5 :'ONLINE_BUDDIES',
    6 :'UNKNOWN_OR_PENDINGAUTH_BUDDIES',
    7 :'RECENTLY_CONTACTED_CONTACTS',
    8 :'CONTACTS_WAITING_MY_AUTHORIZATION',
    9 :'CONTACTS_AUTHORIZED_BY_ME',
    10:'CONTACTS_BLOCKED_BY_ME',
    11:'UNGROUPED_BUDDIES',
    12:'CUSTOM_GROUP',
    13:'PROPOSED_SHARED_GROUP',
    14:'SHARED_GROUP',
    15:'EXTERNAL_CONTACTS',
    'ALL_KNOWN_CONTACTS'                                : 1,
    'ALL_BUDDIES'                                       : 2,
    'SKYPE_BUDDIES'                                     : 3,
    'SKYPEOUT_BUDDIES'                                  : 4,
    'ONLINE_BUDDIES'                                    : 5,
    'UNKNOWN_OR_PENDINGAUTH_BUDDIES'                    : 6,
    'RECENTLY_CONTACTED_CONTACTS'                       : 7,
    'CONTACTS_WAITING_MY_AUTHORIZATION'                 : 8,
    'CONTACTS_AUTHORIZED_BY_ME'                         : 9,
    'CONTACTS_BLOCKED_BY_ME'                            :10,
    'UNGROUPED_BUDDIES'                                 :11,
    'CUSTOM_GROUP'                                      :12,
    'PROPOSED_SHARED_GROUP'                             :13,
    'SHARED_GROUP'                                      :14,
    'EXTERNAL_CONTACTS'                                 :15
  }

  def _Gettype(self):
    return ContactGroup.TYPE[self._Property("ZG\233\001]\012",155, True)]
  type = property(_Gettype)
  propid2label[155] = "type"
  def _Getcustom_group_id(self):
    return self._Property("ZG\232\001]\012",154, True)
  custom_group_id = property(_Getcustom_group_id)
  propid2label[154] = "custom_group_id"
  def _Getgiven_displayname(self):
    return self._Property("ZG\227\001]\012",151, True)
  given_displayname = property(_Getgiven_displayname)
  propid2label[151] = "given_displayname"
  def _Getnrofcontacts(self):
    return self._Property("ZG\230\001]\012",152, True)
  nrofcontacts = property(_Getnrofcontacts)
  propid2label[152] = "nrofcontacts"
  def _Getnrofcontacts_online(self):
    return self._Property("ZG\231\001]\012",153, True)
  nrofcontacts_online = property(_Getnrofcontacts_online)
  propid2label[153] = "nrofcontacts_online"

  def GiveDisplayName(
    self,
    name
    ):
    request = XCallRequest("ZR\012\001",10,1)
    request.AddParm('O',0,self)
    request.AddParm('S',1,name)
    response = self.transport.Xcall(request)
  def Delete(self):
    request = XCallRequest("ZR\012\002",10,2)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def GetConversations(self):
    request = XCallRequest("ZR\012\003",10,3)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = [module_id2classes[18](oid,self.transport) for oid in response.get(1,[])]
    return result
  def CanAddConversation(
    self,
    conversation
    ):
    request = XCallRequest("ZR\012\004",10,4)
    request.AddParm('O',0,self)
    request.AddParm('O',1,conversation)
    response = self.transport.Xcall(request)
  def AddConversation(
    self,
    conversation
    ):
    request = XCallRequest("ZR\012\005",10,5)
    request.AddParm('O',0,self)
    request.AddParm('O',1,conversation)
    response = self.transport.Xcall(request)
  def CanRemoveConversation(self):
    request = XCallRequest("ZR\012\006",10,6)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def RemoveConversation(
    self,
    conversation
    ):
    request = XCallRequest("ZR\012\007",10,7)
    request.AddParm('O',0,self)
    request.AddParm('O',1,conversation)
    response = self.transport.Xcall(request)
  def OnChangeConversation(
    self,
    conversation
    ): pass
  event_handlers[1] = "OnChangeConversationDispatch"
  def OnChangeConversationDispatch(self, parms):
    cleanparms = module_id2classes[18](parms.get(1),self.transport)
    self.OnChangeConversation(cleanparms)
  def GetContacts(self):
    request = XCallRequest("ZR\012\010",10,8)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = [module_id2classes[2](oid,self.transport) for oid in response.get(1,[])]
    return result
  def CanAddContact(
    self,
    contact
    ):
    request = XCallRequest("ZR\012\011",10,9)
    request.AddParm('O',0,self)
    request.AddParm('O',1,contact)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def AddContact(
    self,
    contact
    ):
    request = XCallRequest("ZR\012\012",10,10)
    request.AddParm('O',0,self)
    request.AddParm('O',1,contact)
    response = self.transport.Xcall(request)
  def CanRemoveContact(self):
    request = XCallRequest("ZR\012\013",10,11)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def RemoveContact(
    self,
    contact
    ):
    request = XCallRequest("ZR\012\014",10,12)
    request.AddParm('O',0,self)
    request.AddParm('O',1,contact)
    response = self.transport.Xcall(request)
  def OnChange(
    self,
    contact
    ): pass
  event_handlers[2] = "OnChangeDispatch"
  def OnChangeDispatch(self, parms):
    cleanparms = module_id2classes[2](parms.get(1),self.transport)
    self.OnChange(cleanparms)
module_id2classes[10] = ContactGroup

class Contact(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Contact %s" % (self.object_id, )
  module_id = 2
  def OnPropertyChange(self, property_name): pass
  TYPE= {0:'UNRECOGNIZED', 'UNRECOGNIZED':0, 1:'SKYPE', 'SKYPE':1, 2:'PSTN', 'PSTN':2, 3:'EMERGENCY_PSTN', 'EMERGENCY_PSTN':3, 4:'FREE_PSTN', 'FREE_PSTN':4, 5:'UNDISCLOSED_PSTN', 'UNDISCLOSED_PSTN':5, 6:'EXTERNAL', 'EXTERNAL':6}
  AUTHLEVEL= {0:'NONE', 'NONE':0, 1:'AUTHORIZED_BY_ME', 'AUTHORIZED_BY_ME':1, 2:'BLOCKED_BY_ME', 'BLOCKED_BY_ME':2}
  AVAILABILITY= {
    0 :'UNKNOWN',
    8 :'PENDINGAUTH',
    9 :'BLOCKED',
    11:'BLOCKED_SKYPEOUT',
    10:'SKYPEOUT',
    1 :'OFFLINE',
    12:'OFFLINE_BUT_VM_ABLE',
    13:'OFFLINE_BUT_CF_ABLE',
    2 :'ONLINE',
    3 :'AWAY',
    4 :'NOT_AVAILABLE',
    5 :'DO_NOT_DISTURB',
    7 :'SKYPE_ME',
    6 :'INVISIBLE',
    14:'CONNECTING',
    15:'ONLINE_FROM_MOBILE',
    16:'AWAY_FROM_MOBILE',
    17:'NOT_AVAILABLE_FROM_MOBILE',
    18:'DO_NOT_DISTURB_FROM_MOBILE',
    20:'SKYPE_ME_FROM_MOBILE',
    'UNKNOWN'                                           : 0,
    'PENDINGAUTH'                                       : 8,
    'BLOCKED'                                           : 9,
    'BLOCKED_SKYPEOUT'                                  :11,
    'SKYPEOUT'                                          :10,
    'OFFLINE'                                           : 1,
    'OFFLINE_BUT_VM_ABLE'                               :12,
    'OFFLINE_BUT_CF_ABLE'                               :13,
    'ONLINE'                                            : 2,
    'AWAY'                                              : 3,
    'NOT_AVAILABLE'                                     : 4,
    'DO_NOT_DISTURB'                                    : 5,
    'SKYPE_ME'                                          : 7,
    'INVISIBLE'                                         : 6,
    'CONNECTING'                                        :14,
    'ONLINE_FROM_MOBILE'                                :15,
    'AWAY_FROM_MOBILE'                                  :16,
    'NOT_AVAILABLE_FROM_MOBILE'                         :17,
    'DO_NOT_DISTURB_FROM_MOBILE'                        :18,
    'SKYPE_ME_FROM_MOBILE'                              :20
  }
  CAPABILITY= {
    0 :'CAPABILITY_VOICEMAIL',
    1 :'CAPABILITY_SKYPEOUT',
    2 :'CAPABILITY_SKYPEIN',
    3 :'CAPABILITY_CAN_BE_SENT_VM',
    4 :'CAPABILITY_CALL_FORWARD',
    5 :'CAPABILITY_VIDEO',
    6 :'CAPABILITY_TEXT',
    7 :'CAPABILITY_SERVICE_PROVIDER',
    8 :'CAPABILITY_LARGE_CONFERENCE',
    9 :'CAPABILITY_COMMERCIAL_CONTACT',
    10:'CAPABILITY_PSTN_TRANSFER',
    11:'CAPABILITY_TEXT_EVER',
    12:'CAPABILITY_VOICE_EVER',
    13:'CAPABILITY_MOBILE_DEVICE',
    14:'CAPABILITY_PUBLIC_CONTACT',
    'CAPABILITY_VOICEMAIL'                              : 0,
    'CAPABILITY_SKYPEOUT'                               : 1,
    'CAPABILITY_SKYPEIN'                                : 2,
    'CAPABILITY_CAN_BE_SENT_VM'                         : 3,
    'CAPABILITY_CALL_FORWARD'                           : 4,
    'CAPABILITY_VIDEO'                                  : 5,
    'CAPABILITY_TEXT'                                   : 6,
    'CAPABILITY_SERVICE_PROVIDER'                       : 7,
    'CAPABILITY_LARGE_CONFERENCE'                       : 8,
    'CAPABILITY_COMMERCIAL_CONTACT'                     : 9,
    'CAPABILITY_PSTN_TRANSFER'                          :10,
    'CAPABILITY_TEXT_EVER'                              :11,
    'CAPABILITY_VOICE_EVER'                             :12,
    'CAPABILITY_MOBILE_DEVICE'                          :13,
    'CAPABILITY_PUBLIC_CONTACT'                         :14
  }
  CAPABILITYSTATUS= {0:'NO_CAPABILITY', 'NO_CAPABILITY':0, 1:'CAPABILITY_MIXED', 'CAPABILITY_MIXED':1, 2:'CAPABILITY_EXISTS', 'CAPABILITY_EXISTS':2}

  def _Gettype(self):
    return Contact.TYPE[self._Property("ZG\312\001]\002",202, True)]
  type = property(_Gettype)
  propid2label[202] = "type"
  def _Getskypename(self):
    return self._Property("ZG\004]\002",4, True)
  skypename = property(_Getskypename)
  propid2label[4] = "skypename"
  def _Getpstnnumber(self):
    return self._Property("ZG\006]\002",6, True)
  pstnnumber = property(_Getpstnnumber)
  propid2label[6] = "pstnnumber"
  def _Getfullname(self):
    return self._Property("ZG\005]\002",5, True)
  fullname = property(_Getfullname)
  propid2label[5] = "fullname"
  def _Getbirthday(self):
    return self._Property("ZG\007]\002",7, True)
  birthday = property(_Getbirthday)
  propid2label[7] = "birthday"
  def _Getgender(self):
    return self._Property("ZG\010]\002",8, True)
  gender = property(_Getgender)
  propid2label[8] = "gender"
  def _Getlanguages(self):
    return self._Property("ZG\011]\002",9, True)
  languages = property(_Getlanguages)
  propid2label[9] = "languages"
  def _Getcountry(self):
    return self._Property("ZG\012]\002",10, True)
  country = property(_Getcountry)
  propid2label[10] = "country"
  def _Getprovince(self):
    return self._Property("ZG\013]\002",11, True)
  province = property(_Getprovince)
  propid2label[11] = "province"
  def _Getcity(self):
    return self._Property("ZG\014]\002",12, True)
  city = property(_Getcity)
  propid2label[12] = "city"
  def _Getphone_home(self):
    return self._Property("ZG\015]\002",13, True)
  phone_home = property(_Getphone_home)
  propid2label[13] = "phone_home"
  def _Getphone_office(self):
    return self._Property("ZG\016]\002",14, True)
  phone_office = property(_Getphone_office)
  propid2label[14] = "phone_office"
  def _Getphone_mobile(self):
    return self._Property("ZG\017]\002",15, True)
  phone_mobile = property(_Getphone_mobile)
  propid2label[15] = "phone_mobile"
  def _Getemails(self):
    return self._Property("ZG\020]\002",16, True)
  emails = property(_Getemails)
  propid2label[16] = "emails"
  def _Gethomepage(self):
    return self._Property("ZG\021]\002",17, True)
  homepage = property(_Gethomepage)
  propid2label[17] = "homepage"
  def _Getabout(self):
    return self._Property("ZG\022]\002",18, True)
  about = property(_Getabout)
  propid2label[18] = "about"
  def _Getavatar_image(self):
    return self._Property("ZG%]\002",37, True)
  avatar_image = property(_Getavatar_image)
  propid2label[37] = "avatar_image"
  def _Getmood_text(self):
    return self._Property("ZG\032]\002",26, True)
  mood_text = property(_Getmood_text)
  propid2label[26] = "mood_text"
  def _Getrich_mood_text(self):
    return self._Property("ZG\315\001]\002",205, True)
  rich_mood_text = property(_Getrich_mood_text)
  propid2label[205] = "rich_mood_text"
  def _Gettimezone(self):
    return self._Property("ZG\033]\002",27, True)
  timezone = property(_Gettimezone)
  propid2label[27] = "timezone"
  def _Getcapabilities(self):
    return self._Property("ZG$]\002",36, True)
  capabilities = property(_Getcapabilities)
  propid2label[36] = "capabilities"
  def _Getprofile_timestamp(self):
    return self._Property("ZG\023]\002",19, True)
  profile_timestamp = property(_Getprofile_timestamp)
  propid2label[19] = "profile_timestamp"
  def _Getnrof_authed_buddies(self):
    return self._Property("ZG\034]\002",28, True)
  nrof_authed_buddies = property(_Getnrof_authed_buddies)
  propid2label[28] = "nrof_authed_buddies"
  def _Getipcountry(self):
    return self._Property("ZG\035]\002",29, True)
  ipcountry = property(_Getipcountry)
  propid2label[29] = "ipcountry"
  def _Getavatar_timestamp(self):
    return self._Property("ZG\266\001]\002",182, True)
  avatar_timestamp = property(_Getavatar_timestamp)
  propid2label[182] = "avatar_timestamp"
  def _Getmood_timestamp(self):
    return self._Property("ZG\267\001]\002",183, True)
  mood_timestamp = property(_Getmood_timestamp)
  propid2label[183] = "mood_timestamp"
  def _Getreceived_authrequest(self):
    return self._Property("ZG\024]\002",20, True)
  received_authrequest = property(_Getreceived_authrequest)
  propid2label[20] = "received_authrequest"
  def _Getauthreq_timestamp(self):
    return self._Property("ZG\031]\002",25, True)
  authreq_timestamp = property(_Getauthreq_timestamp)
  propid2label[25] = "authreq_timestamp"
  def _Getlastonline_timestamp(self):
    return self._Property("ZG#]\002",35, True)
  lastonline_timestamp = property(_Getlastonline_timestamp)
  propid2label[35] = "lastonline_timestamp"
  def _Getavailability(self):
    return Contact.AVAILABILITY[self._Property("ZG\042]\002",34, True)]
  availability = property(_Getavailability)
  propid2label[34] = "availability"
  def _Getdisplayname(self):
    return self._Property("ZG\025]\002",21, True)
  displayname = property(_Getdisplayname)
  propid2label[21] = "displayname"
  def _Getrefreshing(self):
    return self._Property("ZG\026]\002",22, True)
  refreshing = property(_Getrefreshing)
  propid2label[22] = "refreshing"
  def _Getgiven_authlevel(self):
    return Contact.AUTHLEVEL[self._Property("ZG\027]\002",23, True)]
  given_authlevel = property(_Getgiven_authlevel)
  propid2label[23] = "given_authlevel"
  def _Getgiven_displayname(self):
    return self._Property("ZG!]\002",33, True)
  given_displayname = property(_Getgiven_displayname)
  propid2label[33] = "given_displayname"
  def _Getassigned_comment(self):
    return self._Property("ZG\264\001]\002",180, True)
  assigned_comment = property(_Getassigned_comment)
  propid2label[180] = "assigned_comment"
  def _Getlastused_timestamp(self):
    return self._Property("ZG']\002",39, True)
  lastused_timestamp = property(_Getlastused_timestamp)
  propid2label[39] = "lastused_timestamp"
  def _Getauthrequest_count(self):
    return self._Property("ZG)]\002",41, True)
  authrequest_count = property(_Getauthrequest_count)
  propid2label[41] = "authrequest_count"
  def _Getassigned_phone1(self):
    return self._Property("ZG\270\001]\002",184, True)
  assigned_phone1 = property(_Getassigned_phone1)
  propid2label[184] = "assigned_phone1"
  def _Getassigned_phone1_label(self):
    return self._Property("ZG\271\001]\002",185, True)
  assigned_phone1_label = property(_Getassigned_phone1_label)
  propid2label[185] = "assigned_phone1_label"
  def _Getassigned_phone2(self):
    return self._Property("ZG\272\001]\002",186, True)
  assigned_phone2 = property(_Getassigned_phone2)
  propid2label[186] = "assigned_phone2"
  def _Getassigned_phone2_label(self):
    return self._Property("ZG\273\001]\002",187, True)
  assigned_phone2_label = property(_Getassigned_phone2_label)
  propid2label[187] = "assigned_phone2_label"
  def _Getassigned_phone3(self):
    return self._Property("ZG\274\001]\002",188, True)
  assigned_phone3 = property(_Getassigned_phone3)
  propid2label[188] = "assigned_phone3"
  def _Getassigned_phone3_label(self):
    return self._Property("ZG\275\001]\002",189, True)
  assigned_phone3_label = property(_Getassigned_phone3_label)
  propid2label[189] = "assigned_phone3_label"

  def GetType(self):
    request = XCallRequest("ZR\002\001",2,1)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = Contact.TYPE[response.get(1)]
    return result
  def GetIdentity(self):
    request = XCallRequest("ZR\002\002",2,2)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def GetAvatar(self):
    request = XCallRequest("ZR\002\004",2,4)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = (response.get(1,False)),
    result += (response.get(2,'')),
    return result
  def IsMemberOf(
    self,
    group
    ):
    request = XCallRequest("ZR\002\006",2,6)
    request.AddParm('O',0,self)
    request.AddParm('O',1,group)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def IsMemberOfHardwiredGroup(
    self,
    groupType
    ):
    request = XCallRequest("ZR\002\007",2,7)
    request.AddParm('O',0,self)
    request.AddParm('e',1,ContactGroup.TYPE[groupType])
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def SetBlocked(
    self,
    blocked,
    abuse
    ):
    request = XCallRequest("ZR\002\315\002",2,333)
    request.AddParm('O',0,self)
    request.AddParm('b',1,blocked)
    request.AddParm('b',2,abuse)
    response = self.transport.Xcall(request)
  def IgnoreAuthRequest(self):
    request = XCallRequest("ZR\002\025",2,21)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def GiveDisplayName(
    self,
    name
    ):
    request = XCallRequest("ZR\002\012",2,10)
    request.AddParm('O',0,self)
    request.AddParm('S',1,name)
    response = self.transport.Xcall(request)
  def SetBuddyStatus(
    self,
    isMyBuddy,
    syncAuth
    ):
    request = XCallRequest("ZR\002\014",2,12)
    request.AddParm('O',0,self)
    request.AddParm('b',1,isMyBuddy)
    request.AddParm('b',2,syncAuth)
    response = self.transport.Xcall(request)
  def SendAuthRequest(
    self,
    message
    ):
    request = XCallRequest("ZR\002\015",2,13)
    request.AddParm('O',0,self)
    request.AddParm('S',1,message)
    response = self.transport.Xcall(request)
  def HasAuthorizedMe(self):
    request = XCallRequest("ZR\002\016",2,14)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def SetPhoneNumber(
    self,
    num,
    label,
    number
    ):
    request = XCallRequest("ZR\002\017",2,15)
    request.AddParm('O',0,self)
    request.AddParm('u',1,num)
    request.AddParm('S',2,label)
    request.AddParm('S',3,number)
    response = self.transport.Xcall(request)
  def OpenConversation(self):
    request = XCallRequest("ZR\002\021",2,17)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = module_id2classes[18](response.get(1),self.transport)
    return result
  def HasCapability(
    self,
    capability,
    queryServer
    ):
    request = XCallRequest("ZR\002\022",2,18)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Contact.CAPABILITY[capability])
    request.AddParm('b',2,queryServer)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def GetCapabilityStatus(
    self,
    capability,
    queryServer
    ):
    request = XCallRequest("ZR\002\023",2,19)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Contact.CAPABILITY[capability])
    request.AddParm('b',2,queryServer)
    response = self.transport.Xcall(request)
    result  = Contact.CAPABILITYSTATUS[response.get(1)]
    return result
  def RefreshProfile(self):
    request = XCallRequest("ZR\002\024",2,20)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def mget_profile(self):
    self.multiget("ZG\004,\006,\005,\032,\020,\015,\016,\017,\007,\010,\011,\012,\013,\014,\021,\022,\033]\002")
module_id2classes[2] = Contact

class ContactSearch(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "ContactSearch %s" % (self.object_id, )
  module_id = 1
  def OnPropertyChange(self, property_name): pass
  STATUS= {1:'CONSTRUCTION', 'CONSTRUCTION':1, 2:'PENDING', 'PENDING':2, 3:'EXTENDABLE', 'EXTENDABLE':3, 4:'FINISHED', 'FINISHED':4, 5:'FAILED', 'FAILED':5}
  CONDITION= {
    0:'EQ',
    1:'GT',
    2:'GE',
    3:'LT',
    4:'LE',
    5:'PREFIX_EQ',
    6:'PREFIX_GE',
    7:'PREFIX_LE',
    8:'CONTAINS_WORDS',
    9:'CONTAINS_WORD_PREFIXES',
    'EQ'                                                :0,
    'GT'                                                :1,
    'GE'                                                :2,
    'LT'                                                :3,
    'LE'                                                :4,
    'PREFIX_EQ'                                         :5,
    'PREFIX_GE'                                         :6,
    'PREFIX_LE'                                         :7,
    'CONTAINS_WORDS'                                    :8,
    'CONTAINS_WORD_PREFIXES'                            :9
  }

  def _Getcontact_search_status(self):
    return ContactSearch.STATUS[self._Property("ZG\310\001]\001",200, True)]
  contact_search_status = property(_Getcontact_search_status)
  propid2label[200] = "contact_search_status"

  def AddMinAgeTerm(
    self,
    min_age_in_years,
    add_to_subs
    ):
    request = XCallRequest("ZR\001\001",1,1)
    request.AddParm('O',0,self)
    request.AddParm('u',1,min_age_in_years)
    request.AddParm('b',2,add_to_subs)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def AddMaxAgeTerm(
    self,
    max_age_in_years,
    add_to_subs
    ):
    request = XCallRequest("ZR\001\002",1,2)
    request.AddParm('O',0,self)
    request.AddParm('u',1,max_age_in_years)
    request.AddParm('b',2,add_to_subs)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def AddEmailTerm(
    self,
    email,
    add_to_subs
    ):
    request = XCallRequest("ZR\001\003",1,3)
    request.AddParm('O',0,self)
    request.AddParm('S',1,email)
    request.AddParm('b',2,add_to_subs)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def AddLanguageTerm(
    self,
    language,
    add_to_subs
    ):
    request = XCallRequest("ZR\001\004",1,4)
    request.AddParm('O',0,self)
    request.AddParm('S',1,language)
    request.AddParm('b',2,add_to_subs)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def AddStrTerm(
    self,
    prop,
    cond,
    value,
    add_to_subs
    ):
    request = XCallRequest("ZR\001\005",1,5)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(prop,1))
    request.AddParm('e',2,ContactSearch.CONDITION[cond])
    request.AddParm('S',3,value)
    request.AddParm('b',4,add_to_subs)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def AddIntTerm(
    self,
    prop,
    cond,
    value,
    add_to_subs
    ):
    request = XCallRequest("ZR\001\006",1,6)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(prop,1))
    request.AddParm('e',2,ContactSearch.CONDITION[cond])
    request.AddParm('u',3,value)
    request.AddParm('b',4,add_to_subs)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def AddOr(self):
    request = XCallRequest("ZR\001\007",1,7)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def IsValid(self):
    request = XCallRequest("ZR\001\010",1,8)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def Submit(self):
    request = XCallRequest("ZR\001\011",1,9)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Extend(self):
    request = XCallRequest("ZR\001\012",1,10)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Release(self):
    request = XCallRequest("ZR\001\014",1,12)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def GetResults(
    self,
    from_,
    count
    ):
    request = XCallRequest("ZR\001\013",1,11)
    request.AddParm('O',0,self)
    request.AddParm('u',1,from_)
    request.AddParm('u',2,count)
    response = self.transport.Xcall(request)
    result  = [module_id2classes[2](oid,self.transport) for oid in response.get(1,[])]
    return result
  def OnNewResult(
    self,
    contact,
    rankValue
    ): pass
  event_handlers[1] = "OnNewResultDispatch"
  def OnNewResultDispatch(self, parms):
    cleanparms  = (module_id2classes[2](parms.get(1),self.transport)),
    cleanparms += (parms.get(2,0)),
    self.OnNewResult(*cleanparms)
module_id2classes[1] = ContactSearch

class Participant(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Participant %s" % (self.object_id, )
  module_id = 19
  def OnPropertyChange(self, property_name): pass
  RANK= {1:'CREATOR', 'CREATOR':1, 2:'ADMIN', 'ADMIN':2, 3:'SPEAKER', 'SPEAKER':3, 4:'WRITER', 'WRITER':4, 5:'SPECTATOR', 'SPECTATOR':5, 6:'APPLICANT', 'APPLICANT':6, 7:'RETIRED', 'RETIRED':7, 8:'OUTLAW', 'OUTLAW':8}
  TEXT_STATUS= {0:'TEXT_UNKNOWN', 'TEXT_UNKNOWN':0, 1:'TEXT_NA', 'TEXT_NA':1, 2:'READING', 'READING':2, 3:'WRITING', 'WRITING':3, 4:'WRITING_AS_ANGRY', 'WRITING_AS_ANGRY':4, 5:'WRITING_AS_CAT', 'WRITING_AS_CAT':5}
  VOICE_STATUS= {
    0:'VOICE_UNKNOWN',
    1:'VOICE_NA',
    2:'VOICE_AVAILABLE',
    3:'VOICE_CONNECTING',
    4:'RINGING',
    5:'EARLY_MEDIA',
    6:'LISTENING',
    7:'SPEAKING',
    8:'VOICE_ON_HOLD',
    9:'VOICE_STOPPED',
    'VOICE_UNKNOWN'                                     :0,
    'VOICE_NA'                                          :1,
    'VOICE_AVAILABLE'                                   :2,
    'VOICE_CONNECTING'                                  :3,
    'RINGING'                                           :4,
    'EARLY_MEDIA'                                       :5,
    'LISTENING'                                         :6,
    'SPEAKING'                                          :7,
    'VOICE_ON_HOLD'                                     :8,
    'VOICE_STOPPED'                                     :9
  }
  VIDEO_STATUS= {0:'VIDEO_UNKNOWN', 'VIDEO_UNKNOWN':0, 1:'VIDEO_NA', 'VIDEO_NA':1, 2:'VIDEO_AVAILABLE', 'VIDEO_AVAILABLE':2, 3:'VIDEO_CONNECTING', 'VIDEO_CONNECTING':3, 4:'STREAMING', 'STREAMING':4, 5:'VIDEO_ON_HOLD', 'VIDEO_ON_HOLD':5}
  DTMF= {
    0 :'DTMF_0',
    1 :'DTMF_1',
    2 :'DTMF_2',
    3 :'DTMF_3',
    4 :'DTMF_4',
    5 :'DTMF_5',
    6 :'DTMF_6',
    7 :'DTMF_7',
    8 :'DTMF_8',
    9 :'DTMF_9',
    10:'DTMF_STAR',
    11:'DTMF_POUND',
    'DTMF_0'                                            : 0,
    'DTMF_1'                                            : 1,
    'DTMF_2'                                            : 2,
    'DTMF_3'                                            : 3,
    'DTMF_4'                                            : 4,
    'DTMF_5'                                            : 5,
    'DTMF_6'                                            : 6,
    'DTMF_7'                                            : 7,
    'DTMF_8'                                            : 8,
    'DTMF_9'                                            : 9,
    'DTMF_STAR'                                         :10,
    'DTMF_POUND'                                        :11
  }

  def _Getconvo_id(self): #@IndentOk
    return module_id2classes[18](self._Property("ZG\242\007]\023",930, True),self.transport)
  convo_id = property(_Getconvo_id)
  propid2label[930] = "convo_id"
  def _Getidentity(self):
    return self._Property("ZG\243\007]\023",931, True)
  identity = property(_Getidentity)
  propid2label[931] = "identity"
  def _Getrank(self):
    return Participant.RANK[self._Property("ZG\244\007]\023",932, True)]
  rank = property(_Getrank)
  propid2label[932] = "rank"
  def _Getrequested_rank(self):
    return Participant.RANK[self._Property("ZG\245\007]\023",933, True)]
  requested_rank = property(_Getrequested_rank)
  propid2label[933] = "requested_rank"
  def _Gettext_status(self):
    return Participant.TEXT_STATUS[self._Property("ZG\246\007]\023",934, True)]
  text_status = property(_Gettext_status)
  propid2label[934] = "text_status"
  def _Getvoice_status(self):
    return Participant.VOICE_STATUS[self._Property("ZG\247\007]\023",935, True)]
  voice_status = property(_Getvoice_status)
  propid2label[935] = "voice_status"
  def _Getvideo_status(self):
    return Participant.VIDEO_STATUS[self._Property("ZG\250\007]\023",936, True)]
  video_status = property(_Getvideo_status)
  propid2label[936] = "video_status"
  def _Getlive_identity(self):
    return self._Property("ZG\257\007]\023",943, False)
  live_identity = property(_Getlive_identity)
  propid2label[943] = "live_identity"
  def _Getlive_price_for_me(self):
    return self._Property("ZG\252\007]\023",938, True)
  live_price_for_me = property(_Getlive_price_for_me)
  propid2label[938] = "live_price_for_me"
  def _Getlive_fwd_identities(self):
    return self._Property("ZG\264\007]\023",948, True)
  live_fwd_identities = property(_Getlive_fwd_identities)
  propid2label[948] = "live_fwd_identities"
  def _Getlive_start_timestamp(self):
    return self._Property("ZG\253\007]\023",939, True)
  live_start_timestamp = property(_Getlive_start_timestamp)
  propid2label[939] = "live_start_timestamp"
  def _Getsound_level(self):
    return self._Property("ZG\255\007]\023",941, True)
  sound_level = property(_Getsound_level)
  propid2label[941] = "sound_level"
  def _Getdebuginfo(self):
    return self._Property("ZG\256\007]\023",942, False)
  debuginfo = property(_Getdebuginfo)
  propid2label[942] = "debuginfo"
  def _Getlast_voice_error(self):
    return self._Property("ZG\263\007]\023",947, True)
  last_voice_error = property(_Getlast_voice_error)
  propid2label[947] = "last_voice_error"
  def _Getquality_problems(self):
    return self._Property("ZG\265\007]\023",949, True)
  quality_problems = property(_Getquality_problems)
  propid2label[949] = "quality_problems"
  def _Getlive_type(self):
    return SkyLib.IDENTITYTYPE[self._Property("ZG\266\007]\023",950, True)]
  live_type = property(_Getlive_type)
  propid2label[950] = "live_type"
  def _Getlive_country(self):
    return self._Property("ZG\267\007]\023",951, False)
  live_country = property(_Getlive_country)
  propid2label[951] = "live_country"
  def _Gettransferred_by(self):
    return self._Property("ZG\270\007]\023",952, True)
  transferred_by = property(_Gettransferred_by)
  propid2label[952] = "transferred_by"
  def _Gettransferred_to(self):
    return self._Property("ZG\271\007]\023",953, True)
  transferred_to = property(_Gettransferred_to)
  propid2label[953] = "transferred_to"
  def _Getadder(self):
    return self._Property("ZG\272\007]\023",954, True)
  adder = property(_Getadder)
  propid2label[954] = "adder"

  def CanSetRankTo(
    self,
    rank
    ):
    request = XCallRequest("ZR\023\001",19,1)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Participant.RANK[rank])
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def SetRankTo(
    self,
    rank
    ):
    request = XCallRequest("ZR\023\002",19,2)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Participant.RANK[rank])
    response = self.transport.Xcall(request)
  def Ring(
    self,
    identityToUse,
    videoCall,
    nrofRedials,
    redialPeriod,
    autoStartVM,
    origin
    ):
    request = XCallRequest("ZR\023\003",19,3)
    request.AddParm('O',0,self)
    request.AddParm('S',1,identityToUse)
    request.AddParm('b',2,videoCall)
    request.AddParm('u',3,nrofRedials)
    request.AddParm('u',4,redialPeriod)
    request.AddParm('b',5,autoStartVM)
    request.AddParm('S',6,origin)
    response = self.transport.Xcall(request)
  def GetVideo(self):
    request = XCallRequest("ZR\023\004",19,4)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = module_id2classes[11](response.get(1),self.transport)
    return result
  def Hangup(self):
    request = XCallRequest("ZR\023\005",19,5)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Retire(self):
    request = XCallRequest("ZR\023\006",19,6)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def OnIncomingDTMF(
    self,
    dtmf
    ): pass
  event_handlers[1] = "OnIncomingDTMFDispatch"
  def OnIncomingDTMFDispatch(self, parms):
    cleanparms = Participant.DTMF[parms.get(1)]
    self.OnIncomingDTMF(cleanparms)
module_id2classes[19] = Participant

class Conversation(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Conversation %s" % (self.object_id, )
  module_id = 18
  def OnPropertyChange(self, property_name): pass
  TYPE= {1:'DIALOG', 'DIALOG':1, 2:'CONFERENCE', 'CONFERENCE':2, 3:'TERMINATED_CONFERENCE', 'TERMINATED_CONFERENCE':3, 4:'LEGACY_VOICE_CONFERENCE', 'LEGACY_VOICE_CONFERENCE':4, 5:'LEGACY_SHAREDGROUP', 'LEGACY_SHAREDGROUP':5}
  MY_STATUS= {
    1 :'CONNECTING',
    2 :'RETRY_CONNECTING',
    3 :'DOWNLOADING_MESSAGES',
    4 :'QUEUED_TO_ENTER',
    5 :'APPLICANT',
    6 :'APPLICATION_DENIED',
    7 :'INVALID_ACCESS_TOKEN',
    8 :'CONSUMER',
    9 :'RETIRED_FORCEFULLY',
    10:'RETIRED_VOLUNTARILY',
    'CONNECTING'                                        : 1,
    'RETRY_CONNECTING'                                  : 2,
    'DOWNLOADING_MESSAGES'                              : 3,
    'QUEUED_TO_ENTER'                                   : 4,
    'APPLICANT'                                         : 5,
    'APPLICATION_DENIED'                                : 6,
    'INVALID_ACCESS_TOKEN'                              : 7,
    'CONSUMER'                                          : 8,
    'RETIRED_FORCEFULLY'                                : 9,
    'RETIRED_VOLUNTARILY'                               :10
  }
  LOCAL_LIVESTATUS= {
    0 :'NONE',
    1 :'STARTING',
    2 :'RINGING_FOR_ME',
    3 :'IM_LIVE',
    5 :'ON_HOLD_LOCALLY',
    6 :'ON_HOLD_REMOTELY',
    7 :'OTHERS_ARE_LIVE',
    11:'OTHERS_ARE_LIVE_FULL',
    8 :'PLAYING_VOICE_MESSAGE',
    9 :'RECORDING_VOICE_MESSAGE',
    10:'RECENTLY_LIVE',
    12:'TRANSFERRING',
    'NONE'                                              : 0,
    'STARTING'                                          : 1,
    'RINGING_FOR_ME'                                    : 2,
    'IM_LIVE'                                           : 3,
    'ON_HOLD_LOCALLY'                                   : 5,
    'ON_HOLD_REMOTELY'                                  : 6,
    'OTHERS_ARE_LIVE'                                   : 7,
    'OTHERS_ARE_LIVE_FULL'                              :11,
    'PLAYING_VOICE_MESSAGE'                             : 8,
    'RECORDING_VOICE_MESSAGE'                           : 9,
    'RECENTLY_LIVE'                                     :10,
    'TRANSFERRING'                                      :12
  }
  ALLOWED_ACTIVITY= {1:'SET_META', 'SET_META':1, 2:'ADD_CONSUMERS', 'ADD_CONSUMERS':2, 4:'SPEAK', 'SPEAK':4, 8:'SPEAK_AND_WRITE', 'SPEAK_AND_WRITE':8}
  PARTICIPANTFILTER= {0:'ALL', 'ALL':0, 1:'CONSUMERS', 'CONSUMERS':1, 2:'APPLICANTS', 'APPLICANTS':2, 3:'CONSUMERS_AND_APPLICANTS', 'CONSUMERS_AND_APPLICANTS':3, 4:'MYSELF', 'MYSELF':4, 5:'OTHER_CONSUMERS', 'OTHER_CONSUMERS':5}
  LIST_TYPE= {0:'ALL_CONVERSATIONS', 'ALL_CONVERSATIONS':0, 1:'INBOX_CONVERSATIONS', 'INBOX_CONVERSATIONS':1, 2:'BOOKMARKED_CONVERSATIONS', 'BOOKMARKED_CONVERSATIONS':2, 3:'LIVE_CONVERSATIONS', 'LIVE_CONVERSATIONS':3}

  def _Getidentity(self):
    return self._Property("ZG\314\007]\022",972, True)
  identity = property(_Getidentity)
  propid2label[972] = "identity"
  def _Gettype(self):
    return Conversation.TYPE[self._Property("ZG\206\007]\022",902, True)]
  type = property(_Gettype)
  propid2label[902] = "type"
  def _Getlive_host(self):
    return self._Property("ZG\226\007]\022",918, True)
  live_host = property(_Getlive_host)
  propid2label[918] = "live_host"
  def _Getlive_start_timestamp(self):
    return self._Property("ZG\316\007]\022",974, True)
  live_start_timestamp = property(_Getlive_start_timestamp)
  propid2label[974] = "live_start_timestamp"
  def _Getlive_is_muted(self):
    return self._Property("ZG\344\007]\022",996, True)
  live_is_muted = property(_Getlive_is_muted)
  propid2label[996] = "live_is_muted"
  def _Getalert_string(self):
    return self._Property("ZG\230\007]\022",920, True)
  alert_string = property(_Getalert_string)
  propid2label[920] = "alert_string"
  def _Getis_bookmarked(self):
    return self._Property("ZG\231\007]\022",921, True)
  is_bookmarked = property(_Getis_bookmarked)
  propid2label[921] = "is_bookmarked"
  def _Getgiven_displayname(self):
    return self._Property("ZG\235\007]\022",925, True)
  given_displayname = property(_Getgiven_displayname)
  propid2label[925] = "given_displayname"
  def _Getdisplayname(self):
    return self._Property("ZG\234\007]\022",924, True)
  displayname = property(_Getdisplayname)
  propid2label[924] = "displayname"
  def _Getlocal_livestatus(self):
    return Conversation.LOCAL_LIVESTATUS[self._Property("ZG\237\007]\022",927, True)]
  local_livestatus = property(_Getlocal_livestatus)
  propid2label[927] = "local_livestatus"
  def _Getinbox_timestamp(self):
    return self._Property("ZG\240\007]\022",928, True)
  inbox_timestamp = property(_Getinbox_timestamp)
  propid2label[928] = "inbox_timestamp"
  def _Getinbox_message_id(self):
    return module_id2classes[9](self._Property("ZG\315\007]\022",973, True),self.transport)
  inbox_message_id = property(_Getinbox_message_id)
  propid2label[973] = "inbox_message_id"
  def _Getunconsumed_suppressed_messages(self):
    return self._Property("ZG\317\007]\022",975, True)
  unconsumed_suppressed_messages = property(_Getunconsumed_suppressed_messages)
  propid2label[975] = "unconsumed_suppressed_messages"
  def _Getunconsumed_normal_messages(self):
    return self._Property("ZG\320\007]\022",976, True)
  unconsumed_normal_messages = property(_Getunconsumed_normal_messages)
  propid2label[976] = "unconsumed_normal_messages"
  def _Getunconsumed_elevated_messages(self):
    return self._Property("ZG\321\007]\022",977, True)
  unconsumed_elevated_messages = property(_Getunconsumed_elevated_messages)
  propid2label[977] = "unconsumed_elevated_messages"
  def _Getunconsumed_messages_voice(self):
    return self._Property("ZG\312\007]\022",970, True)
  unconsumed_messages_voice = property(_Getunconsumed_messages_voice)
  propid2label[970] = "unconsumed_messages_voice"
  def _Getactive_vm_id(self):
    return module_id2classes[7](self._Property("ZG\313\007]\022",971, True),self.transport)
  active_vm_id = property(_Getactive_vm_id)
  propid2label[971] = "active_vm_id"
  def _Getconsumption_horizon(self):
    return self._Property("ZG\323\007]\022",979, True)
  consumption_horizon = property(_Getconsumption_horizon)
  propid2label[979] = "consumption_horizon"
  def _Getlast_activity_timestamp(self):
    return self._Property("ZG\325\007]\022",981, True)
  last_activity_timestamp = property(_Getlast_activity_timestamp)
  propid2label[981] = "last_activity_timestamp"
  def _Getspawned_from_convo_id(self):
    return module_id2classes[18](self._Property("ZG\223\007]\022",915, True),self.transport)
  spawned_from_convo_id = property(_Getspawned_from_convo_id)
  propid2label[915] = "spawned_from_convo_id"
  def _Getcreator(self):
    return self._Property("ZG\207\007]\022",903, True)
  creator = property(_Getcreator)
  propid2label[903] = "creator"
  def _Getcreation_timestamp(self):
    return self._Property("ZG\210\007]\022",904, True)
  creation_timestamp = property(_Getcreation_timestamp)
  propid2label[904] = "creation_timestamp"
  def _Getmy_status(self):
    return Conversation.MY_STATUS[self._Property("ZG\227\007]\022",919, True)]
  my_status = property(_Getmy_status)
  propid2label[919] = "my_status"
  def _Getopt_joining_enabled(self):
    return self._Property("ZG\232\007]\022",922, True)
  opt_joining_enabled = property(_Getopt_joining_enabled)
  propid2label[922] = "opt_joining_enabled"
  def _Getopt_entry_level_rank(self):
    return Participant.RANK[self._Property("ZG\212\007]\022",906, True)]
  opt_entry_level_rank = property(_Getopt_entry_level_rank)
  propid2label[906] = "opt_entry_level_rank"
  def _Getopt_disclose_history(self):
    return self._Property("ZG\213\007]\022",907, True)
  opt_disclose_history = property(_Getopt_disclose_history)
  propid2label[907] = "opt_disclose_history"
  def _Getopt_admin_only_activities(self):
    return self._Property("ZG\215\007]\022",909, True)
  opt_admin_only_activities = property(_Getopt_admin_only_activities)
  propid2label[909] = "opt_admin_only_activities"
  def _Getpasswordhint(self):
    return self._Property("ZG\324\007]\022",980, True)
  passwordhint = property(_Getpasswordhint)
  propid2label[980] = "passwordhint"
  def _Getmeta_name(self):
    return self._Property("ZG\216\007]\022",910, True)
  meta_name = property(_Getmeta_name)
  propid2label[910] = "meta_name"
  def _Getmeta_topic(self):
    return self._Property("ZG\217\007]\022",911, True)
  meta_topic = property(_Getmeta_topic)
  propid2label[911] = "meta_topic"
  def _Getmeta_guidelines(self):
    return self._Property("ZG\221\007]\022",913, True)
  meta_guidelines = property(_Getmeta_guidelines)
  propid2label[913] = "meta_guidelines"
  def _Getmeta_picture(self):
    return self._Property("ZG\222\007]\022",914, True)
  meta_picture = property(_Getmeta_picture)
  propid2label[914] = "meta_picture"

  SETUPKEY_ENABLE_BIRTHDAY_NOTIFICATION="Lib/Conversation/EnableBirthday"
  SETUPKEY_INBOX_UPDATE_TIMEOUT="Lib/Conversation/InboxUpdateTimeout"
  SETUPKEY_RECENTLY_LIVE_TIMEOUT="Lib/Conversation/RecentlyLiveTimeout"
  SETUPKEY_DISABLE_CHAT="*Lib/Chat/DisableChat"
  SETUPKEY_DISABLE_CHAT_HISTORY="Lib/Message/DisableHistory"
  SETUPKEY_CHAT_HISTORY_DAYS="Lib/Chat/HistoryDays"
  SETUPKEY_DISABLE_CHAT_ACTIVITY_INDICATION="Lib/Chat/DisableActivityIndication"
  SETUPKEY_CALL_NOANSWER_TIMEOUT="Lib/Call/NoAnswerTimeout"
  SETUPKEY_CALL_SEND_TO_VM="Lib/Call/SendToVM"
  SETUPKEY_CALL_APPLY_CF="Lib/Call/ApplyCF"
  SETUPKEY_CALL_EMERGENCY_COUNTRY="Lib/Call/EmergencyCountry"
  def SetOption(
    self,
    propKey,
    value
    ):
    request = XCallRequest("ZR\022\001",18,1)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(propKey,1))
    request.AddParm('u',2,value)
    response = self.transport.Xcall(request)
  def SetTopic(
    self,
    topic,
    isXML
    ):
    request = XCallRequest("ZR\022\002",18,2)
    request.AddParm('O',0,self)
    request.AddParm('S',1,topic)
    request.AddParm('b',2,isXML)
    response = self.transport.Xcall(request)
  def SetGuidelines(
    self,
    guidelines,
    isXML
    ):
    request = XCallRequest("ZR\022\003",18,3)
    request.AddParm('O',0,self)
    request.AddParm('S',1,guidelines)
    request.AddParm('b',2,isXML)
    response = self.transport.Xcall(request)
  def SetPicture(
    self,
    jpeg
    ):
    request = XCallRequest("ZR\022\004",18,4)
    request.AddParm('O',0,self)
    request.AddParm('B',1,jpeg)
    response = self.transport.Xcall(request)
  def SpawnConference(
    self,
    identitiesToAdd
    ):
    request = XCallRequest("ZR\022\006",18,6)
    request.AddParm('O',0,self)
    request.AddParm('S',1,identitiesToAdd)
    response = self.transport.Xcall(request)
    result  = module_id2classes[18](response.get(1),self.transport)
    return result
  def AddConsumers(
    self,
    identities
    ):
    request = XCallRequest("ZR\022\007",18,7)
    request.AddParm('O',0,self)
    request.AddParm('S',1,identities)
    response = self.transport.Xcall(request)
  def Assimilate(
    self,
    otherConversation
    ):
    request = XCallRequest("ZR\022\011",18,9)
    request.AddParm('O',0,self)
    request.AddParm('O',1,otherConversation)
    response = self.transport.Xcall(request)
    result  = module_id2classes[18](response.get(1),self.transport)
    return result
  def JoinLiveSession(
    self,
    accessToken
    ):
    request = XCallRequest("ZR\022\012",18,10)
    request.AddParm('O',0,self)
    request.AddParm('S',1,accessToken)
    response = self.transport.Xcall(request)
  def MuteMyMicrophone(self):
    request = XCallRequest("ZR\022\013",18,11)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def UnmuteMyMicrophone(self):
    request = XCallRequest("ZR\022\014",18,12)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def HoldMyLiveSession(self):
    request = XCallRequest("ZR\022\015",18,13)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def ResumeMyLiveSession(self):
    request = XCallRequest("ZR\022\016",18,14)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def LeaveLiveSession(
    self,
    postVoiceAutoresponse
    ):
    request = XCallRequest("ZR\022\017",18,15)
    request.AddParm('O',0,self)
    request.AddParm('b',1,postVoiceAutoresponse)
    response = self.transport.Xcall(request)
  def StartVoiceMessage(self):
    request = XCallRequest("ZR\022-",18,45)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def TransferLiveSession(
    self,
    identities,
    transferTopic
    ):
    request = XCallRequest("ZR\022(",18,40)
    request.AddParm('O',0,self)
    request.AddParm('S',1,identities)
    request.AddParm('S',2,transferTopic)
    response = self.transport.Xcall(request)
  def CanTransferLiveSession(
    self,
    identity
    ):
    request = XCallRequest("ZR\022.",18,46)
    request.AddParm('O',0,self)
    request.AddParm('S',1,identity)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def SendDTMF(
    self,
    dtmf,
    lengthInMS
    ):
    request = XCallRequest("ZR\022\020",18,16)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Participant.DTMF[dtmf])
    request.AddParm('u',2,lengthInMS)
    response = self.transport.Xcall(request)
  def StopSendDTMF(self):
    request = XCallRequest("ZR\022\060",18,48)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def SetMyTextStatusTo(
    self,
    status
    ):
    request = XCallRequest("ZR\022\022",18,18)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Participant.TEXT_STATUS[status])
    response = self.transport.Xcall(request)
  def PostText(
    self,
    text,
    isXML
    ):
    request = XCallRequest("ZR\022\023",18,19)
    request.AddParm('O',0,self)
    request.AddParm('S',1,text)
    request.AddParm('b',2,isXML)
    response = self.transport.Xcall(request)
    result  = module_id2classes[9](response.get(1),self.transport)
    return result
  def PostContacts(
    self,
    contacts
    ):
    request = XCallRequest("ZR\022\024",18,20)
    request.AddParm('O',0,self)
    request.AddParm('O',1,contacts)
    response = self.transport.Xcall(request)
  def PostFiles(
    self,
    paths,
    body
    ):
    request = XCallRequest("ZR\022\025",18,21)
    request.AddParm('O',0,self)
    request.AddParm('f',1,paths)
    request.AddParm('S',2,body)
    response = self.transport.Xcall(request)
    result  = (SkyLib.TRANSFER_SENDFILE_ERROR[response.get(1)]),
    result += (response.get(2,'')),
    return result
  def PostVoiceMessage(
    self,
    voicemail,
    body
    ):
    request = XCallRequest("ZR\022\026",18,22)
    request.AddParm('O',0,self)
    request.AddParm('O',1,voicemail)
    request.AddParm('S',2,body)
    response = self.transport.Xcall(request)
  def PostSMS(
    self,
    sms,
    body
    ):
    request = XCallRequest("ZR\022\027",18,23)
    request.AddParm('O',0,self)
    request.AddParm('O',1,sms)
    request.AddParm('S',2,body)
    response = self.transport.Xcall(request)
  def GetJoinBlob(self):
    request = XCallRequest("ZR\022\030",18,24)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def Join(self):
    request = XCallRequest("ZR\022\031",18,25)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def EnterPassword(
    self,
    password
    ):
    request = XCallRequest("ZR\022\032",18,26)
    request.AddParm('O',0,self)
    request.AddParm('S',1,password)
    response = self.transport.Xcall(request)
  def SetPassword(
    self,
    password,
    hint
    ):
    request = XCallRequest("ZR\022\033",18,27)
    request.AddParm('O',0,self)
    request.AddParm('S',1,password)
    request.AddParm('S',2,hint)
    response = self.transport.Xcall(request)
  def RetireFrom(self):
    request = XCallRequest("ZR\022\034",18,28)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Delete(self):
    request = XCallRequest("ZR\022/",18,47)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def RenameTo(
    self,
    name
    ):
    request = XCallRequest("ZR\022\035",18,29)
    request.AddParm('O',0,self)
    request.AddParm('S',1,name)
    response = self.transport.Xcall(request)
  def SetBookmark(
    self,
    bookmark
    ):
    request = XCallRequest("ZR\022\036",18,30)
    request.AddParm('O',0,self)
    request.AddParm('b',1,bookmark)
    response = self.transport.Xcall(request)
  def SetAlertString(
    self,
    alertString
    ):
    request = XCallRequest("ZR\022\037",18,31)
    request.AddParm('O',0,self)
    request.AddParm('S',1,alertString)
    response = self.transport.Xcall(request)
  def RemoveFromInbox(self):
    request = XCallRequest("ZR\022 ",18,32)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def AddToInbox(self):
    request = XCallRequest("ZR\022!",18,33)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def SetConsumedHorizon(
    self,
    timestamp,
    also_unconsume
    ):
    request = XCallRequest("ZR\022\042",18,34)
    request.AddParm('O',0,self)
    request.AddParm('u',1,timestamp)
    request.AddParm('b',2,also_unconsume)
    response = self.transport.Xcall(request)
  def MarkUnread(self):
    request = XCallRequest("ZR\022#",18,35)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def IsMemberOf(
    self,
    group
    ):
    request = XCallRequest("ZR\022%",18,37)
    request.AddParm('O',0,self)
    request.AddParm('O',1,group)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def GetParticipants(
    self,
    filter
    ):
    request = XCallRequest("ZR\022&",18,38)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Conversation.PARTICIPANTFILTER[filter])
    response = self.transport.Xcall(request)
    result  = [module_id2classes[19](oid,self.transport) for oid in response.get(1,[])]
    return result
  def GetLastMessages(
    self,
    requireTimestamp
    ):
    request = XCallRequest("ZR\022'",18,39)
    request.AddParm('O',0,self)
    request.AddParm('u',1,requireTimestamp)
    response = self.transport.Xcall(request)
    result  = ([module_id2classes[9](oid,self.transport) for oid in response.get(1,[])]),
    result += ([module_id2classes[9](oid,self.transport) for oid in response.get(2,[])]),
    return result
  def FindMessage(
    self,
    text,
    fromTimestampUp
    ):
    request = XCallRequest("ZR\022)",18,41)
    request.AddParm('O',0,self)
    request.AddParm('S',1,text)
    request.AddParm('u',2,fromTimestampUp)
    response = self.transport.Xcall(request)
    result  = module_id2classes[9](response.get(1),self.transport)
    return result
  def OnParticipantListChange(self): pass
  def OnParticipantListChangeDispatch(self, parms): self.OnParticipantListChange()
  event_handlers[1] = "OnParticipantListChangeDispatch"
  def OnMessage(
    self,
    message
    ): pass
  event_handlers[2] = "OnMessageDispatch"
  def OnMessageDispatch(self, parms):
    cleanparms = module_id2classes[9](parms.get(1),self.transport)
    self.OnMessage(cleanparms)
  def OnSpawnConference(
    self,
    spawned
    ): pass
  event_handlers[3] = "OnSpawnConferenceDispatch"
  def OnSpawnConferenceDispatch(self, parms):
    cleanparms = module_id2classes[18](parms.get(1),self.transport)
    self.OnSpawnConference(cleanparms)
module_id2classes[18] = Conversation

class Message(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Message %s" % (self.object_id, )
  module_id = 9
  def OnPropertyChange(self, property_name): pass
  TYPE= {
    2  :'SET_METADATA',
    4  :'SPAWNED_CONFERENCE',
    10 :'ADDED_CONSUMERS',
    11 :'ADDED_APPLICANTS',
    12 :'RETIRED_OTHERS',
    13 :'RETIRED',
    21 :'SET_RANK',
    30 :'STARTED_LIVESESSION',
    39 :'ENDED_LIVESESSION',
    50 :'REQUESTED_AUTH',
    51 :'GRANTED_AUTH',
    53 :'BLOCKED',
    61 :'POSTED_TEXT',
    60 :'POSTED_EMOTE',
    63 :'POSTED_CONTACTS',
    64 :'POSTED_SMS',
    65 :'POSTED_ALERT',
    67 :'POSTED_VOICE_MESSAGE',
    68 :'POSTED_FILES',
    69 :'POSTED_INVOICE',
    110:'HAS_BIRTHDAY',
    'SET_METADATA'                                      :  2,
    'SPAWNED_CONFERENCE'                                :  4,
    'ADDED_CONSUMERS'                                   : 10,
    'ADDED_APPLICANTS'                                  : 11,
    'RETIRED_OTHERS'                                    : 12,
    'RETIRED'                                           : 13,
    'SET_RANK'                                          : 21,
    'STARTED_LIVESESSION'                               : 30,
    'ENDED_LIVESESSION'                                 : 39,
    'REQUESTED_AUTH'                                    : 50,
    'GRANTED_AUTH'                                      : 51,
    'BLOCKED'                                           : 53,
    'POSTED_TEXT'                                       : 61,
    'POSTED_EMOTE'                                      : 60,
    'POSTED_CONTACTS'                                   : 63,
    'POSTED_SMS'                                        : 64,
    'POSTED_ALERT'                                      : 65,
    'POSTED_VOICE_MESSAGE'                              : 67,
    'POSTED_FILES'                                      : 68,
    'POSTED_INVOICE'                                    : 69,
    'HAS_BIRTHDAY'                                      :110
  }
  SENDING_STATUS= {1:'SENDING', 'SENDING':1, 2:'SENT', 'SENT':2, 3:'FAILED_TO_SEND', 'FAILED_TO_SEND':3}
  CONSUMPTION_STATUS= {0:'CONSUMED', 'CONSUMED':0, 1:'UNCONSUMED_SUPPRESSED', 'UNCONSUMED_SUPPRESSED':1, 2:'UNCONSUMED_NORMAL', 'UNCONSUMED_NORMAL':2, 3:'UNCONSUMED_ELEVATED', 'UNCONSUMED_ELEVATED':3}
  SET_METADATA_KEY= {3640:'SET_META_NAME', 'SET_META_NAME':3640, 3644:'SET_META_TOPIC', 'SET_META_TOPIC':3644, 3652:'SET_META_GUIDELINES', 'SET_META_GUIDELINES':3652, 3658:'SET_META_PICTURE', 'SET_META_PICTURE':3658}
  SET_OPTION_KEY= {3689:'SET_OPTION_JOINING_ENABLED', 'SET_OPTION_JOINING_ENABLED':3689, 3625:'SET_OPTION_ENTRY_LEVEL_RANK', 'SET_OPTION_ENTRY_LEVEL_RANK':3625, 3629:'SET_OPTION_DISCLOSE_HISTORY', 'SET_OPTION_DISCLOSE_HISTORY':3629, 3633:'SET_OPTION_HISTORY_LIMIT_IN_DAYS', 'SET_OPTION_HISTORY_LIMIT_IN_DAYS':3633, 3637:'SET_OPTION_ADMIN_ONLY_ACTIVITIES', 'SET_OPTION_ADMIN_ONLY_ACTIVITIES':3637}
  LEAVEREASON= {2:'USER_INCAPABLE', 'USER_INCAPABLE':2, 3:'ADDER_MUST_BE_FRIEND', 'ADDER_MUST_BE_FRIEND':3, 4:'ADDER_MUST_BE_AUTHORIZED', 'ADDER_MUST_BE_AUTHORIZED':4, 5:'DECLINE_ADD', 'DECLINE_ADD':5, 6:'UNSUBSCRIBE', 'UNSUBSCRIBE':6}

  def _Getconvo_id(self):
    return module_id2classes[18](self._Property("ZG\300\007]\011",960, True),self.transport)
  convo_id = property(_Getconvo_id)
  propid2label[960] = "convo_id"
  def _Getconvo_guid(self):
    return self._Property("ZGx]\011",120, True)
  convo_guid = property(_Getconvo_guid)
  propid2label[120] = "convo_guid"
  def _Getauthor(self):
    return self._Property("ZGz]\011",122, True)
  author = property(_Getauthor)
  propid2label[122] = "author"
  def _Getauthor_displayname(self):
    return self._Property("ZG{]\011",123, True)
  author_displayname = property(_Getauthor_displayname)
  propid2label[123] = "author_displayname"
  def _Getguid(self):
    return self._Property("ZG\230\006]\011",792, True)
  guid = property(_Getguid)
  propid2label[792] = "guid"
  def _Getoriginally_meant_for(self):
    return self._Property("ZG\226\006]\011",790, True)
  originally_meant_for = property(_Getoriginally_meant_for)
  propid2label[790] = "originally_meant_for"
  def _Gettimestamp(self):
    return self._Property("ZGy]\011",121, True)
  timestamp = property(_Gettimestamp)
  propid2label[121] = "timestamp"
  def _Gettype(self):
    return Message.TYPE[self._Property("ZG\301\007]\011",961, True)]
  type = property(_Gettype)
  propid2label[961] = "type"
  def _Getsending_status(self):
    return Message.SENDING_STATUS[self._Property("ZG\302\007]\011",962, True)]
  sending_status = property(_Getsending_status)
  propid2label[962] = "sending_status"
  def _Getconsumption_status(self):
    return Message.CONSUMPTION_STATUS[self._Property("ZG\310\007]\011",968, True)]
  consumption_status = property(_Getconsumption_status)
  propid2label[968] = "consumption_status"
  def _Getedited_by(self):
    return self._Property("ZG\336\001]\011",222, True)
  edited_by = property(_Getedited_by)
  propid2label[222] = "edited_by"
  def _Getedit_timestamp(self):
    return self._Property("ZG\337\001]\011",223, True)
  edit_timestamp = property(_Getedit_timestamp)
  propid2label[223] = "edit_timestamp"
  def _Getparam_key(self):
    return self._Property("ZG\303\007]\011",963, True)
  param_key = property(_Getparam_key)
  propid2label[963] = "param_key"
  def _Getparam_value(self):
    return self._Property("ZG\304\007]\011",964, True)
  param_value = property(_Getparam_value)
  propid2label[964] = "param_value"
  def _Getbody_xml(self):
    return self._Property("ZG\177]\011",127, True)
  body_xml = property(_Getbody_xml)
  propid2label[127] = "body_xml"
  def _Getidentities(self):
    return self._Property("ZG}]\011",125, True)
  identities = property(_Getidentities)
  propid2label[125] = "identities"
  def _Getreason(self):
    return self._Property("ZG\306\007]\011",966, True)
  reason = property(_Getreason)
  propid2label[966] = "reason"
  def _Getleavereason(self):
    return Message.LEAVEREASON[self._Property("ZG~]\011",126, True)]
  leavereason = property(_Getleavereason)
  propid2label[126] = "leavereason"
  def _Getparticipant_count(self):
    return self._Property("ZG\326\007]\011",982, True)
  participant_count = property(_Getparticipant_count)
  propid2label[982] = "participant_count"

  def CanEdit(self):
    request = XCallRequest("ZR\011\001",9,1)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def Edit(
    self,
    newText,
    isXML
    ):
    request = XCallRequest("ZR\011\002",9,2)
    request.AddParm('O',0,self)
    request.AddParm('S',1,newText)
    request.AddParm('b',2,isXML)
    response = self.transport.Xcall(request)
  def GetContacts(self):
    request = XCallRequest("ZR\011\003",9,3)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = [module_id2classes[2](oid,self.transport) for oid in response.get(1,[])]
    return result
  def GetTransfers(self):
    request = XCallRequest("ZR\011\004",9,4)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = [module_id2classes[6](oid,self.transport) for oid in response.get(1,[])]
    return result
  def GetVoiceMessage(self):
    request = XCallRequest("ZR\011\005",9,5)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = module_id2classes[7](response.get(1),self.transport)
    return result
  def GetSMS(self):
    request = XCallRequest("ZR\011\006",9,6)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = module_id2classes[12](response.get(1),self.transport)
    return result
  def DeleteLocally(self):
    request = XCallRequest("ZR\011\010",9,8)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
module_id2classes[9] = Message

class Video(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Video %s" % (self.object_id, )
  module_id = 11
  def OnPropertyChange(self, property_name): pass
  STATUS= {
    0 :'NOT_AVAILABLE',
    1 :'AVAILABLE',
    2 :'STARTING',
    3 :'REJECTED',
    4 :'RUNNING',
    5 :'STOPPING',
    6 :'PAUSED',
    7 :'NOT_STARTED',
    8 :'HINT_IS_VIDEOCALL_RECEIVED',
    9 :'UNKNOWN',
    10:'RENDERING',
    'NOT_AVAILABLE'                                     : 0,
    'AVAILABLE'                                         : 1,
    'STARTING'                                          : 2,
    'REJECTED'                                          : 3,
    'RUNNING'                                           : 4,
    'STOPPING'                                          : 5,
    'PAUSED'                                            : 6,
    'NOT_STARTED'                                       : 7,
    'HINT_IS_VIDEOCALL_RECEIVED'                        : 8,
    'UNKNOWN'                                           : 9,
    'RENDERING'                                         :10
  }
  MEDIATYPE= {1:'MEDIA_SCREENSHARING', 'MEDIA_SCREENSHARING':1, 0:'MEDIA_VIDEO', 'MEDIA_VIDEO':0}
  VIDEO_DEVICE_CAPABILITY= {0:'VIDEOCAP_HQ_CAPABLE', 'VIDEOCAP_HQ_CAPABLE':0, 1:'VIDEOCAP_HQ_CERTIFIED', 'VIDEOCAP_HQ_CERTIFIED':1, 2:'VIDEOCAP_REQ_DRIVERUPDATE', 'VIDEOCAP_REQ_DRIVERUPDATE':2, 3:'VIDEOCAP_USB_HIGHSPEED', 'VIDEOCAP_USB_HIGHSPEED':3}

  def _Getstatus(self):
    return Video.STATUS[self._Property("ZG\202\001]\013",130, True)]
  status = property(_Getstatus)
  propid2label[130] = "status"
  def _Geterror(self):
    return self._Property("ZG\203\001]\013",131, True)
  error = property(_Geterror)
  propid2label[131] = "error"
  def _Getdebuginfo(self):
    return self._Property("ZG\204\001]\013",132, True)
  debuginfo = property(_Getdebuginfo)
  propid2label[132] = "debuginfo"
  def _Getdimensions(self):
    return self._Property("ZG\205\001]\013",133, True)
  dimensions = property(_Getdimensions)
  propid2label[133] = "dimensions"
  def _Getmedia_type(self):
    return Video.MEDIATYPE[self._Property("ZG\206\001]\013",134, True)]
  media_type = property(_Getmedia_type)
  propid2label[134] = "media_type"
  def _Getconvo_id(self):
    return self._Property("ZG\320\010]\013",1104, True)
  convo_id = property(_Getconvo_id)
  propid2label[1104] = "convo_id"
  def _Getdevice_path(self):
    return self._Property("ZG\321\010]\013",1105, True)
  device_path = property(_Getdevice_path)
  propid2label[1105] = "device_path"

  SETUPKEY_VIDEO_DEVICE="Lib/Video/Device"
  SETUPKEY_VIDEO_DEVICE_PATH="Lib/Video/DevicePath"
  SETUPKEY_VIDEO_AUTOSEND="Lib/Video/AutoSend"
  SETUPKEY_VIDEO_DISABLE="*Lib/Video/Disable"
  SETUPKEY_VIDEO_RECVPOLICY="Lib/Video/RecvPolicy"
  SETUPKEY_VIDEO_ADVERTPOLICY="Lib/Video/AdvertPolicy"
  def SetScreen(
    self,
    windowh
    ):
    request = XCallRequest("ZR\013\001",11,1)
    request.AddParm('O',0,self)
    request.AddParm('u',1,windowh)
    response = self.transport.Xcall(request)
  def Start(self):
    request = XCallRequest("ZR\013\002",11,2)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Stop(self):
    request = XCallRequest("ZR\013\003",11,3)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def SubmitCaptureRequest(self):
    request = XCallRequest("ZR\013\013",11,11)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = (response.get(1,False)),
    result += (response.get(2,0)),
    return result
  def OnCaptureRequestCompleted(
    self,
    requestId,
    isSuccessful,
    image,
    width,
    height
    ): pass
  event_handlers[2] = "OnCaptureRequestCompletedDispatch"
  def OnCaptureRequestCompletedDispatch(self, parms):
    cleanparms  = (parms.get(1,0)),
    cleanparms += (parms.get(2,False)),
    cleanparms += (parms.get(3,'')),
    cleanparms += (parms.get(4,0)),
    cleanparms += (parms.get(5,0)),
    self.OnCaptureRequestCompleted(*cleanparms)
  def SetScreenCaptureRectangle(
    self,
    x0,
    y0,
    width,
    height,
    monitorNumber,
    windowHandle
    ):
    request = XCallRequest("ZR\013\005",11,5)
    request.AddParm('O',0,self)
    request.AddParm('i',1,x0)
    request.AddParm('i',2,y0)
    request.AddParm('u',3,width)
    request.AddParm('u',4,height)
    request.AddParm('i',5,monitorNumber)
    request.AddParm('u',6,windowHandle)
    response = self.transport.Xcall(request)
  def SetRenderRectangle(
    self,
    x0,
    y0,
    width,
    height
    ):
    request = XCallRequest("ZR\013\006",11,6)
    request.AddParm('O',0,self)
    request.AddParm('i',1,x0)
    request.AddParm('i',2,y0)
    request.AddParm('u',3,width)
    request.AddParm('u',4,height)
    response = self.transport.Xcall(request)
  def SelectVideoSource(
    self,
    mediaType,
    webcamName,
    devicePath,
    updateSetup
    ):
    request = XCallRequest("ZR\013\007",11,7)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Video.MEDIATYPE[mediaType])
    request.AddParm('S',2,webcamName)
    request.AddParm('S',3,devicePath)
    request.AddParm('b',4,updateSetup)
    response = self.transport.Xcall(request)
  def GetCurrentVideoDevice(self):
    request = XCallRequest("ZR\013\012",11,10)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = (Video.MEDIATYPE[response.get(1)]),
    result += (response.get(2,'')),
    result += (response.get(3,'')),
    return result
  def OnLastFrameCapture(
    self,
    image,
    width,
    height
    ): pass
  event_handlers[1] = "OnLastFrameCaptureDispatch"
  def OnLastFrameCaptureDispatch(self, parms):
    cleanparms  = (parms.get(1,'')),
    cleanparms += (parms.get(2,0)),
    cleanparms += (parms.get(3,0)),
    self.OnLastFrameCapture(*cleanparms)
module_id2classes[11] = Video

class Voicemail(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Voicemail %s" % (self.object_id, )
  module_id = 7
  def OnPropertyChange(self, property_name): pass
  TYPE= {1:'INCOMING', 'INCOMING':1, 4:'DEFAULT_GREETING', 'DEFAULT_GREETING':4, 2:'CUSTOM_GREETING', 'CUSTOM_GREETING':2, 3:'OUTGOING', 'OUTGOING':3}
  STATUS= {
    1 :'NOTDOWNLOADED',
    2 :'DOWNLOADING',
    3 :'UNPLAYED',
    4 :'BUFFERING',
    5 :'PLAYING',
    6 :'PLAYED',
    7 :'BLANK',
    8 :'RECORDING',
    9 :'RECORDED',
    10:'UPLOADING',
    11:'UPLOADED',
    12:'DELETING',
    13:'FAILED',
    14:'DELETING_FAILED',
    15:'CHECKING',
    16:'CANCELLED',
    'NOTDOWNLOADED'                                     : 1,
    'DOWNLOADING'                                       : 2,
    'UNPLAYED'                                          : 3,
    'BUFFERING'                                         : 4,
    'PLAYING'                                           : 5,
    'PLAYED'                                            : 6,
    'BLANK'                                             : 7,
    'RECORDING'                                         : 8,
    'RECORDED'                                          : 9,
    'UPLOADING'                                         :10,
    'UPLOADED'                                          :11,
    'DELETING'                                          :12,
    'FAILED'                                            :13,
    'DELETING_FAILED'                                   :14,
    'CHECKING'                                          :15,
    'CANCELLED'                                         :16
  }
  FAILUREREASON= {
    1 :'MISC_ERROR',
    2 :'CONNECT_ERROR',
    3 :'NO_VOICEMAIL_CAPABILITY',
    4 :'NO_SUCH_VOICEMAIL',
    5 :'FILE_READ_ERROR',
    6 :'FILE_WRITE_ERROR',
    7 :'RECORDING_ERROR',
    8 :'PLAYBACK_ERROR',
    9 :'NO_PERMISSION',
    10:'RECEIVER_DISABLED_VOICEMAIL',
    11:'SENDER_NOT_AUTHORIZED',
    12:'SENDER_BLOCKED',
    'MISC_ERROR'                                        : 1,
    'CONNECT_ERROR'                                     : 2,
    'NO_VOICEMAIL_CAPABILITY'                           : 3,
    'NO_SUCH_VOICEMAIL'                                 : 4,
    'FILE_READ_ERROR'                                   : 5,
    'FILE_WRITE_ERROR'                                  : 6,
    'RECORDING_ERROR'                                   : 7,
    'PLAYBACK_ERROR'                                    : 8,
    'NO_PERMISSION'                                     : 9,
    'RECEIVER_DISABLED_VOICEMAIL'                       :10,
    'SENDER_NOT_AUTHORIZED'                             :11,
    'SENDER_BLOCKED'                                    :12
  }

  def _Gettype(self):
    return Voicemail.TYPE[self._Property("ZGd]\007",100, True)]
  type = property(_Gettype)
  propid2label[100] = "type"
  def _Getpartner_handle(self):
    return self._Property("ZGe]\007",101, True)
  partner_handle = property(_Getpartner_handle)
  propid2label[101] = "partner_handle"
  def _Getpartner_dispname(self):
    return self._Property("ZGf]\007",102, True)
  partner_dispname = property(_Getpartner_dispname)
  propid2label[102] = "partner_dispname"
  def _Getstatus(self):
    return Voicemail.STATUS[self._Property("ZGg]\007",103, True)]
  status = property(_Getstatus)
  propid2label[103] = "status"
  def _Getfailurereason(self):
    return Voicemail.FAILUREREASON[self._Property("ZGh]\007",104, True)]
  failurereason = property(_Getfailurereason)
  propid2label[104] = "failurereason"
  def _Getsubject(self):
    return self._Property("ZGi]\007",105, True)
  subject = property(_Getsubject)
  propid2label[105] = "subject"
  def _Gettimestamp(self):
    return self._Property("ZGj]\007",106, True)
  timestamp = property(_Gettimestamp)
  propid2label[106] = "timestamp"
  def _Getduration(self):
    return self._Property("ZGk]\007",107, True)
  duration = property(_Getduration)
  propid2label[107] = "duration"
  def _Getallowed_duration(self):
    return self._Property("ZGl]\007",108, True)
  allowed_duration = property(_Getallowed_duration)
  propid2label[108] = "allowed_duration"
  def _Getplayback_progress(self):
    return self._Property("ZGm]\007",109, True)
  playback_progress = property(_Getplayback_progress)
  propid2label[109] = "playback_progress"
  def _Getconvo_id(self):
    return module_id2classes[18](self._Property("ZG\276\006]\007",830, True),self.transport)
  convo_id = property(_Getconvo_id)
  propid2label[830] = "convo_id"
  def _Getchatmsg_guid(self):
    return self._Property("ZG\277\006]\007",831, True)
  chatmsg_guid = property(_Getchatmsg_guid)
  propid2label[831] = "chatmsg_guid"

  def StartRecording(self):
    request = XCallRequest("ZR\007\003",7,3)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def StopRecording(self):
    request = XCallRequest("ZR\007\004",7,4)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def StartPlayback(self):
    request = XCallRequest("ZR\007\005",7,5)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def StopPlayback(self):
    request = XCallRequest("ZR\007\006",7,6)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Delete(self):
    request = XCallRequest("ZR\007\007",7,7)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Cancel(self):
    request = XCallRequest("ZR\007\010",7,8)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def CheckPermission(self):
    request = XCallRequest("ZR\007\015",7,13)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
module_id2classes[7] = Voicemail

class Sms(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Sms %s" % (self.object_id, )
  module_id = 12
  def OnPropertyChange(self, property_name): pass
  TYPE= {1:'INCOMING', 'INCOMING':1, 2:'OUTGOING', 'OUTGOING':2, 3:'CONFIRMATION_CODE_REQUEST', 'CONFIRMATION_CODE_REQUEST':3, 4:'CONFIRMATION_CODE_SUBMIT', 'CONFIRMATION_CODE_SUBMIT':4}
  STATUS= {1:'RECEIVED', 'RECEIVED':1, 2:'READ', 'READ':2, 3:'COMPOSING', 'COMPOSING':3, 4:'SENDING_TO_SERVER', 'SENDING_TO_SERVER':4, 5:'SENT_TO_SERVER', 'SENT_TO_SERVER':5, 6:'DELIVERED', 'DELIVERED':6, 7:'SOME_TARGETS_FAILED', 'SOME_TARGETS_FAILED':7, 8:'FAILED', 'FAILED':8}
  FAILUREREASON= {
    1:'MISC_ERROR',
    2:'SERVER_CONNECT_FAILED',
    3:'NO_SMS_CAPABILITY',
    4:'INSUFFICIENT_FUNDS',
    5:'INVALID_CONFIRMATION_CODE',
    6:'USER_BLOCKED',
    7:'IP_BLOCKED',
    8:'NODE_BLOCKED',
    9:'NO_SENDERID_CAPABILITY',
    'MISC_ERROR'                                        :1,
    'SERVER_CONNECT_FAILED'                             :2,
    'NO_SMS_CAPABILITY'                                 :3,
    'INSUFFICIENT_FUNDS'                                :4,
    'INVALID_CONFIRMATION_CODE'                         :5,
    'USER_BLOCKED'                                      :6,
    'IP_BLOCKED'                                        :7,
    'NODE_BLOCKED'                                      :8,
    'NO_SENDERID_CAPABILITY'                            :9
  }
  TARGETSTATUS= {1:'TARGET_ANALYZING', 'TARGET_ANALYZING':1, 2:'TARGET_UNDEFINED', 'TARGET_UNDEFINED':2, 3:'TARGET_ACCEPTABLE', 'TARGET_ACCEPTABLE':3, 4:'TARGET_NOT_ROUTABLE', 'TARGET_NOT_ROUTABLE':4, 5:'TARGET_DELIVERY_PENDING', 'TARGET_DELIVERY_PENDING':5, 6:'TARGET_DELIVERY_SUCCESSFUL', 'TARGET_DELIVERY_SUCCESSFUL':6, 7:'TARGET_DELIVERY_FAILED', 'TARGET_DELIVERY_FAILED':7}
  SETBODYRESULT= {0:'BODY_INVALID', 'BODY_INVALID':0, 1:'BODY_TRUNCATED', 'BODY_TRUNCATED':1, 2:'BODY_OK', 'BODY_OK':2, 3:'BODY_LASTCHAR_IGNORED', 'BODY_LASTCHAR_IGNORED':3}

  def _Gettype(self):
    return Sms.TYPE[self._Property("ZG\276\001]\014",190, True)]
  type = property(_Gettype)
  propid2label[190] = "type"
  def _Getstatus(self):
    return Sms.STATUS[self._Property("ZG\277\001]\014",191, True)]
  status = property(_Getstatus)
  propid2label[191] = "status"
  def _Getfailurereason(self):
    return Sms.FAILUREREASON[self._Property("ZG\300\001]\014",192, True)]
  failurereason = property(_Getfailurereason)
  propid2label[192] = "failurereason"
  def _Getis_failed_unseen(self):
    return self._Property("ZG0]\014",48, True)
  is_failed_unseen = property(_Getis_failed_unseen)
  propid2label[48] = "is_failed_unseen"
  def _Gettimestamp(self):
    return self._Property("ZG\306\001]\014",198, True)
  timestamp = property(_Gettimestamp)
  propid2label[198] = "timestamp"
  def _Getprice(self):
    return self._Property("ZG\301\001]\014",193, True)
  price = property(_Getprice)
  propid2label[193] = "price"
  def _Getprice_precision(self):
    return self._Property("ZG1]\014",49, True)
  price_precision = property(_Getprice_precision)
  propid2label[49] = "price_precision"
  def _Getprice_currency(self):
    return self._Property("ZG\302\001]\014",194, True)
  price_currency = property(_Getprice_currency)
  propid2label[194] = "price_currency"
  def _Getreply_to_number(self):
    return self._Property("ZG\307\001]\014",199, True)
  reply_to_number = property(_Getreply_to_number)
  propid2label[199] = "reply_to_number"
  def _Gettarget_numbers(self):
    return self._Property("ZG\303\001]\014",195, True)
  target_numbers = property(_Gettarget_numbers)
  propid2label[195] = "target_numbers"
  def _Gettarget_statuses(self):
    return self._Property("ZG\304\001]\014",196, True)
  target_statuses = property(_Gettarget_statuses)
  propid2label[196] = "target_statuses"
  def _Getbody(self):
    return self._Property("ZG\305\001]\014",197, True)
  body = property(_Getbody)
  propid2label[197] = "body"
  def _Getchatmsg_id(self):
    return module_id2classes[9](self._Property("ZG\310\006]\014",840, True),self.transport)
  chatmsg_id = property(_Getchatmsg_id)
  propid2label[840] = "chatmsg_id"

  def GetTargetStatus(
    self,
    target
    ):
    request = XCallRequest("ZR\014\004",12,4)
    request.AddParm('O',0,self)
    request.AddParm('S',1,target)
    response = self.transport.Xcall(request)
    result  = Sms.TARGETSTATUS[response.get(1)]
    return result
  def GetTargetPrice(
    self,
    target
    ):
    request = XCallRequest("ZR\014\015",12,13)
    request.AddParm('O',0,self)
    request.AddParm('S',1,target)
    response = self.transport.Xcall(request)
    result  = response.get(1,0)
    return result
  def SetReplyTo(
    self,
    number
    ):
    request = XCallRequest("ZR\014\005",12,5)
    request.AddParm('O',0,self)
    request.AddParm('S',1,number)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def SetTargets(
    self,
    numbers
    ):
    request = XCallRequest("ZR\014\006",12,6)
    request.AddParm('O',0,self)
    request.AddParm('S',1,numbers)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def SetBody(
    self,
    text
    ):
    request = XCallRequest("ZR\014\007",12,7)
    request.AddParm('O',0,self)
    request.AddParm('S',1,text)
    response = self.transport.Xcall(request)
    result  = (Sms.SETBODYRESULT[response.get(1)]),
    result += (response.get(2,[])),
    result += (response.get(3,0)),
    return result
  def GetBodyChunks(self):
    request = XCallRequest("ZR\014\010",12,8)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = (response.get(1,[])),
    result += (response.get(2,0)),
    return result
  def SetOrigin(
    self,
    origin
    ):
    request = XCallRequest("ZR\014\016",12,14)
    request.AddParm('O',0,self)
    request.AddParm('S',1,origin)
    response = self.transport.Xcall(request)
module_id2classes[12] = Sms

class Transfer(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Transfer %s" % (self.object_id, )
  module_id = 6
  def OnPropertyChange(self, property_name): pass
  TYPE= {1:'INCOMING', 'INCOMING':1, 2:'OUTGOING', 'OUTGOING':2}
  STATUS= {
    0 :'NEW',
    1 :'CONNECTING',
    2 :'WAITING_FOR_ACCEPT',
    3 :'TRANSFERRING',
    4 :'TRANSFERRING_OVER_RELAY',
    5 :'PAUSED',
    6 :'REMOTELY_PAUSED',
    7 :'CANCELLED',
    8 :'COMPLETED',
    9 :'FAILED',
    10:'PLACEHOLDER',
    11:'OFFER_FROM_OTHER_INSTANCE',
    12:'CANCELLED_BY_REMOTE',
    'NEW'                                               : 0,
    'CONNECTING'                                        : 1,
    'WAITING_FOR_ACCEPT'                                : 2,
    'TRANSFERRING'                                      : 3,
    'TRANSFERRING_OVER_RELAY'                           : 4,
    'PAUSED'                                            : 5,
    'REMOTELY_PAUSED'                                   : 6,
    'CANCELLED'                                         : 7,
    'COMPLETED'                                         : 8,
    'FAILED'                                            : 9,
    'PLACEHOLDER'                                       :10,
    'OFFER_FROM_OTHER_INSTANCE'                         :11,
    'CANCELLED_BY_REMOTE'                               :12
  }
  FAILUREREASON= {
    1 :'SENDER_NOT_AUTHORISED',
    2 :'REMOTELY_CANCELLED',
    3 :'FAILED_READ',
    4 :'FAILED_REMOTE_READ',
    5 :'FAILED_WRITE',
    6 :'FAILED_REMOTE_WRITE',
    7 :'REMOTE_DOES_NOT_SUPPORT_FT',
    8 :'REMOTE_OFFLINE_FOR_TOO_LONG',
    9 :'TOO_MANY_PARALLEL',
    10:'PLACEHOLDER_TIMEOUT',
    'SENDER_NOT_AUTHORISED'                             : 1,
    'REMOTELY_CANCELLED'                                : 2,
    'FAILED_READ'                                       : 3,
    'FAILED_REMOTE_READ'                                : 4,
    'FAILED_WRITE'                                      : 5,
    'FAILED_REMOTE_WRITE'                               : 6,
    'REMOTE_DOES_NOT_SUPPORT_FT'                        : 7,
    'REMOTE_OFFLINE_FOR_TOO_LONG'                       : 8,
    'TOO_MANY_PARALLEL'                                 : 9,
    'PLACEHOLDER_TIMEOUT'                               :10
  }

  def _Gettype(self):
    return Transfer.TYPE[self._Property("ZGP]\006",80, True)]
  type = property(_Gettype)
  propid2label[80] = "type"
  def _Getpartner_handle(self):
    return self._Property("ZGQ]\006",81, True)
  partner_handle = property(_Getpartner_handle)
  propid2label[81] = "partner_handle"
  def _Getpartner_dispname(self):
    return self._Property("ZGR]\006",82, True)
  partner_dispname = property(_Getpartner_dispname)
  propid2label[82] = "partner_dispname"
  def _Getstatus(self):
    return Transfer.STATUS[self._Property("ZGS]\006",83, True)]
  status = property(_Getstatus)
  propid2label[83] = "status"
  def _Getfailurereason(self):
    return Transfer.FAILUREREASON[self._Property("ZGT]\006",84, True)]
  failurereason = property(_Getfailurereason)
  propid2label[84] = "failurereason"
  def _Getstarttime(self):
    return self._Property("ZGU]\006",85, True)
  starttime = property(_Getstarttime)
  propid2label[85] = "starttime"
  def _Getfinishtime(self):
    return self._Property("ZGV]\006",86, True)
  finishtime = property(_Getfinishtime)
  propid2label[86] = "finishtime"
  def _Getfilepath(self):
    return self._Property("ZGW]\006",87, True)
  filepath = property(_Getfilepath)
  propid2label[87] = "filepath"
  def _Getfilename(self):
    return self._Property("ZGX]\006",88, True)
  filename = property(_Getfilename)
  propid2label[88] = "filename"
  def _Getfilesize(self):
    return self._Property("ZGY]\006",89, True)
  filesize = property(_Getfilesize)
  propid2label[89] = "filesize"
  def _Getbytestransferred(self):
    return self._Property("ZGZ]\006",90, True)
  bytestransferred = property(_Getbytestransferred)
  propid2label[90] = "bytestransferred"
  def _Getbytespersecond(self):
    return self._Property("ZG[]\006",91, True)
  bytespersecond = property(_Getbytespersecond)
  propid2label[91] = "bytespersecond"
  def _Getchatmsg_guid(self):
    return self._Property("ZG\134]\006",92, True)
  chatmsg_guid = property(_Getchatmsg_guid)
  propid2label[92] = "chatmsg_guid"
  def _Getchatmsg_index(self):
    return self._Property("ZG]]\006",93, True)
  chatmsg_index = property(_Getchatmsg_index)
  propid2label[93] = "chatmsg_index"
  def _Getconvo_id(self):
    return module_id2classes[18](self._Property("ZGb]\006",98, True),self.transport)
  convo_id = property(_Getconvo_id)
  propid2label[98] = "convo_id"

  def Accept(
    self,
    filenameWithPath
    ):
    request = XCallRequest("ZR\006\003",6,3)
    request.AddParm('O',0,self)
    request.AddParm('f',1,filenameWithPath)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def Pause(self):
    request = XCallRequest("ZR\006\004",6,4)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Resume(self):
    request = XCallRequest("ZR\006\005",6,5)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def Cancel(self):
    request = XCallRequest("ZR\006\006",6,6)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
module_id2classes[6] = Transfer

class Account(Object):
  event_handlers = {}
  propid2label   = {}
  def _Init(self, object_id, transport):
    Object._Init(self, object_id, transport)
  def __str__(self):
    return "Account %s" % (self.object_id, )
  module_id = 5
  def OnPropertyChange(self, property_name): pass
  STATUS= {1:'LOGGED_OUT', 'LOGGED_OUT':1, 2:'LOGGED_OUT_AND_PWD_SAVED', 'LOGGED_OUT_AND_PWD_SAVED':2, 3:'CONNECTING_TO_P2P', 'CONNECTING_TO_P2P':3, 4:'CONNECTING_TO_SERVER', 'CONNECTING_TO_SERVER':4, 5:'LOGGING_IN', 'LOGGING_IN':5, 6:'INITIALIZING', 'INITIALIZING':6, 7:'LOGGED_IN', 'LOGGED_IN':7, 8:'LOGGING_OUT', 'LOGGING_OUT':8}
  CBLSYNCSTATUS= {0:'CBL_INITIALIZING', 'CBL_INITIALIZING':0, 1:'CBL_INITIAL_SYNC_PENDING', 'CBL_INITIAL_SYNC_PENDING':1, 2:'CBL_SYNC_PENDING', 'CBL_SYNC_PENDING':2, 3:'CBL_SYNC_IN_PROGRESS', 'CBL_SYNC_IN_PROGRESS':3, 4:'CBL_IN_SYNC', 'CBL_IN_SYNC':4, 5:'CBL_SYNC_FAILED', 'CBL_SYNC_FAILED':5, 6:'CBL_REMOTE_SYNC_PENDING', 'CBL_REMOTE_SYNC_PENDING':6}
  LOGOUTREASON= {
    1 :'LOGOUT_CALLED',
    2 :'HTTPS_PROXY_AUTH_FAILED',
    3 :'SOCKS_PROXY_AUTH_FAILED',
    4 :'P2P_CONNECT_FAILED',
    5 :'SERVER_CONNECT_FAILED',
    6 :'SERVER_OVERLOADED',
    7 :'DB_IN_USE',
    8 :'INVALID_SKYPENAME',
    9 :'INVALID_EMAIL',
    10:'UNACCEPTABLE_PASSWORD',
    11:'SKYPENAME_TAKEN',
    12:'REJECTED_AS_UNDERAGE',
    13:'NO_SUCH_IDENTITY',
    14:'INCORRECT_PASSWORD',
    15:'TOO_MANY_LOGIN_ATTEMPTS',
    16:'PASSWORD_HAS_CHANGED',
    17:'PERIODIC_UIC_UPDATE_FAILED',
    18:'DB_DISK_FULL',
    19:'DB_IO_ERROR',
    20:'DB_CORRUPT',
    21:'DB_FAILURE',
    22:'INVALID_APP_ID',
    23:'APP_ID_BLACKLISTED',
    24:'UNSUPPORTED_VERSION',
    'LOGOUT_CALLED'                                     : 1,
    'HTTPS_PROXY_AUTH_FAILED'                           : 2,
    'SOCKS_PROXY_AUTH_FAILED'                           : 3,
    'P2P_CONNECT_FAILED'                                : 4,
    'SERVER_CONNECT_FAILED'                             : 5,
    'SERVER_OVERLOADED'                                 : 6,
    'DB_IN_USE'                                         : 7,
    'INVALID_SKYPENAME'                                 : 8,
    'INVALID_EMAIL'                                     : 9,
    'UNACCEPTABLE_PASSWORD'                             :10,
    'SKYPENAME_TAKEN'                                   :11,
    'REJECTED_AS_UNDERAGE'                              :12,
    'NO_SUCH_IDENTITY'                                  :13,
    'INCORRECT_PASSWORD'                                :14,
    'TOO_MANY_LOGIN_ATTEMPTS'                           :15,
    'PASSWORD_HAS_CHANGED'                              :16,
    'PERIODIC_UIC_UPDATE_FAILED'                        :17,
    'DB_DISK_FULL'                                      :18,
    'DB_IO_ERROR'                                       :19,
    'DB_CORRUPT'                                        :20,
    'DB_FAILURE'                                        :21,
    'INVALID_APP_ID'                                    :22,
    'APP_ID_BLACKLISTED'                                :23,
    'UNSUPPORTED_VERSION'                               :24
  }
  PWDCHANGESTATUS= {0:'PWD_OK', 'PWD_OK':0, 1:'PWD_CHANGING', 'PWD_CHANGING':1, 2:'PWD_INVALID_OLD_PASSWORD', 'PWD_INVALID_OLD_PASSWORD':2, 3:'PWD_SERVER_CONNECT_FAILED', 'PWD_SERVER_CONNECT_FAILED':3, 4:'PWD_OK_BUT_CHANGE_SUGGESTED', 'PWD_OK_BUT_CHANGE_SUGGESTED':4, 5:'PWD_MUST_DIFFER_FROM_OLD', 'PWD_MUST_DIFFER_FROM_OLD':5, 6:'PWD_INVALID_NEW_PWD', 'PWD_INVALID_NEW_PWD':6, 7:'PWD_MUST_LOG_IN_TO_CHANGE', 'PWD_MUST_LOG_IN_TO_CHANGE':7}
  COMMITSTATUS= {1:'COMMITTED', 'COMMITTED':1, 2:'COMMITTING_TO_SERVER', 'COMMITTING_TO_SERVER':2, 3:'COMMIT_FAILED', 'COMMIT_FAILED':3}
  CHATPOLICY= {0:'EVERYONE_CAN_ADD', 'EVERYONE_CAN_ADD':0, 2:'BUDDIES_OR_AUTHORIZED_CAN_ADD', 'BUDDIES_OR_AUTHORIZED_CAN_ADD':2}
  SKYPECALLPOLICY= {0:'EVERYONE_CAN_CALL', 'EVERYONE_CAN_CALL':0, 2:'BUDDIES_OR_AUTHORIZED_CAN_CALL', 'BUDDIES_OR_AUTHORIZED_CAN_CALL':2}
  PSTNCALLPOLICY= {0:'ALL_NUMBERS_CAN_CALL', 'ALL_NUMBERS_CAN_CALL':0, 1:'DISCLOSED_NUMBERS_CAN_CALL', 'DISCLOSED_NUMBERS_CAN_CALL':1, 2:'BUDDY_NUMBERS_CAN_CALL', 'BUDDY_NUMBERS_CAN_CALL':2}
  AVATARPOLICY= {0:'BUDDIES_OR_AUTHORIZED_CAN_SEE', 'BUDDIES_OR_AUTHORIZED_CAN_SEE':0, 2:'EVERYONE_CAN_SEE', 'EVERYONE_CAN_SEE':2}
  BUDDYCOUNTPOLICY= {0:'DISCLOSE_TO_AUTHORIZED', 'DISCLOSE_TO_AUTHORIZED':0, 1:'DISCLOSE_TO_NOONE', 'DISCLOSE_TO_NOONE':1}
  TIMEZONEPOLICY= {0:'TZ_AUTOMATIC', 'TZ_AUTOMATIC':0, 1:'TZ_MANUAL', 'TZ_MANUAL':1, 2:'TZ_UNDISCLOSED', 'TZ_UNDISCLOSED':2}
  WEBPRESENCEPOLICY= {0:'WEBPRESENCE_DISABLED', 'WEBPRESENCE_DISABLED':0, 1:'WEBPRESENCE_ENABLED', 'WEBPRESENCE_ENABLED':1}
  PHONENUMBERSPOLICY= {0:'PHONENUMBERS_VISIBLE_FOR_BUDDIES', 'PHONENUMBERS_VISIBLE_FOR_BUDDIES':0, 1:'PHONENUMBERS_VISIBLE_FOR_EVERYONE', 'PHONENUMBERS_VISIBLE_FOR_EVERYONE':1}
  VOICEMAILPOLICY= {0:'VOICEMAIL_ENABLED', 'VOICEMAIL_ENABLED':0, 1:'VOICEMAIL_DISABLED', 'VOICEMAIL_DISABLED':1}
  AUTHREQUESTPOLICY= {0:'AUTHREQUEST_ENABLED', 'AUTHREQUEST_ENABLED':0, 5:'CHAT_PARTICIPANTS_CAN_AUTHREQ', 'CHAT_PARTICIPANTS_CAN_AUTHREQ':5, 9:'AUTHREQUEST_DISABLED', 'AUTHREQUEST_DISABLED':9}
  CAPABILITYSTATUS= {0:'NO_CAPABILITY', 'NO_CAPABILITY':0, 1:'CAPABILITY_EXISTS', 'CAPABILITY_EXISTS':1, 2:'FIRST_EXPIRY_WARNING', 'FIRST_EXPIRY_WARNING':2, 3:'SECOND_EXPIRY_WARNING', 'SECOND_EXPIRY_WARNING':3, 4:'FINAL_EXPIRY_WARNING', 'FINAL_EXPIRY_WARNING':4}

  def _Getstatus(self):
    return Account.STATUS[self._Property("ZGF]\005",70, True)]
  status = property(_Getstatus)
  propid2label[70] = "status"
  def _Getpwdchangestatus(self):
    return Account.PWDCHANGESTATUS[self._Property("ZGG]\005",71, True)]
  pwdchangestatus = property(_Getpwdchangestatus)
  propid2label[71] = "pwdchangestatus"
  def _Getlogoutreason(self):
    return Account.LOGOUTREASON[self._Property("ZGI]\005",73, True)]
  logoutreason = property(_Getlogoutreason)
  propid2label[73] = "logoutreason"
  def _Getcommitstatus(self):
    return Account.COMMITSTATUS[self._Property("ZGN]\005",78, True)]
  commitstatus = property(_Getcommitstatus)
  propid2label[78] = "commitstatus"
  def _Getsuggested_skypename(self):
    return self._Property("ZGH]\005",72, True)
  suggested_skypename = property(_Getsuggested_skypename)
  propid2label[72] = "suggested_skypename"
  def _Getskypeout_balance_currency(self):
    return self._Property("ZGJ]\005",74, True)
  skypeout_balance_currency = property(_Getskypeout_balance_currency)
  propid2label[74] = "skypeout_balance_currency"
  def _Getskypeout_balance(self):
    return self._Property("ZGK]\005",75, True)
  skypeout_balance = property(_Getskypeout_balance)
  propid2label[75] = "skypeout_balance"
  def _Getskypeout_precision(self):
    return self._Property("ZG\244\006]\005",804, True)
  skypeout_precision = property(_Getskypeout_precision)
  propid2label[804] = "skypeout_precision"
  def _Getskypein_numbers(self):
    return self._Property("ZGL]\005",76, True)
  skypein_numbers = property(_Getskypein_numbers)
  propid2label[76] = "skypein_numbers"
  def _Getcblsyncstatus(self):
    return Account.CBLSYNCSTATUS[self._Property("ZGO]\005",79, True)]
  cblsyncstatus = property(_Getcblsyncstatus)
  propid2label[79] = "cblsyncstatus"
  def _Getoffline_callforward(self):
    return self._Property("ZGM]\005",77, True)
  offline_callforward = property(_Getoffline_callforward)
  propid2label[77] = "offline_callforward"
  def _Getchat_policy(self):
    return Account.CHATPOLICY[self._Property("ZG\240\001]\005",160, True)]
  chat_policy = property(_Getchat_policy)
  propid2label[160] = "chat_policy"
  def _Getskype_call_policy(self):
    return Account.SKYPECALLPOLICY[self._Property("ZG\241\001]\005",161, True)]
  skype_call_policy = property(_Getskype_call_policy)
  propid2label[161] = "skype_call_policy"
  def _Getpstn_call_policy(self):
    return Account.PSTNCALLPOLICY[self._Property("ZG\242\001]\005",162, True)]
  pstn_call_policy = property(_Getpstn_call_policy)
  propid2label[162] = "pstn_call_policy"
  def _Getavatar_policy(self):
    return Account.AVATARPOLICY[self._Property("ZG\243\001]\005",163, True)]
  avatar_policy = property(_Getavatar_policy)
  propid2label[163] = "avatar_policy"
  def _Getbuddycount_policy(self):
    return Account.BUDDYCOUNTPOLICY[self._Property("ZG\244\001]\005",164, True)]
  buddycount_policy = property(_Getbuddycount_policy)
  propid2label[164] = "buddycount_policy"
  def _Gettimezone_policy(self):
    return Account.TIMEZONEPOLICY[self._Property("ZG\245\001]\005",165, True)]
  timezone_policy = property(_Gettimezone_policy)
  propid2label[165] = "timezone_policy"
  def _Getwebpresence_policy(self):
    return Account.WEBPRESENCEPOLICY[self._Property("ZG\246\001]\005",166, True)]
  webpresence_policy = property(_Getwebpresence_policy)
  propid2label[166] = "webpresence_policy"
  def _Getphonenumbers_policy(self):
    return Account.PHONENUMBERSPOLICY[self._Property("ZG\250\001]\005",168, True)]
  phonenumbers_policy = property(_Getphonenumbers_policy)
  propid2label[168] = "phonenumbers_policy"
  def _Getvoicemail_policy(self):
    return Account.VOICEMAILPOLICY[self._Property("ZG\251\001]\005",169, True)]
  voicemail_policy = property(_Getvoicemail_policy)
  propid2label[169] = "voicemail_policy"
  def _Getauthrequest_policy(self):
    return Account.AUTHREQUESTPOLICY[self._Property("ZG\260\001]\005",176, True)]
  authrequest_policy = property(_Getauthrequest_policy)
  propid2label[176] = "authrequest_policy"
  def _Getpartner_optedout(self):
    return self._Property("ZG\205\006]\005",773, True)
  partner_optedout = property(_Getpartner_optedout)
  propid2label[773] = "partner_optedout"
  def _Getservice_provider_info(self):
    return self._Property("ZG\240\006]\005",800, True)
  service_provider_info = property(_Getservice_provider_info)
  propid2label[800] = "service_provider_info"
  def _Getregistration_timestamp(self):
    return self._Property("ZG\241\006]\005",801, True)
  registration_timestamp = property(_Getregistration_timestamp)
  propid2label[801] = "registration_timestamp"
  def _Getnr_of_other_instances(self):
    return self._Property("ZG\242\006]\005",802, True)
  nr_of_other_instances = property(_Getnr_of_other_instances)
  propid2label[802] = "nr_of_other_instances"
  def _Getskypename(self):
    return self._Property("ZG\004]\005",4, True)
  skypename = property(_Getskypename)
  propid2label[4] = "skypename"
  def _Getfullname(self):
    return self._Property("ZG\005]\005",5, True)
  fullname = property(_Getfullname)
  propid2label[5] = "fullname"
  def _Getbirthday(self):
    return self._Property("ZG\007]\005",7, True)
  birthday = property(_Getbirthday)
  propid2label[7] = "birthday"
  def _Getgender(self):
    return self._Property("ZG\010]\005",8, True)
  gender = property(_Getgender)
  propid2label[8] = "gender"
  def _Getlanguages(self):
    return self._Property("ZG\011]\005",9, True)
  languages = property(_Getlanguages)
  propid2label[9] = "languages"
  def _Getcountry(self):
    return self._Property("ZG\012]\005",10, True)
  country = property(_Getcountry)
  propid2label[10] = "country"
  def _Getprovince(self):
    return self._Property("ZG\013]\005",11, True)
  province = property(_Getprovince)
  propid2label[11] = "province"
  def _Getcity(self):
    return self._Property("ZG\014]\005",12, True)
  city = property(_Getcity)
  propid2label[12] = "city"
  def _Getphone_home(self):
    return self._Property("ZG\015]\005",13, True)
  phone_home = property(_Getphone_home)
  propid2label[13] = "phone_home"
  def _Getphone_office(self):
    return self._Property("ZG\016]\005",14, True)
  phone_office = property(_Getphone_office)
  propid2label[14] = "phone_office"
  def _Getphone_mobile(self):
    return self._Property("ZG\017]\005",15, True)
  phone_mobile = property(_Getphone_mobile)
  propid2label[15] = "phone_mobile"
  def _Getemails(self):
    return self._Property("ZG\020]\005",16, True)
  emails = property(_Getemails)
  propid2label[16] = "emails"
  def _Gethomepage(self):
    return self._Property("ZG\021]\005",17, True)
  homepage = property(_Gethomepage)
  propid2label[17] = "homepage"
  def _Getabout(self):
    return self._Property("ZG\022]\005",18, True)
  about = property(_Getabout)
  propid2label[18] = "about"
  def _Getprofile_timestamp(self):
    return self._Property("ZG\023]\005",19, True)
  profile_timestamp = property(_Getprofile_timestamp)
  propid2label[19] = "profile_timestamp"
  def _Getmood_text(self):
    return self._Property("ZG\032]\005",26, True)
  mood_text = property(_Getmood_text)
  propid2label[26] = "mood_text"
  def _Gettimezone(self):
    return self._Property("ZG\033]\005",27, True)
  timezone = property(_Gettimezone)
  propid2label[27] = "timezone"
  def _Getnrof_authed_buddies(self):
    return self._Property("ZG\034]\005",28, True)
  nrof_authed_buddies = property(_Getnrof_authed_buddies)
  propid2label[28] = "nrof_authed_buddies"
  def _Getavailability(self):
    return Contact.AVAILABILITY[self._Property("ZG\042]\005",34, True)]
  availability = property(_Getavailability)
  propid2label[34] = "availability"
  def _Getavatar_image(self):
    return self._Property("ZG%]\005",37, True)
  avatar_image = property(_Getavatar_image)
  propid2label[37] = "avatar_image"
  def _Getavatar_timestamp(self):
    return self._Property("ZG\266\001]\005",182, True)
  avatar_timestamp = property(_Getavatar_timestamp)
  propid2label[182] = "avatar_timestamp"
  def _Getmood_timestamp(self):
    return self._Property("ZG\267\001]\005",183, True)
  mood_timestamp = property(_Getmood_timestamp)
  propid2label[183] = "mood_timestamp"
  def _Getrich_mood_text(self):
    return self._Property("ZG\315\001]\005",205, True)
  rich_mood_text = property(_Getrich_mood_text)
  propid2label[205] = "rich_mood_text"

  def GetStatusWithProgress(self):
    request = XCallRequest("ZR\005\001",5,1)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = (Account.STATUS[response.get(1)]),
    result += (response.get(2,0)),
    return result
  def Login(
    self,
    setAvailabilityTo
    ):
    request = XCallRequest("ZR\005\005",5,5)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Contact.AVAILABILITY[setAvailabilityTo])
    response = self.transport.Xcall(request)
  def LoginWithPassword(
    self,
    password,
    savePwd,
    saveDataLocally
    ):
    request = XCallRequest("ZR\005\006",5,6)
    request.AddParm('O',0,self)
    request.AddParm('S',1,password)
    request.AddParm('b',2,savePwd)
    request.AddParm('b',3,saveDataLocally)
    response = self.transport.Xcall(request)
  def Register(
    self,
    password,
    savePwd,
    saveDataLocally,
    email,
    allowSpam
    ):
    request = XCallRequest("ZR\005\007",5,7)
    request.AddParm('O',0,self)
    request.AddParm('S',1,password)
    request.AddParm('b',2,savePwd)
    request.AddParm('b',3,saveDataLocally)
    request.AddParm('S',4,email)
    request.AddParm('b',5,allowSpam)
    response = self.transport.Xcall(request)
  def Logout(
    self,
    clearSavedPwd
    ):
    request = XCallRequest("ZR\005\010",5,8)
    request.AddParm('O',0,self)
    request.AddParm('b',1,clearSavedPwd)
    response = self.transport.Xcall(request)
  def ChangePassword(
    self,
    oldPassword,
    newPassword,
    savePwd
    ):
    request = XCallRequest("ZR\005\013",5,11)
    request.AddParm('O',0,self)
    request.AddParm('S',1,oldPassword)
    request.AddParm('S',2,newPassword)
    request.AddParm('b',3,savePwd)
    response = self.transport.Xcall(request)
  def SetPasswordSaved(
    self,
    savePwd
    ):
    request = XCallRequest("ZR\005\031",5,25)
    request.AddParm('O',0,self)
    request.AddParm('b',1,savePwd)
    response = self.transport.Xcall(request)
  def SetServersideIntProperty(
    self,
    propKey,
    value
    ):
    request = XCallRequest("ZR\005\014",5,12)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(propKey,1))
    request.AddParm('u',2,value)
    response = self.transport.Xcall(request)
  def SetServersideStrProperty(
    self,
    propKey,
    value
    ):
    request = XCallRequest("ZR\005\015",5,13)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(propKey,0))
    request.AddParm('S',2,value)
    response = self.transport.Xcall(request)
  def CancelServerCommit(self):
    request = XCallRequest("ZR\005\017",5,15)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def SetIntProperty(
    self,
    propKey,
    value
    ):
    request = XCallRequest("ZR\005\020",5,16)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(propKey,1))
    request.AddParm('u',2,value)
    response = self.transport.Xcall(request)
  def SetStrProperty(
    self,
    propKey,
    value
    ):
    request = XCallRequest("ZR\005\021",5,17)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(propKey,0))
    request.AddParm('S',2,value)
    response = self.transport.Xcall(request)
  def SetBinProperty(
    self,
    propKey,
    value
    ):
    request = XCallRequest("ZR\005\022",5,18)
    request.AddParm('O',0,self)
    request.AddParm('e',1,self._propkey(propKey,2))
    request.AddParm('B',2,value)
    response = self.transport.Xcall(request)
  def SetAvailability(
    self,
    availability
    ):
    request = XCallRequest("ZR\005\023",5,19)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Contact.AVAILABILITY[availability])
    response = self.transport.Xcall(request)
  def SetStandby(
    self,
    standby
    ):
    request = XCallRequest("ZR\005\220\001",5,144)
    request.AddParm('O',0,self)
    request.AddParm('b',1,standby)
    response = self.transport.Xcall(request)
  def GetCapabilityStatus(
    self,
    capability
    ):
    request = XCallRequest("ZR\005\025",5,21)
    request.AddParm('O',0,self)
    request.AddParm('e',1,Contact.CAPABILITY[capability])
    response = self.transport.Xcall(request)
    result  = (Account.CAPABILITYSTATUS[response.get(1)]),
    result += (response.get(2,0)),
    return result
  def GetSkypenameHash(self):
    request = XCallRequest("ZR\005\026",5,22)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def Delete(self):
    request = XCallRequest("ZR\005\030",5,24)
    request.AddParm('O',0,self)
    response = self.transport.Xcall(request)
  def mget_profile(self):
    self.multiget("ZG\004,\005,\032,\020,\015,\016,\017,\007,\010,\011,\012,\013,\014,\021,\022,\033]\005")
module_id2classes[5] = Account
class SkyLib(object):
  module_id = 0
  event_handlers = {}
  def __init__(self, transport):
    self.object_id = 0
    self.transport = transport
    transport.setRoot(self)
  ''' Stop background operations (background threads). Might take some time.
  '''
  def Stop(self):
    self.transport.Stop()

  def _propkey(self, propname, t):
    for p,l in Contact.propid2label.items():
      if l == propname: return p*4+t
    for p,l in Account.propid2label.items():
      if l == propname: return p*4+t
    raise Error('Unknown ' + propname)
  def GetHardwiredContactGroup(
    self,
    type
    ):
    request = XCallRequest("ZR\000\001",0,1)
    request.AddParm('e',1,ContactGroup.TYPE[type])
    response = self.transport.Xcall(request)
    result  = module_id2classes[10](response.get(1),self.transport)
    return result
  def GetCustomContactGroups(self):
    request = XCallRequest("ZR\000\002",0,2)
    response = self.transport.Xcall(request)
    result  = [module_id2classes[10](oid,self.transport) for oid in response.get(1,[])]
    return result
  def CreateCustomContactGroup(self):
    request = XCallRequest("ZR\000\003",0,3)
    response = self.transport.Xcall(request)
    result  = module_id2classes[10](response.get(1),self.transport)
    return result
  def OnNewCustomContactGroup(
    self,
    group
    ): pass
  event_handlers[1] = "OnNewCustomContactGroupDispatch"
  def OnNewCustomContactGroupDispatch(self, parms):
    cleanparms = module_id2classes[10](parms.get(1),self.transport)
    self.OnNewCustomContactGroup(cleanparms)
  def mget_info_from_Contacts(self, objects):
    self.transport.multiget("ZG\042,\025]\002",objects)
  def GetContactType(
    self,
    identity
    ):
    request = XCallRequest("ZR\000\005",0,5)
    request.AddParm('S',1,identity)
    response = self.transport.Xcall(request)
    result  = Contact.TYPE[response.get(1)]
    return result
  def GetContact(
    self,
    identity
    ):
    request = XCallRequest("ZR\000\006",0,6)
    request.AddParm('S',1,identity)
    response = self.transport.Xcall(request)
    result  = module_id2classes[2](response.get(2),self.transport)
    return result
  def FindContactByPstnNumber(
    self,
    number
    ):
    request = XCallRequest("ZR\000\010",0,8)
    request.AddParm('S',1,number)
    response = self.transport.Xcall(request)
    result  = (response.get(1,False)),
    result += (module_id2classes[2](response.get(2),self.transport)),
    result += (response.get(3,0)),
    return result
  IDENTITYTYPE= {
    0:'UNRECOGNIZED',
    1:'SKYPE',
    2:'SKYPE_MYSELF',
    3:'SKYPE_UNDISCLOSED',
    4:'PSTN',
    5:'PSTN_EMERGENCY',
    6:'PSTN_FREE',
    7:'PSTN_UNDISCLOSED',
    8:'CONFERENCE',
    9:'EXTERNAL',
    'UNRECOGNIZED'                                      :0,
    'SKYPE'                                             :1,
    'SKYPE_MYSELF'                                      :2,
    'SKYPE_UNDISCLOSED'                                 :3,
    'PSTN'                                              :4,
    'PSTN_EMERGENCY'                                    :5,
    'PSTN_FREE'                                         :6,
    'PSTN_UNDISCLOSED'                                  :7,
    'CONFERENCE'                                        :8,
    'EXTERNAL'                                          :9
  }
  def GetIdentityType(
    self,
    identity
    ):
    request = XCallRequest("ZR\000\023",0,19)
    request.AddParm('S',1,identity)
    response = self.transport.Xcall(request)
    result  = SkyLib.IDENTITYTYPE[response.get(1)]
    return result
  NORMALIZERESULT= {0:'IDENTITY_OK', 'IDENTITY_OK':0, 1:'IDENTITY_EMPTY', 'IDENTITY_EMPTY':1, 2:'IDENTITY_TOO_LONG', 'IDENTITY_TOO_LONG':2, 3:'IDENTITY_CONTAINS_INVALID_CHAR', 'IDENTITY_CONTAINS_INVALID_CHAR':3, 4:'PSTN_NUMBER_TOO_SHORT', 'PSTN_NUMBER_TOO_SHORT':4, 5:'PSTN_NUMBER_HAS_INVALID_PREFIX', 'PSTN_NUMBER_HAS_INVALID_PREFIX':5, 6:'SKYPENAME_STARTS_WITH_NONALPHA', 'SKYPENAME_STARTS_WITH_NONALPHA':6, 7:'SKYPENAME_SHORTER_THAN_6_CHARS', 'SKYPENAME_SHORTER_THAN_6_CHARS':7}
  def NormalizeIdentity(
    self,
    original,
    isNewSkypeName
    ):
    request = XCallRequest("ZR\000\011",0,9)
    request.AddParm('S',1,original)
    request.AddParm('b',2,isNewSkypeName)
    response = self.transport.Xcall(request)
    result  = (SkyLib.NORMALIZERESULT[response.get(1)]),
    result += (response.get(2,'')),
    return result
  def NormalizePSTNWithCountry(
    self,
    original,
    countryPrefix
    ):
    request = XCallRequest("ZR\000\315\001",0,205)
    request.AddParm('S',1,original)
    request.AddParm('u',2,countryPrefix)
    response = self.transport.Xcall(request)
    result  = (SkyLib.NORMALIZERESULT[response.get(1)]),
    result += (response.get(2,'')),
    return result
  def OnContactOnlineAppearance(
    self,
    contact
    ): pass
  event_handlers[2] = "OnContactOnlineAppearanceDispatch"
  def OnContactOnlineAppearanceDispatch(self, parms):
    cleanparms = module_id2classes[2](parms.get(1),self.transport)
    self.OnContactOnlineAppearance(cleanparms)
  def OnContactGoneOffline(
    self,
    contact
    ): pass
  event_handlers[3] = "OnContactGoneOfflineDispatch"
  def OnContactGoneOfflineDispatch(self, parms):
    cleanparms = module_id2classes[2](parms.get(1),self.transport)
    self.OnContactGoneOffline(cleanparms)
  def GetOptimalAgeRanges(self):
    request = XCallRequest("ZR\000M",0,77)
    response = self.transport.Xcall(request)
    result  = response.get(1,[])
    return result
  def CreateContactSearch(self):
    request = XCallRequest("ZR\000\012",0,10)
    response = self.transport.Xcall(request)
    result  = module_id2classes[1](response.get(1),self.transport)
    return result
  def CreateBasicContactSearch(
    self,
    text
    ):
    request = XCallRequest("ZR\000\013",0,11)
    request.AddParm('S',1,text)
    response = self.transport.Xcall(request)
    result  = module_id2classes[1](response.get(1),self.transport)
    return result
  def CreateIdentitySearch(
    self,
    identity
    ):
    request = XCallRequest("ZR\000\014",0,12)
    request.AddParm('S',1,identity)
    response = self.transport.Xcall(request)
    result  = module_id2classes[1](response.get(1),self.transport)
    return result
  TRANSFER_SENDFILE_ERROR= {0:'TRANSFER_OPEN_SUCCESS', 'TRANSFER_OPEN_SUCCESS':0, 1:'TRANSFER_BAD_FILENAME', 'TRANSFER_BAD_FILENAME':1, 2:'TRANSFER_OPEN_FAILED', 'TRANSFER_OPEN_FAILED':2, 3:'TRANSFER_TOO_MANY_PARALLEL', 'TRANSFER_TOO_MANY_PARALLEL':3}
  def mget_info_from_Participants(self, objects):
    self.transport.multiget("ZG\247\007,\246\007,\250\007,\244\007,\266\007,\252\007]\023",objects)
  def mget_info_from_Conversations(self, objects):
    self.transport.multiget("ZG\234\007,\320\007,\240\007]\022",objects)
  def CreateConference(self):
    request = XCallRequest("ZR\000\015",0,13)
    response = self.transport.Xcall(request)
    result  = module_id2classes[18](response.get(1),self.transport)
    return result
  def GetConversationByIdentity(
    self,
    convoIdentity
    ):
    request = XCallRequest("ZR\000\017",0,15)
    request.AddParm('S',1,convoIdentity)
    response = self.transport.Xcall(request)
    result  = module_id2classes[18](response.get(1),self.transport)
    return result
  def GetConversationByParticipants(
    self,
    participantIdentities,
    createIfNonExisting,
    ignoreBookmarkedOrNamed
    ):
    request = XCallRequest("ZR\000\020",0,16)
    request.AddParm('S',1,participantIdentities)
    request.AddParm('b',2,createIfNonExisting)
    request.AddParm('b',3,ignoreBookmarkedOrNamed)
    response = self.transport.Xcall(request)
    result  = module_id2classes[18](response.get(1),self.transport)
    return result
  def GetConversationByBlob(
    self,
    joinBlob,
    alsoJoin
    ):
    request = XCallRequest("ZR\000\021",0,17)
    request.AddParm('S',1,joinBlob)
    request.AddParm('b',2,alsoJoin)
    response = self.transport.Xcall(request)
    result  = module_id2classes[18](response.get(1),self.transport)
    return result
  def GetConversationList(
    self,
    type
    ):
    request = XCallRequest("ZR\000\022",0,18)
    request.AddParm('e',1,Conversation.LIST_TYPE[type])
    response = self.transport.Xcall(request)
    result  = [module_id2classes[18](oid,self.transport) for oid in response.get(1,[])]
    return result
  def OnConversationListChange(
    self,
    conversation,
    type,
    added
    ): pass
  event_handlers[4] = "OnConversationListChangeDispatch"
  def OnConversationListChangeDispatch(self, parms):
    cleanparms  = (module_id2classes[18](parms.get(1),self.transport)),
    cleanparms += (Conversation.LIST_TYPE[parms.get(2)]),
    cleanparms += (parms.get(3,False)),
    self.OnConversationListChange(*cleanparms)
  def mget_info_from_Messages(self, objects):
    self.transport.multiget("ZG\300\007,{,\301\007,\177,y]\011",objects)
  def GetMessageByGuid(
    self,
    guid
    ):
    request = XCallRequest("ZR\000\025",0,21)
    request.AddParm('B',1,guid)
    response = self.transport.Xcall(request)
    result  = module_id2classes[9](response.get(1),self.transport)
    return result
  def OnMessage(
    self,
    message,
    changesInboxTimestamp,
    supersedesHistoryMessage,
    conversation
    ): pass
  event_handlers[5] = "OnMessageDispatch"
  def OnMessageDispatch(self, parms):
    cleanparms  = (module_id2classes[9](parms.get(1),self.transport)),
    cleanparms += (parms.get(2,False)),
    cleanparms += (module_id2classes[9](parms.get(3),self.transport)),
    cleanparms += (module_id2classes[18](parms.get(4),self.transport)),
    self.OnMessage(*cleanparms)
    cleanparms[3].OnMessage(cleanparms[0])
  def GetAvailableVideoDevices(self):
    request = XCallRequest("ZR\000P",0,80)
    response = self.transport.Xcall(request)
    result  = (response.get(1,[])),
    result += (response.get(2,[])),
    result += (response.get(3,0)),
    return result
  def HasVideoDeviceCapability(
    self,
    deviceName,
    devicePath,
    cap
    ):
    request = XCallRequest("ZR\000!",0,33)
    request.AddParm('S',1,deviceName)
    request.AddParm('S',2,devicePath)
    request.AddParm('e',3,Video.VIDEO_DEVICE_CAPABILITY[cap])
    response = self.transport.Xcall(request)
  def DisplayVideoDeviceTuningDialog(
    self,
    deviceName,
    devicePath
    ):
    request = XCallRequest("ZR\000\042",0,34)
    request.AddParm('S',1,deviceName)
    request.AddParm('S',2,devicePath)
    response = self.transport.Xcall(request)
  def GetLocalVideo(
    self,
    type,
    deviceName,
    devicePath
    ):
    request = XCallRequest("ZR\000\203\001",0,131)
    request.AddParm('e',1,Video.MEDIATYPE[type])
    request.AddParm('S',2,deviceName)
    request.AddParm('S',3,devicePath)
    response = self.transport.Xcall(request)
    result  = module_id2classes[11](response.get(1),self.transport)
    return result
  def GetPreviewVideo(
    self,
    type,
    deviceName,
    devicePath
    ):
    request = XCallRequest("ZR\000#",0,35)
    request.AddParm('e',1,Video.MEDIATYPE[type])
    request.AddParm('S',2,deviceName)
    request.AddParm('S',3,devicePath)
    response = self.transport.Xcall(request)
    result  = module_id2classes[11](response.get(1),self.transport)
    return result
  def VideoCommand(
    self,
    command
    ):
    request = XCallRequest("ZR\000;",0,59)
    request.AddParm('S',1,command)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def OnAvailableVideoDeviceListChange(self): pass
  def OnAvailableVideoDeviceListChangeDispatch(self, parms): self.OnAvailableVideoDeviceListChange()
  event_handlers[7] = "OnAvailableVideoDeviceListChangeDispatch"
  def GetGreeting(
    self,
    skypeName
    ):
    request = XCallRequest("ZR\000-",0,45)
    request.AddParm('S',1,skypeName)
    response = self.transport.Xcall(request)
    result  = module_id2classes[7](response.get(1),self.transport)
    return result
  PREPARESOUNDRESULT= {0:'PREPARESOUND_SUCCESS', 'PREPARESOUND_SUCCESS':0, 1:'PREPARESOUND_MISC_ERROR', 'PREPARESOUND_MISC_ERROR':1, 2:'PREPARESOUND_FILE_NOT_FOUND', 'PREPARESOUND_FILE_NOT_FOUND':2, 3:'PREPARESOUND_FILE_TOO_BIG', 'PREPARESOUND_FILE_TOO_BIG':3, 4:'PREPARESOUND_FILE_READ_ERROR', 'PREPARESOUND_FILE_READ_ERROR':4, 5:'PREPARESOUND_UNSUPPORTED_FILE_FORMAT', 'PREPARESOUND_UNSUPPORTED_FILE_FORMAT':5, 6:'PREPARESOUND_PLAYBACK_NOT_SUPPORTED', 'PREPARESOUND_PLAYBACK_NOT_SUPPORTED':6}
  AUDIODEVICE_CAPABILIES= {
    1   :'HAS_VIDEO_CAPTURE',
    2   :'HAS_USB_INTERFACE',
    4   :'POSSIBLY_HEADSET',
    8   :'HAS_AUDIO_CAPTURE',
    16  :'HAS_AUDIO_RENDERING',
    32  :'HAS_LOWBANDWIDTH_CAPTURE',
    64  :'IS_WEBCAM',
    128 :'IS_HEADSET',
    256 :'POSSIBLY_WEBCAM',
    2048:'HAS_VIDEO_RENDERING',
    4096:'HAS_BLUETOOTH_INTERFACE',
    'HAS_VIDEO_CAPTURE'                                 :   1,
    'HAS_USB_INTERFACE'                                 :   2,
    'POSSIBLY_HEADSET'                                  :   4,
    'HAS_AUDIO_CAPTURE'                                 :   8,
    'HAS_AUDIO_RENDERING'                               :  16,
    'HAS_LOWBANDWIDTH_CAPTURE'                          :  32,
    'IS_WEBCAM'                                         :  64,
    'IS_HEADSET'                                        : 128,
    'POSSIBLY_WEBCAM'                                   : 256,
    'HAS_VIDEO_RENDERING'                               :2048,
    'HAS_BLUETOOTH_INTERFACE'                           :4096
  }
  def PlayStart(
    self,
    soundid,
    sound,
    loop,
    useCallOutDevice
    ):
    request = XCallRequest("ZR\000\060",0,48)
    request.AddParm('u',1,soundid)
    request.AddParm('B',2,sound)
    request.AddParm('b',3,loop)
    request.AddParm('b',4,useCallOutDevice)
    response = self.transport.Xcall(request)
  def PlayStartFromFile(
    self,
    soundid,
    datafile,
    loop,
    useCallOutDevice
    ):
    request = XCallRequest("ZR\000\324\001",0,212)
    request.AddParm('u',1,soundid)
    request.AddParm('f',2,datafile)
    request.AddParm('b',3,loop)
    request.AddParm('b',4,useCallOutDevice)
    response = self.transport.Xcall(request)
    result  = SkyLib.PREPARESOUNDRESULT[response.get(1)]
    return result
  def PlayStop(
    self,
    soundid
    ):
    request = XCallRequest("ZR\000\061",0,49)
    request.AddParm('u',1,soundid)
    response = self.transport.Xcall(request)
  def StartRecordingTest(
    self,
    recordAndPlaybackData
    ):
    request = XCallRequest("ZR\000\062",0,50)
    request.AddParm('b',1,recordAndPlaybackData)
    response = self.transport.Xcall(request)
  def StopRecordingTest(self):
    request = XCallRequest("ZR\000\063",0,51)
    response = self.transport.Xcall(request)
  def GetAvailableOutputDevices(self):
    request = XCallRequest("ZR\000\065",0,53)
    response = self.transport.Xcall(request)
    result  = (response.get(1,[])),
    result += (response.get(2,[])),
    result += (response.get(3,[])),
    return result
  def GetAvailableRecordingDevices(self):
    request = XCallRequest("ZR\000\066",0,54)
    response = self.transport.Xcall(request)
    result  = (response.get(1,[])),
    result += (response.get(2,[])),
    result += (response.get(3,[])),
    return result
  def SelectSoundDevices(
    self,
    callInDevice,
    callOutDevice,
    waveOutDevice
    ):
    request = XCallRequest("ZR\000\067",0,55)
    request.AddParm('S',1,callInDevice)
    request.AddParm('S',2,callOutDevice)
    request.AddParm('S',3,waveOutDevice)
    response = self.transport.Xcall(request)
  def GetAudioDeviceCapabilities(
    self,
    deviceHandle
    ):
    request = XCallRequest("ZR\000\070",0,56)
    request.AddParm('S',1,deviceHandle)
    response = self.transport.Xcall(request)
    result  = (response.get(1,'')),
    result += (response.get(2,0)),
    return result
  def GetNrgLevels(self):
    request = XCallRequest("ZR\000\071",0,57)
    response = self.transport.Xcall(request)
    result  = (response.get(1,0)),
    result += (response.get(2,0)),
    return result
  def VoiceCommand(
    self,
    command
    ):
    request = XCallRequest("ZR\000:",0,58)
    request.AddParm('S',1,command)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def GetSpeakerVolume(self):
    request = XCallRequest("ZR\000<",0,60)
    response = self.transport.Xcall(request)
    result  = response.get(1,0)
    return result
  def SetSpeakerVolume(
    self,
    volume
    ):
    request = XCallRequest("ZR\000=",0,61)
    request.AddParm('u',1,volume)
    response = self.transport.Xcall(request)
  def GetMicVolume(self):
    request = XCallRequest("ZR\000>",0,62)
    response = self.transport.Xcall(request)
    result  = response.get(1,0)
    return result
  def SetMicVolume(
    self,
    volume
    ):
    request = XCallRequest("ZR\000?",0,63)
    request.AddParm('u',1,volume)
    response = self.transport.Xcall(request)
  def IsSpeakerMuted(self):
    request = XCallRequest("ZR\000@",0,64)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def IsMicrophoneMuted(self):
    request = XCallRequest("ZR\000\101",0,65)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def MuteSpeakers(
    self,
    mute
    ):
    request = XCallRequest("ZR\000\102",0,66)
    request.AddParm('b',1,mute)
    response = self.transport.Xcall(request)
  def MuteMicrophone(
    self,
    mute
    ):
    request = XCallRequest("ZR\000\103",0,67)
    request.AddParm('b',1,mute)
    response = self.transport.Xcall(request)
  def OnAvailableDeviceListChange(self): pass
  def OnAvailableDeviceListChangeDispatch(self, parms): self.OnAvailableDeviceListChange()
  event_handlers[10] = "OnAvailableDeviceListChangeDispatch"
  def OnNrgLevelsChange(self): pass
  def OnNrgLevelsChangeDispatch(self, parms): self.OnNrgLevelsChange()
  event_handlers[11] = "OnNrgLevelsChangeDispatch"
  def CreateOutgoingSms(self):
    request = XCallRequest("ZR\000\106",0,70)
    response = self.transport.Xcall(request)
    result  = module_id2classes[12](response.get(1),self.transport)
    return result
  def GetValidatedSmsNumbers(self):
    request = XCallRequest("ZR\000H",0,72)
    response = self.transport.Xcall(request)
    result  = response.get(1,[])
    return result
  SETUPKEY_FT_AUTOACCEPT="Lib/FileTransfer/AutoAccept"
  SETUPKEY_FT_SAVEPATH="Lib/FileTransfer/SavePath"
  SETUPKEY_FT_INCOMING_LIMIT="Lib/FileTransfer/IncomingLimit"
  SETUPKEY_IDLE_TIME_FOR_AWAY="Lib/Account/IdleTimeForAway"
  SETUPKEY_IDLE_TIME_FOR_NA="Lib/Account/IdleTimeForNA"
  def GetAccount(
    self,
    identity
    ):
    request = XCallRequest("ZR\000s",0,115)
    request.AddParm('S',1,identity)
    response = self.transport.Xcall(request)
    result  = module_id2classes[5](response.get(1),self.transport)
    return result
  def GetExistingAccounts(self):
    request = XCallRequest("ZR\000q",0,113)
    response = self.transport.Xcall(request)
    result  = response.get(1,[])
    return result
  def GetDefaultAccountName(self):
    request = XCallRequest("ZR\000r",0,114)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def GetSuggestedSkypename(
    self,
    fullname
    ):
    request = XCallRequest("ZR\000t",0,116)
    request.AddParm('S',1,fullname)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  VALIDATERESULT= {
    0 :'NOT_VALIDATED',
    1 :'VALIDATED_OK',
    2 :'TOO_SHORT',
    3 :'TOO_LONG',
    4 :'CONTAINS_INVALID_CHAR',
    5 :'CONTAINS_SPACE',
    6 :'SAME_AS_USERNAME',
    7 :'INVALID_FORMAT',
    8 :'CONTAINS_INVALID_WORD',
    9 :'TOO_SIMPLE',
    10:'STARTS_WITH_INVALID_CHAR',
    'NOT_VALIDATED'                                     : 0,
    'VALIDATED_OK'                                      : 1,
    'TOO_SHORT'                                         : 2,
    'TOO_LONG'                                          : 3,
    'CONTAINS_INVALID_CHAR'                             : 4,
    'CONTAINS_SPACE'                                    : 5,
    'SAME_AS_USERNAME'                                  : 6,
    'INVALID_FORMAT'                                    : 7,
    'CONTAINS_INVALID_WORD'                             : 8,
    'TOO_SIMPLE'                                        : 9,
    'STARTS_WITH_INVALID_CHAR'                          :10
  }
  def ValidateAvatar(
    self,
    value
    ):
    request = XCallRequest("ZR\000w",0,119)
    request.AddParm('B',1,value)
    response = self.transport.Xcall(request)
    result  = (SkyLib.VALIDATERESULT[response.get(1)]),
    result += (response.get(2,0)),
    return result
  def ValidateProfileString(
    self,
    propKey,
    strValue,
    forRegistration
    ):
    request = XCallRequest("ZR\000f",0,102)
    request.AddParm('e',1,self._propkey(propKey,0))
    request.AddParm('S',2,strValue)
    request.AddParm('b',3,forRegistration)
    response = self.transport.Xcall(request)
    result  = (SkyLib.VALIDATERESULT[response.get(1)]),
    result += (response.get(2,0)),
    return result
  def ValidatePassword(
    self,
    username,
    password
    ):
    request = XCallRequest("ZR\000G",0,71)
    request.AddParm('S',1,username)
    request.AddParm('S',2,password)
    response = self.transport.Xcall(request)
    result  = SkyLib.VALIDATERESULT[response.get(1)]
    return result
  def SetApplicationToken(
    self,
    applicationToken
    ):
    request = XCallRequest("ZR\000\201\001",0,129)
    request.AddParm('S',1,applicationToken)
    response = self.transport.Xcall(request)
  def GetStr(
    self,
    key
    ):
    request = XCallRequest("ZR\000x",0,120)
    request.AddParm('S',1,key)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def GetInt(
    self,
    key
    ):
    request = XCallRequest("ZR\000y",0,121)
    request.AddParm('S',1,key)
    response = self.transport.Xcall(request)
    result  = response.get(1,0)
    return result
  def GetBin(
    self,
    key
    ):
    request = XCallRequest("ZR\000z",0,122)
    request.AddParm('S',1,key)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result
  def SetStr(
    self,
    key,
    value
    ):
    request = XCallRequest("ZR\000{",0,123)
    request.AddParm('S',1,key)
    request.AddParm('S',2,value)
    response = self.transport.Xcall(request)
  def SetInt(
    self,
    key,
    value
    ):
    request = XCallRequest("ZR\000|",0,124)
    request.AddParm('S',1,key)
    request.AddParm('i',2,value)
    response = self.transport.Xcall(request)
  def SetBin(
    self,
    key,
    value
    ):
    request = XCallRequest("ZR\000}",0,125)
    request.AddParm('S',1,key)
    request.AddParm('B',2,value)
    response = self.transport.Xcall(request)
  def IsDefined(
    self,
    key
    ):
    request = XCallRequest("ZR\000~",0,126)
    request.AddParm('S',1,key)
    response = self.transport.Xcall(request)
    result  = response.get(1,False)
    return result
  def Delete(
    self,
    key
    ):
    request = XCallRequest("ZR\000\177",0,127)
    request.AddParm('S',1,key)
    response = self.transport.Xcall(request)
  def GetSubKeys(
    self,
    key
    ):
    request = XCallRequest("ZR\000\200\001",0,128)
    request.AddParm('S',1,key)
    response = self.transport.Xcall(request)
    result  = response.get(1,[])
    return result
  def GetISOLanguageInfo(self):
    request = XCallRequest("ZR\000\317\001",0,207)
    response = self.transport.Xcall(request)
    result  = (response.get(1,[])),
    result += (response.get(2,[])),
    return result
  def GetISOCountryInfo(self):
    request = XCallRequest("ZR\000\320\001",0,208)
    response = self.transport.Xcall(request)
    result  = (response.get(1,[])),
    result += (response.get(2,[])),
    result += (response.get(3,[])),
    result += (response.get(4,[])),
    return result
  def GetISOCountryCodebyPhoneNo(
    self,
    number
    ):
    request = XCallRequest("ZR\000\323\001",0,211)
    request.AddParm('S',1,number)
    response = self.transport.Xcall(request)
    result  = response.get(1,'')
    return result

def GetSkyLib(has_event_thread = True, host = '127.0.0.1', port = 8963, logging_level = logging.NOTSET, logging_file = LOG_FILENAME,logtransport=False):
  return SkyLib(SkypeKit(has_event_thread, host, port, logging_level, logging_file, "SKYPEKIT[19.943 19.942 19.951]",logtransport))
