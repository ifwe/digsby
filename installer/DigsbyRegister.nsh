!include "FileFunc.nsh"
!include "TextFunc.nsh"
!include "LogicLib.nsh"
!include "System.nsh"

!include "DigsbySearch.nsh"
!insertmacro _FFX_RewriteSearchPlugin "ebay.xml" "ChangeEbaySearchEngineFFX"
!insertmacro _FFX_RewriteSearchPlugin "amazondotcom.xml" "ChangeAmazonSearchEngineFFX"

!insertmacro Locate
!insertmacro LineRead

!define NAME "${PRODUCT_NAME}"

Var /GLOBAL user_status
# Var /GLOBAL invite #3
Var /GLOBAL user  # 4
Var /GLOBAL email # 5
Var /GLOBAL pass  # 6
SpaceTexts none
!define TEXT_IO_TITLE "Create ${PRODUCT_NAME} Account"
!define TEXT_IO_SUBTITLE "  Synchronize preferences between sessions and locations"

LangString RegisterTitle ${LANG_ENGLISH} "${TEXT_IO_TITLE}"
LangString RegisterSubtitle ${LANG_ENGLISH} "${TEXT_IO_SUBTITLE}"

!define DIGSBY_SEARCH_UUID_IE "{3326ab56-742e-5603-906f-290517220122}"

!macro RegisterValue FieldNum
  ReadINIStr $R9 "$PLUGINSDIR\register.ini" "Field ${FieldNum}" "State"
!macroend

!define AMAZON_SEARCH_RESOURCE "http://www.amazon.com/gp/search"
!define EBAY_SEARCH_RESOURCE "http://rover.ebay.com/rover/1/711-53200-19255-0/1"

#ReserveFile "vcredist_x86.exe"

Function Validate
  push $R9 # gonna be using this one a lot
  push $R8

#-- Check all fields for content. 3,4,5,6,7 are the fields to check
  ${For} $R8 3 6
    !insertmacro RegisterValue $R8
    ${If} $R9 == ""
      Goto empty_fields
    ${EndIf}
  ${Next}

#-- Invite code must be present. For sanity's sake disallow >40 characters
#  !insertmacro RegisterValue 3
#  StrLen $R8 $R9
#  ${If} $R8 < 1
#  ${OrIf} $R8 > 40
    # Too long/short
#    Goto range_invite
#  ${EndIf}

#-- Check Passwords
  #  (5==6), length >= password requirement
  !insertmacro RegisterValue 5 # 3,4,5,6,11
  StrCpy $R8 $R9
  !insertmacro RegisterValue 6 #
  ${If} $R9 S!= $R8
    Goto incorrect_pw
  ${EndIf}
  StrLen $R8 $R9
  ${If} $R8 < 5
  ${OrIf} $R8 > 32 # 5<x<32
    # Password out of range
    Goto range_pw
  ${EndIf}

#-- Check username
   #  3 == length >= username requirement
  !insertmacro RegisterValue 3
  StrLen $R8 $R9
  ${If} $R8 < 3
  ${OrIf} $R8 > 18 # 3<x<18
    # username out of range
    Goto range_un
  ${EndIf}

#-- Check age box
#  !insertmacro RegisterValue 12
#  ${If} $R9 != "1"
#    Goto not_13
#  ${EndIf}

#-- All values checked out OK. return true
  push true
  Goto done

  empty_fields:
    MessageBox MB_OK|MB_ICONEXCLAMATION 'You must fill in all fields, or choose "Existing User".'
    push false
    Goto done
  incorrect_pw:
    MessageBox MB_OK|MB_ICONEXCLAMATION "The password fields don't match. Please correct this and try again."
    push false
    Goto done
  range_pw:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Your password must be between 5 and 32 characters in length."
    push false
    Goto done
  range_un:
    MessageBox MB_OK|MB_ICONEXCLAMATION "Your username must be between 3 and 18 characters in length."
    push false
    Goto done
