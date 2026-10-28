import json, html
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape
ROOT=Path(__file__).parent; OUT=ROOT/'dist'; ORIGIN='https://brandnewclinicinfo.co.kr'; DATE='2026-09-30'; NAME='브랜뉴의원'
posts=json.loads((ROOT/'content.json').read_text()); E=html.escape
# Markdown posts (content/posts/<slug>.md): frontmatter(title, short_title?, description, category, date +09:00) + '## ' sections.
import datetime as _dt
CATEGORIES={p['topic']:p['slug'] for p in posts}
def _load_md(path):
 raw=path.read_text(encoding='utf-8');assert raw.startswith('---\n'),path
 fm,body=raw[4:].split('\n---\n',1);meta={}
 for line in fm.splitlines():
  if ':' in line:k,v=line.split(':',1);meta[k.strip()]=v.strip().strip('"').strip("'")
 secs=[];cur=None
 for line in body.strip().splitlines():
  if line.startswith('## '):cur=[line[3:].strip(),[]];secs.append(cur)
  elif cur is not None and line.strip():cur[1].append(line.strip())
 sections=[[h,'\n\n'.join(ps)] for h,ps in secs]
 assert 4<=len(sections)<=7,('sections',path)
 assert meta['category'] in CATEGORIES,('category',meta.get('category'),sorted(CATEGORIES),path)
 ts=meta['date'];assert ts.endswith('+09:00'),('date must be KST ISO (+09:00)',path)
 return {'id':'md-'+path.stem,'slug':path.stem,'title':meta['title'],'short_title':meta.get('short_title',''),'description':meta['description'],'category':meta['category'],'stamp':ts,'sections':sections,'path':'/journal/'+path.stem+'/','origin':'markdown'}
_md=sorted((ROOT/'content/posts').glob('*.md')) if (ROOT/'content/posts').exists() else []
_now=_dt.datetime.now(_dt.timezone.utc);md_posts=[]
for _f in _md:
 _m=_load_md(_f)
 if _dt.datetime.fromisoformat(_m['stamp'])>_now:
  _stale=ROOT/'dist/journal'/_m['slug']/'index.html'
  if _stale.exists():_stale.unlink()
  continue
 md_posts.append(_m)
