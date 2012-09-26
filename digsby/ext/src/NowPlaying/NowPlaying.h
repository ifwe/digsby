#ifndef NowPlaying_h
#define NowPlaying_h

#include <string>

#ifdef NOWPLAYING_EXPORTS
#define NP_EXPORT __declspec(dllexport)
#else
#define NP_EXPORT
#endif

enum PlayState
{
    Playing,
    Stopped
};

struct SongStatus
{
    std::wstring filename;
    std::wstring artist;
    std::wstring title;
    PlayState status;
    unsigned int duration;
    unsigned int playlist_position;
    int rating;
    unsigned int size;
};

NP_EXPORT bool currentSong(SongStatus& status);

#endif

