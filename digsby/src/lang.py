import ctypes
from ctypes import byref
import os

MUI_LANGUAGE_ID = 4
MUI_LANGUAGE_NAME = 8

if os.name == 'nt':
    def get_preferred_languages():
        GetUserPreferredUILanguages = ctypes.windll.kernel32.GetUserPreferredUILanguages
        num_languages = ctypes.c_ulong()
        buffer_length = ctypes.c_ulong()
        if GetUserPreferredUILanguages(
            MUI_LANGUAGE_NAME,
            byref(num_languages),
            None,
            byref(buffer_length)) and buffer_length.value:

            buffer = ctypes.create_unicode_buffer(buffer_length.value)

            if GetUserPreferredUILanguages(
                MUI_LANGUAGE_NAME,
                byref(num_languages),
                byref(buffer),
                byref(buffer_length)) and 0 != num_languages.value:

                langlist = wszarray_to_list(buffer)
                assert num_languages.value == len(langlist)
                return langlist

def wszarray_to_list(array):
    '''
    >> wszarray_to_list(ctypes.create_unicode_buffer(u'string1\0string2\0string3\0\0'))
    [u'string1', u'string2', u'string3']
    '''

    offset = 0
    l = []
    while offset < ctypes.sizeof(array):
        sz = ctypes.wstring_at(ctypes.addressof(array) + offset*2)
        if sz:
            l.append(sz)
            offset += len(sz)+1
        else:
            break

    return l

if __name__ == '__main__':
    print get_preferred_languages()

