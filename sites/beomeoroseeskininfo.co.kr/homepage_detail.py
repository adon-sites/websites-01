"""Source-grounded homepage only. Never reads or mutates article/publication records."""
from pathlib import Path
import html,json,re
ROOT=Path(__file__).resolve().parent
E=lambda x:html.escape(str(x),quote=True)
def paras(xs):return ''.join('<p>'+E(x)+'</p>' for x in xs)
def bullets(xs):return '<ul>'+''.join('<li>'+E(x)+'</li>' for x in xs)+'</ul>'
def render(c):
 e=json.loads((ROOT/'homepage-editorial.json').read_text())
 def start(id,kicker,title):return '<section class="original-section" id="'+id+'"><p class="original-kicker">'+E(kicker)+'</p><h2>'+E(title)+'</h2>'
 s='<article class="source-homeguide" id="treatments" data-original-revision="'+E(c.get('revision','2026-10-01-original-manuscript-2'))+'">'
 s+='<header class="original-hero"><p class="original-kicker">'+E(c['eyebrow'])+'</p><h1>'+E(c['title'])+'</h1><p class="original-subtitle">'+E(c['subtitle'])+'</p>'+paras(c['intro'])+'</header>'
 s+='<figure class="home-clinic-photo"><img src="'+E(e['photo'])+'" alt="'+E(e['photoAlt'])+'" width="'+E(e['photoWidth'])+'" height="'+E(e['photoHeight'])+'" loading="lazy"><figcaption>'+E(e['photoAlt'])+'</figcaption></figure>'
 s+=start('guide-checkpoints','CHECKPOINT 01–04','진료 전 살펴볼 네 가지')+'<div class="original-checks">'+''.join('<div class="original-check"><span class="original-count">'+str(i+1).zfill(2)+'</span><h3>'+E(v['title'])+'</h3><p>'+E(v['text'])+'</p></div>' for i,v in enumerate(c['checkpoints']))+'</div></section>'
 s+=start('guide-treatments','TREATMENT GUIDE','진료 항목 자세히 보기')+'<div class="original-treatments">'+''.join('<div class="original-treatment"><span>'+str(i+1).zfill(2)+'</span><div><h3>'+E(v['title'])+'</h3><p>'+E(v['text'])+'</p></div></div>' for i,v in enumerate(c['treatments']))+'</div></section>'
 s+=start('guide-stages','BEFORE & AFTER','치료·시술 전후 일정 안내')+'<div class="original-stages" role="list">'+''.join('<div class="original-stage" role="listitem"><div><span>'+E(v['when'])+'</span><h3>'+E(v['stage'])+'</h3></div><p>'+E(v['text'])+'</p></div>' for v in c['stages'])+'</div><p class="original-note">'+E(c['stageNote'])+'</p></section>'
 s+=start('guide-consultation','CONSULTATION','상담을 준비하는 팁과 질문')+'<div class="original-tips">'+bullets(c['consultTips'])+'</div><div class="original-questions">'+''.join('<details><summary>'+E(v['q'])+'</summary><p>'+E(v['a'])+'</p></details>' for v in c['questions'])+'</div></section>'
 s+=start('guide-patient-info','YOUR INFORMATION','환자가 미리 알려주면 좋은 정보')+bullets(c['patientInfo'])+'</section>'
 s+=start('guide-directions','LOCATION',c['name']+' 오시는 길')+'<p class="original-address">'+E(c['directions']['address'])+'</p>'+paras(c['directions']['items'])
 phone=c['links']['phone'];s+='<div class="original-actions"><a href="tel:'+re.sub(r'\D','',phone)+'"><span>'+E(c.get('phoneLabel','전화 문의'))+'</span><strong>'+E(phone)+'</strong></a><a href="'+E(c['links']['naver'])+'" target="_blank" rel="noopener noreferrer"><span>네이버 플레이스</span><strong>위치·예약 정보 ↗</strong></a><a href="'+E(c['links']['homepage'])+'" target="_blank" rel="noopener noreferrer"><span>공식 홈페이지</span><strong>병원 안내 바로가기 ↗</strong></a></div></section>'
 s+=start('guide-clinic','CLINIC INFORMATION','병원 안내')+paras(c['clinicIntro'])+'<dl class="original-facts">'+''.join('<div><dt>'+E(v['label'])+'</dt><dd>'+E(v['value'])+'</dd></div>' for v in c['clinicFacts'])+'</dl>'
 if c.get('sources'):s+='<details class="original-references"><summary>안내에 참고한 공식 자료</summary><ul>'+''.join('<li><a href="'+E(v['url'])+'" target="_blank" rel="noopener noreferrer">'+E(v['label'])+'</a></li>' for v in c['sources'])+'</ul></details>'
 s+='</section><aside class="original-medical"><h2>의료정보 안내</h2><p>'+E(c['disclaimer'])+'</p></aside></article>'
 return s

def apply():
 c=json.loads((ROOT/'homepage-original.json').read_text());p=ROOT/'dist/index.html';s=p.read_text();body=render(c)
 candidates=[r'<article class="home-editorial"[^>]*>.*?</article>',r'<article class="source-homeguide"[^>]*>.*?</article>']
 matches=[(pat,list(re.finditer(pat,s,re.S))) for pat in candidates];found=[(p,m) for p,m in matches if m]
 assert len(found)==1 and len(found[0][1])==1, 'Expected one bounded homepage article'
 pat,match=found[0];assert match[0].group().count('<article')==1, 'Nested article boundary'
 s=re.sub(pat,lambda _:body,s,count=1,flags=re.S)
 s=s.replace('<link rel="stylesheet" href="/homepage-original.css">','').replace('</head>','<link rel="stylesheet" href="/homepage-original.css"></head>')
 s=s.replace('<link rel="stylesheet" href="/homepage-details.css">','')
 p.write_text(s);(ROOT/'dist/homepage-original.css').write_text((ROOT/'homepage-original.css').read_text())
 print('Original homepage-only:',c['name'])
if __name__=='__main__':apply()
