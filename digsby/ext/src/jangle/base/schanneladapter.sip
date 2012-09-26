
struct _SecBufferDesc;

namespace talk_base {

///////////////////////////////////////////////////////////////////////////////

class SChannelAdapter : /*public*/ talk_base::SSLAdapter, /*public*/ talk_base::MessageHandler {

%TypeHeaderCode
#define SECURITY_WIN32
#include <security.h>
#include <schannel.h>
#include "talk/base/schanneladapter.h"
%End

public:
  SChannelAdapter(talk_base::AsyncSocket* socket);
  virtual ~SChannelAdapter();

  virtual int StartSSL(const char* hostname, bool restartable);
  virtual int Send(const void* pv, size_t cb);
  virtual int Recv(void* pv, size_t cb);
  virtual int Close();

  // Note that the socket returns ST_CONNECTING while SSL is being negotiated.
  virtual ConnState GetState() const;

  struct SSLImpl;
protected:
  enum SSLState {
    SSL_NONE, SSL_WAIT, SSL_CONNECTING, SSL_CONNECTED, SSL_ERROR
  };

  virtual void OnConnectEvent(talk_base::AsyncSocket* socket);
  virtual void OnReadEvent(talk_base::AsyncSocket* socket);
  virtual void OnWriteEvent(talk_base::AsyncSocket* socket);
  virtual void OnCloseEvent(talk_base::AsyncSocket* socket, int err);
  virtual void OnMessage(talk_base::Message* pmsg);

  int BeginSSL();
  int ContinueSSL();
  int ProcessContext(long status, _SecBufferDesc* sbd_in,
                     _SecBufferDesc* sbd_out);
  int DecryptData();

  int Read();
  int Flush();
  void Error(const char* context, int err, bool signal = true);
  void Cleanup();

  void PostEvent();

/*
private:
  SSLState state_;
  std::string ssl_host_name_;
  // If true, socket will retain SSL configuration after Close.
  bool restartable_;
  // If true, we are delaying signalling close until all data is read.
  bool signal_close_;
  // If true, we are waiting to be woken up to signal readability or closure.
  bool message_pending_;
  SSLImpl* impl_;
*/
};

/////////////////////////////////////////////////////////////////////////////

}; // namespace talk_base