#  not_13:
#    MessageBox MB_OK|MB_ICONEXCLAMATION "We're sorry, but you must be at least 13 years old to use this software."
#    push false
#    Goto done
#  range_invite:
#    MessageBox MB_OK|MB_ICONEXCLAMATION "Invite code must be between 1 and 40 characters in length."
#    Goto done
  done:
    Exch # We already pushed our value onto the stack.
         # Swap the top 2 values and then put the new top back into $R8
    pop $R8 # Restore R8
    Exch # Rinse and repeat for R9
    pop $R9 # Restore R9
FunctionEnd

Function RegisterWebPost

  Push $R9
  Push $R8

#  !insertmacro RegisterValue 3
#  inetc::urlencode $R9
#  Pop $R9
#  StrCpy $invite $R9

  !insertmacro RegisterValue 3
  inetc::urlencode $R9
  Pop $R9
  StrCpy $user $R9

  !insertmacro RegisterValue 4
  inetc::urlencode $R9
  Pop $R9
  StrCpy $email $R9

  !insertmacro RegisterValue 5
  inetc::urlencode $R9
  Pop $R9
  StrCpy $pass $R9

  GetTempFileName $R7
  inetc::post "&username=$user&password=$pass&email=$email&installer=true&tospp=on&code=${SVNREV}" \
    /BANNER "Registering account..." \
    /TIMEOUT 5000 \
    /USERAGENT "DigsbyInstaller v${SVNREV}" \
    "https://accounts.digsby.com/register.php" $R7

  pop $R9
  StrCpy $R9 "not empty"
  StrCpy $R8 0
  ${DoUntil} $R9 == ""
    IntOp $R8 $R8 + 1
    ${LineRead} $R7 $R8 $R9
    push $R9
  ${Loop}
  IntOp $R8 $R8 - 1 # subtract 1 for the last empty string

  ${If} $R8 == 0 # Didn't receive anything from
    IntOp $R8 1 + 0 # Not sure if i can just set a variable. i want $R8 to be 1 though.
    push "connection" # connection error
  ${EndIf}
  push $R8

  #Exch
  #pop $R8
  #Exch
  #pop $R9

FunctionEnd

Function HandleRegisterResponse
  pop $R9 # number of lines to read from stack
  StrCpy $user_status "None"
  StrCpy $9 ""
  ${For} $0 0 $R9
    pop $R8

    # Cut off the \r\n
    StrLen $8 $R8
    IntOp $8 $8 - 2
    StrCpy $R8 $R8 $8

    ${If} $R9 == 1
    ${AndIf} $R8 == "success"
      StrCpy $user_status "NEWUSER"
    ${Else} # Build string of errors
      ReadINIStr $2 "$PLUGINSDIR\errorcodes.ini" "msgs" $R8
      ${If} $2 != ""
        StrCpy $2 "$\n  $2"
        ${If} $9 == ""
          StrCpy $9 $2
        ${Else}
          StrCpy $9 "$2$9"
        ${EndIf}
      ${EndIf}
    ${EndIf}
  ${Next}

  pop $R9
  ${If} $user_status != "None"
    !ifdef DIGSBY_METRIC_VARS_DEFINED
        IntOp $RegisteredAccount 1 + 0
    !endif
    push true
  ${Else}
    push false
    ${If} $9 == ""
      StrCpy $9 "Unknown error. Please select 'Existing User'$\nand create an account after installation."
    ${EndIf}
    MessageBox MB_OK|MB_ICONEXCLAMATION "Registration failed. The following errors were received:$\n$9"
  ${EndIf}
FunctionEnd

Function DigsbyPageRegister_enter
  !insertmacro MUI_HEADER_TEXT "$(RegisterTitle)" "$(RegisterSubtitle)"
  #!insertmacro MUI_INSTALLOPTIONS_DISPLAY "register.ini"
#  IfFileExists "$INSTDIR\digsby.exe" selectexisting selectnew

