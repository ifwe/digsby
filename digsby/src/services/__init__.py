'''
Digsby Services

This module is used to detect and load services providers and components that are to be supported by the app.

 * A 'service provider' is a company (or other group) that has a single set of credentials for a given user account.
    For example, Google. Usually though, we'll be referring to the in-app abstraction of this concept, and not to the
    actual remote entity (in code, it may also be referred to as an 'account'). One set of credentials will allow a
    user to access all of their services - chat, mail, g+, maps, etc. The specified credentials should also be unique
    for that service (if correct). Usually this means a unique username, but in some cases more fields may determine
    uniqueness.

    Digsby currently supports the following service providers:
        - AOL
        - Facebook
        - Google
        - LinkedIn
        - MySpace
        - Tagged
        - Twitter
        - Windows Live (aka MSN)
        - Yahoo
        - XMPP (Jabber)
        - POP
        - IMAP

    Note the final three are not companies but are all server software that can be run on nearly any computer. These
    are examples of service providers that may require more than just usernames for uniqueness, depending on server
    configuration.

 * A 'service component' is one of those services - e.g., GMail. We have chosen the name service component in order to
    remain unambiguous. A service provider may have many service components (though it's also technically possible to
    have 0 components), but generally at most one of each type of IM, email, and social are used.

    A user can enable or disable a given component of a service. They should not be required to add any additional
    information to do so - the service provider object should handle everything necessary for account setup. An
    exception is if there is any first-time setup when attempting to connect *any* component of the service. For
    example, when enabling either the IM or social component of a Facebook account, the user must complete OAuth
    authentication - the results of that authentication are stored in the account (service provider).

    Currently supported service components (divided by provider) are:

        AOL: AIM, AOL Mail
        Facebook: Chat, Social Newsfeed
        Google: Mail, Talk
        LinkedIn: Social newsfeed
        MySpace: Chat, Social newsfeed
        Tagged: Social newsfeed
        Twitter: Timeline
        Windows Live: MSN (chat), Hotmail
        Yahoo: Chat, Yahoo Mail
        XMPP: Chat
        POP: mail
        IMAP: mail

Both service providers and service components are implemented as plugins. For examples, see existing plugins. The API
is constantly growing and is not currently documented. (TODO: fix that!)
'''
