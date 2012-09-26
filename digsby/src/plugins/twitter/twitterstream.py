'''
connects to Twitter's streaming API
  http://apiwiki.twitter.com/Streaming-API-Documentation
'''

import netextensions
import common.asynchttp as asynchttp
from common import netcall
from util.primitives.funcs import Delegate
from logging import getLogger; log = getLogger('twstrm')

class TwitterStream(object):
    def __init__(self, username, password, follow_ids):
        self.follow_ids = follow_ids
        self.httpmaster = asynchttp.HttpMaster()

        uris = ['stream.twitter.com', 'twitter.com']
        realm = 'Firehose'
        self.httpmaster.add_password(realm, uris, username, password)

        self.post_data = 'follow=' + ','.join(str(i) for i in follow_ids)

        self.on_tweet = Delegate()

    def start(self):
        url = 'http://stream.twitter.com/1/statuses/filter.json'
        req = asynchttp.HTTPRequest.make_request(url,
                data=self.post_data, method='POST', accumulate_body=False)
        req.bind_event('on_chunk', self._on_chunk)

        log.info('starting twitter stream, following %d people', len(self.follow_ids))
        netcall(lambda: self.httpmaster.request(req))

    def _on_chunk(self, chunk):
        if len(chunk) < 5 and not chunk.strip():
            return # ignore keep alives

        self.on_tweet(chunk)

    def stop(self):
        log.warning('TODO: TwitterStream.stop')

