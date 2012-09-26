SetCompressor /SOLID /FINAL lzma
OutFile "D:\digsbytest\nsis_test.exe"

!include "DigsbyRegister.nsh"
!include "DigsbySearch.nsh"

!insertmacro _FFX_RewriteSearchPlugin "ebay.xml" "ChangeEbaySearchEngineFFX"
!insertmacro _FFX_RewriteSearchPlugin "amazondotcom.xml" "ChangeAmazonSearchEngineFFX"

Section "Install"
  !insertmacro FFX_RewriteSearchPlugin "ebay.xml"
  !insertmacro FFX_RewriteSearchPlugin "amazondotcom.xml"
SectionEnd