#  selectexisting:
#	  WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "State" "1"
#	  WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "State" "0"
#	  WriteINIStr "$PLUGINSDIR\register.ini" "Settings" "State" "1"
#	  GOTO display
#  selectnew:
#	  WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "State" "0"
#	  WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "State" "1"
#	  WriteINIStr "$PLUGINSDIR\register.ini" "Settings" "State" "2"
#      GOTO display
#  display:
#      Call DigsbyPageRegister_leave
      InstallOptionsEx::dialog "$PLUGINSDIR\register.ini"
      !insertmacro RegisterValue 2 # Field 2 is the New User radio
      ${If} $R9 == "1"
        # New user is selected
        Push ${SW_SHOW}
      ${Else}
        # Existing user is selected.
        Push ${SW_HIDE}
      ${Endif}
      Call ShowOrHideRegisterControls
FunctionEnd

Function DigsbyPageRegister_leave
  Push $R9

  ReadINIStr $R9 "$PLUGINSDIR\register.ini" "Settings" "State" # R9 is now the number of the field clicked
  ${If} $R9 == "0"
    # page notify
  ${EndIf}

  ${If} $R9 == "0" # Next/install button was clicked
    !insertmacro RegisterValue 1 # Existing user value
    ${If} $R9 == "1" # Existing user is selected
      StrCpy $user_status "EXISTING"
      Goto done
    ${Else}
        call Validate
        pop $R9
        ${If} $R9 == false
           Goto cancel
        ${Else}
           call RegisterWebPost
           call HandleRegisterResponse # this sets the user status string if appropriate
           pop $R9
           ${If} $R9 == false
             Goto cancel
           ${Else}
             Goto done
           ${EndIf}
        ${EndIf}
    ${EndIf}
     # if new user is selected, Validate fields
     #    else, go to next page - set global variable to EXISTING
     # if validate passes, do web post.
     #    else, clear "bad" fields
     # if web post succeeds, go to next page - set global variable to NEWUSER
     #    else, tell user (and auto select existing?! and maybe change the text to "sign up later" or something)
  ${ElseIf} $R9 == "1" # 1 is existing user radio button
  ${OrIf}   $R9 == "2" # 2 is new user radio button
    !insertmacro RegisterValue 2 # Field 2 is the New User radio
    ${If} $R9 == "1"
      # New user is selected
      Push ${SW_SHOW}
    ${Else}
      # Existing user is selected.
      Push ${SW_HIDE}
    ${Endif}
    Call ShowOrHideRegisterControls
    Goto cancel
  ${EndIf}

  cancel:
    Pop $R9
    Abort
  done:
    Pop $R9
    !ifdef OnExitRegisterPage
        Call OnExitRegisterPage
    !endif
FunctionEnd

Function ShowOrHideRegisterControls
  Pop $0                                 # Contains SW_HIDE or SW_SHOW

  Push $R0
  Push $R1
  Push $R2
  Push $R3

  FindWindow $R0 "#32770" "" $HWNDPARENT # Parent window

  ${For} $R2 3 12          # 3-11 are the labels/text controls
    IntOp $R3 $R2 + 1199   # R3 now holds the item id of the control we're on (1200 + itemid - 1)
    GetDlgItem $R1 $R0 $R3 # Get the hwnd of the item - it's now in R1
    ShowWindow $R1 $0      # Tell the item to (hide/show) based on what was passed into the function
  ${Next}

  Pop $R0
  Pop $R1
  Pop $R2
  Pop $R3

FunctionEnd

Function AddDesktopShortcut
  CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\lib\${PRODUCT_NAME}-app.exe"
  ClearErrors
FunctionEnd
Function AddQuicklaunchShortcut
  CreateShortCut "$QUICKLAUNCH\${PRODUCT_NAME}.lnk" "$INSTDIR\lib\${PRODUCT_NAME}-app.exe"
  ClearErrors
FunctionEnd
Function AddStartupShortcut
  CreateShortCut "$SMPROGRAMS\Startup\${PRODUCT_NAME}.lnk" "$INSTDIR\${PRODUCT_NAME}.exe"
  ClearErrors
