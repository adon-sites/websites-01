"""Build the requested main-page editorial without changing archived posts."""
from pathlib import Path
import json,re,html
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
CFG=json.loads((ROOT/'content/homepage-editorial.json').read_text())
C=json.loads((ROOT/'content/company.json').read_text())
A={a['id']:a for a in json.loads((ROOT/'content/reviewed-articles.json').read_text())}
E=html.escape
s=(OUT/'index.html').read_text()
guide_file=ROOT/'content/homepage-feature-article.json'
if guide_file.exists(): CFG['guide']=json.loads(guide_file.read_text())
featured=CFG.get('guide') or A[CFG['featuredArticleId']]
feature_path='/guides/'+featured['slug']+'/' if CFG.get('guide') else '/blog/'+featured['slug']+'/'
if not CFG.get('guide'): assert (OUT/feature_path.lstrip('/')/'index.html').is_file(), 'Feature requires existing rendered article'
# Keep all six cover assets and card affordances. Only the representative destination changes.
match=re.search(r'<a class="feature" href="[^"]+">.*?</a>',s,re.S)
assert match
card=re.sub(r'href="[^"]+"','href="'+feature_path+'"',match[0],count=1)
card=re.sub(r'(<h3>).*?(</h3>)',lambda m:m[1]+E(featured['title'])+m[2],card,count=1,flags=re.S)
card=re.sub(r'(<span class="eyebrow">).*?(</span>)',lambda m:m[1]+E(C['seo']['primary'])+m[2],card,count=1,flags=re.S)
s=s[:match.start()]+card+s[match.end():]
def schema_update(m):
 obj=json.loads(m[1])
 if obj.get('@type')=='ItemList':
  obj['itemListElement'][0].update(name=featured['title'],url=C['origin'].rstrip('/')+feature_path)
 return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+'</script>'
s=re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema_update,s,flags=re.S)
def paras(ps):return ''.join('<p>'+E(p)+'</p>' for p in ps)
body='<article class="home-editorial" id="keyword-guide"><header class="home-editorial-intro"><span class="eyebrow">AD-ON · 마케팅 운영 가이드</span><h1>'+E(C['seo']['primary'])+'</h1><p class="home-deck">'+E(CFG['deck'])+'</p>'+paras(CFG['intro'])+'</header>'
body+='<section class="home-feature-story"><span class="eyebrow">대표 가이드</span><h2>'+E(featured['title'])+'</h2>'
for sec in featured['sections']:
 if sec['heading']: body+='<h3>'+E(sec['heading'])+'</h3>'
 body+=paras(sec['paragraphs'])
body+='</section>'
for i,sec in enumerate(CFG['sections'],1):
 body+='<section class="home-practical"><span class="eyebrow">'+str(i).zfill(2)+' · '+E(sec.get('label','실무 안내'))+'</span><h2>'+E(sec['heading'])+'</h2>'+paras(sec['paragraphs'])
 if sec.get('items'):body+='<div class="home-check-grid">'+''.join('<div><h3>'+E(x['heading'])+'</h3><p>'+E(x['text'])+'</p></div>' for x in sec['items'])+'</div>'
 body+='</section>'
