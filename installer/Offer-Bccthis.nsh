!define PAGE_NAME_BCCTHIS "bccthis"
!define PAGE_NUM_BCCTHIS "5"

!define COUNTRY_LOOKUP_URL_BCCTHIS "http://digsby.com/cc"

Var BccthisPage.Image
Var BccthisPage.Show
Var BccthisPage.Install
Var BccthisPage.NextText
Var BccthisPage.BackText
Var BccthisPage.DeclineClicked
Var BccthisPage.Results
Var BccthisPage.Visited

!define IMAGE_NAME_BCCTHIS "bccthis_image.bmp"
!define IMAGE_PATH_BCCTHIS "${DIGSRES}\${IMAGE_NAME_BCCTHIS}"
!define INSTALLER_URL_BCCTHIS "http://partners.digsby.com/bccthis/Install_Bccthis.exe"

!define TITLE_TEXT_BCCTHIS "Send Better Email. Guaranteed."
#!define TITLE_TEXT_BCCTHIS "Add relevant context to emails by sending the right message to the right person"
!define TEXT_AGREE_BCCTHIS "By clicking $\"Accept$\", I agree to the                       and                       and want to install bccthis."
!define TEXT_TERMS_OF_USE_BCCTHIS "Terms of Use"
!define TEXT_PRIVACY_BCCTHIS "Privacy Policy"

!define URL_TERMS_OF_USE_BCCTHIS "http://bccthis.com/legal.php#tos"
!define URL_PRIVACY_BCCTHIS "http://bccthis.com/legal.php#privacy"

!define BUTTONTEXT_NEXT_BCCTHIS "&Accept"
!define BUTTONTEXT_BACK_BCCTHIS "&Decline"

!define BCCTHIS_AFFILIATE_ID "Digsby"

!macro DIGSBY_PAGE_BCCTHIS
    
    Function BccthisPage.InitVars
        StrCpy $BccthisPage.DeclineClicked "False"
        StrCpy $BccthisPage.Install "False"
        StrCpy $BccthisPage.Visited "False"
        StrCpy $BccthisPage.Show 0
        IntOp  $BccthisPage.Results 0 + 0
    FunctionEnd
    
    PageEx custom
        PageCallbacks BccthisPage.OnEnter BccthisPage.OnExit
    PageExEnd
    
    Function BccthisPage.ShouldShow
        StrCpy $1 ""
        
        ${If} $XobniPage.Show == 1
            # 80% chance to not show
            Push "100"
            nsRandom::GetRandom
            Pop $1
            ${If} $1 < 80
                StrCpy $InboxPage.Show 0
                Goto no
            ${EndIf}
        ${EndIf}

        ClearErrors
        ReadRegStr $0 HKCU "Software\Microsoft\Windows NT\CurrentVersion\Windows Messaging Subsystem\Profiles" "DefaultProfile"
        
        ${If} ${Errors}
          ${OrIf} $0 == ""
            Goto no
        ${EndIf}
        
        ClearErrors
        ReadRegDWORD $0 HKLM "Software\Microsoft\NET Framework Setup\NDP\v3.5" "SP"
        
        ${If} ${Errors}
          ${OrIf} $0 < 1
            Goto no
        ${EndIf}

        inetc::get      \
         /TIMEOUT 5000  \
         /SILENT        \
         /USERAGENT "DigsbyInstaller v${SVNREV}" \
         "${COUNTRY_LOOKUP_URL_BCCTHIS}" \
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
          ${OrIf} $1 == "IT"
          ${OrIf} $1 == "DE"
          ${OrIf} $1 == "FR"
          ${OrIf} $1 == "ES"
          ${OrIf} $1 == "MX"
          ${OrIf} $1 == "BR"
            Goto yes
        ${Else}
            Goto no
        ${EndIf}
        
        no:
            StrCpy $BccthisPage.Show 0
            Goto end
        yes:
            StrCpy $BccthisPage.Show 1
            Goto end
        end:
            ClearErrors
    FunctionEnd
    
    Function BccthisPage.DeclineButtonClicked
        StrCpy $BccthisPage.DeclineClicked "True"
        StrCpy $BccthisPage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd
    
    Function BccthisPage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_BCCTHIS}"
    FunctionEnd
    
    Function BccthisPage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_BCCTHIS}"
    FunctionEnd

    Function BccthisPage.OnEnter
        IfSilent 0 +2
            Abort
        
        ${If} $BccthisPage.Show == 0
            StrCpy $BccthisPage.Install "False"
            Abort
        ${EndIf}

        ${If} $BccthisPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $BccthisPage.Visited "True"
        ${EndIf}

        IntOp $BccthisPage.Results $BccthisPage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_BCCTHIS}
        
        File "/oname=$PLUGINSDIR\${IMAGE_NAME_BCCTHIS}" "${IMAGE_PATH_BCCTHIS}"
        
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_BCCTHIS}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            
            ${NSD_CreateBitmap} 0 0 0 0 ""
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\${IMAGE_NAME_BCCTHIS}" $BccthisPage.Image
            
            ${NSD_CreateLink} 112u 87% 42u 6% "${TEXT_TERMS_OF_USE_BCCTHIS}" "${URL_TERMS_OF_USE_BCCTHIS}" 
            Pop $1
            ${NSD_OnClick} $1 BccthisPage.TermsOfUseClicked
            SetCtlColors $1 "000080" transparent
            
            ${NSD_CreateLink} 170u 87% 44u 6% "${TEXT_PRIVACY_BCCTHIS}" "${URL_PRIVACY_BCCTHIS}" 
            Pop $1
            ${NSD_OnClick} $1 BccthisPage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 0 87% 100% 12% "${TEXT_AGREE_BCCTHIS}"
            Pop $1
                        
            GetFunctionAddress $1 BccthisPage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1
            
            # Next button
            GetDlgItem $2 $HWNDPARENT 1
            
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $BccthisPage.NextText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_BCCTHIS}'

            # Back button
            GetDlgItem $2 $HWNDPARENT 3
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $BccthisPage.BackText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_BCCTHIS}'
            
        nsDialogs::Show
    FunctionEnd
    
    Function BccthisPage.OnExit
        ${NSD_FreeImage} $BccthisPage.Image
        
        FindWindow $1 "#32770" "" $HWNDPARENT
        
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$BccthisPage.NextText'
        
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$BccthisPage.BackText'
        
        ${If} $BccthisPage.DeclineClicked == "False"
            StrCpy $BccthisPage.Install "True"
        ${EndIf}
    FunctionEnd
    
    Function BccthisPage.PerformInstall
      IntOp $BccthisPage.Results $BccthisPage.Results | ${FLAG_OFFER_ACCEPT}
      StrCpy $3 '"$PLUGINSDIR\Install_Bccthis.exe" AFFILIATE="${BCCTHIS_AFFILIATE_ID}"'
      inetc::get     \
      /TIMEOUT 5000  \
      /SILENT        \
      /USERAGENT "DigsbyInstaller v${SVNREV}" \
      "${INSTALLER_URL_BCCTHIS}" \
      "$PLUGINSDIR\Install_Bccthis.exe"

      ExecWait $3 $1
      
      ReadRegStr $0 HKCU "Software\Bccthis" "Affiliate"
      ${If} $0 == "${BCCTHIS_AFFILIATE_ID}"
        IntOp $BccthisPage.Results $BccthisPage.Results | ${FLAG_OFFER_SUCCESS}
      ${EndIf}
      
      end:

    FunctionEnd

!macroend

