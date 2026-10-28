import json, html, os, re, math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
cfg=json.loads((ROOT/'site-config.json').read_text())
pages=json.loads((ROOT/'content/pages.json').read_text())
post_records=json.loads((ROOT/'content/posts.json').read_text())
now=datetime.now(timezone.utc)
def publishable(post):
    if post.get('status')!='published':return False
    if post.get('publishAt'):
        at=datetime.fromisoformat(post['publishAt'].replace('Z','+00:00'))
        assert at.tzinfo is not None, 'publishAt must include a timezone'
        if at>now:return False
    return True
assert all(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p['slug']) for p in post_records), 'Invalid post slug'
assert len({p['slug'] for p in post_records})==len(post_records), 'Duplicate post slug'
posts=[p for p in post_records if publishable(p)]
# Markdown posts (content/posts/*.md): frontmatter + '## ' sections, same format as the other info sites.
MD_CATEGORIES={'임플란트','충치·신경치료','심미보철','턱관절·예방','사랑니발치'}
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
    assert meta.get('category') in MD_CATEGORIES,('category',meta.get('category'),path)
    assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',path.stem),('slug',path)
    return {'slug':path.stem,'title':meta['title'],'short_title':meta.get('short_title',''),'description':meta['description'],'category':meta['category'],'imageKey':'consultation','textOnly':True,'sections':sections,'status':'published','publishAt':meta['date'],'publishedAt':meta['date'],'origin':'markdown'}
_md=sorted((ROOT/'content/posts').glob('*.md')) if (ROOT/'content/posts').exists() else []
_seen={p['slug'] for p in post_records}
for _f in _md:
    _post=_load_md(_f);assert _post['slug'] not in _seen,('duplicate slug',_f);_seen.add(_post['slug'])
    if publishable(_post):posts.append(_post)
    else:
        _stale=OUT/'blog'/_post['slug']/'index.html'
        if _stale.exists():_stale.unlink()
# Older reviewed reserve records used editorial labels that predate the five
# public category routes. Normalize those labels only for rendered output;
# source records and their reviewed hashes remain immutable.
category_aliases={
    '소아 치과':'턱관절·예방',
    '소아 치아':'턱관절·예방',
    '어린이 구강관리':'턱관절·예방',
    '충치 치료':'충치·신경치료',
    '예방·관리':'턱관절·예방',
    '진료 전 확인':'턱관절·예방',
    '검사·진단':'턱관절·예방',
    '소아·청소년 치아':'턱관절·예방',
    '충치·예방':'턱관절·예방',
    '턱관절·교합':'턱관절·예방',
    '치과검사 이해':'턱관절·예방',
    '치과진료 준비':'턱관절·예방',
    '충치치료 이해':'충치·신경치료',
    '충치치료':'충치·신경치료',
    '치과검진':'턱관절·예방',
    '구강관리 습관':'턱관절·예방',
    '잇몸 관리':'턱관절·예방',
    '미백·생활 습관':'심미보철',
    '치아마모·시림':'턱관절·예방',
}
for post in posts:
    post['category']=category_aliases.get(post['category'],post['category'])
def post_date(post):
    value=post.get('publishedAt') or post.get('publishAt') or cfg['updatedAt']+'T12:00:00+09:00'
    at=datetime.fromisoformat(value.replace('Z','+00:00'))
    assert at.tzinfo is not None, 'publishedAt must include a timezone'
    return at.astimezone(ZoneInfo('Asia/Seoul'))
posts.sort(key=post_date,reverse=True)
extra=json.loads((ROOT/'content/site-sections.json').read_text())
image_sources=json.loads((ROOT/'content/image-sources.json').read_text())
previous_routes=json.loads((ROOT/'content/route-manifest.json').read_text()) if (ROOT/'content/route-manifest.json').exists() else []
origin=cfg['origin'].rstrip('/')
indexing=cfg['indexingEnabled']
if indexing:
    assert cfg['customDomainConfirmed'] and cfg['naverVerification'], 'Confirm domain and ownership verification before enabling indexing'
E=lambda s:html.escape(str(s),quote=True)
J=lambda d:json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
url=lambda path:origin+path
all_routes=[]
categories={'implant':'임플란트','cavity':'충치·신경치료','aesthetic':'심미보철','prevention':'턱관절·예방','wisdom-tooth':'사랑니발치'}
published_categories={k:v for k,v in categories.items() if any(p['category']==v for p in posts)}
site_css=(OUT/'styles.css').read_text()
site_js=(OUT/'site.js').read_text()
assert '</style' not in site_css.lower() and '</script' not in site_js.lower()

def image_alt(key):
    return next((p['alt'] for p in pages if p.get('imageKey')==key),image_sources.get(key,{}).get('alt','새론이치과 진료 안내 이미지'))

