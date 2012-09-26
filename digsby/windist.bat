rem
rem builds a Digsby windows installer
rem

set DIGSBY_INSTALLER_DIR=build\msw\DigsbyInstaller
set DIGSBY_LAUNCHER_DIR=c:\dev\digsby-launcher\bin

rem update all sources
svn up

pushd %DIGSBY_INSTALLER_DIR%
svn up
popd

pushd %DIGSBY_LAUNCHER_DIR%
svn up
popd

rem make the distribution and installer
call dpy makedist.py -p package.py %1 %2 %3 %4 %5 %6

rem copy installers over to mini
copy dist\digsby_setup*.exe \\192.168.1.100\mike /Y

rem pushd build\msw
rem call ss.bat
rem popd
