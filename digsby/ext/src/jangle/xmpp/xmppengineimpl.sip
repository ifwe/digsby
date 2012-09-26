namespace buzz {

//! The XMPP connection engine.
//! This engine implements the client side of the 'core' XMPP protocol.
//! To use it, register an XmppOutputHandler to handle socket output
//! and pass socket input to HandleInput.  Then application code can
//! set up the connection with a user, password, and other settings,
//! and then call Connect() to initiate the connection.
//! An application can listen for events and receive stanzas by
//! registering an XmppStanzaHandler via AddStanzaHandler().
class XmppEngineImpl : /*public*/ buzz::XmppEngine {

%TypeHeaderCode
#include "talk/xmpp/xmppengineimpl.h"
%End

public:
  XmppEngineImpl();
  virtual ~XmppEngineImpl();

  // SOCKET INPUT AND OUTPUT ------------------------------------------------

  //! Registers the handler for socket output
  virtual buzz::XmppReturnStatus SetOutputHandler(buzz::XmppOutputHandler *pxoh);

  //! Provides socket input to the engine
  virtual buzz::XmppReturnStatus HandleInput(const char * bytes, size_t len);

  //! Advises the engine that the socket has closed
  virtual buzz::XmppReturnStatus ConnectionClosed(int subcode);

  // SESSION SETUP ---------------------------------------------------------

  //! Indicates the (bare) JID for the user to use.
  virtual buzz::XmppReturnStatus SetUser(const buzz::Jid & jid);

  //! Get the login (bare) JID.
  virtual const buzz::Jid & GetUser();

  //! Indicates the autentication to use.  Takes ownership of the object.
  virtual buzz::XmppReturnStatus SetSaslHandler(buzz::SaslHandler * sasl_handler);

  //! Sets whether TLS will be used within the connection (default true).
  virtual buzz::XmppReturnStatus SetUseTls(bool useTls);

  //! Sets an alternate domain from which we allows TLS certificates.
  //! This is for use in the case where a we want to allow a proxy to
  //! serve up its own certificate rather than one owned by the underlying
  //! domain.
  virtual buzz::XmppReturnStatus SetTlsServer(const std::string & proxy_hostname,
                                        const std::string & proxy_domain);

  //! Gets whether TLS will be used within the connection.
  virtual bool GetUseTls();

  //! Sets the request resource name, if any (optional).
  //! Note that the resource name may be overridden by the server; after
  //! binding, the actual resource name is available as part of FullJid().
  virtual buzz::XmppReturnStatus SetRequestedResource(const std::string& resource);

  //! Gets the request resource name.
  virtual const std::string & GetRequestedResource();

  //! Sets language
  virtual void SetLanguage(const std::string & lang);

  // SESSION MANAGEMENT ---------------------------------------------------

  //! Set callback for state changes.
  virtual buzz::XmppReturnStatus SetSessionHandler(buzz::XmppSessionHandler* handler);

  //! Initiates the XMPP connection.
  //! After supplying connection settings, call this once to initiate,
  //! (optionally) encrypt, authenticate, and bind the connection.
  virtual buzz::XmppReturnStatus Connect();

  //! The current engine state.
  virtual State GetState();

  //! Returns true if the connection is encrypted (under TLS)
  virtual bool IsEncrypted();

  //! The error code.
  //! Consult this after XmppOutputHandler.OnClose().
  virtual Error GetError(int *subcode);

  //! The stream:error stanza, when the error is XmppEngine::ERROR_STREAM.
  //! Notice the stanza returned is owned by the XmppEngine and
  //! is deleted when the engine is destroyed.
  virtual const buzz::XmlElement * GetStreamError();

  //! Closes down the connection.
  //! Sends CloseConnection to output, and disconnects and registered
  //! session handlers.  After Disconnect completes, it is guaranteed
  //! that no further callbacks will be made.
  virtual buzz::XmppReturnStatus Disconnect();

  // APPLICATION USE -------------------------------------------------------

  //! Adds a listener for session events.
  //! Stanza delivery is chained to session handlers; the first to
  //! return 'true' is the last to get each stanza.
  virtual buzz::XmppReturnStatus AddStanzaHandler(buzz::XmppStanzaHandler* handler,
                                            buzz::XmppEngine::HandlerLevel level);

  //! Removes a listener for session events.
  virtual buzz::XmppReturnStatus RemoveStanzaHandler(buzz::XmppStanzaHandler* handler);

  //! Sends a stanza to the server.
  virtual buzz::XmppReturnStatus SendStanza(const buzz::XmlElement * pelStanza);

  //! Sends raw text to the server
  virtual buzz::XmppReturnStatus SendRaw(const std::string & text);

  //! Sends an iq to the server, and registers a callback for the result.
  //! Returns the cookie passed to the result handler.
  virtual buzz::XmppReturnStatus SendIq(const buzz::XmlElement* pelStanza,
                                  buzz::XmppIqHandler* iq_handler,
                                  buzz::XmppIqCookie* cookie);

  //! Unregisters an iq callback handler given its cookie.
  //! No callback will come to this handler after it's unregistered.
  virtual buzz::XmppReturnStatus RemoveIqHandler(buzz::XmppIqCookie cookie,
                                      buzz::XmppIqHandler** iq_handler);

  //! Forms and sends an error in response to the given stanza.
  //! Swaps to and from, sets type to "error", and adds error information
  //! based on the passed code.  Text is optional and may be STR_EMPTY.
  virtual buzz::XmppReturnStatus SendStanzaError(const buzz::XmlElement * pelOriginal,
                                           buzz::XmppStanzaError code,
                                           const std::string & text);

  //! The fullly bound JID.
  //! This JID is only valid after binding has succeeded.  If the value
  //! is JID_NULL, the binding has not succeeded.
  virtual const buzz::Jid & FullJid();

  //! The next unused iq id for this connection.
  //! Call this when building iq stanzas, to ensure that each iq
  //! gets its own unique id.
  virtual std::string NextId();

private:
    XmppEngineImpl(const buzz::XmppEngineImpl &);
/*
  friend class XmppLoginTask;
  friend class XmppIqEntry;
*/
  void IncomingStanza(const buzz::XmlElement *pelStanza);
  void IncomingStart(const buzz::XmlElement *pelStanza);
  void IncomingEnd(bool isError);

  void InternalSendStart(const std::string & domainName);
  void InternalSendStanza(const buzz::XmlElement * pelStanza);
  std::string ChooseBestSaslMechanism(const std::vector<std::string> & mechanisms, bool encrypted);
  buzz::SaslMechanism * GetSaslMechanism(const std::string & name);
  void SignalBound(const buzz::Jid & fullJid);
  void SignalStreamError(const buzz::XmlElement * pelStreamError);
  void SignalError(Error errorCode, int subCode);
  bool HasError();
  void DeleteIqCookies();
  bool HandleIqResponse(const buzz::XmlElement * element);
  void StartTls(const std::string & domain);
  void RaiseReset();
  /*
  class StanzaParseHandler : public XmppStanzaParseHandler {
  public:
    StanzaParseHandler(XmppEngineImpl * outer);
    virtual void StartStream(const XmlElement * pelStream);
    virtual void Stanza(const XmlElement * pelStanza);
    virtual void EndStream();
    virtual void XmlError();
  private:
    XmppEngineImpl * const outer_;
  };
  */
/*
  class EnterExit {
   public:
    EnterExit(XmppEngineImpl* engine);
    ~EnterExit();
   private:
    XmppEngineImpl* engine_;
    State state_;
    Error error_;

  };
  friend class StanzaParseHandler;
  friend class EnterExit;
*/

/*
  StanzaParseHandler stanzaParseHandler_;
  XmppStanzaParser stanzaParser_;


  // state
  int engine_entered_;
  Jid user_jid_;
  std::string password_;
  std::string requested_resource_;
  bool tls_needed_;
  std::string tls_server_hostname_;
  std::string tls_server_domain_;
  scoped_ptr<XmppLoginTask> login_task_;
  std::string lang_;

  int next_id_;
  Jid bound_jid_;
  State state_;
  bool encrypted_;
  Error error_code_;
  int subcode_;
  scoped_ptr<XmlElement> stream_error_;
  bool raised_reset_;
  XmppOutputHandler* output_handler_;
  XmppSessionHandler* session_handler_;

  typedef STD_VECTOR(XmppStanzaHandler*) StanzaHandlerVector;
  scoped_ptr<StanzaHandlerVector> stanza_handlers_[HL_COUNT];

  typedef STD_VECTOR(XmppIqEntry*) IqEntryVector;
  scoped_ptr<IqEntryVector> iq_entries_;

  scoped_ptr<SaslHandler> sasl_handler_;

  scoped_ptr<std::stringstream> output_;
*/
};

};
