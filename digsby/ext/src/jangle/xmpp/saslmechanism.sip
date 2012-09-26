


namespace buzz {

// Defines a mechnanism to do SASL authentication.
// Subclass instances should have a self-contained way to present
// credentials.
class SaslMechanism {

%TypeHeaderCode
#include "talk/xmpp/saslmechanism.h"
%End

public:

  // Intended to be subclassed
  virtual ~SaslMechanism();

  // Should return the name of the SASL mechanism, e.g., "PLAIN"
  virtual std::string GetMechanismName() = 0;

  // Should generate the initial "auth" request.  Default is just <auth/>.
  virtual buzz::XmlElement * StartSaslAuth();

  // Should respond to a SASL "<challenge>" request.  Default is
  // to abort (for mechanisms that do not do challenge-response)
  virtual buzz::XmlElement * HandleSaslChallenge(const buzz::XmlElement * challenge);

  // Notification of a SASL "<success>".  Sometimes information
  // is passed on success.
  virtual void HandleSaslSuccess(const buzz::XmlElement * success);

  // Notification of a SASL "<failure>".  Sometimes information
  // for the user is passed on failure.
  virtual void HandleSaslFailure(const buzz::XmlElement * failure);

protected:
  static std::string Base64Encode(const std::string & plain);
  static std::string Base64Decode(const std::string & encoded);
  static std::string Base64EncodeFromArray(const char * plain, size_t length);
};

};