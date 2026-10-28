import json, html, os, re, datetime
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image
from xml.sax.saxutils import escape

ROOT=Path(__file__).parent
OUT=ROOT/'dist'
CONFIG=json.loads((ROOT/'site-config.json').read_text())
ORIGIN=CONFIG['origin'].rstrip('/')
INDEX=CONFIG['indexing_enabled']
ALL_POSTS=json.loads((ROOT/'content.json').read_text())
POSTS=[p for p in ALL_POSTS if p.get('status','approved')=='approved']
# Markdown posts (content/posts/*.md): frontmatter + '## ' sections, same format as the other info sites.
# frontmatter category = group slug below (the /category/<group>/ page that lists the post); label is fixed here.
MD_GROUPS={'skin-guide':'피부질환','acne':'여드름·모공·흉터','acne-scars':'여드름·모공·흉터','pigmentation':'기미·색소','thermage':'써마지·탄력','ultherapy':'울쎄라·초음파','lifting':'주름·탄력','hair-removal':'제모','skinboosters':'피부 시술'}
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
 group=meta.get('category','skin-guide');assert group in MD_GROUPS,('category',group,path)
 return {'slug':path.stem,'title':meta['title'],'short_title':meta.get('short_title',''),'description':meta['description'],'group':group,'category':MD_GROUPS[group],'publishedAt':meta['date'],'sections':sections,'featured':False,'textOnly':True,'status':'approved','origin':'markdown'}
_md=sorted((ROOT/'content/posts').glob('*.md')) if (ROOT/'content/posts').exists() else []
_seen={p['slug'] for p in ALL_POSTS};_new=[]
for _f in _md:
 _post=_load_md(_f);assert _post['slug'] not in _seen,('duplicate slug',_f);_seen.add(_post['slug']);_new.append(_post)
_new.sort(key=lambda p:p['publishedAt'],reverse=True)
POSTS=_new+POSTS  # newest markdown posts first in the blog list
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
 _stale=OUT/'journal'/_p['slug']/'index.html'
 if _stale.exists(): _stale.unlink()
POSTS=[p for p in POSTS if p not in _future]
FEATURED=[p for p in POSTS if p.get('featured',False)]
assert len(FEATURED)==6
assert len({p['slug'] for p in POSTS})==len(POSTS), 'duplicate article slug'
NAME='범어로제피부과의원'
OFFICIAL='https://beomeo.roseeskin.com'
ADDRESS='대구 수성구 달구벌대로 2397 KB손해보험 대구빌딩 16층'
E=html.escape
GROUPS=dict((p['group'],p['category']) for p in POSTS)
LIST_URLS=[]
for p in POSTS:
    p['path']='/journal/'+p['slug']+'/'
    p['src']=p.get('image_src') if p.get('featured') else None
    if p['src']:
        p['w'],p['h']=Image.open(OUT/p['src'].lstrip('/')).size
        p['alt']=p['image_alt']

def a(path,label,cls=''):
    return f'<a href="{E(path)}"'+(f' class="{cls}"' if cls else '')+f'>{E(label)}</a>'
def img(p,cls='',lazy=True):
    if not p.get('src'): return ''
    return f'<img src="{p["src"]}" width="{p["w"]}" height="{p["h"]}" alt="{E(p["alt"])}" class="{cls}" loading="{"lazy" if lazy else "eager"}" decoding="async">'
def ld(data):
    return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'
def links():
    return '<p class="meta-backlink" data-carousel-home-link>'+a(ORIGIN+'/','대구써마지')+' · '+a(ORIGIN+'/대구울쎄라/','대구울쎄라')+' · '+a(OFFICIAL+'/','범어로제피부과')+'</p>'
def navgroup(current=''):
    return '<nav class="category-nav" aria-label="블로그 카테고리">'+a('/blog/','전체')+''.join(f'<a href="/category/{g}/"'+(' aria-current="page"' if g==current else '')+f'>{v}</a>' for g,v in GROUPS.items())+'</nav>'
