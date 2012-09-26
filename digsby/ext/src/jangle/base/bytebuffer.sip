
namespace talk_base {

class ByteBuffer {

%TypeHeaderCode
#include "talk/base/bytebuffer.h"
%End

public:
  ByteBuffer();
  ByteBuffer(const char* bytes, size_t len);
  ByteBuffer(const char* bytes); // uses strlen
  ~ByteBuffer();

  const char* Data() const;
  size_t Length();
  size_t Capacity();

  bool ReadUInt8(uint8& val);
  bool ReadUInt16(uint16& val);
  bool ReadUInt32(uint32& val);
  bool ReadString(std::string& val, size_t len); // append to val
  bool ReadBytes(char* val, size_t len);

  void WriteUInt8(uint8 val);
  void WriteUInt16(uint16 val);
  void WriteUInt32(uint32 val);
  void WriteString(const std::string& val);
  void WriteBytes(const char* val, size_t len);

  void Resize(size_t size);
  void Shift(size_t size);

/*
private:
  char* bytes_;
  size_t size_;
  size_t start_;
  size_t end_;
*/
};

}; // namespace talk_base