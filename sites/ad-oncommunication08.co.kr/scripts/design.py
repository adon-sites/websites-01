from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'dist';T=json.loads((ROOT/'content/design.json').read_text())
for p in D.rglob('*.html'):
 s=p.read_text()
 route='home' if p==D/'index.html' else ('listing' if 'class="post-grid"' in s else 'article')
 s=s.replace('<body>',f'<body class="route-{route}" data-design="{T["name"]}">',1)
 s=s.replace('</head>','<link rel="stylesheet" href="/theme.css"></head>',1)
 s=re.sub(r'(<meta name="theme-color" content=")[^"]+',lambda m:m[1]+T['accent'],s)
 if route=='home':
  s=s.replace('<section class="feature-grid"','<div class="design-kicker"><span>AD-ON / 병원마케팅 가이드</span><a href="/blog/">전체 글 보기 →</a></div><section class="feature-grid"',1)
 if T['feature']=='ribbon':s=s.replace('class="feature-grid"','class="feature-grid keep-ribbon"')
 p.write_text(s)
print(json.dumps({'design':T['name'],'html_pages':len(list(D.rglob('*.html')))},ensure_ascii=False))
