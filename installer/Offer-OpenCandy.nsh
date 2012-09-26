!ifdef USE_OPENCANDY
!define PAGE_NAME_OPENCANDY "opencandy"
Var OpencandyPage.Show
Var OpencandyPage.Install
Var OpencandyPage.Results
Var OpencandyPage.Visited
Var OpencandyPage.UserAborted

!define OC_STR_MY_PRODUCT_NAME "${PRODUCT_NAME}"
!define OC_STR_KEY "3d3573561f09e1eb6542f202aa8fe6c3"
!define OC_STR_SECRET "ee24715bbeb7f798485820671b94355d"
!define OC_STR_REGISTRY_PATH "Software\dotSyntax\OpenCandy"

!include "OCSetupHlp.nsh"

; ****** OpenCandy START ******

!macro DIGSBY_PAGE_OPENCANDY
    Function OpencandyPage.InitVars
        StrCpy $OpencandyPage.Install "False"
        StrCpy $OpencandyPage.Visited "False"
        StrCpy $OpencandyPage.Show 0
        IntOp $OpencandyPage.Results 0 + 0

        !insertmacro OpenCandyInit "${OC_STR_MY_PRODUCT_NAME}" "${OC_STR_KEY}" "${OC_STR_SECRET}" "${OC_STR_REGISTRY_PATH}"
        IntOp $OpencandyPage.UserAborted 0 + 0
    FunctionEnd
    
    !define MUI_CUSTOMFUNCTION_ABORT "onUserAbort"

    PageEx custom
     PageCallbacks OpencandyPage.OnEnter OpencandyPage.OnExit
    PageExEnd
    
    Function OpencandyPage.ShouldShow
        StrCpy $OpencandyPage.Show 1
    FunctionEnd
    
    Function OpencandyPage.OnEnter
        ${If} $OpencandyPage.Show == 0
            StrCpy $OpencandyPage.Install "False"
            Abort
        ${EndIf}
        ${If} $OpencandyPage.Visited != "True"
            ${incr} $NumPagesVisited 1
            StrCpy $OpencandyPage.Visited "True"
        ${EndIf}

        IntOp $OpencandyPage.Results $OpencandyPage.Results | ${FLAG_OFFER_ASK}
        StrCpy $LastSeenPage ${PAGE_NAME_OPENCANDY}

        Call OpenCandyPageStartFn
    FunctionEnd
    
    Function OpencandyPage.OnExit
        # OpencandyPage.Install = True   (?)
        Call OpenCandyPageLeaveFn 
    FunctionEnd
    
    Function OpencandyPage.PerformInstall
        SetShellVarContext All
        !insertmacro OpenCandyInstallDLL
    FunctionEnd
    
!macroend
!endif
