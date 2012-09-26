!define PAGE_NAME_BING "bing"
!define PAGE_NUM_BING "5"

!define COUNTRY_LOOKUP_URL_BING "http://digsby.com/cc"

Var BingPage.Image
Var BingPage.Show
Var BingPage.Install
Var BingPage.NextText
Var BingPage.BackText
Var BingPage.DeclineClicked
Var BingPage.Results
Var BingPage.Visited

!define IMAGE_NAME_BING "bing_image.bmp"
!define IMAGE_PATH_BING "${DIGSRES}\${IMAGE_NAME_BING}"
!define INSTALLER_URL_BING "http://partners.digsby.com/bing/bing_install.exe"

!define TITLE_TEXT_BING "Better Web Browsing with the Bing Bar"
!define TEXT_AGREE_BING "By clicking $\"Accept$\", I agree to the          and                        and want to install the Search toolbar powered by Bing. I accept to change my home page and browser search to Bing."
!define TEXT_TERMS_OF_USE_BING "EULA"
!define TEXT_PRIVACY_BING "Privacy Policy"

!define URL_TERMS_OF_USE_BING "http://www.zugosearch.com/terms/"
!define URL_PRIVACY_BING "http://www.zugosearch.com/privacy/"

!define BUTTONTEXT_NEXT_BING "&Accept"
!define BUTTONTEXT_BACK_BING "&Decline"

!macro DIGSBY_PAGE_BING
    
    Function BingPage.InitVars
        StrCpy $BingPage.DeclineClicked "False"
        StrCpy $BingPage.Install "False"
        StrCpy $BingPage.Visited "False"
        StrCpy $BingPage.Show 0
        IntOp  $BingPage.Results 0 + 0
    FunctionEnd
    
    PageEx custom
        PageCallbacks BingPage.OnEnter BingPage.OnExit
    PageExEnd
    
    Function BingPage.ShouldShow
        Push "100"
        nsRandom::GetRandom
        Pop $1
        ${If} $1 > 30
            StrCpy $BingPage.Show 0
            Goto skip
        ${EndIf}
    
        StrCpy $1 ""
        
        inetc::get      \
         /TIMEOUT 5000  \
         /SILENT        \
         /USERAGENT "DigsbyInstaller v${SVNREV}" \
         "${COUNTRY_LOOKUP_URL_BING}" \
         "$PLUGINSDIR\country.txt"
        
        ClearErrors
        FileOpen $0 "$PLUGINSDIR\country.txt" r
        FileRead $0 $1
        FileClose $0
        ClearErrors
        
        ${If} $1 == "US"
            StrCpy $BingPage.Show 1
        ${Else}
            StrCpy $BingPage.Show 0
        ${EndIf}
        
        skip:
    FunctionEnd
    
    Function BingPage.DeclineButtonClicked
        StrCpy $BingPage.DeclineClicked "True"
        StrCpy $BingPage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd
    
    Function BingPage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_BING}"
    FunctionEnd
    
    Function BingPage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_BING}"
    FunctionEnd

    Function BingPage.OnEnter
        IfSilent 0 +2
            Abort
        
        ${If} $BingPage.Show == 0
            StrCpy $BingPage.Install "False"
            Abort
        ${EndIf}

        ${If} $BingPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $BingPage.Visited "True"
        ${EndIf}

        IntOp $BingPage.Results $BingPage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_BING}
        
        File "/oname=$PLUGINSDIR\${IMAGE_NAME_BING}" "${IMAGE_PATH_BING}"
        
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_BING}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            
            ${NSD_CreateBitmap} 0 0 0 0 ""
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\${IMAGE_NAME_BING}" $BingPage.Image
            
            ${NSD_CreateLink} 112u 87% 18u 6% "${TEXT_TERMS_OF_USE_BING}" "${URL_TERMS_OF_USE_BING}" 
            Pop $1
            ${NSD_OnClick} $1 BingPage.TermsOfUseClicked
            SetCtlColors $1 "000080" transparent
            
            ${NSD_CreateLink} 145u 87% 44u 6% "${TEXT_PRIVACY_BING}" "${URL_PRIVACY_BING}" 
            Pop $1
            ${NSD_OnClick} $1 BingPage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 0 87% 102% 12% "${TEXT_AGREE_BING}"
            Pop $1
                        
            GetFunctionAddress $1 BingPage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1
            
            # Next button
            GetDlgItem $2 $HWNDPARENT 1
            
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $BingPage.NextText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_BING}'

            # Back button
            GetDlgItem $2 $HWNDPARENT 3
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $BingPage.BackText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_BING}'
            
        nsDialogs::Show
    FunctionEnd
    
    Function BingPage.OnExit
        ${NSD_FreeImage} $BingPage.Image
        
        FindWindow $1 "#32770" "" $HWNDPARENT
        
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$BingPage.NextText'
        
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$BingPage.BackText'
        
        ${If} $BingPage.DeclineClicked == "False"
            StrCpy $BingPage.Install "True"
        ${EndIf}
    FunctionEnd
    
    Function BingPage.PerformInstall
      IntOp $BingPage.Results $BingPage.Results | ${FLAG_OFFER_ACCEPT}
      StrCpy $3 '"$PLUGINSDIR\bing_install.exe" /TOOLBAR /DEFAULTSEARCH /DEFAULTSTART'
      inetc::get     \
      /TIMEOUT 5000  \
      /SILENT        \
      /USERAGENT "DigsbyInstaller v${SVNREV}" \
      "${INSTALLER_URL_BING}" \
      "$PLUGINSDIR\bing_install.exe"

      ExecWait $3 $1
      IntOp $BingPage.Results $BingPage.Results | ${FLAG_OFFER_SUCCESS}
      
      end:

    FunctionEnd

!macroend

