!ifndef DIGSBY_FINISH_INCLUDED
!define DIGSBY_FINISH_INCLUDED
!verbose push
!verbose 3

!include MUI2.nsh
!include nsDialogs.nsh
!include LogicLib.nsh

!define PAGE_NAME_PLURA "plura"
!define PAGE_NAME_FINISH "finish"
!define FINISH_PAGE_SPACING 2
!ifndef MUI_WELCOMEFINISHPAGE_BITMAP
  !define MUI_WELCOMEFINISHPAGE_BITMAP "${DIGSRES}\wizard.bmp"
!endif

!macro DIGSBY_FINISH_VARS
    !ifndef DIGSBY_FINISH_VARS
        !define DIGSBY_FINISH_VARS

        Var Digsby.FinishPage
        Var Digsby.Finish.SidebarImage
        Var Digsby.Finish.SidebarImageCtrl
        Var Digsby.Finish.CurTop
        Var Digsby.Finish.CurHeight
        Var Digsby.Finish.CurLeft
        Var Digsby.Finish.CurWidth
        Var Digsby.Finish.Title
        Var Digsby.Finish.Text
        Var Digsby.Finish.LaunchCheck

        Var Digsby.Finish.PluraLink
        Var Digsby.Finish.PluraCheck
        Var Digsby.Finish.SearchCheck
        Var Digsby.Finish.GoogleHomeCheck
        Var Digsby.Finish.AdFreeGroupBox

        Var Digsby.Finish.LaunchCheck.Value
        Var Digsby.Finish.PluraCheck.Value
        Var Digsby.Finish.SearchCheck.Value
        Var Digsby.Finish.GoogleHomeCheck.Value
        
        Var Digsby.Finish.ShowSearchCheck
        Var Digsby.Finish.ShowGoogleHomeCheck
        Var Digsby.Finish.ShowPluraCheck
        
        Var PluraPage.Install
        Var PluraPage.Results
        Var PluraPage.Visited

        # INIT VARS HERE
    !endif
!macroend

!macro DIGSBY_FINISH_VARS_INIT
    !ifndef DIGSBY_FINISH_VARS_INIT
        !define DIGSBY_FINISH_VARS_INIT

        !ifdef DIGSBY_FINISH_LAUNCH_STARTCHECKED
            StrCpy $Digsby.Finish.LaunchCheck.Value "${BST_CHECKED}"
        !else
            StrCpy $Digsby.Finish.LaunchCheck.Value "${BST_UNCHECKED}"
        !endif

        !ifdef DIGSBY_FINISH_PLURA_STARTCHECKED
            StrCpy $Digsby.Finish.PluraCheck.Value "${BST_CHECKED}"
        !else
            StrCpy $Digsby.Finish.PluraCheck.Value "${BST_UNCHECKED}"
        !endif

        !ifdef DIGSBY_FINISH_SEARCH_STARTCHECKED
            StrCpy $Digsby.Finish.SearchCheck.Value "${BST_CHECKED}"
        !else
            StrCpy $Digsby.Finish.SearchCheck.Value "${BST_UNCHECKED}"
        !endif

        !ifdef DIGSBY_FINISH_GOOGLE_STARTCHECKED
            StrCpy $Digsby.Finish.GoogleHomeCheck.Value "${BST_CHECKED}"
        !else
            StrCpy $Digsby.Finish.GoogleHomeCheck.Value "${BST_UNCHECKED}"
        !endif
        
        StrCpy $Digsby.Finish.ShowSearchCheck "False"
        StrCpy $Digsby.Finish.ShowGoogleHomeCheck "False"
        StrCpy $Digsby.Finish.ShowPluraCheck "False"
    !endif
!macroend

!macro DIGSBY_FINISH_INIT
    !insertmacro DIGSBY_FINISH_VARS
!macroend

