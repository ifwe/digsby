
!macro openLinkNewWindow_definition
  Push $3
  Push $2
  Push $1
  Push $0
  ReadRegStr $0 HKCR "http\shell\open\command" ""
  StrCpy $2 '"'
  StrCpy $1 $0 1
  StrCmp $1 $2 +2 # if path is not enclosed in " look for space as final char
    StrCpy $2 ' '
  StrCpy $3 1
  loop:
    StrCpy $1 $0 1 $3
    StrCmp $1 $2 found
    StrCmp $1 "" found
    IntOp $3 $3 + 1
    Goto loop

  found:
    StrCpy $1 $0 $3
    StrCmp $2 " " +2
      StrCpy $1 '$1"'

  Pop $0
  Exec '$1 $0'
  Pop $1
  Pop $2
  Pop $3
!macroend

Function func_openLinkNewWindow
  !insertmacro openLinkNewWindow_definition
FunctionEnd

Function un.func_openLinkNewWindow
  !insertmacro openLinkNewWindow_definition
FunctionEnd

!macro _openLinkNewWindow url
    StrCpy $0 ${url}
    Call ${_UN_}func_openLinkNewWindow
!macroend

!define OpenLinkNewWindow "!insertmacro _openLinkNewWindow"

