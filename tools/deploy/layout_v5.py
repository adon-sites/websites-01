#!/usr/bin/env python3
"""layout_v5.py — 새 글 구조(v5)를 빌드 출력에 적용한다. build_site.py 가 빌드 직후(title_hook 앞)에 호출.
usage: layout_v5.py <sites/<도메인> 경로>
대상: content/posts/<slug>.md 의 frontmatter 에 `layout: v5` 가 있는 글만. 그 표기가 없는 글·목록·홈은 읽지도 고치지도 않는다
      (v5 글이 한 편도 없으면 파일을 하나도 쓰지 않는다 → 기존 출력과 바이트 단위로 같다).
v5 md 표기:
  frontmatter  title/short_title/description/category/date (기존과 같음) + layout: v5 + intro: 도입 문단(한 줄) + tags: 태그 9개(쉼표 구분)
  본문         `## 질문형 소제목` 5개 → `## 자주 묻는 질문` + `### 질문` 6개(질문 아래 답 문단)
               표: `| 머리 | 머리 |` / `| --- | --- |` / `| 칸 | 칸 |` (바로 윗줄 `[표] 제목` 은 표 제목, 생략 가능) — 글당 2개
출력(글 페이지의 <div class="article-content"> 안쪽만 바꾼다. 하단 링크 묶음·이전/다음 글·옆단은 생성기 그대로):
  대표 이미지(-1) → 도입 문단 → [이미지(-2…-6) → h2 → 문단·표]×5 → 자주 묻는 질문(h3 6) → 해시태그 9
  + <head>: FAQPage JSON-LD, BlogPosting.image, og:image, 글 전용 CSS.  rss.xml 의 그 글 본문도 같은 내용으로 바꾼다.
이미지 파일(images/enrich/<slug>-1…6.webp)은 make_images.py 가 만든다(enrich_hook 이 호출). enrich v4 보강은 v5 글을 건너뛴다(enrich_post.V5_MARK).
변환할 수 없는 v5 글이 있으면 exit 1 (md 표가 그대로 보이는 페이지가 배포되지 않게 빌드를 멈춘다)."""
import html, json, re, sys
from pathlib import Path
from urllib.parse import urljoin
from xml.sax.saxutils import escape as xesc, unescape as xunesc

MARK = '<!-- post-layout:v5 -->'
IMG_BASE = '/images/enrich/'
FAQ_HEADING = '자주 묻는 질문'
N_SECTIONS, N_TABLES, N_FAQ, N_TAGS = 5, 2, 6, 9
E = html.escape
CSS = ('<style id="post-v5-css">'
       '.post-img{margin:26px 0 14px}.post-img img{width:100%;height:auto;border-radius:10px;display:block}.post-cover{margin-top:6px}'
       '.post-intro{font-size:1.04rem}'
       '.tbl-label{margin:1.3em 0 .4em;color:#345;font-size:.98rem}.tbl-label em{font-style:italic}'
       '.cmp-wrap{overflow-x:auto;margin:0 0 1.2em}'
       'table.cmp{width:100%;border-collapse:collapse;font-size:.93rem;line-height:1.5;background:#fff}'
       'table.cmp th,table.cmp td{border:1px solid #dfe6ee;padding:9px 10px;text-align:left;vertical-align:top}'
       'table.cmp th{background:#f3f6fa;font-weight:600}table.cmp td:first-child{font-weight:600;color:#2a3b4d}'
       '.faq{margin:32px 0 8px}.faq h2{font-size:1.3rem}.faq-item{border-top:1px solid #e6ebf0;padding:14px 0}'
       '.faq-item h3{font-size:1.02rem;margin:0 0 6px}.faq-item p{margin:0 0 6px;font-size:.95rem;color:#333}'
       '.post-tags{margin:18px 0 0;font-size:.92rem;color:#4a6a8a;word-break:keep-all;line-height:1.9}'
       '</style>')


def frontmatter(raw):
    if not raw.startswith('---\n') or '\n---\n' not in raw: return None, ''
    fm, body = raw[4:].split('\n---\n', 1); meta = {}
    for line in fm.splitlines():
        if ':' in line:
            k, v = line.split(':', 1); meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def parse_tags(v):
    v = (v or '').strip().strip('[]')
    out = []
    for t in re.split(r'[,\s]+', v):
        t = re.sub(r'[^가-힣A-Za-z0-9]', '', t)
        if t and t not in out: out.append(t)
    return out


def cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def parse_v5(raw):
    """returns dict(meta, intro, sections=[{heading, blocks}], faq=[(q, [answer paragraphs])], tags).
    block = ('p', text) | ('table', caption, head[], rows[][]) | ('h3', text)"""
    meta, body = frontmatter(raw)
    sections, faq, cur, para, in_faq = [], [], None, [], False
    lines = body.strip().splitlines(); i = 0; caption = ''

    def flush():
        nonlocal para
        if not para: return
        text = ' '.join(para); para = []
        if in_faq:
            if faq: faq[-1][1].append(text)
        elif cur is not None: cur['blocks'].append(('p', text))
    while i < len(lines):
        line = lines[i].rstrip(); s = line.strip()
        if line.startswith('## '):
            flush(); h = line[3:].strip()
            if h == FAQ_HEADING: in_faq = True; cur = None
            else: in_faq = False; cur = {'heading': h, 'blocks': []}; sections.append(cur)
        elif line.startswith('### '):
            flush()
            if in_faq: faq.append((line[4:].strip(), []))
            elif cur is not None: cur['blocks'].append(('h3', line[4:].strip()))
        elif s.startswith('[표]') and i + 1 < len(lines) and lines[i + 1].strip().startswith('|'):
            flush(); caption = s[3:].strip()
        elif s.startswith('|') and i + 1 < len(lines) and re.fullmatch(r'\|?[\s:|-]+\|?', lines[i + 1].strip()) and '-' in lines[i + 1]:
            flush(); head = cells(s); rows = []; i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                r = cells(lines[i]); rows.append((r + [''] * len(head))[:len(head)]); i += 1
            if cur is not None and not in_faq: cur['blocks'].append(('table', caption, head, rows))
            caption = ''; continue
        elif not s: flush()
        else: para.append(s)
        i += 1
    flush()
    return {'meta': meta, 'intro': meta.get('intro', ''), 'sections': sections, 'faq': faq, 'tags': parse_tags(meta.get('tags'))}


def problems(doc):
    """구조 점검(경고용). 변환은 개수가 달라도 한다."""
    w = []
    nt = sum(1 for s in doc['sections'] for b in s['blocks'] if b[0] == 'table')
    if not doc['intro']: w.append('intro 없음')
    if len(doc['sections']) != N_SECTIONS: w.append(f'소제목 {len(doc["sections"])}개(기준 {N_SECTIONS})')
    if nt != N_TABLES: w.append(f'표 {nt}개(기준 {N_TABLES})')
    if len(doc['faq']) != N_FAQ: w.append(f'질문 {len(doc["faq"])}개(기준 {N_FAQ})')
    if len(doc['tags']) != N_TAGS: w.append(f'해시태그 {len(doc["tags"])}개(기준 {N_TAGS})')
    return w


def fig(slug, n, alt, cover=False):
    return (f'<figure class="post-img{" post-cover" if cover else ""}"><img src="{IMG_BASE}{slug}-{n}.webp" alt="{E(alt, quote=True)}" width="1200" height="675" '
            + ('loading="eager" fetchpriority="high"' if cover else 'loading="lazy"') + ' decoding="async"></figure>')


def table_html(caption, head, rows):
    cap = f'<p class="tbl-label"><em>{E(caption)}</em></p>' if caption else ''
    return (cap + '<div class="cmp-wrap"><table class="cmp"><thead><tr>' + ''.join(f'<th scope="col">{E(h)}</th>' for h in head) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{E(c)}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table></div>')


def render(doc, slug, title):
    out = [MARK, fig(slug, 1, title, cover=True)]
    if doc['intro']: out.append(f'<p class="post-intro">{E(doc["intro"])}</p>')
    for i, s in enumerate(doc['sections'], 1):
        out.append(fig(slug, i + 1, s['heading']) + f'<h2 id="s{i}">{E(s["heading"])}</h2>')
        for b in s['blocks']:
            if b[0] == 'p': out.append(f'<p>{E(b[1])}</p>')
            elif b[0] == 'h3': out.append(f'<h3>{E(b[1])}</h3>')
            else: out.append(table_html(b[1], b[2], b[3]))
    if doc['faq']:
        out.append(f'<section class="faq" id="faq"><h2>{FAQ_HEADING}</h2>' + ''.join(
            f'<div class="faq-item"><h3>{E(q)}</h3>' + ''.join(f'<p>{E(a)}</p>' for a in ans) + '</div>' for q, ans in doc['faq']) + '</section>')
    if doc['tags']: out.append('<p class="tags post-tags">' + ' '.join('#' + E(t) for t in doc['tags']) + '</p>')
    return ''.join(out)


def jscript(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '</script>'


CONTENT_RE = re.compile(r'(<div class="article-content">)(.*?)(</div>)', re.S)


def apply_page(s, doc, slug):
    """글 페이지 한 장. returns (새 HTML, 옛 본문 안쪽, 새 본문 안쪽) — 이미 적용됐으면 (s, None, None)."""
    if MARK in s: return s, None, None
    m = CONTENT_RE.search(s)
    if not m: raise ValueError('<div class="article-content"> 없음')
    old = m.group(2)
    if re.search(r'<(?!/?(?:h2|p)>)', old): raise ValueError('본문에 h2·p 가 아닌 태그가 있어 v5 로 바꾸지 않음(생성기 출력이 예상과 다름)')
    h1 = re.search(r'<h1\b[^>]*>(.*?)</h1>', s, re.S)
    title = html.unescape(re.sub(r'<[^>]+>', '', h1.group(1))).strip() if h1 else doc['meta'].get('title', '')
    new = render(doc, slug, title)
    s = s[:m.start(2)] + new + s[m.end(2):]
    canon = re.search(r'<link rel="canonical" href="(https?://[^/"]+)', s); origin = canon.group(1) if canon else ''
    img = origin + f'{IMG_BASE}{slug}-1.webp'
    head = ''
    # BlogPosting 에 대표 이미지(제목·설명 등 다른 값은 그대로)
    def bp(mm):
        try: d = json.loads(mm.group(1))
        except Exception: return mm.group(0)
        if not isinstance(d, dict) or d.get('@type') != 'BlogPosting' or d.get('image'): return mm.group(0)
        d['image'] = {'@type': 'ImageObject', 'url': img, 'width': 1200, 'height': 675}
        return jscript(d)
    s = re.sub(r'<script type="application/ld\+json">(.*?)</script>', bp, s, count=1, flags=re.S)
    if 'property="og:image"' not in s:
        head += (f'<meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="675">'
                 f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{img}">')
    if doc['faq']:
        head += jscript({'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': ' '.join(ans)}} for q, ans in doc['faq']]})
    s = s.replace('</head>', head + CSS + '</head>', 1)
    return s, old, new


