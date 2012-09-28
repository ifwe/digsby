Required tools:
===============
 * [msysgit](http://code.google.com/p/msysgit/downloads/list)
 * [cygwin](http://svn.webkit.org/repository/webkit/trunk/Tools/CygwinDownloader/cygwin-downloader.zip)
    * Note: on windows with UAC enabled, it may fail to run setup.exe after downloading packages. You'll have to run it manually.
    * After installing, open a cygwin shell (cygwin.bat) and execute `perl -e "use Switch;"`
    * If you don't get an error, cygwin is configured properly. Otherwise, execute the following:
        * `curl -L http://search.cpan.org/CPAN/authors/id/R/RG/RGARCIA/Switch-2.16.tar.gz -o Switch-2.16.tar.gz`
        * `tar -xzf Switch-2.16.tar.gz`
        * `cd Switch-2.16`
        * `perl Makefile.PL && make && make install`
 * Microsoft Visual C++ and components
    * [Visual C++ Express](http://www.microsoft.com/visualstudio/en-us/products/2008-editions/express)
    * [.NET Framework 4](https://www.microsoft.com/en-us/download/details.aspx?id=17851)
    * [Windows SDK 7.1](http://www.microsoft.com/en-us/download/details.aspx?id=8279)
    * After installing these components, run `"c:\Program Files\Microsoft SDKs\Windows\v7.1\Setup\WindowsSdkVer.exe" -version:v7.1`
 * [SWIG](http://sourceforge.net/projects/swig/files/swigwin/swigwin-2.0.7/swigwin-2.0.7.zip/download)
    * You'll have to put this on your `PATH` manually.
 * An SVN client ([Tortoise](http://tortoisesvn.net/downloads.html), [Slik](http://www.sliksvn.com/en/download/), [CollabNet](http://www.collab.net/downloads/subversion))
    * Make sure the executing `svn` in your cmd.exe shell succeeds. If not, you'll have to add your client's `bin` directory to your `PATH` manually.
 * [Python 2.6.*](http://www.python.org/download/releases/)
    * As of 2012-Jul-25, the latest binary release is [2.6.6](http://www.python.org/ftp/python/2.6.6/python-2.6.6.msi)
    * Also unpack the [source distribution](http://www.python.org/ftp/python/2.6.6/Python-2.6.6.tgz) on top of your install directory. This will make the headers (\*.h) and object files (\*.lib) for components that will be compiled.
 * [setuptools](http://pypi.python.org/packages/2.6/s/setuptools/setuptools-0.6c11.win32-py2.6.exe#md5=1509752c3c2e64b5d0f9589aafe053dc)
 * [bakefile](http://iweb.dl.sourceforge.net/project/bakefile/bakefile/0.2.9/bakefile-0.2.9-setup.exe)
 * pip - install with `c:\Python26\Scripts\easy_install pip`
 * virtualenv - install with `c:\Python26\Scripts\pip install virtualenv`


Dependencies
============
Assumptions - replace where necessary:
 * Your digsby checkout is in `c:\digsby`
 * You python install is in `c:\Python26`

1. Open the 'Microsoft Visual Studio Command Prompt'
2. `cd c:\digsby`
3. `c:\Python26\Scripts\virtualenv -p c:\python26\python.exe --distribute digsby-venv`
4. `digsby-venv\Scripts\activate.bat`
5. `python bootstrap.py`
6. `deactivate`
7. `digsby-venv\Scripts\activate.bat`
    * bootstrap modifies the activate script.
8. Run MSYS from within your command prompt by executing `Git Bash.lnk` from your msysgit install directory
    * You should now be inside of an MSYS shell with the correct Visual Studio environment variables set.
9. `buildout`
10. `python sanity.py -_xmlextra -blist -cgui -sip -wx -wx.calendar -wx.lib -wx.py -wx.stc -wx.webview`
    * All components should be `OK`. If not, see `Dependency Troubleshooting`, below.
11. `python digsby\build\msw\build_all.py`
12. `python sanity.py`
    * All components should be `OK`. If not, see `Dependency Troubleshooting`, below.

Dependency Troubleshooting
==========================
TODO

Running Digsby
==============
`python Digsby.py`