md_posts.sort(key=lambda p:(p['stamp'],p['slug']),reverse=True)  # newest first, ahead of older manuscripts
nav='<a href="/">소프웨이브</a><a href="/blog/">블로그</a><a href="/#treatments">시술 안내</a><a href="/about/">병원 소개</a><a href="/contact/">오시는 길</a>'
header=f'<a class="skip-link" href="#site-content">본문 바로가기</a><header class="site-header"><div class="header-inner"><a href="/" class="brand" aria-label="브랜뉴의원 소프웨이브 홈"><img class="brand-logo" src="/images/brandnew-logo.svg" alt="브랜뉴의원 로고" width="64" height="43"><span>소프웨이브</span></a><nav class="desktop-menu" aria-label="주 메뉴">{nav}</nav><details class="mobile-menu"><summary>메뉴</summary><nav aria-label="모바일 메뉴">{nav}</nav></details></div></header><nav class="quick-links" aria-label="빠른 안내"><a href="tel:025113075">전화 상담</a><a href="/contact/">오시는 길</a><a href="#site-content">맨 위로</a></nav>'
notice='시술의 적용 여부와 결과, 회복 기간은 개인에 따라 다릅니다. 시술 후 통증·붓기·붉어짐 등의 이상 반응이 생길 수 있습니다. 본 안내는 개별 진료를 대신하지 않습니다.'
footer=f'<footer class="site-footer"><strong>브랜뉴의원</strong><p>서울 강남구 압구정로 437 일신빌딩 4층 · 대표자 윤성은<br>사업자등록번호 211-10-10053<br><a href="tel:025113075">02-511-3075</a> · <a href="https://brandnewclinic.com/" target="_blank" rel="noopener noreferrer">공식 홈페이지</a> · <a href="https://naver.me/FsRLO9Tg" target="_blank" rel="noopener noreferrer">네이버 지도</a></p><p>{notice}</p><p>© 2026 BRANDNEW CLINIC · <a href="/">소프웨이브</a></p></footer>'
favicon='data:image/svg+xml,'+quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#167b86"/><text x="32" y="44" text-anchor="middle" font-family="Arial" font-size="37" font-weight="bold" fill="white">B</text></svg>')
base_schema={'@context':'https://schema.org','@type':'MedicalClinic','@id':ORIGIN+'/#clinic','name':NAME,'url':ORIGIN+'/','telephone':'+82-2-511-3075','image':ORIGIN+'/images/carousel-1.png','address':{'@type':'PostalAddress','streetAddress':'압구정로 437 일신빌딩 4층','addressLocality':'강남구','addressRegion':'서울특별시','addressCountry':'KR'},'sameAs':['https://brandnewclinic.com/','https://naver.me/FsRLO9Tg']}
carousel_images=['carousel-1.png','carousel-2.png','carousel-3.png','carousel-4.png','feature-3.jpg','feature-4.jpg']
backlink='<p class="post-backlink"><a href="https://brandnewclinicinfo.co.kr/">소프웨이브</a></p>'
urls=[]
def page(path,title,desc,body,schemas=[]):
 if path.startswith("/journal/"): body=body.replace("</main>",backlink+"</main>")
 url=ORIGIN+path; dest=OUT/(path.strip('/')+'/index.html' if path!='/' else 'index.html');dest.parent.mkdir(parents=True,exist_ok=True)
 structured=''.join('<script type="application/ld+json">'+json.dumps(s,ensure_ascii=False).replace('</','<\\/')+'</script>' for s in [base_schema]+schemas)
 dest.write_text(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="naver-site-verification" content="3fbc8310d436e95283b6f9cfa5091e9f7e293acb"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)}</title><meta name="description" content="{E(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="icon" type="image/svg+xml" href="/favicon.svg?v=brandnew-transparent-2"><link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png?v=brandnew-transparent-2"><link rel="shortcut icon" href="/favicon.ico?v=brandnew-transparent-2"><link rel="apple-touch-icon" sizes="192x192" href="/favicon-192.png?v=brandnew-transparent-2"><link rel="stylesheet" href="/style.css"><link rel="alternate" type="application/rss+xml" title="브랜뉴의원 블로그" href="/rss.xml"><meta property="og:type" content="website"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="소프웨이브 | 브랜뉴의원"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{ORIGIN}/images/carousel-1.png"><meta property="og:image:width" content="1254"><meta property="og:image:height" content="1254"><meta property="og:image:alt" content="브랜뉴의원 강남소프웨이브 상담 안내 이미지"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{ORIGIN}/images/carousel-1.png">{structured}</head><body>{header}<div id="site-content">{body}</div>{footer}</body></html>');urls.append(path)
def image(i,cls='',lazy=True):
 return f'<img src="/images/{carousel_images[i]}" alt="{E(posts[i]["alt"])}" width="860" height="860" loading="{"lazy" if lazy else "eager"}" decoding="async" class="{cls}">'
def card(i):
 p=posts[i];u='/journal/'+p['slug']+'/'
 return f'<li><article class="featured-card"><a class="featured-thumb" href="{u}">{image(i,lazy=i>2)}</a><div class="featured-copy"><h2><a href="{u}">{E(p["title"])}</a></h2><p class="card-meta"><time datetime="{DATE}">2026. 9. 30.</time> · 브랜뉴의원</p><p class="card-excerpt">{E(p["excerpt"])}</p><a class="card-more" href="{u}" aria-label="{E(p["title"])} 더 읽기">더 읽기</a></div></article></li>'
