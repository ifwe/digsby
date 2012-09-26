!include "nsDialogs_createTextMultiline.nsh"

!define PAGE_NAME_ASK "ask"
!define PAGE_NUM_ASK "4"
!define FLAG_ASKPAGE_SETSEARCH 8

Var AskPage.SearchCheck
Var AskPage.SearchCheck.Value # Holds the value so it stays the same between page views
!define SEARCHCHECK_INITIAL_VALUE_ASKPAGE "${BST_CHECKED}"

Var AskPage.AcceptCheck
Var AskPage.AcceptCheck.Value # Holds the value so it stays the same between page views
!define ACCEPTCHECK_INITIAL_VALUE_ASKPAGE "${BST_CHECKED}"

Var AskPage.ToolbarImage # needs to be freed later
Var AskPage.LicenseTextCtrl
Var AskPage.Show
Var AskPage.Install
Var AskPage.Visited
Var AskPage.Results

!define TITLE_TEXT_ASKPAGE "Better Web Browsing with Digsby Ask Toolbar"
!define TOP_TEXT_ASKPAGE "The Digsby Ask Toolbar makes web browsing more convenient! You can search the web anytime, keep up to date on news, weather, sports, maps, and more!"
!define IMAGE_PATH_ASKPAGE "${DIGSRES}\toolbar_headimg.bmp"
!define SEARCHCHECK_TEXT_ASKPAGE "&Make Ask my default search provider"
!define LICENSE_FILE_ASKPAGE "${DIGSRES}\toolbar_license.txt"
!define ACCEPTCHECK_TEXT_ASKPAGE "I &accept the license agreement and want to install the free Digsby Ask Toolbar"
!define INSTALLCHECKER_EXE_ASKPAGE "${DIGSRES}\AskInstallChecker-1.2.0.0.exe"
!define TOOLBAR_ID "DGY" 

!define TOOLBAR_INSTALLER_URL "http://partners.digsby.com/ask/askToolbarInstaller-1.5.0.0.exe"

