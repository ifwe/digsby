#ifndef Animation_Layer_h
#define Animation_Layer_h

#include "Animation.h"

class Layer;
class WindowTarget;

// TODO: hash/eq functions not from WX
typedef sparse_hash_map<AnimationKeyPath, Animation*, wxIntegerHash, wxIntegerEqual> AnimationMap;

class LayerImpl
{
public:
    virtual ~LayerImpl() {}
};

class PresentationLayerImpl : public LayerImpl
{
public:
    PresentationLayerImpl()
        : m_invalidated(true)
        , m_cacheContents(true)
        , m_backingStore(0)
    {}

    virtual ~PresentationLayerImpl()
    {
    }

    Bitmap m_backingStore;
    bool m_invalidated:1;
    bool m_cacheContents:1;
};

class ModelLayerImpl : public LayerImpl
{
public:
    ModelLayerImpl()
        : m_windowTarget(0)
    {}

    virtual ~ModelLayerImpl()
    {}

    AnimationMap m_animationMap;
    WindowTarget* m_windowTarget;
};

class Layer
{
public:
    Layer(Layer*);
    Layer(WindowTarget* windowTarget = 0);
    virtual ~Layer();

    Point position() const;

    void setSpeed(float speed);
    float speed() const { return m_speed; }
    float effectiveSpeed() const { return m_effectiveSpeed; }

    Rect bounds() const;
    void setBounds(const Rect& bounds);

    Point anchorPoint() const;
    void setAnchorPoint(const Point& anchorPoint);

    void setZPosition(float zPosition);
    float zPosition() const { return m_zPosition; }

    const Transform& transform() const { return m_transform; }

    void setBackgroundColor(const Color& backgroundColor);
    Color backgroundColor() const { return m_backgroundColor; }

    void setBorderColor(const Color& borderColor);
    Color borderColor() const { return m_borderColor; }
    
    void setAutoresizingMask(int autoresizingMask);
    int autoresizingMask() const { return m_autoresizingMask; }
    
    void setMasksToBounds(bool masksToBounds);
    bool masksToBounds() const { return m_masksToBounds; }

    void setMask(Layer* layer);
    Layer* mask() const { return m_mask; }

    void setContents(Bitmap bitmapContents);
    Bitmap contents() const { return m_contents; }

    float opacity() const { return m_opacity; }

    void setContentsGravity(int contentsGravity);
    int contentsGravity() const { return m_contentsGravity; }

    void setName(const String& name);
    String name() const { return m_name; }

    Layer* hitTest(const Point& point) const;

    void drawInContext(GraphicsContext* context);

    Layer* presentationLayer() { return isModel() ? m_siblingLayer : 0; }
    Layer* modelLayer() const { return isModel() ? 0 : m_siblingLayer; }

    Layer* subLayer(size_t index) const {
        ANIM_ASSERT(index < m_sublayers.size());
        return m_sublayers[index];
    }

    WindowTarget* windowTarget() const {
        ANIM_ASSERT(isModel());
        return modelImpl()->m_windowTarget;
    }

    Layer* superlayer() const { return m_superLayer; }
    size_t numLayers() const { return m_sublayers.size(); }

    bool isModel() const { return m_isModel; }
    bool isPresentation() const { return !m_isModel; }
    ModelLayerImpl* modelImpl() const { return (ModelLayerImpl*)m_impl; }
    PresentationLayerImpl* presentationImpl() const { return (PresentationLayerImpl*)m_impl; }

    ///// Model layer specific methods

    void addAnimation(Animation* animation, AnimationKeyPath key);
    bool removeAnimationForKey(AnimationKeyPath key);
    void removeAllAnimations();
    void removeAnimation(Animation* animation);

    void addSublayer(Layer* sublayer);
    void insertSublayer(Layer* sublayer, size_t index);

    void setPosition(const Point& position);
    void setOpacity(float opacity);

    ///// Presentation layer specific methods

    void _drawInContext(GraphicsContext* context);
    void paintBackingStore(GraphicsContext* context);

    bool backingStoreValid() const { return presentationImpl()->m_backingStore != 0; }
    Bitmap backingStore() const { return presentationImpl()->m_backingStore; }

    bool invalidated() const { return presentationImpl()->m_invalidated; }
    void invalidate();

    void _setPosition(const Point& position);
    void _setOpacity(float opacity);
    void _setBackgroundColor(const Color& color);

protected:
    virtual Layer* createPresentationLayer(Layer* modelLayer) { return new Layer(modelLayer); }
    virtual void _init();
    void _initModel();
    void _initPresentation(Layer* modelLayer);

    // Model only
    AnimationMap* animationMap() const { return &modelImpl()->m_animationMap; }

    // Presentation only
    bool cacheContents() const { return presentationImpl()->m_cacheContents; }
    void setBackingStore(Bitmap bitmap) { presentationImpl()->m_backingStore = bitmap; }
    virtual void _renderContentAndChildren(GraphicsContext*);
    virtual void renderContent(GraphicsContext* context);

    Layer* m_superLayer;
    Layer* m_siblingLayer;
    Layer* m_mask;

    String m_name;
    Bitmap m_contents;

    Transform m_transform;
    
    LayerImpl* m_impl;

    int m_autoresizingMask;
    int m_contentsGravity;
    float m_zPosition;
    float m_opacity;

    Color m_borderColor;
    Color m_backgroundColor;

    unsigned short int m_borderWidth;

    vector<Layer*> m_sublayers;

    float m_speed;
    float m_effectiveSpeed;

    bool m_masksToBounds:1;
    bool m_isModel:1;

private:
    Layer(const Layer&);
};

void print_transform(FILE *fp, const Transform& t);
void print_layers(FILE* fp, Layer* layer, int indent = 0);

#endif // Animation_Layer_h

