
namespace talk_base {


// Provides the ability to perform file I/O asynchronously.
// TODO: Create a common base class with AsyncSocket.
class AsyncFile {

%TypeHeaderCode
#include "talk/base/asyncfile.h"
%End

public:
  virtual ~AsyncFile();

  // Determines whether the file will receive read events.
  virtual bool readable() = 0;
  virtual void set_readable(bool value) = 0;

  // Determines whether the file will receive write events.
  virtual bool writable() = 0;
  virtual void set_writable(bool value) = 0;

//  sigslot::signal1<AsyncFile*> SignalReadEvent;
//  sigslot::signal1<AsyncFile*> SignalWriteEvent;
//  sigslot::signal2<AsyncFile*,int> SignalCloseEvent;
};

}; // namespace talk_base