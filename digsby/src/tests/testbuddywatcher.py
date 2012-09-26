from common.buddy_watcher import BuddyWatcher

def main():
    watcher    = BuddyWatcher()
    messages = ('out to lunch', 'busy right now', 'free for chat', '<3','oh hai can haz cookie?', 'save me jebus')
    states = 'idle away online offline'.split()

    names = 'mario luigi sonic tails batman robin peanutbutter jelly homer marge'.split()

    buddies = [BuddyState() for _ in range(10)]

    for name,buddy in zip(names, buddies):
        buddy.name = name
        watcher.register(buddy)


    from time import sleep
    import random

    for i in range(200):
        buddy = random.choice(buddies)
        oldmsg, oldsta = buddy.message, buddy.status
        buddy.message = random.choice(messages)
        buddy.status = random.choice(states)
        print buddy.name, oldsta, '->', buddy.status, '//', repr(oldmsg), '->', repr(buddy.message or ''),
        watcher.on_change(buddy)
        print

    for buddy in buddies:
        watcher.unregister(buddy)

if __name__ == '__main__':
    main()
