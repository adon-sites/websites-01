import json,html,pathlib,datetime
from PIL import Image
R=pathlib.Path(__file__).resolve().parents[1]; D=R/'dist'; C=json.loads((R/'site-config.json').read_text()); P=json.loads((R/'content/pages.json').read_text()); POSTS=json.loads((R/'content/posts.json').read_text());
# Markdown posts (content/posts/*.md): frontmatter + '## ' sections, same format as the other info sites.
def _load_md(path):
 raw=path.read_text(encoding='utf-8');assert raw.startswith('---\n'),path
 fm,body=raw[4:].split('\n---\n',1);meta={}
 for line in fm.splitlines():
  if ':' in line:k,v=line.split(':',1);meta[k.strip()]=v.strip().strip('"').strip("'")
 secs=[];cur=None
 for line in body.strip().splitlines():
  if line.startswith('## '):cur=[line[3:].strip(),[]];secs.append(cur)
  elif cur is not None and line.strip():cur[1].append(line.strip())
 sections=[[h,'\n\n'.join(' '.join(x for x in [l]) for l in ps)] for h,ps in secs]
 assert 4<=len(sections)<=7,('sections',path)
 return {'slug':path.stem,'title':meta['title'],'short_title':meta.get('short_title',''),'description':meta['description'],'category':meta.get('category','치아관리'),'publishedAt':meta['date'],'sections':sections,'textOnly':True,'origin':'markdown'}
_md=sorted((R/'content/posts').glob('*.md')) if (R/'content/posts').exists() else []
_seen={p['slug'] for p in POSTS};_new=[]
for _f in _md:
 _post=_load_md(_f);assert _post['slug'] not in _seen,('duplicate slug',_f);_seen.add(_post['slug']);_new.append(_post)
