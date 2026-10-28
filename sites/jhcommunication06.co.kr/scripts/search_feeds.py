from pathlib import Path
from urllib.parse import urljoin
from xml.sax.saxutils import escape
from email.utils import format_datetime
import datetime,re

def build_rss(root, origin, articles):
    rss='<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>애드온 인사이트</title><link>'+origin+'/blog/</link><description>공개된 애드온 콘텐츠</description><language>ko-KR</language>'
    # Keep enough recent entries for a full daily allocation plus any delayed
    # independently-reviewed corrections released in the same deployment.
    for a in sorted(articles,key=lambda a:a.get('publishedAt') or '',reverse=True)[:50]:
        text=(root/'dist'/a['path'].lstrip('/')/'index.html').read_text()
        body=re.search(r'<article(?:\s[^>]*)?>(.*?)</article>',text,re.S).group(1)
        body=re.sub(r'(href|src)="([^"#][^"]*)"',lambda m:m[1]+'="'+urljoin(origin+a['path'],m[2])+'"',body)
        url=origin+a['path']
        rss+='<item><title>'+escape(a['title'])+'</title><link>'+escape(url)+'</link><guid isPermaLink="true">'+escape(url)+'</guid><description>'+escape(body)+'</description>'
        # Omit unknown historical dates instead of assigning the indexing date.
        if a.get('publishedAt'):
            date=datetime.datetime.fromisoformat(a['publishedAt'].replace('Z','+00:00'))
            assert date.tzinfo and date<=datetime.datetime.now(datetime.timezone.utc)
            rss+='<pubDate>'+format_datetime(date)+'</pubDate>'
        rss+='</item>'
    return rss+'</channel></rss>'
