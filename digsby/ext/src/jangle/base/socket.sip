

namespace talk_base {


// General interface for the socket implementations of various networks.  The
// methods match those of normal UNIX sockets very closely.
class Socket {

%TypeHeaderCode
#include "talk/base/socket.h"
%End

public:
  virtual ~Socket();

  // Returns the address to which the socket is bound.  If the socket is not
  // bound, then the any-address is returned.
  virtual talk_base::SocketAddress GetLocalAddress() const = 0;

  // Returns the address to which the socket is connected.  If the socket is
  // not connected, then the any-address is returned.
  virtual talk_base::SocketAddress GetRemoteAddress() const = 0;

  virtual int Bind(const talk_base::SocketAddress& addr) = 0;
  virtual int Connect(const talk_base::SocketAddress& addr) = 0;
  virtual int Send(const void *pv, size_t cb) = 0;
  virtual int SendTo(const void *pv, size_t cb, const talk_base::SocketAddress& addr) = 0;
  virtual int Recv(void *pv, size_t cb) = 0;
  virtual int RecvFrom(void *pv, size_t cb, talk_base::SocketAddress *paddr) = 0;
  virtual int Listen(int backlog) = 0;
  virtual talk_base::Socket *Accept(talk_base::SocketAddress *paddr) = 0;
  virtual int Close() = 0;
  virtual int GetError() const = 0;
  virtual void SetError(int error) = 0;
  bool IsBlocking() const;

  enum ConnState {
    CS_CLOSED,
    CS_CONNECTING,
    CS_CONNECTED
  };
  virtual ConnState GetState() const = 0;

  // Fills in the given uint16 with the current estimate of the MTU along the
  // path to the address to which this socket is connected.
  virtual int EstimateMTU(uint16* mtu) = 0;

  enum Option {
    OPT_DONTFRAGMENT
  };
  virtual int SetOption(talk_base::Socket::Option opt, int value) = 0;

protected:
  Socket();

private:
  Socket(const talk_base::Socket&);
//  void operator=(const Socket&);

};

}; // namespace talk_base