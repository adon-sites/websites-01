#!/usr/bin/env python3
"""photo_cards.py — 새 글 구조(v5) 대표 이미지를 '사진 + 글자'로 그린다(2026-11-26 사용자 승인 시범 구성).
사진은 photos/NN-k.jpg(1200×675, 왼쪽 절반이 빈 실사 사진). 글자는 왼쪽 64~504px 안에만 둔다(인물과 겹치지 않게).
어느 글에 어느 사진을 쓰는지는 pick() 이 정한다(규칙은 아래 주석). 글을 날짜순으로 훑으므로 새 글이 늘어도 앞 글의 사진은 바뀌지 않는다."""
import hashlib, json, re
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
PHOTOS = HERE / 'photos'
CODE = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12]
W, H = 1200, 675
TEXT_W = 440   # 글자 최대 폭(64 → 504px)

# ── 고르는 규칙(사용자 2026-11-26 18:13) ──────────────────────────────────────────
# 가. 글이 특정 진료과·건강 주제를 직접 다루면 그 주제 사진(09~19)에서만 고른다. 다른 진료과 사진은 절대 쓰지 않는다.
# 나. 그 주제 사진이 없거나 다 썼으면 병원 접수·안내 사진(19) → 마케팅 업무 사진(01~08) 순으로 고른다.
# 다. 진료과와 무관한 글(블로그 운영·검색 노출·계약·보고 등)은 글 분류에 맞는 업무 사진(01~08)에서 고른다.
# 중복 제외: 업무 사진은 최근 10편에 쓴 것 제외. 진료과 사진은 최근 10편 제외 → 안 되면 직전 3편만 제외 → 그래도 없으면 나.
# 사이트 묶음(photo_sets.json sites[도메인].photos)은 업무 사진에만 적용, 진료과 사진은 모든 사이트 공용.
DEPT = [  # (글 분류·제목에 들어 있는 낱말, 주제 번호) — 위에서부터 먼저 맞는 것. 성형(17)·피부·미용(10)은 '눈 성형'이 안과로 가지 않게 안과보다 먼저.
    (('치과', '치아', '구강', '임플란트', '충치', '잇몸', '사랑니', '치열', '스케일링'), '09'),
    (('성형', '쌍꺼풀', '윤곽', '재수술', '눈매', '코 수술'), '17'),
    (('피부', '미용', '시술', '모발', '탈모', '여드름', '기미', '색소', '리프팅', '보톡스', '필러', '제모', '흉터'), '10'),
    (('안과', '시력', '라식', '라섹', '백내장', '녹내장', '안구', '렌즈', '눈 건강', '눈·시력', '눈 '), '11'),
    (('정형외과', '관절', '근골격', '척추', '무릎', '어깨', '허리', '디스크', '도수치료'), '12'),
    (('여성 건강', '산부인과', '여성의원', '임신', '난임', '갱년기', '자궁', '생리'), '13'),
    (('요양', '간병', '어르신', '노인', '돌봄'), '18'),
    (('수면', '불면', '잠들', '숙면'), '15'), (('스트레칭',), '14'), (('건강검진', '검진 결과'), '16'),
    (('의료기관', '병원 방문', '진료 준비', '접수', '문진'), '19'),   # 특정 진료과가 아닌 병원 접수·안내 글
]
WORK = [  # (분류에 들어 있는 낱말, 업무 사진 주제들)
    (('검색', 'SEO', '성과', '분석', '광고'), ['02']), (('블로그', '콘텐츠', '편집', '문장', '기획'), ['01', '06']),
    (('상담', '예약', '답변', '방문', '안내'), ['04', '07']), (('플레이스', '지역', '매장', '지점'), ['03']),
    (('홈페이지', '사용성', '접근성', '화면', '사이트'), ['05']), (('마케팅', '협업', '대행', '외주', '법률', '노무', '행정', '문서'), ['08', '06']),
    (('카페', '커뮤니티', '생활', '서비스'), ['07', '03']),
]
def dept_for(category, title):
    t = f'{category or ""} {title or ""} '
    for words, n in DEPT:
        if any(w in t for w in words): return n
    return None
