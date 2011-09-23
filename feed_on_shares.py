#!/usr/bin

# we are going to feed on some motha f'n feeds!
#!/usr/bin/python

from lib.memcache import default_client as memcache_client
import models as m; m.setup()

# who will be feasting tonight ?
from tools import Feeder as THEMONSTER

if __name__ == '__main__':

    # go through the users, devouring, drooling
    # slashing, consuming
    users = m.User.query.all()

    # come to me my precious
    for user in users:

        print 'the monster has spotted %s' % user.handle

        # for now the feed urls attribute is semi-colon seperated urls
        for url in [u.strip() for u in user.feed_urls.split(';')]:

            if not url:
                continue

            print 'let the feast begin! %s' % url

            # get ready
            feast = THEMONSTER(url)

            # FEAST
            remains = feast.pull() # (nom nom nom)

            # on whom did we we feast?
            for mangled_mess in remains:
                mangled_mess.relatives.append(user.get_author())

    m.session.commit()
    memcache_client.incr('key_counter')
