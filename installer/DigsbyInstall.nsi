SetCompressor /SOLID /FINAL lzma

!addincludedir "NSIS\Include"
!addplugindir "NSIS\Plugins"

!include "PyInfo.nsh"

!ifdef USE_OPENCANDY
    RequestExecutionLevel admin
!else
    RequestExecutionLevel user
!endif

# HM NIS Edit Wizard helper defines
!define HTTPS "https"
!define PRODUCT_NAME "Digsby"
!define PRODUCT_VERSION "1.0"
!define PRODUCT_PUBLISHER "Tagged, Inc"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_KEY "${PRODUCT_UNINST_KEY}"
!define MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_VALUENAME "InstallPath"

BrandingText "Digsby r${SVNREV}"
InstallButtonText "&Next >"
AutoCloseWindow true

# MUI 1.67 compatible ------
!include "System.nsh"
!include "LogicLib.nsh"
!include "DetailPrint.nsh"
!include "WinMessages.nsh"
!include "TextFunc.nsh"
!include "OpenLinkInBrowser.nsh"
!include "digsbyutil.nsh"

!define MULTIUSER_MUI
!define MULTIUSER_EXECUTIONLEVEL Highest
!define MULTIUSER_INSTALLMODE_INSTDIR_ALLUSERS ${PRODUCT_NAME}
!define MULTIUSER_INSTALLMODE_INSTDIR_CURRENT "${PRODUCT_NAME}\App"
!include "MultiUser.nsh"

!define FLAG_SILENT    1                # Installer run in silent mode?
!define FLAG_SETHOME   2                # did the user set their home page?
!define FLAG_SET_DIGSBYSEARCH    4      # Did they set the digsby search provider
!define FLAG_AMAZON    8                # did the user select the amazon/ebay search options

!define FLAG_OFFER_ASK 1
!define FLAG_OFFER_ACCEPT 2
!define FLAG_OFFER_SUCCESS 4

!define VARNAME_FLAG "f"  # flags mentioned above
!define VARNAME_PAGE "p"  # what page number we finish on
!define VARNAME_INSTVER "v" # the version of the installer
!define VARNAME_DIGSVER "rev" # the SVN revision of digsby
!define VARNAME_EXITPAGE "e"
!define VARNAME_OFFERS_SHOWN "os"
!define VARNAME_OFFER_RESULTS "or"

!insertmacro LineRead

# MUI Settings
!define DIGSINST "${DIGSBY_INSTALLER_DIR}"
!define DIGSRES  "${DIGSINST}\res"

#!include "Offer-OpenCandy.nsh"
#!include "Offer-Bing.nsh"
#!include "Offer-Bccthis.nsh"
#!include "Offer-Xobni.nsh"
#!include "Offer-AskToolbar.nsh"
#!include "Offer-Crawler.nsh"
#!include "Offer-Inbox.nsh"
#!include "Offer-Babylon.nsh"
#!include "Offer-Uniblue.nsh"
#!include "Offer-Aro.nsh"

!include "Page1-Welcome.nsh"
!include "Page5-Finish.nsh"

!ifndef INSTVER
 !define INSTVER_REPLACE 1
 !define INSTVER ""
!else
 !define INSTVER_REPLACE ""
!endif

!define SILENT_VERSION_NUMBER ${INSTVER} # this is the version the installer sends IfSilent

${REDEF} MUI_FINISHPAGE_V_OFFSET -12

!define MUI_ICON "${DIGSRES}\digsby.ico"
!define MUI_UNICON "${DIGSRES}\digsby.ico"

!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT

!define MUI_HEADERIMAGE_BITMAP "${DIGSRES}\new_right_header.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "${DIGSRES}\new_right_header.bmp"

!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${DIGSRES}\wizard-un.bmp"

!define DIGSBY_FINISH_NEXT_TEXT "Launch"
!define DIGSBY_FINISH_CANCEL_DISABLED
!define DIGSBY_FINISH_BACK_DISABLED

