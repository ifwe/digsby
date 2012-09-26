@echo off
setlocal

rem path to .pyd and .dll
set bindir=msvc2008\Release

set PYTHONPATH=%PYTHONPATH%;%~d0%~p0\%bindir%

pushd %~d0%~p0\test

rem Run Python unittests
%DIGSBY_PYTHON%\python.exe sorter_test.py
if errorlevel 1 goto done

rem Run C++ unittests
pushd %~d0%~p0\%bindir%
buddylist_test.exe

:done
popd
popd


