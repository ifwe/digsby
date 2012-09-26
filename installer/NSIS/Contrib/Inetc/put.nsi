
;--------------------------------
; General Attributes

Name "Inetc Test"
OutFile "put.exe"


;--------------------------------
;Interface Settings

  !include "MUI.nsh"
  !define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install-colorful.ico"
  !insertmacro MUI_PAGE_INSTFILES
  !insertmacro MUI_LANGUAGE "English"


;--------------------------------
;Installer Sections

Section "Dummy Section" SecDummy

; this is my LAN sample, use your own URL for tests. Login/pwd hidden from user. Sample put.php (for http request) included

    inetc::put /POPUP "http://p320/" /CAPTION "my local http upload" "http://takhir:pwd@p320/m2.jpg" "$EXEDIR\m2.jpg"
;    inetc::put /POPUP "ftp://p320/" /CAPTION "my local ftp upload" "ftp://takhir:pwd@p320/m2.bu.jpg" "$EXEDIR\m2.jpg"
    Pop $0 # return value = exit code, "OK" if OK
    MessageBox MB_OK "Upload Status: $0"

SectionEnd
