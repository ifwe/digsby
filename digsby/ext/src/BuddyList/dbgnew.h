#if defined(WIN32) && defined(_DEBUG)
#include <crtdbg.h>
#define MYDEBUG_NEW   new(_CLIENT_BLOCK, __FILE__, __LINE__)
#define new MYDEBUG_NEW
#else
#endif
