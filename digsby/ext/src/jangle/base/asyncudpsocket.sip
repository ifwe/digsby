
namespace talk_base {

// Provides the ability to receive packets asynchronously.  Sends are not
// buffered since it is acceptable to drop packets under high load.
class AsyncUDPSocket : /*public*/ talk_base::AsyncPacketSocket {

%TypeHeaderCode
#include "talk/base/asyncudpsocket.h"
%End

public:
  AsyncUDPSocket(talk_base::AsyncSocket* socket);
  virtual ~AsyncUDPSocket();
/*
private:
  char* buf_;
  size_t size_;

  // Called when the underlying socket is ready to be read from.
  void OnReadEvent(AsyncSocket* socket);
*/
};

/*
// Creates a new socket for sending asynchronous UDP packets using an
// asynchronous socket from the given factory.
inline AsyncUDPSocket* CreateAsyncUDPSocket(SocketFactory* factory) {
  return new AsyncUDPSocket(factory->CreateAsyncSocket(SOCK_DGRAM));
}
*/

}; // namespace talk_base