hours='<dl class="hours"><dt>화요일</dt><dd>10:00–20:30</dd><dt>수·목·금요일</dt><dd>10:00–18:30</dd><dt>토요일</dt><dd>09:00–15:00</dd><dt>휴진</dt><dd>월요일·일요일·공휴일·국경일</dd></dl><p class="muted">점심시간 없이 진료 · 공식 홈페이지 안내 기준, 방문 전 일정 확인</p>'
actions='<div class="clinic-actions"><a href="tel:025113075">02-511-3075 전화 상담</a><a href="https://naver.me/FsRLO9Tg" target="_blank" rel="noopener noreferrer">네이버 지도에서 위치 확인</a><a href="https://pf.kakao.com/_KsZkM" target="_blank" rel="noopener noreferrer">공식 카카오톡 상담</a></div>'
source='<aside class="source-links"><p>참고 자료 · 2026. 9. 30. 확인</p><p><a href="https://brandnewclinic.com/sofwave" target="_blank" rel="noopener noreferrer">브랜뉴의원 소프웨이브 공식 안내</a> · <a href="https://sofwave.com/patients/face" target="_blank" rel="noopener noreferrer">제조사 시술 안내</a> · <a href="https://sofwave.com/safety-information" target="_blank" rel="noopener noreferrer">제조사 안전 정보</a></p></aside>'
alts=['브랜뉴의원 의료진 단체 사진','브랜뉴의원 의료진 상담 안내','브랜뉴의원 소프웨이브 의료진 안내','브랜뉴의원 마취과 의료진 안내','브랜뉴의원 소프웨이브 안내 이미지','브랜뉴의원 실내 공간']
for p,a in zip(posts,alts):p['alt']=a
itemlist={'@context':'https://schema.org','@type':'ItemList','name':'소프웨이브 주요 안내 6편','itemListOrder':'https://schema.org/ItemListOrderAscending','numberOfItems':6,'itemListElement':[{'@type':'ListItem','position':i+1,'url':ORIGIN+'/journal/'+p['slug']+'/','name':p['title'],'image':ORIGIN+f'/images/{carousel_images[i]}'} for i,p in enumerate(posts)]}
summary=''.join(f'<div class="treatment-summary"><h3><a href="/treatments/{p["slug"]}/">소프웨이브 {p["topic"]} 안내</a></h3><p>{p["excerpt"]}</p><a class="text-link" href="/treatments/{p["slug"]}/">더 읽기</a></div>' for p in posts)
home=f'<main class="home-shell"><section class="featured-section" aria-label="소프웨이브 대표 안내"><ul class="featured-list">{"".join(card(i) for i in range(6))}</ul><div class="more-row"><a class="more-button" href="/blog/">글 더보기</a></div></section><section class="clinic-gallery" aria-label="브랜뉴의원 병원 공간"><img src="/images/interior-1.jpg" alt="브랜뉴의원 내부 공간" width="1000" height="667" loading="lazy"><img src="/images/interior-2.jpg" alt="브랜뉴의원 진료 공간" width="1000" height="667" loading="lazy"></section><section class="home-intro" id="treatments"><h1>소프웨이브</h1><p>브랜뉴의원에서 안내하는 소프웨이브. 시술 원리부터 상담, 회복과 주의사항까지 살펴보세요.</p><p class="eyebrow">SOFWAVE · 01—06</p><h2>궁금한 내용부터 살펴보세요</h2>{summary}<p class="notice">{notice}</p></section><section class="clinic-info"><h2>브랜뉴의원 진료·위치 안내</h2><p>서울 강남구 압구정로 437 일신빌딩 4층</p>{hours}{actions}<p><a class="text-link" href="/contact/">진료시간과 오시는 길</a></p></section></main>'
page('/','소프웨이브 | 브랜뉴의원','소프웨이브 원리와 상담 전 확인사항, 회복 안내. 브랜뉴의원 진료시간·위치와 피부 건강정보를 확인하세요.',home,[itemlist])
for i,p in enumerate(posts):
 path='/journal/'+p['slug']+'/';schema={'@context':'https://schema.org','@type':'BlogPosting','headline':p['title'],'description':p['excerpt'],'datePublished':DATE+'T15:30:00+09:00','dateModified':DATE+'T15:30:00+09:00','image':ORIGIN+f'/images/{carousel_images[i]}','author':{'@type':'Organization','name':'브랜뉴의원 시술 안내'},'mainEntityOfPage':ORIGIN+path,'publisher':{'@id':ORIGIN+'/#clinic'}}
 toc='<nav class="toc" aria-label="글 목차"><strong>이 글에서 확인할 내용</strong><ol>'+''.join(f'<li><a href="#section-{j}">{E(h)}</a></li>' for j,(h,t) in enumerate(p['sections']))+'</ol></nav>'
 sections=''.join(f'<section id="section-{j}"><h2>{E(h)}</h2><p>{E(t)}</p></section>' for j,(h,t) in enumerate(p['sections']))
 related=''.join(f'<a href="/journal/{q["slug"]}/">{q["topic"]}</a>' for q in posts if q!=p)
 body=f'<main class="article journal-article"><p class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a> / {p["topic"]}</p><header class="entry-header"><h1>{p["title"]}</h1><p class="blog-meta"><time datetime="{DATE}">2026년 9월 30일</time> · 브랜뉴의원 시술 안내</p></header><p class="lead">{p["excerpt"]}</p><figure class="article-photo">{image(i)}<figcaption>브랜뉴의원 제공 자료</figcaption></figure>{toc}{sections}<p class="notice">{notice}</p>{source}<nav class="related" aria-label="관련 글">{related}</nav><p><a class="text-link" href="/">소프웨이브</a> · <a class="text-link" href="/blog/">전체 글 보기</a> · <a class="text-link" href="/contact/">상담·오시는 길</a></p></main>'
 page(path,p['title']+' | 브랜뉴의원',p['excerpt'],body,[schema])
 body=f'<main class="article"><p class="crumb"><a href="/">홈</a> / 시술 안내</p><h1>소프웨이브 {p["topic"]}</h1><p class="lead">{p["excerpt"]}</p><h2>상담 전 살펴볼 내용</h2><ul>'+''.join(f'<li>{h}</li>' for h,t in p['sections'])+f'</ul><p>현재 피부 상태와 기존 시술 경험을 함께 확인한 뒤 계획을 결정합니다. 아래 상세 안내에서 질문을 정리해 보세요.</p><p><a class="button" href="/journal/{p["slug"]}/">{p["topic"]} 상세 안내 읽기</a></p><p class="notice">{notice}</p><div class="related"><a href="/contact/">상담 안내</a><a href="/#treatments">전체 시술 안내</a></div></main>'
 page('/treatments/'+p['slug']+'/',f'소프웨이브 {p["topic"]} | 브랜뉴의원',p['excerpt'],body)
