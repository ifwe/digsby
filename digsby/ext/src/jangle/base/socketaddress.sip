
namespace talk_base {

%TypeHeaderCode
#include "talk/base/socketaddress.h"
#undef SetPort
%End

// Records an IP address and port, which are 32 and 16 bit integers,
// respectively, both in <b>host byte-order</b>.
class SocketAddress {

public:
  // Creates a missing / unknown address.
  SocketAddress();

  // Creates the address with the given host and port.  If use_dns is true,
  // the hostname will be immediately resolved to an IP (which may block for
  // several seconds if DNS is not available).  Alternately, set use_dns to
  // false, and then call Resolve() to complete resolution later, or use
  // SetResolvedIP to set the IP explictly.
  SocketAddress(const std::string& hostname, int port = 0, bool use_dns = true);

  // Creates the address with the given IP and port.
  SocketAddress(uint32 ip, int port);

  // Creates a copy of the given address.
  SocketAddress(const talk_base::SocketAddress& addr);

  // Resets to missing / unknown address.
  void Clear();

  // Replaces our address with the given one.
//  SocketAddress& operator =(const talk_base::SocketAddress& addr);

  // Changes the IP of this address to the given one, and clears the hostname.
  void SetIP(uint32 ip);

  // Changes the hostname of this address to the given one.
  // Calls Resolve and returns the result.
  bool SetIP(const std::string& hostname, bool use_dns = true);

  // Sets the IP address while retaining the hostname.  Useful for bypassing
  // DNS for a pre-resolved IP.
  void SetResolvedIP(uint32 ip);

  // Changes the port of this address to the given one.
  void SetPort(int port);

  // Returns the IP address.
  uint32 ip() const;

  // Returns the port part of this address.
  uint16 port() const;

  // Returns the hostname
  const std::string& hostname() const;

  // Returns the IP address in dotted form.
  std::string IPAsString() const;

  // Returns the port as a string
  std::string PortAsString() const;

  // Returns a display version of the IP/port.
  std::string ToString() const;

  // Determines whether this represents a missing / any address.
  bool IsAny() const;

  // Synomym for missing / any.
  bool IsNil() const;

  // Determines whether the IP address refers to the local host, i.e. within
  // the range 127.0.0.0/8.
  bool IsLocalIP() const;

  // Determines whether the IP address is in one of the private ranges:
  // 127.0.0.0/8 10.0.0.0/8 192.168.0.0/16 172.16.0.0/12.
  bool IsPrivateIP() const;

  // Determines whether the hostname has been resolved to an IP
  bool IsUnresolved() const;

  // Attempt to resolve a hostname to IP address.
  // Returns false if resolution is required but failed.
  // 'force' will cause re-resolution of hostname.
  //
  bool Resolve(bool force = false, bool use_dns = true);

  // Determines whether this address is identical to the given one.
  bool operator ==(const talk_base::SocketAddress& addr) const;

  bool operator !=(const talk_base::SocketAddress& addr) const;

  // Compares based on IP and then port.
  bool operator <(const talk_base::SocketAddress& addr) const;

  // Determines whether this address has the same IP as the one given.
  bool EqualIPs(const talk_base::SocketAddress& addr) const;

  // Deteremines whether this address has the same port as the one given.
  bool EqualPorts(const talk_base::SocketAddress& addr) const;

  // Hashes this address into a small number.
  size_t Hash() const;

  // Returns the size of this address when written.
  size_t Size_() const;

  // Writes this address into the given buffer.
  void Write_(char* buf, int len) const;

  // Reads this address from the given buffer.
  void Read_(const char* buf, int len);

  // Convert to and from sockaddr_in
//  void ToSockAddr(sockaddr_in* saddr) const;
//  void FromSockAddr(const sockaddr_in& saddr);

  // Converts the IP address given in compact form into dotted form.
  static std::string IPToString(uint32 ip);

  // Converts the IP address given in dotted form into compact form.
  // Without 'use_dns', only dotted names (A.B.C.D) are resolved.
  static uint32 StringToIP(const std::string& str, bool use_dns = true);

  // Get local machine's hostname
  static std::string GetHostname();

  // Get a list of the local machine's ip addresses
//  static bool GetLocalIPs(std::vector<uint32>& ips);
  SIP_PYLIST GetLocalIPs();
%MethodCode
      std::vector<uint32> ips;
      if (!sipCpp->GetLocalIPs(ips)) {
          PyErr_SetString(PyExc_ValueError, "couldn't retrieve ips");
          sipIsErr = 1;
      } else {
        // stuff
        sipRes = PyList_New(ips.size());
        for (int i = 0; i < ips.size(); i++) {
            PyList_SET_ITEM(sipRes, i, PyInt_FromLong(ips[i]));
        }
      }
%End

};

}; // namespace talk_base