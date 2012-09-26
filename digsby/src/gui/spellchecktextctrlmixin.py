import string
import wx
import re
from common import profile, pref, prefprop
from gui.textutil import FindAny, rFindAny

from cgui import InputBox

from common.spelling import spellchecker


from util.net import isurl

punc = ''.join((string.punctuation.replace("'", ''),' ','\t','\n')) # all punctuation but single quote, which is used in correctly spelled words. i.e. don't
word_splitting_chars = re.escape(punc)
tokenizer_re = re.compile(r'\s+|[%s]' % word_splitting_chars)


import logging

log = logging.getLogger('spellcheckmixin')

class SpellCheckTextCtrlMixin(object):

    def __init__(self):

        #these hold a set of information for the last time the field has been
        #spellchecked to check against to prevent redundant checks
        self.lastvalue = self.Value
        self.lastcharcount = len(self.Value)
        self.lastinsertion = self.InsertionPoint
        self.lastcurrentword = None
        self.needscheck = False
        self.lastkeycode = None
        self.lastchar = None

        self.regex_ignores = []

        self.spellcheckon  = frozenset(punc + ' ')
        self.spellerrors   = dict()

        Bind = self.Bind
        Bind(wx.EVT_KEY_DOWN  , self.OnKey)
        Bind(wx.EVT_TEXT      , self.OnText)
        Bind(wx.EVT_LEFT_DOWN , self.OnLeftDown)


        WM_PAINT = 0x000F #Native Windows Paint Message, thanks MSDN or a source file, I don't remember
        BindWin32 = self.BindWin32
        BindWin32(WM_PAINT, self.WMPaint)

        wx.CallAfter(self.SpellCheckAll)

        link = profile.prefs.link
        link('messaging.spellcheck.enabled', self.UpdateEnablement)
        link('messaging.spellcheck.engineoptions.lang', self.UpdateEnablement)
        link('messaging.spellcheck.engineoptions.keyboard', self.UpdateEnablement)
        self.UpdateEnablement()

    def HasSpellingErrors(self):
        return bool(self.spellerrors)

    def AddRegexIgnore(self, regex):
        self.regex_ignores.append(regex)

    def RemoveRegexIgnore(self, regex):
        try:
            self.regex_ignores.remove(regex)
        except ValueError:
            return False
        else:
            return True

    def UpdateEnablement(self, *a):
        """
            Updates the display and spell errors when the spellcheck options are changed
        """

        #FIXME: Need a way to un-observe after and object is destroyed
        if not wx.IsDestroyed(self):
            spenabled = self.spenabled = pref('messaging.spellcheck.enabled')

            if spenabled:
                self.SpellCheckAll()
            else:
                self.spellerrors.clear()
                self.Refresh()

        else:
            log.error('UpdateEnablement observer called on a SpellCheckTextCtrlMixin that has been destroyed')



    def WMPaint(self, hWnd, msg, wParam, lParam):
        wx.CallAfter(self.PostPaint)


    spsize  = 2      #The thickness of the line
    spstyle = wx.DOT #The type of line used for spellcheck
    def PostPaint(self):

        """
            After the text is done painting, draw the spellcheck markup over it
        """

        try:
            # text control must implement GetReqHeight
            bottom = self.GetReqHeight()
        except AttributeError:
            return

        dc = wx.ClientDC(self)

        dc.Brush = wx.TRANSPARENT_BRUSH #@UndefinedVariable
        dc.Pen = wx.Pen(wx.RED, self.spsize, self.spstyle) #@UndefinedVariable

        lastline = self.GetNumberOfLines() - 1


        Point = wx.Point
        PosXY = lambda i: self.PositionToXY(i)[1:]
        XYPos = self.XYToPosition
        IndexToCoords = self.IndexToCoords
        value = self.Value

        for word in self.spellerrors:
            wordlen = len(word)
            for i in self.spellerrors[word]:

                i1    = i
                start = IndexToCoords(i)
                end   = IndexToCoords(i + wordlen)

                if PosXY(i)[1] != lastline:
                    ymod = IndexToCoords(XYPos(0, PosXY(i)[1]+1))[1] - start.y
                else:
                    ymod = (bottom - start.y) - 8 + IndexToCoords(0).y

                points = []
                while start.y != end.y:
                    r1 = PosXY(i1)[1]
                    i2 = XYPos(0, r1 + 1)
                    e1 = i2 - 1

                    lineend = self.IndexToCoords(e1) + Point(dc.GetTextExtent(value[e1])[0], 0)
                    points.append((start, lineend))

                    i1 = i2
                    start = IndexToCoords(i1)

                points.append((start,end))

                for s, e in points:
                    dc.DrawLine(s.x, s.y + ymod, e.x, e.y + ymod)

    def AddSpellError(self,word,index, refresh = True):

        """
            Adds a misspelled word, or another index of that word to the dictionary of misspelled
            words for lookup later
        """

        if not word in self.spellerrors:
            self.spellerrors[word] = []

        if not index in self.spellerrors[word]:
            self.spellerrors[word].append(index)

        if refresh: self.Refresh()


    def UpdateSpellErrorIndexes(self):
        """
            Offsets all the spellerror indexes by the number of characters that
            have been typed since the last check if the index is higher then the
            last insertion index
        """

        lastinsert = self.lastinsertion
        lastcount  = self.lastcharcount

        deltachar   = len(self.Value) - lastcount
        spellerrors = self.spellerrors

        for word in spellerrors:
            for n in list(spellerrors[word]):
                if n > lastinsert:
                    i = spellerrors[word].index(n)
                    spellerrors[word][i] = n + deltachar

        self.Refresh()

    def ClearSpellErrors(self):
        """
            Clears all the spell errors
            Note that this does not update the display
        """

        self.spellerrors.clear()

    def RemoveExpiredSpellError(self, start, end, value=None):
        """
            This does various checks to try and dismiss marked errors that are no longer valid
        """

        if value is None:
            value = self.Value

        #URLs are not misspelled so lets get them out of the string
        #urllessWords
        purewords = [word for word in value.split() if not self.ignore_word(word)]
        #purewords = ' '.join(urllessWords)

        #validate all the words in the spellerrors dictionary
        for word in set(self.spellerrors):
            wordlen = len(word)

            #if the word is't in the splash zone, don't bother checking it
            if not any(start<=i<=end for i in self.spellerrors[word]):
                continue

            #Remove the mark if the word is in the dictionary or no longer in the textctrl
            if word not in purewords or self.Check(word):
                self.spellerrors.pop(word)

                continue

            #if the word is still marked wrong but the number of instances have changed validate individual indexes
            elif len(self.spellerrors[word]) != purewords.count(word):
                for i in list(self.spellerrors[word]):
                    if value[i:i + wordlen] != word:
                        self.spellerrors[word].remove(i)

        self.Refresh()

    kb_shortcut_fixes = prefprop('messaging.spellcheck.kb_shortcut_fixes', default=False)

    def OnKey(self, e):
        """
            Key press event handling
            records last key code and the unicode character for that key
        """

        e.Skip()

        if not self.spenabled:
            return

        if self.kb_shortcut_fixes and \
                e.GetModifiers() == wx.MOD_CMD and e.KeyCode == wx.WXK_SPACE:
            e.Skip(False)
            return self.ReplaceWordWithBestSuggestion()

        self.lastchar        = e.UnicodeKey
        self.lastvalue       = self.Value
        self.lastcharcount   = len(self.lastvalue)

        wx.CallAfter(self.PostOnKey)

    def PostOnKey(self):
        """
            Activates spellcheck on last change if a
            navigation or other non-editing key is hit
        """
        val = self.Value
        charcount = len(val)
        if self.needscheck and charcount and val == self.lastvalue:
            self.SpellCheckLastChange()

        self.lastinsertion   = self.InsertionPoint
        self.lastcurrentword = self.GetCurrentWord()


    def OnText(self,event):
        """
            Text insertion event, flags the textfield as dirty if the text actually changed
        """

        event.Skip()

        if not self.spenabled or self.Value == self.lastvalue:
            self.Refresh()
            return

        self.needscheck = True

        self.UpdateSpellErrorIndexes()

        charcount = len(self.Value)

        if abs(charcount - self.lastcharcount) == 1:
            keypressed = unichr(self.lastchar) if self.lastchar else None
            currentword = self.GetCurrentWord()

            if ((keypressed in self.spellcheckon) or
                self.lastcurrentword in self.spellerrors and currentword != self.lastcurrentword):
                self.SpellCheckLastChange()
        else:
            self.SpellCheckAll()


    def UpdateLasts(self):
        """
            Updates variables used to determine if the string should be checked again
        """
        pass

    def Check(self, word):
        '''Returns True if a word should be considered spelled correctly.'''

        return self.ignore_word(word) or spellchecker.Check(word)

    def ignore_word(self, word):
        if word and isurl(word):
            return True

        for regex in self.regex_ignores:
            if regex.match(word):
                return True

        return False

    def SpellCheckAll(self):
        """
            Clears all the errors and re-spellchecks the entire text field
        """

        self.ClearSpellErrors()

        val = self.Value
        span = [word for word in val.split() if not self.ignore_word(word)]
        words = tokenizer_re.split(' '.join(span))

        index = 0

        for word in words:
            word = word.strip(string.punctuation)
            correct = self.Check(word)

            index = val.find(word, index)

            if not correct: self.AddSpellError(word, index, False)

            index += len(word)


        self.needscheck = False


        self.Refresh()


    def OnLeftDown(self,event):
        """
            Event handler to trigger spellcheck on click
        """
        event.Skip()

        if not self.spenabled:
            return

        charcount = len(self.Value)

        if charcount and self.needscheck:
            self.SpellCheckLastChange()

        self.lastinsertion = self.InsertionPoint
        self.lastcurrentword = self.GetCurrentWord()


    def GetCurrentWord(self):
        """
            Get word at cursor position
        """
        return self.GetWordAtPosition(self.InsertionPoint)

    def GetWordRangeAtPosition(self, ip):
        """
            For suggestion menu, only returns the word range using punctuation
            as a word breaking character
        """
        s = self.Value

        # for misspellings like "audio/vedio" we will underline
        # only "vedio." make sure that if you right click it, you
        # get only "vedio" -- the word the cursor is under.
        split_on = word_splitting_chars

        end = FindAny(s, split_on, ip)
        if end == -1: end = len(s)

        start = max(rFindAny(s, split_on, 0, end), 0)
        return start, end

    def GetWordAtPosition(self, ip):
        """
            For suggestion menu, only returns the word range using punctuation
            as a word breaking character
        """
        start, end = self.GetWordRangeAtPosition(ip)
        word = self.Value[start:end].split()
        if word:
            return word[0].strip(string.punctuation)

    def AddWordToDictionary(self, word):
        """
            Add a word, duh
        """
        spellchecker.Add(word)

        self.SpellCheckAll()

    def HitTestSuggestions(self, pos):
        """
            Returns the word under the mouse
        """
        result, col, row = self.HitTest(pos)
        if result == wx.TE_HT_UNKNOWN:
            return -1, []

        i = self.XYToPosition(col, row)
        return i, self.GetSuggestionsForPosition(i)

    def GetSuggestionsForPosition(self, i):
        if i == -1: return []

        word = self.GetWordAtPosition(i)

        if word and word in self.spellerrors:
            return spellchecker.Suggest(word)
        else:
            return []

    def AdjustSpellerrorIndex(self, index, diff):
        """
            This offsets all spellerror index that are highr than index by diff
        """
        spellerrors = self.spellerrors

        for word in spellerrors:
            for n in list(spellerrors[word]):
                if n > index:
                    i = spellerrors[word].index(n)
                    spellerrors[word][i] = n + diff


    def ReplaceWord(self, position, new_word):
        """
            Replaces the word at the position with the new word, and spell checks he area
        """
        oldip = self.InsertionPoint

        old_value = self.Value
        i, j = self.GetWordRangeAtPosition(position)


        old_word = old_value[i:j]

        # Since GetWordRangeAtPosition returns punctuation and whitespace...
        l = len(old_word)
        old_word = old_word.lstrip(nonword_characters)
        i += l - len(old_word)

        l = len(old_word)
        old_word = old_word.rstrip(nonword_characters)
        j -= l - len(old_word)

        self.Replace(i, j, new_word)


        diff = (len(new_word) - len(old_word))
        self.AdjustSpellerrorIndex(position, diff)
        self.InsertionPoint = oldip + diff