_new.sort(key=lambda p:p['publishedAt'],reverse=True)
POSTS=_new+POSTS  # newest markdown posts first in the blog list
O=C['origin'].rstrip('/'); E=html.escape
# Hourly automation moves only verified articles into native source. Reserve stays outside dist.
_now=datetime.datetime.now(datetime.timezone.utc)
_counts={}
for _p in POSTS:
 if _p.get('publishedAt'):
  _at=datetime.datetime.fromisoformat(_p['publishedAt'].replace('Z','+00:00'))
  _day=_at.astimezone(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
  _counts[_day]=_counts.get(_day,0)+1
assert all(v<=30 for v in _counts.values()), 'KST daily new-article cap exceeded'
_future=[p for p in POSTS if p.get('publishedAt') and datetime.datetime.fromisoformat(p['publishedAt'].replace('Z','+00:00'))>_now]
for _p in _future:
 _stale=D/'blog'/_p['slug']/'index.html'
 if _stale.exists(): _stale.unlink()
POSTS=[p for p in POSTS if p not in _future]
css='''*{box-sizing:border-box}body{margin:0;color:#142e4e;background:#fff;font:16px/1.8 Arial,"Malgun Gothic",sans-serif;word-break:keep-all}a{color:inherit;text-decoration:none}a:hover{color:#0865b1}a:focus-visible,button:focus-visible{outline:3px solid #fb9e38;outline-offset:4px}img{max-width:100%;height:auto;display:block}button{font:inherit;cursor:pointer}.wrap{max-width:1200px;margin:auto;padding:0 30px}.top{background:#0c315f;color:white;font-size:14px;padding:7px 0}.top .wrap{display:flex;justify-content:space-between}header.site{border-bottom:1px solid #dbe3ee;background:white}.header{display:flex;align-items:center;justify-content:space-between;padding-top:16px;padding-bottom:16px;gap:22px}.brand{font-size:23px;font-weight:bold;display:flex;gap:12px;align-items:center}.brand img{width:58px;height:55px;object-fit:contain}.nav{display:flex;gap:25px;flex-wrap:wrap;font-weight:bold}.intro{padding:48px 0 26px}.eyebrow{font-size:13px;letter-spacing:.13em;color:#366b99;font-weight:bold;margin:0 0 8px}h1{font-size:clamp(30px,4vw,46px);line-height:1.35;margin:0 0 14px;letter-spacing:-.04em}h2{font-size:25px;line-height:1.5;margin:0 0 14px}p{margin:0 0 20px}.lead{color:#52667e;max-width:760px;font-size:18px}.heading{display:flex;align-items:center;justify-content:space-between;margin:12px 0 20px;gap:16px}.arrows{display:flex;gap:8px}.arrows button{border:1px solid #cad9e9;background:white;border-radius:50%;width:42px;height:42px}.carousel{display:flex;gap:24px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:22px}.card{flex:0 0 calc((100% - 48px)/3);scroll-snap-align:start;border-bottom:2px solid #dce8f5;padding-bottom:24px}.card img{width:100%;aspect-ratio:1;object-fit:contain;background:#e7f2ff;border-radius:4px}.card .cat{display:block;color:#386793;font-size:14px;margin:20px 0 8px}.card h3{font-size:21px;line-height:1.5;margin:0 0 12px}.card p{color:#52667e;margin:0 0 16px}.more{font-weight:bold;font-size:15px;color:#1c5785}.section{padding:55px 0}.tint{background:#edf4fb;margin-top:34px}.split{display:grid;grid-template-columns:1fr 1fr;gap:55px;align-items:center}.photo{border-radius:4px;width:100%;max-height:450px;object-fit:cover}.tags{display:flex;gap:25px;margin:28px 0}.tags strong{font-size:26px;color:#0c4c89}.btn{display:inline-block;padding:11px 22px;background:#0c315f;color:#fff;border-radius:3px;margin:5px 8px 5px 0}.btn:hover{background:#18518b;color:white}.btn.light{background:white;color:#0c315f;border:1px solid #b8cce1}.linkrow{display:flex;gap:18px;flex-wrap:wrap}dl{margin:0}dt{font-weight:bold}dd{margin:0 0 12px;color:#52667e}.crumb{font-size:14px;color:#56738d;padding-top:26px}.detail{display:grid;grid-template-columns:minmax(0,780px) 260px;gap:60px;margin-bottom:60px}.article img{max-height:760px;object-fit:contain;margin:0 auto 40px}.article section{margin:34px 0}.article p{line-height:1.95}.aside{border-left:1px solid #d9e5f0;padding-left:25px}.aside a{display:block;padding:10px 0;border-bottom:1px solid #e5edf5}.notice{background:#f1f5fa;padding:22px;color:#4f6277;font-size:14px}.backlinks{margin-top:30px;padding-top:24px;border-top:1px solid #dce5ee;display:flex;gap:20px;flex-wrap:wrap}.backlinks a{text-decoration:underline;text-underline-offset:5px}.tabs{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:32px}.tabs a{padding:7px 17px;border:1px solid #c8d8e8;border-radius:30px}.tabs a[aria-current]{background:#0c315f;color:white}.blog-grid{display:grid;grid-template-columns:minmax(0,800px) 240px;gap:65px}.entry{padding:0 0 40px;margin-bottom:40px;border-bottom:1px solid #d7e2ed}.entry img{width:220px;float:right;margin:0 0 20px 30px}.entry:after{content:"";display:block;clear:both}.entry h2{font-size:25px}.entry p{color:#52667e}.meta{font-size:14px;color:#386793}.footer{background:#0d294b;color:#d7e5f4;padding:42px 0 90px}.footer p{font-size:14px;max-width:850px}.footer strong{color:white;font-size:21px;display:block;margin-bottom:15px}.bottom{position:fixed;bottom:0;right:24px;background:#0c315f;color:white;display:flex;z-index:5;box-shadow:0 -2px 15px #1234}.bottom a{padding:12px 22px;border:1px solid #315777}.skip{position:absolute;left:0;top:-90px;background:white;padding:15px;z-index:20}.skip:focus{top:0}@media(max-width:800px){.wrap{padding:0 20px}.header{padding-top:15px;padding-bottom:15px;display:block}.nav{gap:18px;font-size:14px;margin-top:13px}.brand{font-size:21px}.card{flex-basis:78%}.split,.detail,.blog-grid{grid-template-columns:1fr;gap:28px}.intro{padding-top:30px}.section{padding:35px 0}.aside{border-left:0;padding:0;border-top:1px solid #dbe5ef}.entry img{width:140px;margin-left:15px}.bottom{right:0;left:0;justify-content:stretch}.bottom a{flex:1;text-align:center;padding:10px}.top{font-size:12px}.tags{gap:20px}.footer{padding-bottom:90px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}'''
(D/'assets/style.css').write_text(css)
(D/'assets/site.js').write_text("document.querySelectorAll('[data-slide]').forEach(b=>b.addEventListener('click',()=>{const t=document.querySelector('.carousel');t.scrollBy({left:Number(b.dataset.slide)*(t.querySelector('.card').getBoundingClientRect().width+24),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}));")
def image(p,card=False):
 src='/assets/'+p['slug']+('-card-860.jpg' if card else '.webp');w,h=Image.open(D/src.lstrip('/')).size
 alt=p['alt'] if not card else f"새로운치과의원 {p['title'].split(',')[0].split(' ')[0]} 상담 안내 이미지"
 return f'<img src="{src}" alt="{E(alt)}" width="{w}" height="{h}" loading="lazy" decoding="async">'
def links():return '<nav class="backlinks" aria-label="관련 링크"><a href="'+O+'/">시흥치과</a></nav>'
def frame(path,title,desc,body,p=None,home=False):
 img='/assets/'+(p['slug']+'-card-860.jpg' if p else P[0]['slug']+'-card-860.jpg')
 robots='index,follow' if C['indexingEnabled'] else 'noindex,nofollow'
 schema={'@context':'https://schema.org','@type':'Dentist','@id':O+'/#clinic','name':C['businessName'],'url':O+'/','telephone':C['telephone'],'image':O+img,'address':{'@type':'PostalAddress','streetAddress':'정왕대로 56, 세종월드 2층','addressLocality':'시흥시','addressRegion':'경기도','addressCountry':'KR'},'sameAs':[C['officialUrl'],C['placeUrl']]}
 ld='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False)+'</script>'
 if p and not home: ld+='<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@type':'WebPage','@id':O+path+'#webpage','url':O+path,'name':title,'inLanguage':'ko-KR','about':{'@id':O+'/#clinic'},'image':O+img,'primaryImageOfPage':{'@type':'ImageObject','url':O+img,'width':860,'height':860}},ensure_ascii=False)+'</script>'
 if home:
  items=[{'@type':'ListItem','position':i+1,'name':x['title'],'url':O+'/'+x['slug']+'/','image':O+'/assets/'+x['slug']+'-card-860.jpg'} for i,x in enumerate(P)]
  ld+='<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@type':'ItemList','name':'시흥 새로운치과 주요 안내','numberOfItems':6,'itemListElement':items},ensure_ascii=False)+'</script>'
 verify='<meta name="naver-site-verification" content="'+E(C['naverVerification'])+'">' if C['naverVerification'] else ''
 s=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)}</title><meta name="description" content="{E(desc)}"><meta name="robots" content="{robots}"><link rel="canonical" href="{O+path}"><meta property="og:type" content="website"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{O+path}"><meta property="og:image" content="{O+img}"><meta property="og:image:width" content="860"><meta property="og:image:height" content="860"><meta property="og:image:alt" content="{E(p['alt'] if p else P[0]['alt'])}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{O+img}"><link rel="icon" type="image/png" href="/assets/new-dental-favicon.png"><link rel="stylesheet" href="/assets/style.css">{verify}{ld}</head><body><a href="#main" class="skip">본문 바로가기</a><div class="top"><div class="wrap"><span>월요일 20:00까지 야간진료</span><a href="tel:0314325755">031-432-5755</a></div></div><header class="site"><div class="wrap header"><a class="brand" href="/"><img src="/assets/logo.png" alt="" width="58" height="55">시흥치과</a><nav class="nav" aria-label="주 메뉴"><a href="/">시흥치과</a><a href="/about/">치과소개</a><a href="/team/">의료진</a><a href="/blog/">블로그</a><a href="/visit/">오시는 길</a></nav></div></header><main id="main">{body}</main><footer class="footer"><div class="wrap"><strong>새로운치과의원</strong><p>{C['address']}<br>대표전화 <a href="tel:0314325755">{C['telephone']}</a></p><div class="linkrow"><a href="{C['officialUrl']}">공식 홈페이지</a><a href="{C['placeUrl']}">네이버 플레이스</a><a href="/blog/">전체 글</a></div><p style="margin-top:22px">이 사이트는 새로운치과의 진료 안내와 일반적인 치아 건강정보를 제공합니다. 치료 방법, 기간과 결과는 개인의 구강 및 전신 건강 상태에 따라 달라집니다. 정확한 진단과 치료 계획은 치과 진료를 통해 확인해 주세요.</p><p>© 2026 새로운치과의원</p></div></footer><div class="bottom"><a href="tel:0314325755">전화 문의</a><a href="{C['placeUrl']}">네이버 지도·예약</a></div><script src="/assets/site.js" defer></script></body></html>'''
 out=D/path.lstrip('/')/'index.html';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(s)
 return path
