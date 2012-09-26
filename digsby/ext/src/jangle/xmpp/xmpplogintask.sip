namespace buzz {

class XmppLoginTask {

%TypeHeaderCode
#include "talk/xmpp/xmpplogintask.h"
%End

public:
  XmppLoginTask(buzz::XmppEngineImpl *pctx);
  ~XmppLoginTask();

  bool IsDone();
  void IncomingStanza(const buzz::XmlElement * element, bool isStart);
  void OutgoingStanza(const buzz::XmlElement *element);

private:
    XmppLoginTask();
    XmppLoginTask(const buzz::XmppLoginTask &);
/*
  enum LoginTaskState {
    LOGINSTATE_INIT = 0,
    LOGINSTATE_STREAMSTART_SENT,
    LOGINSTATE_STARTED_XMPP,
    LOGINSTATE_TLS_INIT,
    LOGINSTATE_AUTH_INIT,
    LOGINSTATE_BIND_INIT,
    LOGINSTATE_TLS_REQUESTED,
    LOGINSTATE_SASL_RUNNING,
    LOGINSTATE_BIND_REQUESTED,
    LOGINSTATE_SESSION_REQUESTED,
    LOGINSTATE_DONE,
  };
*/
  const buzz::XmlElement * NextStanza();
  bool Advance();
  bool HandleStartStream(const buzz::XmlElement * element);
  bool HandleFeatures(const buzz::XmlElement * element);
  const buzz::XmlElement * GetFeature(const buzz::QName & name);
  bool Failure(buzz::XmppEngine::Error reason);
  void FlushQueuedStanzas();

/*
  XmppEngineImpl * pctx_;
  bool authNeeded_;
  LoginTaskState state_;
  const XmlElement * pelStanza_;
  bool isStart_;
  std::string iqId_;
  scoped_ptr<XmlElement> pelFeatures_;
  Jid fullJid_;
  std::string streamId_;
  scoped_ptr<std::vector<XmlElement *,
          std::allocator<XmlElement *> > > pvecQueuedStanzas_;

  scoped_ptr<SaslMechanism> sasl_mech_;

#ifdef _DEBUG
  static const talk_base::ConstantLabel LOGINTASK_STATES[];
#endif  // _DEBUG

*/
};

};
