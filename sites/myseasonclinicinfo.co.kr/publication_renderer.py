import json, re, math
from datetime import datetime
from email.utils import format_datetime
from xml.sax.saxutils import escape

LINK='<aside class="publication-link"><p>나의계절의원 안내: <a href="http://myseasonclinicinfo.co.kr">대구필러</a></p></aside>'
def enrich(g):
 root,out,E,page,origin,posts,urls=[g[k] for k in ['ROOT','OUT','E','page','ORIGIN','posts','urls']]
 state=json.loads((root/'publication/state.json').read_text())
 approved=json.loads((root/'publication/approved.json').read_text())
 published=[dict(p,**state['published'][p['id']]) for p in approved if p['id'] in state['published']]
 md_posts=g.get('md_posts',[]);categories=g.get('CATEGORIES',{})
 assert not ({p['slug'] for p in md_posts}&({p['slug'] for p in published}|{p['slug'] for p in posts})),'duplicate slug between markdown post and existing article'
 for p in published+md_posts:
  path='/journal/'+p['slug']+'/'
  if p.get('sections'):  # markdown post: '## ' sections rendered as h2 + paragraphs
   desc=p['excerpt'];crumb=f'<p class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a> / <a href="/category/{categories[p["category"]]}/">{E(p["category"])}</a></p>'
   content=''.join('<section><h2>'+E(h)+'</h2>'+''.join('<p>'+E(par)+'</p>' for par in c.split('\n\n'))+'</section>' for h,c in p['sections'])
   title=p['short_title'] or p['title']+' | 나의계절의원'
  else:
   desc=' '.join(p['body'].split())[:150];crumb='<p class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a></p>'
   content=f'<div class="approved-manuscript" style="white-space:pre-wrap;overflow-wrap:anywhere">{E(p["body"])}</div>'
   title=p['title']+' | 나의계절의원'
  body=f'<main class="article journal-article">{crumb}<header class="entry-header"><h1>{E(p["title"])}</h1><p class="blog-meta"><time datetime="{p["timestamp"]}">{p["date"]}</time> · 나의계절의원</p></header>{content}{LINK}<p><a href="/blog/">전체 글 보기</a></p></main>'
  schema={'@context':'https://schema.org','@type':'BlogPosting','headline':p['title'],'datePublished':p['timestamp'],'dateModified':p['timestamp'],'mainEntityOfPage':origin+path,'author':{'@type':'Organization','name':'나의계절의원'},'publisher':{'@id':origin+'/#clinic'}}
  page(path,title,desc,body,[schema])
  dest=out/path.strip('/')/'index.html'
  dest.write_text(re.sub(r'<meta property="og:image(?::alt)?"[^>]*>','',dest.read_text()).replace('property="og:type" content="website"','property="og:type" content="article"'))
 # Include the requested anchor in every existing journal and treatment article.
 for folder in ['journal','treatments']:
  for dest in (out/folder).glob('*/index.html'):
   text=dest.read_text()
   if 'class="publication-link"' not in text: dest.write_text(text.replace('</main>',LINK+'</main>'))
 ordered=md_posts+sorted(published,key=lambda p:(p['date'],p['id']),reverse=True)  # newest markdown posts first
 pages=max(1,math.ceil(len(ordered)/20))
 for number in range(1,pages+1):
  path='/blog/' if number==1 else f'/blog/page/{number}/'
  pinned='<section><h2>대표 안내</h2><ul class="featured-list">'+''.join(g['card'](i) for i in range(6))+'</ul></section>' if number==1 else ''
  entries=''.join(f'<article><h2><a href="/journal/{p["slug"]}/">{E(p["title"])}</a></h2><p class="blog-meta">{p["date"]} · 나의계절의원</p><p>{E(p["excerpt"] if p.get("sections") else " ".join(p["body"].split())[:160])}… <a href="/journal/{p["slug"]}/">더 읽기</a></p></article>' for p in ordered[(number-1)*20:number*20])
  pagination='<nav class="related" aria-label="글 목록 페이지">'+''.join(f'<a href="{"/blog/" if n==1 else "/blog/page/"+str(n)+"/"}"'+(' aria-current="page"' if n==number else '')+f'>{n}</a>' for n in range(1,pages+1))+'</nav>'
  page(path,'나의계절의원 블로그'+('' if number==1 else f' · {number}페이지'),'나의계절의원 시술 안내와 피부 건강정보',f'<main class="blog-shell"><h1>나의계절의원 블로그</h1>{pinned}<h2>최신 글</h2><div class="blog-list">{entries}</div>{pagination}</main>')
 dates={'/journal/'+p['slug']+'/':p['date'] for p in published+md_posts}
 (out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{origin}{u}</loc><lastmod>{dates.get(u,max(dates.values(),default=g["DATE"]))}</lastmod></url>' for u in dict.fromkeys(urls))+'</urlset>')
 feed=ordered+[dict(p,timestamp=g['DATE']+'T17:22:48+09:00') for p in posts]
 (out/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>대구필러 | 나의계절의원</title><link>'+origin+'</link><description>나의계절의원 블로그</description><language>ko</language>'+''.join(f'<item><title>{escape(p["title"])}</title><link>{origin}/journal/{p["slug"]}/</link><guid>{origin}/journal/{p["slug"]}/</guid><description>{escape(p.get("excerpt",p.get("body",""))[:160])}</description><pubDate>{format_datetime(datetime.fromisoformat(p["timestamp"]))}</pubDate></item>' for p in feed)+'</channel></rss>')
 print(f'Published approved manuscripts: {len(published)}; all articles have keyword link')
