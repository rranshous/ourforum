from ConfigParser import ConfigParser
import fnmatch
import os
from mako.template import Template
from functools import partial
from types import MethodType
import json
from pyexiv2 import Image
import re

# read in the config
config = ConfigParser()
config.read('development.ini')
_config = {}
# i prefer using a normal dict for lookups
for section in config.sections():
    _config[section] = {}
    for k,v in config.items(section):
        _config[section][k] = v
_config.update(config.defaults())
config = _config


# ty: http://stackoverflow.com/questions/2186525/use-a-glob-to-find-files-recursively-in-python
def recursive_find(root,patterns):
    if type(patterns) not in (tuple,list):
        patterns = [patterns]
    patterns = [re.compile(pattern) for pattern in patterns]
    matches = []
    for root, dirnames, filenames in os.walk(root):
        file_matches = _recursive_find(filenames,patterns)
        matches += [os.path.join(root,m) for m in file_matches]
    return matches

def _recursive_find(filenames,patterns):
    m = []
    for p in patterns:
        m += [x for x in filenames if p.match(x)]
    return m


def read_map(map_path):
    # we are going to read in the map as json
    try:
        lookup = json.load(open(map_path,'r'))
    except IOError: # no existing file
        lookup = {}
    except ValueError: # can't deserialize
        lookup = {}
    return lookup

def get_map():
    """ return default map as read from config """
    map_path = config.get('map_path')
    return read_map(map_path)

def get_renderer(name):
    root = config.get('template_root')
    path = os.path.join(root,'%s.mako' % name)
    template = Template(filename=path)
    # we are going to decorate the templates
    # render method to make the config available
    _r = partial(template.render,
                    config=config,
                    get_media_page_url=get_media_page_url,
                    get_media_url=get_media_url)
    return _r

IMAGE_COMMENT_TAG = 'Exif.Image.ImageDescription'
COMMENT_DELIMINATOR = '\n\n'
def get_image_comments(path):
    image = Image(path)
    image.readMetadata()
    comments = image.getComment()
    if not comments:
        return []
    pieces = comments.split(COMMENT_DELIMINATOR)
    comments = []
    print 'getting:',path
    for piece in pieces:
        data = {}
        sub_pieces = [x.strip() for x in piece.split(':') if x.strip()]
        # the first piece (if there is more than one)
        # is the label. if there is only one it's the body

        if len(sub_pieces) == 0:
            continue
        elif len(sub_pieces) == 1:
            body = data.get('body','')
            body += ('\n' if body else '') + sub_pieces[0]
            data['body'] = body
        else:
            # first is going to be the label w/
            # possible sub labels
            if '[' in sub_pieces[0]:
                label = sub_pieces[0].split('[')[0]
                data['label'] = label
                sub_labels = sub_pieces[0][len(label):]
                sub_labels = sub_labels.replace('[')
                # the last one will be blank
                sub_labels = sub_labels.split(']')[:-1]
                data['sub_labels'] = sub_labels
            else:
                data['label'] = sub_pieces[0]
        print 'adding:',data
        comments.append(data)
    return comments

TEMPLATES = {
    'rating': "rating[0-100]:%s",
    'body': "%s"
}
def set_image_comment(path,*args,**kwargs):
    """
    takes any kwarg, to use as a labeled part of the comment.
    can also take single arg to use as body of comment
    """
    if args and not kwargs:
        kwargs['body'] = '\n'.join(args)

    image = Image(path)
    image.readMetadata()
    # append is a possible kwarg
    append = True
    existing = image.getComment() or "" if append else ""
    comment_parts = [COMMENT_DELIMINATOR] if existing else []
    for k,v in kwargs.iteritems():
        if v is None:
            continue
        if k == 'append':
            append = v
        else:
            template = TEMPLATES.get(k,"%s:%s" % (k,v))
            comment_parts.append(template % v)
    image.setComment(existing + "\n".join(comment_parts))
    image.writeMetadata()


def get_media_page_url(mid):
    """ return url for media's page """
    return '%s%s' % (config.get('media_pages_root'),mid)

def get_media_url(mid):
    """ returns the url for media's data """
    return '%s%s' % (config.get('media_files_root'),mid)
