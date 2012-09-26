namespace buzz {

class XmlnsStack {
public:
  XmlnsStack();
  ~XmlnsStack();

  void AddXmlns(const std::string & prefix, const std::string & ns);
  void RemoveXmlns();
  void PushFrame();
  void PopFrame();
  void Reset();

  const std::string * NsForPrefix(const std::string & prefix);
  bool PrefixMatchesNs(const std::string & prefix, const std::string & ns);

  //////////////////////////////////////////////////////////////
  /*
  std::pair<std::string, bool> PrefixForNs(const std::string & ns, bool isAttr);
  std::pair<std::string, bool> AddNewPrefix(const std::string & ns, bool isAttr);
  */
  /////////////////////////////////////////////////////////////

  std::string FormatQName(const buzz::QName & name, bool isAttr);

private:
  XmlnsStack(const buzz::XmlnsStack &);
/*

  scoped_ptr<std::vector<std::string, std::allocator<std::string> > > pxmlnsStack_;
  scoped_ptr<std::vector<size_t, std::allocator<size_t> > > pxmlnsDepthStack_;
*/
};
};