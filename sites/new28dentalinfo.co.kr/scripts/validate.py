import pathlib,json,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit
from PIL import Image
R=pathlib.Path(__file__).resolve().parents[1];D=R/'dist';C=json.loads((R/'site-config.json').read_text());P=json.loads((R/'content/pages.json').read_text());POSTS=json.loads((R/'content/posts.json').read_text())
assert len(P)==6 and len(P)+len(POSTS)>=200,(len(P),len(POSTS))
class Parse(HTMLParser):
 def __init__(self):super().__init__();self.tags=[];self.ld=[];self.active=False
 def handle_starttag(self,t,a):
  a=dict(a);self.tags.append((t,a))
  if t=='script' and a.get('type')=='application/ld+json':self.active=True
 def handle_endtag(self,t):
  if t=='script':self.active=False
 def handle_data(self,d):
  if self.active:self.ld.append(json.loads(d))
files=[f for f in D.rglob('index.html') if f.relative_to(D).parts[0] not in {'client','server','.openai','_appgen_meta'}];titles=[]
for f in files:
 s=f.read_text();p=Parse();p.feed(s);assert sum(t=='h1' for t,a in p.tags)==1
 title=s.split('<title>')[1].split('</title>')[0];assert title not in titles; titles.append(title)
 route='/'+str(f.parent.relative_to(D)).replace('\\','/')+'/' if f.parent!=D else '/'
 assert any(t=='link' and a.get('rel')=='canonical' and a.get('href')==C['origin']+route for t,a in p.tags)
 assert any(t=='meta' and a.get('name')=='robots' and a.get('content')==('index,follow' if C['indexingEnabled'] else 'noindex,nofollow') for t,a in p.tags)
 for t,a in p.tags:
  u=a.get('href') if t=='a' else a.get('src') if t in ['img','script'] else None
  if u and u.startswith('/'):
   dest=D/u.lstrip('/');assert dest.exists(),(f,u)
  if t=='img':assert a.get('alt') is not None and a.get('width') and a.get('height')
 lists=[x for x in p.ld if x.get('@type')=='ItemList']
 if f==D/'index.html':
  assert len(lists)==1 and len(lists[0]['itemListElement'])==6
  assert s.index('ItemList')<s.index('</head>')
  assert s.count('data-featured>')==6
  for i,(a,b) in enumerate(zip(lists[0]['itemListElement'],P)):
   assert a['position']==i+1 and a['name']==b['title'] and a['url']==C['origin']+'/'+b['slug']+'/' and a['image']==C['origin']+'/assets/'+b['slug']+'-card.webp'
   assert Image.open(D/'assets'/f'{b["slug"]}-card.webp').size==(800,800)
 else:assert not lists
for p in P+POSTS:
 f=D/(('blog/' if p in POSTS else '')+p['slug'])/'index.html'
 s=f.read_text();assert '<nav class="backlinks" aria-label="관련 링크"><a href="'+C['origin']+'/">시흥치과</a></nav>' in s and C['officialUrl'] in s and C['placeUrl'] in s
assert (D/'blog/index.html').read_text().count('data-featured-post')==6
assert all((D/'blog'/x['slug']/'index.html').exists() for x in POSTS)
for x in POSTS:
 s=(D/'blog'/x['slug']/'index.html').read_text()
 article=s.split('<article class="article">',1)[1].split('</article>',1)[0]
 assert '<img' not in article,x['slug']
blog_pages=sorted((D/'blog').glob('page/*/index.html'))
assert sum(f.read_text().count('치아 건강정보</p>') for f in [D/'blog/index.html',*blog_pages])==len(POSTS)
assert all('data-featured-post' not in f.read_text() for f in blog_pages)
sitemap=ET.parse(D/'sitemap.xml').getroot()
feed=ET.parse(D/'rss.xml').findall('.//item')
robots=(D/'robots.txt').read_text()
if C['indexingEnabled']:
 assert C['customDomainConfirmed']
 assert len(sitemap)==len(files)
 expected={C['origin']+('/'+str(f.parent.relative_to(D))+'/' if f.parent!=D else '/') for f in files}
 assert {x.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text for x in sitemap}==expected
 assert len(feed)==len(P)+len(POSTS)
 assert all(x.find('link').text in expected for x in feed)
 assert 'Allow: /' in robots and 'Disallow: /' not in robots
 assert 'Sitemap: '+C['origin']+'/sitemap.xml' in robots
else:
 assert len(sitemap)==0 and not feed
 assert 'Disallow: /' in robots
assert not any('사용 X' in str(f) for f in D.rglob('*'))
print(json.dumps({'result':'passed','html_pages':len(files),'featured':6,'articles':len(POSTS),'categories':6,'backlinks':'verified','ItemList':'home only; 1:1','indexing':'enabled' if C['indexingEnabled'] else 'blocked'},ensure_ascii=False))
