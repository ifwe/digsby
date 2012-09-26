@setlocal
@echo off

set BROWSER=%ProgramFiles%\safari\safari.exe
set PORT=4224
set CONFIG=%~d0%~p0\..\..\..\plugins\twitter\jsTestDriver.conf

java -jar %~d0%~p0\JsTestDriver-1.2.2.jar --port %PORT% --browser "%BROWSER%"  --tests all --testOutput testOutputDir --config "%CONFIG%"

