!define PAGE_NAME_XOBNI "xobni"
!define PAGE_NUM_XOBNI 3
Var XobniPage.Image # needs to be freed
Var XobniPage.Show
Var XobniPage.Install
Var XobniPage.InstallGuid
Var XobniPage.NextText
Var XobniPage.BackText
Var XobniPage.Results
Var XobniPage.Visited 

Var XobniPage.DeclineClicked

!define TITLE_TEXT_XOBNI "Drowning in Email? Save Time with Xobni"
!define IMAGE_NAME_XOBNI "xobni_image.bmp"
!define IMAGE_PATH_XOBNI "${DIGSRES}\${IMAGE_NAME_XOBNI}"

!define INSTALLCHECKER_EXE_XOBNI "${DIGSRES}\XobniDecide_100709.exe"
!define XOBNI_OUTPUT_KEY "Software\Xobni\output"

!define TEXT_AGREE_1_XOBNI "By clicking $\"Accept$\", I agree to the"
!define TEXT_AGREE_2_XOBNI "and"
!define TEXT_AGREE_3_XOBNI "and want to install Xobni."

!define BUTTONTEXT_NEXT_XOBNI "&Accept"
!define BUTTONTEXT_BACK_XOBNI "&Decline"

!define CHECKER_ID_XOBNI "1462750"
!define INSTALLER_URL_XOBNI "http://partners.digsby.com/xobni/XobniMiniSetup.exe"

!define TEXT_TERMS_OF_USE_XOBNI "Terms of Use"
!define TEXT_PRIVACY_XOBNI "Privacy Policy"

!define URL_TERMS_OF_USE_XOBNI "http://www.xobni.com/legal/license"
!define URL_PRIVACY_XOBNI "http://www.xobni.com/legal/privacy"

