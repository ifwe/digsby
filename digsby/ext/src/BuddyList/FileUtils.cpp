#include "precompiled.h"
#include "config.h"
#include "FileUtils.h"
#include "PythonInterface.h"

#ifdef WIN32
#include <windows.h>



class Glob
{
public:
    Glob(const wstring& wildcard) {
        m_handle = FindFirstFileEx(wildcard.c_str(), FindExInfoBasic, &m_findData, FindExSearchNameMatch, NULL, 0);
        if (ok() && atVDir())
            next();
    }

    bool ok() const { return m_handle != INVALID_HANDLE_VALUE; }

    bool next() {
        BOOL res;
        while (res = FindNextFile(m_handle, &m_findData))
            if (!atVDir())
                return res == TRUE;

        return res == TRUE;
    }

    wchar_t* filename() const { return (wchar_t*)(&m_findData.cFileName); }

    fsize_t fileSize() const {
        return ((fsize_t)m_findData.nFileSizeHigh << 32) + m_findData.nFileSizeLow;
    }

    ~Glob() {
        if (ok())
            FindClose(m_handle);
    }

    const WIN32_FIND_DATA& fileData() { return m_findData; }

protected:
    bool atVDir() const {
        return wcscmp(filename(), L".") == 0 || wcscmp(filename(), L"..") == 0;
    }

    WIN32_FIND_DATA m_findData;
    HANDLE m_handle;
};

bool getLogSizes(LogSizeMap& sizes, const wstring& logdir)
{
    Glob services(logdir + L"\\*");
    if (services.ok()) {
        do {
            wstring service(services.filename());
            wstring servicePath(logdir + L"\\" + service);
            Glob accounts(servicePath + L"\\*");
            if (accounts.ok()) {
                do {
                    wstring accountPath(servicePath + L"\\" + accounts.filename());

                    Glob buddies(accountPath + L"\\*");
                    if (buddies.ok()) {
                        do {
                            wstring buddy(buddies.filename());
                            wstring buddyPath(accountPath + L"\\" + buddy);
                            sizes[buddy] += sumFileSizes(buddyPath + L"\\*-*-*.html");
                        } while(buddies.next());
                    }
                } while (accounts.next());
            }
        } while (services.next());
    }

    return true;
}

fsize_t sumFileSizes(const std::wstring& wildcard)
{
    fsize_t totalSize = 0;

    Glob glob(wildcard);
    if (glob.ok())
        do {
            totalSize += glob.fileSize();
        } while (glob.next());

    return totalSize;
}

bool findFiles(std::vector<std::wstring>& files, const std::wstring& wildcard, bool sort /*=true*/)
{
    Glob glob(wildcard);
    if (glob.ok())
        do {
            files.push_back(glob.filename());
        } while (glob.next());
    else
        return false;

    std::sort(files.begin(), files.end(), std::greater<std::wstring>());
    return true;
}
#else
bool findFiles(std::vector<std::wstring>& files, const std::wstring& wildcard, bool sort)
{
    return false;
}

fsize_t sumFileSizes(const std::wstring& wildcard)
{
    return 0;
}

bool getLogSizes(LogSizeMap& sizes, const wstring& logdir)
{
    return false;
}
#endif