!define DIGSBY_FINISH_LAUNCHCHECK_TEXT "&Launch Digsby when my computer starts"
!define DIGSBY_FINISH_PLURALINK_TEXT "?"
!define DIGSBY_FINISH_PLURACHECK_TEXT "Allow Digsby to use idle CPU time for grid computing [   ]"
!define DIGSBY_FINISH_SEARCHCHECK_TEXT "Make Google Powered Digsby Search my &search engine"
!define DIGSBY_FINISH_GOOGLEHOMECHECK_TEXT "Make Google Powered Digsby Search my &home page"
!define DIGSBY_FINISH_PLURALINK_ONCLICK PluraLearnMoreLink
!define DIGSBY_FINISH_LAUNCHCHECK_FUNC AddStartupShortcut
!define DIGSBY_FINISH_PLURACHECK_FUNC EnablePlura
!define DIGSBY_FINISH_SEARCHCHECK_FUNC AddGoogleSearchEngine
!define DIGSBY_FINISH_GOOGLEHOMECHECK_FUNC AddGoogleHomePage

!define DIGSBY_FINISH_LAUNCH_STARTCHECKED
!define DIGSBY_FINISH_PLURA_STARTCHECKED
!define DIGSBY_FINISH_SEARCH_STARTCHECKED
!define DIGSBY_FINISH_GOOGLE_STARTCHECKED

!ifndef DIGSBY_REGISTRATION_IN_INSTALLER
  !define MUI_BUTTONTEXT_FINISH "Launch"
!endif

Var FinishFlags
Var LastSeenpage
Var NumPagesVisited
Var RegisteredAccount
Var HomePageSet
Var SearchPageSet
Var IsPortable

Var PostUrl

!define PLURA_ENABLED_FLAG "--set-plura-enabled"
!define PLURA_DISABLED_FLAG "--set-plura-disabled"
Var PluraCommandString

!define DIGSBY_METRIC_VARS_DEFINED

!insertmacro DIGSBY_WELCOME_INIT
!insertmacro DIGSBY_FINISH_INIT

${REDEF} _UN_ ""

!include "DigsbyIni.nsh"
!include "DigsbyRegister.nsh"

!define FLAG_PLURAPAGE_LEARN 8
Function EnablePlura
    StrCpy $PluraCommandString ${PLURA_ENABLED_FLAG}
FunctionEnd

Function PluraLearnMoreLink
    IntOp $PluraPage.Results $PluraPage.Results | ${FLAG_PLURAPAGE_LEARN}
    ${OpenLinkNewWindow} "${PLURA_LEARNMORE_URL}"
FunctionEnd

Function .onInit
  StrCpy $LastSeenPage ""
  !insertmacro MULTIUSER_INIT
  !insertmacro DIGSBY_WELCOME_VARS_INIT
  !insertmacro DIGSBY_FINISH_VARS_INIT
  IntOp $FinishFlags 0 + 0
  IntOp $NumPagesVisited 0 + 0
  IntOp $RegisteredAccount 0 + 0
  IntOp $HomePageSet 0 + 0
  IntOp $SearchPageSet 0 + 0

  !ifdef PAGE_NAME_XOBNI
    Call XobniPage.InitVars
  !endif

  !ifdef PAGE_NAME_ASK
    Call AskPage.InitVars
  !endif

  !ifdef PAGE_NAME_BING
    Call BingPage.InitVars
  !endif

  !ifdef PAGE_NAME_BCCTHIS
    Call BccthisPage.InitVars
  !endif

  !ifdef PAGE_NAME_BABYLON
    Call BabylonPage.InitVars
  !endif

  !ifdef PAGE_NAME_UNIBLUE
    Call UnibluePage.InitVars
  !endif

  !ifdef PAGE_NAME_ARO
    Call AroPage.InitVars
  !endif

  !ifdef PAGE_NAME_CRAWLER
    Call CrawlerPage.InitVars
  !endif

  !ifdef PAGE_NAME_INBOX
    Call InboxPage.InitVars
  !endif

  !ifdef PAGE_NAME_CAUSES
    Call CausesPage.InitVars
  !endif

  !ifdef PAGE_NAME_PLURA
    Call PluraPage.InitVars
  !endif

  !ifdef PAGE_NAME_OPENCANDY
    Call OpencandyPage.InitVars
  !endif

  StrCpy $PluraCommandString ${PLURA_DISABLED_FLAG}
  StrCpy $user_status "None"
  StrCpy $IsPortable "False"

  InitPluginsDir
  GetTempFileName $0
  Rename $0 "$PLUGINSDIR\register.ini"

  GetTempFileName $0
  Rename $0 "$PLUGINSDIR\errorcodes.ini"

  IfSilent 0 next
    Call EnablePlura
    IntOp $FinishFlags $FinishFlags | ${FLAG_SILENT}

  next:
  Call WriteIni  # From DigsbyIni
