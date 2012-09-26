#original = "Using Digsby to manage IM, Email, and Twitter from one application - http://twitter.digsby.com"
#see ticket #4511

MESSAGES = filter(None, (s.strip() for s in '''
Using Digsby to manage IM, Email, and Twitter from one application - http://bit.ly/VqFb7

Simplify your life with Digsby - http://bit.ly/3Ti1kR

You've gotta check out Digsby - http://bit.ly/gIRnH

One app to rule them all! You've gotta check out Digsby - http://bit.ly/1oLJQH

I just changed my life using Digsby!  Check it out - http://bit.ly/pIFS9

Tweet Tweet. Check out Twitter using Digsby - http://bit.ly/4EiV4D

Ahh, Digsby. Exactly what I've been looking for.  Check it out - http://bit.ly/2MBcxg

Tweeting without Digsby should be illegal.  Give it a try - http://bit.ly/KzSx7

I tweet therefore I dig Digsby (and you will too).  Check it out - http://bit.ly/1gzp06

Saving time with Digsby, one tweet at a time.  Check it out - http://bit.ly/3PTL7y

Keep your life together with Digsby!  Check it out - http://bit.ly/3LX3Z1

Whew! Just got my life together with Digsby. Check it out - http://bit.ly/1ZDuB1

Why didn't someone think of this before?!?  I dig Digsby - http://bit.ly/2U629D

Whew! Finally one place to organize all my online stuff.  Take a look at Digsby - http://bit.ly/QtRX6

Nice! All my social networks in one place! Check out Digsby - http://bit.ly/a40YW

An app this good should be illegal! Check out Digsby - http://bit.ly/23o4DR

4 out of 5 tweetologists say using Digsby increases productivity. That's a no-brainer! http://bit.ly/2jZd3Y

Before there was Digsby, there was only noise.  Reduce the clutter!  Use Digsby! http://bit.ly/3MWCeV

Want to simplify your life? You've gotta check out Digsby - http://bit.ly/3lTmZ0
'''.splitlines()))

def DIGSBY_TWEET_MESSAGE():
    from random import choice
    return choice(MESSAGES)
