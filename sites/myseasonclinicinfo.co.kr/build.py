import json, html
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape
ROOT=Path(__file__).parent; OUT=ROOT/'dist'; ORIGIN='https://myseasonclinicinfo.co.kr'; DATE='2026-09-30'; NAME='나의계절의원'
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
 return {'id':'md-'+path.stem,'slug':path.stem,'title':meta['title'],'short_title':meta.get('short_title',''),'excerpt':meta['description'],'category':meta['category'],'date':ts[:10],'timestamp':ts,'sections':sections,'body':'\n\n'.join(h+'\n'+c for h,c in sections),'origin':'markdown'}
_md=sorted((ROOT/'content/posts').glob('*.md')) if (ROOT/'content/posts').exists() else []
_now=_dt.datetime.now(_dt.timezone.utc);md_posts=[]
for _f in _md:
 _m=_load_md(_f)
 if _dt.datetime.fromisoformat(_m['timestamp'])>_now:
  _stale=ROOT/'dist/journal'/_m['slug']/'index.html'
  if _stale.exists():_stale.unlink()
  continue
 md_posts.append(_m)
md_posts.sort(key=lambda p:(p['timestamp'],p['slug']),reverse=True)  # newest first, ahead of older manuscripts
nav='<a href="/">대구필러</a><a href="/blog/">블로그</a><a href="/#treatments">시술 안내</a><a href="/about/">병원 소개</a><a href="/contact/">오시는 길</a>'
header=f'<a class="skip-link" href="#site-content">본문 바로가기</a><header class="site-header"><div class="header-inner"><a href="/" class="brand" aria-label="나의계절의원 대구필러 홈"><img class="brand-logo" src="/images/brand-logo.jpg" alt="나의계절의원 로고" width="1000" height="1000"><span>대구필러</span></a><nav class="desktop-menu" aria-label="주 메뉴">{nav}</nav><details class="mobile-menu"><summary>메뉴</summary><nav aria-label="모바일 메뉴">{nav}</nav></details></div></header><nav class="quick-links" aria-label="빠른 안내"><a href="tel:0534247575">전화 상담</a><a href="/contact/">오시는 길</a><a href="#site-content">맨 위로</a></nav>'
notice='시술의 적용 여부와 결과, 회복 기간은 개인에 따라 다릅니다. 시술 후 통증·붓기·붉어짐 등의 이상 반응이 생길 수 있습니다. 본 안내는 개별 진료를 대신하지 않습니다.'
footer=f'<footer class="site-footer"><strong>나의계절의원</strong><p>대구 중구 명륜로23길 106 클래시아 2차 5층 · 대표자 김근영<br>사업자등록번호 896-26-01055<br><a href="tel:0534247575">053-424-7575</a> · <a href="https://myseasonclinic.com/" target="_blank" rel="noopener noreferrer">공식 홈페이지</a> · <a href="https://naver.me/GvfxgcBw" target="_blank" rel="noopener noreferrer">네이버 지도</a></p><p>{notice}</p><p>© 2026 MY SEASON CLINIC · <a href="/">대구필러</a></p></footer>'
favicon='data:image/svg+xml,'+quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#167b86"/><text x="32" y="44" text-anchor="middle" font-family="Arial" font-size="37" font-weight="bold" fill="white">B</text></svg>')
base_schema={'@context':'https://schema.org','@type':'MedicalClinic','@id':ORIGIN+'/#clinic','name':NAME,'url':ORIGIN+'/','telephone':'+82-53-424-7575','image':ORIGIN+'/images/feature-1.jpg','address':{'@type':'PostalAddress','streetAddress':'명륜로23길 106 클래시아 2차 5층','addressLocality':'중구','addressRegion':'대구광역시','addressCountry':'KR'},'sameAs':['https://myseasonclinic.com/','https://naver.me/GvfxgcBw']}
urls=[]
def page(path,title,desc,body,schemas=None):
 schemas=schemas or []
 selected=next((p for p in posts if p["slug"] in path),posts[0])
 pi=posts.index(selected)+1
 og=f'<meta property="og:image" content="{ORIGIN}/images/feature-{pi}.jpg"><meta property="og:image:width" content="900"><meta property="og:image:height" content="900"><meta property="og:image:alt" content="{E(selected["alt"])}">'
 url=ORIGIN+path; dest=OUT/(path.strip('/')+'/index.html' if path!='/' else 'index.html');dest.parent.mkdir(parents=True,exist_ok=True)
 structured=''.join('<script type="application/ld+json">'+json.dumps(s,ensure_ascii=False).replace('</','<\\/')+'</script>' for s in [base_schema]+schemas)
 dest.write_text(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="naver-site-verification" content="34eb6c7df443aba3bd9cf934d470bda94d1fa915"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)}</title><meta name="description" content="{E(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="icon" type="image/png" href="/favicon-transparent.png?v=2"><link rel="stylesheet" href="/style.css"><link rel="alternate" type="application/rss+xml" title="나의계절의원 블로그" href="/rss.xml"><meta property="og:type" content="website"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="대구필러 | 나의계절의원"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}">{og}{structured}</head><body>{header}<div id="site-content">{body}</div>{footer}</body></html>');urls.append(path)
