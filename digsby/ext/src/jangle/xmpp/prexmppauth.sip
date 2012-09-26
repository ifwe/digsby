namespace buzz {

class CaptchaChallenge {

%TypeHeaderCode
#include "talk/xmpp/prexmppauth.h"
%End

 public:
  CaptchaChallenge();
  CaptchaChallenge(const std::string& token, const std::string& url);

  bool captcha_needed() const;
  const std::string& captcha_token() const;

  // This url is relative to the gaia server.  Once we have better tools
  // for cracking URLs, we should probably make this a full URL
  const std::string& captcha_image_url() const;

/*
 private:
  bool captcha_needed_;
  std::string captcha_token_;
  std::string captcha_image_url_;
*/
};

class PreXmppAuth : /*public*/ buzz::SaslHandler {

%TypeHeaderCode
#include "talk/xmpp/prexmppauth.h"
%End

public:
  virtual ~PreXmppAuth();

  virtual void StartPreXmppAuth(
    const buzz::Jid & jid,
    const talk_base::SocketAddress & server,
    const talk_base::CryptString & pass,
    const std::string & auth_cookie) = 0;

//  sigslot::signal0<> SignalAuthDone;

  virtual bool IsAuthDone() = 0;
  virtual bool IsAuthorized() = 0;
  virtual bool HadError() = 0;
  virtual int GetError() = 0;
  virtual buzz::CaptchaChallenge GetCaptchaChallenge() = 0;
  virtual std::string GetAuthCookie() = 0;
};

};