FunctionEnd

!macro POST_METRICS
  !ifndef SKIP_METRICS_POST
    !ifdef INSTALLER_PROGRESS_URL
      StrCpy $PostUrl "${INSTALLER_PROGRESS_URL}?"
      StrCpy $PostUrl "$PostUrl${VARNAME_PAGE}=$NumPagesVisited"
      StrCpy $PostUrl "$PostUrl&${VARNAME_DIGSVER}=${SVNREV}"
      IfSilent 0 notsilent
          StrCpy $PostUrl "$PostUrl&${VARNAME_INSTVER}=${SILENT_VERSION_NUMBER}"
          Goto nextvar
      notsilent:
          StrCpy $PostUrl "$PostUrl&${VARNAME_INSTVER}=${INSTVER}${INSTVER_REPLACE}"
      nextvar:


      StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=digsby"
      StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$FinishFlags"

      StrCpy $PostUrl "$PostUrl&${VARNAME_EXITPAGE}=$LastSeenPage"

      !ifdef PAGE_NAME_CAUSES
          ${If} $CausesPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_CAUSES}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$CausesPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_PLURA
          ${If} $PluraPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_PLURA}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$PluraPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_BING
          ${If} $BingPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_BING}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$BingPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_BCCTHIS
          ${If} $BccthisPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_BCCTHIS}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$BccthisPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_BABYLON
          ${If} $BabylonPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_BABYLON}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$BabylonPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_UNIBLUE
          ${If} $UnibluePage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_UNIBLUE}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$UnibluePage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_ARO
          ${If} $AroPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_ARO}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$AroPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_ASK
          ${If} $AskPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_ASK}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$AskPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_XOBNI
          ${If} $XobniPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_XOBNI}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$XobniPage.Results"
          ${EndIf}
      !endif

      !ifdef PAGE_NAME_CRAWLER
          ${If} $CrawlerPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_CRAWLER}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$CrawlerPage.Results"
          ${EndIf}
      !endif

      !ifdef PAGE_NAME_INBOX
          ${If} $InboxPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_INBOX}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$InboxPage.Results"
          ${EndIf}
      !endif
      !ifdef PAGE_NAME_OPENCANDY
          ${If} $OpencandyPage.Visited == "True"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFERS_SHOWN}[]=${PAGE_NAME_OPENCANDY}"
              StrCpy $PostUrl "$PostUrl&${VARNAME_OFFER_RESULTS}[]=$OpencandyPage.Results"
          ${EndIf}
      !endif

      #MessageBox MB_OK "$PostUrl"

      GetTempFileName $R7
      inetc::get       \
      /TIMEOUT 5000    \
      /SILENT          \
      /USERAGENT "DigsbyInstaller v${SVNREV}" \
      "$PostUrl" \
      $R7
    !endif
  !endif
!macroend

Function .onInstSuccess
  !ifdef PAGE_NAME_OPENCANDY
    !insertmacro OpenCandyOnInstSuccess
  !endif

  !ifdef VCREDIST
    Delete "$INSTDIR\vcredist.exe"
  !endif

  ${If} $IsPortable == "False"
      Call AddQuicklaunchShortcut
      Call AddDesktopShortcut
  ${Else}
      Call AddPortableRootShortcut
  ${EndIf}

  !ifndef BRAND
    !ifdef INSTALL_THANKS_URL
      ${OpenLinkNewWindow} "${INSTALL_THANKS_URL}"
    !endif
  !endif

  IfSilent next
    Goto common
  next:
    Call AddStartupShortcut
    !insertmacro POST_METRICS

  common:

  !ifndef DIGSBY_REGISTRATION_IN_INSTALLER
    Call StartDigsby
  !else
    IfSilent 0 end
      Call StartDigsby
  !endif
  end:
FunctionEnd

Function .onInstFailed
    !ifdef PAGE_NAME_OPENCANDY
        !insertmacro OpenCandyOnInstFailed
    !endif
FunctionEnd

