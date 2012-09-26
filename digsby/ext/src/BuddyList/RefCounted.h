#ifndef RefCounted_h
#define RefCounted_h

#include <boost/smart_ptr.hpp>
using boost::intrusive_ptr;

template<class Derived> 
class RefCounted 
{ 
protected: 
    RefCounted() : ref_count__(0) {} 

    friend void intrusive_ptr_add_ref(RefCounted* o) 
    { 
        ++o->ref_count__; 
    } 

    friend void intrusive_ptr_release(RefCounted* o) 
    { 
       if (--o->ref_count__ == 0)
           delete static_cast<Derived*>(o); 
    } 

    int ref_count__; 

public:
    typedef intrusive_ptr<Derived> Ptr;

}; 

#endif