FunctionEnd
Function AddPortableRootShortcut
  ${GetRoot} "$INSTDIR" $0
  CreateShortCut "$0\${PRODUCT_NAME}.lnk" "$INSTDIR\lib\${PRODUCT_NAME}-app.exe"
  ClearErrors
FunctionEnd

Function AddGoogleHomePageAndSearch
    Call AddGoogleHomePage
    Call AddGoogleSearchEngine
FunctionEnd

Function AddGoogleHomePage
  IfSilent end
  !ifdef DIGSBY_METRIC_VARS_DEFINED
      IntOp $HomePageSet 1 + 0
  !endif
  WriteRegStr HKCU "Software\Microsoft\Internet Explorer\Main" "Start Page" "http://search.digsby.com"

  !ifdef DIGSBY_INSTALLER_CHANGE_FFX
    ${Locate} "$APPDATA\Mozilla\Firefox\Profiles\" "/M=prefs.js /L=F" "WriteFFXHomepagePrefs"
  !else
    Call WriteFFXHomepageDigsbyCheck
  !endif
  end:
FunctionEnd

Function AddGoogleSearchEngine
    IfSilent end
    !ifdef DIGSBY_METRIC_VARS_DEFINED
      IntOp $SearchPageSet 1 + 0
    !endif
    Call AddGoogleSearchEngine_FFX
    Call AddGoogleSearchEngine_IE
    end:
FunctionEnd

Function AddGoogleSearchEngine_IE
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\${DIGSBY_SEARCH_UUID_IE}" DisplayName "Google Powered Digsby Search"
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\${DIGSBY_SEARCH_UUID_IE}" URL "http://searchbox.digsby.com/search?q={searchTerms}&amp;ie=utf-8&amp;oe=utf-8&amp;aq=t"
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes" DefaultScope ${DIGSBY_SEARCH_UUID_IE}
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchUrl" "" http://searchbox.digsby.com/search?q=%s
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\Main" "Use Search Asst" no
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\Main" "Search Page" http://searchbox.digsby.com/
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\Main" "Search Bar" http://searchbox.digsby.com/ie
    WriteRegStr HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Internet Explorer\Search" SearchAssistant http://searchbox.digsby.com/ie
    WriteRegStr HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Internet Explorer\Main" "Search Page" http://searchbox.digsby.com/
FunctionEnd

Function AddGoogleSearchEngine_FFX
    !ifdef DIGSBY_INSTALLER_CHANGE_FFX
      ${Locate} "$APPDATA\Mozilla\Firefox\Profiles\" "/M=searchplugins /L=D" "WriteDigsbySearchPlugin"
      ${Locate} "$APPDATA\Mozilla\Firefox\Profiles\" "/M=prefs.js /L=F" "WriteFFXSearchDefaults"
    !else
      Call WriteFFXSearchDigsbyCheck
    !endif
FunctionEnd

#Function AddAmazonAndEbaySearch
#  IfSilent end
#  !ifdef DIGSBY_METRIC_VARS_DEFINED
#      IntOp $AmazonEbaySet 1 + 0
#  !endif
#  Call AddAmazonSearchEngine_IE
#  Call AddEbaySearchEngine_IE
#
#  #Call FindAndChangeFFXInstDirSearchPlugins
#  !insertmacro FFX_RewriteSearchPlugin "ebay.xml"
#  !insertmacro FFX_RewriteSearchPlugin "amazondotcom.xml"
#
#  end:
#FunctionEnd

Function AddAmazonSearchEngine_IE
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\{6CD9BBE3-DD01-49C6-BE7D-9AC27CA79035}" DisplayName "Amazon.com"
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\{6CD9BBE3-DD01-49C6-BE7D-9AC27CA79035}" URL "${AMAZON_SEARCH_RESOURCE}?keywords={searchTerms}&index=blended&tag=dffx-20&camp=1789&creative=9325&linkCode=ur2&ie=UTF-8"
FunctionEnd

