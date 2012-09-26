@echo off

if "%1" == "" goto error
python build_%1.py %2 %3 %4 %5 %6 %7 %8 %9
goto done

:error
python build_all.py --help

:done