Function onUserAbort
    !ifdef PAGE_NAME_OPENCANDY
        IntOp $OpencandyPage.UserAborted 1 + 0
    !endif
FunctionEnd

Function .onGUIEnd
    #MessageBox MB_OK "PageTitle: $OCPageTitle$\r$\nOCPageDesc: $OCPageDesc"

    ## Set flags for stats reporting
    ${If} $HomePageSet != 0
      IntOp $FinishFlags $FinishFlags | ${FLAG_SETHOME}
    ${EndIf}

    ${If} $SearchPageSet != 0
      IntOp $FinishFlags $FinishFlags | ${FLAG_SET_DIGSBYSEARCH}
    ${EndIf}

    IfSilent 0 +2
      IntOp $FinishFlags $FinishFlags | ${FLAG_SILENT}
    ###

    !ifdef PAGE_NAME_OPENCANDY
        !insertmacro OpenCandyOnGuiEnd
        IntCmp $OpencandyPage.UserAborted 0 ocdone
        !insertmacro OpenCandyOnInstFailed
        ocdone:
    !endif

    !insertmacro POST_METRICS
FunctionEnd

!macro DIGSBY_PAGE_REGISTER

  !verbose push
  !verbose ${MUI_VERBOSE}

  !insertmacro MUI_PAGE_INIT

  Page custom DigsbyPageRegister_enter DigsbyPageRegister_leave "" # Both are from DigsbyRegister.nsh

  !verbose pop

!macroend

!insertmacro DIGSBY_PAGE_WELCOME
!insertmacro MULTIUSER_PAGE_INSTALLMODE
!ifdef PAGE_NAME_XOBNI
    !insertmacro DIGSBY_PAGE_XOBNI
!endif
!ifdef PAGE_NAME_BCCTHIS
    !insertmacro DIGSBY_PAGE_BCCTHIS
!endif
!ifdef PAGE_NAME_CRAWLER
    !insertmacro DIGSBY_PAGE_CRAWLER
!endif
!ifdef PAGE_NAME_INBOX
    !insertmacro DIGSBY_PAGE_INBOX
!endif
!ifdef PAGE_NAME_BING
    !insertmacro DIGSBY_PAGE_BING
!endif
!ifdef PAGE_NAME_BABYLON
    !insertmacro DIGSBY_PAGE_BABYLON
!endif
!ifdef PAGE_NAME_OPENCANDY
    !insertmacro DIGSBY_PAGE_OPENCANDY
!endif
!ifdef PAGE_NAME_ASK
    !insertmacro DIGSBY_PAGE_ASK_TOOLBAR
!endif
!ifdef PAGE_NAME_UNIBLUE
    !insertmacro DIGSBY_PAGE_UNIBLUE
!endif
!ifdef PAGE_NAME_ARO
    !insertmacro DIGSBY_PAGE_ARO
!endif

!ifdef DIGSBY_REGISTRATION_IN_INSTALLER
  Page custom DigsbyPageRegister_enter DigsbyPageRegister_leave ""
!endif

!insertmacro MUI_PAGE_INSTFILES
#!insertmacro MUI_PAGE_FINISH
!insertmacro DIGSBY_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

# Reserve files
#!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS

# MUI end ------

Name "${PRODUCT_NAME}" #${PRODUCT_VERSION}
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"

!macro CleanInstDir
  IfFileExists "$INSTDIR\manifest" 0 +2
    Delete "$INSTDIR\manifest"
  IfFileExists "$INSTDIR\${PRODUCT_NAME}.exe" 0 +2
    Delete "$INSTDIR\${PRODUCT_NAME}.exe"
  IfFileExists "$INSTDIR\python25.dll" 0 +2
    Delete "$INSTDIR\python25.dll"
  IfFileExists "$INSTDIR\msvcr90.dll" 0 +2
    Delete "$INSTDIR\msvcr90.dll"
  IfFileExists "$INSTDIR\msvcp90.dll" 0 +2
    Delete "$INSTDIR\msvcp90.dll"
  IfFileExists "$INSTDIR\Microsoft.VC90.CRT.manifest" 0 +2
    Delete "$INSTDIR\Microsoft.VC90.CRT.manifest"
  IfFileExists "$INSTDIR\msvcr71.dll" 0 +2
    Delete "$INSTDIR\msvcr71.dll"

  # delete the updatetag file so that a fresh install brings you back to release
  IfFileExists "$LOCALAPPDATA\${PRODUCT_NAME}\tag.yaml" 0 +2
    Delete "$LOCALAPPDATA\${PRODUCT_NAME}\tag.yaml"

  RMDir /R "$INSTDIR\res"
  RMDir /R "$INSTDIR\logs"
  RMDir /R "$INSTDIR\lib"
  RMDir /R "$INSTDIR\temp"
