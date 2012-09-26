%ModuleHeaderCode
#include "talk/base/helpers.h"
%End

namespace cricket {

// srand initializer
void InitRandom(const char *client_unique, size_t len);

// For testing, the random seed can be directly accessed.
long GetRandomSeed();
void SetRandomSeed(unsigned long seed);

// Generates a (cryptographically) random string of the given length.
std::string CreateRandomString(int length);

// Generates a random id
uint32 CreateRandomId();

// Determines whether the given string consists entirely of valid base64
// encoded characters.
bool IsBase64Encoded(const std::string& str);

}; // namespace cricket