def blog(path,chosen,title,extra=''):
 entries=''.join(f'<article><a class="initial-post-image" href="/journal/{p["slug"]}/">{image(posts.index(p))}</a><h2><a href="/journal/{p["slug"]}/">{p["title"]}</a></h2><p class="blog-meta"><time datetime="{DATE}">2026년 9월 30일</time> · 작성자: 브랜뉴의원 시술 안내</p><p class="blog-excerpt">{p["excerpt"]} <a class="blog-read-more" href="/journal/{p["slug"]}/">더 읽기</a></p><p class="blog-category">카테고리 <a href="/category/{p["slug"]}/">{p["topic"]}</a></p></article>' for p in chosen)+extra
 topics='<nav class="blog-topics" aria-label="블로그 카테고리"><div class="related"><a href="/blog/">전체</a>'+''.join(f'<a href="/category/{p["slug"]}/">{p["topic"]}</a>' for p in posts)+'</div></nav>'
 page(path,title+' | 브랜뉴의원','소프웨이브 시술 안내 글을 주제별로 확인하세요.',f'<main class="blog-shell"><h1 class="blog-topic-heading">{title}</h1>{topics}<div class="blog-list">{entries}</div></main>')
blog('/blog/',posts,'브랜뉴의원 블로그')
def md_entry(m):return f'<article><h2><a href="{m["path"]}">{E(m["title"])}</a></h2><p class="blog-meta"><time datetime="{m["stamp"]}">{m["stamp"][:10]}</time> · 브랜뉴의원</p><p class="blog-excerpt">{E(m["description"])} <a class="blog-read-more" href="{m["path"]}">더 읽기</a></p><p class="blog-category">카테고리 <a href="/category/{CATEGORIES[m["category"]]}/">{E(m["category"])}</a></p></article>'
for p in posts:blog('/category/'+p['slug']+'/',[p],'소프웨이브 '+p['topic'],''.join(md_entry(m) for m in md_posts if m['category']==p['topic']))
page('/about/','병원 소개 | 소프웨이브 브랜뉴의원','브랜뉴의원의 소프웨이브 진료 안내와 공식 의료진 소개를 확인하세요.',f'<main class="article"><p class="crumb"><a href="/">홈</a> / 병원 소개</p><h1>브랜뉴의원</h1><p class="lead">소프웨이브와 피부 탄력에 관한 정보를 안내합니다.</p><img class="full-image" src="/images/doctor.jpg" alt="브랜뉴의원 제공 의료진 사진" width="1000" height="667"><h2>상담 전 충분히 살펴보세요</h2><p>이 사이트에서는 소프웨이브의 원리, 시술 과정, 회복과 주의사항을 주제별로 정리했습니다. 궁금한 내용을 읽고 자신의 피부 고민과 이전 시술 기록을 준비해 상담에 활용해 보세요.</p><h2>병원 정보</h2><p>상호: 브랜뉴의원<br>대표자: 윤성은<br>주소: 서울 강남구 압구정로 437 일신빌딩 4층<br>전화: <a href="tel:025113075">02-511-3075</a></p><p><a class="text-link" href="https://brandnewclinic.com/Brandnew-02" target="_blank" rel="noopener noreferrer">공식 홈페이지 의료진 소개</a></p><img class="full-image" src="/images/interior-1.jpg" alt="브랜뉴의원 내부 공간" width="1000" height="667" loading="lazy"><p class="notice">{notice}</p><a class="button" href="/contact/">진료·위치 안내</a></main>')
page('/contact/','오시는 길·진료시간 | 브랜뉴의원','서울 강남구 압구정로 437 일신빌딩 4층. 브랜뉴의원 전화 상담, 네이버 지도, 진료시간 안내.',f'<main class="article"><p class="crumb"><a href="/">홈</a> / 오시는 길</p><h1>진료시간과 오시는 길</h1><p class="lead">브랜뉴의원 · 서울 강남구 압구정로 437<br>일신빌딩 4층</p>{actions}<h2>진료시간</h2>{hours}<h2>방문 전 확인해 주세요</h2><p>당일 예약 가능 여부와 휴진 일정, 주차 및 이동 안내는 병원에 문의해 주세요. 소프웨이브 상담을 예약할 때 현재 피부 상태와 이전 시술 경험을 함께 전달하면 좋습니다.</p><p><a class="text-link" href="https://brandnewclinic.com/Brandnew-03" target="_blank" rel="noopener noreferrer">공식 홈페이지 진료·위치 안내</a></p><p class="notice">{notice}</p></main>')
page('/404/','페이지를 찾을 수 없습니다 | 브랜뉴의원','브랜뉴의원 소프웨이브 안내로 돌아가세요.','<main class="article"><h1>페이지를 찾을 수 없습니다</h1><p>주소를 확인하거나 전체 글 목록에서 원하는 내용을 찾아보세요.</p><a class="button" href="/blog/">블로그 보기</a></main>')
(OUT/'404.html').write_text((OUT/'404/index.html').read_text());urls.remove('/404/')
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{ORIGIN}{u}</loc><lastmod>{DATE}</lastmod></url>' for u in urls)+'</urlset>')
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n')
(OUT/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>소프웨이브 | 브랜뉴의원</title><link>'+ORIGIN+'</link><description>소프웨이브 상담·회복·주의사항 안내</description><language>ko</language>'+''.join(f'<item><title>{escape(p["title"])}</title><link>{ORIGIN}/journal/{p["slug"]}/</link><guid>{ORIGIN}/journal/{p["slug"]}/</guid><description>{escape(p["excerpt"])}</description><pubDate>Wed, 30 Sep 2026 06:30:00 GMT</pubDate></item>' for p in posts)+'</channel></rss>')
print('Built',len(urls),'pages; 6 articles; sitemap, RSS, robots')

from publication.render import render_publications
render_publications(globals())

# The homepage-only presentation pass leaves all publication routes unchanged.
from home_layout import apply as apply_home_layout
apply_home_layout(globals())

# Homepage detail content stays in the normal build flow.
import runpy as _detail_runpy
from pathlib import Path
_detail_runpy.run_path(str(Path(__file__).resolve().parent/'homepage_detail.py'), run_name='__main__')

# Append only the requested homepage budget section.
import runpy as _cost_runpy
from pathlib import Path as _CostPath
_cost_runpy.run_path(str(_CostPath(__file__).resolve().parent/"home_cost_guide.py"),run_name="__main__")

# Preserve first-visit image and stylesheet optimizations after every content build.
import runpy as _speed_runpy
_speed_runpy.run_path(str(ROOT/"scripts/optimize_first_visit.py"), run_name="__main__")

# Live-site keyword pass (ported from adon-company01/build_site.mjs applyBrandnewKeywords): title/brand/og text substitutions
# applied to every dist/*.html and rss.xml after all other stages. Homepage gets the full title/description/h1 swap.
import re as _kw_re
def apply_brandnew_keywords(text,homepage=False):
 title='브랜뉴클리닉ㅣ강남온다리프팅ㅣ강남소프웨이브'
 text=(text.replace('aria-label="브랜뉴의원 소프웨이브 홈"','aria-label="브랜뉴클리닉 강남온다리프팅 강남소프웨이브 홈"')
  .replace('<span>소프웨이브</span>','<span>강남온다리프팅<br>강남소프웨이브</span>')
  .replace('rel="noopener noreferrer">소프웨이브</a></nav>','rel="noopener noreferrer">강남온다리프팅 · 강남소프웨이브</a></nav>')
  .replace('property="og:site_name" content="소프웨이브 | 브랜뉴의원"','property="og:site_name" content="'+title+'"')
  .replace('<channel><title>소프웨이브 | 브랜뉴의원</title>','<channel><title>'+title+'</title>'))
 if homepage:
  desc='강남온다리프팅ㅣ강남소프웨이브ㅣ브랜뉴는 고객 한 분의 아름다움을 만들어 드리기 위해 끊임없이 고민하고 연구합니다. 프라이빗 더마톨로지 브랜뉴클리닉'
  text=_kw_re.sub(r'<title>[^<]*</title>','<title>'+title+'</title>',text,count=1)
  text=_kw_re.sub(r'(<meta\s+property="og:title"\s+content=")[^"]*"',lambda m:m.group(1)+title+'"',text,count=1)
  text=_kw_re.sub(r'(<meta\s+name="description"\s+content=")[^"]*"',lambda m:m.group(1)+desc+'"',text,count=1)
  text=_kw_re.sub(r'(<meta\s+property="og:description"\s+content=")[^"]*"',lambda m:m.group(1)+desc+'"',text,count=1)
  text=text.replace('<h1>소프웨이브, 얼굴선보다 피부 탄력부터 살펴볼 때</h1>','<h1>강남온다리프팅 · 강남소프웨이브</h1>',1)
  text=text.replace('잔주름과 탄력 저하, 볼륨 부족과 깊은 처짐을 구분하는 브랜뉴의원 시술 안내','브랜뉴클리닉 피부 탄력 상담 안내',1)
  assert '<h1>강남온다리프팅 · 강남소프웨이브</h1>' in text,'Brandnew homepage heading not found'
 return text
for _f in sorted(OUT.rglob('*')):
 if _f.is_file() and (_f.suffix=='.html' or _f.name=='rss.xml'):
  _f.write_text(apply_brandnew_keywords(_f.read_text(encoding='utf-8'),_f==OUT/'index.html'),encoding='utf-8')
print('Applied Brandnew keyword substitutions to dist html/rss')

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
