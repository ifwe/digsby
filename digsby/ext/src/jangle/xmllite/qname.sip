

namespace buzz {


class QName
{

%TypeHeaderCode
#include "talk/xmllite/qname.h"
%End

public:
  explicit QName();
  QName(const buzz::QName & qname);
  explicit QName(bool add, const std::string & ns, const char * local);
  explicit QName(bool add, const std::string & ns, const std::string & local);
  explicit QName(const std::string & ns, const char * local);
  explicit QName(const std::string & mergedOrLocal);
//  QName & operator=(const buzz::QName & qn);
  ~QName();

  const std::string & Namespace() const;
  const std::string & LocalPart() const;
  std::string Merged() const;
  int Compare(const buzz::QName & other) const;
  bool operator==(const buzz::QName & other) const;
  bool operator!=(const buzz::QName & other) const;
  bool operator<(const buzz::QName & other) const;

  class Data {
  public:
    Data(const std::string & ns, const std::string & local);

    Data();

    std::string namespace_;
    std::string localPart_;
    void AddRef();
    void Release();
    bool Occupied();
  /*
  private:
    int refcount_;
  */
  };
/*
private:
  Data * data_;
*/
};


};