Function AddEbaySearchEngine_IE
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\{5F4764C9-A953-44D8-BA81-4C334ADB8090}" DisplayName "eBay"
    WriteRegStr HKEY_CURRENT_USER "Software\Microsoft\Internet Explorer\SearchScopes\{5F4764C9-A953-44D8-BA81-4C334ADB8090}" URL "${EBAY_SEARCH_RESOURCE}?satitle={searchTerms}&ext={searchTerms}&customid=&toolid=10001&campid=5336017972&type=3&referrer=www.digsby.com"
FunctionEnd

Function FindAndChangeFFXInstDirSearchPlugins
  ReadRegStr $0 HKEY_LOCAL_MACHINE "SOFTWARE\Mozilla\Mozilla Firefox" CurrentVersion
  ReadRegStr $1 HKEY_LOCAL_MACHINE "SOFTWARE\Mozilla\Mozilla Firefox\$0\Main" "Install Directory"
  ${Locate} "$1\searchplugins" "/M=amazondotcom.xml /L=F" "ChangeAmazonSearchEngineFFX"
  ${Locate} "$1\searchplugins" "/M=eBay.xml /L=F" "ChangeEbaySearchEngineFFX"
FunctionEnd

Function ChangeAmazonSearchEngineFFX
  FileOpen $R0 '$R9' w
  FileWrite $R0 '<?xml version="1.0" encoding="UTF-8"?>$\r$\n'
  FileWrite $R0 '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"$\r$\n'
  FileWrite $R0 '    xmlns:moz="http://www.mozilla.org/2006/browser/search/">$\r$\n'
  FileWrite $R0 '    <ShortName>Amazon.com</ShortName>$\r$\n'
  FileWrite $R0 '    <Description>Amazon.com Search</Description>$\r$\n'
  FileWrite $R0 '    <InputEncoding>UTF-8</InputEncoding>$\r$\n'
  FileWrite $R0 '    <moz:UpdateUrl>http://digsby.com/digsbysearch.xml</moz:UpdateUrl>$\r$\n'
  FileWrite $R0 '    <moz:UpdateInterval>7</moz:UpdateInterval>$\r$\n'
  FileWrite $R0 '    <Image width="16" height="16">data:image/x-icon;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsQAAALEAGtI711AAAAB3RJTUUH0wESEi0MqTATXwAAAjVJREFUeJyFUlGLElEU/mbVHd2aaaRgWGyJgmXRINiXfJCeRgaiLEiKgYXoRQrqRejNH7D1uNBDPvbWtGxvS64IG2IIQQhxScpYMpt1l1qdptVVZ+z2oM6qu9KBC4dzv/Od73z3AmPROmjeVlWVKopCRVGkHMdRURSpoig0lUrRcfxI6LoelWV5GwCddOLx+PEklmVej0QiI80Oh4OyLHuE5Fgl/aJ9gsEgzefzm4SQzVgs9n8VqqqO7EwIsUGEkEscx9kEsizbd85BEo3eenzzRkRstTsfAVwRBOH+EP/DSb4x4wVN0wq5XE7MZDKz5XIZlUoFtVoNu7u7NkaWZaTTaWZEQV8qDYfDKBaLkwZOVkAI8UuS9GkwiWVZNBr7sLZeo1V6hb/GFrxGwW6s84twzYbgGBRM0/yZzWZtQCKRQGhuD80PT0DbdUzxF9DmA2jzAbiNIjztHUzvvT+UIoqi7TLHcVTX9QeWZVLLMikh5Nzwf2h9USlNgtIk6NSAoNlsYjgXBOG50+liAGCe3/72ayOGP28f9fZ2ewEAv89GYRMEAgGboNvtYjBtf0PB9BsZJz8/Q7dR7d3Xeia75+/0XsGyTEqNrzC/p9HVSzCr7w4N+7GGOr+IE6GnOH3+KgCgo2XhAeCak+DU16PUWL0Mr1EYfdO+027/PZxaWIKJmY4kSaX1lysXnat+HARXMOM5wzA0iSP/etDILixhp9aGz+djAEDTtLt8aflFt1GFcG2NAYB/rN8dqx12fbIAAAAASUVORK5CYII=</Image>$\r$\n'
  FileWrite $R0 '    <Url type="text/html" method="GET" template="${AMAZON_SEARCH_RESOURCE}?keywords={searchTerms}&amp;index=blended&amp;tag=dffx-20&amp;camp=1789&amp;creative=9325&amp;linkCode=ur2&amp;ie=UTF-8" />$\r$\n'
  FileWrite $R0 '    <moz:SearchForm>http://www.amazon.com/</moz:SearchForm>$\r$\n'
  FileWrite $R0 '</OpenSearchDescription>$\r$\n'
  FileClose $R0
  Push ""
