"""Append a source-based homepage budget guide; never mutates publication content."""
from pathlib import Path
import json,html,re
ROOT=Path(__file__).resolve().parent
E=lambda v:html.escape(str(v),quote=True)
def render(c):
 s='<section class="cost-guide" id="cost-maintenance" aria-labelledby="cost-maintenance-title" data-cost-revision="'+E(c['revision'])+'" style="--cost-accent:'+E(c.get('accent','#335eaa'))+'"><p class="cost-kicker">'+E(c['eyebrow'])+'</p><h2 id="cost-maintenance-title">'+E(c['title'])+'</h2>'
 s+=''.join('<p>'+E(x)+'</p>'for x in c['intro'])+'<p class="cost-date">'+E(c['dateNote'])+'</p>'
 s+='<table><caption>'+E(c.get('caption','출처가 확인된 공개 사례만 표시했습니다. 확인되지 않은 평균·고정 유지비는 계산하지 않습니다.'))+'</caption><thead><tr>'+''.join('<th scope="col">'+E(x)+'</th>'for x in c['columns'])+'</tr></thead><tbody>'
 for r in c['rows']:
  s+='<tr><th scope="row">'+E(r['treatment'])+'</th><td data-label="'+E(c['columns'][1])+'"><strong class="cost-price">'+E(r['price'])+'</strong></td><td data-label="'+E(c['columns'][2])+'">'+E(r['timing'])+'</td><td data-label="'+E(c['columns'][3])+'">'+E(r['annual'])+'</td></tr>'
 s+='</tbody></table><div class="cost-table-notes"><p>'+E(c['methodNote'])+'</p><ul>'+''.join('<li><strong>'+E(r['treatment'])+'</strong>: '+E(r['priceNote'])+'</li>' for r in c['rows'])+'</ul></div><div class="cost-calculation"><h3>'+E(c['calculationTitle'])+'</h3><ul>'+''.join('<li>'+E(x)+'</li>'for x in c['calculation'])+'</ul></div><p class="cost-safety">'+E(c['note'])+'</p><details><summary>가격·관리 안내의 출처와 산정 기준</summary><ol class="cost-sources">'
 for r in c['sources']:s+='<li><a href="'+E(r['url'])+'" target="_blank" rel="noopener noreferrer">'+E(r['label'])+'</a><span>'+E(r['note'])+'</span></li>'
 return s+'</ol></details></section>'
def apply():
 c=json.loads((ROOT/'homepage-cost-guide.json').read_text());p=ROOT/'dist/index.html';s=p.read_text();assert s.count('</main>')==1
 s=re.sub(r'<!-- COST_GUIDE_START -->.*?<!-- COST_GUIDE_END -->','',s,flags=re.S)
 s=s.replace('</main>','<!-- COST_GUIDE_START -->'+render(c)+'<!-- COST_GUIDE_END --></main>')
 link='<link rel="stylesheet" href="/homepage-cost-guide.css">';s=s.replace(link,'').replace('</head>',link+'</head>');p.write_text(s);(ROOT/'dist/homepage-cost-guide.css').write_text((ROOT/'homepage-cost-guide.css').read_text())
 print('Cost/maintenance homepage guide:',c['name'],len(c['rows']),'rows')
if __name__=='__main__':apply()
