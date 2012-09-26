!ifndef OpenDetailPrint
	!define OpenDetailPrint `!insertmacro _OpenDetailPrint`
!endif

!ifndef DetailPrint
	!define DetailPrint `!insertmacro _DetailPrint`
!endif

!ifndef CloseDetailPrint
	!define CloseDetailPrint `!insertmacro _CloseDetailPrint`
!endif

!macro _OpenDetailPrint _FILE
	!ifndef DETAIL_PRINT_FILE
		!define DETAIL_PRINT_FILE
		Var /GLOBAL DETAIL_PRINT_FILE
	!endif
	StrCpy $DETAIL_PRINT_FILE ${_FILE}
	FileOpen $DETAIL_PRINT_FILE `${_FILE}` `w`
!macroend

!macro _DetailPrint _STRING
	FileWrite $DETAIL_PRINT_FILE `${_STRING}$\r$\n`
!macroend

!macro _CloseDetailPrint
	FileClose $DETAIL_PRINT_FILE
!macroend
