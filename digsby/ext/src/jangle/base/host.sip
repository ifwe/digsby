/*
namespace talk_base {

// Provides information about a host in the network.
class Host {

%TypeHeaderCode
#include "talk/base/host.h"
%End

public:
  Host(const std::string& name, std::vector<Network*>* networks);

  const std::string& name() const;
  const std::vector<Network*>& networks() const;

private:
  std::string name_;
  std::vector<Network*>* networks_;

};

// Returns a reference to the description of the local host.
const talk_base::Host& LocalHost();

// Returns the name of the local host.
std::string GetHostName();

}; // namespace talk_base

*/
