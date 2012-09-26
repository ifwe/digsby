from collections import defaultdict
from weakref import WeakValueDictionary
from pprint import pprint

class Resource(object):
    _idhash = WeakValueDictionary()

    def __new__(cls, *a, **k):
        print 'id', a[0]

        instance = super(Resource, cls).__new__(cls, *a, **k)



    def __init__(self, name, value):
        self.name = name
        self.value = value

    @staticmethod
    def from_id(id, *a, **k):
        try:
            r = Resource._idhash[id]
        except KeyError:
            r = Resource._idhash[id] = Resource(*a, **k)
            r.id = id
            return r
        else:
            r.__init__(*a, **k)
            return r

    def __repr__(self):
        return '<%s #%d>' % (self.__class__.__name__, self.id)



if __name__ == '__main__':
    one = Resource(5, 'myResource', 15)
    two = Resource(10, 'other', 20)
    three = Resource(5, 'yet another', 25)

    print one, two, three
    print one is three

    print one.test()