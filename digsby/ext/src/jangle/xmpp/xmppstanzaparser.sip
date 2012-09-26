namespace buzz {


class XmppStanzaParseHandler {

%TypeHeaderCode
#include "talk/xmpp/xmppstanzaparser.h"
%End

public:
  virtual void StartStream(const buzz::XmlElement * pelStream) = 0;
  virtual void Stanza(const buzz::XmlElement * pelStanza) = 0;
  virtual void EndStream() = 0;
  virtual void XmlError() = 0;
};

class XmppStanzaParser {

%TypeHeaderCode
#include "talk/xmpp/xmppstanzaparser.h"
%End

public:
  XmppStanzaParser(buzz::XmppStanzaParseHandler *psph);
  bool Parse(const char * data, size_t len, bool isFinal);
  void Reset();

private:
  XmppStanzaParser();
  XmppStanzaParser(const buzz::XmppStanzaParser &);
/*
  class ParseHandler : public XmlParseHandler {
  public:
    ParseHandler(XmppStanzaParser * outer) : outer_(outer) {}
    virtual void StartElement(XmlParseContext * pctx,
               const char * name, const char ** atts)
      { outer_->IncomingStartElement(pctx, name, atts); }
    virtual void EndElement(XmlParseContext * pctx,
               const char * name)
      { outer_->IncomingEndElement(pctx, name); }
    virtual void CharacterData(XmlParseContext * pctx,
               const char * text, int len)
      { outer_->IncomingCharacterData(pctx, text, len); }
    virtual void Error(XmlParseContext * pctx,
               XML_Error errCode)
      { outer_->IncomingError(pctx, errCode); }
  private:
    XmppStanzaParser * const outer_;
  };

  friend class ParseHandler;
*/
  void IncomingStartElement(buzz::XmlParseContext * pctx,
               const char * name, const char ** atts);
  void IncomingEndElement(buzz::XmlParseContext * pctx,
               const char * name);
  void IncomingCharacterData(buzz::XmlParseContext * pctx,
               const char * text, int len);
  void IncomingError(buzz::XmlParseContext * pctx,
               XML_Error errCode);
/*
  XmppStanzaParseHandler * psph_;
  ParseHandler innerHandler_;
  XmlParser parser_;
  int depth_;
  XmlBuilder builder_;
*/
 };

};