def patch_rss(rss, link, new_inner, base):
    """rss.xml 에서 그 글 item 의 description 본문만 새 본문으로(이미지 주소는 절대 주소)."""
    def item(m):
        it = m.group(0)
        if f'<link>{xesc(link)}</link>' not in it: return it
        d = re.search(r'(<description>)(.*?)(</description>)', it, re.S)
        if not d: return it
        body = xunesc(d.group(2))
        if MARK in body: return it
        inner = re.sub(r'(href|src)="([^"#][^"]*)"', lambda x: x.group(1) + '="' + urljoin(base, x.group(2)) + '"', new_inner)
        body2, n = CONTENT_RE.subn(lambda x: x.group(1) + inner + x.group(3), body, count=1)
        return it[:d.start(2)] + xesc(body2) + it[d.end(2):] if n else it
    return re.sub(r'<item>.*?</item>', item, rss, flags=re.S)


def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8')); domain = sj['domain']; out = site / sj['dist']
    posts = site / 'content' / 'posts'
    done = held = 0; bad = []; warns = []
    rss_p = out / 'rss.xml'; rss = rss_p.read_text(encoding='utf-8') if rss_p.is_file() else ''; rss0 = rss
    for md in sorted(posts.glob('*.md')) if posts.is_dir() else []:
        with md.open(encoding='utf-8') as f: headtxt = f.read(4000)
        fm = headtxt[4:].split('\n---\n', 1)[0] if headtxt.startswith('---\n') else ''
        if not re.search(r'^layout:\s*["\']?v5["\']?\s*$', fm, re.M): continue
        slug = md.stem; page = out / 'blog' / slug / 'index.html'
        if not page.is_file(): held += 1; continue   # 예약(미래 날짜) 글은 생성기가 아직 만들지 않는다
        try:
            doc = parse_v5(md.read_text(encoding='utf-8'))
            if not doc['sections']: raise ValueError('소제목 없음')
            s = page.read_text(encoding='utf-8')
            s2, old, new = apply_page(s, doc, slug)
            if new is None: continue
            page.write_text(s2, encoding='utf-8'); done += 1
            w = problems(doc)
            if w: warns.append(f'{slug}: ' + ', '.join(w))
            canon = re.search(r'<link rel="canonical" href="([^"]+)"', s2)
            if rss and canon and f'<link>{xesc(canon.group(1))}</link>' in rss: rss = patch_rss(rss, canon.group(1), new, canon.group(1))   # rss 는 최신 30편만
        except Exception as e:
            bad.append(f'{slug}: {e}')
    if rss != rss0: rss_p.write_text(rss, encoding='utf-8')
    print(f'[{domain}] layout v5: 적용 {done}편 · 예약 대기 {held} · 경고 {len(warns)} · 실패 {len(bad)}')
    for w in warns[:20]: print(f'::warning::[{domain}] v5 구조 {w}')
    for b in bad[:20]: print(f'::error::[{domain}] v5 변환 실패 {b}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__': main()