def image(key,alt,wide=False,priority=False,sizes=None):
    suffix='-wide' if wide else ''
    width,height=(1200,630) if wide else (1024,1024)
    attrs='fetchpriority="high"' if priority else 'loading="lazy"'
    sizes=sizes or ('(max-width:800px) calc(100vw - 40px), 800px' if wide else '(max-width:800px) 77vw, 380px')
    small='-wide-small' if wide else '-small'
    small_width=600 if wide else 480
    source=f'<source type="image/webp" srcset="/images/{key}{small}.webp {small_width}w, /images/{key}{suffix}.webp {width}w" sizes="{E(sizes)}">'
    return f'<picture>{source}<img src="/images/{key}{suffix}.jpg" srcset="/images/{key}{small}.jpg {small_width}w, /images/{key}{suffix}.jpg {width}w" sizes="{E(sizes)}" alt="{E(alt)}" width="{width}" height="{height}" {attrs} decoding="async"></picture>'

def breadcrumb_items(path,title):
    items=[('김해치과','/')]
    if path.startswith('/blog/') and path!='/blog/':items.append(('블로그','/blog/'))
    post=next((p for p in posts if path=='/blog/'+p['slug']+'/'),None)
    if post:
        key=next(k for k,v in categories.items() if v==post['category'])
        items.append((post['category']+' 건강정보','/blog/category/'+key+'/'))
    if path!='/':items.append((title,path))
    return items

def breadcrumb(path,title):
    items=breadcrumb_items(path,title)
    return '<nav class="breadcrumb" aria-label="현재 위치">'+'<span aria-hidden="true">›</span>'.join(f'<a href="{E(p)}">{E(t)}</a>' if i<len(items)-1 else f'<span aria-current="page">{E(t)}</span>' for i,(t,p) in enumerate(items))+'</nav>'

def nav(active=''):
    links=[('/','김해치과'),('/clinic/','치과소개'),('/blog/','블로그'),('/hours/','오시는 길')]
    out=''.join(f'<a href="{p}"'+(' aria-current="page"' if p==active else '')+f'>{t}</a>' for p,t in links)
    return f'''<a class="skip" href="#content">본문 바로가기</a><div class="utility"><div class="wrap"><span>화·목 21:00까지 야간진료</span><a href="tel:0557242833">055-724-2833</a></div></div><header class="header"><div class="wrap"><a class="brand" href="/" aria-label="김해치과 새론이치과의원 홈"><span class="site-keyword">김해치과</span><span class="bar" aria-hidden="true"></span><img src="/images/saeroni-logo-ai.svg" width="860" height="175" alt="새론이치과의원"></a><button class="menu-toggle" type="button" aria-controls="site-nav" aria-expanded="false">메뉴</button><nav class="nav" id="site-nav" aria-label="주 메뉴">{out}</nav></div></header>'''

def footer():
    return f'''<footer class="footer"><div class="wrap"><div class="footer-top"><div><h2>새론이치과의원</h2><p>{E(cfg['address'])}</p><p>대표자 황수정 · 사업자등록번호 177-22-02159</p><p>대표전화 <a href="tel:0557242833">055-724-2833</a></p></div><div class="footer-links"><a href="{cfg['officialUrl']}" target="_blank" rel="noopener">공식 홈페이지</a><a href="https://blog.naver.com/saero2024" target="_blank" rel="noopener">네이버 블로그</a><a href="{cfg['reservationUrl']}" target="_blank" rel="noopener">네이버 예약</a></div></div><div class="disclaimer">이 사이트는 새론이치과의 진료 안내와 일반적인 치아 건강정보를 제공합니다. 치료 방법, 기간과 결과는 개인의 구강 및 전신 건강 상태에 따라 다릅니다. 정확한 진단과 치료 계획은 치과의사의 진료를 통해 확인해 주세요.<br>진료시간은 병원 사정에 따라 변경될 수 있으니 방문 전 확인해 주세요.<p>© 2026 새론이치과의원</p></div></div></footer><div class="mobile-call"><a href="tel:0557242833">전화 문의</a><a href="{cfg['reservationUrl']}" target="_blank" rel="noopener">네이버 예약</a></div><script src="/site.js" defer></script>'''

