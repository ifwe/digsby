#include <rpc.h>

#include <iostream>
using std::wcout;
using std::wostream;
using std::endl;

#include "NowPlaying.h"

static const char* stringForStatus(const PlayState& s)
{
    switch (s) {
        case Playing: return "playing";
        case Stopped: return "stopped";
        default: return "<<unknown>>";
    }
}

wostream& operator << (wostream& o, const SongStatus& s)
{
    o << "title:  " << s.title << endl
      << "artist: " << s.artist<< endl
      << "status: " << stringForStatus(s.status) << endl
      ;
    return o;
}

void main(int argc, char** argv)
{
    CoInitialize(0);
    SongStatus status;

    if (currentSong(status)) {
        wcout << "currentSong:" << endl << status << endl;

    } else {
        wcout << "could not get current song" << endl;
    }

    CoUninitialize();
    system("pause");
}
