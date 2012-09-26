namespace buzz {

class SaslCookieMechanism : /*public*/ buzz::SaslMechanism {

%TypeHeaderCode
#include "talk/xmpp/saslcookiemechanism.h"
%End

public:
  SaslCookieMechanism(const std::string & mechanism, const std::string & username, const std::string & cookie);

  virtual std::string GetMechanismName();

  virtual buzz::XmlElement * StartSaslAuth();

/*
private:
  std::string mechanism_;
  std::string username_;
  std::string cookie_;
*/
};

};