def work_topics(category):
    c = category or ''
    for words, ts in WORK:
        if any(w in c for w in words): return ts
    return ['01', '02', '06', '08']

def pick(domain, posts, detail=False):
    """posts: [(slug, date, category, title)] (새 글 구조 글 전부) → {slug: 사진 id} (detail=True 면 {slug: (사진 id, 이유)}). 날짜순으로 정한다."""
    cfg = json.loads((HERE / 'photo_sets.json').read_text(encoding='utf-8')); me = (cfg.get('sites') or {}).get(domain) or {}
    have = lambda k: (PHOTOS / f'{k}.jpg').is_file()
    batches = sorted(cfg.get('batches') or [], key=lambda b: b['at'])
    pools = [(b['at'], [k for k in (b.get('sites') or {}).get(domain, []) if int(k[:2]) <= 8 and have(k)], [k for k in (b.get('dept') or []) if have(k)]) for b in batches]
    frm = me.get('from'); limit = me.get('limit')
    if not pools or not frm: return {}
    todo = sorted((p for p in posts if p[1] and p[1] >= frm), key=lambda p: (p[1], p[0]))
    if limit: todo = todo[:int(limit)]
    win = int(cfg.get('window') or 10); recent = deque(maxlen=win); out = {}
    kw_from = cfg.get('kw_strip_from') or '9999'; kws = []
    try:
        kws.append((json.loads((HERE.parent.parent / 'sites' / domain / 'content' / 'company.json').read_text(encoding='utf-8')).get('seo') or {}).get('primary') or '')
        kws.append(((json.loads((HERE / 'enrich_sites.json').read_text(encoding='utf-8')).get(domain)) or {}).get('keyword_new') or '')
    except Exception: pass
    kws = sorted({w_.strip() for w_ in kws if w_ and w_.strip()}, key=len, reverse=True)
    grp = {}
    for g in (cfg.get('scenes') or []):
        for k_ in g: grp[k_] = set(g)
    wide = lambda ks: set(ks) | {m_ for k_ in ks for m_ in grp.get(k_, ())}   # 같은 장면의 다른 판(그림체가 달라도)도 함께 제외
    # (병원 접수·안내 사진 19 는 주제 사진이 모자랄 때 업무 사진보다 먼저 쓴다 — 아래 desk)
    for slug, _date, cat, title in todo:
        # 글 날짜보다 앞선 판 중 가장 늦은 판(없으면 첫 판) — 사진을 더 받아 판이 늘어도 앞 글의 사진은 그대로
        _at, bundle, shared = ([p_ for p_ in pools if p_[0] <= _date] or pools[:1])[-1]
        if not bundle: continue
        desk = [x for x in shared if x[:2] == '19']
        order = lambda k: hashlib.md5((slug + k).encode()).hexdigest()
        r = list(recent); k = why = None
        if kws and _date >= kw_from:   # 사이트 대표 키워드는 빼고 판단 → 아무것도 안 나오면 (제목에 키워드가 있던 글만) 키워드의 진료과
            t2 = title or ''
            for w_ in kws: t2 = t2.replace(w_, ' ')
            dep = dept_for(cat, t2) or (dept_for('', ' '.join(kws)) if t2 != (title or '') else None)
        else: dep = dept_for(cat, title)
        if dep:
            pool = [x for x in shared if x[:2] == dep]
            thin = dep in (cfg.get('thin') or {}).get('depts', []) and _date >= cfg['thin']['from']   # 장면 수가 적은 주제: 최근 10편에 다 썼으면 직전 3편 완화 없이 접수·안내로
            for ex in ((wide(r),) if thin else (wide(r), wide(r[-3:]))):
                cand = [x for x in pool if x not in ex]
                if cand: k, why = min(cand, key=order), '가'; break
            if not k and dep != '19':
                for ex in (wide(r), wide(r[-3:])):
                    cand = [x for x in desk if x not in ex]
                    if cand: k, why = min(cand, key=order), '나(접수·안내)'; break
        if not k:
            free = [x for x in bundle if x not in r] or [x for x in bundle if x not in r[-3:]] or bundle
            ts = work_topics(cat); cand = [x for x in free if x[:2] in ts] or free
            k, why = min(cand, key=order), ('나' if dep else '다')
        out[slug] = (k, why) if detail else k; recent.append(k)
    return out