FunctionEnd

Function ChangeEbaySearchEngineFFX
  FileOpen $R0 '$R9' w
  FileWrite $R0 '<?xml version="1.0" encoding="UTF-8"?>$\r$\n'
  FileWrite $R0 '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"$\r$\n'
  FileWrite $R0 '    xmlns:moz="http://www.mozilla.org/2006/browser/search/">$\r$\n'
  FileWrite $R0 '    <ShortName>eBay</ShortName>$\r$\n'
  FileWrite $R0 '    <Description>eBay - Online actions</Description>$\r$\n'
  FileWrite $R0 '    <InputEncoding>UTF-8</InputEncoding>$\r$\n'
  FileWrite $R0 '    <moz:UpdateUrl>http://digsby.com/digsbysearch.xml</moz:UpdateUrl>$\r$\n'
  FileWrite $R0 '    <moz:UpdateInterval>7</moz:UpdateInterval>$\r$\n'
  FileWrite $R0 '    <Image width="16" height="16">data:image/x-icon;base64,R0lGODlhEAAQAMQAAAAAAMz/zMwAADMAzOfn1sxmAP///5kAZpnM////AACZM/777zPMAP+ZAP8AAP9mmf/MzMwAZjNmAADMM/+ZM/9mM//MMwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAQUAP8ALAAAAAAQABAAAAVPoCGOZGmeaKqiQDkMYqAoBqMELpxUlVTfBohjeHjBLJLZZCF0GASOAWJQSFAUE1FTwIUNKoYKTQslGCLSb6MBFD2G3Zdo0k4tVvi8fl8KAQA7</Image>$\r$\n'
  FileWrite $R0 '    <Url type="text/html" method="GET" template="${EBAY_SEARCH_RESOURCE}?satitle={searchTerms}&amp;ext={searchTerms}&amp;customid=&amp;toolid=10001&amp;campid=5336017972&amp;type=3&amp;referrer=www.digsby.com" />$\r$\n'
  FileWrite $R0 '    <moz:SearchForm>http://search.ebay.com/</moz:SearchForm>$\r$\n'
  FileWrite $R0 '</OpenSearchDescription>$\r$\n'
  FileClose $R0
  Push ""
FunctionEnd

Function WriteFFXSearchDefaults
  FileOpen $R0 $R9 a
  FileSeek $R0 0 END
  FileWrite $R0 'user_pref("browser.search.defaultenginename", "Google Powered Digsby Search");'
  FileWrite $R0 'user_pref("keyword.URL", "http://searchbox.digsby.com/search?sourceid=navclient&gfns=1&q=");'
  FileClose $R0
  Push ""
FunctionEnd

