


namespace buzz {

class XmppClient : talk_base::Task
{

%TypeHeaderCode
#include "talk/xmpp/xmppclient.h"
#include "talk/xmpp/xmppengine.h"
%End

public:
  XmppClient(talk_base::Task * parent);
  ~XmppClient();

  buzz::XmppReturnStatus Connect(const buzz::XmppClientSettings & settings,
                           const std::string & lang,
                           buzz::AsyncSocket * socket,
                           buzz::PreXmppAuth * preauth);

  virtual talk_base::Task* GetParent(int code);
  virtual int ProcessStart();
  virtual int ProcessResponse();
  buzz::XmppReturnStatus Disconnect();

  const buzz::Jid & jid();
%MethodCode
      if (!sipCpp->engine()) {
          PyErr_SetString(PyExc_AssertionError, "No engine");
          sipIsErr = 1;
      } else {
        // stuff       
        sipRes = new buzz::Jid(sipCpp->jid());
      }
%End

//  sigslot::signal1<XmppEngine::State> SignalStateChange;

  buzz::XmppEngine::State GetState();
  buzz::XmppEngine::Error GetError(int *subcode);

  // When there is a <stream:error> stanza, return the stanza
  // so that they can be handled.
  const buzz::XmlElement *GetStreamError();

  // When there is an authentication error, we may have captcha info
  // that the user can use to unlock their account
  buzz::CaptchaChallenge GetCaptchaChallenge();

  // When authentication is successful, this returns the service cookie
  // (if we used GAIA authentication)
  std::string GetAuthCookie();

  std::string NextId();
  buzz::XmppReturnStatus SendStanza(const buzz::XmlElement *stanza);
  buzz::XmppReturnStatus SendRaw(const std::string & text);
  buzz::XmppReturnStatus SendStanzaError(const buzz::XmlElement * pelOriginal,
                       buzz::XmppStanzaError code,
                       const std::string & text);

  buzz::XmppEngine* engine();

//  sigslot::signal2<const char *, int> SignalLogInput;
//  sigslot::signal2<const char *, int> SignalLogOutput;

};

};