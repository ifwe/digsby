namespace buzz {

class SaslPlainMechanism : /*public*/ buzz::SaslMechanism {

%TypeHeaderCode
#include "talk/xmpp/saslplainmechanism.h"
%End

public:
  SaslPlainMechanism(const buzz::Jid user_jid, const talk_base::CryptString & password);

  virtual std::string GetMechanismName();

  virtual buzz::XmlElement * StartSaslAuth();
/*
private:
  Jid user_jid_;
  talk_base::CryptString password_;
*/
};

};