#ifndef BL_Precompiled_H
#define BL_Precompiled_H

#include <queue>
#include <iostream>
#include <vector>
#ifdef __GNUC__
#include <ext/hash_map>
#else
#include <hash_map>
#endif
#include <map>
#include <sstream>
#include <string>

#include <boost/foreach.hpp>
#ifdef __GNUC__
#define foreach BOOST_FOREACH
#endif
#include <boost/smart_ptr.hpp>
#include <boost/function.hpp>
#include <boost/bind.hpp>

#include "dbgnew.h"

#ifdef WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

#endif
