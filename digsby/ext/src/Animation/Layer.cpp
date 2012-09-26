#include "Layer.h"
#include "Transaction.h"
#include "WindowTarget.h"

// this constructor creates a model layer
Layer::Layer(WindowTarget* windowTarget /* = 0*/)
{
    _initModel();

    modelImpl()->m_windowTarget = windowTarget;
    if (windowTarget)
        windowTarget->setRootLayer(this);
}

// this constructor creates a presentation layer
Layer::Layer(Layer* modelLayer)
{
    _initPresentation(modelLayer);
}

void Layer::_initModel()
{
    m_isModel = true;
    m_impl = new ModelLayerImpl();
    m_siblingLayer = createPresentationLayer(this);
    _init();
}

void Layer::_initPresentation(Layer* modelLayer)
{
    m_isModel = false;
    m_impl = new PresentationLayerImpl();
    m_siblingLayer = modelLayer;
    _init();
}

void Layer::_init()
{
    m_contents = 0;
    m_autoresizingMask = LayerHeightSizable;
    m_masksToBounds = false;
    m_opacity = 1.0f;
    m_speed = 1.0f;
    m_effectiveSpeed = 1.0f;
    m_superLayer = 0;

    cairo_matrix_init_identity(&m_transform);
}

Layer::~Layer()
{
    delete m_impl;
}

Point Layer::position() const
{
    Point p;
    cairo_matrix_transform_point(&m_transform, &p.x, &p.y);
    return p;
}

void Layer::setSpeed(float speed)
{
    float parentMultiplier = superlayer() ? superlayer()->effectiveSpeed() : 1.0f;
    m_effectiveSpeed = speed * parentMultiplier;
    m_speed = speed;

    // update effective speeds of all animations
    AnimationMap::iterator i;
    for (i = animationMap()->begin(); i != animationMap()->end(); i++)
        i->second->setSpeed(i->second->speed());

    // update effective speeds of all children (and their children...)
    for (size_t j = 0; j < m_sublayers.size(); ++j) {
        Layer* sublayer = subLayer(j);
        sublayer->setSpeed(sublayer->speed());
    }
}

void Layer::addSublayer(Layer* sublayer)
{
    ANIM_ASSERT(isModel());

    // need to hook up both model and presentation layers
    Layer* pSubLayer = sublayer->presentationLayer();

    sublayer->m_superLayer = this;
    pSubLayer->m_superLayer = m_superLayer ? m_superLayer->presentationLayer() : 0;

    m_sublayers.push_back(sublayer);
    presentationLayer()->m_sublayers.push_back(pSubLayer);
}

void Layer::drawInContext(GraphicsContext* context)
{
    ANIM_ASSERT(isModel());
    presentationLayer()->_drawInContext(context);
}

void Layer::addAnimation(Animation* animation, AnimationKeyPath key)
{
    ANIM_ASSERT(isModel());
    AnimationMap::iterator i = animationMap()->find(key);

    if (i != animationMap()->end())
        delete i->second;

    (*animationMap())[key] = animation;

    animation->setLayer(this);
}

void Layer::removeAnimation(Animation* animation)
{
    ANIM_ASSERT(isModel());
    AnimationMap::iterator i;
    for (i = animationMap()->begin(); i != animationMap()->end(); i++) {
        if (i->second == animation) {
            delete i->second;
            animationMap()->erase(i);
            break;
        }
    }
}

bool Layer::removeAnimationForKey(AnimationKeyPath key)
{
    ANIM_ASSERT(isModel());
    AnimationMap::iterator i = animationMap()->find(key);
    if (i != animationMap()->end()) {
        delete i->second;
        animationMap()->erase(i);
    }
}

void Layer::removeAllAnimations()
{
    ANIM_ASSERT(isModel());
    AnimationMap::iterator i;
    for (i = animationMap()->begin(); i != animationMap()->end(); i++)
        delete i->second;
    
    animationMap()->clear();
}

void Layer::setPosition(const Point& point)
{
    ANIM_ASSERT(isModel());
    ImplicitTransaction t(this, AnimatePosition);
    m_transform.x0 = point.x;
    m_transform.y0 = point.y;
}

void Layer::setOpacity(float opacity)
{
    ANIM_ASSERT(isModel());
    ImplicitTransaction(this, AnimateOpacity);
    m_opacity = opacity;
}

void Layer::setContents(Bitmap contents)
{
    // TODO: animatable

    if (m_contents)
        cairo_surface_destroy(m_contents);

    m_contents = contents;

    if (m_contents)
        cairo_surface_reference(m_contents);
}

