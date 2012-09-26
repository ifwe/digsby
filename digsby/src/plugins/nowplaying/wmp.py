from comtypes.client import CreateObject
from gui.native.win.process import process_list

WMP_PROCESS_NAME = 'wmplayer.exe'

def currentSong(processes):
    if processes is None:
        processes = process_list()

    if not WMP_PROCESS_NAME in processes:
        return

    wmp = CreateObject("WMPlayer.OCX" )

'''
Wscript.Echo objItem.durationString
Wscript.Echo objItem.sourceURL
Wscript.Echo objSong.getItemInfo("WM/AlbumArtist")
Wscript.Echo objSong.getItemInfo("UserPlayCount")


>    def OnVisible(self,evt):
>        print "OnVisible changed:",evt
>    def OnError(self,evt=None):
>        print "OnError",evt
>    def OnMediaError(self,evt=None):
>        print "OnMediaError",evt
>    def OnDisconnect(self,evt):
>        print "OnDisconnect",evt
>    def OnStatusChange(self):
>        print "OnStatusChange"
>    def OnDisconnect(self,evt):
>        print "Disconnect",evt
>    def OnBuffering(self,evt):
>        print "OnBuffering changed:",evt
>    def OnOpenStateChange(self,evt=None):
>        print "OnOpenStateChange" ,evt
'''

def main():
    from time import clock
    from pprint import pprint
    before = clock()
    pprint(currentSong())

    print 'took', clock() - before

if __name__ == '__main__':
    main()