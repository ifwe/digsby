#ifndef __CGUI_ANIMATION_H__
#define __CGUI_ANIMATION_H__

#include <vector>
using std::vector;

#define ANIM_ASSERT(x) \
    do { if (!(x)) DebugBreak(); } while(0);

#include "AnimationPlatform.h"
#include "TimingFunction.h"

enum FillMode
{
    FillModeRemoved,
    FillModeForwards,
    FillModeBackwards,
    FillModeBoth
};

class Layer;
class Transaction;

class MediaTiming
{
public:
    bool autoreverses() const { return m_autoreverses; }
    void setAutoreverses(bool autoreverses);

    Time duration() const { return m_duration; }
    void setDuration(Time duration);

    Time beginTime() const { return m_beginTime; }
    void setBeginTime(Time beginTime);

    Time timeOffset() const { return m_timeOffset; }
    void setTimeOffset(Time timeOffset);

    float speed() const { return m_speed; }
    float effectiveSpeed() const { return m_effectiveSpeed; }

    float repeatCount() const { return m_repeatCount; }
    void setRepeatCount(float repeatCount);

    float repeatDuration() const { return m_repeatDuration; }
    void setRepeatDuration(float repeatDuration);

    FillMode fillMode() const { return m_fillMode; }
    void setFillMode(FillMode fillMode);

protected:
    MediaTiming();

    FillMode m_fillMode;
    Time m_duration;
    Time m_beginTime;
    Time m_timeOffset;
    float m_speed;
    float m_effectiveSpeed;
    float m_repeatCount;
    float m_repeatDuration;
    bool m_autoreverses:1;
};

// autoResizingMask property
enum AutoResizeMode
{
    LayerHeightSizable = 1<<0,
    LayerWidthSizable  = 1<<1,
    LayerMinXMargin    = 1<<2,
    LayerMaxXMargin    = 1<<2,
    LayerMinYMargin    = 1<<3,
    LayerMaxYMargin    = 1<<4
};

// contentsGravity property
enum Gravity
{
    GravityTopLeft  = 1<<0,
    GravityTop      = 1<<1,
    GravityTopRight = 1<<2,
    GravityLeft     = 1<<3,
    GravityCenter   = 1<<4,
    GravityRight = 1<<5,
    GravityBottomLeft = 1<<6,
    GravityBottom = 1<<7,
    GravityBottomRight = 1<<8,
    GravityResize = 1<<9,
    GravityResizeAspect = 1<<10
};

enum AnimationKeyPath
{
    AnimatePosition,
    AnimateForegroundColor,
    AnimateOpacity
};


class Animation : public MediaTiming
{
public:
    void setTimingFunction(StandardTimingFunction timingFunction);
    void setTimingFunction(TimingFunction* timingFunction);
    void setSpeed(float speed);
    TimingFunction* getTimingFunction() const { return m_timingFunction; }

    static Time defaultDuration(AnimationKeyPath animationType);

    bool removedOnCompletion() const { return m_removedOnCompletion; }

    void setLayer(Layer* layer);
    Layer* layer() const { return m_layer; }
    ~Animation();

    static void tickAll(Time time);

protected:
    friend class Transaction;

    Animation();

    static Animation* defaultAnimation(AnimationKeyPath animationKeyPath, Layer* layer);
    TimingFunction* m_timingFunction;

    virtual void applyDeltaToLayer(double delta) = 0;

    void tick(Time time);

    Time absoluteDuration() const;
    Time absoluteStart() const;

    //
    
    bool m_removedOnCompletion:1;
    Time m_startedTime;
    Layer* m_layer;

    static vector<Animation*> gs_animations;
};

// a virtual subclass exists for each AnimationType
class Animator
{
public:
    Animator(Layer* layer)
        : m_layer(layer)
    {}

    Layer* layer() const { return m_layer; }

    virtual void apply(double delta) = 0;

protected:
    Layer* m_layer;
};


class PropertyAnimation : public Animation
{
public:
    virtual ~PropertyAnimation();

    static PropertyAnimation* animationForKeyPath(AnimationKeyPath keyPath);

    bool setAdditive(bool additive);
    bool additive() const { return m_additive; }

    void setCumulative(bool cumulative);
    bool cumulative() const { return m_cumulative; }

    AnimationKeyPath keyPath() const { return m_keyPath; }

protected:
    friend class Animation;

    virtual void applyDeltaToLayer(double delta);
    PropertyAnimation(AnimationKeyPath keyPath);
    void createAnimator(AnimationKeyPath keyPath, Layer* layer);

    AnimationKeyPath m_keyPath;
    bool m_additive:1;
    bool m_cumulative:1;

    Layer* m_layer;

    Animator* m_animator;
};

class BasicAnimation : public Animation
{
public:
    void setRepeatCount(size_t repeatCount);
    size_t getRepeatCount() const { return m_repeatCount; }

    void setFromValue(double value);
    double getFromValue() const { return m_fromValue; }

    void setToValue(double value);
    double getToValue() const { return m_toValue; }

protected:
    size_t m_repeatCount;

    double m_fromValue;
    double m_toValue;
};

enum CalculationMode
{
    AnimationLinear,
    AnimationDiscrete,
    AnimationPaced,
};

class KeyframeAnimation
{
public:
    void setCalculationMode(CalculationMode calculationMode);
    CalculationMode calculationMode() const { return m_calculationMode; }
protected:
    CalculationMode m_calculationMode;
};

class Transition
{
};

class AnimationGroup
{
};


#endif // __CGUI_ANIMATION_H__