def schema(path,title,desc,img,article=False,img_alt=''):
    org={'@type':'Dentist','@id':url('/#clinic'),'name':cfg['businessName'],'url':url('/'),'telephone':'+82-55-724-2833','image':url('/images/clinic-photo.jpg'),'logo':url('/images/saeroni-logo-ai.svg'),'address':{'@type':'PostalAddress','streetAddress':'내외중앙로 68, 3층','addressLocality':'김해시','addressRegion':'경상남도','addressCountry':'KR'},'sameAs':[cfg['officialUrl'],'https://blog.naver.com/saero2024',cfg['reservationUrl']],'openingHoursSpecification':[{'@type':'OpeningHoursSpecification','dayOfWeek':['Monday','Wednesday','Friday'],'opens':'10:00','closes':'19:00'},{'@type':'OpeningHoursSpecification','dayOfWeek':['Tuesday','Thursday'],'opens':'10:00','closes':'21:00'},{'@type':'OpeningHoursSpecification','dayOfWeek':['Saturday'],'opens':'10:00','closes':'14:00'}]}
    org['openingHoursSpecification']=[
        {'@type':'OpeningHoursSpecification','dayOfWeek':['Monday','Tuesday','Wednesday','Thursday','Friday'],'opens':'10:00','closes':'13:00'},
        {'@type':'OpeningHoursSpecification','dayOfWeek':['Monday','Wednesday','Friday'],'opens':'14:00','closes':'19:00'},
        {'@type':'OpeningHoursSpecification','dayOfWeek':['Tuesday','Thursday'],'opens':'14:00','closes':'21:00'},
        {'@type':'OpeningHoursSpecification','dayOfWeek':['Saturday'],'opens':'10:00','closes':'14:00'}]
    website={'@type':'WebSite','@id':url('/#website'),'name':'김해치과','alternateName':'새론이치과의원','url':url('/'),'inLanguage':'ko-KR','publisher':{'@id':url('/#clinic')}}
    webpage={'@type':'WebPage','@id':url(path+'#webpage'),'url':url(path),'name':title,'description':desc,'inLanguage':'ko-KR','isPartOf':{'@id':url('/#website')},'primaryImageOfPage':{'@type':'ImageObject','url':url(img)}}
    webpage['primaryImageOfPage'].update({'width':1200 if '-wide.' in img else 1024,'height':630 if '-wide.' in img else 1024,'caption':img_alt or title})
    if path.startswith('/blog/') and not article:webpage['@type']='CollectionPage'
    graph=[org,website,webpage]
    if path!='/':
        crumbs=[{'@type':'ListItem','position':i+1,'name':t,'item':url(p)} for i,(t,p) in enumerate(breadcrumb_items(path,title))]
        webpage['breadcrumb']={'@id':url(path+'#breadcrumb')}
        graph.append({'@type':'BreadcrumbList','@id':url(path+'#breadcrumb'),'itemListElement':crumbs})
    if article:
        post=next(p for p in posts if path=='/blog/'+p['slug']+'/')
        graph.append({'@type':'BlogPosting','headline':title,'description':desc,'image':url(img),'url':url(path),'mainEntityOfPage':{'@id':url(path+'#webpage')},'datePublished':post_date(post).isoformat(),'dateModified':post.get('modifiedAt',post_date(post).isoformat()),'author':{'@type':'Organization','name':'새론이치과의원'},'publisher':{'@id':url('/#clinic')}})
    scripts=f'<script type="application/ld+json">{J({"@context":"https://schema.org","@graph":graph})}</script>'
    if path=='/':
        items=[{'@type':'ListItem','position':i+1,'name':p['title'],'url':url('/'+p['slug']+'/'),'image':url('/images/'+p.get('imageKey',p['slug'])+'.jpg')} for i,p in enumerate(pages)]
        data={'@context':'https://schema.org','@type':'ItemList','name':'김해치과 새론이치과 주요 안내','numberOfItems':len(items),'itemListOrder':'https://schema.org/ItemListOrderAscending','itemListElement':items}
        scripts+=f'<script type="application/ld+json">{J(data)}</script>'
    return scripts