!macro DIGSBY_FINISH_PAGEDECL
    Function PluraPage.InitVars
        StrCpy $PluraPage.Install "False"
        StrCpy $PluraPage.Visited "False"
        IntOp $PluraPage.Results 0 + 0
    FunctionEnd

    # lots of MUI_DEFAULT for string values here

    !define DIGSBY_FINISH_PRE_FUNCNAME Digsby.FinishPre_${MUI_UNIQUEID}
    !define DIGSBY_FINISH_LEAVE_FUNCNAME Digsby.FinishLeave_${MUI_UNIQUEID}
    PageEx custom

        PageCallbacks "${DIGSBY_FINISH_PRE_FUNCNAME}" "${DIGSBY_FINISH_LEAVE_FUNCNAME}"
        Caption " "
    PageExEnd

    !insertmacro DIGSBY_FUNCTION_FINISHPAGE "${DIGSBY_FINISH_PRE_FUNCNAME}" "${DIGSBY_FINISH_LEAVE_FUNCNAME}"

    # !undef all the things from MUI_DEFAULT section above
!macroend

!macro DIGSBY_PAGE_FINISH
    !verbose push
    !verbose 3

    !insertmacro MUI_PAGE_INIT
    !insertmacro MUI_SET MUI_${MUI_PAGE_UNINSTALLER_PREFIX}FINISHPAGE
    !insertmacro DIGSBY_FINISH_PAGEDECL

    !verbose pop
!macroend

!ifdef _CreateControl
    !undef _CreateControl
!endif
!macro _CreateControl nsdmacro text
    ${NSD_Create${nsdmacro}} "$Digsby.Finish.CurLeftu" "$Digsby.Finish.CurTopu" "$Digsby.Finish.CurWidthu" "$Digsby.Finish.CurHeightu" "${text}"
!macroend

!ifdef CreateControl
    !undef CreateControl
!endif
!define CreateControl "!insertmacro _CreateControl "

