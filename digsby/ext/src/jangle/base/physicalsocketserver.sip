%Platforms {WIN32_PLATFORM POSIX_PLATFORM MACOS_PLATFORM}

%If(WIN32_PLATFORM)
//WinSock2.h
/*
 * The new type to be used in all
 * instances which refer to sockets.
 */
typedef unsigned int UINT_PTR;
typedef UINT_PTR        SOCKET;
%End

%If(POSIX_PLATFORM || MACOS_PLATFORM)
typedef int SOCKET;
%End // POSIX

namespace talk_base {

// A socket server that provides the real sockets of the underlying OS.
class PhysicalSocketServer : /*public*/ talk_base::SocketServer {

%TypeHeaderCode
#include "talk/base/physicalsocketserver.h"
%End

public:
  PhysicalSocketServer();
  virtual ~PhysicalSocketServer();

  // SocketFactory:
  virtual talk_base::Socket* CreateSocket(int type);
  virtual talk_base::AsyncSocket* CreateAsyncSocket(int type);

  // Internal Factory for Accept
  talk_base::AsyncSocket* WrapSocket(SOCKET s);

  // SocketServer:
  virtual bool Wait(int cms, bool process_io);
  virtual void WakeUp();
/*
  void Add(Dispatcher* dispatcher);
  void Remove(Dispatcher* dispatcher);
*/
%If(POSIX_PLATFORM || MACOS_PLATFORM)
  AsyncFile* CreateFile(int fd);
%End
/*
private:
  std::vector<Dispatcher*> dispatchers_;
  Signaler* signal_wakeup_;
  CriticalSection crit_;
  bool fWait_;
  uint32 last_tick_tracked_;
  int last_tick_dispatch_count_;
*/
};

}; // namespace talk_base