def image(i,cls='',lazy=True):
 return f'<img src="/images/feature-{i+1}.jpg" alt="{E(posts[i]["alt"])}" width="{900 if i<3 else 800}" height="{900 if i<3 else 1000}" loading="{"lazy" if lazy else "eager"}" decoding="async" class="{cls}">'
def card(i):
 p=posts[i];u='/journal/'+p['slug']+'/'
 return f'<li><article class="featured-card"><a class="featured-thumb" href="{u}">{image(i,lazy=i>2)}</a><div class="featured-copy"><h2><a href="{u}">{E(p["title"])}</a></h2><p class="card-meta"><time datetime="{DATE}">2026. 9. 30.</time> · 나의계절의원</p><p class="card-excerpt">{E(p["excerpt"])}</p><a class="card-more" href="{u}" aria-label="{E(p["title"])} 더 읽기">더 읽기</a></div></article></li>'
hours='<dl class="hours"><dt>월·금요일</dt><dd>10:00–20:00</dd><dt>화·수요일</dt><dd>10:00–19:00</dd><dt>목요일</dt><dd>휴무</dd><dt>토요일</dt><dd>10:00–16:00</dd><dt>점심시간</dt><dd>14:00–15:00</dd></dl><p class="muted">공식 홈페이지 안내 기준 · 피부관리 마감, 토요일 점심시간 및 휴일 진료는 방문 전 전화로 확인해 주세요.</p>'

actions='<div class="clinic-actions"><a href="tel:0534247575">053-424-7575 전화 상담</a><a href="https://naver.me/GvfxgcBw" target="_blank" rel="noopener noreferrer">네이버 지도에서 위치 확인</a><a href="https://myseasonclinic.com/" target="_blank" rel="noopener noreferrer">공식 홈페이지</a></div>'
source='<aside class="source-links"><p>참고 자료</p><p><a href="https://myseasonclinic.com/contents/03_filler/sub01.html" target="_blank" rel="noopener noreferrer">나의계절의원 필러 공식 안내</a> · <a href="https://www.fda.gov/medical-devices/aesthetic-cosmetic-devices/dermal-fillers-soft-tissue-fillers" target="_blank" rel="noopener noreferrer">필러 일반 안전 정보(FDA)</a></p><p>제품별 국내 허가 범위와 개인별 주의사항은 진료 시 확인하세요. 제공 사진은 병원·행사·시술 소개 자료이며 개인의 시술 결과를 보여주는 사진이 아닙니다.</p></aside>'

