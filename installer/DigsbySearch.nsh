!include "FileFunc.nsh"
!include "StrFunc.nsh"

!insertmacro Locate
!insertmacro GetParent
!insertmacro GetFileName
${StrLoc}

!macro _FFX_RewriteSearchPlugin WhichOne FunctionToCall
    Function _OnFindUserFolder_${WhichOne}
     Push "" # Return val to Locate
     #MessageBox MB_OK "Found userfolder for $R7: $R9$R1"
     IfFileExists $R9$R1 0 end
     # $R1 is still the suffix of the "$APPDATA" folder from the function "WriteSearchPluginToFFXProfileFolders".
     ClearErrors
     ${Locate} "$R9$R1\Mozilla\Firefox\Profiles" "/M=* /L=D /G=0" "_OnFindFFXProfile_${WhichOne}" 
     end:
     ClearErrors
    FunctionEnd
 
    Function FFX_WriteSearch_${WhichOne} 
     ClearErrors
     IfFileExists "$R9\searchplugins" do_write_${WhichOne}
       CreateDirectory "$R9\searchplugins"
       ClearErrors
       
     do_write_${WhichOne}:
       Push $R9
       Push "$R9\searchplugins\${WhichOne}"
       Pop $R9
       #MessageBox MB_OK "Calling ${FunctionToCall} for this file:$\n$R9"
       Call ${FunctionToCall}
       ClearErrors
       Exch
       Pop $R9
    FunctionEnd

    Function _OnFindFFXProfile_${WhichOne}
     ClearErrors
     #MessageBox MB_OK "Found FFX Profile $R9"
     #Push "" # Return val to Locate
     Call FFX_WriteSearch_${WhichOne} 
     ClearErrors
    FunctionEnd
    
    Function WriteSearchPluginToFFXProfileFolders_${WhichOne}
     Push $R1
     Push $R2

     !define prefix_len $0
     !define suffix_len $1
     !define profile_prefix $2
     !define appdata_suffix $3
     !define profile_len $4
     !define appdata_len $5
     
     !define PROFILE $PROFILE 
     !define APPDATA $APPDATA 
     
     StrLen ${profile_len} ${PROFILE}
     StrCpy ${appdata_suffix} ${APPDATA} "" ${profile_len}
     StrLen ${suffix_len} ${appdata_suffix}
     IntOp ${prefix_len} ${appdata_len} - ${suffix_len}
     StrCpy ${profile_prefix} ${APPDATA} ${prefix_len}

     Push ${appdata_suffix}
     Pop $R1

     # $R1 is now the suffix of APPDATA that does not include PROFILE.
     # e.g. profile is "c:\Users\Mike" and AppData is "C:\users\Mike\AppData\Roaming"
     # $R1 is "\AppData\Roaming"
     # ${profile_prefix} is the first part, so we can check if it's actually a prefix of PROFILE
     ${GetParent} "${PROFILE}" $R2
     StrCmp ${profile_prefix} ${PROFILE} 0 unknown_profile
     #MessageBox MB_OK "Looking for folders like $R2\*$R1."
     ${Locate} $R2 "/M=* /L=D /G=0" "_OnFindUserFolder_${WhichOne}"
     #MessageBox MB_OK "Done looking for user folders for ${WhichOne}."
     
     !undef prefix_len 
     !undef suffix_len 
     !undef profile_prefix 
     !undef appdata_suffix 
     !undef appdata_len 
     !undef profile_len 
     !undef PROFILE
     !undef APPDATA
    
     unknown_profile:
       
     Pop $R2
     Pop $R1
    FunctionEnd

   Function _FFX_RewriteSearchPlugin_impl_${WhichOne}
       ClearErrors
       !insertmacro DeleteFromMozillaSearchPlugins ${WhichOne}
       IfErrors rewritedone_${WhichOne}
       Call WriteSearchPluginToFFXProfileFolders_${WhichOne}

      rewritedone_${WhichOne}:
       ClearErrors
       
   FunctionEnd
!macroend

!macro FFX_RewriteSearchPlugin Filename
 Call _FFX_RewriteSearchPlugin_impl_${Filename}
!macroend

!macro DeleteFromMozillaSearchPlugins WhatFile
  # ClearErrors
  ReadRegStr $0 HKEY_LOCAL_MACHINE "SOFTWARE\Mozilla\Mozilla Firefox" CurrentVersion
  ${StrLoc} $2 $0 "a" ">"
  StrCmp $2 "" 0 done_${WhatFile}
  ${StrLoc} $2 $0 "A" ">"
  StrCmp $2 "" 0 done_${WhatFile}
  ${StrLoc} $2 $0 "b" ">"
  StrCmp $2 "" 0 done_${WhatFile}
  ${StrLoc} $2 $0 "B" ">"
  StrCmp $2 "" 0 done_${WhatFile}
  ${StrLoc} $2 $0 "c" ">"
  StrCmp $2 "" 0 done_${WhatFile}
  ${StrLoc} $2 $0 "C" ">"
  StrCmp $2 "" 0 done_${WhatFile}
  
  ReadRegStr $1 HKEY_LOCAL_MACHINE "SOFTWARE\Mozilla\Mozilla Firefox\$0\Main" "Install Directory"
  
  IfFileExists "$1\searchplugins\${WhatFile}" 0 notfound_${WhatFile}
   #MessageBox MB_OK "Deleting this: $1\searchplugins\${WhatFile}"
   ClearErrors
   Delete "$1\searchplugins\${WhatFile}"
   Goto done_${WhatFile}

  notfound_${WhatFile}:
    SetErrors
    #MessageBox MB_OK "Not found: $1\searchplugins\${WhatFile}"
    
  done_${WhatFile}:
!macroend

