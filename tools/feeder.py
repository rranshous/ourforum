

# the goal is to watch a feed and add it's items
# as nodes

import models as m
import feedparser
import time

class Feeder:
    def __init__(self,url):
        self.url = url
        self.seen = []
        self._populate_seen()

    def pull(self):
        """ check the feed for new entries
            and add them as nodes """
        # get the current feed
        feed = feedparser.parse(self.url)

        nodes = []
        # go through the entries possibly adding them
        for entry in feed.get('entries',[]):
            # check and see if we've seen this
            # entry before
            if self.has_seen(entry):
                continue

            # since we haven't seen it we should
            # add it
            node = self.create_node(entry)
            nodes.append(node)

            # now note that we've seen it
            self.mark_seen(entry)

        # now that we've seen what we've come
        # to see lets update our file
        self._write_seen()

        return nodes

    def create_node(self,entry):
        """ takes an entry and creates a
            FeedEntry node """
        attr_lookup = {
            'source':('link',),
            'body':('content','summary'),
            'title':('title',),
            'timestamp':('updated_parsed','updated')
        }
        value_modifiers = {
            'updated_parsed': lambda v: time.asctime(v),
            'content': lambda v: v[0].get('value')
        }
        # now we try and create our node
        # go through the attribute lookup
        # trying to fill in params
        node = m.FeedEntry()
        for k, attrs in attr_lookup.iteritems():
            for attr in attrs:
                if entry.get(attr):
                    v = entry.get(attr)
                    if attr in value_modifiers:
                        v = value_modifiers.get(attr)(v)
                        print 'v: %s' % v
                    setattr(node,k,v)
                    break


        return node

    def _populate_seen(self):
        from json import loads
        # update the list of entries we've seen
        # it lives on the drive as a giant json file
        try:
            with file('./seen.json','r') as fh:
                self.seen = loads(fh.read())
        except:
            pass

    def _write_seen(self):
        from json import dumps
        with file('./seen.json','w') as fh:
            fh.write(dumps(self.seen))

    def has_seen(self,entry):
        """ return True if we've already
            processed the node """
        return entry.get('id','UNKNOWN') in self.seen

    def mark_seen(self,entry):
        """ update our seen list """
        self.seen.append(entry.get('id','UNKNOWN'))
