/*

MultiUser.nsh

Installer configuration for multi-user Windows environments

Copyright © 2008 Joost Verburg

*/

!ifndef MULTIUSER_INCLUDED
!define MULTIUSER_INCLUDED
!define PAGE_NAME_MULTIUSER "dir"
!verbose push
!verbose 3

;Standard NSIS header files

!ifdef MULTIUSER_MUI
  !include MUI2.nsh
!endif
!include nsDialogs.nsh
!include LogicLib.nsh
!include WinVer.nsh
!include FileFunc.nsh
!include StrFunc.nsh

;Variables

Var MultiUser.Privileges
Var MultiUser.InstallMode
Var MultiUser.Visited

;Command line installation mode setting

!ifdef MULTIUSER_INSTALLMODE_COMMANDLINE
  !insertmacro GetParameters
  !ifndef MULTIUSER_NOUNINSTALL
    !insertmacro un.GetParameters
  !endif
  !include StrFunc.nsh
  !ifndef StrStr_INCLUDED
    ${StrStr}
  !endif
  !ifndef MULTIUSER_NOUNINSTALL
    !ifndef UnStrStr_INCLUDED
      ${UnStrStr}
    !endif
  !endif
  
  Var MultiUser.Parameters
  Var MultiUser.Result
!endif

;Installation folder stored in registry

!ifdef MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_KEY & MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_VALUENAME
  Var MultiUser.InstDir
!endif

!ifdef MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY & MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME
  Var MultiUser.DefaultKeyValue
!endif

;Windows Vista UAC setting

!if "${MULTIUSER_EXECUTIONLEVEL}" == Admin
  RequestExecutionLevel admin
  !define MULTIUSER_EXECUTIONLEVEL_ALLUSERS
!else if "${MULTIUSER_EXECUTIONLEVEL}" == Power
  RequestExecutionLevel admin
  !define MULTIUSER_EXECUTIONLEVEL_ALLUSERS
!else if "${MULTIUSER_EXECUTIONLEVEL}" == Highest
  RequestExecutionLevel highest
  !define MULTIUSER_EXECUTIONLEVEL_ALLUSERS
!else
  RequestExecutionLevel user
!endif

/*

Install modes

*/

!macro MULTIUSER_INSTALLMODE_ALLUSERS UNINSTALLER_PREFIX UNINSTALLER_FUNCPREFIX

  ;Install mode initialization - per-machine

  ${ifnot} ${IsNT}
    ${orif} $MultiUser.Privileges == "Admin"
    ${orif} $MultiUser.Privileges == "Power"
  
    StrCpy $MultiUser.InstallMode AllUsers
  
    SetShellVarContext all
  
    !if "${UNINSTALLER_PREFIX}" != UN
      ;Set default installation location for installer
      !ifdef MULTIUSER_INSTALLMODE_INSTDIR_ALLUSERS
        StrCpy $INSTDIR "$PROGRAMFILES\${MULTIUSER_INSTALLMODE_INSTDIR_ALLUSERS}"
      !endif
    !endif
  
    !ifdef MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_KEY & MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_VALUENAME
  
      ReadRegStr $MultiUser.InstDir HKLM "${MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_KEY}" "${MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_VALUENAME}"
  
      ${if} $MultiUser.InstDir != ""
        StrCpy $INSTDIR $MultiUser.InstDir
      ${endif}
  
    !endif
  
    !ifdef MULTIUSER_INSTALLMODE_${UNINSTALLER_PREFIX}FUNCTION
      Call "${MULTIUSER_INSTALLMODE_${UNINSTALLER_PREFIX}FUNCTION}"
    !endif
    
  ${endif}

!macroend

