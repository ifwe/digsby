!define PAGE_NAME_ARO "aro"
!define PAGE_NUM_ARO "5"

!define COUNTRY_LOOKUP_URL_ARO "http://digsby.com/cc"

Var AroPage.Image
Var AroPage.Show
Var AroPage.Install
Var AroPage.NextText
Var AroPage.BackText
Var AroPage.DeclineClicked
Var AroPage.Results
Var AroPage.Visited

!define IMAGE_NAME_ARO "aro_image.bmp"
!define IMAGE_PATH_ARO "${DIGSRES}\${IMAGE_NAME_ARO}"
!define INSTALLER_URL_ARO "http://partners.digsby.com/aro/aro_installer.exe"

!define TITLE_TEXT_ARO "Is your computer slowing down?"
!define TEXT_AGREE_ARO "By clicking $\"Accept$\", I agree to the          and                        and want to install ARO."
!define TEXT_TERMS_OF_USE_ARO "EULA"
!define TEXT_PRIVACY_ARO "Privacy Policy"

!define URL_TERMS_OF_USE_ARO "http://www.sammsoft.com/ARO_EULA.aspx"
!define URL_PRIVACY_ARO "http://www.sammsoft.com/Privacy.aspx"

!define BUTTONTEXT_NEXT_ARO "&Accept"
!define BUTTONTEXT_BACK_ARO "&Decline"

!macro DIGSBY_PAGE_ARO
    
    Function AroPage.InitVars
        StrCpy $AroPage.DeclineClicked "False"
        StrCpy $AroPage.Install "False"
        StrCpy $AroPage.Visited "False"
        StrCpy $AroPage.Show 0
        IntOp  $AroPage.Results 0 + 0
    FunctionEnd
    
    PageEx custom
        PageCallbacks AroPage.OnEnter AroPage.OnExit
    PageExEnd
    
    Function AroPage.ShouldShow
        StrCpy $1 ""
        
        !ifdef PAGE_NAME_XOBNI
          ${If} $XobniPage.Show == 1
            StrCpy $AroPage.Show 0
            Goto skip
          ${EndIf}
        !endif
        
        # Sending them all our traffic for now.
        StrCpy $AroPage.Show 1
        
#        inetc::get      \
#         /TIMEOUT 5000  \
#         /SILENT        \
#         /USERAGENT "DigsbyInstaller v${SVNREV}" \
#         "${COUNTRY_LOOKUP_URL_ARO}" \
#         "$PLUGINSDIR\country.txt"
#        
#        ClearErrors
#        FileOpen $0 "$PLUGINSDIR\country.txt" r
#        FileRead $0 $1
#        FileClose $0
#        ClearErrors
#        
#        # US only
#        ${If} $1 == "US"
#            StrCpy $AroPage.Show 1
#        ${Else}
#            StrCpy $AroPage.Show 0
#        ${EndIf}
        
        skip:
    FunctionEnd
    
    Function AroPage.DeclineButtonClicked
        StrCpy $AroPage.DeclineClicked "True"
        StrCpy $AroPage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd
    
    Function AroPage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_ARO}"
    FunctionEnd
    
    Function AroPage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_ARO}"
    FunctionEnd

    Function AroPage.OnEnter
        IfSilent 0 +2
            Abort
        
        ${If} $AroPage.Show == 0
            StrCpy $AroPage.Install "False"
            Abort
        ${EndIf}

        ${If} $AroPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $AroPage.Visited "True"
        ${EndIf}

        IntOp $AroPage.Results $AroPage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_ARO}
        
        File "/oname=$PLUGINSDIR\${IMAGE_NAME_ARO}" "${IMAGE_PATH_ARO}"
        
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_ARO}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            
            ${NSD_CreateBitmap} 0 0 0 0 ""
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\${IMAGE_NAME_ARO}" $AroPage.Image
            
            ${NSD_CreateLink} 111u 87% 18u 6% "${TEXT_TERMS_OF_USE_ARO}" "${URL_TERMS_OF_USE_ARO}" 
            Pop $1
            ${NSD_OnClick} $1 AroPage.TermsOfUseClicked
            SetCtlColors $1 "000080" transparent
            
            ${NSD_CreateLink} 145u 87% 44u 6% "${TEXT_PRIVACY_ARO}" "${URL_PRIVACY_ARO}" 
            Pop $1
            ${NSD_OnClick} $1 AroPage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 0 87% 100% 12% "${TEXT_AGREE_ARO}"
            Pop $1
                        
            GetFunctionAddress $1 AroPage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1
            
            # Next button
            GetDlgItem $2 $HWNDPARENT 1
            
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $AroPage.NextText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_ARO}'

            # Back button
            GetDlgItem $2 $HWNDPARENT 3
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $AroPage.BackText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_ARO}'
            
        nsDialogs::Show
    FunctionEnd
    
    Function AroPage.OnExit
        ${NSD_FreeImage} $AroPage.Image
        
        FindWindow $1 "#32770" "" $HWNDPARENT
        
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$AroPage.NextText'
        
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$AroPage.BackText'
        
        ${If} $AroPage.DeclineClicked == "False"
            StrCpy $AroPage.Install "True"
        ${EndIf}
    FunctionEnd
    
    Function AroPage.PerformInstall
      IntOp $AroPage.Results $AroPage.Results | ${FLAG_OFFER_ACCEPT}
      #StrCpy $3 '"$PLUGINSDIR\aro_install.exe" /S'
      inetc::get     \
      /TIMEOUT 5000  \
      /SILENT        \
      /USERAGENT "DigsbyInstaller v${SVNREV}" \
      "${INSTALLER_URL_ARO}" \
      "$PLUGINSDIR\aro_install.exe"
      
      ExecWait "$PLUGINSDIR\aro_install.exe /verysilent /nolaunch" $1
      IntOp $AroPage.Results $AroPage.Results | ${FLAG_OFFER_SUCCESS}
      
      end:
    FunctionEnd

!macroend