paths=[]
cards=''.join(f'<article class="card" data-featured><a href="/{p["slug"]}/">{image(p,True).replace('loading="lazy"','loading="eager" fetchpriority="high"') if i<3 else image(p,True)}<span class="cat">0{i+1} / {p["category"]}</span><h3>{p["title"]}</h3><p>{p["description"]}</p><span class="more">자세히 보기 →</span></a></article>' for i,p in enumerate(P))
home=f'''<div class="wrap"><div class="intro"><p class="eyebrow">NEW DENTAL CLINIC · SIHEUNG</p><h1>시흥치과</h1><p class="lead">지금의 치아 상태를 살피고,<br>필요한 진료와 관리 방법을 함께 이야기합니다.</p></div><div class="heading"><h2>새로운치과 주요 안내</h2><div class="arrows"><button data-slide="-1" aria-label="이전 안내">←</button><button data-slide="1" aria-label="다음 안내">→</button></div></div><div class="carousel" aria-label="대표 안내 6개" tabindex="0">{cards}</div></div><section class="tint section"><div class="wrap split"><div><p class="eyebrow">ABOUT OUR CLINIC</p><h2>자연치아의 상태부터<br>차근차근 확인합니다.</h2><p>불편한 부위와 기존 치료 이력을 살피고,<br>현재 상태에 맞는 치료 방향을 상담합니다.</p><div class="tags"><span><strong>3인</strong><br>의료진 협진</span><span><strong>20시</strong><br>월요일 야간진료</span></div><a class="btn" href="/about/">치과소개 보기</a><a class="btn light" href="/team/">의료진 안내</a></div><img class="photo" src="/assets/about.webp" alt="새로운치과 내부 공간" width="1000" height="667"></div></section><section class="section"><div class="wrap"><div class="heading"><div><p class="eyebrow">DENTAL GUIDE</p><h2>진료 전에 읽어보세요</h2></div><a class="more" href="/blog/">블로그 전체 보기 →</a></div><div class="split"><div><h3><a href="/implant/">임플란트 상담에서 확인할 것</a></h3><p>검사부터 식립, 보철 연결과 이후 관리까지 치료의 흐름을 확인하세요.</p></div><div><h3><a href="/wisdom/">사랑니를 꼭 빼야 할까요?</a></h3><p>위치와 방향, 주변 치아 상태를 살피는 것이 발치 여부 판단의 출발점입니다.</p></div></div></div></section><section class="tint section"><div class="wrap split"><div><p class="eyebrow">CLINIC HOURS</p><h2>진료시간</h2><dl><dt>월요일 · 야간진료</dt><dd>09:30–20:00</dd><dt>화·수·목·금</dt><dd>09:30–18:30</dd><dt>토요일</dt><dd>09:30–13:30 · 점심시간 없이 진료</dd><dt>점심시간 / 휴진</dt><dd>13:00–14:00 / 일요일·공휴일 휴진</dd></dl></div><div><p class="eyebrow">LOCATION</p><h2>시흥 정왕동 새로운치과</h2><p>{C['address']}<br>031-432-5755</p><p>방문 전 접수 가능 시간과 진료 일정을 확인해 주세요.</p><a class="btn" href="{C['placeUrl']}">네이버 길찾기</a><a class="btn light" href="/visit/">방문 안내</a></div></div></section>'''
paths.append(frame('/','시흥치과 | 새로운치과의원, 임플란트·사랑니·충치치료','시흥 정왕동 새로운치과의원. 3인 의료진, 임플란트·사랑니·충치치료와 월요일 야간진료, 진료시간·위치를 안내합니다.',home,home=True))
for p in P:
 sections=''.join(f'<section><h2>{E(a)}</h2><p>{E(b)}</p></section>' for a,b in p['sections'])
 aside='<aside class="aside"><h2>진료 안내</h2>'+''.join(f'<a href="/{x["slug"]}/">{x["category"]}</a>' for x in P)+'<a href="/blog/">블로그 전체 보기</a></aside>'
 body=f'<div class="wrap"><nav class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a> / {p["category"]}</nav><div class="intro"><p class="eyebrow">{p["category"]}</p><h1>{p["title"]}</h1><p class="lead">{p["description"]}</p></div><div class="detail"><article class="article">{image(p,True).replace('loading="lazy"','loading="eager" fetchpriority="high"')}{sections}<p class="notice">개인의 상태에 따라 필요한 검사, 치료 방법과 경과가 달라질 수 있습니다. 자세한 내용은 진료 후 확인해 주세요.</p>{links()}</article>{aside}</div></div>'
 paths.append(frame('/'+p['slug']+'/',p['title']+' | 새로운치과의원',p['description'],body,p))
