
namespace talk_base {

class Base64
{

%TypeHeaderCode
#include "talk/base/base64.h"
%End

public:
  static std::string encode(const std::string & data);
  static std::string decode(const std::string & data);
  static std::string encodeFromArray(const char * data, size_t len);

};

};