!ifndef DIGSBY_WELCOME_INCLUDED
!define DIGSBY_WELCOME_INCLDUED

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"

!define PAGE_NAME_WELCOME "welcome"
!define WELCOME_PAGE_SPACING 2
!define DIGSBY_WELCOME_TITLE_TEXT "Welcome to the ${PRODUCT_NAME} Setup Wizard"

!define DIGSBY_WELCOME_INTRO_TEXT "This wizard will guide you through the installation of ${PRODUCT_NAME}. By clicking Next, I agree to the                            and consent to install ${PRODUCT_NAME}."
!define DIGSBY_WELCOME_INTRO_LINK_TEXT "Terms of Service"
!define DIGSBY_WELCOME_INTRO_LINK_URL "http://www.digsby.com/tos.php"
# Causes stuff
#!define PAGE_NAME_CAUSES "causes"
!define DIGSBY_CAUSES_BOX_TEXT "Digsby Donates"
!define DIGSBY_CAUSES_CHECK_TEXT "Enable Digsby Donates"
!define DIGSBY_CAUSES_LABEL_TEXT "A free browser plugin that helps support Digsby development and allows us to make a donation at no cost to you whenever you shop at one of over 1,800 participating merchants. [   ]"
#!define DIGSBY_CAUSES_STARTCHECKED
!define DIGSBY_CAUSES_LINK_TEXT "?"
!define DIGSBY_CAUSES_LINK_URL "http://wiki.digsby.com/doku.php?id=donate"

!ifndef MUI_WELCOMEFINISHPAGE_BITMAP
    !define MUI_WELCOMEFINISHPAGE_BITMAP "${DIGSRES}\wizard.bmp"
!endif

!macro DIGSBY_WELCOME_VARS
    !ifndef DIGSBY_WELCOME_VARS
        !define DIGSBY_WELCOME_VARS
        Var Digsby.Welcome
        Var Digsby.Welcome.SidebarImage
        Var Digsby.Welcome.SidebarImageCtrl
        
        Var Digsby.Welcome.CurTop
        Var Digsby.Welcome.CurHeight
        Var Digsby.Welcome.CurLeft
        Var Digsby.Welcome.CurWidth
        
        Var Digsby.Welcome.CausesCheck
        Var Digsby.Welcome.CausesCheck.Value
        
        Var CausesPage.Install
        Var CausesPage.Results
        Var CausesPage.Visited
        Var CausesPage.Show # Controls if the causes check should show
    !endif
!macroend

!macro DIGSBY_WELCOME_VARS_INIT
    !ifndef DIGSBY_WELCOME_VARS_INIT
        !define DIGSBY_WELCOME_VARS_INIT
        
        !ifdef DIGSBY_CAUSES_STARTCHECKED
            StrCpy $Digsby.Welcome.CausesCheck.Value "${BST_CHECKED}"
        !else
            StrCpy $Digsby.Welcome.CausesCheck.Value "${BST_UNCHECKED}"
        !endif
    !endif
!macroend

!macro DIGSBY_WELCOME_INIT
    !insertmacro DIGSBY_WELCOME_VARS
!macroend

!macro DIGSBY_WELCOME_PAGEDECL
    !define DIGSBY_WELCOME_PRE_FUNCNAME Digsby.WelcomePre_${MUI_UNIQUEID}
    !define DIGSBY_WELCOME_LEAVE_FUNCNAME Digsby.WelcomeLeave_${MUI_UNIQUEID}

    !insertmacro DIGSBY_FUNCTION_WELCOMEPAGE "${DIGSBY_WELCOME_PRE_FUNCNAME}" "${DIGSBY_WELCOME_LEAVE_FUNCNAME}"
    
    PageEx custom 
        #PageCallbacks OnEnterWelcomePage OnExitWelcomePage
        PageCallbacks "${DIGSBY_WELCOME_PRE_FUNCNAME}" "${DIGSBY_WELCOME_LEAVE_FUNCNAME}"
    PageExEnd
    
!macroend

!macro DIGSBY_PAGE_WELCOME
    !verbose push
    !verbose 3
    
    !insertmacro MUI_PAGE_INIT
    !insertmacro MUI_SET MUI_${MUI_PAGE_UNINSTALLER_PREFIX}WELCOMEPAGE
    !insertmacro DIGSBY_WELCOME_PAGEDECL
    
    !verbose pop
!macroend


!macro _CreateControl_WelcomePage nsdmacro text
    ${NSD_Create${nsdmacro}} "$Digsby.Welcome.CurLeftu" "$Digsby.Welcome.CurTopu" "$Digsby.Welcome.CurWidthu" "$Digsby.Welcome.CurHeightu" "${text}"
!macroend

!define CreateControlW "!insertmacro _CreateControl_WelcomePage "

