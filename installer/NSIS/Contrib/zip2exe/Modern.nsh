;Change this file to customize zip2exe generated installers with a modern interface

!include "MUI.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"

!define DIGSINST "c:\workspace\installer"
!define DIGSRES  "${DIGSINST}\res"

!define MUI_ICON "${DIGSRES}\digsby.ico"
!define MUI_UNICON "${DIGSRES}\digsby.ico"

!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT

!define MUI_HEADERIMAGE_BITMAP "${DIGSRES}\new_right_header.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "${DIGSRES}\new_right_header.bmp"

!define MUI_WELCOMEFINISHPAGE_BITMAP "${DIGSRES}\wizard.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${DIGSRES}\wizard-un.bmp"  

!define MUI_FINISHPAGE_RUN 
!define MUI_FINISHPAGE_RUN_TEXT "Add shortcut to &Desktop"
!define MUI_FINISHPAGE_RUN_FUNCTION AddDesktopShortcut

!define MUI_FINISHPAGE_SHOWREADME
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Add shortcut to &QuickLaunch"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION AddQuicklaunchShortcut

!define MUI_FINISHPAGE_CHECKBOX3
!define MUI_FINISHPAGE_CHECKBOX3_TEXT "&Launch digsby when my computer starts"
!define MUI_FINISHPAGE_CHECKBOX3_FUNCTION AddStartupShortcut

!define MUI_FINISHPAGE_CHECKBOX4
!define MUI_FINISHPAGE_CHECKBOX4_TEXT "&Make Google Search my home page"
!define MUI_FINISHPAGE_CHECKBOX4_FUNCTION AddGoogleHomePage

!define MUI_FINISHPAGE_CHECKBOX5
!define MUI_FINISHPAGE_CHECKBOX5_TEXT "&Run digsby now"
!define MUI_FINISHPAGE_CHECKBOX5_FUNCTION StartDigsby

!include "${DIGSINST}\DigsbyIni.nsh"
!include "${DIGSINST}\DigsbyRegister.nsh"

Function .onInit

  StrCpy $user_status "None"

  InitPluginsDir
  GetTempFileName $0
  Rename $0 "$PLUGINSDIR\register.ini"
  
  GetTempFileName $0
  Rename $0 "$PLUGINSDIR\errorcodes.ini"
  
  Call WriteIni  ; From DigsbyIni
  
  
FunctionEnd

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${DIGSINST}\license.txt"
!insertmacro MUI_PAGE_DIRECTORY
Page custom DigsbyPageRegister_enter DigsbyPageRegister_leave "" 
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English" 