for post in POSTS:
 sections=''.join('<section><h2>'+E(heading)+'</h2>'+''.join('<p>'+E(par)+'</p>' for par in copy.split('\n\n'))+'</section>' for heading,copy in post['sections'])
 related=[x for x in POSTS if x['category']==post['category'] and x['slug']!=post['slug']][:3]
 related_html='<aside class="aside"><h2>같은 주제의 글</h2>'+''.join(f'<a href="/blog/{x["slug"]}/">{E(x["title"])}</a>' for x in related)+'<a href="/blog/">전체 글 보기</a></aside>'
 body=f'<div class="wrap"><nav class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a> / {E(post["category"])}</nav><div class="intro"><p class="eyebrow">{E(post["category"])} · 치아 건강정보</p><h1>{E(post["title"])}</h1><p class="lead">{E(post["description"])}</p></div><div class="detail"><article class="article">{sections}<p class="notice">이 글은 일반적인 치아 건강정보입니다. 증상의 원인과 필요한 진료는 검사 결과에 따라 달라집니다.</p>{links()}</article>{related_html}</div></div>'
 paths.append(frame('/blog/'+post['slug']+'/',post['short_title'] if post.get('short_title') else post['title']+' | 새로운치과의원',post['description'],body))
for category in [None]+[p['slug'] for p in P]:
 selected=P if category is None else [x for x in P if x['slug']==category]
 article_categories={'implant':'임플란트','wisdom':'사랑니발치','cavity':'충치·신경치료','about':'치아관리'}
 articles=POSTS if category is None else [x for x in POSTS if x['category']==article_categories.get(category)]
 title='시흥치과 블로그' if category is None else selected[0]['category']+' 안내'
 base='/blog/' if category is None else '/blog/category/'+category+'/'
 tabs='<nav class="tabs" aria-label="블로그 카테고리"><a href="/blog/"'+(' aria-current="page"' if category is None else '')+'>전체</a>'+''.join(f'<a href="/blog/category/{p["slug"]}/"'+(' aria-current="page"' if category==p['slug'] else '')+f'>{p["category"]}</a>' for p in P)+'</nav>'
 pages=max(1,(len(articles)+19)//20)
 for page in range(1,pages+1):
  route=base if page==1 else base+f'page/{page}/'
  entries=''.join(f'<article class="entry" data-featured-post><a href="/{p["slug"]}/">{image(p,True)}</a><p class="meta">{p["category"]} · 대표 안내</p><h2><a href="/{p["slug"]}/">{p["title"]}</a></h2><p>{p["sections"][0][1]} <a class="more" href="/{p["slug"]}/">더 읽기 →</a></p></article>' for p in (selected if page==1 else []))
  subset=articles[(page-1)*20:page*20]
  posts_html=''.join(f'<article class="entry"><p class="meta">{E(x["category"])} · 치아 건강정보</p><h2><a href="/blog/{x["slug"]}/">{E(x["title"])}</a></h2><p>{E(x["description"])} <a class="more" href="/blog/{x["slug"]}/">더 읽기 →</a></p></article>' for x in subset)
  pager='<nav aria-label="글 목록 페이지" class="tabs">'+''.join(f'<a href="{base if n==1 else base+f"page/{n}/"}"'+(' aria-current="page"' if n==page else '')+f'>{n}</a>' for n in range(1,pages+1))+'</nav>' if pages>1 else ''
  body=f'<div class="wrap section"><p class="eyebrow">NEW DENTAL JOURNAL</p><h1>{title}</h1><p class="lead">치과 방문 전 알아두면 좋은 진료 안내를 확인하세요.</p>{tabs}<div class="blog-grid"><div>{entries}{posts_html}{pager}<p>{page} / {pages} 페이지 · {len(selected)+len(articles)}개 글</p></div><aside class="aside"><h2>새로운치과</h2><p>시흥 정왕동의 치과 진료와 방문 안내</p><a href="tel:0314325755">031-432-5755</a><a href="/visit/">진료시간·오시는 길</a></aside></div></div>'
  page_title=title if page==1 else f'{title} {page}페이지'
  paths.append(frame(route,page_title+' | 새로운치과의원',title+' 목록. 새로운치과의 진료 정보와 방문 안내를 확인하세요.',body,selected[0] if category else None))
# Private preview: discovery feeds deliberately empty until a confirmed domain and launch.
visible=paths if C['indexingEnabled'] else []
(D/'robots.txt').write_text('User-agent: *\n'+('Allow: /\nSitemap: '+O+'/sitemap.xml\n' if C['indexingEnabled'] else 'Disallow: /\n'))
(D/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+O+p+'</loc></url>' for p in visible)+'</urlset>')
(D/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>새로운치과 진료 안내</title><link>'+O+'/</link><description>시흥 새로운치과 안내</description>'+(''.join('<item><title>'+E(p['title'])+'</title><link>'+O+('/blog/' if p in POSTS else '/')+p['slug']+'/</link><guid>'+O+('/blog/' if p in POSTS else '/')+p['slug']+'/</guid><description>'+E(p['description'])+'</description></item>' for p in P+POSTS) if C['indexingEnabled'] else '')+'</channel></rss>')
(D/'404.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="robots" content="noindex"><title>페이지를 찾을 수 없습니다</title><h1>페이지를 찾을 수 없습니다</h1><a href="/">홈으로 돌아가기</a></html>')
print(json.dumps({'routes':len(paths),'featured':len(P),'articles':len(POSTS),'indexing':C['indexingEnabled'],'reference_files':len(list((R/'content/reference').glob('*.txt')))}))

# Persist the requested homepage layout without changing publication records.
import runpy as _home_runpy
_home_runpy.run_path(str(R/'home_layout.py'), run_name='__main__')

# Homepage detail content stays in the normal build flow.
import runpy as _detail_runpy
_detail_runpy.run_path(str(R/'homepage_detail.py'), run_name='__main__')

# Source-based cost guide is homepage-only and preserves all publication data.
_cost_runpy=__import__("runpy")
_cost_runpy.run_path(str(__import__("pathlib").Path(__file__).resolve().parents[1]/"home_cost_guide.py"),run_name="__main__")

# Preserve first-visit image and stylesheet optimizations after every content build.
import runpy as _speed_runpy
_speed_runpy.run_path(str(R/"scripts/optimize_first_visit.py"), run_name="__main__")

# ---- quickmenu (2026-10-22): dist 전체 HTML의 </body> 앞에 오른쪽 고정 퀵메뉴 삽입 ----
def _qm_apply():
    import re as _re, pathlib as _pl
    here = _pl.Path(__file__).resolve()
    for root in (here.parent, here.parent.parent):
        f = root / 'quickmenu.html'
        if f.exists():
            frag = f.read_text(encoding='utf-8'); out = root / 'dist'; break
    else:
        return
    for p in out.rglob('*.html'):
        s = p.read_text(encoding='utf-8')
        s2 = _re.sub(r'<!-- quickmenu:start -->.*?<!-- quickmenu:end -->', '', s, flags=_re.S)
        if '</body>' in s2:
            s2 = s2.replace('</body>', frag + '</body>', 1)
        if s2 != s: p.write_text(s2, encoding='utf-8')
_qm_apply()
