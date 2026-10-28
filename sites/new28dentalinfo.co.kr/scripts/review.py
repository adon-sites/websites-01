import json,re,hashlib,collections,pathlib,itertools
R=pathlib.Path(__file__).resolve().parents[1];posts=json.loads((R/'content/posts.json').read_text());pages=json.loads((R/'content/pages.json').read_text())
def normalize(s):return re.sub(r'[^가-힣a-z0-9]','',s.lower())
def shingles(s,n=12):
 s=normalize(s)
 return {s[i:i+n] for i in range(max(0,len(s)-n+1))}
ref={p.name:p for p in (R/'content/reference').glob('*.txt')}
def source_names(sources):
 out=[]
 for source in sources:
  if isinstance(source,str) and not re.match(r'https?://',source): out.append(pathlib.Path(source).name)
  elif isinstance(source,dict) and source.get('path'): out.append(pathlib.Path(source['path']).name)
 return out
assert len(posts)==len({p['slug'] for p in posts})==len({normalize(p['title']) for p in posts})
assert set(p['slug'] for p in posts).isdisjoint({p['slug'] for p in pages})
for p in posts:
 names=source_names(p.get('sources',[]))
 assert (p.get('sources') or p.get('sourceScope')) and all(x in ref for x in names),(p['slug'],p.get('sources'))
 assert len(p['sections'])>=7,(p['slug'],'sections')
 assert len({normalize(s[0]) for s in p['sections']})==len(p['sections'])
 assert all(len(s[1])>60 for s in p['sections'])
 txt=' '.join(s[1] for s in p['sections'])
 assert not re.search(r'100%|완치|부작용 없음|반영구적|원장입니다|(?<![가-힣])기적(?:의|인)|최저가',txt),(p['slug'],'claims')
 assert len(normalize(txt))>=650,(p['slug'],'length')
texts={p['slug']:shingles(' '.join(s[1] for s in p['sections'])) for p in posts}
pairs=[]
for (a,x),(b,y) in itertools.combinations(texts.items(),2):
 score=len(x&y)/min(len(x),len(y))
 pairs.append((score,a,b))
assert max(pairs)[0]<.12,sorted(pairs,reverse=True)[:5]
ref_text={}
for name,path in ref.items():
 b=path.read_bytes()
 try:s=b.decode('utf-8-sig')
 except UnicodeDecodeError:s=b.decode('cp949')
 ref_text[name]=shingles(s)
source_max=[]
for slug,g in texts.items():
 score,name=max((len(g&x)/len(g),name) for name,x in ref_text.items())
 source_max.append((score,slug,name))
assert max(source_max)[0]<.1,sorted(source_max,reverse=True)[:5]
used=set(itertools.chain.from_iterable(source_names(x.get('sources',[])) for x in posts));unassigned=sorted(set(ref)-used)
report={'reference_text_files':len(ref),'published_articles':len(posts),'site_article_total':len(pages)+len(posts),'source_files_used':len(used),'supplemental_evidence_articles':sum(bool(p.get('evidenceUrls')) for p in posts),'shortest_visible_body':min(len(''.join(s[1] for s in p['sections'])) for p in posts),'other_reference_files':len(unassigned),'other_reference_reason':'지역명 변형, 같은 치료 주제의 반복, 카페 질문글·의료진 명의 칼럼 포함. 개별 검수 전 추가 공개하지 않음.','other_reference_names':unassigned,'maximum_12gram_overlap_between_new_articles':round(max(pairs)[0],3),'maximum_12gram_containment_in_an_original':round(max(source_max)[0],3),'image_policy':'대표 6개 글만 본문·목록 이미지 사용; 신규 건강정보 글은 텍스트만','backlink_policy':'각 대표·건강정보 글 하단 시흥치과 → 사이트 메인 1회','medical_review':'금지 단정 표현 정적 검사; 개별 진단·효과 보장 없음','checked_on':'2026-10-07'}
(R/'content/review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='other_reference_names'},ensure_ascii=False))
