

namespace talk_base {

// Provides the ability to receive packets asynchronously.  Sends are not
// buffered since it is acceptable to drop packets under high load.
class AsyncPacketSocket /* : sigslot::has_slots<> */ {
%TypeHeaderCode
#include "talk/base/asyncpacketsocket.h"
%End
public:
  AsyncPacketSocket(talk_base::AsyncSocket* socket);
  virtual ~AsyncPacketSocket();

  // Relevant socket methods:
  virtual talk_base::SocketAddress GetLocalAddress() const;
  virtual talk_base::SocketAddress GetRemoteAddress() const;
  virtual int Bind(const talk_base::SocketAddress& addr);
  virtual int Connect(const talk_base::SocketAddress& addr);
  virtual int Send(const void *pv, size_t cb);
  virtual int SendTo(const void *pv, size_t cb, const talk_base::SocketAddress& addr);
  virtual int Close();
  virtual int SetOption(talk_base::Socket::Option opt, int value);
  virtual int GetError() const;
  virtual void SetError(int error);

  // Emitted each time a packet is read.
//  sigslot::signal4<const char*, size_t, const talk_base::SocketAddress&, AsyncPacketSocket*> SignalReadPacket;
/*
protected:
  AsyncSocket* socket_;
*/
};

};