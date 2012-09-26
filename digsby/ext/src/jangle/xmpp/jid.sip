
namespace buzz {

class Jid {

%TypeHeaderCode
#include "talk/xmpp/jid.h"
%End

public:
  explicit Jid();
  explicit Jid(const std::string & jid_string);
  explicit Jid(const std::string & node_name,
               const std::string & domain_name,
               const std::string & resource_name);
  explicit Jid(bool special, const std::string & special_string);
  Jid(const buzz::Jid & jid);

//  Jid & operator=(const buzz::Jid & jid);

  const std::string & node();
  const std::string & domain();
  const std::string & resource();

  std::string Str();

  bool IsValid() const;
  bool IsBare() const;
  bool IsFull() const;

  bool BareEquals(const buzz::Jid & other) const;

  bool operator==(const buzz::Jid & other) const;
  bool operator!=(const buzz::Jid & other) const;

  bool operator<(const buzz::Jid & other) const;
  bool operator>(const buzz::Jid & other) const;

  int Compare(const buzz::Jid & other) const;

  // A quick and dirty hash.  Don't count on this producing a great
  // distribution.
  uint32 ComputeLameHash() const;

};

};

