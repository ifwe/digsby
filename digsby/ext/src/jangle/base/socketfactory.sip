namespace talk_base {

class SocketFactory {

%TypeHeaderCode
#include "talk/base/socketfactory.h"
%End

public:
  virtual ~SocketFactory();

  // Returns a new socket for blocking communication.  The type can be
  // SOCK_DGRAM and SOCK_STREAM.
  virtual talk_base::Socket* CreateSocket(int type) = 0;

  // Returns a new socket for nonblocking communication.  The type can be
  // SOCK_DGRAM and SOCK_STREAM.
  virtual talk_base::AsyncSocket* CreateAsyncSocket(int type) = 0;
};

}; // namespace talk_base