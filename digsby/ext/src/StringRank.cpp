//
// quicksilver string matching algorithm
//
// thanks http://rails-oceania.googlecode.com/svn/lachiecox/qs_score/trunk/qs_score.js
//
//
#include <string>
using std::wstring;

float stringRank(const wstring& s, const wstring& abbreviation)
{
    if (abbreviation.size() == 0)
        return 0.9;
    else if (abbreviation.size() > s.size())
        return 0.0;

    for (size_t i = abbreviation.size(); i > 0; --i) {
        wstring sub_abbreviation(abbreviation.substr(0, i));
        size_t index = s.find(sub_abbreviation);

        if (index == std::string::npos)
            continue;
        else if (index + abbreviation.size() > s.size())
            continue;

        wstring next_string = s.substr(index + sub_abbreviation.size());
        wstring next_abbreviation;

        if (i < abbreviation.size())
            next_abbreviation = abbreviation.substr(i, std::string::npos);

        float remaining_score = stringRank(next_string, next_abbreviation);

        if (remaining_score > 0) {
            float score = s.size() - next_string.size();

            if (index != 0) {
                long int c = s[index - 1];
                if (c == 32 || c == 9) {
                    for (int j = index - 2; j >= 0; --j) {
                        c = s[j];
                        score -= ((c == 32 || c == 9) ? 1 : 0.15);
                    }
                } else {
                    score -= index;
                }
            }

            score += remaining_score * next_string.size();
            score /= static_cast<float>(s.size());
            return score;
        }
    }

    return 0.0;
}

#ifdef TEST_QS_ALGO
int wmain( int argc, wchar_t *argv[ ], wchar_t *envp[ ] )
{
    if (argc < 3) {
        printf("Usage: %ws <string> <match1> [<match2> ...]\n",
               argv[0]);
        return -1;
    }

    wstring s(argv[1]);

    for (int c = 2; c < argc; ++c) {
        wchar_t* arg = argv[c];
        printf("%ws <-> %ws: %f\n", s.c_str(), arg, stringRank(s, arg));
    }

    return 0;
}
#endif

