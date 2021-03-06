

# the goal is to watch a feed and add it's items
# as nodes

import models as m
import feedparser
import time
import mechanize
import os
from BeautifulSoup import BeautifulSoup as BS

HERE = os.path.dirname(os.path.abspath(__file__))

class Feeder:
    def __init__(self,url):
        self.url = url
        self.seen = []
        self._populate_seen()
        self.browser = mechanize.Browser()
        self.browser.set_handle_robots(False)
        self.reader_logged_in = False

    def log_into_reader(self):
        """ logs into google reader """

        if self.reader_logged_in: return True

        print 'logging into google reader'

        # if we are a google reader url make sure
        # we are logged into google
        with open(os.path.join(HERE,'reader_creds.txt')) as fh:
            username = fh.readline().strip()
            password = fh.readline().strip()

        self.browser.open('https://accounts.google.com/ServiceLoginAuth?continue=http%3A%2F%2Fwww.google.com%2Freader&followup=http%3A%2F%2Fwww.google.com%2Freader&service=reader')
        forms = list(self.browser.forms())
        form = forms[0]
        form['Email'] = username
        form['Passwd'] = password
        # submit our form
        self.browser.open(form.click()) # now we're logged in !
        self.reader_logged_in = True
        return True

    def openurl(self, url):
        """ returns url's html """
        return self.browser.open(url)

    def pull(self):
        """ check the feed for new entries
            and add them as nodes """

        # is it a google reader url?
        if 'google.com/reader' in self.url and not 'public' in self.url:
            self.log_into_reader()

        # get the current feed
        feed = feedparser.parse(self.openurl(self.url))

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
            if not node:
                print 'no node, skipping'
                continue

            if isinstance(node,(list,tuple)):
                nodes += node
            else:
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
            'content': lambda v: v[0].value
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
                        print 'len v: %s' % len(v)
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
            print 'COULD NOT FIND SEEN'

    def _write_seen(self):
        from json import dumps
        with file('./seen.json','w') as fh:
            fh.write(dumps(self.seen))

    def _get_id(self,entry):
        _id = entry.get('id')
        if isinstance(_id,dict):
            _id = _id.get('original-id')
        if not _id:
            if 'content' in entry:
                _id = str(hash(entry.get('content')[0].value))
            elif 'summary' in entry:
                _id = str(hash(entry.get('summary')))
            else:
                _id = str(hash(str(entry)))

        return str(_id)

    def has_seen(self,entry):
        """ return True if we've already
            processed the node """
        return self._get_id(entry) in self.seen

    def mark_seen(self,entry):
        """ update our seen list """
        self.seen.append(self._get_id(entry))

class GFeeder(Feeder):
    """ make sure @nodedrop is mentioned """

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
            'content': lambda v: v[0].value
        }

        # filter for @nodedrop
        if 'content' in entry:
            c = entry.get('content')[0].value
        else:
            c = entry.get('summary')

        c = c.lower()

        if '@nodedrop' not in c:
            return None
        else:
            print 'FOUND @NODEDROP REF'

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
                        print 'len v: %s' % len(v)
                    setattr(node,k,v)
                    break


        return node


class ImageFeeder(Feeder):

    def create_node(self, entry):

        print 'creating entry for: %s' % entry.get('guid')

        # pull the body and pull any images
        soup = BS(entry.get('description',
                  entry.get('content',
                  entry.get('summary'))))
        nodes = []
        for url in self._get_img_urls(entry):
            print 'adding node for: %s' % url
            node = m.SexyLady(img_url=url)
            nodes.append(node)

        return nodes

    def _get_img_urls(self, entry):
        # pull the body and pull any images
        soup = BS(entry.get('description',
                  entry.get('content',
                  entry.get('summary'))))
        urls = []
        for img in soup.findAll('img'):
            urls.append(img.get('src'))
        return urls

    def _id_from_images(self,entry):
        return hash(''.join(self._get_img_urls(entry)))

    def has_seen(self,entry):
        """ return True if we've already
            processed the node """
        u = self._id_from_images(entry)
        return u in self.seen

    def mark_seen(self,entry):
        """ update our seen list """
        u = self._id_from_images(entry)
        self.seen.append(u)

