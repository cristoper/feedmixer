import datetime
import feedparser
import feedgenerator

NUM_KEEP = 2

feeds = ['http://notwithoutsincerity.in1accord.net/rss',
        'http://bothsandneithers.tumblr.com/rss',
        'http://feeds.feedburner.com/AmericanCynic',
        'http://wholeheaptogether.in1accord.net/rss',
        'http://mymorninghaiku.blogspot.com//feeds/posts/default']

mixed_entries = []
atom_feed = feedgenerator.Atom1Feed(title="Mixed",
        link="", description="description")

# fetch and parse feeds
for feed in feeds:
    f = feedparser.parse(feed)
    newest = f.entries[0:NUM_KEEP]
    # use feed author if individual entries are missing
    # author property
    if 'author_detail' in f.feed:
        for e in newest:
            if not 'author_detail' in e:
                e['author_detail'] = f.feed.author_detail
                e.author_detail = f.feed.author_detail
    mixed_entries += newest
    
# sort entries by published date
mixed_entries.sort(key = lambda e: e.published,
        reverse = True)

# generate mixed feed
for e in mixed_entries:
    metadata = {}

    # title, link, and description are mandatory
    metadata['title'] = e.get('title', '')
    metadata['link'] = e.get('link', '')
    metadata['description'] = e.get('description', '')

    if 'author_detail' in e:
        metadata['author_email'] = e.author_detail.get('email')
        metadata['author_name'] = e.author_detail.get('name')
        metadata['author_link'] = e.author_detail.get('href')
    
    # convert time_struct tuples into datetime objects
    # (the min() prevents error in the off-chance that the
    # date contains a leap-second)
    tp = e.get('published_parsed')
    if tp:
        metadata['pubdate'] = datetime.datetime(*tp[:5] + (min(tp[5], 59),))

    tu = e.get('updated_parsed')
    if tu:
        metadata['updateddate'] = datetime.datetime(*tu[:5] + (min(tu[5], 59),))

    metadata['comments'] = e.get('comments')
    metadata['unique_id'] = e.get('id')
    metadata['item_copyright'] = e.get('license')

    if 'tags' in e:
        taglist = [tag.get('term') for tag in e.tags]
        metadata['categories'] = taglist
    
    if 'enclosures' in e:
        enclist = [feedgenerator.Enclosure(enc.href, enc.length, enc.type) for enc in e.enclosures]
        metadata['enclosures'] = enclist


    atom_feed.add_item(**metadata)

print(atom_feed.writeString('utf-8'))