!macro MULTIUSER_INSTALLMODE_CURRENTUSER UNINSTALLER_PREFIX UNINSTALLER_FUNCPREFIX

  ;Install mode initialization - per-user
  
  ${if} ${IsNT}  
  
    StrCpy $MultiUser.InstallMode CurrentUser
    
    SetShellVarContext current
  
    !if "${UNINSTALLER_PREFIX}" != UN
      ;Set default installation location for installer  
      !ifdef MULTIUSER_INSTALLMODE_INSTDIR_CURRENT | MULTIUSER_INSTALLMODE_INSTDIR_ALLUSERS
        ${if} ${AtLeastWin2000}
          StrCpy $INSTDIR "$LOCALAPPDATA\${MULTIUSER_INSTALLMODE_INSTDIR_CURRENT}"
        ${else}
          StrCpy $INSTDIR "$PROGRAMFILES\${MULTIUSER_INSTALLMODE_INSTDIR_ALLUSERS}"
        ${endif}
      !endif
    !endif
  
    !ifdef MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_KEY & MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_VALUENAME
  
      ReadRegStr $MultiUser.InstDir HKCU "${MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_KEY}" "${MULTIUSER_INSTALLMODE_INSTDIR_REGISTRY_VALUENAME}"
  
      ${if} $MultiUser.InstDir != ""
        StrCpy $INSTDIR $MultiUser.InstDir
      ${endif}
  
    !endif
  
    !ifdef MULTIUSER_INSTALLMODE_${UNINSTALLER_PREFIX}FUNCTION
      Call "${MULTIUSER_INSTALLMODE_${UNINSTALLER_PREFIX}FUNCTION}"
    !endif
  
  ${endif}

!macroend
!macro MULTIUSER_INSTALLMODE_PORTABLE UNINSTALLER_PREFIX UNINSTALLER_FUNCPREFIX
    StrCpy $MultiUser.InstallMode Portable
    SetShellVarContext current
!macroend

Function MultiUser.InstallMode.AllUsers
  !insertmacro MULTIUSER_INSTALLMODE_ALLUSERS "" ""
FunctionEnd

Function MultiUser.InstallMode.CurrentUser
  !insertmacro MULTIUSER_INSTALLMODE_CURRENTUSER "" ""
FunctionEnd

Function MultiUser.InstallMode.Portable
  !insertmacro MULTIUSER_INSTALLMODE_PORTABLE "" ""
FunctionEnd

!ifndef MULTIUSER_NOUNINSTALL

Function un.MultiUser.InstallMode.AllUsers
  !insertmacro MULTIUSER_INSTALLMODE_ALLUSERS UN .un
FunctionEnd

Function un.MultiUser.InstallMode.CurrentUser
  !insertmacro MULTIUSER_INSTALLMODE_CURRENTUSER UN .un
FunctionEnd

Function un.MultiUser.InstallMode.Portable
  !insertmacro MULTIUSER_INSTALLMODE_PORTABLE UN .un
FunctionEnd

!endif

/*

Installer/uninstaller initialization

*/

!macro MULTIUSER_INIT_QUIT UNINSTALLER_FUNCPREFIX

  !ifdef MULTIUSER_INIT_${UNINSTALLER_FUNCPREFIX}FUNCTIONQUIT
    Call "${MULTIUSER_INIT_${UNINSTALLER_FUNCPREFIX}FUCTIONQUIT}
  !else
    Quit
  !endif

!macroend

!macro MULTIUSER_INIT_TEXTS

  !ifndef MULTIUSER_INIT_TEXT_ADMINREQUIRED
    !define MULTIUSER_INIT_TEXT_ADMINREQUIRED "$(^Caption) requires administrator priviledges."
  !endif

  !ifndef MULTIUSER_INIT_TEXT_POWERREQUIRED
    !define MULTIUSER_INIT_TEXT_POWERREQUIRED "$(^Caption) requires at least Power User priviledges."
  !endif

  !ifndef MULTIUSER_INIT_TEXT_ALLUSERSNOTPOSSIBLE
    !define MULTIUSER_INIT_TEXT_ALLUSERSNOTPOSSIBLE "Your user account does not have sufficient privileges to install $(^Name) for all users of this computer."
  !endif

!macroend

