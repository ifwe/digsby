%ModuleHeaderCode
#include "talk/base/byteorder.h"
%End

namespace talk_base {

uint16 HostToNetwork16(uint16 n);
%MethodCode
  sipRes = htons(a0);
%End

uint32 HostToNetwork32(uint32 n);
%MethodCode
  sipRes = htonl(a0);
%End

uint16 NetworkToHost16(uint16 n);
%MethodCode
  sipRes = ntohs(a0);
%End

uint32 NetworkToHost32(uint32 n);
%MethodCode
  sipRes = ntohl(a0);
%End

}; // namespace talk_base