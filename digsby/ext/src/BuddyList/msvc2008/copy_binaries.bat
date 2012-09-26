@echo off
setlocal

set BUILDDIR=%~d0%~p0\Release
set DEST=%~d0%~p0\..\..\..\..\build\platlib_win32_26

rem "installing buddylist binaries..."
echo blist.pyd
copy %BUILDDIR%\blist.pyd %DEST%
if errorlevel 1 goto done
echo blist.pdb
copy %BUILDDIR%\blist.pdb %DEST%
if errorlevel 1 goto done
echo buddylist.dll
copy %BUILDDIR%\buddylist.dll %DEST%
if errorlevel 1 goto done
echo buddylist.pdb
copy %BUILDDIR%\buddylist.pdb %DEST%
if errorlevel 1 goto done

:done
