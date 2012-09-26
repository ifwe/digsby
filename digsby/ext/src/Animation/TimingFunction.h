#ifndef TimingFunction_h
#define TimingFunction_h

enum StandardTimingFunction
{
    TimingFunctionLinear,
    TimingFunctionEaseIn,
    TimingFunctionEaseOut,
    TimingFunctionEaseInEaseOut
};

class TimingFunction
{
public:
    virtual double interpolate(double delta) = 0;
};

class LinearTimingFunction : public TimingFunction
{
public:
    virtual double interpolate(double delta) { return delta; }
    static LinearTimingFunction ms_instance;
};

class EaseInTimingFunction : public TimingFunction
{
public:
    virtual double interpolate(double delta) { return delta; }
    static EaseInTimingFunction ms_instance;
};

class EaseOutTimingFunction : public TimingFunction
{
public:
    virtual double interpolate(double delta) { return delta; }
    static EaseOutTimingFunction ms_instance;
};

class EaseInEaseOutTimingFunction : public TimingFunction
{
public:
    virtual double interpolate(double x)
    {
        float x2 = x * x;
        float x3 = x2 * x;
        return -2 * x3 + 3 * x2;
    }

    static EaseInEaseOutTimingFunction ms_instance;
};

#endif // TimingFunction_h

