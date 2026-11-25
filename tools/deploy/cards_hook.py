#!/usr/bin/env python3
"""cards_hook.py — 홈 카드 6장이 가리키는 6개 페이지(카드 페이지) 본문 아래에 홈과 같은 카드 6장 목록을 넣는다. 빌드 출력에만 적용, 멱등.
usage: cards_hook.py <sites/<도메인> 경로>
  - 대상: 병원·정보 사이트(group hospital/info/wp). 마케팅 사이트와 cards_hook_skip.json 의 도메인은 건드리지 않는다.
  - 카드 페이지 = 홈 ItemList 의 6개 주소(treatments/ 뿐 아니라 about/, clinic/, contact/, journal/ 등 포함).
  - 카드 = ItemList 의 사진(860 JPG 등), 제목, 주소, 순서 그대로. width·height·alt 는 홈 카드 <img> 값을 그대로 쓴다. 자기 자신 카드 포함 6장.
  - 사진은 <a> 로 감싸고 loading="lazy", 제목은 <h4><a>.
  - 넣는 자리: 본문 아래, 면책 문구(disclaimer·의료정보 안내·출처 표기) 바로 위. 못 찾으면 본문 끝(</article> 또는 </main> 앞).
  - 이미 홈 카드 6장이 나오는 페이지(다른 카드 5장 이상이 사진+링크로 있음)는 건드리지 않는다.
  - 바꾸지 않는 것: 카드 페이지의 title·H1·본문·본문 상단 사진·og:image·구조화 데이터, 홈.
  - 사용자 지시(2026-11-26): 병원·정보 사이트 전부(mediwoman-info.co.kr 제외) 카드 페이지에 카드 6장 목록 추가.
"""
import html, json, os, re, sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

MARK = 'id="home-cards"'
SKIP = {'mediwoman-info.co.kr'}
CSS = ('<style id="home-cards-style">.home-cards{max-width:1080px;margin:44px auto 28px;padding:0 20px}'
       '.home-cards .hc-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}'
       '.home-cards .hc-card{margin:0}.home-cards .hc-card a{color:inherit;text-decoration:none}'
       '.home-cards .hc-card img{display:block;width:100%;height:auto;aspect-ratio:1/1;object-fit:cover;border-radius:10px}'
       '.home-cards .hc-card h4{margin:10px 0 0;font-size:.98rem;line-height:1.45;font-weight:700}'
       '@media(max-width:760px){.home-cards .hc-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.home-cards .hc-card h4{font-size:.9rem}}</style>')


VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
DISC = re.compile(r'\b(disclaimer|medical-note|article-source|original-medical|source-links|notice|fine)\b')
GRIDC = re.compile(r'\b(grid|cols|flex|content-grid|detail-layout)\b')


class _P(HTMLParser):
    """본문(<main>) 안 요소의 시작 위치·부모·글자 수를 모은다(표준 라이브러리만 사용)."""
    def __init__(self, src):
        super().__init__(convert_charrefs=True); self.src = src
        self.ls = [0]
        for line in src.split('\n'): self.ls.append(self.ls[-1] + len(line) + 1)
        self.nodes = []; self.stack = []; self.main = None; self.main_end = None
    def off(self): l, c = self.getpos(); return self.ls[l - 1] + c
    def handle_starttag(self, tag, attrs):
        if tag in VOID: return
        n = {'tag': tag, 'cls': dict(attrs).get('class') or '', 'start': self.off(), 'parent': self.stack[-1] if self.stack else None, 'text': 0, 'end': None, 'first': ''}
        self.nodes.append(n); self.stack.append(len(self.nodes) - 1)
        if tag == 'main' and self.main is None: self.main = len(self.nodes) - 1
    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.nodes[self.stack[i]]['tag'] == tag:
                self.nodes[self.stack[i]]['end'] = self.off()
                if self.stack[i] == self.main: self.main_end = self.off()
                del self.stack[i:]; break
    def handle_data(self, data):
        t = data.strip()
        if not t: return
        for i in self.stack:
            n = self.nodes[i]; n['text'] += len(t)
            if not n['first']: n['first'] = t[:12]


def insert_pos(rest):
    """카드 목록을 넣을 위치: 본문 안 마지막 면책 문구(또는 그것만 감싼 작은 상자) 바로 앞. 없으면 </main> 바로 앞."""
    ps = _P(rest)
    try: ps.feed(rest)
    except Exception: return None
    if ps.main is None or ps.main_end is None:
        e = rest.rfind('</main>')
        if e < 0: e = rest.rfind('</article>')
        return e if e >= 0 else None
    def inside_main(i):
        while i is not None:
            if i == ps.main: return True
            i = ps.nodes[i]['parent']
        return False
    def skipzone(i):
        while i is not None:
            if ps.nodes[i]['tag'] in ('header', 'nav', 'footer', 'table', 'figure'): return True
            i = ps.nodes[i]['parent']
        return False
    D = None
    for i, n in enumerate(ps.nodes):
        if i == ps.main or not inside_main(i) or skipzone(i) or n['end'] is None: continue
        if n['tag'] in ('p', 'div', 'aside', 'section') and (DISC.search(n['cls']) or (n['tag'] == 'p' and n['first'].startswith('※'))) and n['text'] >= 20: D = i
    if D is None: return ps.main_end
    X = D
    while True:
        p = ps.nodes[X]['parent']
        if p is None or p == ps.main: break
        pn = ps.nodes[p]
        if pn['tag'] in ('section', 'aside', 'div') and not GRIDC.search(pn['cls']) and pn['text'] <= max(600, int(ps.nodes[D]['text'] * 2.5)) and pn['tag'] != 'article': X = p
        else: break
    par = ps.nodes[X]['parent']
    if par is not None and par != ps.main and GRIDC.search(ps.nodes[par]['cls']): return ps.main_end
    return ps.nodes[X]['start']


