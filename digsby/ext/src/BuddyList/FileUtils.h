#ifndef FileUtils_h
#define FileUtils_h

#ifdef WIN32
#include <string>
#include <vector>
typedef __int64 fsize_t;
#endif

#ifdef __GNUC__
typedef unsigned long long fsize_t; // TODO: Find out how to properly define this
#include <ext/hash_map>
#else
#include <hash_map>
#endif

#include "GNUC.h"
using stdext::hash_map;
using std::wstring;


typedef hash_map<wstring, fsize_t> LogSizeMap;
bool findFiles(std::vector<std::wstring>& files, const std::wstring& wildcard, bool sort = true);
fsize_t sumFileSizes(const std::wstring& wildcard);
bool getLogSizes(LogSizeMap& sizes, const wstring& logdir);
#endif