#        self.UpdateSpellErrorIndexes()

        self.SpellCheckLastChange(position)
        self.ProcessEvent(wx.CommandEvent(wx.EVT_TEXT[0], self.Id))

    def ReplaceWordWithBestSuggestion(self, pos=None):
        '''Replaces the word at pos with the spellchecker's best suggestion. Has no
        effect if there are no suggestions.

        If pos is None, the cursor position is used.'''

        pos = pos if pos is not None else self.InsertionPoint
        suggestions = self.GetSuggestionsForPosition(pos)
        if suggestions:
            self.ReplaceWord(pos, suggestions[0])

    # {'word': [1, 56, 34]}

    def SpellCheckLastChange(self, ip = None):
        """
            Figure out a splash area for the last edit and spellcheck everything in it
        """

        # find the start and the end of the possibly relevant area
        val = self.Value
        end = val.find(' ', ip or self.lastinsertion)
        if end != -1: end = val.find(' ', end + 1)
        if end == -1: end = len(val)
        start = val.rfind(' ', 0, end)
        start = val.rfind(' ', 0, start)
        start = max(start, 0)
        start = val.rfind(' ', 0, start)
        start = max(start, 0)

        self.RemoveExpiredSpellError(start, end, value=val)

        # filter out irrelevant words
        span = [word for word in val[start:end].split() if not self.ignore_word(word)]
        words = tokenizer_re.split(' '.join(span))

        # check all the words
        index = start
        for word in words:
            if not word: continue

            word = word.strip(string.punctuation)
            correct = self.Check(word)

            index = val.find(word,index,end)
            if not correct: self.AddSpellError(word, index)
            index += len(word)

        self.needscheck = False

    def AddSuggestionsToMenu(self, menu):
        return add_spelling_suggestions(self, menu)

