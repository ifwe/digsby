#ifndef _CGUI_INTERPOLATION_H_
#define _CGUI_INTERPOLATION_H_

#include <wx/colour.h>

#include <vector>
using std::vector;

/*
 things to interpolate
  - numbers
  - colors
  - points
  - rectangles
  - images

  interpolation methods
  - linear
  - polynomial, etc.
  - strobe
*/

static wxColour interpolate(wxColour c1, wxColour c2, double factor)
{
    return wxColour(
        (c2.Red() - c1.Red()) * factor + c1.Red(),
        (c2.Green() - c1.Green()) * factor + c1.Green(),
        (c2.Blue() - c1.Blue()) * factor + c1.Blue(),
        (c2.Alpha() - c1.Alpha()) * factor + c1.Alpha()
    );
}

static double interpolate(double d1, double d2, double factor)
{
    return (d2 - d1) * factor + d1;
}

template<typename T>
class Fader : Interpolator
{
};

template<typename T>
class SineWave : Interpolator<T>
{
public:

    SineWave(T peak, T valley, double period)
        : m_peak(peak)
        , m_valley(valley)
        , m_period(period)
    {
    }

    T peak() const { return peak; }
    T valley() const { return m_valley; }

    double period() const { return m_period; }

protected:
    T peak;
    T valley;
    double m_period;
};

/*
usage:

// oscillate between red and blue every 1.5 seconds.

vector<wxColour> colors;
colors.push_back(wxRED);
colors.push_back(wxBLUE);

m_colour = new SineWaveInterpolator<wxColour>(colors, 1.5);
*/

#endif // _CGUI_INTERPOLATION_H_

