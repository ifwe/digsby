#ifndef EXT_Noncopyable_h
#define EXT_Noncopyable_h

class Noncopyable
{
    Noncopyable(const Noncopyable&);
    Noncopyable& operator=(const Noncopyable&);

protected:
    Noncopyable() { }
    ~Noncopyable() { }
};

#endif // EXT_Noncopyable_h

