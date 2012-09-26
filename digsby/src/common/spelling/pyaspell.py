# -*- coding: iso-8859-2 -*-
# Aspell interface using ctypes.
# $Date: 2007-04-07 14:27:33 $, $Revision: 1.3 $
#
# This is straightforward translation of my
# aspell-python, C extension.
#
# License: BSD
#
# author: Wojciech Mu?a
# e-mail: wojciech_mula@poczta.onet.pl
# www   : http://wmula.republika.pl/proj/aspell-python/
#
# TODO: add method to get/change **current** speller's config

try:
    import ctypes
    import ctypes.util
except ImportError:
    raise ImportError("ctypes library is needed")


class AspellError(Exception): pass
class AspellConfigError(AspellError): pass
class AspellSpellerError(AspellError): pass


class Aspell(object):
    """
    Aspell speller object.  Allows to check spelling, get suggested
    spelling list, manage user dictionarias, and other.

    Must be closed with 'close' method, or one may experience
    problems, like segfaults.
    """

    VERSION = 5 # must be in (5,6)

    if VERSION == 5:
        LIBNAME = 'aspell\\bin\\aspell-15'
    elif VERSION == 6:
        LIBNAME = 'aspell\\bin\\aspell'
    def __init__(self, configkeys=None, libname=None, **kwds):
        """
        Parameters:
        * configkeys - list of configuration parameters;
          each element is a pair key & value (both strings)
          if None, then default configuration is used
        * libname - explicity set aspell library name;
          if None then default name is used
        """
        if libname is None:
            libname = ctypes.util.find_library(self.LIBNAME)
        self.__lib = ctypes.CDLL(libname)
        self.libname = libname

        # Initialize speller

        # 1. create configuration
        config = self.__lib.new_aspell_config()
        if config == None:
            raise AspellError("Can't create aspell config object")

        # 2. parse configkeys arg.
        if configkeys:
            assert type(configkeys) in (tuple, list, dict), "Tuple, list, or dict expected"
            if hasattr(configkeys, 'items'):
                configkeys = configkeys.items()

            if len(configkeys) == 2 and \
               type(configkeys[0]) is str and \
               type(configkeys[1]) is str:
                configkeys = [configkeys]

            configkeys = dict(configkeys)
        else:
            configkeys = {}

        configkeys.update(kwds)
        configkeys = configkeys.items()

        for key, value in configkeys:
            assert type(key) is str, "Key must be string: %r" % key
            assert type(value) is str, "Value must be string: %r" % value
            if not self.__lib.aspell_config_replace(config, key, value):
                raise self._aspell_config_error(config)

        # 3. create speller
        possible_error = self.__lib.new_aspell_speller(config)
        self.__lib.delete_aspell_config(config)

        errno = self.__lib.aspell_error_number(possible_error)
        #errmsg = self.__lib.aspell_error_message(errno)
        if errno != 0:
            errmsg = ctypes.string_at(self.__lib.aspell_error_message(possible_error))
            self.__lib.delete_aspell_can_have_error(possible_error)
            raise AspellError(errno, errmsg)

        self.__speller = self.__lib.to_aspell_speller(possible_error)

    def check(self, word):
        """
        Check if word is present in main, personal or session
        dictionary.  Boolean value is returned
        """
        if type(word) is str:
            return bool(
                self.__lib.aspell_speller_check(
                    self.__speller,
                    word,
                    len(word)
                ))
        else:
            raise TypeError("String expeced")


    def suggest(self, word):
        """
        Return list of spelling suggestions of given word.
        Works even if word is correct.
        """
        if type(word) is str:
            return self._aspellwordlist(
                self.__lib.aspell_speller_suggest(
                    self.__speller,
                    word,
                    len(word)
                ))
        else:
            raise TypeError("String expeced")


    def personal_dict(self, word=None):
        """
        Aspell's personal dictionary is a user defined, persistent
        list of word (saved in certain file).

        If 'word' is not given, then method returns list of words stored in
        dict.  If 'word' is given, then is added to personal dict.  New words
        are not saved automatically, method 'save_all' have to be call.
        """
        if word is not None:
            # add new word
            assert type(word) is str, "String expeced"
            self.__lib.aspell_speller_add_to_personal(
                self.__speller,
                word,
                len(word)
            )
            self._aspell_check_error()
        else:
            # return list of words from personal dictionary
            return self._aspellwordlist(
                self.__lib.aspell_speller_personal_word_list(self.__speller)
            )


    def session_dict(self, word=None, clear=False):
        """
        Aspell's session dictionary is a user defined, volatile
        list of word, that is destroyed with aspell object.

        If 'word' is None, then list of words from session dictionary
        is returned.  If 'word' is present, then is added to dict.
        If 'clear' is True, then session dictionary is cleared.
        """
        if clear:
            self.__lib.aspell_speller_clear_session(self.__speller)
            self._aspell_check_error()
            return


        if word is not None:
            # add new word
            assert type(word) is str, "String expeced"
            self.__lib.aspell_speller_add_to_session(
                self.__speller,
                word,
                len(word)
            )
            self._aspell_check_error()
        else:
            # return list of words from personal dictionary
            return self._aspellwordlist(
                self.__lib.aspell_speller_session_word_list(self.__speller)
            )


    def add_replacement_pair(self, misspelled, correct):
        """
        Add replacement pair, i.e. pair of misspelled and correct
        word.  It affects on order of words appear on list returned
        by 'suggest' method.
        """
        assert type(misspelled) is str, "String is required"
        assert type(correct) is str, "String is required"

        self.__lib.aspell_speller_store_replacement(
            self.__speller,
            misspelled,
            len(misspelled),
            correct,
            len(correct)
        )
        self._aspell_check_error()


    def save_all(self):
        """
        Saves all words added to personal or session dictionary to
        the apell's defined file.
        """
        self.__lib.aspell_speller_save_all_word_lists(self.__speller)
        self._aspell_check_error()


    def configkeys(self):
        """
        Returns list of all available config keys that can be passed
        to contructor.

        List contains a 3-tuples:
        1. key name
        2. default value of type:
           * bool
           * int
           * string
           * list of string
        3. short description
           if None, then this key is undocumented is should not
           be used, unless one know what really do
        """

        config = self.__lib.aspell_speller_config(self.__speller)
        if config is None:
            raise AspellConfigError("Can't get speller's config")

        keys_enum = self.__lib.aspell_config_possible_elements(config, 1)
        if keys_enum is None:
            raise AspellError("Can't get list of config keys")

        class KeyInfo(ctypes.Structure):
            _fields_ = [
                ("name",    ctypes.c_char_p),
                ("type",    ctypes.c_int),
                ("default",    ctypes.c_char_p),
                ("desc",    ctypes.c_char_p),
                ("flags",    ctypes.c_int),
                ("other_data", ctypes.c_int),
            ]

        key_next = self.__lib.aspell_key_info_enumeration_next
        key_next.restype = ctypes.POINTER(KeyInfo)

        list = []
        while True:
            key_info = key_next(keys_enum)
            if not key_info:
                break
            else:
                key_info = key_info.contents

            if key_info.type == 0:
                # string
                list.append((
                    key_info.name,
                    key_info.default,
                    key_info.desc,
                ))

            elif key_info.type == 1:
                # integer
                list.append((
                    key_info.name,
                    int(key_info.default),
                    key_info.desc,
                ))
            elif key_info.type == 2:
                # boolean
                if key_info.default.lower() == 'true':
                    list.append((
                        key_info.name,
                        True,
                        key_info.desc,
                    ))
                else:
                    list.append((
                        key_info.name,
                        False,
                        key_info.desc,
                    ))
            elif key_info.type == 3:
                # list
                list.append((
                    key_info.name,
                    key_info.default.split(),
                    key_info.desc,
                    ))

        self.__lib.delete_aspell_key_info_enumeration(keys_enum)
        return list

    def reset_cache(self):
        return self._reload_lib() #self.__lib.aspell_reset_cache()

    def close(self):
        """
        Close aspell speller object.
        """
        self.__lib.delete_aspell_speller(self.__speller)

    def _reload_lib(self):
        from _ctypes import LoadLibrary as _LoadLibrary, FreeLibrary as _FreeLibrary
        if self.__lib._handle != 0:
            _FreeLibrary(self.__lib._handle)
            del self.__lib
            self.__lib = ctypes.CDLL(self.libname)

    # XXX: internal function, do not call directly
    def _aspellwordlist(self, wordlist_id):
        """
        XXX: internal function

        Converts aspell list into python list.
        """
        elements = self.__lib.aspell_word_list_elements(wordlist_id)
        list = []
        while True:
            wordptr = self.__lib.aspell_string_enumeration_next(elements)
            if not wordptr:
                break
            else:
                word = ctypes.c_char_p(wordptr)
                list.append(word.value)

        self.__lib.delete_aspell_string_enumeration(elements)
        return list


    def _aspell_config_error(self, config):
        """
        XXX: internal function

        Raise excpetion if operation of speller config
        caused an error.  Additionaly destroy config object.
        """
        # make exception object & copy error msg
        exc = AspellConfigError(
            ctypes.c_char_p(
                self.__lib.aspell_config_error_message(config)
            ).value
        )

        # then destroy config objcet
        self.__lib.delete_aspell_config(config)

        # and then raise exception
        raise exc


    def _aspell_check_error(self):
        """
        XXX: internal function

        Raise exception if previous speller operation
        caused an error.
        """
        if self.__lib.aspell_speller_error(self.__speller) != 0:
            msg = self.__lib.aspell_speller_error_message(self.__speller)
            raise AspellSpellerError(ctypes.string_at(msg))
