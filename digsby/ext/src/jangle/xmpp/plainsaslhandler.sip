namespace buzz {

class PlainSaslHandler : /*public*/ buzz::SaslHandler {

%TypeHeaderCode
#include "talk/xmpp/saslplainmechanism.h"
#include "talk/xmpp/plainsaslhandler.h"
%End

public:
  PlainSaslHandler(const buzz::Jid & jid, const talk_base::CryptString & password,
      bool allow_plain);

  virtual ~PlainSaslHandler();

  // Should pick the best method according to this handler
  // returns the empty string if none are suitable
  virtual std::string ChooseBestSaslMechanism(const std::vector<std::string> & mechanisms, bool encrypted);

  // Creates a SaslMechanism for the given mechanism name (you own it
  // once you get it).  If not handled, return NULL.
  virtual buzz::SaslMechanism * CreateSaslMechanism(const std::string & mechanism);

/*
private:
  Jid jid_;
  talk_base::CryptString password_;
  bool allow_plain_;
*/
};


};