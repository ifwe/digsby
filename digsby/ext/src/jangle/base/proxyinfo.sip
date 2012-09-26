


namespace talk_base {

enum ProxyType { PROXY_NONE, PROXY_HTTPS, PROXY_SOCKS5, PROXY_UNKNOWN };
const char * ProxyToString(talk_base::ProxyType proxy);

struct ProxyInfo {
  talk_base::ProxyType type;
  talk_base::SocketAddress address;
  std::string username;
  talk_base::CryptString password;

  ProxyInfo();
};

}; // namespace talk_base