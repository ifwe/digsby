/* This file provides the smooth scrolling effect via Javascript. If you don't like it, just delete it! */

//Auto-scroll to bottom.  Use nearBottom to determine if a scrollToBottom is desired.
function nearBottom()
{
    return ( window.pageYOffset >= ( document.body.offsetHeight - ( window.innerHeight * 1.2 ) ) );
}

var intervall_scroll;

function scrollToBottom()
{
    //document.body.scrollTop = (document.body.scrollHeight-window.innerHeight);
    //return;
    if (intervall_scroll) clearInterval( intervall_scroll );
    intervall_scroll = setInterval( function() {
        var target_scroll = document.body.offsetHeight - window.innerHeight;
        var scrolldiff = target_scroll - window.pageYOffset;
        if (window.pageYOffset != target_scroll) {
            var saved_scroll = window.pageYOffset;
            window.scrollTo(window.pageXOffset, window.pageYOffset + (scrolldiff / 5 + ( scrolldiff >= 0 ? (scrolldiff != 0 ) : -1 )));
         } else {
             saved_scroll = -1;
             clearInterval( intervall_scroll );
         }
    } , 10 );
    return;
}
