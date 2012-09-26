namespace buzz {

class XmlParseContext {

%TypeHeaderCode
#include "talk/xmllite/xmlparser.h"
%End

public:
  virtual buzz::QName ResolveQName(const char * qname, bool isAttr) = 0;
  virtual void RaiseError(XML_Error err) = 0;
};

class XmlParseHandler {

%TypeHeaderCode
#include "talk/xmllite/xmlparser.h"
%End

public:
  virtual void StartElement(buzz::XmlParseContext * pctx,
               const char * name, const char ** atts) = 0;
  virtual void EndElement(buzz::XmlParseContext * pctx,
               const char * name) = 0;
  virtual void CharacterData(buzz::XmlParseContext * pctx,
               const char * text, int len) = 0;
  virtual void Error(buzz::XmlParseContext * pctx,
               XML_Error errorCode) = 0;
};

class XmlParser {

%TypeHeaderCode
#include "talk/xmllite/xmlparser.h"
%End

public:
  static void ParseXml(buzz::XmlParseHandler * pxph, std::string text);

  explicit XmlParser(buzz::XmlParseHandler * pxph);
  bool Parse(const char * data, size_t len, bool isFinal);
  void Reset();
  virtual ~XmlParser();

  // expat callbacks
  void ExpatStartElement(const char * name, const char ** atts);
  void ExpatEndElement(const char * name);
  void ExpatCharacterData(const char * text, int len);
  void ExpatXmlDecl(const char * ver, const char * enc, int standalone);

private:
  XmlParser();
  XmlParser(const buzz::XmlParser &);

/*
  class ParseContext : public XmlParseContext {
  public:
    ParseContext(XmlParser * parser);
    virtual ~ParseContext();
    virtual QName ResolveQName(const char * qname, bool isAttr);
    virtual void RaiseError(XML_Error err) { if (!raised_) raised_ = err; }
    XML_Error RaisedError() { return raised_; }
    void Reset();

    void StartElement();
    void EndElement();
    void StartNamespace(const char * prefix, const char * ns);

  private:
    const XmlParser * parser_;
    XmlnsStack xmlnsstack_;
    XML_Error raised_;
  };

  ParseContext context_;
  XML_Parser expat_;
  XmlParseHandler * pxph_;
  bool sentError_;
*/
};

};