!macro MULTIUSER_INIT_CHECKS UNINSTALLER_PREFIX UNINSTALLER_FUNCPREFIX

  ;Installer initialization - check privileges and set install mode

  !insertmacro MULTIUSER_INIT_TEXTS

  UserInfo::GetAccountType
  Pop $MultiUser.Privileges
  
  ${if} ${IsNT}
  
    ;Check privileges
  
    !if "${MULTIUSER_EXECUTIONLEVEL}" == Admin
  
      ${if} $MultiUser.Privileges != "Admin"
        MessageBox MB_OK|MB_ICONSTOP "${MULTIUSER_INIT_TEXT_ADMINREQUIRED}"
        !insertmacro MULTIUSER_INIT_QUIT "${UNINSTALLER_FUNCPREFIX}"
      ${endif}
  
    !else if "${MULTIUSER_EXECUTIONLEVEL}" == Power
  
      ${if} $MultiUser.Privileges != "Power"
        ${andif} $MultiUser.Privileges != "Admin"
        ${if} ${AtMostWinXP}
           MessageBox MB_OK|MB_ICONSTOP "${MULTIUSER_INIT_TEXT_POWERREQUIRED}"
        ${else}
           MessageBox MB_OK|MB_ICONSTOP "${MULTIUSER_INIT_TEXT_ADMINREQUIRED}"
        ${endif}        
        !insertmacro MULTIUSER_INIT_QUIT "${UNINSTALLER_FUNCPREFIX}"
      ${endif}
  
    !endif
    
    !ifdef MULTIUSER_EXECUTIONLEVEL_ALLUSERS
    
      ;Default to per-machine installation if possible
    
      ${if} $MultiUser.Privileges == "Admin"
        ${orif} $MultiUser.Privileges == "Power"
        !ifndef MULTIUSER_INSTALLMODE_DEFAULT_CURRENTUSER
          Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.AllUsers
        !else
          Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.CurrentUser
        !endif

        !ifdef MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY & MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME

          ;Set installation mode to setting from a previous installation

          !ifndef MULTIUSER_INSTALLMODE_DEFAULT_CURRENTUSER
            ReadRegStr $MultiUser.DefaultKeyValue HKLM "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY}" "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME}"
            ${if} $MultiUser.DefaultKeyValue == ""
              ReadRegStr $MultiUser.DefaultKeyValue HKCU "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY}" "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME}"
              ${if} $MultiUser.DefaultKeyValue != ""
                Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.CurrentUser
              ${endif}
            ${endif}
          !else
            ReadRegStr $MultiUser.DefaultKeyValue HKCU "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY}" "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME}"
            ${if} $MultiUser.DefaultKeyValue == ""
              ReadRegStr $MultiUser.DefaultKeyValue HKLM "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_KEY}" "${MULTIUSER_INSTALLMODE_DEFAULT_REGISTRY_VALUENAME}"
              ${if} $MultiUser.DefaultKeyValue != ""
                Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.AllUsers
              ${endif}
            ${endif}
          !endif

        !endif

      ${else}
        Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.CurrentUser
      ${endif}
    
    !else

      Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.CurrentUser

    !endif
  
    !ifdef MULTIUSER_INSTALLMODE_COMMANDLINE
    
      ;Check for install mode setting on command line

      ${${UNINSTALLER_FUNCPREFIX}GetParameters} $MultiUser.Parameters
  
      ${${UNINSTALLER_PREFIX}StrStr} $MultiUser.Result $MultiUser.Parameters "/CurrentUser"    
    
      ${if} $MultiUser.Result != ""
        Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.CurrentUser
      ${endif}    
  
      ${${UNINSTALLER_PREFIX}StrStr} $MultiUser.Result $MultiUser.Parameters "/AllUsers"    
    
      ${if} $MultiUser.Result != ""
        ${if} $MultiUser.Privileges == "Admin"
          ${orif} $MultiUser.Privileges == "Power"
          Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.AllUsers
        ${else}
          MessageBox MB_OK|MB_ICONSTOP "${MULTIUSER_INIT_TEXT_ALLUSERSNOTPOSSIBLE}"
        ${endif}
      ${endif}
  
    !endif
    
  ${else}
  
    ;Not running Windows NT, per-user installation not supported
    
    Call ${UNINSTALLER_FUNCPREFIX}MultiUser.InstallMode.AllUsers
  
  ${endif}

!macroend

!macro MULTIUSER_INIT
  !verbose push
  !verbose 3
  
  !insertmacro MULTIUSER_INIT_CHECKS "" ""
  
  !verbose pop 
!macroend

!ifndef MULTIUSER_NOUNINSTALL

!macro MULTIUSER_UNINIT
  !verbose push
  !verbose 3
  
  !insertmacro MULTIUSER_INIT_CHECKS Un un.
  
  !verbose pop 
!macroend

!endif

/*

Modern UI 2 page

*/