itemlist={'@context':'https://schema.org','@type':'ItemList','name':'대구필러 주요 안내 6편','itemListOrder':'https://schema.org/ItemListOrderAscending','numberOfItems':6,'itemListElement':[{'@type':'ListItem','position':i+1,'url':ORIGIN+'/journal/'+p['slug']+'/','name':p['title'],'image':ORIGIN+f'/images/feature-{i+1}.jpg'} for i,p in enumerate(posts)]}
summary=''.join(f'<div class="treatment-summary"><h3><a href="/treatments/{p["slug"]}/">대구필러 {p["topic"]} 안내</a></h3><p>{p["excerpt"]}</p><a class="text-link" href="/treatments/{p["slug"]}/">더 읽기</a></div>' for p in posts)
home=f'<main class="home-shell"><section class="featured-section" aria-label="대구필러 대표 안내"><ul class="featured-list">{"".join(card(i) for i in range(6))}</ul><div class="more-row"><a class="more-button" href="/blog/">글 더보기</a></div></section><section class="clinic-gallery" aria-label="나의계절의원 병원 공간"><img src="/images/interior-1.jpg" alt="나의계절의원 내부 공간" width="1000" height="667" loading="lazy"><img src="/images/interior-2.jpg" alt="나의계절의원 진료 공간" width="1000" height="667" loading="lazy"></section><section class="home-intro" id="treatments"><h1>대구필러</h1><p>나의계절의원 필러 안내. 상담에서 확인할 질문부터 부위별 고민, 제품과 주의사항까지 살펴보세요.</p><p class="eyebrow">FILLER · 01—06</p><h2>궁금한 내용부터 살펴보세요</h2>{summary}<p class="notice">{notice}</p></section><section class="clinic-info"><h2>나의계절의원 진료·위치 안내</h2><p>대구 중구 명륜로23길 106 클래시아 2차 5층</p>{hours}{actions}<p><a class="text-link" href="/contact/">진료시간과 오시는 길</a></p></section></main>'
page('/','대구필러 | 나의계절의원','대구필러 상담 전 확인사항과 부위별 필러 안내. 나의계절의원 진료시간·위치와 피부 건강정보를 확인하세요.',home,[itemlist])
for i,p in enumerate(posts):
 path='/journal/'+p['slug']+'/';schema={'@context':'https://schema.org','@type':'BlogPosting','headline':p['title'],'description':p['excerpt'],'datePublished':DATE+'T17:22:48+09:00','dateModified':DATE+'T17:22:48+09:00','image':ORIGIN+f'/images/feature-{i+1}.jpg','author':{'@type':'Organization','name':'나의계절의원 시술 안내'},'mainEntityOfPage':ORIGIN+path,'publisher':{'@id':ORIGIN+'/#clinic'}}
 toc='<nav class="toc" aria-label="글 목차"><strong>이 글에서 확인할 내용</strong><ol>'+''.join(f'<li><a href="#section-{j}">{E(h)}</a></li>' for j,(h,t) in enumerate(p['sections']))+'</ol></nav>'
 sections=''.join(f'<section id="section-{j}"><h2>{E(h)}</h2><p>{E(t)}</p></section>' for j,(h,t) in enumerate(p['sections']))
 related=''.join(f'<a href="/journal/{q["slug"]}/">{q["topic"]}</a>' for q in posts if q!=p)
 body=f'<main class="article journal-article"><p class="crumb"><a href="/">홈</a> / <a href="/blog/">블로그</a> / {p["topic"]}</p><header class="entry-header"><h1>{p["title"]}</h1><p class="blog-meta"><time datetime="{DATE}">2026년 9월 30일</time> · 나의계절의원 시술 안내</p></header><p class="lead">{p["excerpt"]}</p><figure class="article-photo">{image(i)}<figcaption>나의계절의원 제공 자료</figcaption></figure>{toc}{sections}<p class="notice">{notice}</p>{source}<nav class="related" aria-label="관련 글">{related}</nav><p><a class="text-link" href="/">대구필러</a> · <a class="text-link" href="/blog/">전체 글 보기</a> · <a class="text-link" href="/contact/">상담·오시는 길</a></p></main>'
 page(path,p['title']+' | 나의계절의원',p['excerpt'],body,[schema])
 body=f'<main class="article"><p class="crumb"><a href="/">홈</a> / 시술 안내</p><h1>대구필러 {p["topic"]}</h1><p class="lead">{p["excerpt"]}</p><h2>상담 전 살펴볼 내용</h2><ul>'+''.join(f'<li>{h}</li>' for h,t in p['sections'])+f'</ul><p>현재 피부 상태와 기존 시술 경험을 함께 확인한 뒤 계획을 결정합니다. 아래 상세 안내에서 질문을 정리해 보세요.</p><p><a class="button" href="/journal/{p["slug"]}/">{p["topic"]} 상세 안내 읽기</a></p><p class="notice">{notice}</p><div class="related"><a href="/contact/">상담 안내</a><a href="/#treatments">전체 시술 안내</a></div></main>'
 page('/treatments/'+p['slug']+'/',f'대구필러 {p["topic"]} | 나의계절의원','나의계절의원 '+p['topic']+' 시술 안내. '+p['excerpt'],body)
def blog(path,chosen,title,extra=''):
 entries=''.join(f'<article><a class="initial-post-image" href="/journal/{p["slug"]}/">{image(posts.index(p))}</a><h2><a href="/journal/{p["slug"]}/">{p["title"]}</a></h2><p class="blog-meta"><time datetime="{DATE}">2026년 9월 30일</time> · 작성자: 나의계절의원 시술 안내</p><p class="blog-excerpt">{p["excerpt"]} <a class="blog-read-more" href="/journal/{p["slug"]}/">더 읽기</a></p><p class="blog-category">카테고리 <a href="/category/{p["slug"]}/">{p["topic"]}</a></p></article>' for p in chosen)+extra
 topics='<nav class="blog-topics" aria-label="블로그 카테고리"><div class="related"><a href="/blog/">전체</a>'+''.join(f'<a href="/category/{p["slug"]}/">{p["topic"]}</a>' for p in posts)+'</div></nav>'
 page(path,title+' | 나의계절의원',title+' — 상담 질문과 부위별 확인사항을 글 목록에서 살펴보세요.',f'<main class="blog-shell"><h1 class="blog-topic-heading">{title}</h1>{topics}<div class="blog-list">{entries}</div></main>')
