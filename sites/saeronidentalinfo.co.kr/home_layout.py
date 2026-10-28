"""Homepage-only transformation. Publication records, articles and feeds are untouched."""
from pathlib import Path
from urllib.parse import quote
import json,re,html
E=html.escape

def apply(root=None):
 root=Path(root) if root else Path(__file__).resolve().parent
 cfg=json.loads((root/'homepage-editorial.json').read_text());out=root/'dist';target=out/'index.html';s=target.read_text()
 name,keyword,p=cfg['name'],cfg['keyword'],cfg['primary']
 assert keyword in p['title'], 'Representative article must include the designated keyword'
 if cfg['kind']=='skin':
  match=re.search(r'<section class="featured-section".*?</section>',s,re.S);assert match
  carousel=re.sub(r'<div class="more-row">.*?</div>','',match[0],flags=re.S)
  first=re.search(r'<li>.*?</li>',carousel,re.S);assert first
  card=first[0];path='/journal/'+p['slug']+'/'
  assert (out/path.lstrip('/')/'index.html').is_file(), 'Representative page must already be public'
  card=re.sub(r'href="[^"]+"','href="'+path+'"',card)
  card=re.sub(r'(<h2><a[^>]*>).*?(</a></h2>)',lambda m:m[1]+E(p['title'])+m[2],card,flags=re.S)
  card=re.sub(r'(<p class="card-excerpt">).*?(</p>)',lambda m:m[1]+E(p['description'])+m[2],card,flags=re.S)
  card=re.sub(r'(<p class="card-meta">).*?(</p>)',lambda m:m[1]+E(p['category'])+' · 범어로제피부과'+m[2],card,flags=re.S)
  carousel=carousel[:first.start()]+card+carousel[first.end():]
  def schema(m):
   obj=json.loads(m[1])
   if obj.get('@type')=='ItemList':
    obj['itemListElement'][0]['name']=p['title'];obj['itemListElement'][0]['url']='https://beomeoroseeskininfo.co.kr'+path
   return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+'</script>'
  s=re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema,s,flags=re.S)
 else:
  match=re.search(r'<div class="carousel"[^>]*>.*?</article></div>',s,re.S);assert match
  arrow=re.search(r'<div class="arrows">.*?</div>',s,re.S)
  carousel='<section class="wrap homepage-carousel" aria-label="'+E(keyword)+' 주요 안내"><div class="heading"><h2>'+E(name)+' 주요 안내</h2>'+(arrow[0] if arrow else '')+'</div>'+match[0]+'</section>'
 assert len(re.findall(r'<article\b',carousel))==6
 sections=''.join('<section class="editorial-section"><span class="section-number">'+str(i+1).zfill(2)+'</span><h2>'+E(h)+'</h2>'+''.join('<p>'+E(t)+'</p>' for t in body.split('\n\n') if t.strip())+'</section>' for i,(h,body) in enumerate(p['sections']))
 topics=''.join('<div class="topic-detail"><h3>'+E(t['title'])+'</h3><p>'+E(t['text'])+'</p></div>' for t in cfg['topics'])
 faq=''.join('<details class="faq-item"><summary>'+E(q)+'</summary><p>'+E(a)+'</p></details>' for q,a in cfg['faq'])
 address=cfg['address'];mapurl='https://maps.google.com/maps?q='+quote(address)+'&output=embed'
 body=f'''{carousel}<article class="home-editorial" id="treatments"><header class="editorial-heading"><p class="eyebrow">{E(cfg['eyebrow'])}</p><h1>{E(cfg['headline'])}</h1><p class="editorial-lead">{E(cfg['intro'])}</p></header><figure class="home-clinic-photo"><img src="{E(cfg['photo'])}" alt="{E(cfg['photoAlt'])}" width="{cfg['photoWidth']}" height="{cfg['photoHeight']}" loading="lazy"><figcaption>{E(name)} 제공 병원 사진</figcaption></figure><div class="editorial-callout"><p>상담 전에 고민을 정리하고,<br><strong>설명을 충분히 들은 뒤 결정하세요.</strong></p></div><section class="editorial-section"><p class="eyebrow">PRIMARY GUIDE</p><h2>{E(p['title'])}</h2><p>{E(p['description'])}</p></section>{sections}<section class="editorial-section"><p class="eyebrow">CARE GUIDE</p><h2>고민에 따라 확인할 내용</h2><p>아래 내용은 진료 전 이해를 돕는 안내입니다. 같은 증상이라도 현재 상태와 이전 치료에 따라 확인할 내용이 달라질 수 있습니다.</p>{topics}</section><section class="editorial-section"><p class="eyebrow">BEFORE YOUR VISIT</p><h2>방문 전에 준비할 세 가지</h2><div class="topic-detail"><h3>증상과 이전 기록</h3><p>증상이 시작된 시기와 변화, 이전 치료·시술의 종류와 날짜를 정리하세요. 정확히 기억나지 않는 내용은 확인되지 않았다고 알려 주세요.</p></div><div class="topic-detail"><h3>복용약과 건강 상태</h3><p>복용약과 알레르기, 치료 중인 질환을 의료진에게 알리세요. 임의로 약을 중단하거나 바꾸지 말고 진료에서 필요한 안내를 받으세요.</p></div><div class="topic-detail"><h3>일정과 사후 진료</h3><p>방문 가능한 시간과 중요한 일정을 알리고, 예상 과정·비용·주의사항과 불편할 때 연락할 방법을 확인하세요.</p></div></section><section class="editorial-section home-faq" id="visit-faq"><p class="eyebrow">FAQ</p><h2>{E(keyword)} 자주 묻는 질문</h2>{faq}</section><section class="editorial-section home-location" id="visit-hours"><p class="eyebrow">LOCATION</p><h2>{E(name)} 오시는 길</h2><p class="location-address">{E(address)}</p><iframe class="location-map" title="{E(name)} 주소 지도" src="{E(mapurl)}" width="900" height="400" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe><p class="map-note">지도는 위 도로명 주소를 기준으로 표시됩니다. 방문 전 병원 안내에서 층수, 진료 일정과 주차 방법을 확인해 주세요.</p><div class="location-actions"><a href="tel:{re.sub('[^0-9]','',cfg['phone'])}">{E(cfg['phone'])} 전화 문의</a><a href="{E(cfg['map'])}" target="_blank" rel="noopener noreferrer">네이버 지도</a><a href="{E(cfg['official'])}" target="_blank" rel="noopener noreferrer">공식 병원 안내</a></div></section><aside class="medical-disclaimer"><h2>의료정보 안내</h2><p>{E(cfg['disclaimer'])}</p></aside></article>'''
 
 if not re.search(r'<a[^>]+href="/blog/?"', s[s.find('</main>'):]):
  body+='<nav class="home-archive-link" aria-label="건강정보 전체 글" style="max-width:900px;margin:0 auto 48px;padding:0 24px"><a href="/blog/">건강정보 전체 글 →</a></nav>'
 s=re.sub(r'(<main\b[^>]*>).*?(</main>)',lambda m:m[1]+body+m[2],s,count=1,flags=re.S)
 anchor='<nav class="homepage-keyword" aria-label="공식 병원 안내"><a href="'+E(cfg['official'])+'" target="_blank" rel="noopener noreferrer">'+E(keyword)+'</a></nav>'
 s=re.sub(r'<nav class="(?:desktop-menu|nav|homepage-keyword)"[^>]*>.*?</nav>',anchor,s,count=1,flags=re.S)
 s=re.sub(r'<details class="mobile-menu">.*?</details>','',s,count=1,flags=re.S)
 s=re.sub(r'<button class="menu-toggle".*?</button>','',s,count=1,flags=re.S)
 s=s.replace('<body>','<body class="home-layout">')
 if 'href="/home-layout.css"' not in s:s=s.replace('</head>','<link rel="stylesheet" href="/home-layout.css"></head>')
 target.write_text(s);(out/'home-layout.css').write_text((root/'home-layout.css').read_text())
 print(json.dumps({'homepage':keyword,'cards':6,'primary':p['slug'],'faq':len(cfg['faq']),'onlyHomeAndCss':True},ensure_ascii=False))

if __name__=='__main__':apply()
