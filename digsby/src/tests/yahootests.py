from yahoo.YahooSocket import to_ydict, from_ydict, argsep
import unittest, string

d = {'1': 'penultimatefire','2': 'some ascii'}
d2= {  1: 'penultimatefire',  2: 'some ascii'}

bytes = '1\xc0\x80penultimatefire\xc0\x802\xc0\x80some ascii\xc0\x80'

class YahooTestingSuite(unittest.TestCase):

    def testYDictConstruction(self):

        str = string.Template("1${a}penultimatefire${a}2${a}some ascii${a}")

        self.assertEqual(to_ydict(d), to_ydict(d2))
        self.assertEqual(to_ydict(d), str.substitute(a=argsep))
        self.assertEqual(to_ydict(d), bytes)

    def testYDictFromNetwork(self):
        self.assertEqual(from_ydict(bytes), [d])
        self.assertEqual(from_ydict(""), {})

if __name__ == "__main__":
    unittest.main()