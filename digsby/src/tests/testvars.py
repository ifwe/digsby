class Model1(object):
    def __init__( self, root = None, expanded = None):
        self.root = root or []
        self.expanded = expanded or []
        self.flattened_list = []
        self.listeners = []
        self.depths = {}
        self.filters = []
        self.donotexpand = []

class Model2(object):
    def __init__( self, root = None, expanded = None):
        vars(self).update(root = root or [],
                          expanded = expanded or [],
                          flattened_list = [],
                          listeners = [],
                          depths = {},
                          filters = [],
                          donotexpand = [])

class Model3(object):
    def __init__( self, root = None, expanded = None):
        self.__dict__.update(root = root or [],
                          expanded = expanded or [],
                          flattened_list = [],
                          listeners = [],
                          depths = {},
                          filters = [],
                          donotexpand = [])

class Model4(object):
    def __init__( self, root = None, expanded = None):
        for key, val in [('root', root or []),
                         ('expanded', expanded or []),
                         ('flattened_list', []),
                         ('listeners', []),
                         ('depths', {}),
                         ('filters', []),
                         ('donotexpand', [])]:
            setattr(self, key, val)

if __name__ == '__main__':
    from timeit import Timer

    print 'Model1', Timer('Model1()', 'from __main__ import Model1').timeit()
    print 'Model2', Timer('Model2()', 'from __main__ import Model2').timeit()
    print 'Model3', Timer('Model3()', 'from __main__ import Model3').timeit()
    print 'Model4', Timer('Model4()', 'from __main__ import Model4').timeit()
