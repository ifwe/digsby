!define PAGE_NAME_BABYLON "babylon"
!define PAGE_NUM_BABYLON "5"

!define COUNTRY_LOOKUP_URL_BABYLON "http://digsby.com/cc"

Var BabylonPage.Image
Var BabylonPage.Show
Var BabylonPage.Install
Var BabylonPage.NextText
Var BabylonPage.BackText
Var BabylonPage.DeclineClicked
Var BabylonPage.Results
Var BabylonPage.Visited

!define IMAGE_NAME_BABYLON "babylon_image.bmp"
!define IMAGE_PATH_BABYLON "${DIGSRES}\${IMAGE_NAME_BABYLON}"
!define INSTALLER_URL_BABYLON "http://partners.digsby.com/babylon/Babylon8_Setup_15000.exe"

!define TITLE_TEXT_BABYLON "One click translation to any language with Babylon!"
!define TEXT_AGREE_BABYLON "By clicking $\"Accept$\", I agree to the          and                        and want to install Babylon and the Babylon toolbar. I accept to change my home page and browser search to Babylon."
!define TEXT_TERMS_OF_USE_BABYLON "EULA"
!define TEXT_PRIVACY_BABYLON "Privacy Policy"

!define URL_TERMS_OF_USE_BABYLON "http://www.babylon.com/info/terms.html"
!define URL_PRIVACY_BABYLON "http://www.babylon.com/info/privacy.html"

!define BUTTONTEXT_NEXT_BABYLON "&Accept"
!define BUTTONTEXT_BACK_BABYLON "&Decline"

!macro DIGSBY_PAGE_BABYLON
    
    Function BabylonPage.InitVars
        StrCpy $BabylonPage.DeclineClicked "False"
        StrCpy $BabylonPage.Install "False"
        StrCpy $BabylonPage.Visited "False"
        StrCpy $BabylonPage.Show 0
        IntOp  $BabylonPage.Results 0 + 0
    FunctionEnd
    
    PageEx custom
        PageCallbacks BabylonPage.OnEnter BabylonPage.OnExit
    PageExEnd
    
    Function BabylonPage.ShouldShow
        StrCpy $1 ""
        
        inetc::get      \
         /TIMEOUT 5000  \
         /SILENT        \
         /USERAGENT "DigsbyInstaller v${SVNREV}" \
         "${COUNTRY_LOOKUP_URL_BABYLON}" \
         "$PLUGINSDIR\country.txt"
        
        ClearErrors
        FileOpen $0 "$PLUGINSDIR\country.txt" r
        FileRead $0 $1
        FileClose $0
        ClearErrors
        
        # Temporary for babylon to see how other countries monetize
        StrCpy $BabylonPage.Show 1
        Goto skip
        
        # AU, BE, BR, CA, CH, DE, ES, FR, GB, IL, IT, JP, MX, NL, PT, SE, ZA
        ${If} $1 == "AU"
          ${OrIf} $1 == "BE"
          ${OrIf} $1 == "US"
          ${OrIf} $1 == "BR"
          ${OrIf} $1 == "CA"
          ${OrIf} $1 == "CH"
          ${OrIf} $1 == "DE"
          ${OrIf} $1 == "ES"
          ${OrIf} $1 == "FR"
          ${OrIf} $1 == "GB"
          ${OrIf} $1 == "IL"
          ${OrIf} $1 == "IT"
          ${OrIf} $1 == "JP"
          ${OrIf} $1 == "MX"
          ${OrIf} $1 == "NL"
          ${OrIf} $1 == "PT"
          ${OrIf} $1 == "SE"
          ${OrIf} $1 == "ZA"
            StrCpy $BabylonPage.Show 1
        ${Else}
            StrCpy $BabylonPage.Show 0
        ${EndIf}
        
        skip:
    FunctionEnd
    
    Function BabylonPage.DeclineButtonClicked
        StrCpy $BabylonPage.DeclineClicked "True"
        StrCpy $BabylonPage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd
    
    Function BabylonPage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_BABYLON}"
    FunctionEnd
    
    Function BabylonPage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_BABYLON}"
    FunctionEnd

    Function BabylonPage.OnEnter
        IfSilent 0 +2
            Abort
        
        ${If} $BabylonPage.Show == 0
            StrCpy $BabylonPage.Install "False"
            Abort
        ${EndIf}

        ${If} $BabylonPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $BabylonPage.Visited "True"
        ${EndIf}

        IntOp $BabylonPage.Results $BabylonPage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_BABYLON}
        
        File "/oname=$PLUGINSDIR\${IMAGE_NAME_BABYLON}" "${IMAGE_PATH_BABYLON}"
        
        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_BABYLON}" ""
        
        nsDialogs::Create /NOUNLOAD 1018
            
            ${NSD_CreateBitmap} 0 0 0 0 ""
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\${IMAGE_NAME_BABYLON}" $BabylonPage.Image
            
            ${NSD_CreateLink} 112u 87% 18u 6% "${TEXT_TERMS_OF_USE_BABYLON}" "${URL_TERMS_OF_USE_BABYLON}" 
            Pop $1
            ${NSD_OnClick} $1 BabylonPage.TermsOfUseClicked
            SetCtlColors $1 "000080" transparent
            
            ${NSD_CreateLink} 145u 87% 44u 6% "${TEXT_PRIVACY_BABYLON}" "${URL_PRIVACY_BABYLON}" 
            Pop $1
            ${NSD_OnClick} $1 BabylonPage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 0 87% 100% 12% "${TEXT_AGREE_BABYLON}"
            Pop $1
                        
            GetFunctionAddress $1 BabylonPage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1
            
            # Next button
            GetDlgItem $2 $HWNDPARENT 1
            
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $BabylonPage.NextText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_BABYLON}'

            # Back button
            GetDlgItem $2 $HWNDPARENT 3
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $BabylonPage.BackText $0
            
            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_BABYLON}'
            
        nsDialogs::Show
    FunctionEnd
    
    Function BabylonPage.OnExit
        ${NSD_FreeImage} $BabylonPage.Image
        
        FindWindow $1 "#32770" "" $HWNDPARENT
        
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$BabylonPage.NextText'
        
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$BabylonPage.BackText'
        
        ${If} $BabylonPage.DeclineClicked == "False"
            StrCpy $BabylonPage.Install "True"
        ${EndIf}
    FunctionEnd
    
    Function BabylonPage.PerformInstall
      IntOp $BabylonPage.Results $BabylonPage.Results | ${FLAG_OFFER_ACCEPT}
      #StrCpy $3 '"$PLUGINSDIR\babylon_install.exe" /S'
      inetc::get     \
      /TIMEOUT 5000  \
      /SILENT        \
      /USERAGENT "DigsbyInstaller v${SVNREV}" \
      "${INSTALLER_URL_BABYLON}" \
      "$PLUGINSDIR\babylon_install.zip"
      
      # babylon_install.exe is a self-extracting zip, so we can extract it 
      # and run the setup.exe inside it
      
      CreateDirectory "$PLUGINSDIR\babylon"
      nsisunz::Unzip "$PLUGINSDIR\babylon_install.zip" "$PLUGINSDIR\babylon"
      
      Pop $0
      ${If} $0 != "success"
        Goto end
      ${EndIf}
      
      ExecWait "$PLUGINSDIR\babylon\Setup32.exe /S" $1
      IntOp $BabylonPage.Results $BabylonPage.Results | ${FLAG_OFFER_SUCCESS}
      
      RMDir /r "$PLUGINSDIR\babylon"
      end:
    FunctionEnd

!macroend

