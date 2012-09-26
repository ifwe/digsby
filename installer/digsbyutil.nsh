!macro _UNDEF name
    !ifdef ${name}
       !undef ${name}
    !endif
!macroend

!define UNDEF "!insertmacro _UNDEF"

!macro _REDEF name what
    ${UNDEF} ${name}
    !define ${name} ${what}
!macroend

!define REDEF "!insertmacro _REDEF"

#---
#  result = val1 op val2
#---
!macro _REDEF_MATH rmresult rmval1 rmop rmval2
    ${UNDEF} ${rmresult}
    !define /math ${rmresult} ${${rmval1}} ${rmop} ${rmval2}
!macroend
!define REDEF_MATH "!insertmacro _REDEF_MATH"

#---
#  val1 = val1 op val2
#---
!macro _IMATH imval1 imop imval2
    #MessageBox MB_OK "imath in ${${imval1}}"
    ${REDEF_MATH} _IMATH_TEMP_VAR ${${imval1}} ${imop} ${imval2}
    ${REDEF} ${imval1} ${_IMATH_TEMP_VAR}
    ${UNDEF} _IMATH_TEMP_VAR
    #MessageBox MB_OK "imath out ${${imval1}}"
!macroend
!define IMATH "!insertmacro _IMATH"

#---
#  val++
#---
!macro _INCREMENT val
    !ifndef ${val}
       ${REDEF} ${val} 0
    !endif
    ${IMATH} ${val} + 1
!macroend
!define INCREMENT "!insertmacro _INCREMENT"

!macro _FINISHPAGE_VOFFSET what howmuch
    !define /math MUI_FINISHPAGE_${what}_VOFFSET ${howmuch} + ${MUI_FINISHPAGE_V_OFFSET}
!macroend
!define FINISHPAGE_VOFFSET "!insertmacro _FINISHPAGE_VOFFSET"

!macro _incr _var val
  IntOp ${_var} ${_var} + ${val}
!macroend

!define incr "!insertmacro _incr "

!macro _decr _var val
  IntOp ${_var} ${_var} - ${val}
!macroend

!define decr "!insertmacro _decr "

Function RelGotoPage
    IntCmp $R9 0 0 Move Move
    StrCmp $R9 "X" 0 Move
    StrCpy $R9 "120"

  Move:
    SendMessage $HWNDPARENT "0x408" "$R9" ""
FunctionEnd
