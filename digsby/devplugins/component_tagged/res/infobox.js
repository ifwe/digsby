/* TODO Fix menu */
newsfeed = $('.tagged-newsfeed');
menu = newsfeed.find('.menu');

elections_feed = newsfeed.find('.elections-feed');
pets_feed = newsfeed.find('.pets-feed');

selected = elections_feed;

$(function() {
    menu.find('.id-button-elections').click(function() {
        selected.hide();
        elections_feed.show();
        selected = elections_feed;
    });

    menu.find('.id-button-pets').click(function() {
        selected.hide();
        pets_feed.show();
        selected = pets_feed;
    });
});