body+='<section class="home-faq" id="homepage-faq"><span class="eyebrow">FAQ</span><h2>'+E(C['seo']['primary'])+' 자주 묻는 질문</h2>'+''.join('<details><summary>'+E(q['question'])+'</summary><p>'+E(q['answer'])+'</p></details>' for q in CFG['faq'])+'</section>'
body+='<section class="home-company" id="company-information"><span class="eyebrow">COMPANY</span><h2>애드온 회사·문의 안내</h2><dl>'+''.join('<div><dt>'+E(k)+'</dt><dd>'+E(v)+'</dd></div>' for k,v in [('상호',C['name']+' (AD-ON)'),('대표',C['representative']),('사업자등록번호',C['businessNumber']),('소재지',C['address']),('이메일',C['email'])])+'</dl><p class="home-notice">'+E(CFG['notice'])+'</p></section></article>'
# Preserve original networking and contact sections after the editorial.
start=re.search(r'<section class="feature-grid[^\"]*".*?</section>',s,re.S)
assert start
end=s.find('<section class="hospital-links marketing-network-links"',start.end())
if end<0:end=s.find('<section class="consultation"',start.end())
assert end>start.end()
s=s[:start.end()]+body+s[end:]
css='''<style id="homepage-editorial-style">.home-editorial{max-width:880px;margin:0 auto 56px;background:#fff;padding:clamp(24px,5vw,64px);border-radius:var(--radius,12px);border:1px solid var(--line,#ddd)}.home-editorial section{padding:40px 0;border-top:1px solid var(--line,#ddd)}.home-editorial-intro{padding-bottom:40px}.home-editorial h1{margin:12px 0 24px;font-size:clamp(30px,3.5vw,48px)}.home-editorial h2{margin:12px 0 24px;font-size:clamp(23px,2.5vw,30px)}.home-editorial h3{font-size:20px}.home-editorial p{font-size:17px;line-height:2;margin:18px 0;word-break:keep-all;overflow-wrap:anywhere}.home-editorial .home-deck{font-size:21px;color:var(--accent,#254763);font-weight:600;line-height:1.7}.home-check-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:28px 0}.home-check-grid>div{background:var(--pale,#f4f7f9);padding:24px;border-radius:var(--radius,12px)}.home-check-grid h3{margin:0 0 12px}.home-check-grid p{font-size:16px;margin:0}.home-faq details{border-bottom:1px solid var(--line,#ddd);padding:18px 0}.home-faq summary{cursor:pointer;font-size:18px;font-weight:700;min-height:32px}.home-faq details p{margin-bottom:4px}.home-company dl>div{display:grid;grid-template-columns:130px 1fr;gap:20px;padding:14px 0;border-bottom:1px solid var(--line,#ddd)}.home-company dt{font-weight:700}.home-company dd{margin:0}.home-editorial .home-notice{font-size:14px;color:var(--muted,#56616d);padding:20px;background:var(--pale,#f4f7f9)}@media(max-width:700px){.home-editorial{padding:26px 22px;margin-top:24px}.home-editorial section{padding:30px 0}.home-check-grid{grid-template-columns:1fr}.home-company dl>div{grid-template-columns:1fr;gap:4px}.home-editorial p{font-size:16px;line-height:1.95}.home-editorial .home-deck{font-size:19px}.home-faq summary{font-size:17px}}
</style>'''
s=re.sub(r'<style id="homepage-editorial-style">.*?</style>','',s,flags=re.S).replace('</head>',css+'</head>',1)
# FAQ data is identical to the answers visible on this page, without ranking promises.
s=re.sub(r'<script type="application/ld\+json" id="homepage-faq-schema">.*?</script>','',s,flags=re.S)
faq={'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':q['question'],'acceptedAnswer':{'@type':'Answer','text':q['answer']}} for q in CFG['faq']]}
s=s.replace('</head>','<script type="application/ld+json" id="homepage-faq-schema">'+json.dumps(faq,ensure_ascii=False).replace('<','\\u003c')+'</script></head>',1)
(OUT/'index.html').write_text(s)
if CFG.get('guide'):
 # A separately authored homepage guide never enters the campaign corpus or its ledger.
 guide_s=s
 guide_s=re.sub(r'<div class="design-kicker">.*?</div>','',guide_s,count=1,flags=re.S)
 guide_s=re.sub(r'<section class="feature-grid[^\"]*".*?</section>','',guide_s,count=1,flags=re.S)
 guide_s=re.sub(r'<title>.*?</title>','<title>'+E(featured['title'])+' | 애드온</title>',guide_s,count=1,flags=re.S)
 guide_url=C['origin'].rstrip('/')+feature_path
 guide_s=re.sub(r'<link rel="canonical" href="[^"]+">','<link rel="canonical" href="'+guide_url+'">',guide_s,count=1)
 guide_s=re.sub(r'<meta property="og:url" content="[^"]+">','<meta property="og:url" content="'+guide_url+'">',guide_s,count=1)
 guide_s=re.sub(r'<meta property="og:title" content="[^"]+">','<meta property="og:title" content="'+E(featured['title'],quote=True)+'">',guide_s,count=1)
 guide_s=re.sub(r'<meta name="description" content="[^"]+">','<meta name="description" content="'+E(featured['description'],quote=True)+'">',guide_s,count=1)
 guide_s=re.sub(r'<meta property="og:description" content="[^"]+">','<meta property="og:description" content="'+E(featured['description'],quote=True)+'">',guide_s,count=1)
 guide_s=re.sub(r'<h1>.*?</h1>','<h1>'+E(featured['title'])+'</h1>',guide_s,count=1,flags=re.S)
 guide_s=guide_s.replace('class="route-home"','class="route-article"',1)
 guide_s=re.sub(r'<script type="application/ld\+json">(.*?)</script>',lambda m:'' if json.loads(m[1]).get('@type')=='ItemList' else m[0],guide_s,flags=re.S)
 guide_schema={'@context':'https://schema.org','@type':'Article','headline':featured['title'],'description':featured['description'],'url':guide_url,'mainEntityOfPage':guide_url,'author':{'@type':'Organization','name':C['name']},'inLanguage':'ko-KR'}
 guide_s=guide_s.replace('</head>','<script type="application/ld+json">'+json.dumps(guide_schema,ensure_ascii=False).replace('<','\\u003c')+'</script></head>',1)
 guide_s=re.sub(r'<meta property="og:type" content="[^"]+">','<meta property="og:type" content="article">',guide_s,count=1)
 # Retain the normal article template's clinic-reference links on the new guide.
 missing_links=[x for x in C['hospitalLinks'] if x['url'] not in guide_s]
 if missing_links:
  guide_links='<section class="hospital-links"><h2>관련 병원 안내</h2><ul>'+''.join('<li><a href="'+E(x['url'],quote=True)+'">'+E(x['label'])+'</a></li>' for x in missing_links)+'</ul></section>'
  guide_s=guide_s.replace('</main>',guide_links+'</main>',1)
 guide_s=guide_s.replace('</main>','<nav class="post-nav" aria-label="가이드 탐색"><a href="/">홈으로</a><a href="/blog/">마케팅 인사이트 전체 글</a></nav></main>',1)
 dest=OUT/feature_path.lstrip('/')/'index.html';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(guide_s)
 sitemap=OUT/'sitemap.xml';sm=sitemap.read_text()
 if guide_url not in sm: sitemap.write_text(sm.replace('</urlset>','<url><loc>'+E(guide_url)+'</loc></url></urlset>'))

print(json.dumps({'homeEditorial':True,'domain':C['customDomain'],'primary':C['seo']['primary'],'featured':featured['id'],'faq':len(CFG['faq'])},ensure_ascii=False))
