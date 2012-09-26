

namespace buzz {

class XmlChild {

%TypeHeaderCode
#include "talk/xmllite/xmlelement.h"
%End

//friend class XmlElement;

public:

  buzz::XmlChild * NextChild(); // { return pNextChild_; }
//  const buzz::XmlChild * NextChild() const { return pNextChild_; }

  bool IsText() const;

  buzz::XmlElement * AsElement(); // { return AsElementImpl(); }
//  const XmlElement * AsElement() const { return AsElementImpl(); }

  buzz::XmlText * AsText(); // { return AsTextImpl(); }
//  const XmlText * AsText() const { return AsTextImpl(); }


protected:

  XmlChild();

  virtual bool IsTextImpl() const = 0;
  virtual buzz::XmlElement * AsElementImpl() const = 0;
  virtual buzz::XmlText * AsTextImpl() const = 0;


  virtual ~XmlChild();
private:
  XmlChild(const buzz::XmlChild & noimpl);

/*
  XmlChild * pNextChild_;
*/

};

class XmlText : /*public*/ buzz::XmlChild {

%TypeHeaderCode
#include "talk/xmllite/xmlelement.h"
%End

public:
  explicit XmlText(const std::string & text);
  explicit XmlText(const buzz::XmlText & t);
  explicit XmlText(const char * cstr, size_t len);
  virtual ~XmlText();

  const std::string & Text() const;
  void SetText(const std::string & text);
  void AddParsedText(const char * buf, int len);
  void AddText(const std::string & text);

protected:
  virtual bool IsTextImpl() const;
  virtual buzz::XmlElement * AsElementImpl() const;
  virtual buzz::XmlText * AsTextImpl() const;
/*
private:
  std::string text_;
*/
};

class XmlAttr {

%TypeHeaderCode
#include "talk/xmllite/xmlelement.h"
%End

//friend class XmlElement;

public:
  buzz::XmlAttr * NextAttr() const;
  const buzz::QName & Name() const;
  const std::string & Value() const;

private:
  explicit XmlAttr(const buzz::QName & name, const std::string & value);
  explicit XmlAttr(const buzz::XmlAttr & att);
/*
  buzz::XmlAttr * pNextAttr_;
  QName name_;
  std::string value_;
*/
};

class XmlElement : /*public*/ buzz::XmlChild {

%TypeHeaderCode
#include <ostream>
#include "talk/xmllite/xmlelement.h"
%End

public:
  explicit XmlElement(const buzz::QName & name);
  explicit XmlElement(const buzz::QName & name, bool useDefaultNs);
  explicit XmlElement(const buzz::XmlElement & elt);

  virtual ~XmlElement();

  const buzz::QName& Name() const;
  void SetName(const buzz::QName& name);

  const std::string & BodyText() const;
  void SetBodyText(const std::string & text);

  const buzz::QName & FirstElementName() const;

  buzz::XmlAttr * FirstAttr();
//  const buzz::XmlAttr * FirstAttr() const;

  //! Attr will return STR_EMPTY if the attribute isn't there:
  //! use HasAttr to test presence of an attribute.
  const std::string & Attr(const buzz::QName & name) const;
  bool HasAttr(const buzz::QName & name) const;
  void SetAttr(const buzz::QName & name, const std::string & value);
  void ClearAttr(const buzz::QName & name);

  buzz::XmlChild * FirstChild();
//  const buzz::XmlChild * FirstChild() const;

  buzz::XmlElement * FirstElement();
//  const buzz::XmlElement * FirstElement() const;

  buzz::XmlElement * NextElement();
//  const buzz::XmlElement * NextElement() const;

  buzz::XmlElement * FirstWithNamespace(const std::string & ns);
//  const buzz::XmlElement * FirstWithNamespace(const std::string & ns) const;

  buzz::XmlElement * NextWithNamespace(const std::string & ns);
//  const buzz::XmlElement * NextWithNamespace(const std::string & ns) const;

  buzz::XmlElement * FirstNamed(const buzz::QName & name);
//  const buzz::XmlElement * FirstNamed(const buzz::QName & name) const;

  buzz::XmlElement * NextNamed(const buzz::QName & name);
//  const buzz::XmlElement * NextNamed(const buzz::QName & name) const;

  // Finds the first element named 'name'.  If that element can't be found then
  // adds one and returns it.
  buzz::XmlElement* FindOrAddNamedChild(const buzz::QName& name);

  const std::string & TextNamed(const buzz::QName & name) const;

  void InsertChildAfter(buzz::XmlChild * pPredecessor, buzz::XmlChild * pNewChild);
  void RemoveChildAfter(buzz::XmlChild * pPredecessor);

  void AddParsedText(const char * buf, int len);
  void AddText(const std::string & text);
  void AddText(const std::string & text, int depth);
  void AddElement(buzz::XmlElement * pelChild);
  void AddElement(buzz::XmlElement * pelChild, int depth);
  void AddAttr(const buzz::QName & name, const std::string & value);
  void AddAttr(const buzz::QName & name, const std::string & value, int depth);
  void ClearNamedChildren(const buzz::QName & name);
  void ClearChildren();

  static buzz::XmlElement * ForStr(const std::string & str);
  std::string Str() const;

//  void Print(std::ostream * pout, std::string * xmlns, int xmlnsCount) const;

protected:
  virtual bool IsTextImpl() const;
  virtual buzz::XmlElement * AsElementImpl() const;
  virtual buzz::XmlText * AsTextImpl() const;
private:
  XmlElement();
/*
  QName name_;
  XmlAttr * pFirstAttr_;
  XmlAttr * pLastAttr_;
  XmlChild * pFirstChild_;
  XmlChild * pLastChild_;
*/
};

};