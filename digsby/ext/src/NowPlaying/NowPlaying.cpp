#include "NowPlaying.h"

#include "itunes.h"

bool currentSong(SongStatus& status)
{
    if (currentSong_iTunes(status))
        return true;

    return false;
}