def write_page(path,title,desc,body,img='/images/home-wide.jpg',article=False,img_alt='새론이치과 의료진의 진료 모습',short_title=''):
    fulltitle=short_title if short_title else title if path=='/' else title+' | 새론이치과의원'
    ogtitle=short_title or title
    robots='index,follow,max-image-preview:large' if indexing else 'noindex,nofollow,max-image-preview:large'
    if path=='/404.html':robots='noindex,nofollow'
    width,height=(1200,630) if '-wide.' in img else (1024,1024)
    icon='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#008cce"/><text x="32" y="45" text-anchor="middle" font-size="43" font-family="Arial" font-weight="700" fill="white">S</text></svg>'
    verification=f'<meta name="naver-site-verification" content="{E(cfg["naverVerification"])}">' if cfg['naverVerification'] else ''
    doc=f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(fulltitle)}</title><meta name="description" content="{E(desc)}"><meta name="robots" content="{robots}"><meta name="theme-color" content="#008cce"><meta name="application-name" content="김해치과"><link rel="canonical" href="{url(path)}"><link rel="icon" type="image/svg+xml" href="/images/favicon-ai.svg"><link rel="icon" sizes="32x32" href="/favicon.ico"><link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png"><link rel="stylesheet" href="/styles.css"><noscript><style>.menu-toggle,.arrows{{display:none}}@media(max-width:800px){{.nav{{display:flex}}}}</style></noscript><link rel="alternate" type="application/rss+xml" title="새론이치과 치아 건강정보" href="{url('/rss.xml')}"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="{E(cfg['siteName'])}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:title" content="{E(ogtitle)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url(path)}"><meta property="og:image" content="{url(img)}"><meta property="og:image:width" content="{width}"><meta property="og:image:height" content="{height}"><meta property="og:image:type" content="image/jpeg"><meta property="og:image:alt" content="{E(img_alt)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(ogtitle)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{url(img)}"><meta name="twitter:image:alt" content="{E(img_alt)}">{verification}{schema(path,title,desc,img,article,img_alt)}</head><body>{nav(path)}<main id="content">{body}</main>{footer()}</body></html>'''
    # Keep first paint and menu controls independent of additional authenticated requests.
    doc=doc.replace('<link rel="stylesheet" href="/styles.css">','<style id="site-styles">'+site_css+'</style>')
    doc=doc.replace('<script src="/site.js" defer></script>','<script id="site-controls">'+site_js+'</script>')
    target=OUT/'index.html' if path=='/' else OUT/path.lstrip('/')/'index.html' if path.endswith('/') else OUT/path.lstrip('/')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(doc)
    if path!='/404.html':
        lastmod=post_date(next(p for p in posts if path=='/blog/'+p['slug']+'/')).date().isoformat() if article else (max([cfg.get('blogUpdatedAt',cfg['updatedAt'])]+[post_date(p).date().isoformat() for p in posts]) if path.startswith('/blog/') else cfg['updatedAt'])
        all_routes.append({'path':path,'title':title,'description':desc,'image':img,'lastmod':lastmod})

def cards():
    out=''
    for i,p in enumerate(pages):
        out+=f'''<article class="card" data-carousel-card><a href="/{p['slug']}/"><div class="card-image">{image(p.get('imageKey',p['slug']),p['alt'],priority=i==0)}</div><p class="kicker">0{i+1} / {E(p['category'])}</p><h2>{E(p['title'])}</h2><p>{E(p['description'])}</p><span class="readmore">자세히 보기 →</span></a></article>'''
    return '<div class="carousel" id="main-carousel" tabindex="0" role="region" aria-label="새론이치과 주요 안내 6개">'+out+'</div>'

def arrows():return '<div class="arrows"><span class="carousel-status" aria-live="polite" aria-atomic="true">1 / 6</span><button type="button" data-carousel-direction="-1" aria-controls="main-carousel" aria-label="이전 안내 보기" disabled>‹</button><button type="button" data-carousel-direction="1" aria-controls="main-carousel" aria-label="다음 안내 보기">›</button></div>'

def hours():
    return '''<table class="hours"><caption class="sr-only">새론이치과 요일별 진료시간</caption><tbody><tr><th scope="row">월 · 수 · 금</th><td>10:00 – 19:00</td></tr><tr class="night"><th scope="row">화 · 목 / 야간진료</th><td>10:00 – 21:00</td></tr><tr><th scope="row">토요일</th><td>10:00 – 14:00</td></tr><tr><th scope="row">점심시간</th><td>13:00 – 14:00</td></tr><tr><th scope="row">일요일 · 공휴일</th><td>휴진</td></tr></tbody></table><p class="note">토요일은 점심시간 없이 진료합니다.<br>방문 전 접수 가능 시간과 진료 일정을 확인해 주세요.</p>'''

def visit():
    return f'''<section class="section tint" id="visit-hours"><div class="wrap visit"><div><p class="eyebrow">HOURS</p><h2>내 일정에 맞춰, 진료시간</h2>{hours()}</div><div><p class="eyebrow">LOCATION</p><h2>새론이치과 오시는 길</h2><p class="address">경남 김해시 내외중앙로 68<br>3층, 우리은행 옆</p><p>치과 옆 대호주차장 이용 가능</p><a class="phone" href="tel:0557242833">055-724-2833</a><div class="actions"><a class="btn" href="{cfg['reservationUrl']}" target="_blank" rel="noopener">네이버 예약·지도</a><a class="btn outline" href="/hours/">진료시간 자세히</a></div></div></div></section>'''

def doctors():
    docs=[('황수정','대표원장','통합치의학 전문의','조선대학교 치의학 석사','1'),('오준석','원장','경북대학교 치과대학 졸업','부산대학교 치과병원 인턴 수료','3')]
    return '<div class="doctors">'+''.join(f'<article class="doctor"><div class="photo"><img src="/images/docSec_pu{n}_img.webp" width="480" height="{532 if n=="3" else 567}" alt="새론이치과 {name} {role}" loading="lazy"></div><div><h3>{name} <span>{role}</span></h3><p>{a}</p><p>{b}</p></div></article>' for name,role,a,b,n in docs)+'</div>'

def postcard(p):
    return f'''<article class="card"><a href="/blog/{p['slug']}/"><div class="card-image">{image(p['imageKey'],image_alt(p['imageKey']),wide=True,sizes='(max-width:480px) calc(100vw - 40px), (max-width:800px) calc((100vw - 56px) / 2), 380px')}</div><p class="kicker">{E(p['category'])}</p><h2>{E(p['title'])}</h2><p>{E(p['description'])}</p><span class="readmore">내용 읽기 →</span></a></article>'''

def care_overview():
    items=''.join(f'<article class="care-item"><h3><a href="{path}">{E(title)} <span aria-hidden="true">↗</span></a></h3><p>{E(text)}</p></article>' for title,path,text in extra['care'])
    return '<section class="section" id="treatments"><div class="wrap"><p class="eyebrow">DENTAL CARE</p><h2>김해 새론이치과에서 상담하는 진료</h2><p class="section-lead">불편한 부위와 기존 치료를 함께 살피고, 현재 상태에 필요한 진료를 이야기합니다.</p><div class="care-grid">'+items+'</div></div></section>'

def environment():
    return '<section class="section tint" id="environment"><div class="wrap"><p class="eyebrow">CLINIC ENVIRONMENT</p><h2>구강 정보를 확인하고, 진료 환경을 관리합니다</h2><div class="health-grid">'+''.join(f'<article class="health-item"><h3>{E(t)}</h3><p>{E(s)}</p></article>' for t,s in extra['environment'])+'</div><a class="readmore" href="/clinic/">진료 공간과 의료진 알아보기 →</a></div></section>'

def visit_preparation():
    steps=''.join(f'<li><h3>{E(t)}</h3><p>{E(s)}</p></li>' for t,s in extra['visitSteps'])
    checklist=''.join(f'<li>{E(s)}</li>' for s in extra['checklist'])
    return '<section id="first-visit" class="first-visit"><h2>처음 방문하신다면</h2><ol class="visit-steps">'+steps+'</ol><div class="preparation"><h3>상담 전에 정리해 오시면 좋아요</h3><ul>'+checklist+'</ul></div></section>'

def faq():
    return '<section id="visit-faq" class="faq"><h2>방문 전 자주 묻는 질문</h2>'+''.join(f'<details><summary>{E(q["question"])}</summary><p>{E(q["answer"])}</p></details>' for q in extra['faqs'])+'</section>'

def business_table():
    return f'<section id="clinic-information"><h2>새론이치과 기본 정보</h2><table class="business-table"><caption class="sr-only">병원명, 대표자, 사업자등록번호와 주소 안내</caption><tbody><tr><th scope="row">병원명</th><td>{E(cfg["businessName"])}</td></tr><tr><th scope="row">대표자</th><td>황수정</td></tr><tr><th scope="row">사업자등록번호</th><td>177-22-02159</td></tr><tr><th scope="row">주소</th><td>{E(cfg["address"])}</td></tr><tr><th scope="row">대표전화</th><td><a href="tel:0557242833">055-724-2833</a></td></tr><tr><th scope="row">주차</th><td>치과 옆 대호주차장 · 이용 조건은 방문 전 문의</td></tr></tbody></table></section>'

home=f'''<div class="wrap"><div class="pagehead"><p class="eyebrow">SAERON E DENTAL CLINIC</p><h1>김해치과</h1><p class="lead">새론이치과의 진료 안내와 치아 건강정보를 만나보세요.</p></div><div class="section-title"><h2>새론이치과 주요 안내</h2>{arrows()}</div>{cards()}<section class="intro"><div><p class="eyebrow">SINCE 2016</p><h2>가족의 치아 건강을<br>함께 생각합니다.</h2><p>김해에서 이어온 진료, 새론이치과의원.<br>지금의 구강 상태를 살피고 필요한 치료와 관리 방법을 함께 이야기합니다.</p><div class="tagline"><span><strong>2인</strong> 의료진 협진</span><span><strong>21시</strong> 화·목 야간진료</span></div><div class="actions"><a class="btn outline" href="/clinic/">치과소개 보기</a></div></div><div>{image('home','새론이치과 의료진의 진료 모습',wide=True)}</div></section></div><section class="section tint"><div class="wrap"><div class="section-title"><div><p class="eyebrow">OUR DOCTORS</p><h2>새론이치과 의료진</h2></div><a class="readmore" href="/clinic/">의료진 소개 →</a></div>{doctors()}</div></section><section class="section"><div class="wrap"><div class="section-title"><h2>알아두면 좋은 치아 이야기</h2><a class="readmore" href="/blog/">전체 글 보기 →</a></div><div class="health-grid">{''.join(f'<article class="health-item"><span class="pill">{E(p["category"])}</span><h3><a href="/blog/{p["slug"]}/">{E(p["title"])}</a></h3><p>{E(p["description"])}</p><a class="readmore" href="/blog/{p["slug"]}/">내용 읽기 →</a></article>' for p in posts[:3])}</div></div></section>{visit()}'''
home=home.replace('<div class="section-title"><h2>새론이치과 주요 안내</h2>', '<nav class="quick-links" aria-label="메인 페이지 바로가기"><a href="#treatments">진료 안내</a><a href="#environment">진료 환경</a><a href="#visit-hours">시간·위치</a><a href="#first-visit">첫 방문</a><a href="#visit-faq">자주 묻는 질문</a></nav><div class="section-title"><h2>새론이치과 주요 안내</h2>')
home=home.replace('<h2>새론이치과 의료진</h2>','<h2>2인 의료진 협진</h2>')
home=home.replace('<section class="section"><div class="wrap"><div class="section-title"><h2>알아두면 좋은 치아 이야기</h2>',care_overview()+environment()+'<section class="section"><div class="wrap"><div class="section-title"><h2>알아두면 좋은 치아 이야기</h2>')
home+='<div class="wrap section visitor-guide">'+visit_preparation()+faq()+business_table()+'</div>'
write_page('/','김해치과 · 김해임플란트 | 새론이치과의원','김해치과·김해임플란트 새론이치과의원. 임플란트·충치치료·심미보철·사랑니발치, 의료진과 진료시간·위치를 안내합니다.',home)

def sections_html(sections):return ''.join(f'<section id="section-{i+1}"><h2>{E(t)}</h2>'+''.join('<p>'+E(par)+'</p>' for par in s.split('\n\n') if par.strip())+'</section>' for i,(t,s) in enumerate(sections))

def contents(p):
    items=[(t,'section-'+str(i+1)) for i,(t,s) in enumerate(p['sections'])]
    if p['slug']=='clinic':items.append(('의료진 소개','medical-team'))
    if p['slug']=='hours':items += [('요일별 진료시간','weekly-hours'),('첫 방문 준비','first-visit'),('자주 묻는 질문','visit-faq')]
    return '<nav class="article-contents" aria-label="본문 목차"><p>이 페이지에서 확인할 내용</p><ol>'+''.join(f'<li><a href="#{anchor}">{E(t)}</a></li>' for t,anchor in items)+'</ol></nav>'

def sidebar(active=''):
    return '<aside class="aside" aria-label="다른 진료 안내"><h2>새론이치과 진료 안내</h2>'+''.join(f'<a href="/{p["slug"]}/"'+(' aria-current="page"' if active=='/'+p['slug']+'/' else '')+f'>{E(p["shortTitle"])}</a>' for p in pages)+f'<a href="/prevention/">예방진료</a><a href="/blog/">치아 건강정보</a><div class="contact-box"><p>진료 문의</p><strong><a href="tel:0557242833">055-724-2833</a></strong><p>화·목 21:00까지 야간진료</p><a class="btn" href="{cfg["reservationUrl"]}" target="_blank" rel="noopener">네이버 예약</a></div></aside>'

def detail(p,ispost=False):
    path=('/blog/' if ispost else '/')+p['slug']+'/'
    key=p.get('imageKey',p['slug'])
    meta=post_meta(p) if ispost else ''
    hero='' if p.get('textOnly') else f'<div class="article-hero">{image(key,p.get("alt",image_alt(key)),wide=True,priority=True)}</div>'
    body=f'<div class="wrap">{breadcrumb(path,p["title"])}<header class="detail-head"><p class="eyebrow">{E(p["category"])}</p><h1>{E(p["title"])}</h1>{meta}<p class="lead">{E(p["description"])}</p></header><div class="content-grid"><article class="article-body">{hero}{contents(p)}{sections_html(p["sections"])}'
    if p['slug']=='clinic':body+='<h2 id="medical-team">의료진 소개</h2>'+doctors()
    if p['slug']=='hours':body+='<h2 id="weekly-hours">요일별 진료시간</h2>'+hours()+f'<div class="actions"><a class="btn" href="{cfg["reservationUrl"]}" target="_blank" rel="noopener">네이버 지도·예약</a><a class="btn outline" href="tel:0557242833">전화 문의</a></div>'+visit_preparation()+faq()+business_table()
    related=[x for x in posts if x['category']==p['category'] and x['slug']!=p['slug']][:3]
    if ispost:
        catkey=next(k for k,v in categories.items() if v==p['category'])
        guide=extra['categoryIntros'][catkey]['guide']
        body+=f'<nav class="article-return" aria-label="글 목록과 진료 안내"><a href="/blog/category/{catkey}/">← {E(p["category"])} 글 목록</a><a href="{guide}">관련 진료 안내 →</a></nav>'
    if related:body+='<div class="related"><h2>함께 읽을 정보</h2>'+''.join(f'<a href="/blog/{x["slug"]}/">{E(x["title"])} →</a>' for x in related)+'</div>'
    if p.get('sourceReferences'):
        body+='<section class="article-references"><h2>참고 자료</h2><ul>'+''.join(f'<li><a href="{E(ref["url"])}" target="_blank" rel="noopener">{E(ref["title"])}</a></li>' for ref in p['sourceReferences'])+'</ul><p class="note">일반적인 구강 건강정보이며 개인별 진단이나 치료 계획을 대신하지 않습니다.</p></section>'
    home_link=f'<p data-carousel-home-link style="margin-top:32px;padding-top:20px;border-top:1px solid #dce4e8"><a href="{url("/")}" style="text-decoration:underline;text-underline-offset:3px;font-weight:600">김해치과</a></p>'
    body+=f'<div class="callout"><h2>내 치아 상태에 맞는 상담</h2><p>치료 방법과 일정은 개인의 구강 및 전신 건강 상태에 따라 다릅니다. 진료를 통해 현재 상태를 확인해 주세요.</p><a class="readmore" href="{cfg["reservationUrl"]}" target="_blank" rel="noopener">새론이치과 네이버 예약 →</a></div><p class="article-source">진료·의료진·이용 안내: 업체 제공자료 및 <a href="{cfg["officialUrl"]}" target="_blank" rel="noopener">새론이치과 공식 홈페이지</a> 기준 · 정보 확인 {cfg["updatedAt"]}</p>{home_link}</article>{sidebar(path)}</div></div>'
    write_page(path,p['title'],p['description'],body,'/images/'+key+('-wide.jpg' if ispost else '.jpg'),ispost,p.get('alt',image_alt(key)),short_title=p.get('short_title',''))

def post_meta(post):
    at=post_date(post)
    label=f'{at.year}년 {at.month}월 {at.day}일'
    return f'<p class="blog-meta"><time datetime="{at.isoformat()}">{label}</time><span>작성자: 새론이치과 진료 안내</span></p>'

def blog_entry(post,featured=False):
    path=('/' if featured else '/blog/')+post['slug']+'/'
    category=next((k for k,v in categories.items() if v==post['category']),None)
    excerpt=' '.join([post['description']]+[text for heading,text in post['sections'][:2]])
    if len(excerpt)>320:excerpt=excerpt[:320].rsplit(' ',1)[0].rstrip('.,')+'…'
    picture=f'<a class="initial-post-image" href="{path}">{image(post["imageKey"],post["alt"],sizes="(max-width:768px) calc(100vw - 92px), 860px")}</a>' if featured else ''
    meta='<p class="blog-meta"><span>새론이치과 주요 안내</span><span>작성자: 새론이치과 진료 안내</span></p>' if featured else post_meta(post)
    category_path='/blog/category/'+category+'/' if category in published_categories else path
    marker=' data-featured-guide="'+post['slug']+'"' if featured else ''
    return f'<article class="blog-entry"{marker}>{picture}<h2><a href="{path}">{E(post["title"])}</a></h2>{meta}<p class="blog-excerpt">{E(excerpt)} <a class="blog-read-more" href="{path}" aria-label="{E(post["title"])} 더 읽기">더 읽기</a></p><p class="blog-category">카테고리 <a href="{category_path}">{E(post["category"])}</a></p></article>'

for p in pages:detail(p)
for p in posts:detail(p,True)
prevention={'slug':'prevention','category':'턱관절·예방','title':'김해치과 예방진료와 정기검진','description':'새론이치과의 정기검진과 구강 위생 관리, 자연치아를 지키기 위한 예방진료를 안내합니다.','imageKey':'prevention','sections':[['불편하기 전 구강 상태 확인','치아와 잇몸 상태를 주기적으로 확인하면 현재 관리가 필요한 부분을 파악하는 데 도움이 됩니다. 검진 간격과 필요한 진료는 충치 위험, 잇몸 상태, 기존 치료 이력 등에 따라 의료진과 상의합니다.'],['내 치아에 맞는 위생 관리','양치와 치간 관리 방법은 치아 사이 간격이나 보철물 형태에 따라 달라질 수 있습니다. 평소 음식물이 잘 끼는 부위와 양치할 때 출혈이 있는 부위를 알려주면 관리 방법을 안내받는 데 도움이 됩니다.'],['진료 뒤에도 이어지는 확인','임플란트나 크라운 등 보철 치료 뒤에도 주변 치아와 잇몸, 맞물림을 확인합니다. 기존과 다른 불편감이 생기면 정기검진 날짜만 기다리지 말고 치과에 문의해 주세요.']]}
detail(prevention)

def blog(category=None):
    base='/blog/' if category is None else '/blog/category/'+category+'/'
    name='김해치과 블로그' if category is None else categories[category]+' 건강정보'
    selected=posts if category is None else [p for p in posts if p['category']==categories[category]]
    featured=pages if category is None else []
    first_count=10-len(featured)
    total_pages=1+math.ceil(max(0,len(selected)-first_count)/10)
    path_for=lambda n:base if n==1 else base+'page/'+str(n)+'/'
    tabs='<a href="/blog/"'+(' aria-current="page"' if category is None else '')+'>전체</a>'+''.join(f'<a href="/blog/category/{k}/"'+(' aria-current="page"' if k==category else '')+f'>{E(v)}</a>' for k,v in published_categories.items())
    intro=extra['categoryIntros'].get(category)
    key=intro['imageKey'] if intro else 'clinic-photo'
    for number in range(1,total_pages+1):
        start=0 if number==1 else first_count+(number-2)*10
        items=selected[start:start+(first_count if number==1 else 10)]
        pinned=featured if number==1 else []
        label=name+(' · '+str(number)+'페이지' if number>1 else '')
        body=f'<div class="wrap blog-shell"><section class="blog-content" aria-labelledby="blog-heading"><h1 id="blog-heading" class="{ "sr-only" if category is None else "blog-heading" }">{E(label)}</h1>'
        if intro:body+=f'<div class="category-intro"><p>{E(intro["text"])}</p><a class="readmore" href="{intro["guide"]}">관련 진료 안내 →</a></div>'
        body+='<div class="blog-list">'+''.join(blog_entry(p,True) for p in pinned)+''.join(blog_entry(p) for p in items)+'</div>'
        if not items and not pinned:body+='<p>아직 등록된 글이 없습니다.</p>'
        body+='<nav class="blog-pagination" aria-label="글 목록 페이지">'
        if number>1:body+=f'<a href="{path_for(number-1)}" rel="prev">← 이전</a>'
        for n in range(1,total_pages+1):
            body+=(f'<span aria-current="page" aria-label="현재 페이지 {n}">{n}</span>' if n==number else f'<a href="{path_for(n)}" aria-label="{n}페이지">{n}</a>')
        if number<total_pages:body+=f'<a href="{path_for(number+1)}" rel="next">다음 →</a>'
        body+=f'<span class="blog-count">총 {len(selected)+len(featured)}개의 글</span></nav>'
        body+=f'</section><nav class="blog-topics" aria-label="블로그 카테고리">{tabs}</nav></div>'
        desc=intro['text'] if intro else f'새론이치과 주요 안내 6개와 치아 건강정보 {len(posts)}편을 살펴보세요. 주요 안내는 첫 페이지에 모았습니다.'
        if number>1:desc=f'{name} {number}페이지. '+desc
        title=label if category is None else label+' | 김해치과'
        write_page(path_for(number),title,desc,body,'/images/'+key+'-wide.jpg',img_alt=image_alt(key))
blog()
for category in published_categories:blog(category)
write_page('/404.html','페이지를 찾을 수 없습니다','요청하신 페이지를 찾을 수 없습니다.','<div class="wrap section"><h1>페이지를 찾을 수 없습니다</h1><p>주소를 확인하거나 아래 메뉴에서 필요한 진료 안내를 찾아주세요.</p><a class="btn" href="/">김해치과 홈으로</a></div>')

index_routes=all_routes if indexing else []
sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(url(r['path']))+'</loc><lastmod>'+r['lastmod']+'</lastmod></url>' for r in index_routes)+'</urlset>'
(OUT/'sitemap.xml').write_text(sitemap)
def rss_description(post):
    body=f'<p>{E(post["description"])}</p>'+sections_html(post['sections'])
    if post.get('sourceReferences'):body+='<h2>참고 자료</h2><ul>'+''.join(f'<li><a href="{E(ref["url"])}">{E(ref["title"])}</a></li>' for ref in post['sourceReferences'])+'</ul>'
    body+='<p>치료 방법과 일정은 개인의 구강 및 전신 건강 상태에 따라 다릅니다. 진료를 통해 현재 상태를 확인해 주세요.</p>'
    return escape(body)
