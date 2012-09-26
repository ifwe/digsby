import syck

# this yaml has duplicate keys
# and makes the parser return inconsistent data

fail_yaml ='''
one: two
one: three
four: five
four: six
six: seven
six: eight
'''

def test_syck():
    s = fail_yaml


    for x in xrange(100): # really make sure :)
        assert syck.load(s) == syck.load(s)

if __name__ == '__main__':
    test_syck()
