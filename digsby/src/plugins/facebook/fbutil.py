from hashlib import md5
from util.primitives.error_handling import traceguard, try_this
import logging

def signature(secret, **kw):
    return md5("".join('='.join((str(k),str(v)))
                       for (k,v) in sorted(kw.items()))+secret).hexdigest()

def trim_profiles(stream_dict):
    post_profiles = extract_profile_ids(stream_dict)
    trimmed = set()
    for key in stream_dict['profiles']:
        if key not in post_profiles:
            trimmed.add(key)
    profiles_len = len(stream_dict['profiles'])
    for key in trimmed:
        stream_dict['profiles'].pop(key)
    if len(trimmed):
        log = logging.getLogger('fbutil').info
    else:
        log = logging.getLogger('fbutil').debug
    log('trimmed %d of %d profiles, %d remain', len(trimmed), profiles_len, len(stream_dict['profiles']))
    log('trimmed %r', trimmed)
    log('profiles %r', stream_dict['profiles'].keys())

POST_ID_NAMES = frozenset(('viewer_id', 'actor_id', 'target_id', 'source_id'))

IGNORED = (KeyError, IndexError, TypeError)

def extract_profile_ids(stream):
    ret = set()
    for post in stream['posts']:
        """(SELECT viewer_id FROM #posts)"""
        """(SELECT actor_id FROM #posts)"""
        """(SELECT target_id FROM #posts)"""
        """(SELECT source_id FROM #posts)"""
        for key in POST_ID_NAMES:
            with traceguard:
                try_this(lambda: ret.add(post[key]), ignore = IGNORED)
        """(SELECT likes.sample FROM #posts)"""
        with traceguard:
            try_this(lambda: ret.update(post['likes']['sample']), ignore = IGNORED)
        """(SELECT likes.friends FROM #posts)"""
        with traceguard:
            try_this(lambda: ret.update(post['likes']['friends']), ignore = IGNORED)

    """(SELECT fromid FROM #comments)"""
    for post_comments in stream['comments'].values():
        for comment in post_comments:
            with traceguard:
                try_this(lambda: ret.add(comment['fromid']), ignore = IGNORED)

    """(SELECT sender_id FROM #notifications)"""
    for notification in stream.get('notifications', []):
        with traceguard:
            try_this(lambda: ret.add(notification['sender_id']), ignore = IGNORED)

    return ret

