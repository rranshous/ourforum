#!/usr/bin

# we are going to feed on some motha f'n feeds!
#!/usr/bin/python
import sys
from time import sleep
from lib.memcache import default_client as memcache_client
import models as m; m.setup()

# who will be feasting tonight ?
from tools import GFeeder as THEMONSTER

SLEEP_TIME = 30

def run(the_monster=None):

    if not the_monster:
        the_monster = THEMONSTER(None)

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
            the_monster.url = url

            # FEAST
            remains = the_monster.pull() # (nom nom nom)

            # on whom did we we feast?
            for mangled_mess in remains:

                # if the node's content has a blockquote b/c it was commented
                # on in greader lets strip that out as it's own comment node
                if mangled_mess.body.startswith('<blockquote'):
                    pieces = mangled_mess.body.split('</blockquote>')
                    mangled_mess.body = ''.join(pieces[1:])
                    comment = m.Comment(title="shared from greader")
                    _comment = pieces[0][len('<blockquote>'):]
                    _comment = '\n'.join(_comment.split('\n')[2:])
                    comment.comment = _comment
                    print 'comment: %s' % _comment
                    mangled_mess.relatives.append(comment)

                mangled_mess.relatives.append(user.get_author())

    m.session.commit()
    memcache_client.incr('key_counter')

if __name__ == '__main__':
    continuous = True
    the_monster = THEMONSTER(None)
    while continuous:
        run(the_monster)
        continuous = 'continuous' in sys.argv
        if continuous:
            sleep(SLEEP_TIME)