///////
// Presentation layer implementation
//////


void Layer::paintBackingStore(GraphicsContext* context)
{
    ANIM_ASSERT(isPresentation());
    cairo_surface_t* surface = backingStore();
    cairo_set_source_surface(context, surface, 0, 0);
    cairo_paint_with_alpha(context, m_opacity);
}

void Layer::_renderContentAndChildren(GraphicsContext* context)
{
    renderContent(context);

    for (size_t i = 0; i < numLayers(); ++i)
        subLayer(i)->_drawInContext(context);
}

void Layer::_drawInContext(GraphicsContext* context)
{
    ANIM_ASSERT(isPresentation());
    cairo_save(context);

    if (0 && !cacheContents()) {
        cairo_transform(context, &m_transform);
        _renderContentAndChildren(context);
    } else {
        if (1 || invalidated() || !backingStoreValid()) {
            cairo_push_group(context);
            _renderContentAndChildren(context);

            if (backingStore())
                cairo_surface_destroy(backingStore());

            cairo_surface_t* surface = cairo_get_group_target(context);
            cairo_surface_reference(surface);
            setBackingStore(surface);

            cairo_pattern_t* pattern = cairo_pop_group(context);
            cairo_pattern_destroy(pattern);

            presentationImpl()->m_invalidated = false;
        }

        cairo_transform(context, &m_transform);
        paintBackingStore(context);
    }

    cairo_restore(context);
}

static void render_empty_layer_content(GraphicsContext* cr)
{
    cairo_set_line_width (cr, 15.0);
    cairo_move_to (cr, 76.8, 84.48);
    cairo_rel_line_to (cr, 51.2, -51.2);
    cairo_rel_line_to (cr, 51.2, 51.2);
    cairo_stroke (cr);
}

static void GraphicsContext_DrawBitmap(GraphicsContext* cr, Bitmap contents, double x, double y, double w, double h)
{
    cairo_rectangle(cr, x, y, w, h);
    cairo_fill(cr);
}

static void GraphicsContext_DrawBitmap(GraphicsContext* cr, Bitmap contents, double x, double y)
{
    cairo_set_source_surface(cr, contents, 0, 0);
    cairo_surface_t* image = cairo_win32_surface_get_image(contents);
    int width  = cairo_image_surface_get_width(image);
    int height = cairo_image_surface_get_height(image);

    GraphicsContext_DrawBitmap(cr, contents, x, y, width, height);
}

static void Transform_SetTranslation(Transform& t, double x, double y)
{
    t.x0 = x;
    t.y0 = y;
}

static void Transform_SetTranslation(Transform& t, const Point& p)
{
    Transform_SetTranslation(t, p.x, p.y);
}


void Layer::renderContent(GraphicsContext* cr)
{
    ANIM_ASSERT(isPresentation());

    cairo_surface_t* contents = modelLayer()->contents();

    if (contents) {
        GraphicsContext_DrawBitmap(cr, contents, 0, 0);
    } else {
        //render_empty_layer_content(cr);
    }
}

void Layer::_setPosition(const Point& point)
{
    ANIM_ASSERT(isPresentation());
    Transform_SetTranslation(m_transform, point);
    invalidate();
}

void Layer::_setOpacity(float opacity)
{
    m_opacity = opacity;
    invalidate();
}

void Layer::_setBackgroundColor(const Color& color)
{
    m_backgroundColor = color;
    invalidate();
}

void Layer::invalidate()
{
    ANIM_ASSERT(isPresentation());
    presentationImpl()->m_invalidated = true;
    Layer* l = superlayer();
    if (l) {
        ANIM_ASSERT(l != this);
        l->invalidate();
    } else {
        Layer* m = modelLayer();
        ANIM_ASSERT(!m->superlayer());

        WindowTarget* windowTarget = m->windowTarget();
        ANIM_ASSERT(windowTarget);

        windowTarget->invalidate();
    }
}

// debug helpers

void print_transform(FILE *fp, const Transform& t)
{
    fprintf(fp, "  %3.1f %3.1f\n  %3.1f %3.1f\n  %3.1f %3.1f\n", t.xx, t.yx, t.xy, t.yy, t.x0, t.y0);
}

void print_layers(FILE* fp, Layer* layer, int indent)
{
    fprintf(fp, "Layer at %p with contents(%p):\n", layer, layer->contents());
    print_transform(fp, layer->transform());

    for (size_t i = 0; i < layer->numLayers(); ++i)
        print_layers(fp, layer->subLayer(i), indent + 4);
}

