from tests import TestCase, test_main

import lxml.html
from util.htmlutils import to_xhtml, remove_tags, remove_attrs, render_contents, remove_styles, transform_text


class TestStripFormatting(TestCase):
    'test HTML transformations'

    def test_html_and_body_tag_removed(self):
        'test AIM-style html junk removal'

        # tuples of (input, expected_output)
        fragments = [
            (u'<html><body bgcolor="#ff0000"><b>red <i>text</i></b></body></html>',
             u'<span style="background-color: #ff0000;"><b>red <i>text</i></b></span>'),

            (u'<html><body>test</body></html>', u'test'),
            (u'<html>bare html</html>', u'bare html'),
        ]

        for original, expected in fragments:
            transformed = to_xhtml(original)
            self.expect_equal(expected, transformed)

    def test_html_unharmed(self):
        'test that some text fragments remain untransformed'
        
        # these shouldn't change
        fragments = [
            '<b>test</b>',
            '<i>test</i>',
            'test',
            '     ',
            '',
            'test &amp; test',
        ]

        for fragment in fragments:
            transformed = to_xhtml(fragment)
            self.expect_equal(fragment, transformed)

    def test_remove_tags(self):
        'test removing tags'

        # (tags to remove, input string, expected)
        fragments = [
            (('b',),     '<b>test</b>', 'test'),
            (('b',),     '<i>test</i>', '<i>test</i>'),
            (('b', 'i'), '<b>test <i>foo</i></b>', 'test foo'),
            ((),         '<b><i>test</i></b>', '<b><i>test</i></b>'),
        ]

        for tagnames, fragment, expected in fragments:
            tree = string_to_tree(fragment)
            transformed = remove_tags(tree, tagnames)
            self.expect_equal(expected, tree_to_string(tree))

    def test_remove_attrs(self):
        'test removing attributes'

        tests = [
            (('bgcolor',),  '<font bgcolor="#ff0000">red</font>', '<font>red</font>'),
            (('bgcolor',),  '<font fgcolor="#0000ff" bgcolor="#ff0000">red</font>', '<font fgcolor="#0000ff">red</font>'),
            (('bgcolor',),  'wut', 'wut'),
        ]

        for attrs, inp, expected in tests:
            tree = string_to_tree(inp)
            remove_attrs(tree, attrs)
            transformed = tree_to_string(tree)
            self.expect_equal(expected, transformed)

    def test_remove_styles(self):
        'test removing styles'

        # (style to remove, input, expected)
        tests = [
            (('background-color',),
             '<span style="background-color: red;">foo</span>',
             '<span style="">foo</span>',
            ),
            (('background-color',),
             '<span style="background-color: red; font-weight: bold;">foo</span>',
             '<span style="font-weight: bold;">foo</span>',
            ),
            (('foo',), 'abc', 'abc'),
        ]

        for styles, inp, expected in tests:
            tree = string_to_tree(inp)
            remove_styles(tree, styles)
            transformed = tree_to_string(tree)
            self.expect_equal(expected, transformed)

    def test_transform_text(self):
        'test transforming text nodes'

        # (transform function, input, expected)
        tests = [
            (str.upper,
             '<b>test <i>more test</i></b>',
             '<b>TEST <i>MORE TEST</i></b>'),
            ((lambda s: s),
             '<b>test<i>test</i></b>',
             '<b>test<i>test</i></b>',),
            (str.upper, '', ''),
        ]

        for func, inp, expected in tests:
            tree = string_to_tree(inp)
            transform_text(tree, func)
            self.expect_equal(expected, tree_to_string(tree))

def string_to_tree(s):
    return lxml.html.fragment_fromstring('<wrapper>' + s + '</wrapper>')

def tree_to_string(tree):
    return render_contents(tree)


if __name__ == '__main__':
    test_main()

