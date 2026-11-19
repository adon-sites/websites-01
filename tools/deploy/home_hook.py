#!/usr/bin/env python3
"""home_hook.py — 병원·업체 사이트 첫 페이지(index.html)를 빌드 출력에서 보강한다. build_site.py 가 enrich_hook 다음에 호출(커밋본 홈은 그대로 두고 배포 때마다 적용, 멱등).
usage: home_hook.py <sites/<도메인> 경로>
근거: 레퍼런스 3곳(orthocareplus·orthomedical·na-medi.kr) 첫 페이지 구조 비교 → 사용자 2026-11-19 16:47 "제안한대로 모두 적용, 제목 키워드만, 자매링크는 범어·나의계절만".
 ① <title>·og:title·twitter:title = 키워드만  ② og:site_name = "키워드 | 병원명", article:modified_time(최신 글 시각)
 ③ 본문 h2 를 "키워드 : 소제목" 으로(키워드·병원명·오시는 길·병원 안내 h2 는 그대로, 최대 8개)  ④ 목차(h2 앵커)
 ⑤ 대표 카드 다음에 최근 글 6개 카드(rss.xml 순서; <!-- home:latest --> 구간은 발행 때마다 바뀌므로 r2_sync 보호 검사에서 제외)
 ⑥ 자주 묻는 질문이 없으면 6문항(질문에 키워드, 답은 그 페이지의 안내 문장 인용)  ⑦ 같은 병원 사이트끼리 푸터 링크(SISTERS)
 ⑧ 화면 키워드 수가 KW_MAX 를 넘으면 최근 글 alt·FAQ 질문·카드 외 이미지 alt 의 키워드를 뺀다.
h3 에는 키워드를 넣지 않는다(카드 제목 h3 는 이미 키워드로 시작 — 과다 반복 방지). 마케팅 사이트는 대상 아님."""
import html, json, re, sys, urllib.parse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enrich_post as E

MARK = '<!-- home:v1 -->'
KW_MAX = 45
SISTERS = {'beomeorosee.co.kr': ['beomeoroseeskininfo.co.kr'], 'beomeoroseeskininfo.co.kr': ['beomeorosee.co.kr'],
           'myseasonclinicinfo.co.kr': ['myseasonclinic-ulsaninfo.co.kr'], 'myseasonclinic-ulsaninfo.co.kr': ['myseasonclinicinfo.co.kr']}
H2_KEEP = re.compile(r'오시는 길|병원 안내|의원 안내|의료정보 안내|주요 안내|진료시간|진료 시간|자주 묻는|최근 안내 글')
KST = timezone(timedelta(hours=9))
CSS = """
.home-toc{max-width:1080px;margin:28px auto 8px;padding:16px 20px;border:1px solid #e3e8ee;border-radius:12px;background:#fafbfc;font-size:.95rem}
.home-toc strong{display:block;margin:0 0 8px}.home-toc ol{margin:0;padding-left:1.3em;columns:2;column-gap:28px}.home-toc li{margin:0 0 6px;break-inside:avoid}.home-toc a{color:inherit;text-decoration:underline}
@media(max-width:640px){.home-toc ol{columns:1}}
.home-latest{max-width:1080px;margin:36px auto 8px;padding:0 20px}.home-latest h2{font-size:1.35rem;margin:0 0 14px}
.home-latest ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.home-latest li{margin:0}.home-latest a{display:block;color:inherit;text-decoration:none;border:1px solid #e3e8ee;border-radius:12px;overflow:hidden;background:#fff;height:100%}
.home-latest img{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:cover}.home-latest span{display:block;padding:10px 12px 12px;font-size:.95rem;line-height:1.45;word-break:keep-all}
@media(max-width:820px){.home-latest ul{grid-template-columns:repeat(2,1fr)}}@media(max-width:520px){.home-latest ul{grid-template-columns:1fr}}
.home-faq{max-width:1080px;margin:40px auto 8px;padding:0 20px}.home-faq h2{font-size:1.35rem;margin:0 0 10px}
.home-faq .faq-item{border-top:1px solid #e6ebf0;padding:14px 0}.home-faq h3{font-size:1.02rem;margin:0 0 6px}.home-faq p{margin:0;font-size:.95rem;color:#333}
.home-faq .faq-q{color:#2a5d8f;font-weight:700;margin-right:2px}.home-faq .faq-a{color:#b4532a;font-weight:700;margin-right:2px}
.home-sister{margin:14px 0 0;font-size:.9rem}.home-sister a{text-decoration:underline;color:inherit}
"""
FAQ_Q = ['{kw} 상담 전에 ‘{h}’에서 먼저 확인할 점은 무엇인가요?', '{kw} ‘{h}’ 내용은 누구에게나 똑같이 적용되나요?', '{kw} 상담에서 ‘{h}’ 내용은 어떻게 활용하면 되나요?',
         '{kw} ‘{h}’{g} 관련해 미리 준비할 것이 있나요?', '{kw} ‘{h}’ 내용을 읽고 궁금한 점이 남으면 어떻게 하나요?']
