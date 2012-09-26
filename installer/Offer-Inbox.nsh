!define PAGE_NAME_INBOX "inbox"

!define COUNTRY_LOOKUP_URL_INBOX "http://digsby.com/cc"

Var InboxPage.Image
Var InboxPage.Show
Var InboxPage.Install
Var InboxPage.NextText
Var InboxPage.BackText
Var InboxPage.DeclineClicked
Var InboxPage.Results
Var InboxPage.Visited

!define IMAGE_NAME_INBOX "inbox_image.bmp"
!define IMAGE_PATH_INBOX "${DIGSRES}\${IMAGE_NAME_INBOX}"
!define INSTALLER_URL_INBOX "http://partners.digsby.com/inbox/inbox_install.exe"

!define TITLE_TEXT_INBOX "Enhance Your Browser Experience with Inbox Toolbar"
!define TEXT_AGREE_INBOX "By clicking $\"Accept$\", I agree to the                            and                        and want to install the Inbox toolbar. I accept to change default search provider to Inbox Search."
!define TEXT_TERMS_OF_USE_INBOX "Terms of Service"
!define TEXT_PRIVACY_INBOX "Privacy Policy"

!define URL_TERMS_OF_USE_INBOX "http://toolbar.inbox.com/legal/terms.aspx"
!define URL_PRIVACY_INBOX "http://toolbar.inbox.com/legal/privacy.aspx"

!define BUTTONTEXT_NEXT_INBOX "&Accept"
!define BUTTONTEXT_BACK_INBOX "&Decline"

!macro DIGSBY_PAGE_INBOX

    Function InboxPage.InitVars
        StrCpy $InboxPage.DeclineClicked "False"
        StrCpy $InboxPage.Install "False"
        StrCpy $InboxPage.Visited "False"
        StrCpy $InboxPage.Show 0
        IntOp  $InboxPage.Results 0 + 0
    FunctionEnd

    PageEx custom
        PageCallbacks InboxPage.OnEnter InboxPage.OnExit
    PageExEnd

    Function InboxPage.ShouldShow
        # Check for previous install first

        # 90% chance to not show
        Push "100"
        nsRandom::GetRandom
        Pop $1
        ${If} $1 < 90
            StrCpy $InboxPage.Show 0
            Goto skip
        ${EndIf}

        inetc::get      \
         /TIMEOUT 5000  \
         /SILENT        \
         /USERAGENT "DigsbyInstaller v${SVNREV}" \
         "${COUNTRY_LOOKUP_URL_INBOX}" \
         "$PLUGINSDIR\country.txt"
        
        ClearErrors
        FileOpen $0 "$PLUGINSDIR\country.txt" r
        FileRead $0 $1
        FileClose $0
        ClearErrors
        
        ${If} $1 == "US"
          ${OrIf} $1 == "GB"
          ${OrIf} $1 == "CA"
          ${OrIf} $1 == "AU"
            StrCpy $InboxPage.Show 1
        ${Else}
            StrCpy $InboxPage.Show 0
        ${EndIf}
        
        skip:
    FunctionEnd
    
    Function InboxPage.DeclineButtonClicked
        StrCpy $InboxPage.DeclineCLicked "True"
        StrCpy $InboxPage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd
    
    Function InboxPage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_INBOX}"
    FunctionEnd
    
    Function InboxPage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_INBOX}"
    FunctionEnd

    Function InboxPage.OnEnter
        IfSilent 0 +2
            Abort
            
        ${If} $InboxPage.Show == 0
            StrCpy $InboxPage.Install "False"
            Abort
        ${EndIf}
        
        ${If} $InboxPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $InboxPage.Visited "True"
        ${EndIf}
        
        IntOp $InboxPage.Results $InboxPage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_INBOX}
        
        File "/oname=$PLUGINSDIR\${IMAGE_NAME_INBOX}" "${IMAGE_PATH_INBOX}"
        
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_INBOX}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            ${NSD_CreateBitmap} 0 0 0 0 ""
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\${IMAGE_NAME_INBOX}" $InboxPage.Image
            
            ${NSD_CreateLink} 112u 87% 54u 6% "${TEXT_TERMS_OF_USE_INBOX}" "${URL_TERMS_OF_USE_INBOX}"
            Pop $1
            ${NSD_OnClick} $1 InboxPage.TermsOfUseClicked
            SetCtlCOlors $1 "000080" transparent
            
            ${NSD_CreateLink} 181u 87% 44u 6% "${TEXT_PRIVACY_INBOX}" "${URL_PRIVACY_INBOX}"
            Pop $1
            ${NSD_OnClick} $1 InboxPage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent
            
            ${NSD_CreateLabel} 0 87% 102% 12% "${TEXT_AGREE_INBOX}"
            Pop $1
            
            GetFunctionAddress $1 InboxPage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1
            
            GetDlgItem $2 $HWNDPARENT 1
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $InboxPage.NextText $0
            
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_INBOX}'
            
            GetDlgItem $2 $HWNDPARENT 3
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $InboxPage.BackText $0
            
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_INBOX}'
            
        nsDialogs::Show
    FunctionEnd
    
    Function InboxPage.OnExit
        ${NSD_FreeImage} $InboxPage.Image
        
        FindWindow $1 "#32770" "" $HWNDPARENT
        
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$InboxPage.NextText'
        
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$InboxPage.BackText'
        
        ${If} $InboxPage.DeclineClicked == "False"
            StrCpy $InboxPage.Install "True"
        ${EndIf}
    FunctionEnd
    
    Function InboxPage.PerformInstall
        IntOp $InboxPage.Results $InboxPage.Results | ${FLAG_OFFER_ACCEPT}
        
        StrCpy $3 '"$PLUGINSDIR\inbox_install.exe" /VERYSILENT /NORESTART'
        inetc::get     \
          /TIMEOUT 5000  \
          /SILENT        \
          /USERAGENT "DigsbyInstaller v${SVNREV}" \
          "${INSTALLER_URL_INBOX}" \
          "$PLUGINSDIR\inbox_install.exe"
          
        ExecWait $3 $1
        
        IntOp $InboxPage.Results $InboxPage.Results | ${FLAG_OFFER_SUCCESS}

        end:
    FunctionEnd

!macroend