_FADE = None
def _base(photo_id):
    global _FADE
    im = Image.open(PHOTOS / f'{photo_id}.jpg').convert('RGB')
    if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
    if _FADE is None:
        _FADE = Image.new('L', (W, H), 0); d = ImageDraw.Draw(_FADE)
        for x in range(W): d.line([x, 0, x, H], fill=235 if x < 470 else max(0, int(235 * (1 - (x - 470) / 150))))
    im.paste(Image.new('RGB', (W, H), '#ffffff'), (0, 0), _FADE); return im

def hero(title, kw, site, pal, photo_id):
    """대표 이미지: 키워드 라벨 + 글 제목 + 사이트 이름(왼쪽) / 사진(오른쪽)."""
    import make_images as M
    img = _base(photo_id); d = ImageDraw.Draw(img); d.rectangle([0, 0, 12, H], fill=pal[0])
    fk = M.font(M.FONT_B, 26)
    while d.textlength(kw, font=fk) > TEXT_W - 44 and fk.size > 18: fk = M.font(M.FONT_B, fk.size - 2)
    d.rounded_rectangle([64, 64, 64 + d.textlength(kw, font=fk) + 44, 112], radius=24, fill=pal[0]); d.text((86, 64 + (48 - fk.size) // 2 - 4), kw, font=fk, fill='#ffffff')
    size = 50
    while True:
        ft = M.font(M.FONT_B, size); lines = M.wrap(d, title, ft, TEXT_W)
        if len(lines) <= 5 or size <= 32: break
        size -= 3
    y = 152
    for ln in lines[:6]:
        d.text((64, y), ln, font=ft, fill=pal[0]); y += int(size * 1.4)
    d.line([64, H - 100, 154, H - 100], fill=pal[2], width=4); d.text((64, H - 84), site, font=M.font(M.FONT_R, 24), fill='#4a5563')
    return img

def hero2(title, kw, site, pal, photo_id, summary, big=False):
    """대표 이미지 + 제목 아래 요약 한 문장(도입의 첫 문장). 요약이 글자 자리(왼쪽 64~504)와 아래 여백에 다 들어갈 때만 넣고, 넘치면 요약 없이 hero 와 같게 그린다."""
    import make_images as M
    img = _base(photo_id); d = ImageDraw.Draw(img); d.rectangle([0, 0, 12, H], fill=pal[0])
    fk = M.font(M.FONT_B, 26)
    while d.textlength(kw, font=fk) > TEXT_W - 44 and fk.size > 18: fk = M.font(M.FONT_B, fk.size - 2)
    d.rounded_rectangle([64, 64, 64 + d.textlength(kw, font=fk) + 44, 112], radius=24, fill=pal[0]); d.text((86, 64 + (48 - fk.size) // 2 - 4), kw, font=fk, fill='#ffffff')
    ok = False
    for ss in ((26, 23) if big else (23,)):   # 요약 글자: 한 단계 큰 26 이 들어가면 26, 아니면 23
        fs = M.font(M.FONT_R, ss); sl = M.wrap(d, summary or '', fs, TEXT_W) if summary else []; slh = int(ss * 1.52)
        if len(sl) > 4: continue
        for size in (46, 43, 40, 37, 34, 32):
            ft = M.font(M.FONT_B, size); lines = M.wrap(d, title, ft, TEXT_W); need = len(lines) * int(size * 1.4) + (18 + len(sl) * slh if sl else 0)
            if len(lines) <= 5 and 152 + need <= H - 118: ok = True; break
        if ok: break
    if not ok: return hero(title, kw, site, pal, photo_id)   # 요약까지 넣으면 넘침 → 요약을 뺀다
    y = 152
    for ln in lines: d.text((64, y), ln, font=ft, fill=pal[0]); y += int(ft.size * 1.4)
    y += 18
    for ln in sl: d.text((64, y), ln, font=fs, fill='#3a4450'); y += slh
    d.line([64, H - 100, 154, H - 100], fill=pal[2], width=4); d.text((64, H - 84), site, font=M.font(M.FONT_R, 24), fill='#4a5563')
    return img
