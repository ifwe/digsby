namespace talk_base {

///////////////////////////////////////////////////////////////////////////////

class SSLAdapter : /*public*/ talk_base::AsyncSocketAdapter {

%TypeHeaderCode
#include "talk/base/ssladapter.h"
%End

public:
  SSLAdapter(talk_base::AsyncSocket* socket);

  bool ignore_bad_cert() const;
  void set_ignore_bad_cert(bool ignore);

  // StartSSL returns 0 if successful.
  // If StartSSL is called while the socket is closed or connecting, the SSL
  // negotiation will begin as soon as the socket connects.
  virtual int StartSSL(const char* hostname, bool restartable) = 0;

  // Create the default SSL adapter for this platform
  static talk_base::SSLAdapter* Create(talk_base::AsyncSocket* socket);
/*
private:
  // If true, the server certificate need not match the configured hostname.
  bool ignore_bad_cert_;
*/
};

///////////////////////////////////////////////////////////////////////////////

// Call this on the main thread, before using SSL.
// Call CleanupSSLThread when finished with SSL.
bool InitializeSSL();

// Call to initialize additional threads.
bool InitializeSSLThread();

// Call to cleanup additional threads, and also the main thread.
bool CleanupSSL();

///////////////////////////////////////////////////////////////////////////////

};  // namespace talk_base