!macro DIGSBY_FUNCTION_FINISHPAGE PRE LEAVE
    Function "${PRE}"
        ${incr} $NumPagesVisited 1
        StrCpy $LastSeenPage ${PAGE_NAME_FINISH}
        IntOp $Digsby.Finish.CurTop 0 + 10
        IntOp $Digsby.Finish.CurLeft 0 + 120
        IntOp $Digsby.Finish.CurWidth 0 + 201

        #StrCpy $IsPortable "False"

        !insertmacro MUI_WELCOMEFINISHPAGE_FUNCTION_CUSTOM

        nsDialogs::Create /NOUNLOAD 1044
        Pop $Digsby.FinishPage
        SetCtlColors $Digsby.FinishPage "" "${MUI_BGCOLOR}"

        #${incr} $Digsby.Finish.CurTop ${MUI_FINISHPAGE_V_OFFSET}

        ${NSD_CreateBitmap} 0 0 100% 100% ""
        Pop $Digsby.Finish.SidebarImageCtrl
        ${NSD_SetImage} $Digsby.Finish.SidebarImageCtrl "$PLUGINSDIR\modern-wizard.bmp" $Digsby.Finish.SidebarImage

      LockWindow on
        ### Finish page title
            # First control is large bold text- height of 20
            IntOp $Digsby.Finish.CurHeight 0 + 20

            ${CreateControl} Label $(MUI_TEXT_FINISH_INFO_TITLE) 
            Pop $Digsby.Finish.Title

            # Set bold and background color
            CreateFont $2 "$(^Font)" "12" "700"
            SendMessage $Digsby.Finish.Title ${WM_SETFONT} $2 0
            SetCtlColors $Digsby.Finish.Title "" "${MUI_BGCOLOR}"
        ###

        ${incr} $Digsby.Finish.CurTop $Digsby.Finish.CurHeight
        ${incr} $Digsby.Finish.CurTop ${FINISH_PAGE_SPACING}

        ### Next, three lines of descriptive text
            IntOp $Digsby.Finish.CurHeight 0 + 30

            ${CreateControl} Label "$(^NameDA) has been installed on your computer."
            Pop $Digsby.Finish.Text

            # Set background color
            SetCtlColors $Digsby.Finish.Text "" "${MUI_BGCOLOR}"
        ###

        ${If} $IsPortable == "False"

            ${incr} $Digsby.Finish.CurTop $Digsby.Finish.CurHeight
            ${incr} $Digsby.Finish.CurTop ${FINISH_PAGE_SPACING}

            ### "Launch Digsby" checkbox
                IntOp $Digsby.Finish.CurHeight 0 + 10
                IntOp $Digsby.Finish.CurTop 0 + 90

                ${CreateControl} CheckBox "${DIGSBY_FINISH_LAUNCHCHECK_TEXT}"
                Pop $Digsby.Finish.LaunchCheck

                # Set background color
                SetCtlColors $Digsby.Finish.LaunchCheck "" "${MUI_BGCOLOR}"
            ###
        ${EndIf}

        # Figure out which checkboxes we're suppose to show
        
        ${If} $IsPortable == "True"
            StrCpy $Digsby.Finish.ShowSearchCheck "False"
            StrCpy $Digsby.Finish.ShowGoogleHomeCheck "False"
        ${EndIf}

        !ifdef PAGE_NAME_XOBNI
            ${If} $XobniPage.Install == "True"
                StrCpy $Digsby.Finish.ShowSearchCheck "False"
            ${EndIf}
        !endif

        !ifdef PAGE_NAME_BING
            ${If} $BingPage.Install == "True"
                StrCpy $Digsby.Finish.ShowSearchCheck "False"
                StrCpy $Digsby.Finish.ShowGoogleHomeCheck "False"
            ${EndIf}
        !endif
        
        !ifdef PAGE_NAME_BABYLON
            ${If} $BabylonPage.Install == "True"
                StrCpy $Digsby.Finish.ShowSearchCheck "False"
                StrCpy $Digsby.Finish.ShowGoogleHomeCheck "False"
            ${EndIf}
        !endif

        !ifdef PAGE_NAME_UNIBLUE
            ${If} $UnibluePage.Install == "True"
                # Not a search offer, doesn't change anything
            ${EndIf}
        !endif

        !ifdef PAGE_NAME_ARO
            ${If} $AroPage.Install == "True"
                # Not a search offer, doesn't change anything
            ${EndIf}
        !endif

        !ifdef PAGE_NAME_ASK
            ${If} $AskPage.Install == "True"
                StrCpy $Digsby.Finish.ShowSearchCheck "False"
            ${EndIf}
        !endif
        
        !ifdef PAGE_NAME_CRAWLER
            ${If} $CrawlerPage.Install == "True"
                StrCpy $Digsby.Finish.ShowSearchCheck "False"
            ${EndIf}
        !endif

        !ifdef PAGE_NAME_INBOX
            ${If} $InboxPage.Install == "True"
                StrCpy $Digsby.Finish.ShowSearchCheck "False"
            ${EndIf}
        !endif
        
        !ifdef PAGE_NAME_OPENCANDY
            ${If} $OpencandyPage.Visited == "True"
                StrCpy $Digsby.Finish.ShowSearchCheck "False"
                StrCpy $Digsby.Finish.ShowGoogleHomeCheck "False"
                StrCpy $Digsby.Finish.ShowPluraCheck "False"
            ${EndIf}
        !endif
        
        ${If} $Digsby.Finish.ShowSearchCheck == "False"
            StrCpy $Digsby.Finish.SearchCheck.Value ${BST_UNCHECKED}
        ${EndIf}
        ${If} $Digsby.Finish.ShowPluraCheck == "False"
            StrCpy $Digsby.Finish.PluraCheck.Value ${BST_UNCHECKED}
        ${EndIf}
        ${If} $Digsby.Finish.ShowGoogleHomeCheck == "False"
            StrCpy $Digsby.Finish.GoogleHomeCheck.Value ${BST_UNCHECKED}
        ${EndIf}


        ##
        # Now we start building up from the bottom.
        ##

        IntOp $Digsby.Finish.CurHeight 0 + 8
        IntOp $Digsby.Finish.CurTop 0 + 180
        
        ${If} $Digsby.Finish.ShowPluraCheck == "True"
            ### Link
            # move right 10ish pixels
            ${incr} $Digsby.Finish.CurLeft 181
            ${decr} $Digsby.Finish.CurWidth 196
            ${CreateControl} Link "${DIGSBY_FINISH_PLURALINK_TEXT}"
            Pop $Digsby.Finish.PluraLink

            SetCtlColors $Digsby.Finish.PluraLink "000080" "${MUI_BGCOLOR}"

            ${NSD_OnClick} $Digsby.Finish.PluraLink ${DIGSBY_FINISH_PLURALINK_ONCLICK}

            # move back to the left
            ${decr} $Digsby.Finish.CurLeft 181
            ${incr} $Digsby.Finish.CurWidth 196

        ${EndIf}
        
        IntOp $Digsby.Finish.CurHeight 0 + 10
        
        ${If} $Digsby.Finish.ShowPluraCheck == "True"

            ### Checkbox
            
            #${decr} $Digsby.Finish.CurTop $Digsby.Finish.CurHeight
            #${decr} $Digsby.Finish.CurTop ${FINISH_PAGE_SPACING}

            ### Enable Plura checkbox
            ${CreateControl} CheckBox "${DIGSBY_FINISH_PLURACHECK_TEXT}"
            Pop $Digsby.Finish.PluraCheck

            # Set background color
            SetCtlColors $Digsby.Finish.PluraCheck "" "${MUI_BGCOLOR}"
            IntOp $PluraPage.Results $PluraPage.Results | ${FLAG_OFFER_ASK}
            StrCpy $PluraPage.Visited "True"
            ###
        ${EndIf}
        

        ${If} $Digsby.Finish.ShowSearchCheck == "True"
              ${decr} $Digsby.Finish.CurTop $Digsby.Finish.CurHeight
              ${decr} $Digsby.Finish.CurTop ${FINISH_PAGE_SPACING}

              ###
                  ${CreateControl} CheckBox "${DIGSBY_FINISH_SEARCHCHECK_TEXT}"
                  Pop $Digsby.Finish.SearchCheck

                  SetCtlColors $Digsby.Finish.SearchCheck "" "${MUI_BGCOLOR}"
              ###
        ${EndIf}
        ${If} $Digsby.Finish.ShowGoogleHomeCheck == "True"
            ${decr} $Digsby.Finish.CurTop $Digsby.Finish.CurHeight
            ${decr} $Digsby.Finish.CurTop ${FINISH_PAGE_SPACING}

            ###
                ${CreateControl} CheckBox "${DIGSBY_FINISH_GOOGLEHOMECHECK_TEXT}"
                Pop $Digsby.Finish.GoogleHomeCheck

                SetCtlColors $Digsby.Finish.GoogleHomeCheck "" "${MUI_BGCOLOR}"
            ###
        ${EndIf}

        ${decr} $Digsby.Finish.CurTop $Digsby.Finish.CurHeight
        #${decr} $Digsby.Finish.CurTop ${FINISH_PAGE_SPACING}
        #${decr} $Digsby.Finish.CurTop ${FINISH_PAGE_SPACING}
        ${decr} $Digsby.Finish.CurLeft 4
        ${incr} $Digsby.Finish.CurWidth 8
        
        IntOp $Digsby.Finish.CurHeight 0 + 10
        ${If} $Digsby.Finish.ShowPluraCheck == "True"
            IntOp $Digsby.Finish.CurHeight $Digsby.Finish.CurHeight + 12
        ${EndIf}
        
        ${If} $Digsby.Finish.ShowSearchCheck == "True"
            IntOp $Digsby.Finish.CurHeight $Digsby.Finish.CurHeight + 12
        ${EndIf}
        
        ${If} $Digsby.Finish.ShowGoogleHomeCheck == "True"
            IntOp $Digsby.Finish.CurHeight $Digsby.Finish.CurHeight + 12
        ${EndIf}

        ${If} $Digsby.Finish.ShowPluraCheck == "True"
          ${OrIf} $Digsby.Finish.ShowSearchCheck == "True"
          ${OrIf} $Digsby.Finish.ShowGoogleHomeCheck == "True"
            
            ${CreateControl} GroupBox "Help Support Digsby Development"
            Pop $Digsby.Finish.AdFreeGroupBox
            SetCtlColors $Digsby.Finish.AdFreeGroupBox "" "${MUI_BGCOLOR}"
            CreateFont $2 "$(^Font)" "7" "700"
            SendMessage $Digsby.Finish.AdFreeGroupBox ${WM_SETFONT} $2 0
        ${EndIf}

      LockWindow off
      SendMessage $Digsby.Finish.LaunchCheck ${BM_SETCHECK} "$Digsby.Finish.LaunchCheck.Value" 0
      SendMessage $Digsby.Finish.PluraCheck ${BM_SETCHECK} "$Digsby.Finish.PluraCheck.Value" 0
      SendMessage $Digsby.Finish.SearchCheck ${BM_SETCHECK} "$Digsby.Finish.SearchCheck.Value" 0
      SendMessage $Digsby.Finish.GoogleHomeCheck ${BM_SETCHECK} "$Digsby.Finish.GoogleHomeCheck.Value" 0

      GetDlgItem $1 $HWNDPARENT 1028 # 1028 is the "branding text" control
      ShowWindow $1 ${SW_HIDE}
      GetDlgItem $1 $HWNDPARENT 1256 # 1256 is ... something else that looks like the branding text?
      ShowWindow $1 ${SW_HIDE}
      GetDlgItem $1 $HWNDPARENT 1035 # 1035 is the horizontal line thingy
      ShowWindow $1 ${SW_HIDE}

      !ifdef DIGSBY_FINISH_CANCEL_DISABLED
        GetDlgItem $1 $HWNDPARENT 3 # cancel button
        EnableWindow $1 0
      !endif

      !ifdef DIGSBY_FINISH_BACK_DISABLED
        GetDlgItem $1 $HWNDPARENT 2 # Back button
        EnableWindow $1 0
      !endif

      !ifdef DIGSBY_FINISH_NEXT_TEXT
        GetDlgItem $1 $HWNDPARENT 1 # next button
        SendMessage $1 ${WM_SETTEXT} 0 "STR:${DIGSBY_FINISH_NEXT_TEXT}"
      !endif

      !insertmacro MUI_PAGE_FUNCTION_CUSTOM PRE
      !insertmacro MUI_PAGE_FUNCTION_CUSTOM SHOW

      nsDialogs::Show
      GetDlgItem $1 $HWNDPARENT 1028 # 1028 is the "branding text" control
      ShowWindow $1 ${SW_SHOW}
      GetDlgItem $1 $HWNDPARENT 1256 # 1256 is ... something else that looks like the branding text?
      ShowWindow $1 ${SW_SHOW}
      GetDlgItem $1 $HWNDPARENT 1035 # 1035 is the horizontal line thingy
      ShowWindow $1 ${SW_SHOW}

      ${NSD_FreeImage} $Digsby.Finish.SidebarImage

    FunctionEnd

    Function "${LEAVE}"
        SetShellVarContext current
        
        ${If} $IsPortable == "True"
            # Make sure these are disabled for portable mode.
            StrCpy $Digsby.Finish.LaunchCheck.Value ${BST_UNCHECKED}
            StrCpy $Digsby.Finish.SearchCheck.Value ${BST_UNCHECKED}
            StrCpy $Digsby.Finish.GoogleHomeCheck.Value ${BST_UNCHECKED}
        ${Else}
            ${NSD_GetState} $Digsby.Finish.LaunchCheck $Digsby.Finish.LaunchCheck.Value
            ${NSD_GetState} $Digsby.Finish.GoogleHomeCheck $Digsby.Finish.GoogleHomeCheck.Value
            ${NSD_GetState} $Digsby.Finish.SearchCheck $Digsby.Finish.SearchCheck.Value
            ${NSD_GetState} $Digsby.Finish.PluraCheck $Digsby.Finish.PluraCheck.Value
        ${EndIf}

        ## Call functions for finish page check boxes
        ${If} $Digsby.Finish.LaunchCheck.Value == ${BST_CHECKED}
          Call ${DIGSBY_FINISH_LAUNCHCHECK_FUNC}
        ${EndIf}

        ${If} $Digsby.Finish.PluraCheck.Value == ${BST_CHECKED}
          StrCpy $PluraPage.Install "True"
          IntOp $PluraPage.Results $PluraPage.Results | ${FLAG_OFFER_ACCEPT}
          IntOp $PluraPage.Results $PluraPage.Results | ${FLAG_OFFER_SUCCESS}
          Call ${DIGSBY_FINISH_PLURACHECK_FUNC}
        ${EndIf}

        ${If} $Digsby.Finish.SearchCheck.Value == ${BST_CHECKED}
          Call ${DIGSBY_FINISH_SEARCHCHECK_FUNC} 
        ${EndIf}

        ${If} $Digsby.Finish.GoogleHomeCheck.Value == ${BST_CHECKED}
          Call ${DIGSBY_FINISH_GOOGLEHOMECHECK_FUNC}
        ${EndIf}
        ###

        !insertmacro MUI_PAGE_FUNCTION_CUSTOM LEAVE
    FunctionEnd

!macroend

!endif

