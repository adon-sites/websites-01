"""Render only released, byte-preserved source manuscripts; no images in new posts."""
import json
import math
from datetime import datetime
from email.utils import format_datetime
from xml.sax.saxutils import escape


def render_publications(site):
    root, out, origin = site['ROOT'], site['OUT'], site['ORIGIN']
    page, esc = site['page'], site['E']
    folder = root / 'publication'
    manifest = json.loads((folder / 'manifest.json').read_text())
    released = json.loads((folder / 'released.json').read_text())
    articles = []
    for item in manifest['articles']:
        stamp = released.get(str(item['id']))
        if not stamp:
            continue
        source = (folder / 'manuscripts' / item['file']).read_text(encoding='utf-8-sig')
        title, _, body = source.partition('\n')
        desc = next(line for line in body.splitlines() if line.strip())[:150]
        path = '/journal/' + item['slug'] + '/'
        content = (f'<main class="article journal-article"><p class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a></p>'
                   f'<header class="entry-header"><h1>{esc(title)}</h1><p class="blog-meta"><time datetime="{stamp}">{stamp[:10]}</time> · 브랜뉴의원</p></header>'
                   f'<div class="manuscript-body" style="white-space:pre-wrap;overflow-wrap:anywhere">{esc(body)}</div>'
                   '<p><a class="text-link" href="/blog/">전체 글 보기</a></p></main>')
        schema = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': title,
                  'description': desc, 'datePublished': stamp, 'dateModified': stamp,
                  'mainEntityOfPage': origin + path, 'author': {'@type': 'Organization', 'name': '브랜뉴의원'},
                  'publisher': {'@id': origin + '/#clinic'}}
        page(path, title + ' | 브랜뉴의원', desc, content, [schema])
        articles.append(dict(item, path=path, stamp=stamp, description=desc))
    # Markdown posts (content/posts/*.md, loaded in build.py): '## ' sections rendered as h2 + paragraphs, text-only.
    md_posts = site.get('md_posts', []); categories = site.get('CATEGORIES', {})
    taken = {a['slug'] for a in articles} | {p['slug'] for p in site['posts']} | {str(i['slug']) for i in manifest['articles']}
    for m in md_posts:
        assert m['slug'] not in taken, ('duplicate slug', m['slug'])
        body = ''.join('<section><h2>' + esc(h) + '</h2>' + ''.join('<p>' + esc(par) + '</p>' for par in c.split('\n\n')) + '</section>' for h, c in m['sections'])
        content = (f'<main class="article journal-article"><p class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a> / <a href="/category/{categories[m["category"]]}/">{esc(m["category"])}</a></p>'
                   f'<header class="entry-header"><h1>{esc(m["title"])}</h1><p class="blog-meta"><time datetime="{m["stamp"]}">{m["stamp"][:10]}</time> · 브랜뉴의원</p></header>'
                   f'{body}<p><a class="text-link" href="/blog/">전체 글 보기</a></p></main>')
        schema = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': m['title'],
                  'description': m['description'], 'datePublished': m['stamp'], 'dateModified': m['stamp'],
                  'mainEntityOfPage': origin + m['path'], 'author': {'@type': 'Organization', 'name': '브랜뉴의원'},
                  'publisher': {'@id': origin + '/#clinic'}}
        page(m['path'], m['short_title'] or m['title'] + ' | 브랜뉴의원', m['description'], content, [schema])
    md_cards = [dict(m, id=m['slug']) for m in md_posts]

    # First page retains all six illustrated featured articles. Remaining entries are text-only.
    featured = []
    for i, post in enumerate(site['posts']):
        featured.append(f'<article><a class="initial-post-image" href="/journal/{post["slug"]}/">{site["image"](i)}</a>'
                        f'<h2><a href="/journal/{post["slug"]}/">{esc(post["title"])}</a></h2>'
                        f'<p class="blog-meta">2026-09-30 · 브랜뉴의원</p><p class="blog-excerpt">{esc(post["excerpt"])}</p></article>')
    cards = []
    for item in md_cards + sorted(articles, key=lambda a: (a['stamp'], a['id']), reverse=True):  # newest markdown posts first
        cards.append(f'<article><h2><a href="{item["path"]}">{esc(item["title"])}</a></h2>'
                     f'<p class="blog-meta"><time datetime="{item["stamp"]}">{item["stamp"][:10]}</time> · 브랜뉴의원</p>'
                     f'<p class="blog-excerpt">{esc(item["description"])} <a class="blog-read-more" href="{item["path"]}">더 읽기</a></p></article>')
    count = max(1, math.ceil(len(cards)/20))
    for n in range(1, count+1):
        path = '/blog/' if n == 1 else f'/blog/page/{n}/'
        navigation = '<nav class="blog-pagination" aria-label="블로그 페이지">' + ' · '.join(
            f'<a href="{"/blog/" if k==1 else f"/blog/page/{k}/"}"' + (' aria-current="page"' if n==k else '') + f'>{k}</a>'
            for k in range(1, count+1)) + '</nav>'
        entries = (''.join(featured) if n==1 else '') + ''.join(cards[(n-1)*20:n*20])
        page(path, f'브랜뉴의원 블로그{f" {n}페이지" if n>1 else ""} | 소프웨이브',
             '브랜뉴의원 피부·시술 정보와 상담 전 확인사항을 읽어보세요.',
             '<main class="blog-shell"><h1 class="blog-topic-heading">브랜뉴의원 블로그</h1>' +
             f'<div class="blog-list">{entries}</div>{navigation}</main>')

    dates = {item['path']: item['stamp'][:10] for item in articles + md_cards}
    paths = list(dict.fromkeys(site['urls']))
    (out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+
        ''.join(f'<url><loc>{origin}{p}</loc><lastmod>{dates.get(p, site["DATE"])}</lastmod></url>' for p in paths)+'</urlset>')
    feeds = (md_cards + sorted(articles, key=lambda a: (a['stamp'], a['id']), reverse=True))[:50]
    (out/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>소프웨이브 | 브랜뉴의원</title>'+
        f'<link>{origin}/</link><description>브랜뉴의원 피부 건강정보</description><language>ko</language>'+
        ''.join(f'<item><title>{escape(a["title"])}</title><link>{origin}{a["path"]}</link><guid>{origin}{a["path"]}</guid><description>{escape(a["description"])}</description><pubDate>{format_datetime(datetime.fromisoformat(a["stamp"]))}</pubDate></item>' for a in feeds)+'</channel></rss>')
    print(f'Supplied manuscripts: {len(articles)} published / {manifest["total"]}; blog pages: {count}')
