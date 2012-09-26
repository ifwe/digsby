#ifndef blist_GNUC_h
#define blist_GNUC_h

#ifdef __GNUC__
#include <boost/functional/hash.hpp>
namespace stdext
{
    using namespace __gnu_cxx;
}
namespace __gnu_cxx
{
	template <>
	struct hash<std::wstring> {
	        size_t operator() (const std::wstring& x) const {
	                return boost::hash<std::wstring>()(x);
	        }
	};
}
#endif

#endif //blist_GNUC_h