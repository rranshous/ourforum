#!/usr/bin/python

from lib.memcache import default_client as memcache_client
import models as m; m.setup()

# who will be feasting tonight ?
from tools import ImageFeeder as Feeder

if __name__ == '__main__':

    # go through SexyLadyFeeds
    feeds = m.SexyLadyFeed.query.all()

    # come to me my precious
    for feed in feeds:

        print 'feed: %s' % feed.url

        # for now the feed urls attribute is semi-colon seperated urls
        for url in [u.strip() for u in feed.url.split(';')]:

            if not url:
                continue

            print 'parsing: %s' % url

            # get ready
            tramp = Feeder(url)

            # FEAST
            sexies = tramp.pull() # (nom nom nom)

            print 'created %s entries' % len(sexies)

    #m.session.commit()
    #memcache_client.incr('key_counter')