!macro DIGSBY_FUNCTION_WELCOMEPAGE PRE LEAVE
    
    Function CausesPage.InitVars
        StrCpy $CausesPage.Show "True"
        StrCpy $CausesPage.Install "False"
        StrCpy $CausesPage.Visited "False"
        IntOp  $CausesPage.Results 0 + 0
    FunctionEnd 
    
    Function OpenWelcomeIntroLink
        ${OpenLinkNewWindow} "${DIGSBY_WELCOME_INTRO_LINK_URL}"
    FunctionEnd
    
    Function CausesPage.LearnMoreClicked
        ${OpenLinkNewWindow} "${DIGSBY_CAUSES_LINK_URL}"
    FunctionEnd
    
    Function "${PRE}"
    
        !ifdef PAGE_NAME_CAUSES
            ${If} $CausesPage.Visited != "True"
                ${incr} $NumPagesVisited 1
                StrCpy $CausesPage.Visited "True"
            ${EndIf}
        !endif
        StrCpy $LastSeenPage ${PAGE_NAME_WELCOME}
        IntOp $Digsby.Welcome.CurTop 0 + 10
        IntOp $Digsby.Welcome.CurLeft 0 + 120
        IntOp $Digsby.Welcome.CurWidth 0 + 201
        
        !insertmacro MUI_WELCOMEFINISHPAGE_FUNCTION_CUSTOM
        
        # this file is used by welcome and finish page
        File "/oname=$PLUGINSDIR\modern-wizard.bmp" "${MUI_WELCOMEFINISHPAGE_BITMAP}"
        StrCpy $CausesPage.Visited "True"

        nsDialogs::Create /NOUNLOAD 1044
            Pop $Digsby.Welcome
            SetCtlColors $Digsby.Welcome "" "${MUI_BGCOLOR}"
            
            ${NSD_CreateBitmap} 0 0 100% 100% ""
            Pop $Digsby.Welcome.SidebarImageCtrl
            ${NSD_SetImage} $Digsby.Welcome.SidebarImageCtrl "$PLUGINSDIR\modern-wizard.bmp" $Digsby.Welcome.SidebarImage

        LockWindow on
            ### Title
                IntOp $Digsby.Welcome.CurHeight 0 + 20
                ${CreateControlW} Label "${DIGSBY_WELCOME_TITLE_TEXT}"
                Pop $1
                CreateFont $2 "$(^Font)" "12" "700"
                SendMessage $1 ${WM_SETFONT} $2 0
                SetCtlColors $1 "" "${MUI_BGCOLOR}"
            ###
            
            ${incr} $Digsby.Welcome.CurTop $Digsby.Welcome.CurHeight
            ${incr} $Digsby.Welcome.CurTop ${WELCOME_PAGE_SPACING}
            
            ### Link, must be absolutely positioned. 	 	 
            ### also have to place it first, for z-order reasons. 	 	 
                ${NSD_CreateLink} 210u 40u 53u 10u "${DIGSBY_WELCOME_INTRO_LINK_TEXT}"
                Pop $1 	 	 

                SetCtlColors $1 "000080" "${MUI_BGCOLOR}" 	 	 
                ${NSD_OnClick} $1 "OpenWelcomeIntroLink" 	 	 
            ###

            ### Intro
                IntOp $Digsby.Welcome.CurHeight 0 + 40
                ${CreateControlW} Label "${DIGSBY_WELCOME_INTRO_TEXT}"
                Pop $1
                SetCtlColors $1 "" "${MUI_BGCOLOR}"
            ###
            
            !ifdef PAGE_NAME_CAUSES
            ### Causes "Learn more" link
                ${NSD_CreateLink} 311u 178u 3u 10u "${DIGSBY_CAUSES_LINK_TEXT}"
                Pop $1
                
                SetCtlColors $1 "000080" "${MUI_BGCOLOR}"
                ${NSD_OnClick} $1 "CausesPage.LearnMoreClicked"
            ###
            
            ### Causes check box
                IntOp $Digsby.Welcome.CurHeight 0 + 10
                #IntOp $Digsby.Welcome.CurWidth $Digsby.Welcome.CurWidth - 5
                IntOp $Digsby.Welcome.CurTop 152 + 0
                IntOp $Digsby.Welcome.CurLeft 116 + 0

                ${CreateControlW} CheckBox "${DIGSBY_CAUSES_CHECK_TEXT}"
                Pop $Digsby.Welcome.CausesCheck
                ${NSD_SetState} $Digsby.Welcome.CausesCheck $Digsby.Welcome.CausesCheck.Value

                CreateFont $2 "$(^Font)" "7" "700"
                SendMessage $Digsby.Welcome.CausesCheck ${WM_SETFONT} $2 0
                SetCtlColors $Digsby.Welcome.CausesCheck "" "${MUI_BGCOLOR}"

                ${incr} $Digsby.Welcome.CurTop $Digsby.Welcome.CurHeight
                #${incr} $Digsby.Welcome.CurTop ${WELCOME_PAGE_SPACING}

            ###
            ### Causes text box
                IntOp $Digsby.Welcome.CurHeight 0 + 30
                ${incr} $Digsby.Welcome.CurLeft 12
                ${incr} $Digsby.Welcome.CurWidth 8
                
                ${CreateControlW} Label "${DIGSBY_CAUSES_LABEL_TEXT}"
                Pop $1
                SetCtlColors $1 "" "${MUI_BGCOLOR}"

                # not setting an OnClick handler because this is the only checkbox.
                # state can be grabbed on page exit
            ### End causes
            !endif

          GetDlgItem $1 $HWNDPARENT 1028 # 1028 is the "branding text" control
          ShowWindow $1 ${SW_HIDE}
          GetDlgItem $1 $HWNDPARENT 1256 # 1256 is ... something else that looks like the branding text?
          ShowWindow $1 ${SW_HIDE}
          GetDlgItem $1 $HWNDPARENT 1035 # 1035 is the horizontal line thingy
          ShowWindow $1 ${SW_HIDE}
        LockWindow off

        IntOp $CausesPage.Results $CausesPage.Results | ${FLAG_OFFER_ASK}
        nsDialogs::Show
        GetDlgItem $1 $HWNDPARENT 1028 # 1028 is the "branding text" control
        ShowWindow $1 ${SW_SHOW}
        GetDlgItem $1 $HWNDPARENT 1256 # 1256 is ... something else that looks like the branding text?
        ShowWindow $1 ${SW_SHOW}
        GetDlgItem $1 $HWNDPARENT 1035 # 1035 is the horizontal line thingy
        ShowWindow $1 ${SW_SHOW}
        
    FunctionEnd
    
    Function "${LEAVE}"
      
      !ifdef PAGE_NAME_XOBNI
        Call XobniPage.ShouldShow
        ${If} $XobniPage.Show == 1
            #Goto foundone
        ${EndIf}
      !endif
      
      !ifdef PAGE_NAME_BCCTHIS
        Call BccthisPage.ShouldShow
        ${If} $BccthisPage.Show == 1
            ${If} $XobniPage.Show == 1
                Goto foundone
            ${EndIf}
        ${EndIf}
      !endif
      
      !ifdef PAGE_NAME_OPENCANDY
        !ifdef PAGE_NAME_XOBNI
        ${If} $XobniPage.Show == 0
        !endif
            Call OpencandyPage.ShouldShow
            ${If} $OpencandyPage.Show == 1
                #Goto foundone
            ${EndIf}
        !ifdef PAGE_NAME_XOBNI
        ${EndIf}
        !endif
      !endif

      !ifdef PAGE_NAME_UNIBLUE
        !ifdef PAGE_NAME_XOBNI
        ${If} $XobniPage.Show == 0
        !endif
            Call UnibluePage.ShouldShow
            ${If} $UnibluePage.Show == 1
                #Goto foundone
            ${EndIf}
        !ifdef PAGE_NAME_XOBNI
        ${EndIf}
        !endif
      !endif
      
      !ifdef PAGE_NAME_ARO
        !ifdef PAGE_NAME_XOBNI
        ${If} $XobniPage.Show == 0
        !endif
            Call AroPage.ShouldShow
            ${If} $AroPage.Show == 1
                #Goto foundone
            ${EndIf}
        !ifdef PAGE_NAME_XOBNI
        ${EndIf}
        !endif
      !endif
      
      !ifdef PAGE_NAME_BING
        Call BingPage.ShouldShow
        ${If} $BingPage.Show == 1
            Goto foundone
        ${EndIf}
      !endif

      !ifdef PAGE_NAME_CRAWLER
        Call CrawlerPage.ShouldShow
        ${If} $CrawlerPage.Show == 1
            Goto foundone
        ${EndIf}
      !endif

      !ifdef PAGE_NAME_INBOX
        Call InboxPage.ShouldShow
        ${If} $InboxPage.Show == 1
            Goto foundone
        ${EndIf}
      !endif
      
      !ifdef PAGE_NAME_BABYLON
        Call BabylonPage.ShouldShow
        ${If} $BabylonPage.Show == 1
            Goto foundone
        ${EndIf}
      !endif

      !ifdef PAGE_NAME_ASK
        Call AskPage.ShouldShow
        ${If} $AskPage.Show == 1
            Goto foundone
        ${EndIf}
      !endif

      foundone:

      ${NSD_GetState} $Digsby.Welcome.CausesCheck $Digsby.Welcome.CausesCheck.Value
      ${If} $Digsby.Welcome.CausesCheck.Value == ${BST_CHECKED}
        StrCpy $CausesPage.Install "True"
      ${Else}
        StrCpy $CausesPage.Install "False"
      ${EndIf}

    FunctionEnd
    
    Function CausesPage.PerformInstall
        IntOp $CausesPage.Results $CausesPage.Results | ${FLAG_OFFER_ACCEPT}
        File "/oname=$PLUGINSDIR\Digsby_Donates.exe" "${DIGSRES}\Digsby_Donates.exe"
        ExecWait "$PLUGINSDIR\Digsby_Donates.exe /S" $1
        ${If} $1 == 0
            IntOp $CausesPage.Results $CausesPage.Results | ${FLAG_OFFER_SUCCESS}
        ${EndIf}
    FunctionEnd
!macroend

!endif