nonword_characters = string.whitespace + string.punctuation

def add_spelling_suggestions(tc, menu):
    '''
    Adds spelling suggestions to a UMenu.
    '''

    # Grab suggestions from the spell checker.
    position, suggestions = tc.HitTestSuggestions(tc.ScreenToClient(wx.GetMousePosition()))

    # Add a menu item with each suggestion.
    for sug in suggestions:
        if sug != '':
            menu.AddItem(sug, callback = lambda sug=sug: tc.ReplaceWord(position, sug))

    word = tc.GetWordAtPosition(position)

    if word and word in tc.spellerrors:
        menu.AddItem(_('Add to Dictionary'),
                     callback = lambda: tc.AddWordToDictionary(word) if word is not None else None)

        if suggestions:
            menu.AddSep()

    return suggestions


class SpellCheckedTextCtrl(InputBox, SpellCheckTextCtrlMixin):
    def __init__(self, parent,
                       id = wx.ID_ANY,
                       value = '',
                       pos = wx.DefaultPosition,
                       size = wx.DefaultSize,
                       style = 0,
                       validator = wx.DefaultValidator):

        InputBox.__init__(self, parent, id, value, pos, size, style, validator)
        SpellCheckTextCtrlMixin.__init__(self)
        self.Bind(wx.EVT_CONTEXT_MENU, self.__OnContextMenu)

    def __OnContextMenu(self, e):
        from gui.uberwidgets.umenu import UMenu
        from gui.toolbox import std_textctrl_menu

        with UMenu.Reuse(self) as menu:
            self.AddSuggestionsToMenu(menu)
            std_textctrl_menu(self, menu)

