@echo off
setlocal

echo Running digsby unit tests in src/tests/unittests

set PYTHONPATH=.;.\src;.\lib;.\platlib\win;.\ext\win;.\src\plugins
build\msw\dpython\python.exe src\tests\unittests\runtests.py
