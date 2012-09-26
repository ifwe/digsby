#include "BuddyList.h"
#include "ctextutil.h"

#include "BuddyList/config.h"
#include "BuddyList/Contact.h"

#include <wx/gdicmn.h>

static wxFont fontFromFaceAndSize(const wxString& face, int size)
{
    return wxFont(size, wxFONTFAMILY_DEFAULT, wxFONTSTYLE_NORMAL,
        wxFONTWEIGHT_NORMAL, false, face);
}

BuddyList::BuddyList(wxWindow* parent)
    : TreeList(parent)
{
}

BuddyList::~BuddyList()
{
}

void BuddyList::foo()
{

}

struct CellRenderInfo
{
    wxRect rect;
    size_t index;
    short depth;
    Elem* elem;

    bool selected:1;
    bool expanded:1;
    bool expandable:1;
    bool hover:1;
};

struct IconPos
{
    unsigned char pos;

    enum
    {
        ICON_POS_FAR = (1<<0),
        ICON_POS_BADGE = (1<<1),
        ICON_POS_LEFT = (1<<2),
        ICON_POS_RIGHT = (1<<3)
    };

    IconPos(bool left, bool badge, bool isfar)
    {
        pos = 0;
        if (left) pos |= ICON_POS_LEFT;
        else      pos |= ICON_POS_RIGHT;

        if (badge) pos |= ICON_POS_BADGE;

        if (isfar) pos |= ICON_POS_FAR;
    }

    bool isfar() const { return pos | ICON_POS_FAR; }
    bool badge() const { return pos | ICON_POS_BADGE; }
    bool left() const { return pos | ICON_POS_LEFT; }
};
struct ContactRenderOptions
{
    ContactRenderOptions(const wxFont& nameFont,
                         const wxFont& extraFont,
                         const IconPos& buddyIconPos,
                         const IconPos& serviceIconPos)
        : name_font(nameFont)
        , extra_font(extraFont)
        , buddy_icon_pos(buddyIconPos)
        , service_icon_pos(serviceIconPos)
    {}

    enum Details
    {
        None,
        Status,
        IdleTime,
        StatusAndIdleTime
    };

    wxFont name_font;
    wxFont extra_font;

    IconPos buddy_icon_pos;
    unsigned char buddy_icon_size;

    IconPos service_icon_pos;
    unsigned char service_icon_size;

    unsigned char badge_max_size;
    unsigned char badge_min_size;
    char badge_ratio;

    wxSize icon_frame_size;
    wxSize sideIconSize;

    Details extra_info;
    short indent;    // number of pixels to indent for each indentation level
    short padding;   // padding between elements

    bool show_extra:1;
    bool show_status_icon:1;
    bool show_service_icon:1;
    bool show_buddy_icon:1;
    bool grey_offline:1;
};


class CellRenderer
{
public:
    virtual void Draw(wxDC& dc, CellRenderInfo& renderInfo) = 0;

protected:
    ContactRenderOptions* options() const { return m_options; }
    ContactRenderOptions* m_options;
};

/*
[('buddylist.layout.badge_max_size', 16),
 ('buddylist.layout.badge_min_size', 6),
 ('buddylist.layout.badge_ratio', 0.5),
 ('buddylist.layout.buddy_icon_pos', 'right'),
 ('buddylist.layout.buddy_icon_size', 32),
 ('buddylist.layout.extra_font_face', u'Tahoma'),
 ('buddylist.layout.extra_font_size', u'7'),
 ('buddylist.layout.extra_info', 'both'),
 ('buddylist.layout.extra_padding', 1),
 ('buddylist.layout.ez_layout', True),
 ('buddylist.layout.grey_offline', True),
 ('buddylist.layout.indent', 6),
 ('buddylist.layout.minimum_height', 16),
 ('buddylist.layout.name_font_face', u'Trebuchet MS'),
 ('buddylist.layout.name_font_size', u'9'),
 ('buddylist.layout.padding', 1),
 ('buddylist.layout.service_icon_pos', 'bright'),
 ('buddylist.layout.service_icon_size', 16),
 ('buddylist.layout.show_buddy_icon', True),
 ('buddylist.layout.show_extra', True),
 ('buddylist.layout.show_idle_after', 1),
 ('buddylist.layout.show_service_icon', True),
 ('buddylist.layout.show_status_icon', True),
 ('buddylist.layout.side_icon_size', 13),
 ('buddylist.layout.status_icon_pos', 'left'),
 ('buddylist.layout.status_icon_size', 16)]
 */



struct Margins
{
    int x;
    int y;
};

class ContactSkinOptions
{
public:
    Margins margins;
    wxPoint padding;
};

class ContactCellRenderer : public CellRenderer
{
public:
    void UpdateSkin();
    void CalcDraw(int width, int height);
    void CalcSizes();
    void Draw(wxDC& dc, CellRenderInfo& renderInfo);