FAQ_Q_NK = ['상담 전에 ‘{h}’에서 먼저 확인할 점은 무엇인가요?', '‘{h}’ 내용은 누구에게나 똑같이 적용되나요?', '상담에서 ‘{h}’ 내용은 어떻게 활용하면 되나요?',
            '‘{h}’{g} 관련해 미리 준비할 것이 있나요?', '‘{h}’ 내용을 읽고 궁금한 점이 남으면 어떻게 하나요?']
FAQ_A = [('이 페이지에서는 “{s}”라고 안내해 드리고 있습니다. 해당하는 부분이 있으면 상담 때 말씀해 주시기 바랍니다.', '현재 상태와 궁금한 점을 먼저 정리해 오시면 상담에서 차례로 확인해 드립니다.'),
         ('개인의 상태에 따라 달라집니다. “{s}”라는 안내를 참고하시되, 구체적인 적용은 진료에서 확인해 드립니다.', '개인의 상태에 따라 달라집니다. 구체적인 적용은 진료에서 확인해 드립니다.'),
         ('“{s}”라는 안내를 기준으로 본인에게 해당하는 부분을 상담에서 질문해 주시면 됩니다.', '안내 내용 가운데 본인에게 해당하는 부분을 상담에서 질문해 주시면 됩니다.'),
         ('“{s}”라는 안내와 관련된 기록이나 자료가 있으면 내원하실 때 함께 가져와 주시기 바랍니다.', '관련된 기록이나 자료가 있으면 내원하실 때 함께 가져와 주시기 바랍니다.'),
         ('', '남은 질문은 메모해 두셨다가 상담에서 말씀해 주시기 바랍니다. 진료에서 직접 확인해 드립니다.')]
FAQ_LAST = ('{kw} 진료시간과 오시는 길은 어디에서 확인하나요?', '진료시간과 오시는 길은 어디에서 확인하나요?', '이 페이지의 오시는 길과 병원 안내 항목에 정리해 두었습니다. 진료시간은 변경될 수 있으니 방문 전에 확인해 주시기 바랍니다.')

def text(h): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)\b.*?</\1>', '', h, flags=re.S)))).strip()
def set_meta(s, attr, name, value):
    v = html.escape(value, quote=True)
    pat = re.compile(r'(<meta\b[^>]*\b' + attr + r'="' + re.escape(name) + r'"[^>]*\bcontent=")[^"]*(")')
    if pat.search(s): return pat.sub(lambda m: m.group(1) + v + m.group(2), s, count=1)
    pat2 = re.compile(r'(<meta\b[^>]*\bcontent=")[^"]*("[^>]*\b' + attr + r'="' + re.escape(name) + r'")')
    if pat2.search(s): return pat2.sub(lambda m: m.group(1) + v + m.group(2), s, count=1)
    return s.replace('</head>', f'<meta {attr}="{name}" content="{v}">\n</head>', 1)

def latest_posts(out: Path, domain, post_prefix, n=6):
    rss = out / 'rss.xml'
    if not rss.is_file(): return [], None
    items = []; now = datetime.now(KST)
    for it in re.findall(r'<item>(.*?)</item>', rss.read_text(encoding='utf-8'), re.S):
        l = re.search(r'<link>(.*?)</link>', it, re.S); t = re.search(r'<title>(.*?)</title>', it, re.S); d = re.search(r'<pubDate>(.*?)</pubDate>', it)
        if not (l and t): continue
        link = html.unescape(l.group(1).strip()); path = urllib.parse.urlparse(link).path
        if post_prefix and not path.startswith(post_prefix): continue
        if path in ('/', '') : continue
        dt = None
        if d:
            try: dt = parsedate_to_datetime(d.group(1))
            except Exception: dt = None
        if dt and dt > now: continue
        title = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', t.group(1))).strip()
        items.append((dt, path, title))
    if items and all(i[0] for i in items): items.sort(key=lambda i: i[0], reverse=True)
    newest = next((i[0] for i in items if i[0]), None)
    return items[:n], newest

