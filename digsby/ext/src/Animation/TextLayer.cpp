#include "TextLayer.h"
#include "Transaction.h"

TextLayer::TextLayer()
{
    _initModel();
}

TextLayer::TextLayer(Layer* modelLayer)
{
    _initPresentation(modelLayer);
}

TextLayer::TextLayer(const String& string)
    : m_string(string)
{
    _initModel();
}

void TextLayer::_init()
{
    Layer::_init();
    m_font = 0;
    m_fontSize = 20;

    m_red = m_blue = m_green = 0.0;
    m_alpha = 1.0;
    m_truncationMode = TruncationNone;
    m_alignmentMode = AlignmentNatural;
}

void TextLayer::renderContent(GraphicsContext* gc)
{
    printf("TextLayer::renderContent\n");
    printf("  m_font: %p\n", m_font);
    if (m_font) {
        ANIM_ASSERT(cairo_font_face_status(m_font) == CAIRO_STATUS_SUCCESS);
        cairo_set_font_face(gc, m_font);
    }

    cairo_set_source_rgba(gc, m_red, m_green, m_blue, m_alpha);
    cairo_set_font_size(gc, m_fontSize);
    cairo_show_text(gc, m_string.mb_str(wxConvUTF8));
}

void TextLayer::setString(const String& string)
{
    m_string = string;
    reinterpret_cast<TextLayer*>(presentationLayer())->m_string = string;
    invalidate();
}

void TextLayer::setFont(const Font& font)
{
    m_font = font;
    reinterpret_cast<TextLayer*>(presentationLayer())->m_font = font;
}

void TextLayer::setForegroundColor(const Color& color)
{
    TextLayer* p = reinterpret_cast<TextLayer*>(presentationLayer());

    p->m_red = m_red = color.Red()/255.0;
    p->m_green = m_green = color.Green()/255.0;
    p->m_blue = m_blue = color.Blue()/255.0;
    p->m_alpha = m_alpha = color.Alpha()/255.0;
}
