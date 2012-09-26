from tests.testapp import testapp

def test_popupleak():
    from gui.toast import popup
    popup().cancel()

if __name__ == '__main__':
    a = testapp()
    test_popupleak()
    a.MainLoop()