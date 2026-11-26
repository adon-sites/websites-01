#!/usr/bin/env python3
"""photo_cards.py — 새 글 구조(v5) 대표 이미지를 '사진 + 글자'로 그린다(2026-11-26 사용자 승인 시범 구성).
사진은 photos/NN-k.jpg(1200×675, 왼쪽 절반이 빈 실사 사진). 글자는 왼쪽 64~504px 안에만 둔다(인물과 겹치지 않게).
어느 글에 어느 사진을 쓰는지는 pick() 이 정한다: 사이트 묶음(photo_sets.json) 안에서, 최근 window(20)편에 쓴 사진을 빼고,
글 분류에 맞는 주제 → 같은 계열(마케팅 01~08 / 건강 09~16) → 나머지 순. 글을 날짜순으로 훑으므로 새 글이 늘어도 앞 글의 사진은 바뀌지 않는다."""
import hashlib, json, re
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
PHOTOS = HERE / 'photos'
CODE = hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:12]
W, H = 1200, 675
TEXT_W = 440   # 글자 최대 폭(64 → 504px)

RULES = [  # (분류에 들어 있는 낱말, 주제 번호들) — 위에서부터 먼저 맞는 것
    (('치아', '구강', '치과'), ['09']), (('눈', '시력', '안과'), ['11']), (('관절', '근골격', '정형'), ['12']), (('여성',), ['13']),
    (('피부', '시술', '미용', '성형'), ['10', '13', '16']), (('건강', '의료', '진료', '수술'), ['16', '14', '15']),
    (('검색', 'SEO', '성과', '분석', '광고'), ['02']), (('블로그', '콘텐츠', '편집', '문장', '기획'), ['01', '06']),
    (('상담', '예약', '답변', '방문', '안내'), ['04', '07']), (('플레이스', '지역', '매장', '지점'), ['03']),
    (('홈페이지', '사용성', '접근성', '화면', '사이트'), ['05']), (('마케팅', '협업', '대행', '외주', '법률', '노무', '행정', '문서'), ['08', '06']),
    (('카페', '커뮤니티', '생활', '서비스'), ['07', '03']),
]
def topics_for(category):
    c = category or ''
    for words, ts in RULES:
        if any(w in c for w in words): return ts
    return ['01', '02', '06', '08']

def pick(domain, posts):
    """posts: [(slug, date, category)] (사진 대표 이미지 대상 글 전부) → {slug: 사진 id}. 날짜순으로 정해 최근 window 편과 겹치지 않게."""
    cfg = json.loads((HERE / 'photo_sets.json').read_text(encoding='utf-8')); me = (cfg.get('sites') or {}).get(domain) or {}
    bundle = [k for k in (me.get('photos') or []) if (PHOTOS / f'{k}.jpg').is_file()]
    frm = me.get('from'); limit = me.get('limit')
    if not bundle or not frm: return {}
    todo = sorted((p for p in posts if p[1] and p[1] >= frm), key=lambda p: (p[1], p[0]))
    if limit: todo = todo[:int(limit)]
    recent = deque(maxlen=min(int(cfg.get('window') or 20), max(1, len(bundle) - 1))); out = {}
    for slug, _date, cat in todo:
        free = [k for k in bundle if k not in recent]
        ts = topics_for(cat); grp = (lambda k: int(k[:2]) <= 8) if int(ts[0]) <= 8 else (lambda k: int(k[:2]) >= 9)
        order = lambda k: hashlib.md5((slug + k).encode()).hexdigest()
        for cand in ([k for k in free if k[:2] in ts], [k for k in free if grp(k)], free):
            if cand: k = min(cand, key=order); break
        out[slug] = k; recent.append(k)
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
