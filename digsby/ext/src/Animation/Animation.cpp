#include "Animation.h"
#include "Layer.h"
#include "TextLayer.h"
#include "TimingFunction.h"
#include "Transaction.h"


MediaTiming::MediaTiming()
    : m_beginTime(0)
    , m_autoreverses(false)
    , m_duration(0.0)
    , m_speed(1.0f)
    , m_effectiveSpeed(1.0f)
    , m_timeOffset(0.0)
    , m_repeatCount(0.0f)
    , m_repeatDuration(0.0f)
    , m_fillMode(FillModeRemoved)
{
}

static TimingFunction* standardTimingFunction(StandardTimingFunction timingFunction)
{
    switch (timingFunction)
    {
        case TimingFunctionLinear:
            return &LinearTimingFunction::ms_instance;
        case TimingFunctionEaseIn:
            return &EaseInTimingFunction::ms_instance;
        case TimingFunctionEaseOut:
            return &EaseOutTimingFunction::ms_instance;
        case TimingFunctionEaseInEaseOut:
            return &EaseInEaseOutTimingFunction::ms_instance;
        default:
            ANIM_ASSERT(false);
    }
}

void Animation::setTimingFunction(StandardTimingFunction timingFunction)
{
    setTimingFunction(standardTimingFunction(timingFunction));
}

void Animation::setTimingFunction(TimingFunction* timingFunction)
{
    m_timingFunction = timingFunction;
}

void MediaTiming::setDuration(Time duration)
{
    m_duration = duration;
}

Animation::Animation()
    : m_removedOnCompletion(true)
    , m_timingFunction(&EaseInEaseOutTimingFunction::ms_instance)
{
    gs_animations.push_back(this);
    m_startedTime = GetCurrentTimeSeconds();
}

vector<Animation*> Animation::gs_animations;

void Animation::tickAll(Time timeMS)
{
    vector<Animation*> animations(gs_animations);
    vector<Animation*>::iterator i;
    for (i = animations.begin(); i != animations.end(); i++)
        (*i)->tick(timeMS);
}

Animation::~Animation()
{
    vector<Animation*>::iterator i;
    for (i = gs_animations.begin(); i != gs_animations.end(); i++) {
        if (*i == this) {
            gs_animations.erase(i);
            return;
        }
    }

    ANIM_ASSERT(false);
}

void Animation::setSpeed(float speed)
{
    m_effectiveSpeed = speed * m_layer->effectiveSpeed();
    m_speed = speed;
}

void Animation::setLayer(Layer* layer)
{
    m_layer = layer;
}

template<typename T>
class LinearAnimator : public Animator
{
public:
    LinearAnimator(Layer* layer, const T& a, const T& b)
        : Animator(layer)
        , m_from(a)
        , m_to(b)
    {}

    T interpolate(double delta)
    {
        return m_from + (m_to - m_from) * delta;
    }

protected:
    T m_from;
    T m_to;
};

class PositionAnimator : public LinearAnimator<Point>
{
public:
    PositionAnimator(Layer* layer, const Point& a, const Point& b)
        : LinearAnimator<Point>(layer, a, b)
    {}

    virtual void apply(double delta)
    {
        layer()->_setPosition(interpolate(delta));
    }
};

class ColorAnimator : public Animator
{
public:
    ColorAnimator(Layer* layer, const Color& a, const Color& b)
        : Animator(layer)
        , m_from(a)
        , m_to(b)
    {}

    Color interpolate(double delta)
    {
        return Color(m_from.Red()   + (m_to.Red()   - m_from.Red())   * delta,
                     m_from.Green() + (m_to.Green() - m_from.Green()) * delta,
                     m_from.Blue()  + (m_to.Blue()  - m_from.Blue())  * delta,
                     m_from.Alpha() + (m_to.Alpha() - m_from.Alpha()) * delta);
    }

    virtual void apply(double delta) = 0;
protected:
    Color m_from;
    Color m_to;
};

