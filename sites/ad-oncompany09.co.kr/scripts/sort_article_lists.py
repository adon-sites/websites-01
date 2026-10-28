"""Sort each complete paginated listing by its visible date, newest first."""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
card_pattern=r'<article class="post-card[^\"]*".*?</article>'
groups={}
for f in OUT.rglob('*.html'):
    s=f.read_text()
    if 'class="post-grid"' not in s:continue
    rel=str(f.relative_to(OUT));m=re.fullmatch(r'(.*?)(?:page/(\d+)/)?index.html',rel)
    assert m,rel
    start=s.index('<div class="post-grid">')+len('<div class="post-grid">')
    end=s.index('</div><nav class="pagination"',start)
    region=s[start:end];cards=re.findall(card_pattern,region,re.S)
    if not cards:continue
    assert ''.join(cards)==region,(rel,'unexpected content in card grid')
    groups.setdefault(m[1],[]).append((int(m[2] or 1),f,s,start,end,cards))
counts={}
for name,pages in groups.items():
    pages.sort(key=lambda x:x[0]);original=[c for p in pages for c in p[5]]
    def key(card):
        m=re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"',card)
        assert m,(name,'missing visible date')
        return m[1]
    ordered=sorted(original,key=key,reverse=True)
    assert sorted(original)==sorted(ordered)
    offset=0
    for n,f,s,start,end,cards in pages:
        replacement=''.join(ordered[offset:offset+len(cards)]);offset+=len(cards)
        updated=s[:start]+replacement+s[end:]
        if updated!=s:f.write_text(updated)
    assert offset==len(original)
    assert [key(c) for c in ordered]==sorted([key(c) for c in original],reverse=True)
    counts[name]=len(original)
print(json.dumps({'sorted_lists':len(groups),'cards':sum(counts.values()),'order':'newest_first','content_preserved':True}))
