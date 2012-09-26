
%ModuleHeaderCode
#include "talk/base/cryptstring.h"
%End

namespace talk_base {

class CryptStringImpl {
public:
  virtual ~CryptStringImpl();
  virtual size_t GetLength() const = 0;
  virtual void CopyTo(char * dest, bool nullterminate) const = 0;
  virtual std::string UrlEncode() const = 0;
  virtual talk_base::CryptStringImpl * Copy() const = 0;
};

class EmptyCryptStringImpl : talk_base::CryptStringImpl {
public:
  virtual ~EmptyCryptStringImpl();
  virtual size_t GetLength() const;
  virtual void CopyTo(char * dest, bool nullterminate) const;
  virtual std::string UrlEncode() const;
  virtual talk_base::CryptStringImpl * Copy() const;
};

class CryptString {
public:
  CryptString();
  size_t GetLength() const;
  void CopyTo(char * dest, bool nullterminate) const;
  CryptString(const talk_base::CryptString & other);
  explicit CryptString(const talk_base::CryptStringImpl & impl);
//  CryptString & operator=(const talk_base::CryptString & other);
  void Clear();
  std::string UrlEncode() const;

};


// Used for constructing strings where a password is involved and we
// need to ensure that we zero memory afterwards
class FormatCryptString {
public:
  FormatCryptString();

  void Append(const std::string & text);

  void Append(const char * data, size_t length);

  void Append(const talk_base::CryptString * password);

  size_t GetLength();

  const char * GetData();


  // Ensures storage of at least n bytes
  void EnsureStorage(size_t n);

  ~FormatCryptString();
};

class InsecureCryptStringImpl : talk_base::CryptStringImpl {
 public:
  //std::string& password();
  //const std::string& password() const;
  std::string password;
%GetCode
    sipPy = PyString_FromStringAndSize(sipCpp->password().c_str(), sipCpp->password().size());
%End
%SetCode
    if (PyBytes_Check(sipPy)) {
        sipCpp->password() = std::string(PyString_AsString(sipPy), PyString_GET_SIZE(sipPy));
    } else {
        PyErr_SetString(PyExc_ValueError, "expected str");
        sipErr = true;
    }
%End

  virtual ~InsecureCryptStringImpl();
  virtual size_t GetLength() const;
  virtual void CopyTo(char * dest, bool nullterminate);
  virtual std::string UrlEncode() const;
  virtual talk_base::CryptStringImpl * Copy();
};

};
