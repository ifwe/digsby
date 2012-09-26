namespace buzz {

%TypeHeaderCode
#include "talk/xmllite/xmlbuilder.h"
%End

class XmlBuilder : /*public*/ buzz::XmlParseHandler {
public:
  XmlBuilder();

  static buzz::XmlElement * BuildElement(buzz::XmlParseContext * pctx,
                                  const char * name, const char ** atts);
  virtual void StartElement(buzz::XmlParseContext * pctx,
                            const char * name, const char ** atts);
  virtual void EndElement(buzz::XmlParseContext * pctx, const char * name);
  virtual void CharacterData(buzz::XmlParseContext * pctx,
                             const char * text, int len);
  virtual void Error(buzz::XmlParseContext * pctx, XML_Error);
  virtual ~XmlBuilder();

  void Reset();

  // Take ownership of the built element; second call returns NULL
  buzz::XmlElement * CreateElement();

  // Peek at the built element without taking ownership
  buzz::XmlElement * BuiltElement();

private:
  XmlBuilder(const buzz::XmlBuilder &);
/*
  XmlElement * pelCurrent_;
  scoped_ptr<XmlElement> pelRoot_;
  scoped_ptr<std::vector<XmlElement *, std::allocator<XmlElement *> > >
    pvParents_;
*/
};

};