def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8')); domain = sj['domain']
    cfg = json.loads((HERE / 'enrich_sites.json').read_text(encoding='utf-8')); me = cfg.get(domain)
    if not me or me.get('group') == 'marketing': print(f'[{domain}] home: 대상 아님'); return
    out = site / sj['dist']; p = out / 'index.html'
    if not p.is_file(): print(f'[{domain}] home: index.html 없음'); return
    s = p.read_text(encoding='utf-8')
    if MARK in s: print(f'[{domain}] home: 이미 적용'); return
    kw = E.kw_parts(me['keyword'])[0]; name = me.get('site_name') or sj.get('name') or ''
    E.set_profile(me.get('profile')); E._AVOID = []
    a0 = s.find('<main'); a1 = s.find('</main>')
    if a0 == -1 or a1 == -1 or '<h1' not in s: print(f'[{domain}] home: main/h1 없음 → 건너뜀'); return
    base_cnt = text(s[s.find('<body'):]).count(kw)
    head_end = s.find('</head>'); head, rest = s[:head_end], s[head_end:]
    # ① 제목 = 키워드만
    head = re.sub(r'<title>.*?</title>', lambda m: f'<title>{html.escape(kw)}</title>', head, count=1, flags=re.S)
    head = set_meta(head + '</head>', 'property', 'og:title', kw)[:-7]; head = set_meta(head + '</head>', 'name', 'twitter:title', kw)[:-7]
    # ② site_name · 수정 시각
    pm = re.match(r'^(/[A-Za-z0-9_-]+/)<slug>', sj.get('post_url') or '')
    posts, newest = latest_posts(out, domain, pm.group(1) if (pm and sj.get('builder') != 'wpstatic') else '')
    head = set_meta(head + '</head>', 'property', 'og:site_name', f'{kw} | {name}' if name else kw)[:-7]
    if newest:
        head += f'<meta property="article:modified_time" content="{newest.astimezone(KST).isoformat(timespec="seconds")}"><!-- home:mtime -->\n'
    main_html = rest[rest.find('<main'):rest.find('</main>')]; pre = rest[:rest.find('<main')]; post = rest[rest.find('</main>'):]
    # ③ h2 "키워드 : 소제목" + id
    secs = []; toc = []; n_pref = 0; idn = 0
    def h2sub(m):
        nonlocal n_pref, idn
        attrs, inner = m.group(1), m.group(2); t = text(inner)
        keep = (kw in t) or H2_KEEP.search(t) or (name and name[:3] in t) or n_pref >= 8 or not t
        idm = re.search(r'\bid="([^"]+)"', attrs)
        if idm: hid = idm.group(1)
        else: idn += 1; hid = f'home-sec-{idn}'; attrs += f' id="{hid}"'
        if not keep:
            n_pref += 1; inner = f'{html.escape(kw)} : ' + inner; secs.append((t, m.end()))
            toc.append((hid, f'{kw} : {t}'))
        elif H2_KEEP.search(t) and '주요 안내' not in t: toc.append((hid, t))
        return f'<h2{attrs}>{inner}</h2>'
    hero = main_html.find('<h1')
    guide_at = main_html.rfind('<article class="source-homeguide"', 0, hero)
    if guide_at == -1: guide_at = main_html.rfind('<section', 0, hero)
    if guide_at == -1: guide_at = 0
    top, guide = main_html[:guide_at], main_html[guide_at:]
    guide_src = guide
    guide = re.sub(r'<h2\b([^>]*)>(.*?)</h2>', h2sub, guide, flags=re.S)
    # FAQ 용 절(원래 제목, 문단들)
    sec_data = []
    for b in re.split(r'(?=<h2\b)', guide_src)[1:]:
        m = re.match(r'<h2\b[^>]*>(.*?)</h2>', b, re.S); t = text(m.group(1)) if m else ''
        if not t or kw in t or H2_KEEP.search(t) or (name and name[:3] in t): continue
        paras = re.findall(r'<p(?![^>]*class=)[^>]*>(.*?)</p>', b, re.S)
        if paras: sec_data.append((E.head_label(t, kw, 30), paras))
    # ⑤ 최근 글 6
    def latest_block(alt_kw=True):
        if not posts: return ''
        lis = []
        for i, (_, path, title) in enumerate(posts, 1):
            slug = urllib.parse.unquote(path.rstrip('/').rsplit('/', 1)[-1])
            img = out / 'images' / 'enrich' / f'{slug}-1.webp'
            alt = f'{kw} 글 이미지 ({i})' if alt_kw else f'최근 글 이미지 ({i})'
            im = f'<img src="/images/enrich/{html.escape(urllib.parse.quote(slug))}-1.webp" alt="{html.escape(alt, quote=True)}" width="1200" height="675" loading="lazy" decoding="async">' if img.is_file() else ''
            lis.append(f'<li><a href="{html.escape(path, quote=True)}">{im}<span>{html.escape(title)}</span></a></li>')
        return (f'<section class="home-latest" aria-labelledby="home-latest-h"><h2 id="home-latest-h">{html.escape(kw)} : 최근 안내 글</h2>'
                f'<!-- home:latest --><ul>{"".join(lis)}</ul><!-- /home:latest --></section>\n')
    # ⑥ FAQ
    has_faq = bool(re.search(r'자주 묻는|자주 확인하는 질문', text(main_html))) or '"FAQPage"' in s
    def faq_block(q_kw=True):
        if has_faq or not sec_data: return ''
        used = set(); items = []; seed = sum(map(ord, domain))
        for i in range(5):
            h, paras = sec_data[(i + seed) % len(sec_data)]
            a_s, a_plain = FAQ_A[i]
            x = E.full_sentence(paras, used, limit=70, hint=h) if a_s else None
            x = x[:-1] if x else None
            if x and (any(c in x for c in '“”"') or len(x) > 110): x = None
            q = (FAQ_Q if q_kw else FAQ_Q_NK)[i].format(kw=kw, h=h, g=E.gwa(h)); a = a_s.format(s=x) if x else a_plain
            items.append((q, a))
        items.append((FAQ_LAST[0].format(kw=kw) if q_kw else FAQ_LAST[1], FAQ_LAST[2]))
        body = ''.join(f'<div class="faq-item"><h3><span class="faq-q">Q.</span> {html.escape(q)}</h3><p><span class="faq-a">A.</span> {html.escape(a)}</p></div>' for q, a in items)
        return f'<section class="home-faq" id="home-faq"><h2 id="home-faq-h">{html.escape(kw)} : 자주 묻는 질문</h2>{body}</section>\n'
    # ⑦ 자매 링크
    sis = ''
    for d in SISTERS.get(domain, []):
        o = cfg.get(d)
        if o: sis += f'<a href="{html.escape(o["home"], quote=True)}">{html.escape(E.kw_parts(o["keyword"])[0])}</a> '
    if sis: sis = f'<p class="home-sister">함께 보는 안내: {sis.strip()}</p>'
    def assemble(toc_kw, alt_kw, q_kw, trim_alt):
        lb = latest_block(alt_kw); fb = faq_block(q_kw)
        t2 = list(toc)
        if lb: t2.insert(0, ('home-latest-h', f'{kw} : 최근 안내 글'))
        if fb: t2.append(('home-faq-h', f'{kw} : 자주 묻는 질문'))
        tocb = ('<nav class="home-toc" aria-label="목차"><strong>목차</strong><ol>' + ''.join(f'<li><a href="#{html.escape(i, quote=True)}">{html.escape(t if toc_kw else t.replace(kw + " : ", ""))}</a></li>' for i, t in t2) + '</ol></nav>\n') if len(t2) >= 4 else ''
        g = guide
        # 목차: 첫 "키워드 : " h2 가 든 section 앞
        if tocb:
            k = g.find(f'>{html.escape(kw)} : ')
            k = g.rfind('<section', 0, k) if k != -1 else -1
            g = (g[:k] + tocb + g[k:]) if k > 0 else g + tocb
        body = pre + top + lb + g + fb + post
        if trim_alt:   # 카드 6장 밖의 이미지 alt 에서 키워드 빼기
            seen = 0
            def altsub(m):
                nonlocal seen
                if kw not in m.group(2) or 'home-latest' in m.group(0): return m.group(0)
                seen += 1
                return m.group(0) if seen <= 6 else m.group(1) + re.sub(r'\s{2,}', ' ', m.group(2).replace(kw, '')).strip() + m.group(3)
            body = re.sub(r'(<img\b[^>]*\balt=")([^"]*)(")', altsub, body)
        if sis and '</footer>' in body: body = body.replace('</footer>', sis + '</footer>', 1)
        return body
    best = None
    for opts in ((True, True, True, False), (False, True, True, False), (False, False, True, False), (False, False, False, False), (False, False, False, True)):
        body = assemble(*opts); c = text(body[body.find('<body'):]).count(kw); best = (body, c, opts)
        if c <= KW_MAX: break
    body, c, opts = best
    body = body.replace('<body', '<body', 1)
    bm = re.search(r'<body\b[^>]*>', body); body = body[:bm.end()] + MARK + body[bm.end():]
    head += f'<style id="home-css">{CSS}</style>\n'
    p.write_text(head + body, encoding='utf-8')
    print(f'[{domain}] home v1: 키워드 {base_cnt}→{c} · h2 {n_pref} · 최근 글 {len(posts)} · FAQ {"기존" if has_faq else ("추가" if sec_data else "없음")} · 목차 {len(toc)} · 자매 {len(SISTERS.get(domain, []))} · 옵션(목차키워드,alt키워드,질문키워드,alt정리)={opts}')

if __name__ == '__main__':
    try: main()
    except Exception as e:   # 홈 보강이 실패해도 배포는 막지 않는다(홈은 원본 그대로 올라감)
        import traceback; traceback.print_exc(); print(f'::warning::home_hook 실패: {e}')
