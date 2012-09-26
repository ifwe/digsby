from tests import TestCase, test_main
import gui.imwin.emoticons as emoticons

class TestEmoticons(TestCase):
    def test_quotes(self):
        from pprint import pprint
        pack = 'Yahoo Messenger'
        pprint(emoticons.load_pack(pack).emoticons)

        def success(emot):
            self.assertTrue('img src' in emoticons.apply_emoticons(emot, pack))

        success(':)')
        success('>:)')
        success(':-"')
        success(':-&quot;')
        success('&gt;:)')

if __name__ == '__main__':
    test_main()
