'''

Validators for text controls.

'''

import wx, string

class SimpleValidator(wx.PyValidator):
    def __init__(self, char_callbacks, str_callbacks):
        # Guard agaisnt accidentally calling with a single function

        if callable(char_callbacks):
            char_callbacks = (char_callbacks,)
        if callable(str_callbacks):
            str_callbacks = (str_callbacks,)

        wx.PyValidator.__init__(self)
        self.char_callbacks = char_callbacks
        self.str_callbacks = str_callbacks
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_TEXT, self.OnText)

    def OnChar(self, event):
        key = event.GetKeyCode()
        if key < 0 or key > 255 or chr(key) not in string.printable or self.check_char(chr(key)):
            event.Skip()
            self._last_ok_val = event.EventObject.Value
            return

        if not wx.Validator.IsSilent(): wx.Bell()

    def OnText(self, event):
        s = event.EventObject.Value

        if not self.check_string(s):
            event.EventObject.Value = self._last_ok_val
        else:
            self._last_ok_val = s
            event.Skip()

    def check_char(self, c):
        return all(cb(c) for cb in self.char_callbacks)

    def check_string(self, s):
        return all(cb(s) for cb in self.str_callbacks)

    def Clone(self):
        return SimpleValidator(self.char_callbacks, self.str_callbacks)

    def Validate(self, win):
        return 1

    def TransferToWindow(self):
        """ Transfer data from validator to window.

         The default implementation returns False, indicating that an error
         occurred.  We simply return True, as we don't do any data transfer.
        """
        return True # Prevent wx.Dialog from complaining.


    def TransferFromWindow(self):
        """ Transfer data from window to validator.

         The default implementation returns False, indicating that an error
         occurred.  We simply return True, as we don't do any data transfer.
        """
        return True # Prevent wx.Dialog from complaining.

    def __add__(self, other):
        return SimpleValidator(self.char_callbacks + other.char_callbacks, self.str_callbacks + other.str_callbacks)

def string_check(type):
    valid = getattr(string, type)
    return lambda s: all(c in valid for c in s)

def AlphaOnly():
    'A wxValidator which allows only letters.'
    return SimpleValidator((string_check('letters'),), ())

def DigitsOnly():
    'A wxValidator which allows only digits.'
    return SimpleValidator((string_check('digits'),), ())

def LengthLimit(n):
    'A wxValidator that does not allow more than n characters'
    return SimpleValidator((), (lambda s: len(s)<=n,),)

def NumericLimit(start,stop=None):
    if stop is None:
        start, stop = 0, start

    return DigitsOnly() + SimpleValidator((), lambda s: ((not s) or (start <= int(s) <= stop)))


common_validators = dict(
  # Keycode types for formatting strings, i.e. %2(some.pref)d <--- 2 Digits
  d = DigitsOnly,
  s = AlphaOnly
)