class BackgroundColorAnimator : public ColorAnimator
{
public:
    BackgroundColorAnimator(Layer* layer, const Color& a, const Color& b)
        : ColorAnimator(layer, a, b)
    {}

    virtual void apply(double delta)
    {
        layer()->_setBackgroundColor(interpolate(delta));
    }
};

#include <wx/log.h>

class OpacityAnimator : public LinearAnimator<float>
{
public:
    OpacityAnimator(Layer* layer, float a, float b)
        : LinearAnimator<float>(layer, a, b)
    {}

    virtual void apply(double delta)
    {
        layer()->_setOpacity(interpolate(delta));
    }
};

Animation* Animation::defaultAnimation(AnimationKeyPath animationKeyPath, Layer* layer)
{
    PropertyAnimation* animation = PropertyAnimation::animationForKeyPath(animationKeyPath);

    Time duration = Transaction::animationDuration();
    if (duration == 0.0)
        duration = Animation::defaultDuration(animationKeyPath);

    animation->setDuration(duration);

    animation->createAnimator(animationKeyPath, layer);

    // may remove the old animation
    layer->addAnimation(animation, animationKeyPath);

    return animation;
}

Time Animation::defaultDuration(AnimationKeyPath animationType)
{
    return .50;

    /*
    switch (animationType)
    {
        default:
            return .25;
    }
    */
}

void PropertyAnimation::createAnimator(AnimationKeyPath keyPath, Layer* layer)
{
    Layer* pLayer = layer->presentationLayer();

    switch (keyPath)
    {
        case AnimatePosition:
            m_animator = new PositionAnimator(pLayer, pLayer->position(), layer->position());
            break;
        case AnimateOpacity:
            m_animator = new OpacityAnimator(pLayer, pLayer->opacity(), layer->opacity());
            break;
        default:
            ANIM_ASSERT(false);
    }
}


PropertyAnimation::~PropertyAnimation()
{
    if (m_animator)
        delete m_animator;
}

PropertyAnimation* PropertyAnimation::animationForKeyPath(AnimationKeyPath keyPath)
{
    return new PropertyAnimation(keyPath);
}

PropertyAnimation::PropertyAnimation(AnimationKeyPath keyPath)
    : m_additive(false)
    , m_cumulative(false)
    , m_keyPath(keyPath)
    , m_animator(0)
{
}

// direction the animation is currently playing (if the autoreverses
// property is true, it may be going backwards
enum Direction
{
    DirectionForwards,
    DirectionBackwards,
};

Time Animation::absoluteDuration() const
{
    return duration() / m_effectiveSpeed / m_layer->effectiveSpeed();
}

Time Animation::absoluteStart() const
{
    // TODO: transform by beginTime and timeOffset properties
    return m_startedTime;
}

void Animation::tick(Time time)
{
    bool deleteAnimation = false;
    double duration = absoluteDuration();
    Direction direction = DirectionForwards;

    if (autoreverses())
        duration *= 2;

    double start = absoluteStart();

    float repeated = (time - start) / duration;
    float repcount = repeatCount();
    if (repcount == 0.0f)
        repcount = 1.0f;

    double delta;

    if (repeated < 0.0f) {
        // TODO: obey FillMode
        delta = 0.0;
    } else if (repeated > repcount) {
        // TODO: obey FillMode
        delta = 1.0;
        deleteAnimation = true;
    } else {
        // find out if we are currently going backwards
        if (autoreverses())
            if (int(repeated / absoluteDuration()) % 2 == 0)
                direction = DirectionBackwards;

        delta = ((time - start) / absoluteDuration());

        if (autoreverses())
            delta = 1.0 - delta;

        delta = m_timingFunction->interpolate(delta);
    }

    ANIM_ASSERT(delta >= 0.0);
    ANIM_ASSERT(delta <= 1.0);

    applyDeltaToLayer(delta);

    // TODO: this deletes 'this'. is that ok?
    if (deleteAnimation)
        layer()->removeAnimation(this);
}


void PropertyAnimation::applyDeltaToLayer(double delta)
{
    m_animator->apply(delta);
}

