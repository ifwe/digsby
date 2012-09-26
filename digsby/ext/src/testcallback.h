#include <iostream>
using namespace std;

class MyTest
{
public:
    MyTest() {}
    virtual ~MyTest() {}
    
    virtual void Callback()
    {
        cout << "Callback from C++";
    }
};