!macro DIGSBY_PAGE_ASK_TOOLBAR

    Function AskPage.InitVars
        StrCpy $AskPage.Install "False"
        StrCpy $AskPage.Visited "False"
        StrCpy $AskPage.Show 0
        IntOp  $AskPage.Results 0 + 0
    FunctionEnd
    
    PageEx custom

      PageCallbacks AskPage.OnEnter AskPage.OnExit
      
    PageExEnd
    
    Function AskPage.ShouldShow
        File "/oname=$PLUGINSDIR\install_checker.exe" "${INSTALLCHECKER_EXE_ASKPAGE}"
        ExecWait '"$PLUGINSDIR\install_checker.exe" ${TOOLBAR_ID}' $1
        ${If} $1 == 0  # 0 means there is none already installed
            StrCpy $AskPage.Show 1
        ${Else}
            StrCpy $AskPage.Show 0
        ${EndIf}
    FunctionEnd
    
    Function AskPage.AcceptCheckChanged
        ${NSD_GetState} $AskPage.AcceptCheck $1
        ${If} $1 == ${BST_UNCHECKED}
            EnableWindow $AskPage.SearchCheck 0
            ${NSD_SetState} $AskPage.SearchCheck ${BST_UNCHECKED}
            StrCpy $AskPage.Install "False"
        ${Else} 
            EnableWindow $AskPage.SearchCheck 1
            ${NSD_SetState} $AskPage.SearchCheck ${BST_CHECKED}
            StrCpy $AskPage.Install "True"
        ${EndIf}
        Call AskPage.SaveCheckValues
    FunctionEnd

    Function AskPage.SaveCheckValues
        Pop $1
        ${NSD_GetState} $AskPage.AcceptCheck $1
        StrCpy $AskPage.AcceptCheck.Value $1
        
        ${NSD_GetState} $AskPage.SearchCheck $1
        StrCpy $AskPage.SearchCheck.Value $1

    FunctionEnd

    Function AskPage.SetLicenseText
       ClearErrors
       FileOpen $0 "$PLUGINSDIR\toolbar_license.txt" r
       IfErrors exit
       System::Call 'kernel32::GetFileSize(i r0, i 0) i .r1'
       IntOp $1 $1 + 1 ; for terminating zero
       System::Alloc $1
       Pop $2
       System::Call 'kernel32::ReadFile(i r0, i r2, i r1, *i .r3, i 0)'
       FileClose $0
       SendMessage $AskPage.LicenseTextCtrl ${EM_SETLIMITTEXT} $1 0
       SendMessage $AskPage.LicenseTextCtrl ${WM_SETTEXT} 0 $2
       System::Free $2
    exit:
 
    FunctionEnd
    
    Function AskPage.OnEnter
        IfSilent 0 +2
            Abort

        DetailPrint "Initializing..."
        ${If} $AskPage.Show == 0
            StrCpy $AskPage.AcceptCheck.Value ${BST_UNCHECKED}
            StrCpy $AskPage.SearchCheck.Value ${BST_UNCHECKED}
            StrCpy $AskPage.Install "False"
            Abort
        ${EndIf}
        
        ${If} $AskPage.Visited == "False"
            ${incr} $NumPagesVisited 1
            StrCpy $AskPage.Visited "True"
        ${EndIf}

        StrCpy $LastSeenPage ${PAGE_NAME_ASK}
        
        IntOp $AskPage.Results $AskPage.Results | ${FLAG_OFFER_ASK}
        
        File "/oname=$PLUGINSDIR\toolbar_headimg.bmp" "${IMAGE_PATH_ASKPAGE}"
        File "/oname=$PLUGINSDIR\toolbar_license.txt" "${LICENSE_FILE_ASKPAGE}"
    
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_ASKPAGE}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            ${NSD_CreateLabel} 0 0% 100% 12% "${TOP_TEXT_ASKPAGE}"
            Pop $1
            
            ${NSD_CreateBitmap} 0 14% 100% 12% "Image goes here ${IMAGE_PATH_ASKPAGE}"
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\toolbar_headimg.bmp" $AskPage.ToolbarImage 
            
            ## 'Search' checkbox
            ${NSD_CreateCheckbox} 0 28% 100% 6% "${SEARCHCHECK_TEXT_ASKPAGE}"
            Pop $AskPage.SearchCheck
            # Set checked
            ${If} $AskPage.SearchCheck.Value == ""
                StrCpy $AskPage.SearchCheck.Value ${SEARCHCHECK_INITIAL_VALUE_ASKPAGE}
            ${EndIf}
            ${NSD_SetState} $AskPage.SearchCheck $AskPage.SearchCheck.Value
            ${NSD_OnClick} $AskPage.SearchCheck AskPage.SaveCheckValues

            ${NSD_CreateTextMultiline} 0 36% 100% 54% ""
            Pop $AskPage.LicenseTextCtrl
            Call AskPage.SetLicenseText
            
            # Set $1 to read only
            SendMessage $1 ${EM_SETREADONLY} 1 0
            # Set it to be black-on-white-text (instead of "disabled" color background).
            # (does not obey system color settings)
            SetCtlColors $1 "000000" "FFFFFF"

            ## 'Accept' checkbox
            ${NSD_CreateCheckbox} 0 92% 100% 6% "${ACCEPTCHECK_TEXT_ASKPAGE}"
            Pop $AskPage.AcceptCheck
            
            # Set checked
            ${If} $AskPage.AcceptCheck.Value == ""
                StrCpy $AskPage.AcceptCheck.Value ${ACCEPTCHECK_INITIAL_VALUE_ASKPAGE}
            ${EndIf}

            ${NSD_SetState} $AskPage.AcceptCheck $AskPage.AcceptCheck.Value
            ${NSD_OnClick} $AskPage.AcceptCheck AskPage.AcceptCheckChanged
            
        nsDialogs::Show
    FunctionEnd
    
    Function AskPage.OnExit
        ${NSD_FreeImage} $AskPage.ToolbarImage
        
        ${NSD_GetState} $AskPage.AcceptCheck $1
        ${If} $1 == ${BST_UNCHECKED}
            StrCpy $AskPage.Install "False"
        ${Else} 
            StrCpy $AskPage.Install "True"
        ${EndIf}

    FunctionEnd

    Function AskPage.PerformInstall
      StrCpy $3 '"$PLUGINSDIR\ask_installer.exe" toolbar=${TOOLBAR_ID}'
      ${If} $AskPage.Install == "True"
          StrCpy $3 "$3 /tbr"
          IntOp $AskPage.Results $AskPage.Results | ${FLAG_OFFER_ACCEPT}
      ${EndIf}

      ${If} $AskPage.SearchCheck.Value == "${BST_CHECKED}"
          StrCpy $3 "$3 /sa"
          IntOp $AskPage.Results $AskPage.Results | ${FLAG_ASKPAGE_SETSEARCH}
      ${EndIf}
      
      ${If} $AskPage.Install == "True"
        inetc::get       \
          /TIMEOUT 5000  \
          /SILENT        \
          /USERAGENT "DigsbyInstaller v${SVNREV}" \
          "${TOOLBAR_INSTALLER_URL}" \
          "$PLUGINSDIR\ask_installer.exe"

          ExecWait $3 $1
          ${If} $1 == 0
            IntOp $AskPage.Results $AskPage.Results | ${FLAG_OFFER_SUCCESS}
          ${EndIf}
      ${EndIf}
    FunctionEnd

!macroend