!macroend

Section "Install"
  StrCpy $LastSeenPage "install"

  Push "wxWindowClassNR"
  Push "Buddy List"
  Call FindWindowClose

  Push "wxWindowClassNR"
  Push "${PRODUCT_NAME} Login"
  Call FindWindowClose

  !insertmacro CleanInstDir

  #System::Call "advapi32::GetUserName(t .r0, *i ${NSIS_MAX_STRLEN} r1) i.r2"
  RMDir /R "$%LocalAppData%\VirtualStore\Program Files\${PRODUCT_NAME}"
  ClearErrors

  CreateDirectory "$INSTDIR"
  ClearErrors

  !ifdef BRAND
    FileOpen $0 "$INSTDIR\brand.yaml" w
    FileWrite $0 "brand: ${BRAND}$\r$\n"
    FileClose $0
  !endif

  !ifdef TAG
    FileOpen $0 "$INSTDIR\tag.yaml" w
    FileWrite $0 "tag: ${TAG}$\r$\n"
    FileClose $0
  !endif

  SetOutPath "$INSTDIR"
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}\support"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_NAME}.exe"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Support\Documentation.lnk" "${DOCUMENTATION_URL}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Support\Forums.lnk" "${FORUM_SUPPORT_URL}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Support\Uninstall.lnk" "$INSTDIR\uninstall.exe"

  ${If} $IsPortable == "False"
      WriteUninstaller "$INSTDIR\uninstall.exe"
      WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
      WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_NAME}.exe"
      WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
!ifdef INSTALL_THANKS_URL
      WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "HelpLink" "${INSTALL_THANKS_URL}"
!endif
      WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
      WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "InstallPath" "$INSTDIR"
      WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Application" "$INSTDIR\${PRODUCT_NAME}.exe"

      CreateDirectory "$SMPROGRAMS\Digsby"
      CreateDirectory "$SMPROGRAMS\Digsby\support"
      CreateShortCut "$SMPROGRAMS\Digsby\Digsby.lnk" "$INSTDIR\Digsby.exe"
      CreateShortCut "$SMPROGRAMS\Digsby\Support\Documentation.lnk" "${DOCUMENTATION_URL}"
      CreateShortCut "$SMPROGRAMS\Digsby\Support\Forums.lnk" "${FORUM_SUPPORT_URL}"
      CreateShortCut "$SMPROGRAMS\Digsby\Support\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  ${EndIf}

  !ifdef VCREDIST_VERSION
      File "/oname=$INSTDIR\vcredist.exe" "${DIGSINST}\${VCREDIST_VERSION}\vcredist.exe"
  !endif

  !ifdef VCREDIST
      DetailPrint "Installing required system components..."
      ExecWait "vcredist.exe /Q"
  !endif

  File /r "${DISTDIR}\*"

  ${If} $IsPortable == "True"
    CreateDirectory "$INSTDIR\res"
    File "/oname=$INSTDIR\res\portable.yaml" "${DIGSRES}\portable.yaml"
  ${EndIf}

  !ifdef PAGE_NAME_CAUSES
      ${If} $CausesPage.Install == "True"
          Call CausesPage.PerformInstall
      ${EndIf}
  !endif

  !ifdef PAGE_NAME_XOBNI
      ${If} $XobniPage.Install == "True"
          Call XobniPage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_CRAWLER
      ${If} $CrawlerPage.Install == "True"
          Call CrawlerPage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_INBOX
      ${If} $InboxPage.Install == "True"
          Call InboxPage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_BING
      ${If} $BingPage.Install == "True"
          Call BingPage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_BCCTHIS
      ${If} $BccthisPage.Install == "True"
          Call BccthisPage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_BABYLON
      ${If} $BabylonPage.Install == "True"
          Call BabylonPage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_UNIBLUE
      ${If} $UnibluePage.Install == "True"
          Call UnibluePage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_ARO
      ${If} $AroPage.Install == "True"
          Call AroPage.PerformInstall
      ${EndIf}
  !endif
  !ifdef PAGE_NAME_ASK
      ${If} $AskPage.Install == "True"
          Call AskPage.PerformInstall
      ${EndIf}
  !endif

  !ifdef PAGE_NAME_PLURA
      ${If} $PluraPage.Install == "True"
          # Actually there's nothing to do for this,
          # the finish page takes care of calling the right functions
      ${EndIf}
  !endif

  !ifdef PAGE_NAME_OPENCANDY
      # This variable doesn't get set, Opencandy manages its own installation
      #${If} $OpencandyPage.Install == "True"
          Call OpencandyPage.PerformInstall
      #${EndIf}
  !endif

