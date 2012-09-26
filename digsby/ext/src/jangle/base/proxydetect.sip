
%ModuleHeaderCode
#include "talk/base/proxydetect.h"
%End

bool GetProxySettingsForUrl(const char* agent, const char* url,
                            talk_base::ProxyInfo& proxy /Out/,
                            bool long_operation = false);