TwitterTest = TestCase('TwitterTest');

TwitterTest.prototype.testAtify = function() {
    function nameLink(name) {
        return '@<a class=\"userLink\" href="http://twitter.com/' + name + '" ' + 
            atifyOnClick + '>' + name + '</a>';
    }

    function testOneName(name) {
        assertEquals(nameLink(name), atify('@' + name));
    }

    testOneName('digsby');
    testOneName('r2d2');
    testOneName('_why');

    assertEquals('Name in a sentence ' + nameLink('elvis') + '.',
                 atify('Name in a sentence @elvis.'));
};

TwitterTest.prototype.testHashify = function() {
    function searchLink(term) {
        return '<a href="http://search.twitter.com/search?q=%23' + term + '">#' + term + '</a>';
    }

    assertEquals(searchLink('hashtag'), hashify('#hashtag'));
    assertEquals(searchLink('with4numbers'), hashify('#with4numbers'));
    assertEquals('http://google.com/#test', hashify('http://google.com/#test'));
    assertEquals('<a href="http://google.com/#test" title="http://google.com/#test">http://google.com/#test</a>', twitterLinkify('http://google.com/#test'));
};

TwitterTest.prototype.testCompareIds = function() {
    assertEquals('comparing 1 and 2', compareIds('1', '2'), -1);
    assertEquals('comparing 2 and 1', compareIds('2', '1'), 1);

    assertEquals('comparing 3 and 3', compareIds('3', '3'), 0);

    assertEquals('checking to see if strip leading strips zeroes', stripLeading('0000123'), '123');

    assertEquals('cmp big to small', 1, compareIds('10705970246197248', '9999625058521088'));
    assertEquals('cmp small to big', -1, compareIds('9999625058521088',  '10705970246197248'));

    assertEquals('cmp number to string', 1, compareIds(5, '4'));
    assertEquals('cmp number to string', -1, compareIds(5, '70'));
    assertEquals('cmp number to string', 0, compareIds(5, '5'));

    assertEquals('cmp number to number', 1, compareIds(5, 3));
}