SectionEnd

${REDEF} _UN_ "un."

!macro RemoveShortcuts
  RMDir /R "$SMPROGRAMS\${PRODUCT_NAME}\support"
  RMDir /R "$SMPROGRAMS\${PRODUCT_NAME}"

  IfFileExists "$DESKTOP\${PRODUCT_NAME}.lnk" 0 +2
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"

  IfFileExists "$QUICKLAUNCH\${PRODUCT_NAME}.lnk" 0 +2
    Delete "$QUICKLAUNCH\${PRODUCT_NAME}.lnk"

  IfFileExists "$SMPROGRAMS\Startup\${PRODUCT_NAME}.lnk" 0 +2
    Delete "$SMPROGRAMS\Startup\${PRODUCT_NAME}.lnk"
!macroend

Section "Uninstall"
  Push "wxWindowClassNR"
  Push "Buddy List"
  Call un.FindWindowClose

  Push "#32770"
  Push "${PRODUCT_NAME} Login"
  Call un.FindWindowClose

  !insertmacro CleanInstDir

  SetShellVarContext all
  !insertmacro RemoveShortcuts

  SetShellVarContext current
  !insertmacro RemoveShortcuts

!ifdef WHY_UNINSTALL
  # open the 'why did you uninstall' page in a new browser window
  ${OpenLinkNewWindow} "${WHY_UNINSTALL}"
!endif

  IfErrors end
  DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
  IfErrors end
  Delete "$INSTDIR\uninstall.exe"
  RMDir  "$INSTDIR"

  end:
SectionEnd

#Function un.onUninstSuccess
#  HideWindow
#  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
#FunctionEnd

Function un.onInit
#  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove ;$(^Name) and all of its components?" IDYES +2
#  Abort
  !insertmacro MULTIUSER_UNINIT
FunctionEnd

!macro FindWindowClose_definition
    Exch $0
    Exch
    Exch $1
    Push $2
    Push $3
    find:
        FindWindow $2 $1 $0
        IntCmp $2 0 nowindow
            MessageBox MB_OKCANCEL|MB_ICONSTOP "An instance of ${PRODUCT_NAME} is running. Please close it and press OK to continue." IDOK find IDCANCEL abortinst
            Goto find
    abortinst:
      Abort "Please close ${PRODUCT_NAME} to continue this operation."
    nowindow:
    Pop $3
    Pop $2
    Pop $1
    Pop $0
!macroend

Function un.FindWindowClose
  !insertmacro FindWindowClose_definition
FunctionEnd

Function FindWindowClose
  !insertmacro FindWindowClose_definition
FunctionEnd

Function FinishPage_ShowChecks
  FindWindow $R0 "#32770" "" $HWNDPARENT # Parent window

  LockWindow on

  GetDlgItem $R1 $R0 1209
  ShowWindow $R1 ${SW_HIDE}

  GetDlgItem $R1 $R0 1203
  ShowWindow $R1 ${SW_SHOW}

  GetDlgItem $R1 $R0 1204
  ShowWindow $R1 ${SW_SHOW}

  GetDlgItem $R1 $R0 1205
  ShowWindow $R1 ${SW_SHOW}

  GetDlgItem $R1 $R0 1206
  ShowWindow $R1 ${SW_SHOW}

  GetDlgItem $R1 $R0 1208
  ShowWindow $R1 ${SW_SHOW}

  LockWindow off

FunctionEnd