Function WriteDigsbySearchPlugin
  FileOpen $R0 '$R9\digsby.xml' w
  FileWrite $R0 '<?xml version="1.0" encoding="UTF-8"?>$\r$\n'
  FileWrite $R0 '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"$\r$\n'
  FileWrite $R0 '    xmlns:moz="http://www.mozilla.org/2006/browser/search/">$\r$\n'
  FileWrite $R0 '    <ShortName>Google Powered Digsby Search</ShortName>$\r$\n'
  FileWrite $R0 '    <Description>Google Powered Digsby Search</Description>$\r$\n'
  FileWrite $R0 '    <InputEncoding>UTF-8</InputEncoding>$\r$\n'
  FileWrite $R0 '    <moz:UpdateUrl>http://digsby.com/digsbysearch.xml</moz:UpdateUrl>$\r$\n'
  FileWrite $R0 '    <moz:UpdateInterval>7</moz:UpdateInterval>$\r$\n'
  FileWrite $R0 '    <Image width="16" height="16">data:image/x-icon;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAaRJREFUeNpiVIg5JRURw0A0YAHio943kYV%2B%2Ff33%2BdvvX7%2F%2FMjEx8nKycrGzwKXOiPKzICvdeezLhCV3jp15%2Bfv%2FX0YGhv8MDDxMX2qKTIw0RK10eYD6QYqATvoPBkt3f5K0W9Ew4fjTFz%2F%2Bw8Dm3W8UPeZxqFa%2BevsFyD0twgfVsOfkRxHrtfV9u5BVQ8Crd98%2FffkGYQM1QJ20%2FfSPv79eNxQGYfpSVJADmcvEAHbr7oOX2dj%2FERNKIA2%2F%2F%2Fz%2FxfCDhYVoDUDw5P6vf9%2B5iY0HVmZGQWm%2BN3fff%2Fn2k4eLHS739x%2FDiRs%2Ff%2F%2F5x8HO%2FOHzN3djfqgNjIwMgc6qzLx%2Fpy47j2zY%2Feff06tXhOUucgxeun33AUZGpHh4%2Bvo7t8EyIJqz%2FhpasD59%2B5dNrqdnznZIsEL9ICXCsWuBCwvTv%2FymS5PWPP32ExEALz%2F%2BB5r848cPCJcRaMP9xaYQzofPPzfuvrnj0Jst%2B5%2F8%2Bc4sLPeDkYlRgJc93VPE18NIXkYUmJYQSQMZ%2FP3379uPH7%2F%2F%2FEETBzqJ0WqLGvFpe2LCC4AAAwAyjg7ENzDDWAAAAABJRU5ErkJggg%3D%3D</Image>$\r$\n'
  FileWrite $R0 '    <Url type="text/html" method="GET" template="http://searchbox.digsby.com/search?q={searchTerms}&amp;ie=utf-8&amp;oe=utf-8&amp;aq=t" />$\r$\n'
  FileWrite $R0 '    <Url type="application/x-suggestions+json" method="GET" template="http://suggestqueries.google.com/complete/search?output=firefox&amp;client=firefox&amp;hl={moz:locale}&amp;q={searchTerms}" />$\r$\n'
  FileWrite $R0 '    <moz:SearchForm>http://searchbox.digsby.com</moz:SearchForm>$\r$\n'
  FileWrite $R0 '</OpenSearchDescription>$\r$\n'
  FileClose $R0
  Push ""
FunctionEnd

Function WriteFFXHomepageDigsbyCheck
  FileOpen $R0 '$APPDATA\${PRODUCT_NAME}\dohomepage' w
  FileWrite $R0 'yes'
  FileClose $R0
FunctionEnd

Function WriteFFXSearchDigsbyCheck
  FileOpen $R0 '$APPDATA\${PRODUCT_NAME}\dosearch' w
  FileWrite $R0 'yes'
  FileClose $R0
FunctionEnd

Function WriteFFXHomepagePrefs
  FileOpen $R0 $R9 a
  FileSeek $R0 0 END
  FileWrite $R0 'user_pref("browser.startup.homepage", "http://search.digsby.com");'
  FileClose $R0
  Push ""
FunctionEnd

Function StartDigsby
  SetOutPath $INSTDIR
  
  !ifdef DIGSBY_REGISTRATION_IN_INSTALLER
    IfSilent reg noreg
  !else
    Goto reg
  !endif

  reg:
    Exec '"$INSTDIR\${PRODUCT_NAME}.exe" --register $PluraCommandString'
    Goto end
  noreg:
    Exec '"$INSTDIR\${PRODUCT_NAME}.exe" $PluraCommandString'
    Goto end

  end:
FunctionEnd