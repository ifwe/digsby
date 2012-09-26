from gui.imwin.styles import MessageStyle

class BasicMessageStyle(MessageStyle):
    '''
    A backup message style to use if no styles can be found on disk.
    '''

    template = \
'''<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <script type="text/ecmascript" defer="defer">

        //Appending new content to the message view
        function appendMessage(html) {
            shouldScroll = nearBottom();

            //Append the new message to the bottom of our chat block
            chat = document.getElementById("Chat");
            range = document.createRange();
            range.selectNode(chat);
            documentFragment = range.createContextualFragment(html);
            chat.appendChild(documentFragment);

            alignChat(shouldScroll);
        }

        function alignChat(shouldScroll) {
            var windowHeight = window.innerHeight;

            if (windowHeight > 0) {
                var contentElement = document.getElementById('Chat');
                var contentHeight = contentElement.offsetHeight;
                if (windowHeight - contentHeight > 0) {
                    contentElement.style.position = 'relative';
                    contentElement.style.top = (windowHeight - contentHeight - 10) + 'px';
                } else {
                    contentElement.style.position = 'static';
                }
            }

            if (shouldScroll) scrollToBottom();
        }

        function nearBottom() {
            return ( document.body.scrollTop >= ( document.body.offsetHeight - ( window.innerHeight * 1.2 ) ) );
        }
        function scrollToBottom() {
            document.body.scrollTop = document.body.offsetHeight;
        }

        function windowDidResize(){
            alignChat(true/*nearBottom()*/); //nearBottom buggy with inactive tabs
        }

        window.onresize = windowDidResize;
    </script>
    <style type="text/css">
        span.buddyname { font-size: 60%; font-family: Verdana; background-color: #efefef; }
    </style>
    </head>
<body>
<div id="Chat">
</div>
</body>
</html>

'''

    theme_name = 'basic'
    variant = None
    baseUrl = 'file:///'
    allow_text_colors = True

    def initialContents(self, chatName, buddy, header = False, prevent_align_to_bottom=False):
        return self.template

    def show_header_script(self, show):
        return ''

    def format_message(self, messagetype, messageobj, next, context, **extra):
        if messageobj.buddy is not None:
            return 'appendMessage', u'<div><span class="buddyname">%s</span>: %s</div>' % (messageobj.buddy.name, messageobj.message)
        else:
            return 'appendMessage', u'<div>%s</div>' % messageobj.message