!macro DIGSBY_PAGE_XOBNI

    Function XobniPage.InitVars
        StrCpy $XobniPage.DeclineClicked "False"
        StrCpy $XobniPage.Install "False"
        StrCpy $XobniPage.Visited "False"
        StrCpy $XobniPage.Show 0
        IntOp  $XobniPage.Results 0 + 0
    FunctionEnd

    PageEx custom

      PageCallbacks XobniPage.OnEnter XobniPage.OnExit

    PageExEnd

    Function XobniPage.ShouldShow
        File "/oname=$PLUGINSDIR\xobni_install_checker.exe" "${INSTALLCHECKER_EXE_XOBNI}"
        ExecWait '"$PLUGINSDIR\xobni_install_checker.exe" -decide -id ${CHECKER_ID_XOBNI}'

        ReadRegStr $1 HKCU ${XOBNI_OUTPUT_KEY} 'decision'
        ${If} $1 == "yes"
            StrCpy $XobniPage.Show 1
            ReadRegStr $2 HKCU ${XOBNI_OUTPUT_KEY} 'offerguid'
            StrCpy $XobniPage.InstallGuid $2
        ${Else}
            StrCpy $XobniPage.Show 0
        ${EndIf}
        DeleteRegValue HKCU ${XOBNI_OUTPUT_KEY} 'decision'
    FunctionEnd

    Function XobniPage.DeclineButtonClicked
        StrCpy $XobniPage.DeclineClicked "True"
        StrCpy $XobniPage.Install "False"
        StrCpy $R9 1
        Call RelGotoPage
        Abort
    FunctionEnd

    Function XobniPage.TermsOfUseClicked
        ${OpenLinkNewWindow} "${URL_TERMS_OF_USE_XOBNI}"
    FunctionEnd

    Function XobniPage.PrivacyPolicyClicked
        ${OpenLinkNewWindow} "${URL_PRIVACY_XOBNI}"
    FunctionEnd

    Function XobniPage.OnEnter
        IfSilent 0 +2
            Abort

        DetailPrint "Initializing..."
        ${If} $XobniPage.Show == 0
            StrCpy $XobniPage.Install "False"
            Abort
        ${EndIf}

        ${If} $XobniPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $XobniPage.Visited "True"
        ${EndIf}
        
        StrCpy $LastSeenPage ${PAGE_NAME_XOBNI}
        IntOp $XobniPage.Results $XobniPage.Results | ${FLAG_OFFER_ASK}

        File "/oname=$PLUGINSDIR\xobni_image.bmp" "${IMAGE_PATH_XOBNI}"

        !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
        !insertmacro MUI_HEADER_TEXT_PAGE "${TITLE_TEXT_XOBNI}" ""

        nsDialogs::Create /NOUNLOAD 1018
            ${NSD_CreateBitmap} 0 0 84% 12% "Image goes here ${IMAGE_PATH_XOBNI}"
            Pop $1
            ${NSD_SetImage} $1 "$PLUGINSDIR\xobni_image.bmp" $XobniPage.Image

            ## non-checkbox GUI
            ## Make sure to change functionality of back button to 'decline offer'
            ${NSD_CreateLabel} 0 90% 112u 6% "${TEXT_AGREE_1_XOBNI}"
            Pop $1

            ${NSD_CreateLink} 112u 90% 44u 6% "${TEXT_TERMS_OF_USE_XOBNI}" "${URL_TERMS_OF_USE_XOBNI}"
            Pop $1
            ${NSD_OnClick} $1 XobniPage.TermsOfUseClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 156u 90% 14u 6% "${TEXT_AGREE_2_XOBNI}"
            Pop $1

            ${NSD_CreateLink} 170u 90% 44u 6% "${TEXT_PRIVACY_XOBNI}" "${URL_PRIVACY_XOBNI}"
            Pop $1
            ${NSD_OnClick} $1 XobniPage.PrivacyPolicyClicked
            SetCtlColors $1 "000080" transparent

            ${NSD_CreateLabel} 215u 90% 95u 6% "${TEXT_AGREE_3_XOBNI}"
            Pop $1

            GetFunctionAddress $1 XobniPage.DeclineButtonClicked
            nsDialogs::OnBack /NOUNLOAD $1

            # Set next/back button text
            # next is control ID 1, back is 3
            # Store old text in XobniPage.NextText / XobniPage.BackText

            # Next button
            GetDlgItem $2 $HWNDPARENT 1

            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $XobniPage.NextText $0

            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_NEXT_XOBNI}'

            # Back button
            GetDlgItem $2 $HWNDPARENT 3
            # get the current text and set for later
            System::Call 'User32::GetWindowText(p r2, t.r0, i 256)'
            StrCpy $XobniPage.BackText $0

            # set new label
            SendMessage $2 ${WM_SETTEXT} 1 'STR:${BUTTONTEXT_BACK_XOBNI}'

        nsDialogs::Show
    FunctionEnd

    Function XobniPage.OnExit
        ${NSD_FreeImage} $XobniPage.Image

        # Revert the labels on the next/back buttons

        FindWindow $1 "#32770" "" $HWNDPARENT
        # Next button
        GetDlgItem $2 $1 1
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$XobniPage.NextText'

        # Back button
        GetDlgItem $2 $1 3
        SendMessage $2 ${WM_SETTEXT} 1 'STR:$XobniPage.BackText'

        ${If} $XobniPage.DeclineClicked == "False"
            #MessageBox MB_OK "Install Xobni -> True"
            StrCpy $XobniPage.Install "True"
        ${EndIf}

    FunctionEnd
    
    Function XobniPage.PerformInstall
      IntOp $XobniPage.Results $XobniPage.Results | ${FLAG_OFFER_ACCEPT}
      #MessageBox MB_OK "Downloading Xobni Installer"
      StrCpy $3 '"$PLUGINSDIR\xobni_installer.exe" /S -offerguid $XobniPage.InstallGuid'
      inetc::get     \
      /TIMEOUT 5000  \
      /SILENT        \
      /USERAGENT "DigsbyInstaller v${SVNREV}" \
      "${INSTALLER_URL_XOBNI}" \
      "$PLUGINSDIR\xobni_installer.exe"
      
      ExecWait $3 $1
      #MessageBox MB_OK "Xobni Installed, return code: $1"
      ${If} $1 == 0
          IntOp $XobniPage.Results $XobniPage.Results | ${FLAG_OFFER_SUCCESS}
      ${EndIf}
      
      end:
    FunctionEnd

!macroend
