!define PAGE_NAME_CRAWLER "crawler"

!define COUNTRY_LOOKUP_URL_CRAWLER "http://digsby.com/cc"

Var CrawlerPage.Image
Var CrawlerPage.Show
Var CrawlerPage.Install
Var CrawlerPage.NextText
Var CrawlerPage.BackText
Var CrawlerPage.DeclineClicked
Var CrawlerPage.Results
Var CrawlerPage.Visited

!define IMAGE_NAME_CRAWLER "crawler_image.bmp"
!define IMAGE_PATH_CRAWLER "${DIGSRES}\${IMAGE_NAME_CRAWLER}"
!define INSTALLER_URL_CRAWLER "http://partners.digsby.com/crawler/CrawlerSetup.exe"

!define TITLE_TEXT_CRAWLER "Enhance Your Browser Experience with Crawler Toolbar"
!define TEXT_AGREE_CRAWLER "By clicking $\"Accept$\", I agree to the                            and                        and want to install the Crawler toolbar. I accept to change default search provider to Crawler Search."
!define TEXT_TERMS_OF_USE_CRAWLER "Terms of Service"
!define TEXT_PRIVACY_CRAWLER "Privacy Policy"
!define TEXT_HELP_CRAWLER "More Help"

!define URL_TERMS_OF_USE_CRAWLER "http://www.crawler.com/terms_of_use.aspx"
!define URL_PRIVACY_CRAWLER "http://www.crawler.com/privacy_policy.aspx"
!define URL_HELP_CRAWLER "http://www.crawler.com/faqs.aspx"

!define BUTTONTEXT_NEXT_CRAWLER "&Accept"
!define BUTTONTEXT_BACK_CRAWLER "&Decline"

!macro DIGSBY_PAGE_CRAWLER

    Function CrawlerPage.InitVars
        StrCpy $CrawlerPage.DeclineClicked "False"
        StrCpy $CrawlerPage.Install "False"
        StrCpy $CrawlerPage.Visited "False"
        StrCpy $CrawlerPage.Show 0
        IntOp  $CrawlerPage.Results 0 + 0
    FunctionEnd

    PageEx custom
        PageCallbacks CrawlerPage.OnEnter CrawlerPage.OnExit
    PageExEnd

    Function CrawlerPage.ShouldShow
        # 50% chance to not show
        Push "2"
        nsRandom::GetRandom
        Pop $1
        ${If} $1 = 0
            StrCpy $CrawlerPage.Show 0
            Goto skip
        ${EndIf}

        # Check for previous install first
    
        inetc::get      \
         /TIMEOUT 5000  \
         /SILENT        \
         /USERAGENT "DigsbyInstaller v${SVNREV}" \
         "${COUNTRY_LOOKUP_URL_CRAWLER}" \
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
            StrCpy $CrawlerPage.Show 1
        ${Else}
            StrCpy $CrawlerPage.Show 0
        ${EndIf}

        skip:
    FunctionEnd
    
    Function CrawlerPage.DeclineButtonClicked
        StrCpy $CrawlerPage.DeclineCLicked "True"
        StrCpy $CrawlerPage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd
    
    Function CrawlerPage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_CRAWLER}"
    FunctionEnd
    
    Function CrawlerPage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_CRAWLER}"
    FunctionEnd

    Function CrawlerPage.MoreHelpClicked
        ${OpenLinkNewWindow} "${URL_HELP_CRAWLER}"
    FunctionEnd

    Function CrawlerPage.OnEnter
        IfSilent 0 +2
            Abort
            
        ${If} $CrawlerPage.Show == 0
            StrCpy $CrawlerPage.Install "False"
            Abort
        ${EndIf}
        
        ${If} $CrawlerPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $CrawlerPage.Visited "True"
        ${EndIf}
        
        IntOp $CrawlerPage.Results $CrawlerPage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_CRAWLER}
        
        File "/oname=$PLUGINSDIR\${IMAGE_NAME_CRAWLER}" "${IMAGE_PATH_CRAWLER}"
        
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_CRAWLER}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            ${NSD_CreateBitmap} 0 0 0 0 ""
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\${IMAGE_NAME_CRAWLER}" $CrawlerPage.Image
            
            ${NSD_CreateLink} 112u 87% 54u 6% "${TEXT_TERMS_OF_USE_CRAWLER}" "${URL_TERMS_OF_USE_CRAWLER}"
            Pop $1
            ${NSD_OnClick} $1 CrawlerPage.TermsOfUseClicked
            SetCtlCOlors $1 "000080" transparent
            
            ${NSD_CreateLink} 181u 87% 44u 6% "${TEXT_PRIVACY_CRAWLER}" "${URL_PRIVACY_CRAWLER}"
            Pop $1
            ${NSD_OnClick} $1 CrawlerPage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent
            
            ${NSD_CreateLink} 254u 130u 38u 6% "${TEXT_HELP_CRAWLER}" "${URL_HELP_CRAWLER}"
            Pop $1
            ${NSD_OnClick} $1 CrawlerPage.MoreHelpClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 0 87% 102% 12% "${TEXT_AGREE_CRAWLER}"
            Pop $1
            
            GetFunctionAddress $1 CrawlerPage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1
            
            GetDlgItem $2 $HWNDPARENT 1
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $CrawlerPage.NextText $0
            
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_CRAWLER}'
            
            GetDlgItem $2 $HWNDPARENT 3
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $CrawlerPage.BackText $0
            
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_CRAWLER}'
            
        nsDialogs::Show
    FunctionEnd
    
    Function CrawlerPage.OnExit
        ${NSD_FreeImage} $CrawlerPage.Image
        
        FindWindow $1 "#32770" "" $HWNDPARENT
        
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$CrawlerPage.NextText'
        
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$CrawlerPage.BackText'
        
        ${If} $CrawlerPage.DeclineClicked == "False"
            StrCpy $CrawlerPage.Install "True"
        ${EndIf}
    FunctionEnd
    
    Function CrawlerPage.PerformInstall
        IntOp $CrawlerPage.Results $CrawlerPage.Results | ${FLAG_OFFER_ACCEPT}
        
        StrCpy $3 '"$PLUGINSDIR\crawler_install.exe" /VERYSILENT /NORESTART'
        inetc::get     \
          /TIMEOUT 5000  \
          /SILENT        \
          /USERAGENT "DigsbyInstaller v${SVNREV}" \
          "${INSTALLER_URL_CRAWLER}" \
          "$PLUGINSDIR\crawler_install.exe"

        ExecWait $3 $1
        
        IntOp $CrawlerPage.Results $CrawlerPage.Results | ${FLAG_OFFER_SUCCESS}
        end:
          
    FunctionEnd

!macroend