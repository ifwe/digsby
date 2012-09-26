#ifndef _ANIMATION_TEXTLAYER_H__
#define _ANIMATION_TEXTLAYER_H__

#include "Layer.h"

enum AlignmentMode
{
    AlignmentNatural,
    AlignmentLeft,
    AlignmentRight,
    AlignmentCenter,
    AlignmentJustified
};

enum TruncationMode
{
    TruncationNone,
    TruncationStart,
    TruncationEnd,
    TruncationMiddle
};

class TextLayer : public Layer
{
public:
    TextLayer();
    TextLayer(Layer* modelLayer);
    TextLayer(const String& string);
    virtual ~TextLayer() {}

    virtual void _init();

    Font font() const { return m_font; }
    void setFont(const Font& font);

    AlignmentMode alignmentMode() const;
    void setAlignmentMode(AlignmentMode alignmentMode);

    float fontSize() const { return m_fontSize; }
    void setFontSize(float fontSize);

    Color foregroundColor() const { return Color(m_red*255, m_green*255, m_blue*255, m_alpha*255); }
    void setForegroundColor(const Color& foregroundColor);

    String string() const { return m_string; }
    void setString(const String& string);

    TruncationMode truncationMode() const { return m_truncationMode; }
    void setTruncationMode(TruncationMode truncationMode);

protected:
    virtual Layer* createPresentationLayer(Layer* modelLayer) { return new TextLayer(modelLayer); }
    virtual void renderContent(GraphicsContext* context);

    Font m_font;
    float m_fontSize;
    double m_red, m_green, m_blue, m_alpha;
    String m_string;
    TruncationMode m_truncationMode;
    AlignmentMode m_alignmentMode;
};

#endif _ANIMATION_TEXTLAYER_H__