def page(path,title,desc,body,picture=None,extra=None,short_title=''):
    canonical=ORIGIN+path
    schema={'@context':'https://schema.org','@type':'MedicalClinic','@id':ORIGIN+'/#clinic','name':NAME,'url':ORIGIN+'/','telephone':'+82-53-754-1475','address':{'@type':'PostalAddress','streetAddress':'달구벌대로 2397 KB손해보험 대구빌딩 16층','addressLocality':'수성구','addressRegion':'대구광역시','addressCountry':'KR'},'sameAs':[OFFICIAL+'/']}
    menu=a('/','홈')+a('/대구써마지/','대구써마지')+a('/대구울쎄라/','대구울쎄라')+a('/blog/','블로그')+a('/about/','병원 소개')+a('/contact/','오시는 길')
    social=f'<meta property="og:image" content="{ORIGIN+picture["src"]}"><meta property="og:image:alt" content="{E(picture["alt"])}">' if picture and picture.get('src') else ''
    doctitle=short_title if short_title else title+' | '+NAME
    markup=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(doctitle)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="{'index,follow' if INDEX else 'noindex,nofollow'}"><meta property="og:title" content="{E(short_title or title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:type" content="{'article' if path.startswith('/journal/') else 'website'}"><meta property="og:locale" content="ko_KR">{social}<link rel="stylesheet" href="/style.css"><link rel="alternate" type="application/rss+xml" title="{NAME} 블로그" href="/rss.xml"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="icon" href="/favicon.ico"><link rel="apple-touch-icon" href="/apple-touch-icon.png">{ld(schema)}{ld(extra) if extra else ''}</head><body><a class="skip-link" href="#site-content">본문 바로가기</a><header class="site-header"><div class="header-inner"><a href="/" class="brand">대구써마지 · 대구울쎄라<small>THERMAGE · ULTHERAPY DAEGU</small></a><nav class="desktop-menu" aria-label="주 메뉴">{menu}</nav><details class="mobile-menu"><summary>메뉴</summary><nav aria-label="모바일 메뉴">{menu}</nav></details></div></header><div id="site-content">{body}</div><nav class="quick-links" aria-label="빠른 안내">{a('tel:0537541475','전화 상담')}{a('/contact/','오시는 길')}{a('#site-content','맨 위로')}</nav><footer class="site-footer"><strong>{NAME}</strong><p>{ADDRESS}<br>{a('tel:0537541475','053-754-1475')} · {a(OFFICIAL+'/','공식 홈페이지')} · {a('https://naver.me/GSDPm5HN','네이버 지도')}</p><p>개인별 피부 상태와 시술에 따라 적용 여부와 경과가 다릅니다. 본 안내는 진료를 대신하지 않습니다.</p><p>© 2026 BEOMEO ROSEE</p></footer></body></html>'''
    target=OUT/('index.html' if path=='/' else path.strip('/')+'/index.html')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(markup)

cards=''.join(f'<li><article class="featured-card"><a class="featured-thumb" href="{p["path"]}">{img(p,"",False)}</a><div class="featured-copy"><h2>{a(p["path"],p["title"])}</h2><p class="card-meta">{p["category"]} · 범어로제피부과</p><p class="card-excerpt">{p["description"]}</p>{a(p["path"],"더 읽기","card-more")}</div></article></li>' for p in FEATURED)
items={'@context':'https://schema.org','@type':'ItemList','name':NAME+' 주요 진료·상담 안내','numberOfItems':6,'itemListElement':[{'@type':'ListItem','position':i+1,'name':p['title'],'url':ORIGIN+p['path'],'image':ORIGIN+p['src']} for i,p in enumerate(FEATURED)]}
summary=''.join(f'<div class="treatment-summary"><h3>{a("/category/"+g+"/",label)}</h3><p>'+str(sum(p['group']==g for p in POSTS))+'개의 진료·피부 정보</p></div>' for g,label in GROUPS.items())
page('/','대구피부과 범어로제 | 기미·써마지·울쎄라','범어로제피부과의 기미·색소, 써마지 FLX, 울쎄라 프라임 상담과 진료·위치 안내를 살펴보세요.',f'<main class="home-shell"><section class="featured-section" aria-label="대표 글 6개"><ul class="featured-list">{cards}</ul><div class="more-row">{a("/blog/","글 전체보기","more-button")}</div></section><section class="home-intro" id="treatments"><h1>대구피부과</h1><p>피부 고민에 맞는 정보를 살펴보고, 진료 전에 궁금한 내용을 준비하세요.</p><h2>주제별 진료·상담 안내</h2>{summary}</section><section class="clinic-info"><h2>진료·위치 안내</h2><p>{ADDRESS}</p><div class="clinic-actions">{a("tel:0537541475","053-754-1475 전화 상담")}{a("/contact/","진료시간과 오시는 길")}</div></section></main>',POSTS[0],items)

for p in POSTS:
    related=[x for x in POSTS if x['slug']!=p['slug'] and (x['group']==p['group'] or (p['group'] in ['lifting','thermage','ultherapy'] and x['group'] in ['lifting','thermage','ultherapy']))][:3]
    sections=''.join(f'<section id="s{i}"><h2>{E(h)}</h2>'+''.join('<p>'+E(par)+'</p>' for par in t.split('\n\n') if par.strip())+'</section>' for i,(h,t) in enumerate(p['sections']))
    toc='<nav class="toc" aria-label="목차"><strong>이 글에서 살펴볼 내용</strong><ol>'+''.join('<li>'+a('#s'+str(i),s[0])+'</li>' for i,s in enumerate(p['sections']))+'</ol></nav>'
    photo=f'<figure class="article-photo">{img(p)}<figcaption>병원 제공 사진</figcaption></figure>' if p.get('src') else ''
    body=f'<main class="article journal-article"><header class="entry-header"><h1>{E(p["title"])}</h1><p class="blog-meta">{p["category"]} · 범어로제피부과 진료 안내</p></header><p class="lead">{E(p["description"])}</p>{photo}{toc}{sections}<p class="blog-category">카테고리 {a("/category/"+p["group"]+"/",p["category"])}</p>'
    if p.get('sources'):
        body+='<section class="article-sources"><h2>참고 자료</h2><ul>'+''.join('<li>'+a(url,urlparse(url).netloc.replace('www.','')+' · 관련 안내')+'</li>' for url in dict.fromkeys(p['sources']))+'</ul></section>'
    if related:body+='<h2>함께 읽을 글</h2><ul>'+''.join('<li>'+a(r['path'],r['title'])+'</li>' for r in related)+'</ul>'
    body+='<div class="related">'+a('/blog/','전체 글 보기')+a('/contact/','오시는 길')+'</div><p class="notice">시술 적용 여부와 결과는 개인마다 다르며, 일시적인 붉은기·붓기 등 반응이 나타날 수 있습니다. 자세한 주의사항은 진료 시 안내받으세요.</p>'+links()+'</main>'
    page(p['path'],p['title'],p['description'],body,p,{'@context':'https://schema.org','@type':'Article','headline':p['title'],'description':p['description'],**({'image':ORIGIN+p['src']} if p.get('src') else {}),'mainEntityOfPage':ORIGIN+p['path'],'publisher':{'@id':ORIGIN+'/#clinic'},'inLanguage':'ko-KR'},short_title=p.get('short_title',''))

for group in ['',*GROUPS]:
    subset=sorted([p for p in POSTS if not group or p['group']==group], key=lambda p: not p.get('featured',False))
    base='/category/'+group+'/' if group else '/blog/'
    size=12
    total=max(1,(len(subset)+size-1)//size)
    def list_path(num): return base if num==1 else base+'page/'+str(num)+'/'
    for number in range(1,total+1):
        path=list_path(number);LIST_URLS.append(path)
        chunk=subset[(number-1)*size:number*size]
        entries=[]
        for p in chunk:
            thumbnail=('<a class="blog-featured-image" href="'+p['path']+'">'+img(p)+'</a>') if p.get('src') else ''
            copy='<h2>'+a(p['path'],p['title'])+'</h2><p class="blog-meta">'+p['category']+' · 범어로제피부과</p><p class="blog-excerpt">'+E(p['description'])+' '+a(p['path'],'더 읽기','text-link')+'</p>'+links()
            entries.append('<article'+(' class="blog-featured-entry"' if thumbnail else '')+'>'+thumbnail+'<div class="blog-entry-copy">'+copy+'</div></article>')
        listing=''.join(entries)
        pager='<nav class="blog-pagination" aria-label="글 목록 페이지">'+''.join('<span aria-current="page">'+str(i)+'</span>' if i==number else a(list_path(i),str(i)) for i in range(1,total+1))+'</nav>' if total>1 else ''
        title=GROUPS.get(group,'전체 글')+' | 범어로제 블로그'+(' · '+str(number)+'페이지' if number>1 else '')
        page(path,title,'범어로제피부과의 '+GROUPS.get(group,'진료·상담')+' 안내 글 '+str(len(subset))+'개 중 '+str(number)+'페이지입니다.',f'<main class="blog-shell"><section class="blog-content"><h1 class="blog-topic-heading">{E(title)}</h1>{navgroup(group)}<p class="list-count">전체 {len(subset)}개 글 · {number}/{total}페이지</p><div class="blog-list">{listing}</div>{pager}</section></main>')

page('/about/','범어로제피부과 소개','범어로제피부과의 진료 분야와 상담 안내, 공식 홈페이지를 확인하세요.',f'<main class="article"><h1>범어로제피부과의원</h1><p>대구 수성구 범어동에 위치한 피부과의원입니다. 이 사이트에서는 기미·색소와 리프팅·탄력 등 피부 고민에 관한 상담 준비 내용을 안내합니다.</p><h2>진료 분야</h2><p>공식 홈페이지에서는 기미·색소, 리프팅·탄력, 여드름, 모공·흉터, 제모, 홍조·민감성, 스킨부스터, 특수클리닉, 메디컬스킨케어를 안내하고 있습니다.</p><p>분야별 진료 가능 여부와 구체적인 시술 계획은 예약 및 진료 상담에서 확인해 주세요.</p><div class="related">{a(OFFICIAL+"/","병원 공식 홈페이지")}{a("/contact/","위치·연락처")}{a("/blog/","피부 건강정보")}</div>{links()}</main>')
page('/contact/','범어로제피부과 진료·위치 안내','대구 수성구 달구벌대로 2397 KB손해보험 대구빌딩 16층. 전화 053-754-1475.',f'<main class="article"><h1>진료·위치 안내</h1><h2>범어로제피부과의원</h2><p>{ADDRESS}</p><p>전화 {a("tel:0537541475","053-754-1475")}</p><div class="clinic-actions">{a("https://naver.me/GSDPm5HN","네이버 지도에서 위치 확인")}{a(OFFICIAL+"/17","공식 진료시간·위치 안내")}</div><h2>방문 전 확인하세요</h2><p>진료시간, 예약 가능 여부와 주차 안내는 방문 전에 병원 또는 공식 홈페이지에서 확인해 주세요.</p>{links()}</main>')

# ---- 키워드 허브 (2026-10-23 대구써마지·대구울쎄라 재겨냥) ----
HUBS={'/대구써마지/':('대구써마지','thermage','써마지 FLX','대구써마지 범어로제피부과 써마지 FLX 안내','대구써마지 범어로제피부과의원. 써마지 FLX 정품 팁, 피부 두께에 맞춘 샷 수와 팁 선택, 회복 기간을 안내합니다.',
  ['써마지 FLX는 고주파 에너지로 진피층 콜라겐을 자극해 피부 표면 탄력과 잔주름을 다루는 시술입니다. 얼굴 600샷·900샷, 눈가 전용 팁, 바디 팁처럼 부위별로 팁이 다르고, 피부 두께에 따라 에너지 단계를 조절합니다.','범어로제피부과의원은 1회용 정품 팁을 개봉해 사용하며, 상담에서 피부 두께와 처짐 정도를 보고 과하지 않은 적정 샷을 권합니다. 울쎄라와 병행이 필요한지, 순서와 간격은 어떻게 할지도 함께 정합니다.']),
 '/대구울쎄라/':('대구울쎄라','ultherapy','울쎄라 프라임','대구울쎄라 범어로제피부과 울쎄라 프라임 안내','대구울쎄라 범어로제피부과의원. 울쎄라 프라임 정품 카트리지, 얼굴선 고민별 깊이·라인 수와 통증 관리를 안내합니다.',
  ['울쎄라 프라임은 고강도 집속 초음파(HIFU)로 근막층(SMAS)까지 에너지를 전달해 턱선·이중턱·눈썹 처짐 같은 깊은 처짐을 다루는 시술입니다. 1.5·3.0·4.5mm 깊이 카트리지를 부위별로 나누어 쓰며, 초음파 영상으로 깊이를 확인하면서 진행합니다.','범어로제피부과의원은 정품 카트리지를 확인한 뒤 처진 깊이와 지방량에 맞춰 라인 수를 정합니다. 통증은 마취 크림과 깊이별 강도 조절로 관리하고, 써마지와 병행할지 간격을 둘지 상담에서 정합니다.'])}
HUB_URLS=[]
for _path,(_kw,_group,_dev,_title,_desc,_paras) in HUBS.items():
    _posts=[p for p in POSTS if p['group']==_group][:30]
    _other='/대구울쎄라/' if _path=='/대구써마지/' else '/대구써마지/'
    _body=f'<main class="article hub-page"><header class="entry-header"><h1>{E(_title)}</h1><p class="blog-meta">{E(_dev)} · 범어로제피부과의원</p></header><p class="lead">{E(_desc)}</p>'+''.join('<p>'+E(x)+'</p>' for x in _paras)
    _body+='<h2>'+E(_kw)+' 안내 글</h2><ul class="hub-list">'+''.join('<li>'+a(x['path'],x['title'])+'</li>' for x in _posts)+'</ul><div class="related">'+a('/category/'+_group+'/',E(_dev)+' 글 전체')+a(_other,HUBS[_other][0]+' 안내')+a('/contact/','진료시간·오시는 길')+'</div>'
    _body+='<p class="notice">시술 적용 여부와 결과는 개인마다 다르며, 일시적인 붉은기·붓기 등 반응이 나타날 수 있습니다. 자세한 주의사항은 진료 시 안내받으세요.</p>'+links()+'</main>'
    _ld={'@context':'https://schema.org','@type':'CollectionPage','name':_title,'description':_desc,'url':ORIGIN+_path,'inLanguage':'ko-KR','about':{'@id':ORIGIN+'/#clinic'},'mainEntity':{'@type':'ItemList','numberOfItems':len(_posts),'itemListElement':[{'@type':'ListItem','position':i+1,'name':x['title'],'url':ORIGIN+x['path']} for i,x in enumerate(_posts)]}}
    page(_path,_title,_desc,_body,POSTS[0] if False else None,_ld,short_title=_title+' | 범어로제피부과의원')
    HUB_URLS.append(_path)

urls=['/','/about/','/contact/']+HUB_URLS+LIST_URLS+[p['path'] for p in POSTS]
# Private review site: no public feed entries until domain, ownership and indexing are ready.
feedurls=urls if INDEX else []
(OUT/'robots.txt').write_text('User-agent: *\n'+('Allow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n' if INDEX else 'Disallow: /\n'))
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(ORIGIN+u)+'</loc></url>' for u in feedurls)+'</urlset>')
(OUT/'rss.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>'+NAME+'</title><link>'+ORIGIN+'/</link><description>피부 진료·상담 안내</description>'+(''.join('<item><title>'+escape(p['title'])+'</title><link>'+ORIGIN+p['path']+'</link><guid>'+ORIGIN+p['path']+'</guid><description>'+escape(p['description'])+'</description></item>' for p in POSTS) if INDEX else '')+'</channel></rss>')
(OUT/'404.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="robots" content="noindex"><title>페이지를 찾을 수 없습니다</title><h1>페이지를 찾을 수 없습니다.</h1><a href="/">홈으로 돌아가기</a></html>')
print(json.dumps({'pages':len(urls),'featured':len(FEATURED),'articles':len(POSTS),'categories':len(GROUPS),'indexing':INDEX,'origin':ORIGIN},ensure_ascii=False))

# Persist the requested homepage layout without changing publication records.
import runpy as _home_runpy
_home_runpy.run_path(str(ROOT/'home_layout.py'), run_name='__main__')

# Homepage detail content stays in the normal build flow.
import runpy as _detail_runpy
_detail_runpy.run_path(str(ROOT/'homepage_detail.py'), run_name='__main__')

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

# ---- 홈 (2026-10-23): content/home.json → tools/build_home.py 가 index.html을 통째로 생성 (새론이 구조·대구써마지·대구울쎄라) ----
import subprocess as _sp, sys as _sys
_sp.run([_sys.executable,'-I',str(ROOT/'tools'/'build_home.py'),str(ROOT)],check=True)
_qm_apply()
# ---- 허브/카드 대상 6쪽 대표 이미지 = 홈 카드 사진 (2026-10-26, 캐러셀 분석) ----
_sp.run([_sys.executable,'-I',str(ROOT/'tools'/'patch_hubs.py'),str(OUT)],check=True)
