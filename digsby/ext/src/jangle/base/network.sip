
namespace talk_base {

/*
// Keeps track of the available network interfaces over time so that quality
// information can be aggregated and recorded.
class NetworkManager {

%TypeHeaderCode
#include "talk/base/network.h"
%End
public:

  // Updates and returns the current list of networks available on this machine.
  // This version will make sure that repeated calls return the same object for
  // a given network, so that quality is tracked appropriately.
  void GetNetworks(std::vector<Network*>& networks);

  // Reads and writes the state of the quality database in a string format.
  std::string GetState();
  void SetState(std::string str);

  // Creates a network object for each network available on the machine.
  static void CreateNetworks(std::vector<Network*>& networks);

private:
  typedef std::map<std::string,Network*> NetworkMap;

  NetworkMap networks_;

};

// Represents a Unix-type network interface, with a name and single address.
// It also includes the ability to track and estimate quality.
class Network {

%TypeHeaderCode
#include "talk/base/network.h"
%End

public:
  Network(const std::string& name, uint32 ip);

  // Returns the OS name of this network.  This is considered the primary key
  // that identifies each network.
  const std::string& name() const;

  // Identifies the current IP address used by this network.
  uint32 ip() const;
  void set_ip(uint32 ip);

  // Updates the list of sessions that are ongoing.
  void StartSession(NetworkSession* session);
  void StopSession(NetworkSession* session);

  // Re-computes the estimate of near-future quality based on the information
  // as of this exact moment.
  void EstimateQuality();

  // Returns the current estimate of the near-future quality of connections
  // that use this local interface.
  double quality();

  // Debugging description of this network
  std::string ToString() const;

private:
  typedef std::vector<NetworkSession*> SessionList;

  std::string name_;
  uint32 ip_;
  SessionList sessions_;
  double uniform_numerator_;
  double uniform_denominator_;
  double exponential_numerator_;
  double exponential_denominator_;
  uint32 last_data_time_;
  double quality_;

  // Updates the statistics maintained to include the given estimate.
  void AddDataPoint(uint32 time, double quality);

  // Converts the internal state to and from a string.  This is used to record
  // quality information into a permanent store.
  void SetState(std::string str);
  std::string GetState();

  friend class NetworkManager;

};

// Represents a session that is in progress using a particular network and can
// provide data about the quality of the network at any given moment.
class NetworkSession {
public:
  // Determines whether this session has an estimate at this moment.  We will
  // only call GetCurrentQuality when this returns true.
  virtual bool HasQuality() = 0;

  // Returns an estimate of the quality at this exact moment.  The result should
  // be a MOS (mean opinion score) value.
  virtual float GetCurrentQuality() = 0;

};
*/

const double QUALITY_BAD;
const double QUALITY_FAIR;
const double QUALITY_GOOD;

}; // namespace talk_base
