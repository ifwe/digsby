%ModuleHeaderCode
#include "talk/xmpp/constants.h"
%End

namespace buzz {

const buzz::Jid JID_EMPTY;

class Constants {

%TypeHeaderCode
#include "talk/xmpp/constants.h"
%End

 public:
  static const std::string & ns_client();
  static const std::string & ns_server();
  static const std::string & ns_stream();
  static const std::string & ns_xstream();
  static const std::string & ns_tls();
  static const std::string & ns_sasl();
  static const std::string & ns_bind();
  static const std::string & ns_dialback();
  static const std::string & ns_session();
  static const std::string & ns_stanza();
  static const std::string & ns_privacy();
  static const std::string & ns_roster();
  static const std::string & ns_vcard();
  static const std::string & ns_avatar_hash();
  static const std::string & ns_vcard_update();

  static const std::string & str_client();
  static const std::string & str_server();
  static const std::string & str_stream();
};

const std::string STR_GET;
const std::string STR_SET;
const std::string STR_RESULT;
const std::string STR_ERROR;


const std::string STR_FROM;
const std::string STR_TO;
const std::string STR_BOTH;
const std::string STR_REMOVE;

//const std::string STR_MESSAGE;
//const std::string STR_BODY;
//const std::string STR_PRESENCE;
//const std::string STR_STATUS;
//const std::string STR_SHOW;
//const std::string STR_PRIOIRTY;
//const std::string STR_IQ;

const std::string STR_TYPE;
const std::string STR_NAME;
const std::string STR_ID;
const std::string STR_JID;
const std::string STR_SUBSCRIPTION;
const std::string STR_ASK;
const std::string STR_X;
const std::string STR_GOOGLE_COM;
const std::string STR_GMAIL_COM;
const std::string STR_GOOGLEMAIL_COM;
const std::string STR_DEFAULT_DOMAIN;
const std::string STR_TALK_GOOGLE_COM;
const std::string STR_TALKX_L_GOOGLE_COM;

//#ifdef FEATURE_ENABLE_VOICEMAIL
//const std::string STR_VOICEMAIL;
//const std::string STR_OUTGOINGVOICEMAIL;
//#endif

const std::string STR_UNAVAILABLE;

const buzz::QName QN_STREAM_STREAM;
const buzz::QName QN_STREAM_FEATURES;
const buzz::QName QN_STREAM_ERROR;

const buzz::QName QN_XSTREAM_BAD_FORMAT;
const buzz::QName QN_XSTREAM_BAD_NAMESPACE_PREFIX;
const buzz::QName QN_XSTREAM_CONFLICT;
const buzz::QName QN_XSTREAM_CONNECTION_TIMEOUT;
const buzz::QName QN_XSTREAM_HOST_GONE;
const buzz::QName QN_XSTREAM_HOST_UNKNOWN;
const buzz::QName QN_XSTREAM_IMPROPER_ADDRESSIING;
const buzz::QName QN_XSTREAM_INTERNAL_SERVER_ERROR;
const buzz::QName QN_XSTREAM_INVALID_FROM;
const buzz::QName QN_XSTREAM_INVALID_ID;
const buzz::QName QN_XSTREAM_INVALID_NAMESPACE;
const buzz::QName QN_XSTREAM_INVALID_XML;
const buzz::QName QN_XSTREAM_NOT_AUTHORIZED;
const buzz::QName QN_XSTREAM_POLICY_VIOLATION;
const buzz::QName QN_XSTREAM_REMOTE_CONNECTION_FAILED;
const buzz::QName QN_XSTREAM_RESOURCE_CONSTRAINT;
const buzz::QName QN_XSTREAM_RESTRICTED_XML;
const buzz::QName QN_XSTREAM_SEE_OTHER_HOST;
const buzz::QName QN_XSTREAM_SYSTEM_SHUTDOWN;
const buzz::QName QN_XSTREAM_UNDEFINED_CONDITION;
const buzz::QName QN_XSTREAM_UNSUPPORTED_ENCODING;
const buzz::QName QN_XSTREAM_UNSUPPORTED_STANZA_TYPE;
const buzz::QName QN_XSTREAM_UNSUPPORTED_VERSION;
const buzz::QName QN_XSTREAM_XML_NOT_WELL_FORMED;
const buzz::QName QN_XSTREAM_TEXT;

const buzz::QName QN_TLS_STARTTLS;
const buzz::QName QN_TLS_REQUIRED;
const buzz::QName QN_TLS_PROCEED;
const buzz::QName QN_TLS_FAILURE;

const buzz::QName QN_SASL_MECHANISMS;
const buzz::QName QN_SASL_MECHANISM;
const buzz::QName QN_SASL_AUTH;
const buzz::QName QN_SASL_CHALLENGE;
const buzz::QName QN_SASL_RESPONSE;
const buzz::QName QN_SASL_ABORT;
const buzz::QName QN_SASL_SUCCESS;
const buzz::QName QN_SASL_FAILURE;
const buzz::QName QN_SASL_ABORTED;
const buzz::QName QN_SASL_INCORRECT_ENCODING;
const buzz::QName QN_SASL_INVALID_AUTHZID;
const buzz::QName QN_SASL_INVALID_MECHANISM;
const buzz::QName QN_SASL_MECHANISM_TOO_WEAK;
const buzz::QName QN_SASL_NOT_AUTHORIZED;
const buzz::QName QN_SASL_TEMPORARY_AUTH_FAILURE;

const std::string NS_GOOGLE_AUTH;
const buzz::QName QN_MISSING_USERNAME;

const buzz::QName QN_DIALBACK_RESULT;
const buzz::QName QN_DIALBACK_VERIFY;

const buzz::QName QN_STANZA_BAD_REQUEST;
const buzz::QName QN_STANZA_CONFLICT;
const buzz::QName QN_STANZA_FEATURE_NOT_IMPLEMENTED;
const buzz::QName QN_STANZA_FORBIDDEN;
const buzz::QName QN_STANZA_GONE;
const buzz::QName QN_STANZA_INTERNAL_SERVER_ERROR;
const buzz::QName QN_STANZA_ITEM_NOT_FOUND;
const buzz::QName QN_STANZA_JID_MALFORMED;
const buzz::QName QN_STANZA_NOT_ACCEPTABLE;
const buzz::QName QN_STANZA_NOT_ALLOWED;
const buzz::QName QN_STANZA_PAYMENT_REQUIRED;
const buzz::QName QN_STANZA_RECIPIENT_UNAVAILABLE;
const buzz::QName QN_STANZA_REDIRECT;
const buzz::QName QN_STANZA_REGISTRATION_REQUIRED;
const buzz::QName QN_STANZA_REMOTE_SERVER_NOT_FOUND;
const buzz::QName QN_STANZA_REMOTE_SERVER_TIMEOUT;
const buzz::QName QN_STANZA_RESOURCE_CONSTRAINT;
const buzz::QName QN_STANZA_SERVICE_UNAVAILABLE;
const buzz::QName QN_STANZA_SUBSCRIPTION_REQUIRED;
const buzz::QName QN_STANZA_UNDEFINED_CONDITION;
const buzz::QName QN_STANZA_UNEXPECTED_REQUEST;
const buzz::QName QN_STANZA_TEXT;

const buzz::QName QN_BIND_BIND;
const buzz::QName QN_BIND_RESOURCE;
const buzz::QName QN_BIND_JID;

const buzz::QName QN_MESSAGE;
const buzz::QName QN_BODY;
const buzz::QName QN_SUBJECT;
const buzz::QName QN_THREAD;
const buzz::QName QN_PRESENCE;
const buzz::QName QN_SHOW;
const buzz::QName QN_STATUS;
const buzz::QName QN_LANG;
const buzz::QName QN_PRIORITY;
const buzz::QName QN_IQ;
const buzz::QName QN_ERROR;

const buzz::QName QN_SERVER_MESSAGE;
const buzz::QName QN_SERVER_BODY;
const buzz::QName QN_SERVER_SUBJECT;
const buzz::QName QN_SERVER_THREAD;
const buzz::QName QN_SERVER_PRESENCE;
const buzz::QName QN_SERVER_SHOW;
const buzz::QName QN_SERVER_STATUS;
const buzz::QName QN_SERVER_LANG;
const buzz::QName QN_SERVER_PRIORITY;
const buzz::QName QN_SERVER_IQ;
const buzz::QName QN_SERVER_ERROR;

const buzz::QName QN_SESSION_SESSION;

const buzz::QName QN_PRIVACY_QUERY;
const buzz::QName QN_PRIVACY_ACTIVE;
const buzz::QName QN_PRIVACY_DEFAULT;
const buzz::QName QN_PRIVACY_LIST;
const buzz::QName QN_PRIVACY_ITEM;
const buzz::QName QN_PRIVACY_IQ;
const buzz::QName QN_PRIVACY_MESSAGE;
const buzz::QName QN_PRIVACY_PRESENCE_IN;
const buzz::QName QN_PRIVACY_PRESENCE_OUT;

const buzz::QName QN_ROSTER_QUERY;
const buzz::QName QN_ROSTER_ITEM;
const buzz::QName QN_ROSTER_GROUP;

const buzz::QName QN_VCARD;
const buzz::QName QN_VCARD_FN;
const buzz::QName QN_VCARD_PHOTO;
const buzz::QName QN_VCARD_PHOTO_BINVAL;
const buzz::QName QN_VCARD_AVATAR_HASH;
const buzz::QName QN_VCARD_AVATAR_HASH_MODIFIED;


const buzz::QName QN_XML_LANG;

const buzz::QName QN_ENCODING;
const buzz::QName QN_VERSION;
const buzz::QName QN_TO;
const buzz::QName QN_FROM;
const buzz::QName QN_TYPE;
const buzz::QName QN_ID;
const buzz::QName QN_CODE;
const buzz::QName QN_NAME;
const buzz::QName QN_VALUE;
const buzz::QName QN_ACTION;
const buzz::QName QN_ORDER;
const buzz::QName QN_MECHANISM;
const buzz::QName QN_ASK;
const buzz::QName QN_JID;
const buzz::QName QN_SUBSCRIPTION;
const buzz::QName QN_TITLE1;
const buzz::QName QN_TITLE2;


const buzz::QName QN_XMLNS_CLIENT;
const buzz::QName QN_XMLNS_SERVER;
const buzz::QName QN_XMLNS_STREAM;

// Presence
const std::string STR_SHOW_AWAY;
const std::string STR_SHOW_CHAT;
const std::string STR_SHOW_DND;
const std::string STR_SHOW_XA;
const std::string STR_SHOW_OFFLINE;

// Subscription
const std::string STR_SUBSCRIBE;
const std::string STR_SUBSCRIBED;
const std::string STR_UNSUBSCRIBE;
const std::string STR_UNSUBSCRIBED;


// JEP 0030
const buzz::QName QN_NODE;
const buzz::QName QN_CATEGORY;
const buzz::QName QN_VAR;
const std::string NS_DISCO_INFO;
const std::string NS_DISCO_ITEMS;

const buzz::QName QN_DISCO_INFO_QUERY;
const buzz::QName QN_DISCO_IDENTITY;
const buzz::QName QN_DISCO_FEATURE;

const buzz::QName QN_DISCO_ITEMS_QUERY;
const buzz::QName QN_DISCO_ITEM;


// JEP 0115
const std::string NS_CAPS;
const buzz::QName QN_CAPS_C;
const buzz::QName QN_VER;
const buzz::QName QN_EXT;


// Avatar - JEP 0153
const std::string kNSVCard;
const buzz::QName kQnVCardX;
const buzz::QName kQnVCardPhoto;

// JEP 0172 User Nickname
const std::string kNSNickname;
const buzz::QName kQnNickname;


// JEP 0085 chat state
const std::string NS_CHATSTATE;
const buzz::QName QN_CS_ACTIVE;
const buzz::QName QN_CS_COMPOSING;
const buzz::QName QN_CS_PAUSED;
const buzz::QName QN_CS_INACTIVE;
const buzz::QName QN_CS_GONE;

// JEP 0091 Delayed Delivery
const std::string kNSDelay;
const buzz::QName kQnDelayX;
const buzz::QName kQnStamp;

// Google time stamping (higher resolution)
const std::string kNSTimestamp;
const buzz::QName kQnTime;
const buzz::QName kQnMilliseconds;


const std::string NS_JINGLE_INFO;
const buzz::QName QN_JINGLE_INFO_QUERY;
const buzz::QName QN_JINGLE_INFO_STUN;
const buzz::QName QN_JINGLE_INFO_RELAY;
const buzz::QName QN_JINGLE_INFO_SERVER;
const buzz::QName QN_JINGLE_INFO_TOKEN;
const buzz::QName QN_JINGLE_INFO_HOST;
const buzz::QName QN_JINGLE_INFO_TCP;
const buzz::QName QN_JINGLE_INFO_UDP;
const buzz::QName QN_JINGLE_INFO_TCPSSL;

};