!ifdef MULTIUSER_MUI

!macro MULTIUSER_INSTALLMODEPAGE_INTERFACE

  !ifndef MULTIUSER_INSTALLMODEPAGE_INTERFACE
    !define MULTIUSER_INSTALLMODEPAGE_INTERFACE
    Var MultiUser.InstallModePage
    
    Var MultiUser.InstallModePage.Text
    
    Var MultiUser.InstallModePage.AllUsers
    Var MultiUser.InstallModePage.CurrentUser
    Var MultiUser.InstallModePage.Portable
    Var MultiUser.InstallModePage.DirectorySelect
    Var MultiUser.InstallModePage.DirBrowseButton
    
    Var MultiUser.InstallModePage.ReturnValue
    Var MultiUser.DirectoryResult
  !endif

!macroend

!macro MULTIUSER_PAGEDECLARATION_INSTALLMODE

  !insertmacro MUI_SET MULTIUSER_${MUI_PAGE_UNINSTALLER_PREFIX}INSTALLMODEPAGE
  !insertmacro MULTIUSER_INSTALLMODEPAGE_INTERFACE

  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_TEXT_TOP "$(MULTIUSER_INNERTEXT_INSTALLMODE_TOP)"
  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_TEXT_ALLUSERS "All Users"
  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_SUBTEXT_ALLUSERS 'You are the computer administrator and can install to the $\"Program Files$\" folder'
  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_TEXT_CURRENTUSER "Single User"  
  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_SUBTEXT_CURRENTUSER "You have a limited account and can't install to the $\"Program Files$\" folder"
  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_TEXT_PORTABLE "Portable"
  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_SUBTEXT_PORTABLE "Install Digsby to a USB drive or other portable device"
  !insertmacro MUI_DEFAULT MULTIUSER_INSTALLMODEPAGE_TEXT_DIRSELECT "$(MULTIUSER_INNERTEXT_INSTALLMODE_DIRSELECT)"  

  PageEx custom

    PageCallbacks MultiUser.InstallModePre_${MUI_UNIQUEID} MultiUser.InstallModeLeave_${MUI_UNIQUEID}

    Caption " "

  PageExEnd

  !insertmacro MULTIUSER_FUNCTION_INSTALLMODEPAGE MultiUser.InstallModePre_${MUI_UNIQUEID} MultiUser.InstallModeLeave_${MUI_UNIQUEID}

  !undef MULTIUSER_INSTALLMODEPAGE_TEXT_TOP
  !undef MULTIUSER_INSTALLMODEPAGE_TEXT_ALLUSERS
  !undef MULTIUSER_INSTALLMODEPAGE_TEXT_CURRENTUSER
  !undef MULTIUSER_INSTALLMODEPAGE_TEXT_PORTABLE
  !undef MULTIUSER_INSTALLMODEPAGE_SUBTEXT_ALLUSERS
  !undef MULTIUSER_INSTALLMODEPAGE_SUBTEXT_CURRENTUSER
  !undef MULTIUSER_INSTALLMODEPAGE_SUBTEXT_PORTABLE

!macroend

!macro MULTIUSER_PAGE_INSTALLMODE

  ;Modern UI page for install mode

  !verbose push
  !verbose 3
  
  !ifndef MULTIUSER_EXECUTIONLEVEL_ALLUSERS
    !error "A mixed-mode installation requires MULTIUSER_EXECUTIONLEVEL to be set to Admin, Power or Highest."
  !endif
  
  !insertmacro MUI_PAGE_INIT
  !insertmacro MULTIUSER_PAGEDECLARATION_INSTALLMODE
  
  !verbose pop

!macroend

!macro SyncInstDir
    ${NSD_GetText} $MultiUser.InstallModePage.DirectorySelect $MultiUser.DirectoryResult
    ${If} $MultiUser.DirectoryResult != ""
        StrCpy $INSTDIR $MultiUser.DirectoryResult
        ${NSD_SetText} $MultiUser.InstallModePage.DirectorySelect $INSTDIR
    ${EndIf}
    #MessageBox MB_OK "SyncEnd: $MultiUser.DirectoryResult" 
!macroend

