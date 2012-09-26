namespace talk_base {

// Simulates UDP semantics over TCP.  Send and Recv packet sizes
// are preserved, and drops packets silently on Send, rather than
// buffer them in user space.
class AsyncTCPSocket : /* public */ talk_base::AsyncPacketSocket {

%TypeHeaderCode
#include "talk/base/asynctcpsocket.h"
%End

public:
  AsyncTCPSocket(talk_base::AsyncSocket* socket);
  virtual ~AsyncTCPSocket();

  virtual int Send(const void *pv, size_t cb);
  virtual int SendTo(const void *pv, size_t cb, const talk_base::SocketAddress& addr);

/*
  sigslot::signal1<AsyncTCPSocket*> SignalConnect;
  sigslot::signal2<AsyncTCPSocket*,int> SignalClose;
*/
/*
protected:
  int SendRaw(const void * pv, size_t cb);
  virtual void ProcessInput(char * data, size_t& len);
*/
/*
private:
  char* inbuf_, * outbuf_;
  size_t insize_, inpos_, outsize_, outpos_;

  int Flush();

  // Called by the underlying socket
  void OnConnectEvent(AsyncSocket* socket);
  void OnReadEvent(AsyncSocket* socket);
  void OnWriteEvent(AsyncSocket* socket);
  void OnCloseEvent(AsyncSocket* socket, int error);
*/
};

}; // namespace talk_base