rem -- Requires a valid code signing certificate. will use the "best available" so make sure you only have the one you want.
signtool sign /a /t http://timestamp.comodoca.com/authenticode %1
pause