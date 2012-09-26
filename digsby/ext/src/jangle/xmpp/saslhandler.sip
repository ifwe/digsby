%ModuleHeaderCode
#include <vector>
%End

namespace buzz {

class SaslHandler {

%TypeHeaderCode
#include "talk/xmpp/saslhandler.h"
%End

public:

  // Intended to be subclassed
  virtual ~SaslHandler();

  // Should pick the best method according to this handler
  // returns the empty string if none are suitable
  virtual std::string ChooseBestSaslMechanism(const std::vector<std::string> & mechanisms, bool encrypted) = 0;

  // Creates a SaslMechanism for the given mechanism name (you own it
  // once you get it).
  // If not handled, return NULL.
  virtual buzz::SaslMechanism * CreateSaslMechanism(const std::string & mechanism) = 0;

};

};