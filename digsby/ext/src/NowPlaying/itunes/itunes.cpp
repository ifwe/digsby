#include <string>
using std::wstring;

#include "iTunesCOMInterface.h"

#include "NowPlaying.h"

static PlayState playStateForITunesPlayerState(const ITPlayerState& itps)
{
    switch (itps) {
		case ITPlayerStatePlaying:
		case ITPlayerStateFastForward:
		case ITPlayerStateRewind:
		default:
            return Playing;
		case ITPlayerStateStopped:
            return Stopped;
    }
}


#define ERR(x) do { success = false; goto x; } while(0);

bool currentSong_iTunes(SongStatus& songStatus)
{
	IiTunes *itunes = 0;
	IITTrack *track = 0;
    BSTR bstr = 0;
    bool success = true;

	HRESULT hRes = ::CoCreateInstance(CLSID_iTunesApp, NULL, CLSCTX_LOCAL_SERVER, IID_IiTunes, (PVOID *)&itunes);
	if(hRes != S_OK || !itunes)
        ERR(done);

    // get current track in itunes
	if (S_OK != itunes->get_CurrentTrack(&track) || !track)
        ERR(release_itunes);

    if (S_OK != track->get_Name(&bstr) || !bstr) {
        ERR(release_track);
    } else
        songStatus.title = bstr;

    if (S_OK != track->get_Artist(&bstr) || !bstr) {
        ERR(release_track);
    } else
        songStatus.artist = bstr;

    ITPlayerState iIPlayerState;
    if (S_OK != itunes->get_PlayerState(&iIPlayerState))
        ERR(release_track);

    songStatus.status = playStateForITunesPlayerState(iIPlayerState);

    goto done;

release_track:
    track->Release();
release_itunes:
    itunes->Release();

done:
    return success;
}