blog('/blog/',posts,'나의계절의원 블로그')
def md_entry(m):return f'<article><h2><a href="/journal/{m["slug"]}/">{E(m["title"])}</a></h2><p class="blog-meta">{m["date"]} · 나의계절의원</p><p>{E(m["excerpt"])} <a href="/journal/{m["slug"]}/">더 읽기</a></p><p class="blog-category">카테고리 <a href="/category/{CATEGORIES[m["category"]]}/">{E(m["category"])}</a></p></article>'
for p in posts:blog('/category/'+p['slug']+'/',[p],'대구필러 '+p['topic']+' 글 모음',''.join(md_entry(m) for m in md_posts if m['category']==p['topic']))
page('/about/','병원 소개 | 대구필러 나의계절의원','나의계절의원의 대구필러 진료 안내와 공식 의료진 소개를 확인하세요.',f'<main class="article"><p class="crumb"><a href="/">홈</a> / 병원 소개</p><h1>나의계절의원</h1><p class="lead">대구필러 상담과 부위별 시술 정보를 안내합니다.</p><img class="full-image" src="/images/doctor.jpg" alt="나의계절의원 제공 의료진 사진" width="574" height="864"><h2>상담 전 충분히 살펴보세요</h2><p>이 사이트에서는 필러 상담 기준, 제품 확인, 부위별 고민과 주의사항을 주제별로 정리했습니다. 궁금한 내용을 읽고 자신의 피부 고민과 이전 시술 기록을 준비해 상담에 활용해 보세요.</p><h2>병원 정보</h2><p>상호: 나의계절의원<br>대표자: 김근영<br>주소: 대구 중구 명륜로23길 106 클래시아 2차 5층<br>전화: <a href="tel:0534247575">053-424-7575</a></p><p><a class="text-link" href="https://myseasonclinic.com/contents/01_company/sub02.html" target="_blank" rel="noopener noreferrer">공식 홈페이지 의료진 소개</a></p><img class="full-image" src="/images/interior-1.jpg" alt="나의계절의원 내부 공간" width="1000" height="667" loading="lazy"><p class="notice">{notice}</p><a class="button" href="/contact/">진료·위치 안내</a></main>')
page('/contact/','오시는 길·진료시간 | 나의계절의원','대구 중구 명륜로23길 106 클래시아 2차 5층. 나의계절의원 전화 상담, 네이버 지도, 진료시간 안내.',f'<main class="article"><p class="crumb"><a href="/">홈</a> / 오시는 길</p><h1>진료시간과 오시는 길</h1><p class="lead">나의계절의원 · 대구 중구 명륜로23길 106<br>클래시아 2차 5층</p>{actions}<h2>진료시간</h2>{hours}<h2>방문 전 확인해 주세요</h2><p>당일 예약 가능 여부와 휴진 일정, 주차 및 이동 안내는 병원에 문의해 주세요. 대구필러 상담을 예약할 때 현재 피부 상태와 이전 시술 경험을 함께 전달하면 좋습니다.</p><p><a class="text-link" href="https://myseasonclinic.com/contents/01_company/sub03.html" target="_blank" rel="noopener noreferrer">공식 홈페이지 진료·위치 안내</a></p><p class="notice">{notice}</p></main>')
page('/404/','페이지를 찾을 수 없습니다 | 나의계절의원','나의계절의원 대구필러 안내로 돌아가세요.','<main class="article"><h1>페이지를 찾을 수 없습니다</h1><p>주소를 확인하거나 전체 글 목록에서 원하는 내용을 찾아보세요.</p><a class="button" href="/blog/">블로그 보기</a></main>')
(OUT/'404.html').write_text((OUT/'404/index.html').read_text());urls.remove('/404/')
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{ORIGIN}{u}</loc><lastmod>{DATE}</lastmod></url>' for u in urls)+'</urlset>')
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n')
(OUT/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>대구필러 | 나의계절의원</title><link>'+ORIGIN+'</link><description>대구필러 상담·회복·주의사항 안내</description><language>ko</language>'+''.join(f'<item><title>{escape(p["title"])}</title><link>{ORIGIN}/journal/{p["slug"]}/</link><guid>{ORIGIN}/journal/{p["slug"]}/</guid><description>{escape(p["excerpt"])}</description><pubDate>Wed, 30 Sep 2026 08:22:48 GMT</pubDate></item>' for p in posts)+'</channel></rss>')
print('Built',len(urls),'pages; 6 articles; sitemap, RSS, robots')

from publication_renderer import enrich
enrich(globals())

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