items=''.join(f'<item><title>{escape(p["title"])}</title><link>{url("/blog/"+p["slug"]+"/")}</link><guid isPermaLink="true">{url("/blog/"+p["slug"]+"/")}</guid><description>{rss_description(p)}</description><pubDate>{format_datetime(post_date(p))}</pubDate></item>' for p in posts) if indexing else ''
(OUT/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>새론이치과 치아 건강정보</title><link>'+escape(url('/blog/'))+'</link><description>'+escape(cfg['description'])+'</description><language>ko</language>'+items+'</channel></rss>')
(OUT/'robots.txt').write_text('User-agent: *\n'+('Allow: /\nDisallow: /admin/\nDisallow: /drafts/\nSitemap: '+url('/sitemap.xml')+'\n' if indexing else 'Disallow: /\n'))
(OUT/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n'+('  X-Robots-Tag: noindex, nofollow\n' if not indexing else '')+'/images/*\n  Cache-Control: public, max-age=86400\n')
current_paths={r['path'] for r in all_routes}
for old in previous_routes:
    if old['path'] not in current_paths and re.fullmatch(r'/blog/(?:[a-z0-9-]+/)+',old['path']):
        stale=OUT/old['path'].strip('/')/'index.html'
        stale.unlink(missing_ok=True)
(ROOT/'content/route-manifest.json').write_text(json.dumps(all_routes,ensure_ascii=False,indent=2))
print('Built',len(all_routes),'pages + 404; indexing:',indexing,'; blog posts:',len(posts))

# Persist the requested homepage layout without changing publication records.
import runpy as _home_runpy
_home_runpy.run_path(str(ROOT/'home_layout.py'), run_name='__main__')

# Homepage detail content stays in the normal build flow.
import runpy as _detail_runpy
_detail_runpy.run_path(str(ROOT/'homepage_detail.py'), run_name='__main__')

# Source-based cost guide is homepage-only and preserves all publication data.
_cost_runpy=__import__("runpy")
_cost_runpy.run_path(str(Path(__file__).resolve().parents[1]/"home_cost_guide.py"),run_name="__main__")

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
