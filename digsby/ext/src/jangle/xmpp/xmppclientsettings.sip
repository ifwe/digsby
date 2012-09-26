

namespace buzz {

class XmppClientSettings {

%TypeHeaderCode
#include "talk/xmpp/xmppclientsettings.h"
%End

public:
  XmppClientSettings();

  void set_user(const std::string & user);
  void set_host(const std::string & host);
  void set_pass(const talk_base::CryptString & pass);
  void set_auth_cookie(const std::string & cookie);
  void set_resource(const std::string & resource);
  void set_use_tls(bool use_tls);
  void set_server(const talk_base::SocketAddress & server);
  void set_protocol(cricket::ProtocolType protocol);
  void set_proxy(talk_base::ProxyType f);
  void set_proxy_host(const std::string & host);
  void set_proxy_port(int port);
  void set_use_proxy_auth(bool f);
  void set_proxy_user(const std::string & user);
  void set_proxy_pass(const talk_base::CryptString & pass);
  void set_allow_plain(bool f);

  const std::string & user() const;
  const std::string & host() const;
  const talk_base::CryptString & pass() const;
  const std::string & auth_cookie() const;
  const std::string & resource() const;
  bool use_tls() const;
  const talk_base::SocketAddress & server() const;
  cricket::ProtocolType protocol() const;
  talk_base::ProxyType proxy() const;
  const std::string & proxy_host() const;
  int proxy_port() const;
  bool use_proxy_auth() const;
  const std::string & proxy_user() const;
  const talk_base::CryptString & proxy_pass() const;
  bool allow_plain() const;

};

};