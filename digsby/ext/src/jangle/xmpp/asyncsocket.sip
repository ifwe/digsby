

namespace buzz {

class AsyncSocket {

%TypeHeaderCode
#include "talk/xmpp/asyncsocket.h"
%End

public:
  enum State {
    STATE_CLOSED = 0,      //!< Socket is not open.
    STATE_CLOSING,         //!< Socket is closing but can have buffered data
    STATE_CONNECTING,      //!< In the process of
    STATE_OPEN,            //!< Socket is connected
//    STATE_TLS_CONNECTING,  //!< Establishing TLS connection
//    STATE_TLS_OPEN,        //!< TLS connected
  };

  enum Error {
    ERROR_NONE = 0,         //!< No error
    ERROR_WINSOCK,          //!< Winsock error
    ERROR_DNS,              //!< Couldn't resolve host name
    ERROR_WRONGSTATE,       //!< Call made while socket is in the wrong state
//    ERROR_SSL,              //!< Something went wrong with OpenSSL
  };

  virtual ~AsyncSocket();
  virtual buzz::AsyncSocket::State state() = 0;
  virtual buzz::AsyncSocket::Error error() = 0;
  virtual int GetError() = 0;    // winsock error code

  virtual bool Connect(const talk_base::SocketAddress& addr) = 0;
  virtual bool Read(char * data, size_t len, size_t* len_read) = 0;
  virtual bool Write(const char * data, size_t len) = 0;
  virtual bool Close() = 0;

};

};