    wxPoint& padding() { return m_skin.padding; }
    Margins& margins() { return m_skin.margins; }

protected:
    wxSize m_lastSize;
    ContactSkinOptions m_skin;

    short m_mainfont_height;
};

class GroupCellRenderer : public CellRenderer
{
public:
    GroupCellRenderer()
        : m_expander(0)
    {}

    void CalcDraw();
    void CalcSizes();
    void Draw(wxDC& dc, CellRenderInfo& renderInfo);

    wxColor foregroundColor(const CellRenderInfo& rI)
    {
        /*
        if (rI.selected)
            return m_fontColorSelected;
        else if (rI.hover)
            return m_fontColorHover;
        else
            return m_fontColorNormal;
        */

        return *wxBLACK;
    }

    wxString displayString(const wxString& groupName) const;

protected:
    ContactRenderOptions* m_options;
    short m_mainfont_height;
    short m_group_height;
    short m_cell_height;
    wxBitmap* m_expander;
};

enum Icon
{
    ServiceIcon,
    StatusIcon,
    BuddyIcon
};

int iconPositionLessThan(const wxString& a_, const wxString& b_)
{
    wxChar a = a_[0];
    wxChar b = b_[0];

    int x = 0, y = 0;

    if (a == L'f') x = -1;
    else if (a == L'b') x = 1;
    if (b == L'f') y = -1;
    else if (b == L'b') y = 1;

    return x < y;
}

/*
void ContactCellRenderer::CalcSizes()
{
    // contact's name
    m_mainfont_height = GetFontHeight(m_options.name_font);

    // m_extrafont: idle time, status message
    m_extrafont_height = GetFontHeight(m_options.extrafont);

    int icon_size = m_options.buddy_icon_size;
    if (m_icon_frame_size)
        // add overlay size if necessary
        icon_size += m_icon_frame_size->top + m_icon_frame_size->bottom;

    int extraheight;
    if (m_options.extra_info != Details::None)
        extraheight = m_extrafont_height;
    else
        extraheight = 0;
        
    m_cell_height = padding() * 2 +
        max(m_options.show_buddy_icon ? icon_size : 0, m_mainfont_height + extraheight) +
        margins().top + margins().bottom;

    if (m_cell_height < m_mainfont_height * 1.2)
        m_cell_height = m_mainfont_height * 1.2;
}
*/

struct IconTemplate
{
    Icon icon;
    wxSize size;
    wxRect rect;
    int alignment;
};

void ContactCellRenderer::CalcDraw(int width, int height)
{
    if (m_lastSize.x == width && m_lastSize.y == height)
        return;

    // wxRect rect(RectAddMargins(wxRect(0, 0, width, height), skin.margins));

    //for (int i = 0; i < sizeof(all_icons); ++i)
     //   ;// bl_pref_str(prefStringForIcon(icon));

    //m_iconseq.clear();


//    int m_badge_size = min(opts.badge_max_size,
//                         max(opts.badge_min_size,
//                           opts.buddy_icon_size * opts.badge_ratio));
}

void ContactCellRenderer::Draw(wxDC& dc, CellRenderInfo& renderInfo)
{
    Contact* contact = reinterpret_cast<Contact*>(renderInfo.elem);

    wxRect rect(Subtract(renderInfo.rect, options()->indent * renderInfo.depth));

    DrawTruncated(dc, contact->alias(), rect, wxALIGN_LEFT, false, &options()->name_font);
}

void GroupCellRenderer::CalcDraw()
{
    GetFontHeight(m_mainfont_height, &options()->name_font);
    m_group_height = m_mainfont_height /*+ margins().top + margins().bottom + padding().y * 2*/;
}

/*
int VCenter(const wxRect& rect, const wxBitamp& img)
{
    return rect.y + rect.height / 2 - img.GetHeight() / 2;
}
*/

wxString GroupCellRenderer::displayString(const wxString& groupName) const
{
    return groupName;
}

/*
void GroupCellRenderer::Draw(wxDC& dc, CellRenderInfo& renderInfo)
{
    wxRect rect = RectAddMargins(RectAddMargins(renderInfo.rect, margins), wxRect(0, m_padding.y, 0, m_padding.y));

    // Account for depth indent
    rect = Subtract(rect, m_options.indent * renderInfo.depth);

    // Draw the expander triangle, if necessary.
    if (renderInfo.expandable && m_expander) {
        dc.Bitmap(*m_expander, rect.x, VCenter(rect, m_expander), true);
        rect = Subtract(m_expander.GetWidth() + m_padding.x);
    }

    // Draw text
    dc.SetTextForeground(foregroundColor(cellInfo));
    wxString text(displayString(reinterpret_cast<Group*>(renderInfo.elem)->name());
    DrawTruncated(dc, text, rect, wxALIGN_LEFT | wxALIGN_MIDDLE, false, m_options.name_font);
}
*/
