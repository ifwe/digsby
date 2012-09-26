!define PAGE_NAME_UNIBLUE "uniblue"
!define PAGE_NUM_UNIBLUE "5"

!define COUNTRY_LOOKUP_URL_UNIBLUE "http://digsby.com/cc"

Var UnibluePage.Image
Var UnibluePage.Show
Var UnibluePage.Install
Var UnibluePage.NextText
Var UnibluePage.BackText
Var UnibluePage.DeclineClicked
Var UnibluePage.Results
Var UnibluePage.Visited

!define IMAGE_NAME_UNIBLUE "uniblue_image.bmp"
!define IMAGE_PATH_UNIBLUE "${DIGSRES}\${IMAGE_NAME_UNIBLUE}"
!define INSTALLER_URL_UNIBLUE "http://partners.digsby.com/uniblue/uniblue_install.exe"

!define TITLE_TEXT_UNIBLUE "How many errors does your computer have?"
!define TEXT_AGREE_UNIBLUE "By clicking $\"Accept$\", I agree to the                            and                        and want to install RegistryBooster."
!define TEXT_TERMS_OF_USE_UNIBLUE "Terms of Service"
!define TEXT_PRIVACY_UNIBLUE "Privacy Policy"

!define URL_TERMS_OF_USE_UNIBLUE "http://www.uniblue.com/terms/"
!define URL_PRIVACY_UNIBLUE "http://www.uniblue.com/privacy/"

!define BUTTONTEXT_NEXT_UNIBLUE "&Accept"
!define BUTTONTEXT_BACK_UNIBLUE "&Decline"

!macro DIGSBY_PAGE_UNIBLUE
    
    Function UnibluePage.InitVars
        StrCpy $UnibluePage.DeclineClicked "False"
        StrCpy $UnibluePage.Install "False"
        StrCpy $UnibluePage.Visited "False"
        StrCpy $UnibluePage.Show 0
        IntOp  $UnibluePage.Results 0 + 0
    FunctionEnd
    
    PageEx custom
        PageCallbacks UnibluePage.OnEnter UnibluePage.OnExit
    PageExEnd
    
    Function UnibluePage.ShouldShow
        StrCpy $1 ""
        
        !ifdef PAGE_NAME_XOBNI
          ${If} $XobniPage.Show == 1
            StrCpy $UnibluePage.Show 0
            Goto skip
          ${EndIf}
        !endif
        
        # Sending them all our traffic for now.
        StrCpy $UnibluePage.Show 1
        
#        inetc::get      \
#         /TIMEOUT 5000  \
#         /SILENT        \
#         /USERAGENT "DigsbyInstaller v${SVNREV}" \
#         "${COUNTRY_LOOKUP_URL_UNIBLUE}" \
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
#            StrCpy $UnibluePage.Show 1
#        ${Else}
#            StrCpy $UnibluePage.Show 0
#        ${EndIf}
        
        skip:
    FunctionEnd
    
    Function UnibluePage.DeclineButtonClicked
        StrCpy $UnibluePage.DeclineClicked "True"
        StrCpy $UnibluePage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd
    
    Function UnibluePage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_UNIBLUE}"
    FunctionEnd
    
    Function UnibluePage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_UNIBLUE}"
    FunctionEnd

    Function UnibluePage.OnEnter
        IfSilent 0 +2
            Abort
        
        ${If} $UnibluePage.Show == 0
            StrCpy $UnibluePage.Install "False"
            Abort
        ${EndIf}

        ${If} $UnibluePage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $UnibluePage.Visited "True"
        ${EndIf}

        IntOp $UnibluePage.Results $UnibluePage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_UNIBLUE}
        
        File "/oname=$PLUGINSDIR\${IMAGE_NAME_UNIBLUE}" "${IMAGE_PATH_UNIBLUE}"
        
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_UNIBLUE}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            
            ${NSD_CreateBitmap} 0 0 0 0 ""
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\${IMAGE_NAME_UNIBLUE}" $UnibluePage.Image
            
            ${NSD_CreateLink} 111u 87% 55u 6% "${TEXT_TERMS_OF_USE_UNIBLUE}" "${URL_TERMS_OF_USE_UNIBLUE}" 
            Pop $1
            ${NSD_OnClick} $1 UnibluePage.TermsOfUseClicked
            SetCtlColors $1 "000080" transparent
            
            ${NSD_CreateLink} 181u 87% 44u 6% "${TEXT_PRIVACY_UNIBLUE}" "${URL_PRIVACY_UNIBLUE}" 
            Pop $1
            ${NSD_OnClick} $1 UnibluePage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 0 87% 100% 12% "${TEXT_AGREE_UNIBLUE}"
            Pop $1
                        
            GetFunctionAddress $1 UnibluePage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1
            
            # Next button
            GetDlgItem $2 $HWNDPARENT 1
            
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $UnibluePage.NextText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_UNIBLUE}'

            # Back button
            GetDlgItem $2 $HWNDPARENT 3
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $UnibluePage.BackText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_UNIBLUE}'
            
        nsDialogs::Show
    FunctionEnd
    
    Function UnibluePage.OnExit
        ${NSD_FreeImage} $UnibluePage.Image
        
        FindWindow $1 "#32770" "" $HWNDPARENT
        
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$UnibluePage.NextText'
        
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$UnibluePage.BackText'
        
        ${If} $UnibluePage.DeclineClicked == "False"
            StrCpy $UnibluePage.Install "True"
        ${EndIf}
    FunctionEnd
    
    Function UnibluePage.PerformInstall
      IntOp $UnibluePage.Results $UnibluePage.Results | ${FLAG_OFFER_ACCEPT}
      #StrCpy $3 '"$PLUGINSDIR\uniblue_install.exe" /S'
      inetc::get     \
      /TIMEOUT 5000  \
      /SILENT        \
      /USERAGENT "DigsbyInstaller v${SVNREV}" \
      "${INSTALLER_URL_UNIBLUE}" \
      "$PLUGINSDIR\uniblue_install.exe"
      
      ExecWait "$PLUGINSDIR\uniblue_install.exe /verysilent" $1
      IntOp $UnibluePage.Results $UnibluePage.Results | ${FLAG_OFFER_SUCCESS}
      
      end:
    FunctionEnd

!macroend

