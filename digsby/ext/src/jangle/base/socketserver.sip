namespace talk_base {

const int kForever;

// Provides the ability to wait for activity on a set of sockets.  The Thread
// class provides a nice wrapper on a socket server.
//
// The server is also a socket factory.  The sockets it creates will be
// notified of asynchronous I/O from this server's Wait method.
class SocketServer : /*public*/ talk_base::SocketFactory {

%TypeHeaderCode
#include "talk/base/socketserver.h"
%End

public:

  // Sleeps until:
  //  1) cms milliseconds have elapsed (unless cms == kForever)
  //  2) WakeUp() is called
  // While sleeping, I/O is performed if process_io is true.
  virtual bool Wait(int cms, bool process_io) = 0;

  // Causes the current wait (if one is in progress) to wake up.
  virtual void WakeUp() = 0;
};

}; // namespace talk_base