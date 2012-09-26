

namespace talk_base {

// Provides the ability to perform socket I/O asynchronously.
class AsyncSocket : /*public*/ talk_base::Socket /*, public sigslot::has_slots<> */ {

%TypeHeaderCode
#include "talk/base/asyncsocket.h"
%End

public:
  virtual ~AsyncSocket(); //{}
/*
  sigslot::signal1<AsyncSocket*> SignalReadEvent;  // ready to read
  sigslot::signal1<AsyncSocket*> SignalWriteEvent; // ready to write
  sigslot::signal1<AsyncSocket*> SignalConnectEvent; // connected
  sigslot::signal2<AsyncSocket*,int> SignalCloseEvent; // closed
  // TODO: error
*/
};

class AsyncSocketAdapter : /* public */ talk_base::AsyncSocket {

%TypeHeaderCode
#include "talk/base/asyncsocket.h"
%End

public:
  AsyncSocketAdapter(talk_base::Socket * socket);
  AsyncSocketAdapter(talk_base::AsyncSocket * socket);
  virtual ~AsyncSocketAdapter();

  virtual talk_base::SocketAddress GetLocalAddress() const;
  virtual talk_base::SocketAddress GetRemoteAddress() const;

  virtual int Bind(const talk_base::SocketAddress& addr);
  virtual int Connect(const talk_base::SocketAddress& addr);
  virtual int Send(const void *pv, size_t cb);
  virtual int SendTo(const void *pv, size_t cb, const talk_base::SocketAddress& addr);
  virtual int Recv(void *pv, size_t cb);
  virtual int RecvFrom(void *pv, size_t cb, talk_base::SocketAddress *paddr);
  virtual int Listen(int backlog);
  virtual talk_base::Socket *Accept(talk_base::SocketAddress *paddr);
  virtual int Close();
  virtual int GetError() const;
  virtual void SetError(int error);

  virtual ConnState GetState() const;

  virtual int EstimateMTU(uint16* mtu);
  virtual int SetOption(Option opt, int value);
/*
protected:
  virtual void OnConnectEvent(AsyncSocket * socket) { SignalConnectEvent(this); }
  virtual void OnReadEvent(AsyncSocket * socket) { SignalReadEvent(this); }
  virtual void OnWriteEvent(AsyncSocket * socket) { SignalWriteEvent(this); }
  virtual void OnCloseEvent(AsyncSocket * socket, int err) { SignalCloseEvent(this, err); }

  Socket * socket_;
*/
};

}; // namespace talk_base