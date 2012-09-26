;-------------------------
;-- Gui
;-------------------------

Function WriteIni
 ; Writes the INI files for gui, to be read later.
 WriteINIStr "$PLUGINSDIR\register.ini" "Settings" "NumFields" "11"
 ;WriteINIStr "$PLUGINSDIR\register.ini" "Settings" "TimeOut" "500"

 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Type" "RadioButton"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Text" "Existing Digsby user"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Left" "5"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Right" "120"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Top" "3"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Bottom" "16"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "State" "0"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Flags" "GROUP"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 1" "Notify" "ONCLICK"

 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Type" "RadioButton"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Text" "New Digsby user"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "State" "1"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Left" "5"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Right" "120"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Top" "18"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Bottom" "30"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Flags" "NOTIFY"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 2" "Notify" "ONCLICK"

;; Invite Code
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Type" "Text"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "State" ""
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Left" "104"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Right" "228"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Top" "39"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Bottom" "51"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Flags" ""
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Notify" "ONTEXTCHANGE"

;; Username
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Type" "Text"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "State" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Left" "104"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Right" "228"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Top" "55"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Bottom" "67"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Flags" "GROUP"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 3" "Notify" "ONTEXTCHANGE"

;; Email
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "Type" "Text"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "State" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "Left" "104"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "Right" "228"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "Top" "71"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "Bottom" "83"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "Flags" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 4" "Notify" "ONTEXTCHANGE"

;; PW 1
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "Type" "Password"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "State" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "Left" "104"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "Right" "228"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "Top" "87"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "Bottom" "99"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "Flags" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 5" "Notify" "ONTEXTCHANGE"

;; PW 2
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "Type" "Password"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "State" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "Left" "104"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "Right" "228"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "Top" "103"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "Bottom" "114"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "Flags" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 6" "Notify" "ONTEXTCHANGE"

 WriteINIStr "$PLUGINSDIR\register.ini" "Field 7" "Type" "Label"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 7" "Text" "Digsby Username:"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 7" "Left" "44"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 7" "Right" "102"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 7" "Top" "56"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 7" "Bottom" "68"

 WriteINIStr "$PLUGINSDIR\register.ini" "Field 8" "Type" "Label"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 8" "Text" "Your Email Address:"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 8" "Left" "38"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 8" "Right" "102"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 8" "Top" "72"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 8" "Bottom" "80"

 WriteINIStr "$PLUGINSDIR\register.ini" "Field 9" "Type" "Label"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 9" "Text" "Create Password:"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 9" "Left" "44"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 9" "Right" "103"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 9" "Top" "88"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 9" "Bottom" "96"

 WriteINIStr "$PLUGINSDIR\register.ini" "Field 10" "Type" "Label"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 10" "Text" "Verify Password:"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 10" "Left" "48"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 10" "Right" "103"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 10" "Top" "104"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 10" "Bottom" "112"

; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Type" "CheckBox"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Text" "I am at least 13 years of age"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "State" "0"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Flags" ""
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Top" "115"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Left" "104"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Right" "224"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Bottom" "127"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 12" "Notify" "ONCLICK"

 WriteINIStr "$PLUGINSDIR\register.ini" "Field 11" "Type" "Label"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 11" "Text" ""
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 11" "Left" "80"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 11" "Right" "224"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 11" "Top" "130"
 WriteINIStr "$PLUGINSDIR\register.ini" "Field 11" "Bottom" "142"

; WriteINIStr "$PLUGINSDIR\register.ini" "Field 13" "Type" "Label"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 13" "Text" "Invite Code:"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 13" "Left" "62"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 13" "Right" "102"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 13" "Top" "40"
; WriteINIStr "$PLUGINSDIR\register.ini" "Field 13" "Bottom" "48"

 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "connection" "Could not connect to Digsby server."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "user_regex" "Invalid username. Please only use letters and numbers."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "email_regex" "That does not appear to be a valid email address."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "pw_length" "Your password must be between 5 and 32 characters in length."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "age_req" "We're sorry, but you must be at least 13 years old to use this software."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "username_or_email_taken" "That username or email has already been registered."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "server_error" "There was a server error. Please select $\"Existing user$\" and create an account after the installation."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "not_approved" "The invite code you entered is either invalid or expired."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "tospp_req" "You must agree to the Terms of Service and Privacy Policy."
 WriteINIStr "$PLUGINSDIR\errorcodes.ini" "msgs" "outofdate" "This installer is out of date. You should get the latest from http://www.digsby.com"

FunctionEnd