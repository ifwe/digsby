try:
    _
except NameError:
    _ = lambda s: s

class SupportMechanism(object):
    action_text = None # "button label"
    description = None # 'Short description'
    tooltip = None     # 'perhaps a longer description of how this helps digsby'
    action_url = None  # url to open in browser
    say_thanks = False # do alert dialog that says "thanks" ?

    confirm = False    # ask if they're sure
    confirm_text = None    # how to ask
    confirm_title = None   # title for message box
    confirm_default = True # default for confirmation

    def on_action(self):
        pass

class SearchHomepage(SupportMechanism):
    action_text = _('Set')
    description = _('Make Google Powered Digsby Search your homepage')
    say_thanks = True

    def on_action(self):
        # set digsby homepage or set the file marker and trigger the home-page-setter thingy
        import hooks
        hooks.notify("digsby.browsersettings.set_homepage")

class SearchEngine(SupportMechanism):
    action_text = _('Set')
    description = _('Make Google Powered Digsby Search your default search engine')
    say_thanks = True

    def on_action(self):
        # set digsby search engine or set the file marker and trigger the search-engine-setter thingy
        import hooks
        hooks.notify("digsby.browsersettings.set_search")

class EmailInviter(SupportMechanism):
    action_text = _('Invite')
    description = _('Invite your friends via Email')
    action_url = 'http://www.digsby.com/invite/'

class FacebookInviter(SupportMechanism):
    action_text = _('Invite')
    description = _('Invite your friends via Facebook')
    action_url = 'http://apps.facebook.com/digsbyim/invite.php'

class FacebookFan(SupportMechanism):
    action_text = _('Join Group')
    description = _('Become a fan on Facebook')
    action_url = 'http://www.facebook.com/apps/application.php?id=5895217474'

class LinkedInFan(SupportMechanism):
    action_text = _('Join Group')
    description = _('Become a fan on LinkedIn')
    action_url = 'http://www.linkedin.com/groups?gid=911917'

class TwitterFollow(SupportMechanism):
    action_text = _('Follow')
    description = _('Follow us on Twitter')
    action_url = 'http://www.twitter.com/digsby'

class Research(SupportMechanism):
    description = _('Help Digsby conduct research')

    confirm = False
    confirm_text = _("Helping us conduct research keeps Digsby free and ad-free. Are you sure you want to disable this option?")
    confirm_title = _("Are you sure?")
    confirm_default = False

    help_link = 'http://wiki.digsby.com/doku.php?id=cpuusage'

    def should_confirm(self):
        import common
        return common.profile.localprefs['research.enabled']

    def _get_action_text(self):
        import common
        if common.profile.localprefs['research.enabled']:
            return _('Disable')
        else:
            return _('Enable')

    action_text = property(_get_action_text)

    def on_action(self):
        import common
        common.profile.localprefs['research.enabled'] = not common.profile.localprefs['research.enabled']

class BlogSubscribe(SupportMechanism):
    action_text = _('Subscribe')
    description = _('Subscribe to our Blog')
    action_url = 'http://blog.digsby.com/feed'

class CreateWidget(SupportMechanism):
    action_text = _('Create')
    description = _('Create a Digsby widget for your blog or website')
    action_url = 'http://widget.digsby.com/'

class IncrementCounter(SupportMechanism):
    def _get_action_text(self):
        return 'Set to %r' % (getattr(self, 'counter', 0) + 1)

    def _get_description(self):
        return 'Increment this number: %r' % getattr(self, 'counter', 0)

    action_text = property(_get_action_text)
    description = property(_get_description)

    def on_action(self):
        setattr(self, 'counter', getattr(self, 'counter', 0) + 1)

class TextElongonator(SupportMechanism):
    action_text = 'More!'
    description = 'Add dashes to this text label '

    def on_action(self):
        self.description += '-'

enabled = [
           #TextElongonator,
           #IncrementCounter,
           SearchHomepage,
           EmailInviter,
           FacebookInviter,
           FacebookFan,
           LinkedInFan,
           TwitterFollow,
           #Research,
           BlogSubscribe,
           CreateWidget,
           ]

def get_enabled():
    import common
    myenabled = enabled[:]
    if common.pref('support.show_research_option', type = bool, default = False):
        if Research not in myenabled:
            myenabled.insert(-2, Research)

    return myenabled
