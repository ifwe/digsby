#__LICENSE_GOES_HERE__
# -*- coding: utf-8 -*-
from __future__ import with_statement #@UnresolvedImport
from i18n.generate_monolithic import POT_DIR
import sys
import os.path
from babel.messages.pofile import read_po
from path import path


final_pot = path(POT_DIR) / 'digsby' / 'digsby.pot'
digsby_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
leet_pot = os.path.join(digsby_root, 'devplugins', 'l33t_language', 'digsby-lt.po')

interesting = [' ', '\n', '\t']
def teststr(s):
    '''
    return bool(s is interesting)
    '''
    for i in interesting:
        if s.endswith(i) or s.startswith(i) or i*2 in s:
            return True

def _test(message):
    '''
    helper function for plural forms; delegates to teststr()
    '''
    if isinstance(message.id, tuple):
        return teststr(message.id[0]) or teststr(message.id[1])
    return teststr(message.id)

def remove_template_problems(fpath):
    '''
    babel doesn't like the template values for the Plural-Forms,
    nor for the charset in Content-Type.
    since the values for templates are the defaults,
    we filter/correct those
    '''
    from StringIO import StringIO
    with open(fpath) as final:
        lines = final.readlines()
        lines = filter(lambda l: not l.startswith('"Plural-Forms: '), lines)
        lines2 = []
        for line in lines:
            if line == '"Content-Type: text/plain; charset=CHARSET\\n"\n':
                lines2.append('"Content-Type: text/plain; charset=UTF-8\\n"\n')
                continue
            lines2.append(line)
        lines = lines2
        return StringIO(''.join(lines))

def eclipse_path(loc):
    path, lineno = loc
    return '  File "%s", line %s' % (os.path.join(digsby_root, path), lineno)

def _show_message(message):
    print >> sys.stderr, message.id
    for loc in message.locations:
        print >> sys.stderr, eclipse_path(loc)
    print >> sys.stderr, '-'*80

def show_interesting():
    catalog = read_po(remove_template_problems(final_pot))
    for key, message in catalog._messages.items():
        if _test(message):
            _show_message(message)
#        if not message.context:
#            continue
#        if len(message.locations) < 2:
#            continue
#        print repr(key)#, repr(message.id),  message.locations

def _messages_with_mark(pofile_path):
    catalog = read_po(remove_template_problems(pofile_path))
    for message in catalog:
        if 'MARK' in ''.join(comment for comment in message.user_comments):
            yield message

def show_marks(pofile_path):
    '''
    parses the PO file at the given path, and prints to stderr each message
    commented with a MARK
    '''
    count = 0
    for message in _messages_with_mark(pofile_path):
        print >> sys.stderr, '(%s) %s' % ('\n'.join(message.user_comments).replace('MARK: ', ''), message.lineno)
        _show_message(message)
        count += 1
    print count

def save_marks(pofile_path):

    count = 0

    with open('marksfile.txt', 'wb') as marksfile:
        for message in _messages_with_mark(pofile_path):
            marksfile.write('%s: %s %s\n\t\t"%s"\n\n' % (message.lineno, '\n'.join(message.user_comments).replace('MARK: ', ''), message.locations, message.id))
            count += 1

    print count
if __name__ == "__main__":
    #show_interesting()
    save_marks(leet_pot)