!macro SetPathForRadio
    ${NSD_GetState} $MultiUser.InstallModePage.CurrentUser $1
    ${NSD_GetState} $MultiUser.InstallModePage.AllUsers $2
    ${if} $1 == ${BST_CHECKED}  # current user is checked
        ExpandEnvStrings $3 "$LOCALAPPDATA\${MULTIUSER_INSTALLMODE_INSTDIR_CURRENT}"
    ${elseif} $2 == ${BST_CHECKED} # all users is checked
        ExpandEnvStrings $3 "$PROGRAMFILES\${MULTIUSER_INSTALLMODE_INSTDIR_ALLUSERS}"
    ${else} # portable is checked
        ExpandEnvStrings $3 "C:\${MULTIUSER_INSTALLMODE_INSTDIR_CURRENT}"
    ${endif}
    ${NSD_SetText} $MultiUser.InstallModePage.DirectorySelect $3
    !insertmacro SyncInstDir
    
!macroend

!macro MULTIUSER_FUNCTION_INSTALLMODEPAGE PRE LEAVE

  ;Page functions of Modern UI page

    Function nsDialogsPageRadioClicked
      StrCpy $IsPortable "False"
      Pop $1 # clear the clicked window off the stack
      SendMessage $MultiUser.InstallModePage.AllUsers ${BM_GETCHECK} 0 0 $1
      SendMessage $MultiUser.InstallModePage.CurrentUser ${BM_GETCHECK} 0 0 $2
     
      ${if} $1 = ${BST_CHECKED}
         StrCpy $MultiUser.InstallModePage.ReturnValue "all"
      ${elseif} $2 = ${BST_CHECKED}
         StrCpy $MultiUser.InstallModePage.ReturnValue "current"
      ${else}
         StrCpy $MultiUser.InstallModePage.ReturnValue "portable"
      ${endif}
  
      !insertmacro SetPathForRadio
  FunctionEnd
  
  Function nsDialogsBrowseButtonClicked
      Pop $1 # clear the clicked window off the stack

      ${NSD_GetText} $MultiUser.InstallModePage.DirectorySelect $1
      nsDialogs::SelectFolderDialog /NOUNLOAD "Select Folder" $1
      Pop $1
      StrLen $2 $1
      ${If} $2 = 3
        StrCpy $1 $1 -1
      ${EndIf}
      ${if} $1 != ""
        ${andif} $1 != "error"
          ${if} $MultiUser.InstallModePage.ReturnValue == "all"
            ${NSD_SetText} $MultiUser.InstallModePage.DirectorySelect "$1\${MULTIUSER_INSTALLMODE_INSTDIR_ALLUSERS}"
          ${else}
            ${NSD_SetText} $MultiUser.InstallModePage.DirectorySelect "$1\${MULTIUSER_INSTALLMODE_INSTDIR_CURRENT}"
          ${endif}
          !insertmacro SyncInstDir
      ${endif}
      
  FunctionEnd
  
  Function nsDialogsPortableRadioClicked
      ${NSD_SetText} $MultiUser.InstallModepage.DirectorySelect "C:\"
      Call nsDialogsPageRadioClicked
      Push $1
      Call nsDialogsBrowseButtonClicked
      StrCpy $IsPortable "True"
  FunctionEnd
  
  Function nsDialogsDirSelectTextChanged
    Pop $1
    #!insertmacro SyncInstDir
  FunctionEnd

  Function "${PRE}"
  
    ${ifnot} ${IsNT}
      Abort
    ${endif}
    
    ${If} $MultiUser.Visited != "True"
        ${incr} $NumPagesVisited 1
        StrCpy $MultiUser.Visited "True"
    ${EndIf}

    StrCpy $LastSeenPage ${PAGE_NAME_MULTIUSER}

    !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
    !insertmacro MUI_HEADER_TEXT_PAGE $(MULTIUSER_TEXT_INSTALLMODE_TITLE) $(MULTIUSER_TEXT_INSTALLMODE_SUBTITLE)
    
    nsDialogs::Create /NOUNLOAD 1018
    Pop $MultiUser.InstallModePage

    ${NSD_CreateLabel} 0u 0u 300u 20u "${MULTIUSER_INSTALLMODEPAGE_TEXT_TOP}"
    Pop $MultiUser.InstallModePage.Text

    ${NSD_CreateRadioButton} 20u 27u 280u 10u "${MULTIUSER_INSTALLMODEPAGE_TEXT_ALLUSERS}"
    Pop $MultiUser.InstallModePage.AllUsers
    #SendMessage $MultiUser.InstallModePage.AllUsers ${TB_SETSTYLE} ${SW_BOLD}
    ${NSD_OnClick} $MultiUser.InstallModePage.AllUsers nsDialogsPageRadioClicked
    
    ${NSD_CreateLabel} 32u 37u 280u 10u "${MULTIUSER_INSTALLMODEPAGE_SUBTEXT_ALLUSERS}"
    Pop $1
    
    ${NSD_CreateRadioButton} 20u 51u 280u 10u "${MULTIUSER_INSTALLMODEPAGE_TEXT_CURRENTUSER}"
    Pop $MultiUser.InstallModePage.CurrentUser
    # Set bold
    ${NSD_OnClick} $MultiUser.InstallModePage.CurrentUser nsDialogsPageRadioClicked
    
    ${NSD_CreateLabel} 32u 61u 280u 10u "${MULTIUSER_INSTALLMODEPAGE_SUBTEXT_CURRENTUSER}"
    Pop $1
    
    ${NSD_CreateRadioButton} 20u 77u 280u 10u "${MULTIUSER_INSTALLMODEPAGE_TEXT_PORTABLE}"
    Pop $MultiUser.InstallModePage.Portable
    
    ${NSD_OnClick} $MultiUser.InstallModePage.Portable nsDialogsPortableRadioClicked
    
    ${NSD_CreateLabel} 32u 87u 280u 10u "${MULTIUSER_INSTALLMODEPAGE_SUBTEXT_PORTABLE}"
    
    ${NSD_CreateGroupBox} 10u 110u 290u 30u "Destination Folder"
    Pop $1

    ${NSD_CreateDirRequest} 20u 122u 200u 12u "${MULTIUSER_INSTALLMODEPAGE_TEXT_DIRSELECT}"
    Pop $MultiUser.InstallModePage.DirectorySelect
    ${NSD_OnChange} $MultiUser.InstallModePage.DirectorySelect nsDialogsDirSelectTextChanged
    
    ${NSD_CreateBrowseButton} 230u 120u 56u 16u "Browse..."
    Pop $MultiUser.InstallModePage.DirBrowseButton
    ${NSD_OnClick} $MultiUser.InstallModePage.DirBrowseButton nsDialogsBrowseButtonClicked
    
    ${if} $MultiUser.InstallMode == "AllUsers"
      SendMessage $MultiUser.InstallModePage.AllUsers ${BM_SETCHECK} ${BST_CHECKED} 0
    ${else}
      SendMessage $MultiUser.InstallModePage.CurrentUser ${BM_SETCHECK} ${BST_CHECKED} 0
    ${endif}
    
    ${if} $MultiUser.Privileges != "Power"
      ${andif} $MultiUser.Privileges != "Admin"
      SendMessage $MultiUser.InstallModePage.CurrentUser ${BM_SETCHECK} ${BST_CHECKED} 0
      EnableWindow $MultiUser.InstallModePage.AllUsers 0
    ${endif}

    !insertmacro SetPathForRadio
    
    !insertmacro MUI_PAGE_FUNCTION_CUSTOM SHOW
    nsDialogs::Show
    
  FunctionEnd

  Function "${LEAVE}"
    SendMessage $MultiUser.InstallModePage.AllUsers ${BM_GETCHECK} 0 0 $1
    SendMessage $MultiUser.InstallModePage.CurrentUser ${BM_GETCHECK} 0 0 $2
    
    ${if} $1 = ${BST_CHECKED}
       StrCpy $MultiUser.InstallModePage.ReturnValue "all"
       Call MultiUser.InstallMode.AllUsers
    ${elseif} $2 = ${BST_CHECKED}
       StrCpy $MultiUser.InstallModePage.ReturnValue "current"
       Call MultiUser.InstallMode.CurrentUser
    ${else}
       StrCpy $MultiUser.InstallModePage.ReturnValue "portable"
       Call MultiUser.InstallMode.Portable
    ${endif}
  
    !insertmacro SyncInstDir
    
    !insertmacro MUI_PAGE_FUNCTION_CUSTOM LEAVE
  FunctionEnd

!macroend

!endif

!verbose pop
!endif