#class

_test_basic = '''\
>>> a = Aspell(('lang', 'en'))
>>> a.check("when")
True
>>> set(a.suggest("wehn")) == set(['when', 'wen', 'wean', 'ween', 'Wehr', 'whens', 'hen'])
True
>>> a.add_replacement_pair("wehn", "ween")
>>> set(a.suggest("wehn")) == set(['ween', 'when', 'wen', 'wean', 'Wehr', 'whens', 'hen'])
True
>>> a.session_dict() == []
True
>>> a.check("pyaspell")
False
>>> a.session_dict("pyaspell")
>>> a.session_dict() == ['pyaspell']
True
>>> a.check("pyaspell")
True
>>> a.session_dict(clear=True)
>>> a.session_dict()
[]
>>> a.close()'''
_test_locales = '''\
>>> # Locales
>>> a1 = Aspell(('lang', 'en-us'))
>>> a2 = Aspell(('lang', 'en-gb'))
>>> (a1.check('localize'), a2.check('localize')) == (True, False)
True
>>> (a1.check('localize'), a2.check('localize')) == (True, False)
True
>>> (a1.check('localise'), a2.check('localise')) == (False, True)
True
>>> (a1.suggest('localise')[0], a2.suggest('localize')[0]) == ('localize', 'localise')
True
>>> a1.close()
>>> a2.close()'''
_test_case = '''\
>>> # Case sensitivity
>>> a1 = Aspell(('ignore-case',''))
>>> a2 = Aspell(('dont-ignore-case', ''))
>>> (a1.check('steve'), a2.check('steve')) == (True, False)
True
>>> (a1.check('Steve'), a2.check('Steve')) == (True, True)
True
>>> a1.close()
>>> a2.close()'''

__test__ = dict(
                basic=_test_basic,
                locales = _test_locales,
                case = _test_case,
                )

def _test():
    import doctest
    doctest.testmod(verbose=True)


if __name__ == '__main__':
    #_test()
    Aspell(('lang', 'fake'))

# vim: ts=4 sw=4