def path_of(u):
    p = unquote(urlparse(u).path) if re.match(r'https?://', u or '') else unquote((u or '').split('#')[0].split('?')[0])
    return p or '/'


def norm(p): return p.rstrip('/') or '/'


def page_file(out: Path, p):
    rel = p.lstrip('/')
    for c in (out / rel / 'index.html', out / rel, out / (rel.rstrip('/') + '.html')):
        if c.is_file(): return c
    return None


def attr(tag, name):
    m = re.search(r'\b' + name + r'\s*=\s*"([^"]*)"', tag) or re.search(r'\b' + name + r"\s*=\s*'([^']*)'", tag)
    return m.group(1) if m else None


def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8')); domain = sj['domain']
    if sj.get('group') not in ('hospital', 'info', 'wp') or domain in SKIP:
        print(f'[{domain}] cards: 대상 아님'); return
    out = site / sj['dist']; hf = out / 'index.html'
    if not hf.exists(): print(f'[{domain}] cards: 홈 없음'); return
    home = hf.read_text(encoding='utf-8')
    items = []
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', home, re.S):
        try: data = json.loads(m.group(1))
        except Exception: continue
        for n in (data.get('@graph', [data]) if isinstance(data, dict) else data):
            if isinstance(n, dict) and n.get('@type') == 'ItemList' and not items:
                for it in n.get('itemListElement', []):
                    x = it.get('item') if isinstance(it.get('item'), dict) else it
                    u = x.get('url') or it.get('url') or (it.get('item') if isinstance(it.get('item'), str) else None)
                    img = x.get('image') or it.get('image')
                    if isinstance(img, list): img = img[0] if img else None
                    if isinstance(img, dict): img = img.get('url')
                    items.append({'name': x.get('name') or it.get('name') or '', 'path': path_of(u or ''), 'img': path_of(img or '')})
    if len(items) != 6 or any(not i['name'] or not i['img'] for i in items):
        print(f'[{domain}] cards: 홈 ItemList 6항목(이름·주소·사진)을 읽지 못함 → 건너뜀'); return
    # 홈 카드 <img> 의 width·height·alt : 카드 주소로 가는 <a> 안의 첫 <img>
    body = home.split('</head>', 1)[-1]
    for it in items:
        it['w'] = it['h'] = it['alt'] = None; it['href'] = it['path']
        for a in re.finditer(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>', body, re.S):
            if norm(path_of(html.unescape(a.group(1)))) != norm(it['path']): continue
            im = re.search(r'<img\b[^>]*>', a.group(2))
            if not im: continue
            it['w'], it['h'], it['alt'] = attr(im.group(0), 'width'), attr(im.group(0), 'height'), attr(im.group(0), 'alt')
            it['href'] = html.unescape(a.group(1)) if not re.match(r'https?://', a.group(1)) else it['path']
            break
        if it['alt'] is None:
            print(f'[{domain}] cards: 홈에서 카드 사진을 찾지 못함({it["path"]}) → 건너뜀'); return
    E = lambda x: html.escape(x or '', quote=True)
    def card(it):
        wh = (f' width="{E(it["w"])}"' if it['w'] else '') + (f' height="{E(it["h"])}"' if it['h'] else '')
        return (f'<article class="hc-card"><a href="{E(it["href"])}"><img src="{E(it["img"])}"{wh} alt="{it["alt"]}" loading="lazy" decoding="async"></a>'
                f'<h4><a href="{E(it["href"])}">{E(html.unescape(it["name"]))}</a></h4></article>')
    block = f'<section class="home-cards" {MARK} aria-label="주요 안내">' + '<div class="hc-grid">' + ''.join(card(i) for i in items) + '</div></section>\n'
    res = []
    for it in items:
        pf = page_file(out, it['path'])
        if not pf: res.append('없음'); continue
        s = pf.read_text(encoding='utf-8')
        if MARK in s: res.append('유지'); continue
        head, _, rest = s.partition('</head>')
        # 이미 홈 카드가 나오는 페이지: 다른 카드 5장 이상이 (그 카드 주소로 가는 링크 + 그 카드 사진)으로 있음
        zone = re.sub(r'<(header|nav|footer)\b.*?</\1>', '', rest, flags=re.S)
        have = 0
        for o in items:
            if o is it: continue
            base = os.path.basename(o['img']); stem = re.sub(r'(-\d+)?\.[a-z]+$', '', base)
            for a in re.finditer(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>', zone, re.S):
                if norm(path_of(html.unescape(a.group(1)))) == norm(o['path']) and re.search(r'<img\b[^>]*' + re.escape(stem), a.group(2)): have += 1; break
        if have >= 5: res.append('이미 있음'); continue
        pos = insert_pos(rest)
        if pos is None: res.append('자리 없음'); continue
        rest = rest[:pos] + block + rest[pos:]
        if 'id="home-cards-style"' not in head: head += CSS
        pf.write_text(head + '</head>' + rest, encoding='utf-8'); res.append('적용')
    print(f'[{domain}] cards: ' + ' · '.join(f'{i + 1}:{r}' for i, r in enumerate(res)))


if __name__ == '__main__':
    main()
